"""
rule_engine_routes.py - Deterministic Legal Rules Engine API Endpoints.
======================================================================
Provides endpoints to list versioned rules, fetch detailed metadata, evaluate
cases with structured explanations, manage rule lifecycles under strict legal
governance, and reconstruct past historical assessments.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user, require_role, AuthUser
from app.auth.roles import Role
from app.rules.service import _GLOBAL_SERVICE as rule_service
from app.rules.models import RuleLifecycleState
from app.database import get_db_connection

router = APIRouter(prefix="/rules", tags=["Deterministic Rules Engine"])


class LifecycleTransitionRequest(BaseModel):
    target_state: str = Field(..., description="DRAFT, LEGAL_REVIEW, APPROVED, ACTIVE, SUPERSEDED, RETIRED")
    notes: Optional[str] = Field(default="", description="Legal justification notes for this transition.")


class RuleEvaluationRequest(BaseModel):
    case_id: Optional[str] = None
    custody_days: Optional[int] = None
    max_sentence_days: Optional[int] = None
    repeat_offender: Optional[bool] = None
    punishable_by_death_or_life: Optional[bool] = False
    multiple_active_cases: Optional[bool] = False
    excluded_delay_days: Optional[int] = 0
    offense_sections: Optional[list[str]] = None


@router.get("", summary="List all statutory legal rules")
def list_rules(current_user: AuthUser = Depends(get_current_user)):
    """List all versioned statutory legal rules and their lifecycle states."""
    return {"rules": rule_service.list_rules()}


@router.get("/registry", summary="Get rule registry listing")
def get_rule_registry_listing(current_user: AuthUser = Depends(get_current_user)):
    """Legacy registry listing with active version and rules."""
    from app.agents.eligibility_agent import RULE_REGISTRY as legacy_reg
    return {
        "active_version": legacy_reg._active_version,
        "rules": legacy_reg.list_rules(),
    }


@router.get("/{rule_id}", summary="Get rule details and historical versions")
def get_rule_details(rule_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get full metadata, calculation method, and historical versions of a rule."""
    rule = rule_service.get_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Legal rule '{rule_id}' not found in registry.",
        )
    return rule


@router.post("/{rule_id}/lifecycle", summary="Transition rule lifecycle state")
def transition_rule_lifecycle(
    rule_id: str,
    req: LifecycleTransitionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Transition legal rule governance lifecycle.
    Only SUPERVISING_LEGAL_OFFICER can approve or activate rules.
    Platform Administrators are strictly barred from approving statutory rules.
    """
    try:
        target_state_enum = RuleLifecycleState(req.target_state.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid lifecycle state: '{req.target_state}'. Valid states: {[s.value for s in RuleLifecycleState]}",
        )

    # Authority Enforcement Guard
    if target_state_enum in (RuleLifecycleState.APPROVED, RuleLifecycleState.ACTIVE):
        if current_user.role != Role.SUPERVISING_LEGAL_OFFICER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: Legal rule approval and activation requires active SUPERVISING_LEGAL_OFFICER authority. "
                    f"Role '{current_user.role.value}' is not authorized to enact statutory policy."
                ),
            )

    try:
        updated = rule_service.transition_rule_lifecycle(
            rule_id=rule_id,
            target_state=target_state_enum,
            actor=current_user,
            notes=req.notes or "",
        )
        return {
            "message": f"Rule '{rule_id}' successfully transitioned to '{target_state_enum.value}'.",
            "rule": updated.dict(),
        }
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except (ValueError, KeyError) as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post("/{rule_id}/evaluate", summary="Evaluate rule against supplied facts")
def evaluate_rule_against_facts(
    rule_id: str,
    req: RuleEvaluationRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Evaluate deterministic rule against supplied facts and return structured explanation object.
    """
    # Create synthetic CaseRecord proxy for standalone execution
    class ProxyCase:
        def __init__(self, d: RuleEvaluationRequest):
            self.case_id = d.case_id or "ADHOC_EVALUATION"
            self.custody_days = d.custody_days
            self.max_sentence_days_for_offense = d.max_sentence_days
            self.excluded_delay_days = d.excluded_delay_days or 0
            self.punishable_by_death_or_life = d.punishable_by_death_or_life or False
            self.multiple_active_cases = d.multiple_active_cases or False
            self.offense_sections = d.offense_sections or ["BNS Section 303(2)"]
            self.prisoner_category = "UNDERTRIAL"
            
            class ProxyFlags:
                def __init__(self, rep):
                    self.repeat_offender = rep
            self.urgency_flags = ProxyFlags(d.repeat_offender)
            self.missing_docs = []

    proxy = ProxyCase(req)
    result = rule_service.evaluate_case(
        case=proxy,
        rule_id=rule_id,
        actor=current_user,
    )
    return result.dict()


@router.get("/reconstruct/{execution_id}", summary="Reconstruct past assessment")
def reconstruct_past_assessment(
    execution_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Reconstruct an exact past assessment snapshot using its immutable execution record.
    """
    rec = rule_service.reconstruct_assessment(execution_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule execution record '{execution_id}' not found.",
        )
    return rec
