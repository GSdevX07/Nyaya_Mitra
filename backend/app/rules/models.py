"""
models.py - Canonical Pydantic Models for Deterministic Rules Engine.
====================================================================
Formal enums, condition result structures, structured explanation object,
and rule lifecycle definition schemas.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class RuleCategory(str, Enum):
    """Extensible statutory and operational rule categories."""
    CUSTODY_DURATION_THRESHOLD = "CUSTODY_DURATION_THRESHOLD"
    APPLICABLE_EXCLUSIONS = "APPLICABLE_EXCLUSIONS"
    MULTIPLE_ACTIVE_CASES = "MULTIPLE_ACTIVE_CASES"
    SENTENCE_AGGREGATION_REVIEW = "SENTENCE_AGGREGATION_REVIEW"
    DOCUMENT_PREREQUISITES = "DOCUMENT_PREREQUISITES"
    APPEAL_RELATED_WORKFLOWS = "APPEAL_RELATED_WORKFLOWS"
    HEARING_DEADLINES = "HEARING_DEADLINES"
    LEGAL_AID_OPERATIONAL_DEADLINES = "LEGAL_AID_OPERATIONAL_DEADLINES"


class RuleLifecycleState(str, Enum):
    """Formal governance lifecycle states for legal rules."""
    DRAFT = "DRAFT"
    LEGAL_REVIEW = "LEGAL_REVIEW"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class RuleMachineStatus(str, Enum):
    """
    Standardized machine calculation statuses.
    Represents a statutory eligibility/attention signal for legal review,
    NEVER an autonomous judicial determination or release grant.
    """
    THRESHOLD_NOT_REACHED = "THRESHOLD_NOT_REACHED"
    THRESHOLD_REACHED = "THRESHOLD_REACHED"
    POTENTIALLY_APPLICABLE = "POTENTIALLY_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    EXCLUDED = "EXCLUDED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ConditionCheckResult(BaseModel):
    """Individual statutory condition evaluation result."""
    condition_name: str
    satisfied: Optional[bool]
    reason: str
    facts_used: Dict[str, Any] = Field(default_factory=dict)
    proviso_reference: Optional[str] = None


class ExclusionCheckResult(BaseModel):
    """Statutory exclusion or proviso check result."""
    exclusion_name: str
    applies: bool
    statutory_proviso: str
    facts_used: Dict[str, Any] = Field(default_factory=dict)
    notes: str


class RuleExplanation(BaseModel):
    """
    Comprehensive structured explanation object returned with every rule evaluation.
    Enables complete machine interpretability and historical auditability.
    """
    rule_id: str
    rule_version: str
    jurisdiction: str
    legal_source: str
    effective_date: str
    input_facts_used: Dict[str, Any]
    input_provenance: Dict[str, Any] = Field(default_factory=dict)
    calculation_performed: Dict[str, Any]
    conditions_evaluated: List[Dict[str, Any]]
    exclusions_provisos_evaluated: List[Dict[str, Any]]
    missing_or_conflicting_inputs: List[Dict[str, Any]] = Field(default_factory=list)
    machine_status: RuleMachineStatus
    explanation_text: str
    manual_review_reason: Optional[str] = None
    disclaimer: str = (
        "Statutory eligibility signal for authorized human legal review only. "
        "Does not constitute judicial relief, bail order, or legal counsel opinion."
    )


class LegalRuleDefinition(BaseModel):
    """
    Full metadata specification of a versioned, lifecycle-governed statutory rule.
    """
    rule_id: str
    rule_version: str
    title: str
    jurisdiction: str = "India / National"
    category: RuleCategory
    statutory_source: str
    effective_date: str
    lifecycle_state: RuleLifecycleState = RuleLifecycleState.ACTIVE
    applicability_conditions: Dict[str, Any] = Field(default_factory=dict)
    required_inputs: List[str] = Field(default_factory=list)
    calculation_method: str
    exclusions_and_provisos: List[Dict[str, Any]] = Field(default_factory=list)
    output_statuses: List[RuleMachineStatus] = Field(default_factory=list)
    explanation_template: str
    legal_review_metadata: Dict[str, Any] = Field(default_factory=dict)
    approval_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RuleExecutionResult(BaseModel):
    """Complete rule execution outcome with backward-compatible accessors."""
    execution_id: str
    case_id: str
    rule_id: str
    rule_version: str
    machine_status: RuleMachineStatus
    is_eligible: bool
    threshold_fraction: float
    threshold_days: int
    countable_custody_days: int
    total_elapsed_calendar_days: int
    excluded_delay_days: int
    days_overdue: int
    explanation: RuleExplanation
    audit_record_id: Optional[str] = None
