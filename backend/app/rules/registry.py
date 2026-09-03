"""
registry.py - Persistent Legal Rule Registry & Governance Lifecycle Controller.
================================================================================
Maintains authoritative versioned legal rules with persistent database storage:
- Automatically initializes and synchronizes with the persistent `legal_rules`
  and `legal_rule_versions` tables in the database.
- Truthfully marks unreviewed baseline rules as DEMO_BASELINE without fabricating
  human approval records.
- Enforces strict governance over rule lifecycle transitions:
    DRAFT -> LEGAL_REVIEW -> APPROVED -> ACTIVE -> SUPERSEDED / RETIRED
  (Approvals and activations strictly require active SUPERVISING_LEGAL_OFFICER authority;
   Platform Administrators are strictly barred from enacting statutory legal policy).
- FAILS CLOSED: Never silently falls back to active rule if an invalid rule ID is requested.
"""

from __future__ import annotations
import copy
import json
import uuid
import datetime
import logging
from typing import Dict, Any, Optional, List

from app.auth.roles import Role
from app.auth.dependencies import AuthUser
from app.rules.models import (
    RuleCategory,
    RuleLifecycleState,
    RuleMachineStatus,
    LegalRuleDefinition,
)

logger = logging.getLogger(__name__)


class LegalRuleRegistry:
    """Persistent registry managing versioned legal rule definitions and lifecycle transitions."""

    def __init__(self):
        self._rules: Dict[str, LegalRuleDefinition] = {}
        self._versions: Dict[str, List[Dict[str, Any]]] = {}
        self._active_rule_id: str = "RULE-BNSS-479-THRESHOLD-V1"
        self._init_registry()

    def _init_registry(self):
        """Initialize registry from persistent database, seeding baseline if empty."""
        # 1. Register canonical demo baseline rules in memory
        self._register_canonical_baselines()

        # 2. Synchronize with persistent database
        self._sync_with_db()

    def _register_canonical_baselines(self):
        """
        Register canonical statutory rule baselines.
        NOTE: Metadata is truthfully marked as DEMO_BASELINE to respect the project's
        strict 'no fabricated governance/data' principle.
        """
        bnss_rule = LegalRuleDefinition(
            rule_id="RULE-BNSS-479-THRESHOLD-V1",
            rule_version="BNSS_479_RULESET_V1_2023",
            title="BNSS Section 479 Undertrial Detention Statutory Rule",
            jurisdiction="India / National",
            category=RuleCategory.CUSTODY_DURATION_THRESHOLD,
            statutory_source="Bharatiya Nagarik Suraksha Sanhita, 2023 (Section 479)",
            effective_date="2024-07-01",
            lifecycle_state=RuleLifecycleState.ACTIVE,
            applicability_conditions={
                "target_prisoner_category": "UNDERTRIAL",
                "applicable_statute": "BNSS_2023",
                "retrospective_application": "Supreme Court SMW (Crl) No. 4/2021",
                "governance_status": "DEMO_BASELINE",
            },
            required_inputs=[
                "custody_days",
                "max_sentence_days_for_offense",
                "repeat_offender",
                "punishable_by_death_or_life",
                "multiple_active_cases",
            ],
            calculation_method="math.ceil(max_sentence_days * threshold_fraction)",
            exclusions_and_provisos=[
                {"name": "Section 479(1) Proviso 2", "effect": "EXCLUDE_CAPITAL_AND_LIFE"},
                {"name": "Section 479(1) Proviso 3", "effect": "MANUAL_REVIEW_MULTIPLE_PROCEEDINGS"},
                {"name": "Section 479(1) Delay Proviso", "effect": "EXCLUDE_ACCUSED_ATTRIBUTABLE_DELAY"},
            ],
            output_statuses=[
                RuleMachineStatus.THRESHOLD_REACHED,
                RuleMachineStatus.THRESHOLD_NOT_REACHED,
                RuleMachineStatus.POTENTIALLY_APPLICABLE,
                RuleMachineStatus.INSUFFICIENT_DATA,
                RuleMachineStatus.EXCLUDED,
                RuleMachineStatus.MANUAL_REVIEW,
            ],
            explanation_template="Section 479 BNSS: {category_label}. Countable detention ({countable_days}/{required_days} days).",
            legal_review_metadata={
                "status": "DEMO_BASELINE — LEGAL VALIDATION REQUIRED BEFORE PRODUCTION ACTIVATION",
                "review_notes": (
                    "Statutory rule encoding modeled on BNSS Section 479 statutory text. "
                    "Seeded for demonstration and testing; requires formal institutional panel sign-off before production live deployment."
                ),
                "reviewed_by": None,
                "review_timestamp": None,
            },
            approval_metadata={
                "status": "DEMO_BASELINE — FORMAL AUTHORIZATION REQUIRED",
                "approval_notes": (
                    "Baseline seeded for demonstration and testing. Production activation "
                    "requires explicit human legal review by authorized Supervising Legal Officer."
                ),
                "approved_by": None,
                "approval_role": None,
                "approval_timestamp": None,
            },
            created_at="2024-07-01T00:00:00Z",
            updated_at="2024-07-01T00:00:00Z",
        )
        self.register_rule(bnss_rule, persist=False)

        # Historical CRPC 436A comparison rule
        crpc_rule = LegalRuleDefinition(
            rule_id="RULE-CRPC-436A-THRESHOLD-V1",
            rule_version="CRPC_436A_RULESET_V1_1973",
            title="CrPC Section 436A Undertrial Detention Rule (Pre-July 2024)",
            jurisdiction="India / National",
            category=RuleCategory.CUSTODY_DURATION_THRESHOLD,
            statutory_source="Code of Criminal Procedure, 1973 (Section 436A)",
            effective_date="2005-06-23",
            lifecycle_state=RuleLifecycleState.SUPERSEDED,
            applicability_conditions={
                "applicable_statute": "CRPC_1973",
                "status": "HISTORICAL_COMPARISON_BASELINE",
            },
            required_inputs=["custody_days", "max_sentence_days_for_offense"],
            calculation_method="math.ceil(max_sentence_days * 0.5)",
            exclusions_and_provisos=[
                {"name": "Section 436A Proviso", "effect": "EXCLUDE_DEATH_OFFENSES"},
            ],
            output_statuses=[
                RuleMachineStatus.THRESHOLD_REACHED,
                RuleMachineStatus.THRESHOLD_NOT_REACHED,
            ],
            explanation_template="Section 436A CrPC historical threshold: 1/2 of maximum imprisonment.",
            legal_review_metadata={
                "status": "HISTORICAL_COMPARATOR_REGIME",
                "review_notes": "Pre-July 2024 CrPC Section 436A historical comparator regime.",
            },
            approval_metadata={
                "status": "HISTORICAL_REGIME",
                "approved_by": None,
            },
            created_at="2005-06-23T00:00:00Z",
            updated_at="2024-07-01T00:00:00Z",
        )
        self.register_rule(crpc_rule, persist=False)

    def _sync_with_db(self):
        """Persist seeded rules to DB if table is empty, or load persistent rules from DB."""
        try:
            from app.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check existing rules count
            cursor.execute("SELECT COUNT(*) FROM legal_rules")
            row = cursor.fetchone()
            count = row[0] if row else 0

            if count == 0:
                # Seed database from canonical in-memory baseline
                for r in self._rules.values():
                    self._persist_rule_to_db(r, conn)
                conn.commit()
            else:
                # Load persistent rules from DB
                cursor.execute("SELECT * FROM legal_rules")
                rows = cursor.fetchall()
                for r_row in rows:
                    rule_def = self._row_to_rule_def(r_row)
                    self._rules[rule_def.rule_id] = rule_def

                # Load versions
                cursor.execute("SELECT rule_id, version_tag, rule_snapshot, created_at FROM legal_rule_versions")
                v_rows = cursor.fetchall()
                for v in v_rows:
                    rid = v["rule_id"] if isinstance(v, dict) or hasattr(v, "keys") else v[0]
                    vtag = v["version_tag"] if isinstance(v, dict) or hasattr(v, "keys") else v[1]
                    snap = v["rule_snapshot"] if isinstance(v, dict) or hasattr(v, "keys") else v[2]
                    cat = v["created_at"] if isinstance(v, dict) or hasattr(v, "keys") else v[3]
                    if rid not in self._versions:
                        self._versions[rid] = []
                    self._versions[rid].append({
                        "version_tag": vtag,
                        "rule_snapshot": json.loads(snap) if isinstance(snap, str) else snap,
                        "recorded_at": cat,
                    })

            conn.close()
        except Exception as ex:
            logger.warning(f"LegalRuleRegistry DB sync note: {ex}")

    def _persist_rule_to_db(self, rule: LegalRuleDefinition, conn=None):
        """Insert or update rule and snapshot into persistent DB tables."""
        should_close = False
        try:
            if conn is None:
                from app.database import get_db_connection
                conn = get_db_connection()
                should_close = True

            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO legal_rules (
                    id, rule_version, title, jurisdiction, category, statutory_source,
                    effective_date, lifecycle_state, applicability_conditions, required_inputs,
                    calculation_method, exclusions_and_provisos, output_statuses,
                    explanation_template, legal_review_metadata, approval_metadata,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    rule_version=excluded.rule_version,
                    title=excluded.title,
                    jurisdiction=excluded.jurisdiction,
                    category=excluded.category,
                    statutory_source=excluded.statutory_source,
                    effective_date=excluded.effective_date,
                    lifecycle_state=excluded.lifecycle_state,
                    applicability_conditions=excluded.applicability_conditions,
                    required_inputs=excluded.required_inputs,
                    calculation_method=excluded.calculation_method,
                    exclusions_and_provisos=excluded.exclusions_and_provisos,
                    output_statuses=excluded.output_statuses,
                    explanation_template=excluded.explanation_template,
                    legal_review_metadata=excluded.legal_review_metadata,
                    approval_metadata=excluded.approval_metadata,
                    updated_at=excluded.updated_at
                """,
                (
                    rule.rule_id,
                    rule.rule_version,
                    rule.title,
                    rule.jurisdiction,
                    rule.category.value if hasattr(rule.category, "value") else str(rule.category),
                    rule.statutory_source,
                    rule.effective_date,
                    rule.lifecycle_state.value if hasattr(rule.lifecycle_state, "value") else str(rule.lifecycle_state),
                    json.dumps(rule.applicability_conditions),
                    json.dumps(rule.required_inputs),
                    rule.calculation_method,
                    json.dumps(rule.exclusions_and_provisos),
                    json.dumps([s.value if hasattr(s, "value") else str(s) for s in rule.output_statuses]),
                    rule.explanation_template,
                    json.dumps(rule.legal_review_metadata),
                    json.dumps(rule.approval_metadata),
                    rule.created_at,
                    rule.updated_at,
                )
            )

            # Insert version snapshot
            cursor.execute(
                """
                INSERT INTO legal_rule_versions (id, rule_id, version_tag, rule_snapshot, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"VER-{uuid.uuid4().hex[:10].upper()}",
                    rule.rule_id,
                    rule.rule_version,
                    json.dumps(rule.dict()),
                    rule.updated_at or rule.created_at,
                    rule.approval_metadata.get("approved_by") if rule.approval_metadata else "system",
                )
            )

            if should_close:
                conn.commit()
                conn.close()
        except Exception as ex:
            logger.warning(f"Failed to persist rule to DB: {ex}")
            if should_close and conn:
                conn.close()

    def _row_to_rule_def(self, row) -> LegalRuleDefinition:
        """Convert SQLite row to LegalRuleDefinition."""
        def _get(key, idx):
            if isinstance(row, dict) or hasattr(row, "keys"):
                return row[key]
            return row[idx]

        out_statuses_raw = json.loads(_get("output_statuses", 12)) if isinstance(_get("output_statuses", 12), str) else _get("output_statuses", 12)
        out_statuses = [RuleMachineStatus(s) for s in out_statuses_raw]

        return LegalRuleDefinition(
            rule_id=_get("id", 0),
            rule_version=_get("rule_version", 1),
            title=_get("title", 2),
            jurisdiction=_get("jurisdiction", 3),
            category=RuleCategory(_get("category", 4)),
            statutory_source=_get("statutory_source", 5),
            effective_date=_get("effective_date", 6),
            lifecycle_state=RuleLifecycleState(_get("lifecycle_state", 7)),
            applicability_conditions=json.loads(_get("applicability_conditions", 8)) if isinstance(_get("applicability_conditions", 8), str) else _get("applicability_conditions", 8),
            required_inputs=json.loads(_get("required_inputs", 9)) if isinstance(_get("required_inputs", 9), str) else _get("required_inputs", 9),
            calculation_method=_get("calculation_method", 10),
            exclusions_and_provisos=json.loads(_get("exclusions_and_provisos", 11)) if isinstance(_get("exclusions_and_provisos", 11), str) else _get("exclusions_and_provisos", 11),
            output_statuses=out_statuses,
            explanation_template=_get("explanation_template", 13),
            legal_review_metadata=json.loads(_get("legal_review_metadata", 14)) if isinstance(_get("legal_review_metadata", 14), str) else _get("legal_review_metadata", 14),
            approval_metadata=json.loads(_get("approval_metadata", 15)) if isinstance(_get("approval_metadata", 15), str) else _get("approval_metadata", 15),
            created_at=_get("created_at", 16),
            updated_at=_get("updated_at", 17),
        )

    def register_rule(self, rule: LegalRuleDefinition, persist: bool = True):
        """Register or update a rule and save its immutable version snapshot."""
        self._rules[rule.rule_id] = rule
        if rule.rule_id not in self._versions:
            self._versions[rule.rule_id] = []
        self._versions[rule.rule_id].append({
            "version_tag": rule.rule_version,
            "rule_snapshot": rule.dict(),
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

        if persist:
            self._persist_rule_to_db(rule)

    def get_rule(self, rule_id: Optional[str] = None) -> LegalRuleDefinition:
        """
        Retrieve rule by rule_id or version tag.
        If rule_id is None, defaults to the active rule.
        If an explicit rule_id or rule_version is requested but not found, FAILS CLOSED:
        raises KeyError (never silently falls back to active rule).
        """
        if rule_id is None:
            active = self._rules.get(self._active_rule_id)
            if not active:
                raise KeyError(f"No active rule configured in registry (expected '{self._active_rule_id}').")
            return active

        # Lookup by exact rule_id
        if rule_id in self._rules:
            return self._rules[rule_id]

        # Lookup by rule_version tag
        for r in self._rules.values():
            if r.rule_version == rule_id:
                return r

        # FAIL CLOSED: Do not silently fallback!
        raise KeyError(f"Legal rule ID or version '{rule_id}' not found in registry.")

    def list_rules(self) -> List[Dict[str, Any]]:
        return [r.dict() for r in self._rules.values()]

    def get_rule_versions(self, rule_id: str) -> List[Dict[str, Any]]:
        # Verify rule exists
        if rule_id not in self._rules and not any(r.rule_version == rule_id for r in self._rules.values()):
            raise KeyError(f"Rule '{rule_id}' not found in registry.")
        return self._versions.get(rule_id, [])

    def transition_lifecycle(
        self,
        rule_id: str,
        target_state: RuleLifecycleState,
        actor: AuthUser,
        notes: str = "",
    ) -> LegalRuleDefinition:
        """
        Enforce strict governance over legal rule lifecycles:
        - Only SUPERVISING_LEGAL_OFFICER can approve rules or transition from LEGAL_REVIEW -> APPROVED.
        - PLATFORM_ADMIN cannot approve or activate legal rules.
        """
        rule = self.get_rule(rule_id)
        current_state = rule.lifecycle_state

        # Idempotent no-op if rule is already in requested state
        if target_state == current_state:
            return rule

        # Legal Authorization Guard: Approvals & Activations require active legal authority
        if target_state in (RuleLifecycleState.APPROVED, RuleLifecycleState.ACTIVE):
            if actor.role != Role.SUPERVISING_LEGAL_OFFICER:
                raise PermissionError(
                    f"Forbidden: Legal rule lifecycle transition to '{target_state.value}' "
                    f"requires active SUPERVISING_LEGAL_OFFICER authority. Role '{actor.role.value}' is not authorized."
                )

        # Valid transitions
        allowed = {
            RuleLifecycleState.DRAFT: [RuleLifecycleState.LEGAL_REVIEW, RuleLifecycleState.RETIRED],
            RuleLifecycleState.LEGAL_REVIEW: [RuleLifecycleState.APPROVED, RuleLifecycleState.DRAFT, RuleLifecycleState.RETIRED],
            RuleLifecycleState.APPROVED: [RuleLifecycleState.ACTIVE, RuleLifecycleState.RETIRED],
            RuleLifecycleState.ACTIVE: [RuleLifecycleState.SUPERSEDED, RuleLifecycleState.RETIRED],
            RuleLifecycleState.SUPERSEDED: [RuleLifecycleState.RETIRED],
            RuleLifecycleState.RETIRED: [],
        }

        if target_state not in allowed.get(current_state, []):
            raise ValueError(f"Illegal lifecycle transition: cannot move from '{current_state.value}' to '{target_state.value}'.")

        updated_rule = copy.deepcopy(rule)
        updated_rule.lifecycle_state = target_state
        updated_rule.updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if target_state == RuleLifecycleState.APPROVED:
            updated_rule.approval_metadata = {
                "status": "APPROVED_BY_AUTHORIZED_OFFICER",
                "approved_by": getattr(actor, "full_name", None) or actor.id,
                "approval_role": actor.role.value,
                "approval_timestamp": updated_rule.updated_at,
                "approval_notes": notes,
            }
        elif target_state == RuleLifecycleState.LEGAL_REVIEW:
            updated_rule.legal_review_metadata = {
                "status": "UNDER_FORMAL_LEGAL_REVIEW",
                "reviewed_by": getattr(actor, "full_name", None) or actor.id,
                "review_role": actor.role.value,
                "review_timestamp": updated_rule.updated_at,
                "review_notes": notes,
            }

        self.register_rule(updated_rule, persist=True)
        return updated_rule


RULE_REGISTRY = LegalRuleRegistry()
