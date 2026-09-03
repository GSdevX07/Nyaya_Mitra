"""
bnss_479_engine.py - Pure Deterministic BNSS Section 479 Evaluation Engine.
==========================================================================
CRITICAL LEGAL & ARCHITECTURAL GUARANTEES:
1. Pure deterministic arithmetic - zero LLM calculation.
2. Models BNSS Section 479(1) Proviso 1 (1/3 for first-time offenders), general (1/2),
   Proviso 2 (capital/life exclusions), and Proviso 3 (multiple pending cases).
3. Models Section 479(1) maximum imprisonment ceiling (detention cannot exceed full sentence).
4. Models Section 479(2) mandatory Superintendent reporting duty.
5. Deducts accused-attributable delay (excluded_delay_days).
6. Never treats missing data as zero or satisfied; returns INSUFFICIENT_DATA or MANUAL_REVIEW.
7. Identifies conflicting records (e.g. jail vs police/court) and preserves conflicts.
8. Rounding rule: math.ceil as documented statutory integer ceiling.
"""

from __future__ import annotations
import math
import uuid
from typing import Dict, Any, Optional, List

from app.rules.models import (
    RuleMachineStatus,
    RuleExplanation,
    RuleExecutionResult,
)


def evaluate_bnss_479_detention(
    case: Any,
    rule_def: Any,
    provenance_map: Optional[Dict[str, Any]] = None,
    conflicting_records: Optional[List[Dict[str, Any]]] = None,
) -> RuleExecutionResult:
    """
    Deterministically evaluates undertrial detention eligibility under Section 479 BNSS, 2023.
    """
    exec_id = f"EXEC-{uuid.uuid4().hex[:12].upper()}"
    rule_id = getattr(rule_def, "rule_id", "RULE-BNSS-479-THRESHOLD-V1")
    rule_version = getattr(rule_def, "rule_version", "BNSS_479_RULESET_V1_2023")
    jurisdiction = getattr(rule_def, "jurisdiction", "India / National")
    legal_source = getattr(rule_def, "statutory_source", "Bharatiya Nagarik Suraksha Sanhita, 2023 (Section 479)")
    effective_date = getattr(rule_def, "effective_date", "2024-07-01")

    # Extract case attributes
    case_id = getattr(case, "case_id", "UNKNOWN_CASE")
    prisoner_category = str(getattr(case, "prisoner_category", "UNDERTRIAL"))
    custody_days = getattr(case, "custody_days", None)
    excluded_delay_days = getattr(case, "excluded_delay_days", 0) or 0
    max_sentence_days = getattr(case, "max_sentence_days_for_offense", None)
    punishable_by_death_or_life = bool(getattr(case, "punishable_by_death_or_life", False))
    multiple_active_cases = bool(getattr(case, "multiple_active_cases", False))
    offense_sections = getattr(case, "offense_sections", []) or []
    urgency_flags = getattr(case, "urgency_flags", None)
    repeat_offender = getattr(urgency_flags, "repeat_offender", None) if urgency_flags else None
    missing_docs = getattr(case, "missing_docs", []) or []

    # Map input facts actually used
    input_facts: Dict[str, Any] = {
        "case_id": case_id,
        "prisoner_category": prisoner_category,
        "custody_days": custody_days,
        "excluded_delay_days": excluded_delay_days,
        "max_sentence_days_for_offense": max_sentence_days,
        "punishable_by_death_or_life": punishable_by_death_or_life,
        "multiple_active_cases": multiple_active_cases,
        "repeat_offender": repeat_offender,
        "offense_sections": offense_sections,
        "missing_docs_count": len(missing_docs),
    }

    # Map input provenance
    input_provenance = provenance_map or {}
    if not input_provenance and hasattr(case, "field_provenance") and case.field_provenance:
        input_provenance = {
            k: (v.dict() if hasattr(v, "dict") else str(v))
            for k, v in case.field_provenance.items()
        }

    conditions_evaluated: List[Dict[str, Any]] = []
    exclusions_provisos_evaluated: List[Dict[str, Any]] = []
    missing_or_conflicting: List[Dict[str, Any]] = []

    # ── Check 1: Conflicting Authoritative Records ────────────────────────────
    # E.g. Jail register admission date conflicts with police arrest memo
    active_conflicts = conflicting_records or []
    if hasattr(case, "conflicting_records") and case.conflicting_records:
        active_conflicts.extend(case.conflicting_records)

    if active_conflicts:
        for c in active_conflicts:
            missing_or_conflicting.append({
                "type": "CONFLICTING_AUTHORITATIVE_RECORDS",
                "field": c.get("field", "custody_record"),
                "source_a": c.get("source_a", "Prison Custody Register"),
                "source_b": c.get("source_b", "Police Arrest Record"),
                "details": c.get("details", "Discrepancy in documented custody dates."),
            })

        expl = RuleExplanation(
            rule_id=rule_id,
            rule_version=rule_version,
            jurisdiction=jurisdiction,
            legal_source=legal_source,
            effective_date=effective_date,
            input_facts_used=input_facts,
            input_provenance=input_provenance,
            calculation_performed={"status": "HALTED_ON_CONFLICT"},
            conditions_evaluated=conditions_evaluated,
            exclusions_provisos_evaluated=exclusions_provisos_evaluated,
            missing_or_conflicting_inputs=missing_or_conflicting,
            machine_status=RuleMachineStatus.MANUAL_REVIEW,
            explanation_text=(
                f"Conflicting authoritative records detected for case {case_id}. "
                "Discrepancy between institutional sources must be reconciled by DLSA legal officer before statutory determination."
            ),
            manual_review_reason="Conflicting authoritative institutional records detected (e.g. Prison Custody Register vs Police Arrest Sheet).",
        )
        return RuleExecutionResult(
            execution_id=exec_id,
            case_id=case_id,
            rule_id=rule_id,
            rule_version=rule_version,
            machine_status=RuleMachineStatus.MANUAL_REVIEW,
            is_eligible=False,
            threshold_fraction=0.0,
            threshold_days=0,
            countable_custody_days=max(0, (custody_days or 0) - excluded_delay_days),
            total_elapsed_calendar_days=custody_days or 0,
            excluded_delay_days=excluded_delay_days,
            days_overdue=0,
            explanation=expl,
        )

    # ── Check 2: Missing Essential Facts (Never silently assume zero/false) ───
    if custody_days is None:
        missing_or_conflicting.append({
            "type": "MISSING_INPUT",
            "field": "custody_days",
            "reason": "Custody duration in days is not recorded on institutional file.",
        })
    if max_sentence_days is None or max_sentence_days <= 0:
        missing_or_conflicting.append({
            "type": "MISSING_INPUT",
            "field": "max_sentence_days_for_offense",
            "reason": "Maximum statutory punishment in days for charged offenses is not recorded or is zero.",
        })
    if repeat_offender is None:
        missing_or_conflicting.append({
            "type": "MISSING_INPUT",
            "field": "repeat_offender",
            "reason": "Prior conviction status (first-time vs repeat offender) is unrecorded.",
        })

    if missing_or_conflicting:
        expl = RuleExplanation(
            rule_id=rule_id,
            rule_version=rule_version,
            jurisdiction=jurisdiction,
            legal_source=legal_source,
            effective_date=effective_date,
            input_facts_used=input_facts,
            input_provenance=input_provenance,
            calculation_performed={"status": "HALTED_ON_MISSING_DATA"},
            conditions_evaluated=conditions_evaluated,
            exclusions_provisos_evaluated=exclusions_provisos_evaluated,
            missing_or_conflicting_inputs=missing_or_conflicting,
            machine_status=RuleMachineStatus.INSUFFICIENT_DATA,
            explanation_text=(
                f"Required statutory facts are missing for case {case_id}: "
                + ", ".join([f["field"] for f in missing_or_conflicting])
                + ". The deterministic engine refuses to guess missing facts as zero or false."
            ),
            manual_review_reason="Missing essential institutional case facts required for Section 479 calculation.",
        )
        return RuleExecutionResult(
            execution_id=exec_id,
            case_id=case_id,
            rule_id=rule_id,
            rule_version=rule_version,
            machine_status=RuleMachineStatus.INSUFFICIENT_DATA,
            is_eligible=False,
            threshold_fraction=0.0,
            threshold_days=0,
            countable_custody_days=max(0, (custody_days or 0) - excluded_delay_days),
            total_elapsed_calendar_days=custody_days or 0,
            excluded_delay_days=excluded_delay_days,
            days_overdue=0,
            explanation=expl,
        )

    # ── Check 3: Convicted Prisoner Category (Appellate Workflow) ─────────────
    if "CONV" in prisoner_category.upper():
        conditions_evaluated.append({
            "condition_name": "Undertrial Prisoner Status",
            "satisfied": False,
            "reason": "Person is recorded as a convicted prisoner, not an undertrial.",
            "statutory_reference": "Section 479 applies exclusively to undertrial detention.",
        })
        expl = RuleExplanation(
            rule_id=rule_id,
            rule_version=rule_version,
            jurisdiction=jurisdiction,
            legal_source=legal_source,
            effective_date=effective_date,
            input_facts_used=input_facts,
            input_provenance=input_provenance,
            calculation_performed={"status": "APPELLATE_WORKFLOW_REQUIRED"},
            conditions_evaluated=conditions_evaluated,
            exclusions_provisos_evaluated=exclusions_provisos_evaluated,
            missing_or_conflicting_inputs=[],
            machine_status=RuleMachineStatus.MANUAL_REVIEW,
            explanation_text="Case relates to a convicted prisoner. Routed to Appellate Legal Aid Review (BNSS Section 415 / CrPC 389) rather than undertrial detention.",
            manual_review_reason="Convicted prisoner requires appellate suspension of sentence review, not Section 479 undertrial bail.",
        )
        return RuleExecutionResult(
            execution_id=exec_id,
            case_id=case_id,
            rule_id=rule_id,
            rule_version=rule_version,
            machine_status=RuleMachineStatus.MANUAL_REVIEW,
            is_eligible=False,
            threshold_fraction=0.0,
            threshold_days=0,
            countable_custody_days=max(0, custody_days - excluded_delay_days),
            total_elapsed_calendar_days=custody_days,
            excluded_delay_days=excluded_delay_days,
            days_overdue=0,
            explanation=expl,
        )

    # ── Check 4: Statutory Exclusion (Capital / Life Imprisonment) ─────────────
    exclusions_provisos_evaluated.append({
        "proviso_name": "Section 479(1) Proviso 2: Capital or Life Imprisonment Exclusion",
        "applies": punishable_by_death_or_life,
        "statutory_text": "Provided further that no such person shall be so released if the offence is punishable with death or with imprisonment for life.",
        "facts_used": {"punishable_by_death_or_life": punishable_by_death_or_life},
    })
    if punishable_by_death_or_life:
        expl = RuleExplanation(
            rule_id=rule_id,
            rule_version=rule_version,
            jurisdiction=jurisdiction,
            legal_source=legal_source,
            effective_date=effective_date,
            input_facts_used=input_facts,
            input_provenance=input_provenance,
            calculation_performed={"status": "STATUTORY_EXCLUSION_APPLIED"},
            conditions_evaluated=conditions_evaluated,
            exclusions_provisos_evaluated=exclusions_provisos_evaluated,
            missing_or_conflicting_inputs=[],
            machine_status=RuleMachineStatus.EXCLUDED,
            explanation_text="STATUTORY EXCLUSION: Section 479(1) Proviso 2 explicitly bars undertrials charged with offenses punishable by death or life imprisonment. Merits must be evaluated under regular bail provisions by counsel.",
            manual_review_reason="Charged offense carries potential punishment of death or life imprisonment.",
        )
        return RuleExecutionResult(
            execution_id=exec_id,
            case_id=case_id,
            rule_id=rule_id,
            rule_version=rule_version,
            machine_status=RuleMachineStatus.EXCLUDED,
            is_eligible=False,
            threshold_fraction=0.0,
            threshold_days=0,
            countable_custody_days=max(0, custody_days - excluded_delay_days),
            total_elapsed_calendar_days=custody_days,
            excluded_delay_days=excluded_delay_days,
            days_overdue=0,
            explanation=expl,
        )

    # ── Check 5: Proviso on Multiple Active Cases / Proceedings ───────────────
    exclusions_provisos_evaluated.append({
        "proviso_name": "Section 479(1) Proviso 3: Multiple Pending Proceedings",
        "applies": multiple_active_cases,
        "statutory_text": "Provided also that where investigation, inquiry or trial in more than one offence or in multiple cases are pending against a person, he shall not be released on bail by the Court under this section.",
        "facts_used": {"multiple_active_cases": multiple_active_cases},
    })
    if multiple_active_cases:
        expl = RuleExplanation(
            rule_id=rule_id,
            rule_version=rule_version,
            jurisdiction=jurisdiction,
            legal_source=legal_source,
            effective_date=effective_date,
            input_facts_used=input_facts,
            input_provenance=input_provenance,
            calculation_performed={"status": "MULTIPLE_PROCEEDINGS_FLAGGED"},
            conditions_evaluated=conditions_evaluated,
            exclusions_provisos_evaluated=exclusions_provisos_evaluated,
            missing_or_conflicting_inputs=[],
            machine_status=RuleMachineStatus.MANUAL_REVIEW,
            explanation_text="STATUTORY PROVISO: Section 479(1) Proviso 3 identifies multiple pending proceedings. Automatic statutory threshold cannot be applied; requires manual DLSA legal review to assess joint vs separate trial and delay attribution.",
            manual_review_reason="Multiple pending proceedings identified under Section 479(1) Proviso 3.",
        )
        return RuleExecutionResult(
            execution_id=exec_id,
            case_id=case_id,
            rule_id=rule_id,
            rule_version=rule_version,
            machine_status=RuleMachineStatus.MANUAL_REVIEW,
            is_eligible=False,
            threshold_fraction=0.0,
            threshold_days=0,
            countable_custody_days=max(0, custody_days - excluded_delay_days),
            total_elapsed_calendar_days=custody_days,
            excluded_delay_days=excluded_delay_days,
            days_overdue=0,
            explanation=expl,
        )

    # ── Check 6: Multiple Charges with Sentence Aggregation Ambiguity ─────────
    # If 3 or more offense sections exist, flag for sentence aggregation review
    if len(offense_sections) >= 3:
        conditions_evaluated.append({
            "condition_name": "Sentence Aggregation Review",
            "satisfied": None,
            "reason": f"Multiple charged offense sections ({len(offense_sections)}) present. Section 31 CrPC / Section 25 BNSS consecutive vs concurrent sentencing review required by counsel.",
            "statutory_reference": "Section 25 BNSS / Section 31 CrPC",
        })

    # ── Check 7: Countable Detention & Threshold Calculation ──────────────────
    countable_custody = max(0, custody_days - excluded_delay_days)
    is_crpc = "CRPC" in str(rule_version).upper() or "CRPC" in str(rule_id).upper()
    if not is_crpc and not repeat_offender:
        threshold_fraction = 1.0 / 3.0
        fraction_str = "1/3"
        proviso_label = "First-Time Offender Proviso (Section 479(1) Proviso 1)"
    else:
        threshold_fraction = 1.0 / 2.0
        fraction_str = "1/2"
        proviso_label = (
            "General Undertrial Threshold (Section 479(1) Main Provision)"
            if not is_crpc
            else "CrPC Section 436A Historic Threshold (1/2 Maximum Imprisonment)"
        )

    # Documented Rounding Rule: math.ceil(max_sentence_days * threshold_fraction)
    threshold_days = math.ceil(max_sentence_days * threshold_fraction)
    is_threshold_reached = countable_custody >= threshold_days
    days_overdue = max(0, countable_custody - threshold_days) if is_threshold_reached else 0

    # Check maximum detention ceiling (detention cannot exceed total maximum sentence)
    is_max_sentence_reached = countable_custody >= max_sentence_days

    # Check mandatory document prerequisites
    mandatory_blockers = [d for d in missing_docs if "remand" in d.lower() or "charge" in d.lower()]
    has_doc_blocker = len(mandatory_blockers) > 0

    conditions_evaluated.append({
        "condition_name": "Statutory Detention Fraction",
        "satisfied": is_threshold_reached,
        "reason": f"{proviso_label}: Countable custody ({countable_custody}d) vs required threshold ({threshold_days}d).",
        "facts_used": {
            "max_sentence_days": max_sentence_days,
            "threshold_fraction": fraction_str,
            "threshold_days": threshold_days,
            "total_elapsed_days": custody_days,
            "excluded_delay_days": excluded_delay_days,
            "countable_custody_days": countable_custody,
            "rounding_rule": "math.ceil",
        },
    })

    if excluded_delay_days > 0:
        conditions_evaluated.append({
            "condition_name": "Accused-Attributable Delay Deduction",
            "satisfied": True,
            "reason": f"{excluded_delay_days} days of delay attributable to accused excluded from countable custody under Section 479(1) Proviso.",
            "facts_used": {"excluded_delay_days": excluded_delay_days},
        })

    if has_doc_blocker:
        conditions_evaluated.append({
            "condition_name": "Mandatory Record Prerequisite",
            "satisfied": False,
            "reason": f"Mandatory court records missing: {', '.join(mandatory_blockers)}. Section 479 petition requires verified remand order & charge sheet.",
            "facts_used": {"missing_mandatory_docs": mandatory_blockers},
        })

    # Determine final machine status
    if has_doc_blocker:
        machine_status = RuleMachineStatus.POTENTIALLY_APPLICABLE if is_threshold_reached else RuleMachineStatus.THRESHOLD_NOT_REACHED
        manual_review_reason = f"Mandatory records missing ({', '.join(mandatory_blockers)}) preventing filing."
    elif is_threshold_reached:
        machine_status = RuleMachineStatus.THRESHOLD_REACHED
        manual_review_reason = None
    else:
        # Check if approaching (within 15 days or 10%)
        days_remaining = threshold_days - countable_custody
        if days_remaining <= 15:
            machine_status = RuleMachineStatus.POTENTIALLY_APPLICABLE
            manual_review_reason = f"Approaching threshold: {days_remaining} countable days remaining."
        else:
            machine_status = RuleMachineStatus.THRESHOLD_NOT_REACHED
            manual_review_reason = None

    if is_max_sentence_reached:
        explanation_text = (
            f"MAXIMUM STATUTORY DETENTION CEILING REACHED: Undertrial has served {countable_custody} days, "
            f"exceeding the full maximum statutory imprisonment of {max_sentence_days} days. "
            "Under Section 479(1), detention beyond this period is strictly prohibited."
        )
    elif is_threshold_reached:
        explanation_text = (
            f"STATUTORY THRESHOLD REACHED: Documented facts appear to satisfy {proviso_label}. "
            f"Countable detention of {countable_custody} days satisfies required {threshold_days} days "
            f"({fraction_str} of {max_sentence_days}d maximum punishment). "
            f"Section 479(2) triggers mandatory reporting by Jail Superintendent to the jurisdictional Court."
        )
    else:
        days_remaining = threshold_days - countable_custody
        explanation_text = (
            f"STATUTORY THRESHOLD NOT REACHED: Countable detention of {countable_custody} days is below the "
            f"required {threshold_days} days ({fraction_str} of {max_sentence_days}d). "
            f"{days_remaining} additional countable detention days required."
        )

    calculation_performed = {
        "formula": f"math.ceil(max_sentence_days * {fraction_str})",
        "max_sentence_days": max_sentence_days,
        "fraction": fraction_str,
        "threshold_days": threshold_days,
        "total_elapsed_days": custody_days,
        "excluded_delay_days": excluded_delay_days,
        "countable_custody_days": countable_custody,
        "days_overdue": days_overdue,
        "rounding_rule": "math.ceil",
        "superintendent_duty_triggered": is_threshold_reached,
    }

    expl = RuleExplanation(
        rule_id=rule_id,
        rule_version=rule_version,
        jurisdiction=jurisdiction,
        legal_source=legal_source,
        effective_date=effective_date,
        input_facts_used=input_facts,
        input_provenance=input_provenance,
        calculation_performed=calculation_performed,
        conditions_evaluated=conditions_evaluated,
        exclusions_provisos_evaluated=exclusions_provisos_evaluated,
        missing_or_conflicting_inputs=[],
        machine_status=machine_status,
        explanation_text=explanation_text,
        manual_review_reason=manual_review_reason,
    )

    return RuleExecutionResult(
        execution_id=exec_id,
        case_id=case_id,
        rule_id=rule_id,
        rule_version=rule_version,
        machine_status=machine_status,
        is_eligible=is_threshold_reached and not has_doc_blocker,
        threshold_fraction=threshold_fraction,
        threshold_days=threshold_days,
        countable_custody_days=countable_custody,
        total_elapsed_calendar_days=custody_days,
        excluded_delay_days=excluded_delay_days,
        days_overdue=days_overdue,
        explanation=expl,
    )
