"""
document_workspace_routes.py - Professional Document Workspace REST APIs.
=========================================================================
Endpoints for versioned legal templates, grounded AI draft generation,
dual-pane review editing, readiness gating, diffing, packaging, and export.
Strictly NO emojis in code, comments, or error messages.
"""

from __future__ import annotations
import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response

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
    allocate_next_draft_version,
    store_matter_approval,
    store_institutional_delegation,
    get_institutional_delegation,
    list_institutional_delegations,
    revoke_institutional_delegation,
    find_active_user_delegation,
    store_document_preparation_requisition,
    get_document_preparation_requisition,
    list_document_preparation_requisitions_for_case,
    audit_repo,
)
from app.services.document_authorization import (
    authorize_document_action,
    DocumentAction,
    TEMPLATE_MAINTAINER_ROLES,
    DRAFT_APPROVER_ROLES,
    DRAFT_EDITOR_ROLES,
    INTERNAL_AUDIT_ROLES,
    _check_district_jurisdiction,
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
    generate_draft_court_pdf,
    prepare_submission_package,
    record_external_filing,
    can_view_internal_audit_notes,
)
from app.models.domain import AuditAction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Document Workspace"])


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


class RequestRevisionsRequest(BaseModel):
    reason: str
    instructions: Optional[str] = None


class PackagePrepareRequest(BaseModel):
    exhibits: Optional[List[str]] = None


class RecordFilingRequest(BaseModel):
    filing_reference: str
    filing_date: Optional[str] = None
    court_name: Optional[str] = None


class DelegationCreateRequest(BaseModel):
    granted_to_user_id: str
    granted_to_role: str = "DLSA_OFFICER"
    capability: str = "CAN_INITIATE_DOCUMENT_DRAFT"
    allowed_document_types: List[str] = ["*"]
    allowed_case_scope: List[str] = ["*"]
    valid_from: Optional[str] = None
    valid_until: str
    reason: str
    organization_id: Optional[str] = None
    jurisdiction: Optional[str] = "National / BNSS 2023"


class DelegationRevokeRequest(BaseModel):
    reason: Optional[str] = "Delegation revoked by supervisory authority."


class DocumentRequisitionRequest(BaseModel):
    case_id: str
    template_id: Optional[str] = "tmpl_bnss_479_bail_v1"
    document_type: Optional[str] = "BAIL_APPLICATION"
    urgency: Optional[str] = "NORMAL"
    reason: str
    missing_prerequisites: Optional[List[str]] = []
    assigned_counsel_id: Optional[str] = None
    assigned_counsel_name: Optional[str] = None



# ── Template Management Endpoints ────────────────────────────────────────────

@router.get("/templates")
def list_templates(
    doc_type: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
):
    """List available document templates. Returns global templates + user organization templates."""
    authorize_document_action(current_user, DocumentAction.VIEW_TEMPLATE)
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
    authorize_document_action(current_user, DocumentAction.VIEW_TEMPLATE, template_id=template_id)
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
    authorize_document_action(current_user, DocumentAction.MAINTAIN_TEMPLATE)

    user_org = getattr(current_user, "org_id", "GLOBAL_DEFAULT")
    if req.organization_id and req.organization_id != user_org and current_user.role != Role.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Gov Admin can only create templates for their own organization.",
        )
    org_id = req.organization_id or user_org
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
    authorize_document_action(current_user, DocumentAction.MAINTAIN_TEMPLATE, template_id=template_id)

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
    authorize_document_action(current_user, DocumentAction.VIEW_DRAFT, case_id=case_id)
    drafts = list_legal_document_drafts_for_case(case_id)
    return {"case_id": case_id, "drafts": drafts, "total": len(drafts)}


@router.get("/drafts/diff")
def get_explicit_drafts_diff(
    draft_id_a: Optional[str] = Query(None, description="First or prior draft ID"),
    draft_id_b: Optional[str] = Query(None, description="Second or current draft ID"),
    draft_a_id: Optional[str] = Query(None, description="First or prior draft ID alias"),
    draft_b_id: Optional[str] = Query(None, description="Second or current draft ID alias"),
    current_user: AuthUser = Depends(get_current_user),
):
    """Compute line-by-line diff between two explicit draft IDs."""
    a_id = draft_id_a or draft_a_id
    b_id = draft_id_b or draft_b_id
    if not a_id or not b_id:
        raise HTTPException(status_code=400, detail="Query parameters 'draft_id_a' and 'draft_id_b' are required.")

    _, draft_a = authorize_document_action(current_user, DocumentAction.DIFF_DRAFT, draft_id=a_id)
    _, draft_b = authorize_document_action(current_user, DocumentAction.DIFF_DRAFT, draft_id=b_id)

    diff_result = compute_draft_diff(draft_a.get("content_text", ""), draft_b.get("content_text", ""))
    return {
        "draft_id": draft_b.get("draft_id"),
        "base_label": f"Version {draft_a.get('version_number', 1)} ({draft_a.get('status')})",
        "current_label": f"Version {draft_b.get('version_number', 1)} ({draft_b.get('status')})",
        **diff_result,
    }


@router.get("/drafts/{draft_id}")
def get_draft_detail(
    draft_id: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve complete draft record with snapshot facts, citations, warnings, and comments."""
    _, draft = authorize_document_action(current_user, DocumentAction.VIEW_DRAFT, draft_id=draft_id)
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
    case, _ = authorize_document_action(
        current_user,
        DocumentAction.INITIATE_DRAFT,
        case_id=req.case_id,
        template_id=req.template_id,
    )

    case_data = case if isinstance(case, dict) else (
        case.model_dump() if hasattr(case, "model_dump") else case.__dict__
    )

    seed_default_templates()
    template = get_document_template_by_id(req.template_id or "tmpl_bnss_479_bail_v1")
    if not template:
        template = DEFAULT_TEMPLATES[0]

    # Retrieve statutory authority
    retrieved_sources: List[Dict[str, Any]] = []
    try:
        from app.agents.retrieval_agent import retrieve_statutes
        from app.models.schemas import CaseRecord
        case_rec = CaseRecord(**case_data)
        ret_res = retrieve_statutes(case_rec)
        retrieved_text = ret_res.get("retrieved_text", "")
        if retrieved_text:
            retrieved_sources.append({
                "citation_key": "BNSS_479",
                "citation": "Section 479 BNSS, 2023",
                "title": "Section 479 BNSS, 2023",
                "statute_text": retrieved_text,
                "excerpt": retrieved_text[:500],
            })
    except Exception as e:
        logger.warning(f"Statutory retrieval failed or unavailable: {e}")

    # Prepare Case Facts Snapshot (STRICT ANTI-FABRICATION: no invented placeholders)
    accused_name = case_data.get("name") or case_data.get("accused_name")
    court_name = case_data.get("court_name")
    district = case_data.get("district")
    fir_number = case_data.get("fir_number") or case_data.get("fir_no")
    police_station = case_data.get("police_station")
    sections = case_data.get("offense_sections")
    custody_days = case_data.get("custody_days")
    max_days = case_data.get("max_sentence_days_for_offense")
    advocate_name = case_data.get("assigned_lawyer") or case_data.get("assigned_advocate") or current_user.full_name
    parent_name = case_data.get("parent_name") or case_data.get("relative_name")
    arrest_date = case_data.get("arrest_date")
    jail_location = case_data.get("jail_location")

    # Deterministic Rule Result
    is_repeat = bool(case_data.get("urgency_flags", {}).get("repeat_offender") if isinstance(case_data.get("urgency_flags"), dict) else False)
    threshold_fraction = "1/2" if is_repeat else "1/3"
    threshold_days = int(max_days / 2) if (is_repeat and max_days is not None) else (int(max_days / 3) if max_days is not None else None)
    is_eligible = (custody_days >= threshold_days) if (custody_days is not None and threshold_days is not None) else False

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

    # Snapshot of Source Documents (STRICT NO FAKE PROVENANCE)
    source_docs = []
    for d_name in case_data.get("present_docs", []):
        source_docs.append({
            "document_type": d_name,
            "file_name": f"{d_name}_{req.case_id}.pdf",
            "is_verified": bool(case_data.get("evidence_verified")),
            "verification_authority": "MANUAL_CASE_INTAKE",
        })

    # Render Template
    render_ctx = {
        "court_name": court_name.upper() if court_name else None,
        "district": district.upper() if district else None,
        "filing_year": datetime.date.today().year,
        "fir_number": fir_number,
        "police_station": police_station,
        "offense_sections": ", ".join(sections) if isinstance(sections, list) else sections,
        "accused_name": accused_name.upper() if accused_name else None,
        "arrest_date": arrest_date,
        "custody_days": custody_days,
        "jail_location": jail_location,
        "max_sentence_days_for_offense": max_days,
        "threshold_days": threshold_days,
        "statutory_threshold_fraction": threshold_fraction,
        "assigned_lawyer": advocate_name.upper() if advocate_name else None,
        "current_date": datetime.date.today().strftime("%d-%m-%Y"),
        "case_id": req.case_id,
        "parent_or_guardian_name": parent_name,
    }

    rendered_text, missing_fields = render_template(template["content_template"], render_ctx)

    # Concurrency-safe version allocation
    next_ver = allocate_next_draft_version(req.case_id, "bail_draft_01")
    draft_id = f"draft_{uuid.uuid4().hex[:12]}"

    prompt_ver = f"sys_v2.1_tmpl_{template['id']}_v{template['version']}"
    ai_model = "Groq/LLaMA-3-70b + Governed BNSS Engine"

    # Identify citations grounded in template statutory grounds
    source_citations = [
        {"section": "Section 479", "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023", "relevance": "Statutory Bail Ground"},
        {"section": "Article 21", "statute": "Constitution of India", "relevance": "Constitutional Speedy Justice Right"},
    ]

    unresolved_warnings = []
    if "custody_certificate" not in [str(d).lower() for d in case_data.get("present_docs", [])]:
        unresolved_warnings.append("Custody Certificate has not been uploaded. Grounding is tentative until prison certificate is received.")

    # Create Draft Record
    draft_record = {
        "draft_id": draft_id,
        "case_id": req.case_id,
        "artifact_id": "bail_draft_01",
        "organization_id": getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
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
            artifact_type="BAIL_APPLICATION",
            content_text=rendered_text,
            actor=current_user,
            is_ai_generated=True,
            ai_model_name=ai_model,
        )
    except Exception as e:
        logger.warning(f"WorkflowService artifact sync on draft creation: {e}")

    # Record immutable audit event
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
            "readiness_status": readiness["status"],
            "missing_fields": missing_fields,
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
    Update human-edited content in the working draft.
    Preserves original_ai_text untouched.
    Fails if document is formally approved and locked (is_immutable = 1).
    """
    _, draft = authorize_document_action(current_user, DocumentAction.EDIT_DRAFT, draft_id=draft_id)

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
    _, draft = authorize_document_action(current_user, DocumentAction.VIEW_DRAFT, draft_id=draft_id)

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
    _, draft = authorize_document_action(current_user, DocumentAction.COMMENT_DRAFT, draft_id=draft_id)

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
    _, draft = authorize_document_action(current_user, DocumentAction.APPROVE_DRAFT, draft_id=draft_id)

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
    _, draft = authorize_document_action(current_user, DocumentAction.REJECT_DRAFT, draft_id=draft_id)

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


@router.post("/drafts/{draft_id}/request-revisions")
def request_draft_revisions(
    draft_id: str,
    req: RequestRevisionsRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Supervising officer requests revisions on a draft.
    Preserves current version, records directive, creates task for assigned counsel,
    and returns workflow to HUMAN_REVIEW.
    """
    case, draft = authorize_document_action(current_user, DocumentAction.REVISE_DRAFT, draft_id=draft_id)

    if not req.reason or not req.reason.strip():
        raise HTTPException(status_code=400, detail="Revision directives / reason are mandatory.")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Record supervisory comment
    comment_obj = {
        "id": f"comment_{uuid.uuid4().hex[:8]}",
        "author_id": current_user.id,
        "author_name": current_user.full_name or current_user.id,
        "role": current_user.role.value,
        "comment": f"[SUPERVISORY REVISION DIRECTIVE]: {req.reason}",
        "created_at": now_iso,
    }
    comments = draft.get("reviewer_comments", [])
    comments.append(comment_obj)

    update_legal_document_draft(draft_id, {
        "status": "REVISIONS_REQUESTED",
        "reviewer_comments": comments,
        "updated_at": now_iso,
    })

    # Trigger workflow state transition REQUEST_REVISIONS
    from app.workflow.service import WorkflowService
    try:
        WorkflowService.execute_transition(
            case_id=draft["case_id"],
            action="REQUEST_REVISIONS",
            actor=current_user,
            comment=req.reason,
            payload={
                "artifact_id": draft.get("artifact_id", "bail_draft_01"),
                "artifact_version_id": draft_id,
            },
        )
    except Exception as e:
        logger.warning(f"Workflow transition on request_draft_revisions: {e}")

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.UPDATE,
        entity_type="LEGAL_DOCUMENT_DRAFT",
        entity_id=draft_id,
        details={
            "case_id": draft["case_id"],
            "decision": "CHANGES_REQUESTED",
            "reason": req.reason,
            "version_number": draft.get("version_number"),
        },
        organization_id=getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
    )

    updated_draft = get_legal_document_draft(draft_id)
    return {
        **(updated_draft or {}),
        "draft_id": draft_id,
        "case_id": draft["case_id"],
        "status": "REVISIONS_REQUESTED",
        "reason": req.reason,
        "message": "Revision directives recorded. Operational task dispatched to assigned defense counsel.",
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
    _, prior_draft = authorize_document_action(current_user, DocumentAction.REVISE_DRAFT, draft_id=draft_id)

    next_ver = allocate_next_draft_version(prior_draft["case_id"], prior_draft.get("artifact_id", "bail_draft_01"))
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
    authorize_document_action(current_user, DocumentAction.PACKAGE_DRAFT, draft_id=draft_id)
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
    authorize_document_action(current_user, DocumentAction.RECORD_FILING, draft_id=draft_id)
    if not req.filing_reference or not req.filing_reference.strip():
        raise HTTPException(status_code=400, detail="Filing reference (CNR / diary number) is mandatory.")

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
    _, draft = authorize_document_action(current_user, DocumentAction.DIFF_DRAFT, draft_id=draft_id)

    if compare_with == "original":
        base_text = draft.get("original_ai_text", "")
        base_label = "Machine-Generated Original (AI Provisional Draft)"
    else:
        _, other = authorize_document_action(current_user, DocumentAction.DIFF_DRAFT, draft_id=compare_with)
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
    _, draft = authorize_document_action(current_user, DocumentAction.EXPORT_DRAFT, draft_id=draft_id)
    if include_internal_notes:
        authorize_document_action(current_user, DocumentAction.EXPORT_INTERNAL_NOTES, draft_id=draft_id)

    try:
        payload = generate_document_export_payload(
            draft_dict=draft,
            include_internal_notes=include_internal_notes,
            actor=current_user,
        )
        return payload
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/drafts/{draft_id}/export/pdf")
def export_draft_pdf(
    draft_id: str,
    include_internal_notes: bool = Query(False),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Export certified court-grade PDF document (%PDF-1.4).
    Enforces data segregation: internal notes are strictly omitted unless
    include_internal_notes=True AND the user role is authorized.
    """
    _, draft = authorize_document_action(current_user, DocumentAction.EXPORT_DRAFT, draft_id=draft_id)
    if include_internal_notes:
        authorize_document_action(current_user, DocumentAction.EXPORT_INTERNAL_NOTES, draft_id=draft_id)

    try:
        pdf_bytes = generate_draft_court_pdf(
            draft_dict=draft,
            include_internal_notes=include_internal_notes,
            actor=current_user,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    ver = draft.get("version_number", 1)
    case_id = draft.get("case_id", "matter")
    filename = f"Petition_{case_id}_v{ver}.0.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ── Document Preparation Requisition & Delegation Endpoints ─────────────────

@router.post("/drafts/request-preparation", status_code=status.HTTP_201_CREATED)
def request_document_preparation(
    req: DocumentRequisitionRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    DLSA / Supervisory requisition endpoint:
    Routes a formal legal document preparation request to assigned panel counsel.
    Enforces district and organization scoping.
    """
    ALLOWED_REQUISITION_ROLES = {Role.DLSA_OFFICER, Role.SUPERVISING_LEGAL_OFFICER, Role.GOV_ADMIN}
    if current_user.role not in ALLOWED_REQUISITION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{current_user.role.value}' is not authorized to requisition legal document preparation.",
        )

    case = get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{req.case_id}' not found.")

    if current_user.role in (Role.DLSA_OFFICER, Role.SUPERVISING_LEGAL_OFFICER):
        case_org = getattr(case, "organization_id", None) or getattr(case, "org_id", None)
        user_org = getattr(current_user, "org_id", "GLOBAL_DEFAULT")
        if case_org and case_org != "GLOBAL_DEFAULT" and user_org != "GLOBAL_DEFAULT":
            if case_org != user_org:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Case '{req.case_id}' belongs to organization '{case_org}', outside your authorized organization '{user_org}'.",
                )
        if not _check_district_jurisdiction(case, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Case '{req.case_id}' is outside your authorized district jurisdiction.",
            )

    counsel_id = req.assigned_counsel_id or getattr(case, "assigned_lawyer_id", None) or getattr(case, "assigned_lawyer", None)
    counsel_name = req.assigned_counsel_name or getattr(case, "assigned_lawyer", None) or counsel_id or "Assigned Panel Counsel"

    requisition_id = f"req_{uuid.uuid4().hex[:10]}"
    task_id = f"TASK-{req.case_id}-DOC-PREP"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    record = {
        "requisition_id": requisition_id,
        "case_id": req.case_id,
        "template_id": req.template_id or "tmpl_bnss_479_bail_v1",
        "document_type": req.document_type or "BAIL_APPLICATION",
        "requested_by_user_id": current_user.id,
        "requested_by_role": current_user.role.value,
        "assigned_counsel_id": counsel_id,
        "assigned_counsel_name": counsel_name,
        "urgency": req.urgency or "NORMAL",
        "reason": req.reason,
        "missing_prerequisites": req.missing_prerequisites or [],
        "status": "DOCUMENT_PREPARATION_REQUESTED",
        "task_id": task_id,
        "organization_id": getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    store_document_preparation_requisition(record)

    # Insert operational task into task queue for the assigned counsel
    try:
        from app.repositories.task_repository import get_task_repository
        repo = get_task_repository()
        task_data = {
            "id": task_id,
            "case_id": req.case_id,
            "accused_name": getattr(case, "name", ""),
            "task_type": "DRAFT_PETITION",
            "title": f"Draft {req.document_type or 'Bail Petition'} for {getattr(case, 'name', req.case_id)}",
            "description": f"DLSA Preparation Request: {req.reason}",
            "owner_role": "DEFENSE_ADVOCATE",
            "owner_user_id": counsel_id,
            "owner_name": counsel_name,
            "priority": "HIGH" if req.urgency in ("URGENT", "CRITICAL_479") else "MEDIUM",
            "due_date": (datetime.date.today() + datetime.timedelta(days=2)).isoformat(),
            "source": "DLSA_REQUISITION",
            "reason": req.reason,
            "status": "NEW",
            "escalation_path": "SUPERVISING_LEGAL_OFFICER",
            "facility": getattr(case, "jail_location", ""),
            "district": getattr(case, "district", ""),
            "custody_duration_days": getattr(case, "custody_days", 0),
        }
        repo.upsert_task(task_data)
    except Exception as e:
        logger.warning(f"Could not persist operational task for requisition: {e}")

    # Audit log (strictly no full legal document text)
    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.CREATE,
        entity_type="DOCUMENT_PREPARATION_REQUISITION",
        entity_id=requisition_id,
        details={
            "case_id": req.case_id,
            "template_id": req.template_id,
            "urgency": req.urgency,
            "assigned_counsel": counsel_name,
            "missing_prerequisites": req.missing_prerequisites,
        },
        organization_id=getattr(current_user, "org_id", "GLOBAL_DEFAULT"),
    )

    return {
        "status": "DOCUMENT_PREPARATION_REQUESTED",
        "requisition_id": requisition_id,
        "case_id": req.case_id,
        "task_id": task_id,
        "assigned_counsel_id": counsel_id,
        "assigned_counsel_name": counsel_name,
        "urgency": req.urgency,
        "message": f"Document preparation request for {req.document_type} formally routed to assigned counsel {counsel_name}.",
    }


@router.get("/delegations/my-active")
def get_my_active_delegation(
    case_id: Optional[str] = Query(None),
    capability: str = Query("CAN_INITIATE_DOCUMENT_DRAFT"),
    document_type: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Check if the current authenticated user has an active, valid delegation
    for the requested capability, case, and document type.
    """
    user_org = getattr(current_user, "org_id", "GLOBAL_DEFAULT")
    active_delg = find_active_user_delegation(
        user_id=current_user.id,
        capability=capability,
        organization_id=user_org,
        case_id=case_id,
        document_type=document_type,
    )

    return {
        "is_delegated": bool(active_delg),
        "delegation": active_delg,
    }


@router.get("/delegations")
def list_delegations(
    user_id: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: AuthUser = Depends(get_current_user),
):
    """
    List institutional delegations.
    Restricted to supervisory, governance, and audit roles.
    """
    ALLOWED_VIEW_ROLES = {Role.SUPERVISING_LEGAL_OFFICER, Role.GOV_ADMIN, Role.PLATFORM_ADMIN, Role.READ_ONLY_AUDITOR, Role.DLSA_OFFICER}
    if current_user.role not in ALLOWED_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden: Not authorized to view delegations.")

    user_org = getattr(current_user, "org_id", "GLOBAL_DEFAULT")
    delegations = list_institutional_delegations(
        user_id=user_id if current_user.role in (Role.SUPERVISING_LEGAL_OFFICER, Role.GOV_ADMIN, Role.PLATFORM_ADMIN, Role.READ_ONLY_AUDITOR) else current_user.id,
        organization_id=user_org,
        capability=capability,
        status=status_filter,
    )
    return {"delegations": delegations, "total": len(delegations)}


@router.post("/delegations", status_code=status.HTTP_201_CREATED)
def create_delegation(
    req: DelegationCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Grant an explicit, time-bound, scoped institutional delegation.
    Restricted strictly to Supervising Legal Officers and Gov Admins.
    """
    ALLOWED_GRANT_ROLES = {Role.SUPERVISING_LEGAL_OFFICER, Role.GOV_ADMIN}
    if current_user.role not in ALLOWED_GRANT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{current_user.role.value}' cannot grant institutional delegations. Restricted to Supervising Legal Officers and Gov Admins.",
        )

    user_org = getattr(current_user, "org_id", "GLOBAL_DEFAULT")
    if req.organization_id and req.organization_id != user_org and current_user.role != Role.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot create institutional delegations for an external organization.",
        )

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    valid_from = req.valid_from or now_iso
    if req.valid_until <= valid_from:
        raise HTTPException(status_code=400, detail="valid_until must be strictly in the future.")

    delegation_id = f"delg_{uuid.uuid4().hex[:10]}"
    org_id = req.organization_id or user_org

    record = {
        "delegation_id": delegation_id,
        "granted_to_user_id": req.granted_to_user_id,
        "granted_to_role": req.granted_to_role,
        "granted_by_user_id": current_user.id,
        "granted_by_role": current_user.role.value,
        "organization_id": org_id,
        "jurisdiction": req.jurisdiction or "National / BNSS 2023",
        "capability": req.capability,
        "allowed_document_types": req.allowed_document_types,
        "allowed_case_scope": req.allowed_case_scope,
        "valid_from": valid_from,
        "valid_until": req.valid_until,
        "status": "ACTIVE",
        "reason": req.reason,
        "created_at": now_iso,
        "audit_reference": f"ORDER-DLSA-DELG-{datetime.date.today().year}-{uuid.uuid4().hex[:6].upper()}",
    }

    success = store_institutional_delegation(record)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to store institutional delegation.")

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.PRIVILEGE_CHANGE,
        entity_type="INSTITUTIONAL_DELEGATION",
        entity_id=delegation_id,
        details={
            "granted_to_user_id": req.granted_to_user_id,
            "capability": req.capability,
            "valid_until": req.valid_until,
            "allowed_case_scope": req.allowed_case_scope,
        },
        organization_id=org_id,
    )

    return record


@router.post("/delegations/{delegation_id}/revoke")
def revoke_delegation(
    delegation_id: str,
    req: DelegationRevokeRequest,
    current_user: AuthUser = Depends(get_current_user),
):
    """
    Revoke an active institutional delegation immediately.
    Restricted to Supervising Legal Officers and Gov Admins.
    """
    ALLOWED_GRANT_ROLES = {Role.SUPERVISING_LEGAL_OFFICER, Role.GOV_ADMIN}
    if current_user.role not in ALLOWED_GRANT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Supervising Legal Officers and Gov Admins can revoke institutional delegations.",
        )

    existing = get_institutional_delegation(delegation_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Delegation '{delegation_id}' not found.")

    user_org = getattr(current_user, "org_id", "GLOBAL_DEFAULT")
    existing_org = existing.get("organization_id", "GLOBAL_DEFAULT")
    if (
        existing_org != "GLOBAL_DEFAULT"
        and existing_org != user_org
        and current_user.role != Role.PLATFORM_ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot revoke institutional delegations belonging to an external organization.",
        )

    success = revoke_institutional_delegation(delegation_id, current_user.id, req.reason)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to revoke delegation.")

    audit_repo.record(
        actor_id=current_user.id,
        actor_role=current_user.role.value,
        action=AuditAction.PRIVILEGE_CHANGE,
        entity_type="INSTITUTIONAL_DELEGATION",
        entity_id=delegation_id,
        details={"reason": req.reason},
        organization_id=existing.get("organization_id"),
    )

    return {
        "delegation_id": delegation_id,
        "status": "REVOKED",
        "revoked_by": current_user.id,
        "message": "Institutional delegation revoked immediately.",
    }

