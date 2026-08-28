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

from app.models.schemas import CaseRecord


RULE_ENGINE_VERSION = "BNSS_479_RULESET_V1_2023"

_FIRST_TIME_FRACTION: float = 1 / 3   # Section 479(1) Proviso: never previously convicted
_GENERAL_UNDERTRIAL_FRACTION: float = 1 / 2  # Section 479(1) General threshold


def evaluate_eligibility(case: CaseRecord) -> Dict[str, Any]:
    """
    Evaluate whether documented case facts appear to satisfy Section 479 BNSS
    statutory criteria based on deterministic statutory rules.

    The result is an eligibility signal for human legal review, not an automatic
    release entitlement.
    """
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
            "rule_version": RULE_ENGINE_VERSION,
            "eligible": False,
            "human_review_required": True,
            "threshold_fraction": 0.0,
            "total_elapsed_calendar_days": total_elapsed_days,
            "excluded_delay_days": excluded_delay_days,
            "countable_custody_days": countable_custody_days,
            "required_custody_days": 0,
            "days_overdue": 0,
            "exceptions_checked": exceptions_checked,
            "legal_basis": "STATUTORY_EXCLUSION: Section 479 BNSS explicitly excludes offences for which punishment of death or life imprisonment is specified by law.",
            "statutory_signal": "Statutory exclusion applies. Merits of regular bail must be evaluated by counsel under general bail provisions.",
            "disclaimer": "The complete Section 479 rule interpretation must be validated against the authoritative statutory text and reviewed by qualified legal counsel.",
        }

    # ── 2. Check Statutory Condition: Multiple Pending Proceedings ──────────
    if case.multiple_active_cases:
        return {
            "case_id": case.case_id,
            "rule_version": RULE_ENGINE_VERSION,
            "eligible": False,
            "human_review_required": True,
            "threshold_fraction": 0.0,
            "total_elapsed_calendar_days": total_elapsed_days,
            "excluded_delay_days": excluded_delay_days,
            "countable_custody_days": countable_custody_days,
            "required_custody_days": 0,
            "days_overdue": 0,
            "exceptions_checked": exceptions_checked,
            "legal_basis": "STATUTORY_CONDITION: Section 479 BNSS contains specific conditions where investigation/trial in more than one offence or multiple cases is pending.",
            "statutory_signal": "Multiple active cases identified. Requires manual legal review by DLSA counsel to determine applicability of Section 479 provisos.",
            "disclaimer": "The complete Section 479 rule interpretation must be validated against the authoritative statutory text and reviewed by qualified legal counsel.",
        }

    # ── 3. Determine Applicable Statutory Threshold Fraction ─────────────────
    is_repeat = case.urgency_flags.repeat_offender
    if not is_repeat:
        threshold_fraction = _FIRST_TIME_FRACTION
        category_label = "First-Time Offender Proviso (at least 1/3 of maximum sentence)"
    else:
        threshold_fraction = _GENERAL_UNDERTRIAL_FRACTION
        category_label = "General Undertrial Threshold (at least 1/2 of maximum sentence)"

    # ── 4. Compute Required Custody Days using Documented Rounding Rule ──────
    # Documented Rounding Rule: Statutory period calculated precisely; where a fractional
    # day occurs, the integer threshold uses math.ceil as approved during legal validation.
    required_days = math.ceil(case.max_sentence_days_for_offense * threshold_fraction)

    # ── 5. Evaluate Countable Custody against Threshold ──────────────────────
    is_eligible = countable_custody_days >= required_days
    days_overdue = max(0, countable_custody_days - required_days) if is_eligible else 0

    if is_eligible:
        statutory_signal = (
            "The documented facts appear to satisfy the applicable Section 479 statutory criteria, "
            "subject to human legal review."
        )
        legal_basis = f"Section 479 BNSS — {category_label}. Countable detention ({countable_custody_days} days) satisfies required threshold ({required_days} days)."
    else:
        remaining_days = required_days - countable_custody_days
        statutory_signal = (
            f"Statutory detention threshold not yet reached. {remaining_days} additional countable days "
            f"required to reach the {category_label} threshold."
        )
        legal_basis = f"Section 479 BNSS — {category_label}. Countable custody ({countable_custody_days}/{required_days} days)."

    # ── 6. Build Deterministic Result ─────────────────────────────────────────
    return {
        "case_id": case.case_id,
        "rule_version": RULE_ENGINE_VERSION,
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
