"""
registry.py - Legal Rule Registry & Governance Lifecycle Controller.
====================================================================
Maintains authoritative versioned legal rules, stores historical version
snapshots, enforces permission controls on rule lifecycle transitions:
  DRAFT -> LEGAL_REVIEW -> APPROVED -> ACTIVE -> SUPERSEDED / RETIRED
"""

from __future__ import annotations
import copy
import datetime
from typing import Dict, Any, Optional, List
from app.auth.roles import Role
from app.auth.dependencies import AuthUser
from app.rules.models import (
    RuleCategory,
    RuleLifecycleState,
    RuleMachineStatus,
    LegalRuleDefinition,
)


class LegalRuleRegistry:
    """Registry managing versioned legal rule definitions and lifecycle transitions."""

    def __init__(self):
        self._rules: Dict[str, LegalRuleDefinition] = {}
        self._versions: Dict[str, List[Dict[str, Any]]] = {}
        self._active_rule_id: str = "RULE-BNSS-479-THRESHOLD-V1"
        self._register_canonical_rules()

    def _register_canonical_rules(self):
        """Register initial legally-validated canonical rules."""
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
                "reviewed_by": "Authorized Legal Aid Counsel / NALSA Panel",
                "review_date": "2024-07-01",
                "status": "VALIDATED",
            },
            approval_metadata={
                "approved_by": "Supervising Legal Officer / DLSA Secretary",
                "approval_role": Role.SUPERVISING_LEGAL_OFFICER.value,
                "approval_timestamp": "2024-07-01T00:00:00Z",
            },
            created_at="2024-07-01T00:00:00Z",
            updated_at="2024-07-01T00:00:00Z",
        )
        self.register_rule(bnss_rule)

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
            applicability_conditions={"applicable_statute": "CRPC_1973"},
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
            legal_review_metadata={"status": "HISTORICAL_REGIME"},
            approval_metadata={"approved_by": "Supervising Legal Officer"},
            created_at="2005-06-23T00:00:00Z",
            updated_at="2024-07-01T00:00:00Z",
        )
        self.register_rule(crpc_rule)

    def register_rule(self, rule: LegalRuleDefinition):
        """Register or update a rule and save its immutable version snapshot."""
        self._rules[rule.rule_id] = rule
        if rule.rule_id not in self._versions:
            self._versions[rule.rule_id] = []
        self._versions[rule.rule_id].append({
            "version_tag": rule.rule_version,
            "rule_snapshot": rule.dict(),
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

    def get_rule(self, rule_id: Optional[str] = None) -> LegalRuleDefinition:
        rid = rule_id or self._active_rule_id
        if rid not in self._rules:
            # Fallback by rule_version
            for r in self._rules.values():
                if r.rule_version == rule_id:
                    return r
            return self._rules.get(self._active_rule_id)
        return self._rules[rid]

    def list_rules(self) -> List[Dict[str, Any]]:
        return [r.dict() for r in self._rules.values()]

    def get_rule_versions(self, rule_id: str) -> List[Dict[str, Any]]:
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
                "approved_by": getattr(actor, "full_name", None) or actor.id,
                "approval_role": actor.role.value,
                "approval_timestamp": updated_rule.updated_at,
                "approval_notes": notes,
            }
        elif target_state == RuleLifecycleState.LEGAL_REVIEW:
            updated_rule.legal_review_metadata = {
                "reviewed_by": getattr(actor, "full_name", None) or actor.id,
                "review_role": actor.role.value,
                "review_timestamp": updated_rule.updated_at,
                "review_notes": notes,
            }

        self.register_rule(updated_rule)
        return updated_rule


RULE_REGISTRY = LegalRuleRegistry()
