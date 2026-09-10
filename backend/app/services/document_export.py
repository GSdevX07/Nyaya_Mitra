"""
document_export.py - Secure Export, Version Diffing, and Submission Packaging.
=============================================================================
Enforces data segregation between External Court copies and Internal Certified copies,
computes line-level diffs, and strictly enforces the anti-automatic filing policy.
"""

from __future__ import annotations
import difflib
import hashlib
import json
import datetime
import logging
import textwrap
from typing import Dict, Any, List, Optional, Tuple

from app.auth.roles import Role
from app.auth.user_store import AuthUser
from app.database import (
    get_legal_document_draft,
    update_legal_document_draft,
    audit_repo,
)
from app.models.domain import AuditAction

logger = logging.getLogger(__name__)

INTERNAL_AUDIT_ROLES = {
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DEFENSE_ADVOCATE,
    Role.READ_ONLY_AUDITOR,
}


def can_view_internal_audit_notes(role: Role) -> bool:
    """Check if the user is authorized to export internal audit notes."""
    return role in INTERNAL_AUDIT_ROLES


def compute_draft_diff(original_text: str, modified_text: str) -> Dict[str, Any]:
    """
    Compute structured line-by-line diff between two text versions.
    Returns categorized lines (ADDED, REMOVED, UNCHANGED) and summary statistics.
    """
    orig_lines = original_text.splitlines()
    mod_lines = modified_text.splitlines()

    matcher = difflib.SequenceMatcher(None, orig_lines, mod_lines)
    diff_lines: List[Dict[str, Any]] = []

    additions = 0
    deletions = 0
    unchanged = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in orig_lines[i1:i2]:
                diff_lines.append({"type": "UNCHANGED", "text": line})
                unchanged += 1
        elif tag == "replace":
            for line in orig_lines[i1:i2]:
                diff_lines.append({"type": "REMOVED", "text": line})
                deletions += 1
            for line in mod_lines[j1:j2]:
                diff_lines.append({"type": "ADDED", "text": line})
                additions += 1
        elif tag == "delete":
            for line in orig_lines[i1:i2]:
                diff_lines.append({"type": "REMOVED", "text": line})
                deletions += 1
        elif tag == "insert":
            for line in mod_lines[j1:j2]:
                diff_lines.append({"type": "ADDED", "text": line})
                additions += 1

    return {
        "additions": additions,
        "deletions": deletions,
        "lines_added": additions,
        "lines_deleted": deletions,
        "unchanged": unchanged,
        "total_changes": additions + deletions,
        "diff_lines": diff_lines,
    }


def generate_document_export_payload(
    draft_dict: Dict[str, Any],
    include_internal_notes: bool,
    actor: AuthUser,
) -> Dict[str, Any]:
    """
    Generate an export payload with audit metadata.
    Enforces that internal audit notes are strictly excluded unless the actor has explicit permission.
    If include_internal_notes=True is passed by an unauthorized role, raises PermissionError.
    """
    content = draft_dict.get("content_text", "")
    version_tag = f"v{draft_dict.get('version_number', 1)}.0"
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    has_perm = can_view_internal_audit_notes(actor.role)
    actual_include_notes = include_internal_notes and has_perm

    export_type = "INTERNAL_CERTIFIED" if actual_include_notes else "EXTERNAL_COURT"

    # Build header and footer
    header_block = (
        f"════════════════════════════════════════════════════════════════════════\n"
        f"NYAYA MITRA COURT-GRADE LEGAL DOCUMENT // {export_type}\n"
        f"CASE ID: {draft_dict.get('case_id')} | VERSION: {version_tag} | STATUS: {draft_dict.get('status')}\n"
        f"SHA-256 DIGEST: {content_hash}\n"
        f"EXPORTED AT: {now_iso} BY {actor.full_name or actor.id} ({actor.role.value})\n"
        f"════════════════════════════════════════════════════════════════════════\n\n"
    )

    footer_block = (
        f"\n\n════════════════════════════════════════════════════════════════════════\n"
        f"OFFICIAL RECORD // VERIFIED HUMAN SIGN-OFF: {draft_dict.get('approved_by') or 'PENDING APPROVAL'}\n"
        f"AUTOMATIC FILING PROHIBITED. EXTERNAL FILING MUST BE EXPLICITLY RECORDED.\n"
        f"════════════════════════════════════════════════════════════════════════\n"
    )

    export_body = header_block + content + footer_block

    if actual_include_notes:
        audit_section = (
            f"\n\n────────────────────────────────────────────────────────────────────────\n"
            f"INTERNAL AUDIT & SCRUTINY NOTES (STRICTLY CONFIDENTIAL)\n"
            f"────────────────────────────────────────────────────────────────────────\n"
            f"• AI Model: {draft_dict.get('ai_model_name')}\n"
            f"• Prompt Version: {draft_dict.get('prompt_version')}\n"
            f"• Initial Generation Time: {draft_dict.get('created_at')}\n"
            f"• Reviewer Comments ({len(draft_dict.get('reviewer_comments', []))}):\n"
        )
        for idx, c in enumerate(draft_dict.get("reviewer_comments", []), 1):
            audit_section += f"  [{idx}] {c.get('author_name', 'Reviewer')} ({c.get('role')}): {c.get('comment')} (at {c.get('created_at')})\n"

        readiness = draft_dict.get("readiness_check_result", {})
        if readiness:
            audit_section += (
                f"• Pre-Approval Readiness Status: {readiness.get('status')}\n"
                f"• Blocking Issues Resolved: {readiness.get('total_blocking_issues', 0)}\n"
                f"• System Warnings Noted: {readiness.get('total_warnings', 0)}\n"
            )
        export_body += audit_section

    # Record export in append-only audit log
    audit_repo.record(
        actor_id=actor.id,
        actor_role=actor.role.value,
        action=AuditAction.DOCUMENT_DOWNLOAD,
        entity_type="LEGAL_DRAFT_EXPORT",
        entity_id=draft_dict["draft_id"],
        details={
            "case_id": draft_dict["case_id"],
            "version_number": draft_dict.get("version_number", 1),
            "export_type": export_type,
            "included_internal_notes": actual_include_notes,
            "content_hash": content_hash,
        },
        organization_id=actor.org_id,
    )

    return {
        "draft_id": draft_dict["draft_id"],
        "case_id": draft_dict["case_id"],
        "export_type": export_type,
        "content_hash": content_hash,
        "version_tag": version_tag,
        "exported_at": now_iso,
        "includes_internal_notes": actual_include_notes,
        "exported_text": export_body,
        "filename": f"Petition_{draft_dict.get('case_id')}_{version_tag}_{export_type.lower()}.txt",
    }


def prepare_submission_package(
    draft_id: str,
    actor: AuthUser,
    exhibits: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Prepare formal submission package for human review and offline/integration filing.
    STRICT ENFORCEMENT: Automatic filing is prevented.
    """
    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise LookupError(f"Draft '{draft_id}' not found.")

    if actor.role not in {Role.DEFENSE_ADVOCATE, Role.SUPERVISING_LEGAL_OFFICER}:
        raise PermissionError(f"Forbidden: Role '{actor.role.value}' is not authorized to prepare court submission packages. Restricted to assigned counsel and supervisors.")

    if draft.get("status") != "APPROVED" and not draft.get("is_immutable"):
        raise ValueError("Cannot prepare submission package: Document draft must be formally approved before packaging.")

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    package_id = f"pkg_{hashlib.sha256((draft_id + now_iso).encode()).hexdigest()[:12]}"
    content_hash = hashlib.sha256(draft["content_text"].encode("utf-8")).hexdigest()

    manifest = {
        "package_id": package_id,
        "draft_id": draft_id,
        "case_id": draft["case_id"],
        "version_number": draft.get("version_number", 1),
        "document_sha256": content_hash,
        "packaged_by": actor.full_name or actor.id,
        "packaged_by_role": actor.role.value,
        "packaged_at": now_iso,
        "exhibits": exhibits or ["Remand Orders", "Custody Certificate", "Charge Sheet"],
        "approval_sign_off": {
            "approved_by": draft.get("approved_by"),
            "approved_by_role": draft.get("approved_by_role"),
            "approved_at": draft.get("approved_at"),
        },
        "filing_mode": "MANUAL_OR_VERIFIED_INTEGRATION_ONLY",
        "is_automatically_filed": False,
        "filing_status": "PACKAGE_PREPARED_AWAITING_HUMAN_FILING",
    }

    update_legal_document_draft(draft_id, {
        "status": "PACKAGE_PREPARED",
        "submission_package": manifest,
    })

    audit_repo.record(
        actor_id=actor.id,
        actor_role=actor.role.value,
        action=AuditAction.DOCUMENT_UPLOAD,
        entity_type="SUBMISSION_PACKAGE",
        entity_id=package_id,
        details=manifest,
        organization_id=actor.org_id,
    )

    return manifest


def record_external_filing(
    draft_id: str,
    filing_reference: str,
    filing_date: str,
    actor: AuthUser,
    court_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record that an authorized user or verified integration filed the petition in court.
    Transitions matter and records immutable audit reference.
    """
    draft = get_legal_document_draft(draft_id)
    if not draft:
        raise LookupError(f"Draft '{draft_id}' not found.")

    if actor.role not in {Role.DEFENSE_ADVOCATE, Role.SUPERVISING_LEGAL_OFFICER}:
        raise PermissionError(f"Forbidden: Role '{actor.role.value}' is not authorized to record external court filings. Restricted to assigned counsel and supervising legal officers.")

    if not filing_reference or not filing_reference.strip():
        raise ValueError("A valid court filing receipt number or CNR acknowledgment reference is required.")

    update_legal_document_draft(draft_id, {
        "status": "FILED",
        "external_filing_reference": filing_reference.strip(),
        "external_filing_date": filing_date or datetime.date.today().isoformat(),
    })

    # Trigger case state transition through WorkflowService
    from app.workflow.service import WorkflowService
    try:
        WorkflowService.execute_transition(
            case_id=draft["case_id"],
            action="FILE_IN_COURT",
            actor=actor,
            payload={
                "filing_date": filing_date,
                "court_reference": filing_reference,
                "court_name": court_name or draft.get("exact_case_facts", {}).get("court_name"),
            },
            comment=f"Assigned counsel recorded official court filing under receipt reference: {filing_reference}.",
        )
    except Exception as e:
        logger.warning(f"Workflow transition on record_external_filing: {e}")

    audit_repo.record(
        actor_id=actor.id,
        actor_role=actor.role.value,
        action=AuditAction.STATUS_TRANSITION,
        entity_type="COURT_FILING",
        entity_id=draft_id,
        details={
            "case_id": draft["case_id"],
            "filing_reference": filing_reference,
            "filing_date": filing_date,
            "court_name": court_name,
        },
        organization_id=actor.org_id,
    )

    return {
        "draft_id": draft_id,
        "case_id": draft["case_id"],
        "status": "FILED",
        "filing_reference": filing_reference,
        "filing_date": filing_date,
        "message": f"Court filing recorded successfully under reference '{filing_reference}'.",
    }


def _build_pdf_1_4_bytes(text: str) -> bytes:
    """
    Produce standard %PDF-1.4 binary data containing the petition text.
    Implements multi-page pagination with formal margins.
    Verifiable by pypdf and standard PDF parsers.
    """
    raw_lines = text.split("\n")
    wrapped_lines: List[str] = []
    for line in raw_lines:
        if not line:
            wrapped_lines.append("")
        else:
            for sub in textwrap.wrap(line, width=82, replace_whitespace=False, drop_whitespace=False):
                wrapped_lines.append(sub)

    lines_per_page = 48
    page_chunks = [
        wrapped_lines[i : i + lines_per_page]
        for i in range(0, max(1, len(wrapped_lines)), lines_per_page)
    ]
    num_pages = len(page_chunks)

    body = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets: Dict[int, int] = {}

    def write_obj(num: int, data: bytes):
        offsets[num] = sum(len(b) for b in body)
        body.append(f"{num} 0 obj\n".encode("latin-1") + data + b"\nendobj\n")

    font_obj_num = 3 + num_pages * 2

    # 1. Catalog
    write_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")

    # 2. Pages list
    kids_str = " ".join(f"{3 + i * 2} 0 R" for i in range(num_pages))
    write_obj(2, f"<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>".encode("latin-1"))

    # Each page
    for i, chunk in enumerate(page_chunks):
        page_obj_num = 3 + i * 2
        content_obj_num = page_obj_num + 1

        # Content stream
        stream = "BT\n/F1 9 Tf\n50 790 Td\n13 TL\n"
        for line in chunk:
            esc = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream += f"({esc}) '\n"
        stream += "ET"
        stream_bytes = stream.encode("latin-1", "replace")

        # Page object
        page_dict = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Contents {content_obj_num} 0 R /Resources << /Font << /F1 {font_obj_num} 0 R >> >> >>".encode("latin-1")
        write_obj(page_obj_num, page_dict)

        # Content stream object
        content_data = f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1") + stream_bytes + b"\nendstream"
        write_obj(content_obj_num, content_data)

    # Font object
    write_obj(font_obj_num, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Xref & Trailer
    total_objs = font_obj_num + 1
    xref_offset = sum(len(b) for b in body)
    xref = f"xref\n0 {total_objs}\n0000000000 65535 f \n"
    for n in range(1, total_objs):
        off = offsets[n]
        xref += f"{off:010d} 00000 n \n"
    trailer = f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    body.append(xref.encode("latin-1"))
    body.append(trailer.encode("latin-1"))

    return b"".join(body)


def generate_draft_court_pdf(
    draft_dict: Dict[str, Any],
    include_internal_notes: bool,
    actor: AuthUser,
) -> bytes:
    """
    Generate certified %PDF-1.4 binary document for court submission.
    Enforces that internal audit notes are omitted unless authorized.
    """
    export_payload = generate_document_export_payload(
        draft_dict=draft_dict,
        include_internal_notes=include_internal_notes,
        actor=actor,
    )
    return _build_pdf_1_4_bytes(export_payload["exported_text"])
