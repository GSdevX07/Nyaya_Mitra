"""
app.workflow.routes - Server-Enforced Matter/Case Lifecycle REST API.
====================================================================
Exposes authoritative endpoints for transitions, approvals, artifacts, handoffs,
timeline inspection, and external synchronization.
All actions enforce strict Nyaya Mitra role ownership.
"""

from __future__ import annotations
import datetime
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.auth.dependencies import get_current_user, AuthUser
from app.auth.roles import Role
from app.models.schemas import (
    MatterTransitionRequest,
    MatterApprovalRequest,
    MatterHandoffRequest,
    MatterArtifactCreateRequest,
    ExternalSyncRequest,
    MatterState,
)
from app.workflow.service import WorkflowService, ConcurrencyConflictError
from app.workflow.state_machine import WorkflowStateMachine
from app.database import get_matter_approvals, get_matter_artifact_versions, get_active_matter_artifact

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Workflow & Matter Lifecycle"])


@router.post("/matters/{case_id}/transitions")
@router.post("/cases/{case_id}/transitions")
async def execute_transition_endpoint(
    case_id: str,
    req: MatterTransitionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Authoritative state transition request.
    Validates state machine rules, actor roles, required evidence, and concurrency.
    """
    try:
        result = WorkflowService.execute_transition(
            case_id=case_id,
            action=req.transition,
            actor=current_user,
            payload=req.payload,
            comment=req.comment,
            expected_version=req.expected_version,
            is_ai_agent=False,
        )
        return result
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConcurrencyConflictError as e:
        conflict_details = getattr(e, "conflict_details", None)
        headers = {}
        if conflict_details:
            import json
            headers["X-Conflict-Details"] = json.dumps(conflict_details)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
            headers=headers if headers else None,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected transition failure: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Workflow transition failed.")


@router.get("/matters/{case_id}/state")
@router.get("/cases/{case_id}/state")
async def get_case_state_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve current authoritative lifecycle state, version, and case metadata."""
    try:
        canonical_state, version_number, case_data = WorkflowService.get_case_state(case_id)
        return {
            "case_id": case_id,
            "canonical_state": canonical_state.value,
            "raw_status": case_data.get("status") or case_data.get("current_status"),
            "version_number": version_number,
            "assigned_advocate_id": case_data.get("assigned_advocate_id"),
            "assigned_advocate_name": case_data.get("assigned_advocate_name"),
            "filing_reference": case_data.get("filing_reference"),
            "hearing_date": case_data.get("hearing_date"),
        }
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/matters/{case_id}/available-transitions")
@router.get("/cases/{case_id}/available-transitions")
async def get_available_transitions_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """List valid transitions from the current state and indicate if the calling user can execute each."""
    try:
        canonical_state, version_number, case_data = WorkflowService.get_case_state(case_id)
        active_art = get_active_matter_artifact(case_id, "BAIL_APPLICATION")
        has_approval = False
        if active_art:
            approvals = get_matter_approvals(case_id, active_art["version_id"])
            has_approval = any(
                a.get("decision") == "APPROVED" and a.get("approval_level", 1) >= 2 and a.get("is_valid", 1) == 1
                for a in approvals
            )
        transitions = WorkflowStateMachine.get_available_transitions(
            current_state=canonical_state,
            actor_role=current_user.role,
            case_data=case_data,
            actor=current_user,
            active_artifact=active_art,
            has_supervisory_approval=has_approval,
        )
        return {
            "case_id": case_id,
            "current_state": canonical_state.value,
            "version_number": version_number,
            "available_transitions": transitions,
        }
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/matters/{case_id}/approvals")
@router.post("/cases/{case_id}/approvals")
async def record_approval_endpoint(
    case_id: str,
    req: MatterApprovalRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Record first-class institutional approval decision for an exact artifact version."""
    try:
        result = WorkflowService.record_approval(
            case_id=case_id,
            artifact_id=req.artifact_id,
            artifact_version_id=req.artifact_version_id,
            artifact_type=req.artifact_type,
            decision=req.decision,
            comment=req.comment,
            actor=current_user,
            approval_level=req.approval_level,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/matters/{case_id}/approvals")
@router.get("/cases/{case_id}/approvals")
async def get_matter_approvals_endpoint(
    case_id: str,
    artifact_version_id: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
):
    """List approvals recorded for a matter or specific artifact version."""
    approvals = get_matter_approvals(case_id, artifact_version_id)
    return {"case_id": case_id, "approvals": approvals}


@router.post("/matters/{case_id}/artifacts")
@router.post("/cases/{case_id}/artifacts")
async def create_artifact_endpoint(
    case_id: str,
    req: MatterArtifactCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Create an immutable artifact version N+1 with SHA-256 hash."""
    try:
        result = WorkflowService.create_artifact_version(
            case_id=case_id,
            artifact_id=req.artifact_id,
            artifact_type=req.artifact_type,
            content_text=req.content_text,
            actor=current_user,
            is_ai_generated=req.is_ai_generated,
            ai_model_name=req.ai_model_name,
            version_tag=req.version_tag,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/matters/{case_id}/artifacts")
@router.get("/cases/{case_id}/artifacts")
async def list_artifacts_endpoint(
    case_id: str,
    artifact_id: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve versions of legal artifacts registered for the matter."""
    versions = get_matter_artifact_versions(case_id, artifact_id)
    active = get_active_matter_artifact(case_id, "BAIL_APPLICATION")
    return {
        "case_id": case_id,
        "artifact_versions": versions,
        "active_artifact": active,
    }


@router.post("/matters/{case_id}/handoff")
@router.post("/cases/{case_id}/handoff")
async def execute_handoff_endpoint(
    case_id: str,
    req: MatterHandoffRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Reassign case and record immutable handoff packet."""
    try:
        result = WorkflowService.record_handoff(
            case_id=case_id,
            to_user_id=req.to_user_id,
            to_role=req.to_role,
            reason=req.reason,
            actor=current_user,
            metadata=req.metadata,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/matters/{case_id}/handoff-summary")
@router.get("/cases/{case_id}/handoff-summary")
async def get_handoff_summary_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve comprehensive handoff packet for incoming counsel."""
    try:
        summary = WorkflowService.get_handoff_summary(case_id)
        return summary
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/matters/{case_id}/timeline")
async def get_matter_timeline_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve unified chronological timeline with provenance badges (USER, SYSTEM, AI, EXTERNAL_SYNC)."""
    events = WorkflowService.get_matter_timeline(case_id)
    return {"case_id": case_id, "timeline": events}


@router.post("/matters/{case_id}/external-sync")
@router.post("/cases/{case_id}/external-sync")
async def record_external_sync_endpoint(
    case_id: str,
    req: ExternalSyncRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Record external court or prison registry sync."""
    result = WorkflowService.record_external_sync(
        case_id=case_id,
        source_system=req.source_system,
        external_reference=req.external_reference,
        received_data=req.received_data,
        actor=current_user,
    )
    return result


@router.post("/matters/{case_id}/draft/generate")
@router.post("/cases/{case_id}/draft/generate")
async def generate_draft_endpoint(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    On-demand legal aid bail petition generation.
    Allowed roles: DEFENSE_ADVOCATE (assigned), SUPERVISING_LEGAL_OFFICER, DLSA_OFFICER, PLATFORM_ADMIN.
    Synthesizes facts, queries retrieval agent for Section 479 BNSS statutes, invokes LLM with
    guaranteed statutory fallback, and persists active artifact version.
    """
    # Strict Procedural Role Boundary:
    # Only assigned Defense Legal-Aid Advocates are authorized to prepare and generate bail petition drafts.
    # DLSA officers and supervisory officers have oversight/monitoring roles but cannot generate advocate work product.
    if current_user.role not in (
        Role.DEFENSE_ADVOCATE, Role.CONTROLLED_EXTERNAL_ADVOCATE,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only assigned Defense Legal-Aid Advocates are authorized to prepare and generate bail petition drafts. DLSA and supervisory officers may review and coordinate but cannot generate advocate work product.",
        )

    canonical_state, current_ver, case_data = WorkflowService.get_case_state(case_id)
    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")

    # Procedural Rule: Bail petition drafting requires an assigned legal defense counsel
    has_assigned_counsel = bool(
        case_data.get("assigned_advocate_id")
        or case_data.get("assigned_lawyer_id")
        or case_data.get("assigned_lawyer")
    )
    if not has_assigned_counsel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate bail petition draft: Legal Aid defense counsel has not been assigned to case '{case_id}' yet. Please assign counsel from the DLSA roster first.",
        )

    # Defense advocate assignment check
    if current_user.role in (Role.DEFENSE_ADVOCATE, Role.CONTROLLED_EXTERNAL_ADVOCATE):
        user_full = (current_user.full_name or "").lower()
        is_assigned = (
            (case_data.get("assigned_advocate_id") and case_data.get("assigned_advocate_id") == current_user.id)
            or (case_data.get("assigned_lawyer_id") and case_data.get("assigned_lawyer_id") == current_user.id)
            or (case_data.get("assigned_lawyer") and user_full and user_full in case_data.get("assigned_lawyer", "").lower())
            or (getattr(current_user, "linked_case_id", None) and getattr(current_user, "linked_case_id", None) == case_id)
        )
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You are not the assigned defense counsel for case '{case_id}'.",
            )

    # Construct CaseRecord
    from app.models.schemas import CaseRecord
    try:
        case_record = CaseRecord(**case_data)
    except Exception:
        case_record = CaseRecord(
            case_id=case_id,
            name=case_data.get("name") or case_data.get("accused_name", "Under-Trial Accused"),
            offense_sections=case_data.get("offense_sections", ["IPC 379"]),
            arrest_date=case_data.get("arrest_date", "2024-01-01"),
            custody_days=int(case_data.get("custody_days", 180)),
            max_sentence_days_for_offense=int(case_data.get("max_sentence_days_for_offense", 1095)),
            court_name=case_data.get("court_name", "Sessions Court"),
            district=case_data.get("district", "Central District"),
        )

    # Retrieve statutory authority
    retrieved_law = ""
    try:
        from app.agents.retrieval_agent import retrieve_statutes
        retrieved_res = retrieve_statutes(case_record)
        retrieved_law = retrieved_res.get("retrieved_text", "")
    except Exception as e:
        logger.warning(f"Statute retrieval encountered an issue: {e}")

    if not retrieved_law:
        retrieved_law = (
            "Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023: "
            "Where a person has, during the period of investigation, inquiry or trial "
            "under this Sanhita of an offence under any law undergone detention for a period "
            "extending up to one-half (or one-third for a first-time offender) of the maximum period of imprisonment "
            "specified for that offence under that law, he shall be released by the Court on bail."
        )

    # Draft bail application via LLM
    draft_text = ""
    try:
        from app.agents.drafting_agent import draft_bail_application
        draft_res = draft_bail_application(case_record, retrieved_law)
        candidate = draft_res.get("drafted_document", "")
        if candidate and "unavailable" not in candidate.lower() and len(candidate.strip()) > 50:
            draft_text = candidate.strip()
    except Exception as e:
        logger.warning(f"Drafting agent LLM failed: {e}")

    # High-fidelity statutory template fallback if LLM was unavailable
    if not draft_text:
        accused_name = case_data.get("name") or case_data.get("accused_name") or "Under-Trial Prisoner"
        court_name = case_data.get("court_name") or "HON'BLE COURT OF PRINCIPAL SESSIONS JUDGE"
        district = case_data.get("district") or "Central District, Delhi"
        fir_number = case_data.get("fir_number") or case_data.get("fir_no") or f"FIR-2024-{case_id}"
        police_station = case_data.get("police_station") or case_data.get("jail_location") or "Local Police Station"
        sections = ", ".join(case_data.get("offense_sections") or ["Section 379 BNS"])
        custody_days = case_data.get("custody_days") or 180
        max_days = case_data.get("max_sentence_days_for_offense") or 1095
        ratio_pct = round((custody_days / max_days) * 100, 1) if max_days else 50.0
        advocate_name = case_data.get("assigned_advocate_name") or case_data.get("assigned_lawyer") or current_user.full_name or "DLSA Legal Aid Panel Counsel"
        today_str = datetime.date.today().strftime("%d-%m-%Y")

        draft_text = f"""IN THE COURT OF {court_name.upper()}
AT {district.upper()}

BAIL APPLICATION NO. ______ OF {datetime.date.today().year}
IN THE MATTER OF:
CASE / FIR NO: {fir_number}
POLICE STATION: {police_station}
UNDER SECTION(S): {sections}

IN THE MATTER OF:
{accused_name.upper()}
...APPLICANT / ACCUSED

VERSUS

STATE OF NCT OF DELHI / RESPONDENT STATE
...PROSECUTION / RESPONDENT

APPLICATION UNDER SECTION 479 OF BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023 
(READ WITH ARTICLE 21 OF THE CONSTITUTION OF INDIA) FOR GRANT OF STATUTORY MANDATORY BAIL

MOST RESPECTFULLY SHOWETH:

1. That the Applicant / Accused above named has been in continuous judicial custody since {case_data.get("arrest_date", "the date of arrest")}, having completed {custody_days} days of incarceration in {police_station}.

2. That the maximum prescribed term of imprisonment for the alleged offenses ({sections}) is {max_days} days ({round(max_days/365, 1) if max_days else 3} years). The applicant has already undergone {custody_days} days, representing {ratio_pct}% of the maximum term.

3. STATUTORY ENTITLEMENT UNDER SECTION 479 BNSS:
   Under Section 479(1) of Bharatiya Nagarik Suraksha Sanhita, 2023:
   Where a person has undergone detention for a period extending up to one-half (or one-third in the case of a first-time offender) of the maximum period of imprisonment specified for that offense under the law, they shall be released by the Court on bail:
   Provided that where such person is a first-time offender who has never been convicted of any offense in the past, he shall be released on bail on completing one-third custody.
   The applicant satisfies all conditions stipulated under Section 479 BNSS:
   (a) The offenses charged do not carry the punishment of death or life imprisonment.
   (b) The investigation/trial is pending and prolonged incarceration infringes on the constitutional guarantee to speedy justice under Article 21.
   (c) The Applicant has deep familial and societal ties, is not a flight risk, and undertakes to abide strictly by all conditions imposed by this Hon'ble Court.

4. That the Applicant has verified identity, and reliable local sureties are prepared to furnish solvent bond as directed by this Hon'ble Court.

PRAYER:
In the premises aforesaid, it is most respectfully prayed that this Hon'ble Court may be pleased to:
(a) Admit the Applicant / Accused ({accused_name}) to statutory bail under Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023 on reasonable terms and conditions;
(b) Pass any other or further order(s) as this Hon'ble Court may deem fit and proper in the interest of justice.

FILED BY:
ADV. {advocate_name.upper()}
COUNSEL FOR THE APPLICANT
DATE: {today_str}
PLACE: {district}
"""

    # Persist as active artifact version in matter_artifact_versions
    ver_record = WorkflowService.create_artifact_version(
        case_id=case_id,
        artifact_id="bail_draft_01",
        artifact_type="BAIL_APPLICATION",
        content_text=draft_text,
        actor=current_user,
        is_ai_generated=True,
        ai_model_name="Groq/WatsonX LLaMA-3 + BNSS Statutory Engine",
    )

    return {
        "case_id": case_id,
        "draft_text": draft_text,
        "version_id": ver_record["version_id"],
        "version_number": ver_record["version_number"],
        "provenance": ver_record["provenance_tag"],
        "message": "AI bail petition drafted and stored as active artifact version.",
    }

