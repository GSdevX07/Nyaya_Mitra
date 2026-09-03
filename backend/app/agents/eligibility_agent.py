"""
eligibility_agent.py - Deterministic Versioned Section 479 BNSS Rule Engine.

╔══════════════════════════════════════════════════════════════════════════╗
║  CRITICAL LEGAL & ARCHITECTURAL PRINCIPLES                              ║
║  1. Pure deterministic arithmetic - NEVER an LLM decision.               ║
║  2. Versioned Rule System: BNSS_479_RULESET_V1_2023                      ║
║  3. Distinguishes total elapsed calendar days from countable custody      ║
║     (accounting for accused-attributable delay periods).                ║
║  4. Checks statutory exclusions (death/life imprisonment, multiple       ║
║     pending proceedings condition).                                      ║
║  5. Outputs an eligibility signal for human legal review, NOT an         ║
║     automatic release entitlement or judicial prediction.                ║
║  6. Documented Rounding Rule: Computes threshold precisely according to   ║
║     the validated statutory interpretation (using math.ceil as the       ║
║     documented threshold integer rule).                                  ║
║  7. Legal validation requirement: Subject to validation by counsel.     ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
import math
from typing import Dict, Any

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from app.models.schemas import CaseRecord


@dataclass
class StatutoryRuleConfig:
    version_id: str
    statute_name: str
    section: str
    effective_date: str
    description: str
    first_time_offender_fraction: float
    general_undertrial_fraction: float
    excludes_capital_or_life: bool = True
    excludes_multiple_proceedings: bool = True
    rounding_rule: str = "math.ceil"
    is_active: bool = True


class StatutoryRuleRegistry:
    """Versioned registry for statutory bail eligibility rules."""

    def __init__(self):
        self._rules: Dict[str, StatutoryRuleConfig] = {}
        self._active_version: str = "BNSS_479_RULESET_V1_2023"
        self._register_default_rules()

    def _register_default_rules(self):
        self.register_rule(StatutoryRuleConfig(
            version_id="BNSS_479_RULESET_V1_2023",
            statute_name="Bharatiya Nagarik Suraksha Sanhita, 2023",
            section="Section 479",
            effective_date="2024-07-01",
            description="First-time undertrials eligible at 1/3 maximum imprisonment; others at 1/2 maximum imprisonment.",
            first_time_offender_fraction=1 / 3,
            general_undertrial_fraction=1 / 2,
            excludes_capital_or_life=True,
            excludes_multiple_proceedings=True,
            rounding_rule="math.ceil",
            is_active=True,
        ))
        self.register_rule(StatutoryRuleConfig(
            version_id="CRPC_436A_RULESET_V1_1973",
            statute_name="Code of Criminal Procedure, 1973",
            section="Section 436A",
            effective_date="2005-06-23",
            description="Historic regime: Undertrials eligible at 1/2 maximum imprisonment without 1/3 first-time offender proviso.",
            first_time_offender_fraction=1 / 2,
            general_undertrial_fraction=1 / 2,
            excludes_capital_or_life=True,
            excludes_multiple_proceedings=False,
            rounding_rule="math.ceil",
            is_active=False,
        ))

    def register_rule(self, config: StatutoryRuleConfig):
        self._rules[config.version_id] = config

    def get_rule(self, version_id: Optional[str] = None) -> StatutoryRuleConfig:
        vid = version_id or self._active_version
        if vid not in self._rules:
            # Fallback to active version if unknown
            return self._rules.get(self._active_version) or list(self._rules.values())[0]
        return self._rules[vid]

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "version_id": r.version_id,
                "statute_name": r.statute_name,
                "section": r.section,
                "effective_date": r.effective_date,
                "description": r.description,
                "first_time_offender_fraction": r.first_time_offender_fraction,
                "general_undertrial_fraction": r.general_undertrial_fraction,
                "rounding_rule": r.rounding_rule,
                "is_active": (r.version_id == self._active_version),
            }
            for r in self._rules.values()
        ]

    def set_active_version(self, version_id: str):
        if version_id not in self._rules:
            raise KeyError(f"Cannot activate unregistered rule version: {version_id}")
        self._active_version = version_id


RULE_REGISTRY = StatutoryRuleRegistry()
RULE_ENGINE_VERSION = RULE_REGISTRY._active_version


def evaluate_eligibility(case: CaseRecord, rule_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluate whether documented case facts appear to satisfy statutory criteria
    based on the configured versioned rule from the statutory registry.
    """
    rule = RULE_REGISTRY.get_rule(rule_version)
    current_rule_version = rule.version_id
    total_elapsed_days = case.custody_days
    excluded_delay_days = getattr(case, "excluded_delay_days", 0)
    countable_custody_days = max(0, total_elapsed_days - excluded_delay_days)

    exceptions_checked = {
        "capital_or_life_offence_exclusion": case.punishable_by_death_or_life,
        "multiple_pending_proceedings_condition": case.multiple_active_cases,
        "repeat_conviction_status": case.urgency_flags.repeat_offender,
        "accused_attributable_delay_identified": excluded_delay_days > 0,
    }

    # ── 1. Check Statutory Exclusion: Death / Life Imprisonment ──────────────
    if case.punishable_by_death_or_life:
        return {
            "case_id": case.case_id,
            "rule_version": current_rule_version,
            "eligible": False,
            "human_review_required": True,
            "threshold_fraction": 0.0,
            "total_elapsed_calendar_days": total_elapsed_days,
            "excluded_delay_days": excluded_delay_days,
            "countable_custody_days": countable_custody_days,
            "required_custody_days": 0,
            "days_overdue": 0,
            "exceptions_checked": exceptions_checked,
            "legal_basis": f"STATUTORY_EXCLUSION: {rule.statute_name} {rule.section} explicitly excludes offences for which punishment of death or life imprisonment is specified by law.",
            "statutory_signal": "Statutory exclusion applies. Merits of regular bail must be evaluated by counsel under general bail provisions.",
            "disclaimer": f"The complete {rule.section} rule interpretation must be validated against the authoritative statutory text and reviewed by qualified legal counsel.",
        }

    # ── 2. Check Statutory Condition: Multiple Pending Proceedings ──────────
    if case.multiple_active_cases and rule.excludes_multiple_proceedings:
        return {
            "case_id": case.case_id,
            "rule_version": current_rule_version,
            "eligible": False,
            "human_review_required": True,
            "threshold_fraction": 0.0,
            "total_elapsed_calendar_days": total_elapsed_days,
            "excluded_delay_days": excluded_delay_days,
            "countable_custody_days": countable_custody_days,
            "required_custody_days": 0,
            "days_overdue": 0,
            "exceptions_checked": exceptions_checked,
            "legal_basis": f"STATUTORY_CONDITION: {rule.statute_name} {rule.section} contains specific conditions where investigation/trial in more than one offence or multiple cases is pending.",
            "statutory_signal": "Multiple active cases identified. Requires manual legal review by DLSA counsel to determine applicability of statutory provisos.",
            "disclaimer": f"The complete {rule.section} rule interpretation must be validated against the authoritative statutory text and reviewed by qualified legal counsel.",
        }

    # ── 3. Determine Applicable Statutory Threshold Fraction ─────────────────
    is_repeat = case.urgency_flags.repeat_offender
    if not is_repeat:
        threshold_fraction = rule.first_time_offender_fraction
        category_label = f"First-Time Offender Proviso (at least {threshold_fraction:.2f} of maximum sentence)"
    else:
        threshold_fraction = rule.general_undertrial_fraction
        category_label = f"General Undertrial Threshold (at least {threshold_fraction:.2f} of maximum sentence)"

    # ── 4. Compute Required Custody Days using Documented Rounding Rule ──────
    required_days = math.ceil(case.max_sentence_days_for_offense * threshold_fraction)

    # ── 5. Evaluate Countable Custody against Threshold ──────────────────────
    is_eligible = countable_custody_days >= required_days
    days_overdue = max(0, countable_custody_days - required_days) if is_eligible else 0

    if is_eligible:
        statutory_signal = (
            f"The documented facts appear to satisfy the applicable {rule.section} statutory criteria, "
            "subject to human legal review."
        )
        legal_basis = f"{rule.section} {rule.statute_name} — {category_label}. Countable detention ({countable_custody_days} days) satisfies required threshold ({required_days} days)."
    else:
        remaining_days = required_days - countable_custody_days
        statutory_signal = (
            f"Statutory detention threshold not yet reached. {remaining_days} additional countable days "
            f"required to reach the {category_label} threshold."
        )
        legal_basis = f"{rule.section} {rule.statute_name} — {category_label}. Countable custody ({countable_custody_days}/{required_days} days)."

    # ── 6. Build Deterministic Result ─────────────────────────────────────────
    return {
        "case_id": case.case_id,
        "rule_version": current_rule_version,
        "eligible": is_eligible,
        "human_review_required": not is_eligible or excluded_delay_days > 0,
        "threshold_fraction": threshold_fraction,
        "category_label": category_label,
        "total_elapsed_calendar_days": total_elapsed_days,
        "excluded_delay_days": excluded_delay_days,
        "countable_custody_days": countable_custody_days,
        "required_custody_days": required_days,
        "days_overdue": days_overdue,
        "exceptions_checked": exceptions_checked,
        "legal_basis": legal_basis,
        "statutory_signal": statutory_signal,
        "disclaimer": "The complete Section 479 rule interpretation must be validated against the authoritative statutory text and reviewed by qualified legal counsel.",
    }
