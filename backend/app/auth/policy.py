"""
auth/policy.py — RBAC + ABAC policy engine for Nyaya Mitra.

The single entry-point is `check_permission(user, action, resource)`.
Resource is a dict with fields like org_id, facility_id, assigned_lawyer_id, case_id, status.
Raises HTTPException 403 on denial.
"""
from __future__ import annotations
from typing import Any

from fastapi import HTTPException, status

from app.auth.roles import Role
from app.auth.user_store import AuthUser

# ── Permission action constants ──────────────────────────────────────────────

CASES_READ_LIST        = "cases:read_list"
CASES_READ_DETAIL      = "cases:read_detail"
CASES_READ_MEDICAL     = "cases:read_medical"
CASES_APPROVE          = "cases:approve"
CASES_ASSIGN_LAWYER    = "cases:assign_lawyer"
CASES_TAKE_OR_DECLINE  = "cases:take_or_decline"
CASES_FILE_IN_COURT    = "cases:file_in_court"
ACCUSED_READ_IDENTITY  = "accused:read_identity"
ACCUSED_UPDATE_IDENTITY= "accused:update_identity"
ACCUSED_SELF_READ      = "accused:self_read"
ACCUSED_FAMILY_READ    = "accused:family_read"
CUSTODY_UPDATE_STATUS  = "custody:update_status"
DOCUMENTS_UPLOAD       = "documents:upload_official"
DOCUMENTS_DOWNLOAD     = "documents:download"
EVIDENCE_VERIFY        = "evidence:verify"
RAG_INGEST             = "rag:ingest"
EXPORT_CASE_FILE       = "export:case_file"
AUDIT_READ             = "audit:read"
INTEGRATION_RUN        = "integration:run"
REPORTS_READ           = "reports:read"
NOTIFICATIONS_READ     = "notifications:read"
ACTIONS_TRIGGER        = "actions:trigger"
USERS_MANAGE           = "users:manage"


def _deny(reason: str = "Access denied.") -> None:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)


def _org_match(user: AuthUser, resource: dict[str, Any]) -> bool:
    if user.role == Role.PLATFORM_ADMIN:
        return True
    res_org = resource.get("org_id") or resource.get("organization_id") or ""
    return not res_org or user.org_id == res_org


def _facility_match(user: AuthUser, resource: dict[str, Any]) -> bool:
    if user.role in (Role.PLATFORM_ADMIN, Role.GOV_ADMIN):
        return True
    fac = resource.get("facility_id") or resource.get("jail_location") or ""
    return not fac or not user.facility_ids or fac in user.facility_ids


def _is_assigned(user: AuthUser, resource: dict[str, Any]) -> bool:
    return resource.get("assigned_lawyer_id") == user.id


def check_permission(
    user: AuthUser,
    action: str,
    resource: dict[str, Any] | None = None,
) -> None:
    """
    Enforce RBAC + ABAC policy.

    Args:
        user: The authenticated user.
        action: One of the action constants above.
        resource: Dict representing the target resource (case, document, etc.).

    Raises:
        HTTPException 403 if the user does not have permission.
    """
    r = resource or {}
    role = user.role

    # ── Platform admin passes everything ──────────────────────────────────────
    if role == Role.PLATFORM_ADMIN:
        return

    # ── Integration service — only allowed actions ────────────────────────────
    if role == Role.INTEGRATION_SERVICE:
        if action == INTEGRATION_RUN:
            return
        _deny("Integration service accounts can only perform integration actions.")

    # ── Read-only auditor ─────────────────────────────────────────────────────
    if role == Role.READ_ONLY_AUDITOR:
        if action in (AUDIT_READ, CASES_READ_LIST, CASES_READ_DETAIL, REPORTS_READ):
            return
        _deny("Read-only auditor cannot perform write operations.")

    # ── Accused user — own case only ──────────────────────────────────────────
    if role == Role.ACCUSED_USER:
        if action == ACCUSED_SELF_READ:
            if user.linked_case_id and r.get("case_id") == user.linked_case_id:
                return
        _deny("Accused users may only view their own case.")

    # ── Family guardian ───────────────────────────────────────────────────────
    if role == Role.FAMILY_GUARDIAN:
        if action == ACCUSED_FAMILY_READ:
            if user.linked_case_id and r.get("case_id") == user.linked_case_id:
                return
        _deny("Family/guardian may only view their linked accused person's case.")

    # ── Controlled external advocate ──────────────────────────────────────────
    if role == Role.CONTROLLED_EXTERNAL_ADVOCATE:
        if action == DOCUMENTS_DOWNLOAD and r.get("explicitly_shared"):
            return
        if action == CASES_READ_DETAIL and r.get("explicitly_shared"):
            return
        _deny("External advocates can only view explicitly shared records.")

    # ── Jail officer ──────────────────────────────────────────────────────────
    if role == Role.JAIL_OFFICER:
        allowed = {CASES_READ_LIST, CASES_READ_DETAIL, ACCUSED_READ_IDENTITY,
                   CUSTODY_UPDATE_STATUS, DOCUMENTS_UPLOAD, NOTIFICATIONS_READ}
        if action not in allowed:
            _deny(f"Jail officers cannot perform action: {action}")
        if action == CUSTODY_UPDATE_STATUS and not _facility_match(user, r):
            _deny("Jail officers can only update custody for their own facility.")
        return

    # ── Police officer ────────────────────────────────────────────────────────
    if role == Role.POLICE_OFFICER:
        allowed = {CASES_READ_LIST, CASES_READ_DETAIL, ACCUSED_READ_IDENTITY,
                   DOCUMENTS_UPLOAD, NOTIFICATIONS_READ}
        if action not in allowed:
            _deny(f"Police officers cannot perform action: {action}")
        if not _org_match(user, r):
            _deny("Police officers can only access records in their district.")
        return

    # ── DLSA officer ──────────────────────────────────────────────────────────
    if role == Role.DLSA_OFFICER:
        allowed = {CASES_READ_LIST, CASES_READ_DETAIL, CASES_READ_MEDICAL,
                   CASES_ASSIGN_LAWYER, ACCUSED_READ_IDENTITY, DOCUMENTS_UPLOAD,
                   DOCUMENTS_DOWNLOAD, NOTIFICATIONS_READ, REPORTS_READ,
                   EVIDENCE_VERIFY}
        if action not in allowed:
            _deny(f"DLSA officers cannot perform action: {action}")
        if action in (CASES_ASSIGN_LAWYER, CASES_READ_MEDICAL) and not _org_match(user, r):
            _deny("DLSA officers can only assign/review cases in their district.")
        return

    # ── Defense advocate ──────────────────────────────────────────────────────
    if role == Role.DEFENSE_ADVOCATE:
        allowed = {CASES_READ_LIST, CASES_READ_DETAIL, CASES_TAKE_OR_DECLINE,
                   DOCUMENTS_DOWNLOAD, NOTIFICATIONS_READ}
        if action not in allowed:
            _deny(f"Defense advocates cannot perform action: {action}")
        if action == CASES_TAKE_OR_DECLINE:
            # Can take AVAILABLE cases or decline their own assigned case
            case_status = r.get("assignment_status", "")
            if case_status != "AVAILABLE" and not _is_assigned(user, r):
                _deny("Advocates can only take AVAILABLE cases or decline their own assigned cases.")
        return

    # ── Supervising legal officer ─────────────────────────────────────────────
    if role == Role.SUPERVISING_LEGAL_OFFICER:
        allowed = {CASES_READ_LIST, CASES_READ_DETAIL, CASES_READ_MEDICAL,
                   CASES_APPROVE, CASES_FILE_IN_COURT, CASES_ASSIGN_LAWYER,
                   DOCUMENTS_DOWNLOAD, DOCUMENTS_UPLOAD, EVIDENCE_VERIFY,
                   EXPORT_CASE_FILE, REPORTS_READ, NOTIFICATIONS_READ, ACTIONS_TRIGGER}
        if action not in allowed:
            _deny(f"Supervising officers cannot perform action: {action}")
        if not _org_match(user, r):
            _deny("Supervising officers can only act within their organization.")
        if action == CASES_FILE_IN_COURT:
            if r.get("status") != "APPROVED_READY_FOR_FILING":
                _deny("Case must be in APPROVED_READY_FOR_FILING status to file.")
        return

    # ── Gov admin ─────────────────────────────────────────────────────────────
    if role == Role.GOV_ADMIN:
        denied = {ACCUSED_SELF_READ, ACCUSED_FAMILY_READ, INTEGRATION_RUN}
        if action in denied:
            _deny(f"Gov admin cannot perform action: {action}")
        if not _org_match(user, r):
            _deny("Gov admin can only access their organization's records.")
        return

    _deny(f"Role {role} does not have permission for action: {action}")
