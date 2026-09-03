"""
service.py - High-Level Deterministic Legal Rules Service.
==========================================================
Executes versioned rules against case facts, captures structured explanations,
persists execution audit logs to the database, and supports historical assessment
reconstruction across server restarts.
Provides backward-compatible evaluate_eligibility() interface.
"""

from __future__ import annotations
import json
import uuid
import datetime
import logging
from typing import Dict, Any, Optional, List

from app.rules.models import (
    RuleMachineStatus,
    RuleExplanation,
    RuleExecutionResult,
    LegalRuleDefinition,
    RuleLifecycleState,
)
from app.rules.registry import RULE_REGISTRY, LegalRuleRegistry
from app.rules.bnss_479_engine import evaluate_bnss_479_detention
from app.auth.roles import Role
from app.auth.dependencies import AuthUser

logger = logging.getLogger(__name__)

# In-memory execution store for fast lookups (backed by DB)
_RULE_EXECUTIONS: Dict[str, Dict[str, Any]] = {}
_RULE_AUDIT_TRAIL: List[Dict[str, Any]] = []


class RuleEngineService:
    """Service facade for deterministic legal rule execution and lifecycle management."""

    def __init__(self, registry: Optional[LegalRuleRegistry] = None):
        self.registry = registry or RULE_REGISTRY

    def evaluate_case(
        self,
        case: Any,
        rule_id: Optional[str] = None,
        rule_version: Optional[str] = None,
        actor: Optional[AuthUser] = None,
        provenance_map: Optional[Dict[str, Any]] = None,
        conflicting_records: Optional[List[Dict[str, Any]]] = None,
    ) -> RuleExecutionResult:
        """
        Execute deterministic evaluation for a case and record execution audit trail persistently.
        """
        rule = self.registry.get_rule(rule_id or rule_version)
        result = evaluate_bnss_479_detention(
            case=case,
            rule_def=rule,
            provenance_map=provenance_map,
            conflicting_records=conflicting_records,
        )

        # Build execution audit log entry
        audit_entry = {
            "execution_id": result.execution_id,
            "rule_id": result.rule_id,
            "rule_version": result.rule_version,
            "case_id": result.case_id,
            "input_snapshot": result.explanation.input_facts_used,
            "input_provenance": result.explanation.input_provenance,
            "machine_status": result.machine_status.value,
            "explanation_json": result.explanation.dict(),
            "executed_by": getattr(actor, "id", "system") if actor else "system",
            "executed_role": getattr(actor, "role", Role.PLATFORM_ADMIN).value if actor else "SYSTEM",
            "execution_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _RULE_EXECUTIONS[result.execution_id] = audit_entry
        result.audit_record_id = result.execution_id

        # ── Persist Execution Record to Database ─────────────────────────────
        self._persist_execution_to_db(audit_entry)

        return result

    def _persist_execution_to_db(self, entry: Dict[str, Any]):
        """Persist execution record to legal_rule_executions table."""
        try:
            from app.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO legal_rule_executions (
                    id, rule_id, rule_version, case_id, input_snapshot,
                    input_provenance, machine_status, explanation_json,
                    executed_by, executed_role, execution_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["execution_id"],
                    entry["rule_id"],
                    entry["rule_version"],
                    entry["case_id"],
                    json.dumps(entry["input_snapshot"]),
                    json.dumps(entry["input_provenance"]),
                    entry["machine_status"],
                    json.dumps(entry["explanation_json"]),
                    entry["executed_by"],
                    entry["executed_role"],
                    entry["execution_timestamp"],
                )
            )
            conn.commit()
            conn.close()
        except Exception as ex:
            logger.warning(f"Failed to persist legal rule execution to DB: {ex}")

    def reconstruct_assessment(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Reconstruct a past assessment exactly as evaluated historically using the
        input fact snapshot, rule version, provenance, and explanation.
        PERSISTENT: Fetches from DB if memory cache is cold or after server restart.
        """
        # 1. Fast path: check memory cache
        if execution_id in _RULE_EXECUTIONS:
            return _RULE_EXECUTIONS[execution_id]

        # 2. Persistent path: query database table
        try:
            from app.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, rule_id, rule_version, case_id, input_snapshot,
                       input_provenance, machine_status, explanation_json,
                       executed_by, executed_role, execution_timestamp
                FROM legal_rule_executions
                WHERE id = ?
                """,
                (execution_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                def _get(key, idx):
                    if isinstance(row, dict) or hasattr(row, "keys"):
                        return row[key]
                    return row[idx]

                input_snap = _get("input_snapshot", 4)
                input_prov = _get("input_provenance", 5)
                expl_raw = _get("explanation_json", 7)

                rec = {
                    "execution_id": _get("id", 0),
                    "rule_id": _get("rule_id", 1),
                    "rule_version": _get("rule_version", 2),
                    "case_id": _get("case_id", 3),
                    "input_snapshot": json.loads(input_snap) if isinstance(input_snap, str) else input_snap,
                    "input_provenance": json.loads(input_prov) if isinstance(input_prov, str) else input_prov,
                    "machine_status": _get("machine_status", 6),
                    "explanation_json": json.loads(expl_raw) if isinstance(expl_raw, str) else expl_raw,
                    "executed_by": _get("executed_by", 8),
                    "executed_role": _get("executed_role", 9),
                    "execution_timestamp": _get("execution_timestamp", 10),
                }
                # Populate cache
                _RULE_EXECUTIONS[execution_id] = rec
                return rec
        except Exception as ex:
            logger.warning(f"Database lookup failed for execution {execution_id}: {ex}")

        return None

    def list_rules(self) -> List[Dict[str, Any]]:
        return self.registry.list_rules()

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        try:
            rule = self.registry.get_rule(rule_id)
        except KeyError:
            return None
        res = rule.dict()
        try:
            res["historical_versions"] = self.registry.get_rule_versions(rule_id)
        except KeyError:
            res["historical_versions"] = []
        return res

    def transition_rule_lifecycle(
        self,
        rule_id: str,
        target_state: RuleLifecycleState,
        actor: AuthUser,
        notes: str = "",
    ) -> LegalRuleDefinition:
        rule = self.registry.transition_lifecycle(rule_id, target_state, actor, notes)
        audit_item = {
            "id": f"AUDIT-RULE-{uuid.uuid4().hex[:8].upper()}",
            "rule_id": rule_id,
            "action": f"TRANSITION_TO_{target_state.value}",
            "from_state": rule.lifecycle_state.value,
            "to_state": target_state.value,
            "actor_id": actor.id,
            "actor_role": actor.role.value,
            "notes": notes,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _RULE_AUDIT_TRAIL.append(audit_item)

        # Persist audit trail to DB
        try:
            from app.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO legal_rule_audit_trail (
                    id, rule_id, action, from_state, to_state, actor_id, actor_role, notes, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_item["id"],
                    audit_item["rule_id"],
                    audit_item["action"],
                    audit_item["from_state"],
                    audit_item["to_state"],
                    audit_item["actor_id"],
                    audit_item["actor_role"],
                    audit_item["notes"],
                    audit_item["timestamp"],
                )
            )
            conn.commit()
            conn.close()
        except Exception as ex:
            logger.warning(f"Failed to persist rule audit trail to DB: {ex}")

        return rule


_GLOBAL_SERVICE = RuleEngineService()


def evaluate_eligibility(case: Any, rule_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Drop-in backward-compatible function preserving Stage 0-7 caller contract
    while running on the deterministic Stage 8 legal rules engine.
    """
    res = _GLOBAL_SERVICE.evaluate_case(case=case, rule_version=rule_version)
    
    # Map into existing caller dictionary contract
    return {
        "case_id": res.case_id,
        "rule_version": res.rule_version,
        "eligible": res.is_eligible,
        "is_eligible": res.is_eligible,
        "human_review_required": (not res.is_eligible) or (res.machine_status == RuleMachineStatus.MANUAL_REVIEW) or (res.excluded_delay_days > 0),
        "threshold_fraction": res.threshold_fraction,
        "statutory_threshold_fraction": "1/3" if res.threshold_fraction < 0.4 else "1/2",
        "threshold_days": res.threshold_days,
        "category_label": (
            f"First-Time Offender Proviso ({res.threshold_fraction:.2f} of maximum sentence)"
            if res.threshold_fraction < 0.4
            else f"General Undertrial Threshold ({res.threshold_fraction:.2f} of maximum sentence)"
        ),
        "total_elapsed_calendar_days": res.total_elapsed_calendar_days,
        "excluded_delay_days": res.excluded_delay_days,
        "countable_custody_days": res.countable_custody_days,
        "required_custody_days": res.threshold_days,
        "days_overdue": res.days_overdue,
        "machine_status": res.machine_status.value,
        "exceptions_checked": {
            "capital_or_life_offence_exclusion": getattr(case, "punishable_by_death_or_life", False),
            "multiple_pending_proceedings_condition": getattr(case, "multiple_active_cases", False),
            "repeat_conviction_status": getattr(getattr(case, "urgency_flags", None), "repeat_offender", False),
            "accused_attributable_delay_identified": res.excluded_delay_days > 0,
        },
        "legal_basis": res.explanation.explanation_text,
        "statutory_signal": res.explanation.explanation_text,
        "disclaimer": res.explanation.disclaimer,
        "explanation": res.explanation.dict(),
        "execution_id": res.execution_id,
    }
