"""
document_workspace_routes.py - Professional Document Workspace REST APIs.
=========================================================================
Endpoints for versioned legal templates, grounded AI draft generation,
dual-pane review editing, readiness gating, diffing, packaging, and export.
"""

from __future__ import annotations
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.auth.dependencies import get_current_user
from app.auth.user_store import AuthUser
from app.auth.roles import Role
from app.database import (
    get_case,
    get_document_templates,
    get_document_template_by_id,
    store_document_template,
    store_legal_document_draft,
    get_legal_document_draft,
    update_legal_document_draft,
    list_legal_document_drafts_for_case,
    store_matter_approval,
    audit_repo,
)
from app.services.document_templates import (
    can_maintain_templates,
    render_template,
    seed_default_templates,
    DEFAULT_TEMPLATES,
)
from app.services.document_validation import DocumentReadinessChecker
from app.services.document_export import (
    compute_draft_diff,
    generate_document_export_payload,
    prepare_submission_package,
    record_external_filing,
    can_view_internal_audit_notes,
)
from app.models.domain import AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Document Workspace"])


# ── Authorized Role Sets Aligned With 11-Role Matrix (Stage 19) ───────────────

DRAFT_VIEW_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
    Role.CONTROLLED_EXTERNAL_ADVOCATE,
    Role.READ_ONLY_AUDITOR,
}

DRAFT_INITIATE_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
}

DRAFT_EDIT_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
}

DRAFT_APPROVE_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
}

DRAFT_REJECT_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
}

DRAFT_COMMENT_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
}

DRAFT_PACKAGE_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
}

DRAFT_FILING_ROLES = {
    Role.DEFENSE_ADVOCATE,
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
}


# ── Pydantic Request / Response Models ───────────────────────────────────────

class TemplateCreateRequest(BaseModel):
    name: str
    doc_type: str
    jurisdiction: str = "National / BNSS 2023"
    statutory_ground: str
    description: Optional[str] = ""
    content_template: str
    required_fields: List[str] = []
    required_documents: List[str] = []
    organization_id: Optional[str] = None


class TemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content_template: Optional[str] = None
    required_fields: Optional[List[str]] = None
    required_documents: Optional[List[str]] = None
    statutory_ground: Optional[str] = None
    jurisdiction: Optional[str] = None


class DraftGenerateRequest(BaseModel):
    case_id: str
    template_id: Optional[str] = "tmpl_bnss_479_bail_v1"
    custom_instructions: Optional[str] = None


class DraftUpdateRequest(BaseModel):
    content_text: str


class DraftCommentRequest(BaseModel):
    comment: str


class DraftApprovalRequest(BaseModel):
    comment: Optional[str] = "Legal review completed and approved for court filing."


class DraftRejectionRequest(BaseModel):
    reason: str


class PackagePrepareRequest(BaseModel):
    exhibits: Optional[List[str]] = None


class RecordFilingRequest(BaseModel):
    filing_reference: str
    filing_date: Optional[str] = None
    court_name: Optional[str] = None


# ── Template Management Endpoints ────────────────────────────────────────────

@router.get("/templates")
def list_templates(
    doc_type: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
):
    """List available document templates. Returns global templates + user organization templates."""
    if current_user.role in {Role.ACCUSED_USER, Role.FAMILY_GUARDIAN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Accused persons and family members access case documents via the citizen portal.",
        )
    seed_default_templates()
    org_id = getattr(current_user, "org_id", "GLOBAL_DEFAULT")
    templates = get_document_templates(organization_id=org_id, doc_type=doc_type)
    return {"templates": templates, "total": len(templates)}


@router.get("/templates/{template_id}")
def get_template_detail(
    template_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Get single document template by ID."""
    if current_user.role in {Role.ACCUSED_USER, Role.FAMILY_GUARDIAN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Accused persons and family members access case documents via the citizen portal.",
        )
    seed_default_templates()
    tmpl = get_document_template_by_id(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")
    return tmpl


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(
    req: TemplateCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Author a new versioned legal template. Restricted to authorized maintainers."""
    if not can_maintain_templates(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Platform Admins, Gov Admins, and Supervising Legal Officers can create templates.",
        )

    org_id = req.organization_id or getattr(current_user, "org_id", "GLOBAL_DEFAULT")
    tmpl_id = f"tmpl_{req.doc_type.lower()}_{uuid.uuid4().hex[:8]}"

    record = {
        "id": tmpl_id,
        "organization_id": org_id,
        "name": req.name,
        "doc_type": req.doc_type,
        "version": 1,
        "jurisdiction": req.jurisdiction,
        "statutory_ground": req.statutory_ground,
        "description": req.description,
        "content_template": req.content_template,
        "required_fields": req.required_fields,
        "required_documents": req.required_documents,
        "is_active": True,
        "created_by": current_user.full_name or current_user.id,
    }

    success = store_document_template(record)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to persist template.")

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.DOCUMENT_UPLOAD,
        entity_type="DOCUMENT_TEMPLATE",
        entity_id=tmpl_id,
        details={"template_name": req.name, "doc_type": req.doc_type},
        organization_id=org_id,
    )

    return record


@router.put("/templates/{template_id}")
def update_template(
    template_id: str,
    req: TemplateUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Update a document template. Increments version and records audit event."""
    if not can_maintain_templates(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Platform Admins, Gov Admins, and Supervising Legal Officers can edit templates.",
        )

    existing = get_document_template_by_id(template_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found.")

    new_ver = existing.get("version", 1) + 1
    updated = {
        **existing,
        "version": new_ver,
        "name": req.name if req.name is not None else existing["name"],
        "description": req.description if req.description is not None else existing.get("description"),
        "content_template": req.content_template if req.content_template is not None else existing["content_template"],
        "required_fields": req.required_fields if req.required_fields is not None else existing.get("required_fields", []),
        "required_documents": req.required_documents if req.required_documents is not None else existing.get("required_documents", []),
        "statutory_ground": req.statutory_ground if req.statutory_ground is not None else existing["statutory_ground"],
        "jurisdiction": req.jurisdiction if req.jurisdiction is not None else existing["jurisdiction"],
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    store_document_template(updated)

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.DOCUMENT_UPLOAD,
        entity_type="DOCUMENT_TEMPLATE_UPDATE",
        entity_id=template_id,
        details={"new_version": new_ver},
        organization_id=existing.get("organization_id"),
    )

    return updated


# ── Draft Generation & Lifecycle Endpoints ───────────────────────────────────

@router.get("/drafts/case/{case_id}")
def list_case_drafts(
    case_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """List all legal drafts and version history for a case."""
    if current_user.role not in DRAFT_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Access to legal draft records is restricted to authorized legal, supervisory, and audit personnel.",
        )
    drafts = list_legal_document_drafts_for_case(case_id)
    return {"case_id": case_id, "drafts": drafts, "total": len(drafts)}


@router.get("/drafts/{draft_id}")
def get_draft_detail(
    draft_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve complete draft record with snapshot facts, citations, warnings, and comments."""
    if current_user.role not in DRAFT_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Access to legal draft records is restricted to authorized legal, supervisory, and audit personnel.",
        )
    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")
    return draft


@router.post("/drafts/generate", status_code=status.HTTP_201_CREATED)
def generate_grounded_draft(
    req: DraftGenerateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Generate a new provisional legal draft grounded in exact case facts,
    deterministic rules, source documents, retrieved statutory sources, and templates.
    """
    if current_user.role not in DRAFT_INITIATE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only assigned defense advocates, supervising legal officers, or delegated DLSA officers can initiate legal draft generation.",
        )
    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{req.case_id}' not found.")

    case_data = case if isinstance(case, dict) else (
        case.model_dump() if hasattr(case, "model_dump") else case.__dict__
    )

    seed_default_templates()
    template = get_document_template_by_id(req.template_id or "tmpl_bnss_479_bail_v1")
    if not template:
        template = DEFAULT_TEMPLATES[0]

    # Retrieve statutory authority
    retrieved_sources: List[Dict[str, Any]] = []
    retrieved_text = ""
    try:
        from app.agents.retrieval_agent import retrieve_statutes
        from app.models.schemas import CaseRecord
        case_rec = CaseRecord(**case_data)
        ret_res = retrieve_statutes(case_rec)
        retrieved_text = ret_res.get("retrieved_text", "")
        retrieved_sources.append({
            "citation_key": "BNSS_479",
            "citation": "Section 479 BNSS, 2023",
            "title": "Section 479 Bharatiya Nagarik Suraksha Sanhita, 2023",
            "statute_text": retrieved_text,
            "excerpt": retrieved_text,
        })
    except Exception as e:
        logger.warning(f"Retrieval agent error during draft generation: {e}")
        retrieved_text = (
            "Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023: "
            "Where a person has undergone detention for a period extending up to one-half "
            "(or one-third for a first-time offender) of the maximum period of imprisonment, "
            "he shall be released by the Court on bail."
        )
        retrieved_sources.append({
            "citation_key": "BNSS_479_DEFAULT",
            "citation": "Section 479 BNSS, 2023",
            "title": "Section 479 BNSS, 2023 (Statutory Rule)",
            "statute_text": retrieved_text,
            "excerpt": retrieved_text,
        })

    # Prepare Case Facts Snapshot
    accused_name = case_data.get("name") or case_data.get("accused_name", "Undertrial Accused")
    court_name = case_data.get("court_name") or "Hon'ble Court of Principal Sessions Judge"
    district = case_data.get("district") or "Central District, Delhi"
    fir_number = case_data.get("fir_number") or f"FIR-2024-{req.case_id}"
    police_station = case_data.get("police_station") or case_data.get("jail_location", "Local Police Station")
    sections = case_data.get("offense_sections") or ["Section 379 BNS"]
    custody_days = case_data.get("custody_days", 180)
    max_days = case_data.get("max_sentence_days_for_offense", 1095)
    advocate_name = case_data.get("assigned_lawyer") or current_user.full_name or "DLSA Legal Aid Panel Counsel"

    # Deterministic Rule Result
    is_repeat = bool(case_data.get("urgency_flags", {}).get("repeat_offender") if isinstance(case_data.get("urgency_flags"), dict) else False)
    threshold_fraction = "1/2" if is_repeat else "1/3"
    threshold_days = int(max_days / 2) if is_repeat else int(max_days / 3)
    is_eligible = custody_days >= threshold_days
    rule_result = {
        "statute": "Section 479 BNSS, 2023",
        "is_eligible": is_eligible,
        "eligible": is_eligible,
        "mandatory_release_applicable": is_eligible,
        "custody_days": custody_days,
        "threshold_days": threshold_days,
        "statutory_threshold_fraction": threshold_fraction,
        "max_sentence_days": max_days,
    }

    # Snapshot of Source Documents
    source_docs = []
    for d_name in case_data.get("present_docs", []):
        source_docs.append({
            "document_type": d_name,
            "file_name": f"{d_name}_{req.case_id}.pdf",
            "is_verified": True,
            "verification_authority": "eCourts / Prison PMS",
        })

    # Render Template
    render_ctx = {
        "court_name": court_name.upper(),
        "district": district.upper(),
        "filing_year": datetime.date.today().year,
        "fir_number": fir_number,
        "police_station": police_station,
        "offense_sections": ", ".join(sections) if isinstance(sections, list) else sections,
        "accused_name": accused_name.upper(),
        "arrest_date": case_data.get("arrest_date", "the date of arrest"),
        "custody_days": custody_days,
        "jail_location": case_data.get("jail_location", "District Jail"),
        "max_sentence_days_for_offense": max_days,
        "threshold_days": threshold_days,
        "statutory_threshold_fraction": threshold_fraction,
        "assigned_lawyer": advocate_name.upper(),
        "current_date": datetime.date.today().strftime("%d-%m-%Y"),
        "case_id": req.case_id,
        "parent_or_guardian_name": case_data.get("parent_name", "Family Guardian"),
    }

    rendered_text, missing_fields = render_template(template["content_template"], render_ctx)

    # Determine existing drafts count for versioning
    existing_drafts = list_legal_document_drafts_for_case(req.case_id)
    next_ver = len(existing_drafts) + 1
    draft_id = f"draft_{uuid.uuid4().hex[:12]}"

    prompt_ver = f"sys_v2.1_tmpl_{template['id']}_v{template['version']}"
    ai_model = "Groq/LLaMA-3-70b + Governed BNSS Engine"

    # Identify citations & warnings
    source_citations = [
        {"section": "Section 479", "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023", "relevance": "Statutory Bail Ground"},
        {"section": "Article 21", "statute": "Constitution of India", "relevance": "Constitutional Speedy Justice Right"},
    ]

    unresolved_warnings = []
    if "custody_certificate" not in [d.lower() for d in case_data.get("present_docs", [])]:
        unresolved_warnings.append("Custody Certificate has not been uploaded. Grounding is tentative until prison certificate is received.")

    # Create Draft Record
    draft_record = {
        "draft_id": draft_id,
        "case_id": req.case_id,
        "artifact_id": "bail_draft_01",
        "template_id": template["id"],
        "template_version": template["version"],
        "version_number": next_ver,
        "status": "DRAFT",
        "original_ai_text": rendered_text,
        "content_text": rendered_text,
        "exact_case_facts": render_ctx,
        "source_documents": source_docs,
        "legal_rule_result": rule_result,
        "retrieved_legal_sources": retrieved_sources,
        "prompt_version": prompt_ver,
        "ai_model_name": ai_model,
        "source_citations": source_citations,
        "linked_case_facts": render_ctx,
        "missing_facts": missing_fields,
        "unresolved_warnings": unresolved_warnings,
        "reviewer_comments": [],
        "is_immutable": False,
        "created_by": current_user.full_name or current_user.id,
        "created_by_role": current_user.role.value,
    }

    # Run readiness check
    readiness = DocumentReadinessChecker.validate_draft(draft_record, case_data, template)
    draft_record["readiness_check_result"] = readiness

    success = store_legal_document_draft(draft_record)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save generated legal draft.")

    # Dual sync with WorkflowService artifact versions
    try:
        from app.workflow.service import WorkflowService
        WorkflowService.create_artifact_version(
            case_id=req.case_id,
            artifact_id="bail_draft_01",
            artifact_type=template["doc_type"],
            content_text=rendered_text,
            actor=current_user,
            is_ai_generated=True,
            ai_model_name=ai_model,
            version_tag=f"{template['doc_type'].lower()}_v{next_ver}",
        )
    except Exception as e:
        logger.warning(f"WorkflowService artifact dual-sync warning: {e}")

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.DOCUMENT_UPLOAD,
        entity_type="LEGAL_DOCUMENT_DRAFT",
        entity_id=draft_id,
        details={
            "case_id": req.case_id,
            "version_number": next_ver,
            "template_id": template["id"],
            "is_ai_generated": True,
        },
        organization_id=getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
    )

    return draft_record


@router.put("/drafts/{draft_id}")
def update_draft_content(
    draft_id: str,
    req: DraftUpdateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Update working draft content. Preserves original machine text permanently.
    Rejected with 403 if the draft has already received final approval and is immutable.
    """
    if current_user.role not in DRAFT_EDIT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only assigned defense advocates and supervising legal officers are authorized to edit working petition text.",
        )

    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    if draft.get("is_immutable"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Draft '{draft_id}' is permanently immutable because it has received formal legal sign-off. Please initiate a new revision workflow to create Version {draft.get('version_number', 1) + 1}.",
        )

    # Re-evaluate readiness
    updated_draft = {**draft, "content_text": req.content_text}
    template = get_document_template_by_id(draft.get("template_id", ""))
    readiness = DocumentReadinessChecker.validate_draft(updated_draft, draft.get("exact_case_facts"), template)

    update_legal_document_draft(draft_id, {
        "content_text": req.content_text,
        "readiness_check_result": readiness,
    })

    full_draft = get_legal_document_draft(draft_id)
    return {
        **(full_draft or updated_draft),
        "message": "Working draft content updated successfully.",
    }


@router.get("/drafts/{draft_id}/readiness")
@router.post("/drafts/{draft_id}/readiness")
@router.get("/drafts/{draft_id}/validate")
@router.post("/drafts/{draft_id}/validate")
def run_readiness_validation(
    draft_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Execute pre-approval readiness check on a draft."""
    if current_user.role not in DRAFT_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Pre-approval readiness evaluation is restricted to authorized legal, supervisory, and audit personnel.",
        )

    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    template = get_document_template_by_id(draft.get("template_id", ""))
    report = DocumentReadinessChecker.validate_draft(draft, draft.get("exact_case_facts"), template)

    update_legal_document_draft(draft_id, {"readiness_check_result": report})
    return report


@router.post("/drafts/{draft_id}/comments")
def add_reviewer_comment(
    draft_id: str,
    req: DraftCommentRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Add a threaded comment/scrutiny note to a draft."""
    if current_user.role not in DRAFT_COMMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only defense advocates, supervising legal officers, and DLSA officers can record reviewer comments on drafts.",
        )

    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    comment_obj = {
        "id": f"comment_{uuid.uuid4().hex[:8]}",
        "author_id": current_user.id,
        "author_name": current_user.full_name or current_user.id,
        "role": current_user.role.value,
        "comment": req.comment.strip(),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    comments = draft.get("reviewer_comments", [])
    comments.append(comment_obj)
    update_legal_document_draft(draft_id, {"reviewer_comments": comments})

    full_draft = get_legal_document_draft(draft_id)
    return full_draft or {"draft_id": draft_id, "comments": comments}


@router.post("/drafts/{draft_id}/approve")
def approve_draft(
    draft_id: str,
    req: DraftApprovalRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Formal legal approval of draft petition.
    STRICT GATING: Blocked if pre-approval readiness check has unresolved blocking issues.
    Locks document permanently (is_immutable = 1).
    """
    # Role check: only assigned defense advocates and legal supervisors can grant legal sign-off
    if current_user.role not in DRAFT_APPROVE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Formal legal approval is restricted to assigned defense advocates and supervising legal officers.",
        )

    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    if draft.get("is_immutable"):
        return {
            "draft_id": draft_id,
            "status": "APPROVED",
            "is_immutable": True,
            "message": "Draft is already approved and immutable.",
        }

    # Run fresh readiness check
    template = get_document_template_by_id(draft.get("template_id", ""))
    readiness = DocumentReadinessChecker.validate_draft(draft, draft.get("exact_case_facts"), template)

    if not readiness["can_approve"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Cannot approve draft petition: Pre-approval readiness check failed with blocking issues.",
                "blocking_issues": readiness["blocking_issues"],
                "total_blocking_issues": readiness["total_blocking_issues"],
            },
        )

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    update_legal_document_draft(draft_id, {
        "status": "APPROVED",
        "is_immutable": True,
        "approved_by": current_user.full_name or current_user.id,
        "approved_by_role": current_user.role.value,
        "approved_at": now_iso,
        "readiness_check_result": readiness,
    })

    # Record formal approval in matter_approvals
    store_matter_approval({
        "approval_id": f"appr_{uuid.uuid4().hex[:12]}",
        "matter_id": draft["case_id"],
        "actor_id": current_user.id,
        "actor_role": current_user.role.value,
        "organization_id": getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
        "created_at": now_iso,
        "decided_at": now_iso,
        "artifact_id": draft.get("artifact_id", "bail_draft_01"),
        "artifact_version_id": draft_id,
        "artifact_type": "BAIL_APPLICATION",
        "approval_level": 1 if current_user.role == Role.DEFENSE_ADVOCATE else 2,
        "required_level": 1,
        "decision": "APPROVED",
        "comment": req.comment or "Legal review completed and approved for court filing.",
    })

    # Trigger case state progression in WorkflowService
    from app.workflow.service import WorkflowService
    try:
        WorkflowService.execute_transition(
            case_id=draft["case_id"],
            action="COUNSEL_SIGN_OFF" if current_user.role == Role.DEFENSE_ADVOCATE else "SUPERVISORY_APPROVE",
            actor=current_user,
            comment=req.comment or "Formal approval granted on legal petition draft.",
        )
    except Exception as e:
        logger.warning(f"Workflow transition on approve_draft: {e}")

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.ADVOCATE_SIGN_OFF,
        entity_type="LEGAL_DOCUMENT_DRAFT",
        entity_id=draft_id,
        details={
            "case_id": draft["case_id"],
            "decision": "APPROVED",
            "version_number": draft.get("version_number"),
            "is_immutable": True,
        },
        organization_id=getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
    )

    updated_draft = get_legal_document_draft(draft_id)
    return {
        **(updated_draft or {}),
        "draft_id": draft_id,
        "case_id": draft["case_id"],
        "version_number": draft.get("version_number"),
        "status": "APPROVED",
        "is_immutable": True,
        "approved_by": current_user.full_name or current_user.id,
        "approved_at": now_iso,
        "message": "Petition draft formally approved. Document is now permanently locked and immutable.",
    }


@router.post("/drafts/{draft_id}/reject")
def reject_draft(
    draft_id: str,
    req: DraftRejectionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """Reject a draft with mandatory explanation."""
    if current_user.role not in DRAFT_REJECT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Returning drafts for correction is restricted to defense advocates, supervising legal officers, and DLSA officers.",
        )
    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    if not req.reason or not req.reason.strip():
        raise HTTPException(status_code=400, detail="Rejection reason is mandatory.")

    update_legal_document_draft(draft_id, {
        "status": "REJECTED",
    })

    # Add comment with rejection reason
    comment_obj = {
        "id": f"comment_{uuid.uuid4().hex[:8]}",
        "author_id": current_user.id,
        "author_name": current_user.full_name or current_user.id,
        "role": current_user.role.value,
        "comment": f"[REJECTION NOTICE]: {req.reason}",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    comments = draft.get("reviewer_comments", [])
    comments.append(comment_obj)
    update_legal_document_draft(draft_id, {"reviewer_comments": comments})

    updated_draft = get_legal_document_draft(draft_id)
    return {
        **(updated_draft or {}),
        "draft_id": draft_id,
        "status": "REJECTED",
        "reason": req.reason,
    }


@router.post("/drafts/{draft_id}/revise", status_code=status.HTTP_201_CREATED)
def create_draft_revision(
    draft_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Initiate a new revision workflow from an existing draft.
    Creates Version N+1 with status 'DRAFT', resetting approvals while preserving
    prior versions immutably in history.
    """
    if current_user.role not in DRAFT_INITIATE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Initiating draft revisions is restricted to defense advocates, supervising legal officers, and DLSA officers.",
        )

    prior_draft = get_legal_document_draft(draft_id)
    if not prior_draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    next_ver = prior_draft.get("version_number", 1) + 1
    new_draft_id = f"draft_{uuid.uuid4().hex[:12]}"

    new_draft_record = {
        **prior_draft,
        "draft_id": new_draft_id,
        "version_number": next_ver,
        "status": "DRAFT",
        "is_immutable": False,
        "approved_by": None,
        "approved_by_role": None,
        "approved_at": None,
        "submission_package": None,
        "external_filing_reference": None,
        "external_filing_date": None,
        "created_by": current_user.full_name or current_user.id,
        "created_by_role": current_user.role.value,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    # Re-evaluate readiness for new revision
    template = get_document_template_by_id(prior_draft.get("template_id", ""))
    readiness = DocumentReadinessChecker.validate_draft(new_draft_record, prior_draft.get("exact_case_facts"), template)
    new_draft_record["readiness_check_result"] = readiness

    store_legal_document_draft(new_draft_record)

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.DOCUMENT_UPLOAD,
        entity_type="LEGAL_DRAFT_REVISION",
        entity_id=new_draft_id,
        details={
            "prior_draft_id": draft_id,
            "new_version_number": next_ver,
            "case_id": prior_draft["case_id"],
        },
        organization_id=getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
    )

    return new_draft_record


# ── Submission Packaging & Court Filing Endpoints ────────────────────────────

@router.post("/drafts/{draft_id}/package")
def prepare_package(
    draft_id: str,
    req: PackagePrepareRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Prepare submission package for filing.
    ANTI-AUTO-FILING: Automatic filing is strictly disabled. Creates package manifest only.
    """
    if current_user.role not in DRAFT_PACKAGE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Preparing court submission packages is restricted to assigned defense advocates, supervising legal officers, and DLSA officers.",
        )
    try:
        manifest = prepare_submission_package(draft_id, current_user, exhibits=req.exhibits)
        return manifest
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/drafts/{draft_id}/record-filing")
def record_court_filing(
    draft_id: str,
    req: RecordFilingRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Record that an authorized user or verified integration submitted the petition in court.
    Requires verified CNR / filing receipt number.
    """
    if current_user.role not in DRAFT_FILING_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Recording court filing references is restricted to assigned defense advocates, supervising legal officers, and DLSA officers.",
        )
    try:
        res = record_external_filing(
            draft_id=draft_id,
            filing_reference=req.filing_reference,
            filing_date=req.filing_date or datetime.date.today().isoformat(),
            actor=current_user,
            court_name=req.court_name,
        )
        updated_draft = get_legal_document_draft(draft_id)
        return {
            **(updated_draft or {}),
            **res,
        }
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Version Diff & Export Endpoints ──────────────────────────────────────────

@router.get("/drafts/diff")
def get_explicit_drafts_diff(
    draft_id_a: Optional[str] = Query(None, description="First or prior draft ID"),
    draft_id_b: Optional[str] = Query(None, description="Second or current draft ID"),
    current_user: AuthUser = Depends(get_current_user),
):
    """Compute line-by-line diff between two explicit draft IDs."""
    if current_user.role not in DRAFT_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Inspecting draft diffs is restricted to authorized legal and audit personnel.",
        )
    if not draft_id_a or not draft_id_b:
        raise HTTPException(status_code=400, detail="Query parameters 'draft_id_a' and 'draft_id_b' are required.")

    draft_a = get_legal_document_draft(draft_id_a)
    draft_b = get_legal_document_draft(draft_id_b)
    if not draft_a:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id_a}' not found.")
    if not draft_b:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id_b}' not found.")

    diff_result = compute_draft_diff(draft_a.get("content_text", ""), draft_b.get("content_text", ""))
    return {
        "draft_id": draft_b.get("draft_id"),
        "base_label": f"Version {draft_a.get('version_number', 1)} ({draft_a.get('status')})",
        "current_label": f"Version {draft_b.get('version_number', 1)} ({draft_b.get('status')})",
        **diff_result,
    }


@router.get("/drafts/{draft_id}/diff")
def get_draft_diff(
    draft_id: str,
    compare_with: Optional[str] = Query("original", description="'original' or another draft_id"),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Compute line-by-line diff between current draft text and its original machine draft
    or another specific draft version.
    """
    if current_user.role not in DRAFT_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Inspecting draft diffs is restricted to authorized legal and audit personnel.",
        )

    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    if compare_with == "original":
        base_text = draft.get("original_ai_text", "")
        base_label = "Machine-Generated Original (AI Provisional Draft)"
    else:
        other = get_legal_document_draft(compare_with)
        if not other:
            raise HTTPException(status_code=404, detail=f"Comparison draft '{compare_with}' not found.")
        base_text = other.get("content_text", "")
        base_label = f"Version {other.get('version_number', 1)} ({other.get('status')})"

    current_text = draft.get("content_text", "")
    current_label = f"Version {draft.get('version_number', 1)} ({draft.get('status')})"

    diff_result = compute_draft_diff(base_text, current_text)
    return {
        "draft_id": draft_id,
        "base_label": base_label,
        "current_label": current_label,
        **diff_result,
    }


@router.get("/drafts/{draft_id}/export")
def export_draft_document(
    draft_id: str,
    include_internal_notes: bool = Query(False),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Export secure certified legal document.
    Enforces data segregation: internal notes are strictly omitted unless
    include_internal_notes=True AND the user role is authorized.
    """
    if current_user.role not in DRAFT_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Exporting draft documents is restricted to authorized legal and audit personnel.",
        )

    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")

    payload = generate_document_export_payload(
        draft_dict=draft,
        include_internal_notes=include_internal_notes,
        actor=current_user,
    )
    return payload
