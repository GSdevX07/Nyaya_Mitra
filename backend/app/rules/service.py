"""
service.py - High-Level Deterministic Legal Rules Service.
==========================================================
Executes versioned rules against case facts, captures structured explanations,
persists execution audit logs, and supports past assessment reconstruction.
Provides backward-compatible evaluate_eligibility() interface.
"""

from __future__ import annotations
import uuid
import datetime
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

# In-memory execution store for high-speed audit and reconstruction
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
        Execute deterministic evaluation for a case and record execution audit trail.
        """
        rule = self.registry.get_rule(rule_id or rule_version)
        result = evaluate_bnss_479_detention(
            case=case,
            rule_def=rule,
            provenance_map=provenance_map,
            conflicting_records=conflicting_records,
        )

        # Record execution audit log
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

        return result

    def reconstruct_assessment(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Reconstruct a past assessment exactly as evaluated historically using the
        input fact snapshot, rule version, provenance, and explanation.
        """
        return _RULE_EXECUTIONS.get(execution_id)

    def list_rules(self) -> List[Dict[str, Any]]:
        return self.registry.list_rules()

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        rule = self.registry.get_rule(rule_id)
        if not rule:
            return None
        res = rule.dict()
        res["historical_versions"] = self.registry.get_rule_versions(rule_id)
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
            "to_state": target_state.value,
            "actor_id": actor.id,
            "actor_role": actor.role.value,
            "notes": notes,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _RULE_AUDIT_TRAIL.append(audit_item)
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
