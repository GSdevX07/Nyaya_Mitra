"""
test_stage19_auditor_role_hardening.py
======================================
Comprehensive Stage 19 Role Hardening Verification for READ_ONLY_AUDITOR.
Tests institutional oversight, cryptographic ledger inspection, document version/diff viewing,
statutory reporting, mandatory export reason & PII redaction, strict 403 Forbidden denial on
all mutation endpoints across the entire system, and zero-emoji compliance.
"""

import pytest
import datetime
import uuid
import re
import json
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import (
    init_db,
    _MEMORY_CASES,
    get_db_connection,
    store_legal_document_draft,
    store_document_template,
    store_uploaded_document,
    store_document_version,
)
from app.models.schemas import CaseRecord, CaseState

client = TestClient(app)


def _insert_test_case(case_dict: dict) -> CaseRecord:
    cid = case_dict.get("case_id", f"UTP-{uuid.uuid4().hex[:6].upper()}")
    defaults = {
        "case_id": cid,
        "name": f"Undertrial {cid}",
        "prisoner_category": "UNDERTRIAL",
        "legal_code": "BNS_2023",
        "offense_sections": ["Section 303", "Section 479"],
        "arrest_date": "2024-03-01",
        "custody_days": 180,
        "max_sentence_days_for_offense": 730,
        "punishable_by_death_or_life": False,
        "multiple_active_cases": False,
        "required_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "present_docs": ["remand_order", "charge_sheet", "custody_certificate"],
        "urgency_flags": {"age": 32, "health_flag": False, "repeat_offender": False},
        "jail_location": "Tihar Central Jail No. 4",
        "district": "Central Delhi",
        "state": "Delhi",
        "court_name": "Central District Court, Tis Hazari",
        "police_station": "Kotwali",
        "fir_number": "FIR-2024-0101",
        "parent_name": "Harbans Singh",
        "relative_name": "Harbans Singh",
        "relative_relation": "Father",
        "relative_phone": "+91 98765 43210",
        "permanent_address": "House 12, Ward 4, Kotwali, Central Delhi",
        "assignment_status": "ASSIGNED",
        "assigned_lawyer_id": "demo_advocate",
        "assigned_lawyer": "Adv. Rajesh Sharma",
        "data_source_status": "DEMO_SYNTHETIC",
        "status": "SUBMITTED",
        "evidence_verified": True,
        "organization_id": "org_dlsa_central",
    }
    full_dict = {**defaults, **case_dict}
    case_rec = CaseRecord(**full_dict)
    _MEMORY_CASES[case_rec.case_id] = case_rec
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id) VALUES (?, ?, ?, ?, ?)",
        (
            case_rec.case_id,
            json.dumps(case_rec.model_dump()),
            case_rec.status.value if hasattr(case_rec.status, "value") else str(case_rec.status),
            case_rec.assignment_status,
            case_rec.assigned_lawyer_id,
        ),
    )
    conn.commit()
    conn.close()
    return case_rec


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


@pytest.fixture
def auditor_token():
    """Statewide Read-Only Auditor Token."""
    claims = {
        "email": "auditor@delhihc.gov.in",
        "full_name": "High Court Statutory Auditor",
        "district": "All (Statewide)",
        "state_id": "state_delhi",
        "state": "Delhi",
        "scope_type": "STATE",
        "authorized_district_ids": ["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi"],
    }
    return create_access_token(
        subject="demo_auditor",
        role=Role.READ_ONLY_AUDITOR.value,
        org_id="org_slsa_delhi",
        extra_claims=claims,
    )


@pytest.fixture
def district_auditor_token():
    """District-scoped Read-Only Auditor Token."""
    claims = {
        "email": "auditor.central@delhihc.gov.in",
        "full_name": "Central District Auditor",
        "district": "Central Delhi",
        "state_id": "state_delhi",
        "state": "Delhi",
        "scope_type": "DISTRICT",
        "authorized_district_ids": ["Central Delhi"],
    }
    return create_access_token(
        subject="auditor_central_01",
        role=Role.READ_ONLY_AUDITOR.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )


def test_auditor_can_view_audit_events(auditor_token):
    """Auditor can view the immutable cryptographic audit ledger."""
    res = client.get(
        "/audit-events?limit=50",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "events" in data
    assert "total_count" in data
    assert data.get("chain_status") == "CRYPTOGRAPHICALLY_LINKED_SHA256"


def test_auditor_can_verify_audit_ledger_integrity(auditor_token):
    """Auditor can run cryptographic SHA-256 hash chain verification."""
    res = client.get(
        "/audit/verify-integrity?limit=100",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "chain_valid" in data
    assert "total_events_checked" in data
    assert data["chain_valid"] is True


def test_auditor_can_view_audit_exceptions(auditor_token):
    """Auditor can view statutory exceptions and governance bottlenecks."""
    res = client.get(
        "/audit/exceptions",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "exceptions" in data
    assert "total_exceptions" in data


def test_auditor_can_view_statutory_reports(auditor_token):
    """Auditor can access the dedicated statutory audit compliance report."""
    res = client.get(
        "/reports",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "overview" in data
    assert data["overview"].get("report_type") == "STATUTORY_AUDIT_COMPLIANCE_REPORT"
    assert "statutory_compliance" in data


def test_auditor_can_list_cases_with_pii_redacted(auditor_token):
    """Auditor can list cases, but results are projected without sensitive citizen PII."""
    _insert_test_case({"case_id": "UTP-AUDIT-LIST-01", "district": "Central Delhi"})
    res = client.get(
        "/cases",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Auditor gets sanitized audit projections
    first = data[0]
    assert "case_id" in first
    assert "workflow_status" in first
    assert "sla_status" in first
    # Verify no raw sensitive citizen phone number or civilian address is leaked
    assert "relative_phone" not in first
    assert "permanent_address" not in first


def test_auditor_can_view_case_detail_with_pii_redacted(auditor_token):
    """Auditor can inspect a case dossier with civilian PII explicitly redacted."""
    c = _insert_test_case({
        "case_id": "UTP-AUDIT-DETAIL-01",
        "district": "Central Delhi",
        "name": "Secret Undertrial Citizen",
        "relative_name": "Guardian Name",
        "relative_phone": "+91 99999 88888",
        "permanent_address": "Secret Residential Address",
    })
    res = client.get(
        f"/cases/{c.case_id}",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "case" in data
    case_info = data["case"]
    assert case_info["name"] == "[REDACTED - AUDITOR VIEW]"
    assert case_info["relative_name"] == "[REDACTED]"
    assert case_info["relative_phone"] == "[REDACTED]"
    assert case_info["permanent_address"] == "[REDACTED]"
    assert case_info["district"] == "Central Delhi"


def test_auditor_district_scoping_enforced(district_auditor_token):
    """District-scoped auditor cannot access cases outside their district."""
    out_case = _insert_test_case({"case_id": "UTP-OUT-DIST-AUDIT-01", "district": "South Delhi"})
    res = client.get(
        f"/cases/{out_case.case_id}",
        headers={"Authorization": f"Bearer {district_auditor_token}"},
    )
    assert res.status_code == 403
    assert "outside your authorized statutory audit scope" in res.json().get("detail", "")


def test_auditor_can_view_case_timeline(auditor_token):
    """Auditor can view chronological case timeline with data provenance."""
    c = _insert_test_case({"case_id": "UTP-AUDIT-TIME-01", "district": "Central Delhi"})
    res = client.get(
        f"/cases/{c.case_id}/timeline",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "timeline" in data
    assert "data_provenance" in data


def test_auditor_can_view_document_templates(auditor_token):
    """Auditor can view legal templates and template details."""
    res = client.get(
        "/api/documents/templates",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "templates" in data
    assert len(data["templates"]) > 0

    tmpl_id = data["templates"][0]["id"]
    detail_res = client.get(
        f"/api/documents/templates/{tmpl_id}",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert detail_res.status_code == 200


def test_auditor_can_view_document_drafts_and_diffs(auditor_token):
    """Auditor can view draft version histories, draft details, and line-by-line diffs."""
    c = _insert_test_case({"case_id": "UTP-AUDIT-DRAFT-01", "district": "Central Delhi"})
    draft_id_a = f"draft_audit_v1_{uuid.uuid4().hex[:6]}"
    draft_id_b = f"draft_audit_v2_{uuid.uuid4().hex[:6]}"

    store_legal_document_draft({
        "draft_id": draft_id_a,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "DRAFT",
        "content_text": "Original provisional text for bail under Section 479 BNSS.",
        "organization_id": "org_dlsa_central",
        "created_by": "adv_rajesh_sharma",
    })

    store_legal_document_draft({
        "draft_id": draft_id_b,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 2,
        "status": "APPROVED",
        "content_text": "Amended authoritative text for statutory bail under Section 479 BNSS.",
        "organization_id": "org_dlsa_central",
        "created_by": "adv_rajesh_sharma",
    })

    # List drafts
    list_res = client.get(
        f"/api/documents/drafts/case/{c.case_id}",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["drafts"]) >= 2

    # Get single draft detail
    detail_res = client.get(
        f"/api/documents/drafts/{draft_id_b}",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["draft_id"] == draft_id_b

    # Get diff between drafts
    diff_res = client.get(
        f"/api/documents/drafts/diff?draft_id_a={draft_id_a}&draft_id_b={draft_id_b}",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert "diff_lines" in diff_data or "diff" in diff_data or "additions_count" in diff_data


def test_auditor_can_view_document_evidence_chain(auditor_token):
    """Auditor can inspect document evidence provenance chains."""
    c = _insert_test_case({"case_id": "UTP-AUDIT-EVID-01", "district": "Central Delhi"})
    doc_id = store_uploaded_document(
        case_id=c.case_id,
        document_type="custody_certificate",
        file_name="custody_cert.pdf",
        extracted_text="Custody Certificate content",
        custom_text="Custody Certificate content",
        is_handwritten=False,
        ocr_engine="Tesseract",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=1024,
        mime_type="application/pdf",
        document_status="VERIFIED",
    )
    store_document_version(
        document_id=doc_id,
        version_number=1,
        parent_version_id=None,
        processing_status="SUCCESS",
        ocr_engine="Tesseract",
        ocr_confidence=0.98,
        is_handwritten=False,
        manual_verification_required=False,
        needs_human_verification_reason=None,
        raw_text="Custody Certificate content",
        normalized_text="Custody Certificate clean text",
        classification="custody_certificate",
        extracted_facts={"custody_days": 180},
        rag_citations=[],
        assessment_summary={"status": "VERIFIED"},
        processed_by="demo_supervisor",
        processing_time_ms=120,
    )

    res = client.get(
        f"/documents/{doc_id}/evidence-chain",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 200
    assert "provenance" in res.json() or "chain" in res.json() or "document_id" in res.json()


def test_auditor_can_verify_citations_and_evaluate_knowledge(auditor_token):
    """Auditor can run read-only citation verification and retrieval evaluation benchmark."""
    c = _insert_test_case({"case_id": "UTP-AUDIT-CIT-01", "district": "Central Delhi"})
    verify_res = client.post(
        "/api/legal-knowledge/verify-citations",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "draft_statement": "An undertrial is eligible for mandatory bail upon serving one-third sentence under Section 479 BNSS.",
            "case_id": c.case_id,
        },
    )
    assert verify_res.status_code == 200
    assert "grounding_score" in verify_res.json() or "message" in verify_res.json()

    eval_res = client.get(
        "/api/legal-knowledge/evaluate",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert eval_res.status_code == 200


def test_auditor_can_export_audit_ledger_with_substantive_reason(auditor_token):
    """Auditor can export the audit ledger when a substantive reason is provided."""
    res = client.post(
        "/audit/export",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "export_reason": "High Court Registry Annual Statutory Compliance Audit 2026",
            "format": "JSON",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "artifact_sha256" in data
    assert len(data["artifact_sha256"]) == 64
    assert data["export_reason"] == "High Court Registry Annual Statutory Compliance Audit 2026"


def test_auditor_export_audit_ledger_rejects_empty_reason(auditor_token):
    """Auditor export without a substantive reason (<5 chars) is rejected with 422."""
    res = client.post(
        "/audit/export",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "export_reason": "   ",
            "format": "JSON",
        },
    )
    assert res.status_code in (400, 422)


def test_auditor_analytics_export_masks_pii(auditor_token):
    """Analytics export by auditor enforces PII masking and records SHA-256 seal."""
    res = client.post(
        "/api/analytics/export",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "report_type": "CASES_LEDGER",
            "format": "JSON",
            "purpose": "Quarterly Detention Period Audit Inspection",
            "include_pii": True,  # Even if requested, auditor must NOT receive unmasked PII
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["data_minimized"] is True
    assert "checksum_sha256" in data


# ── Strict 403 Forbidden Denial on All Mutation Endpoints ────────────────────

def test_auditor_denied_generate_draft(auditor_token):
    """Auditor cannot generate or initiate legal drafts."""
    c = _insert_test_case({"case_id": "UTP-MUT-01", "district": "Central Delhi"})
    res = client.post(
        "/api/documents/drafts/generate",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"case_id": c.case_id, "template_id": "tmpl_bnss_479_bail_v1"},
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json().get("detail", "") or "cannot mutate legal drafts" in res.json().get("detail", "")


def test_auditor_denied_edit_draft(auditor_token):
    """Auditor cannot edit legal drafts."""
    c = _insert_test_case({"case_id": "UTP-MUT-02", "district": "Central Delhi"})
    draft_id = f"draft_mut_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "DRAFT",
        "content_text": "Text",
        "organization_id": "org_dlsa_central",
    })
    res = client.put(
        f"/api/documents/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"content_text": "Mutated text by auditor"},
    )
    assert res.status_code == 403


def test_auditor_denied_comment_draft(auditor_token):
    """Auditor cannot comment on legal drafts."""
    c = _insert_test_case({"case_id": "UTP-MUT-03", "district": "Central Delhi"})
    draft_id = f"draft_mut_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "DRAFT",
        "content_text": "Text",
        "organization_id": "org_dlsa_central",
    })
    res = client.post(
        f"/api/documents/drafts/{draft_id}/comments",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"comment": "Auditor comment"},
    )
    assert res.status_code == 403


def test_auditor_denied_approve_draft(auditor_token):
    """Auditor cannot approve legal document drafts or case dossiers."""
    c = _insert_test_case({"case_id": "UTP-MUT-04", "district": "Central Delhi"})
    draft_id = f"draft_mut_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "DRAFT",
        "content_text": "Text",
        "organization_id": "org_dlsa_central",
    })
    res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"comment": "Auditor approval attempt"},
    )
    assert res.status_code == 403

    case_appr_res = client.post(
        f"/cases/{c.case_id}/approve",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"notes": "Auditor approval attempt"},
    )
    assert case_appr_res.status_code == 403


def test_auditor_denied_reject_draft(auditor_token):
    """Auditor cannot reject legal document drafts."""
    c = _insert_test_case({"case_id": "UTP-MUT-05", "district": "Central Delhi"})
    draft_id = f"draft_mut_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "DRAFT",
        "content_text": "Text",
        "organization_id": "org_dlsa_central",
    })
    res = client.post(
        f"/api/documents/drafts/{draft_id}/reject",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"reason": "Auditor rejection"},
    )
    assert res.status_code == 403


def test_auditor_denied_revise_draft(auditor_token):
    """Auditor cannot request revisions or revise drafts."""
    c = _insert_test_case({"case_id": "UTP-MUT-06", "district": "Central Delhi"})
    draft_id = f"draft_mut_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "DRAFT",
        "content_text": "Text",
        "organization_id": "org_dlsa_central",
    })
    res = client.post(
        f"/api/documents/drafts/{draft_id}/request-revisions",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"reason": "Auditor revision request", "instructions": "Revise"},
    )
    assert res.status_code == 403


def test_auditor_denied_package_draft(auditor_token):
    """Auditor cannot prepare submission packages."""
    c = _insert_test_case({"case_id": "UTP-MUT-07", "district": "Central Delhi"})
    draft_id = f"draft_mut_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "APPROVED",
        "content_text": "Text",
        "organization_id": "org_dlsa_central",
    })
    res = client.post(
        f"/api/documents/drafts/{draft_id}/package",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"exhibits": []},
    )
    assert res.status_code == 403


def test_auditor_denied_record_filing(auditor_token):
    """Auditor cannot record filings or file in court."""
    c = _insert_test_case({"case_id": "UTP-MUT-08", "district": "Central Delhi"})
    draft_id = f"draft_mut_{uuid.uuid4().hex[:6]}"
    store_legal_document_draft({
        "draft_id": draft_id,
        "case_id": c.case_id,
        "template_id": "tmpl_bnss_479_bail_v1",
        "version_number": 1,
        "status": "APPROVED",
        "content_text": "Text",
        "organization_id": "org_dlsa_central",
    })
    res = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"filing_reference": "FIL-9999", "court_name": "Tis Hazari"},
    )
    assert res.status_code == 403

    case_file_res = client.post(
        f"/cases/{c.case_id}/file",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"court_filing_number": "FIL-9999"},
    )
    assert case_file_res.status_code == 403


def test_auditor_denied_maintain_templates(auditor_token):
    """Auditor cannot create or update legal document templates."""
    create_res = client.post(
        "/api/documents/templates",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "name": "Auditor Template",
            "doc_type": "BAIL_PETITION",
            "statutory_ground": "Section 479",
            "content_template": "Template text",
        },
    )
    assert create_res.status_code == 403

    update_res = client.put(
        "/api/documents/templates/tmpl_bnss_479_bail_v1",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"name": "Updated Name"},
    )
    assert update_res.status_code == 403


def test_auditor_denied_create_delegation(auditor_token):
    """Auditor cannot grant institutional capability delegations."""
    res = client.post(
        "/api/documents/delegations",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "granted_to_user_id": "adv_test_01",
            "granted_to_role": "DEFENSE_ADVOCATE",
            "capability": "CAN_INITIATE_DOCUMENT_DRAFT",
            "valid_until": "2026-12-31T23:59:59Z",
            "reason": "Test delegation",
        },
    )
    assert res.status_code == 403


def test_auditor_denied_upload_and_assess_documents(auditor_token):
    """Auditor cannot upload or assess documents."""
    c = _insert_test_case({"case_id": "UTP-MUT-09", "district": "Central Delhi"})
    upload_res = client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {auditor_token}"},
        data={"case_id": c.case_id, "document_type": "charge_sheet", "custom_text": "Sample text"},
    )
    assert upload_res.status_code == 403

    assess_res = client.post(
        "/documents/assess",
        headers={"Authorization": f"Bearer {auditor_token}"},
        data={"case_id": c.case_id, "document_name": "charge_sheet.pdf", "provided_text": "Sample text"},
    )
    assert assess_res.status_code == 403


def test_auditor_denied_verify_and_review_documents(auditor_token):
    """Auditor cannot verify or review documents."""
    c = _insert_test_case({"case_id": "UTP-MUT-10", "district": "Central Delhi"})
    doc_id = store_uploaded_document(
        case_id=c.case_id,
        document_type="charge_sheet",
        file_name="charge_sheet.pdf",
        extracted_text="Charge Sheet",
        custom_text="Charge Sheet",
        is_handwritten=False,
        ocr_engine="Tesseract",
        file_hash="dummyhash",
        file_size_bytes=1024,
        mime_type="application/pdf",
        document_status="PENDING_VERIFICATION",
    )
    review_res = client.post(
        f"/documents/{doc_id}/review",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert review_res.status_code == 403

    verify_res = client.post(
        f"/documents/{doc_id}/verify",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert verify_res.status_code == 403


def test_auditor_denied_correct_field_and_reprocess(auditor_token):
    """Auditor cannot correct document fields or reprocess documents."""
    c = _insert_test_case({"case_id": "UTP-MUT-11", "district": "Central Delhi"})
    doc_id = store_uploaded_document(
        case_id=c.case_id,
        document_type="charge_sheet",
        file_name="charge_sheet.pdf",
        extracted_text="Charge Sheet",
        custom_text="Charge Sheet",
        is_handwritten=False,
        ocr_engine="Tesseract",
        file_hash="dummyhash",
        file_size_bytes=1024,
        mime_type="application/pdf",
        document_status="PENDING_VERIFICATION",
    )
    correct_res = client.post(
        f"/documents/{doc_id}/correct-field",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"field_name": "custody_days", "corrected_value": 180, "reason": "Audit fix attempt"},
    )
    assert correct_res.status_code == 403

    reproc_res = client.post(
        f"/documents/{doc_id}/reprocess",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"reason": "Audit reprocess attempt"},
    )
    assert reproc_res.status_code == 403


def test_auditor_denied_assign_and_take_lawyer(auditor_token):
    """Auditor cannot assign, take, or decline lawyers."""
    c = _insert_test_case({"case_id": "UTP-MUT-12", "district": "Central Delhi"})
    assign_res = client.post(
        f"/cases/{c.case_id}/assign-lawyer",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"lawyer_id": "demo_advocate", "lawyer_name": "Adv. Rajesh Sharma"},
    )
    assert assign_res.status_code == 403

    take_res = client.post(
        f"/cases/{c.case_id}/take",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert take_res.status_code == 403

    decline_res = client.post(
        f"/cases/{c.case_id}/decline",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"reason": "Auditor decline attempt"},
    )
    assert decline_res.status_code == 403


def test_auditor_denied_trigger_actions(auditor_token):
    """Auditor cannot trigger operational actions from the queue."""
    res = client.post(
        "/actions/trigger?action_id=ACT-UTP-0001-BAIL",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403


def test_auditor_denied_custody_and_fir_intake(auditor_token):
    """Auditor cannot perform custody intake, FIR intake, or custody profile updates."""
    intake_res = client.post(
        "/cases/intake-custody",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "accused_name": "Inmate Test",
            "prison_id": "PRIS-9999",
            "jail_facility": "Tihar Central Jail No. 4",
            "admission_date": "2024-03-01",
        },
    )
    assert intake_res.status_code == 403

    fir_res = client.post(
        "/cases/fir-intake",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "fir_number": "FIR-9999",
            "police_station": "Kotwali",
            "sections": ["Section 303"],
        },
    )
    assert fir_res.status_code == 403


def test_auditor_denied_mutate_tasks(auditor_token):
    """Auditor cannot mutate operational tasks or execute bulk transitions."""
    patch_res = client.patch(
        "/tasks/TASK-UTP-0001-JAIL-VERIF",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"status": "COMPLETED"},
    )
    assert patch_res.status_code == 403

    bulk_res = client.post(
        "/tasks/bulk-action",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"action": "MARK_REVIEWED", "task_ids": ["TASK-UTP-0001-JAIL-VERIF"]},
    )
    assert bulk_res.status_code == 403


def test_auditor_denied_mutate_rule_lifecycle(auditor_token):
    """Auditor cannot transition legal rule lifecycles."""
    res = client.post(
        "/rules/BNSS_479_FIRST_TIME/lifecycle",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={"target_state": "LEGAL_REVIEW", "notes": "Auditor rule transition attempt"},
    )
    assert res.status_code == 403


def test_auditor_denied_clear_notifications(auditor_token):
    """Auditor cannot delete or clear notifications or dispatch notifications."""
    del_res = client.delete(
        "/notifications",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert del_res.status_code == 403

    clear_res = client.post(
        "/notifications/clear",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert clear_res.status_code == 403

    disp_res = client.post(
        "/api/notifications/dispatch",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "event_type": "APPROACHING_CUSTODY_THRESHOLD",
            "case_id": "UTP-0001",
            "recipient": "test@test.com",
            "target_role": "ALL",
            "priority": "HIGH",
            "payload": {"message": "Test notification"},
        },
    )
    assert disp_res.status_code == 403


def test_auditor_denied_schedule_reports(auditor_token):
    """Auditor cannot create recurring report schedules or trigger their execution."""
    create_res = client.post(
        "/api/analytics/schedules",
        headers={"Authorization": f"Bearer {auditor_token}"},
        json={
            "title": "Auditor Schedule",
            "report_type": "CASES_LEDGER",
            "frequency": "WEEKLY",
            "recipients": ["auditor@demo.nyayamitra.in"],
        },
    )
    assert create_res.status_code == 403

    trig_res = client.post(
        "/api/analytics/schedules/sched_test_01/trigger",
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert trig_res.status_code == 403


def test_zero_emoji_compliance(auditor_token):
    """Verify that all responses returned to READ_ONLY_AUDITOR contain zero emojis."""
    emoji_pattern = re.compile(
        r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]",
        flags=re.UNICODE,
    )

    endpoints = [
        "/audit-events",
        "/audit/verify-integrity",
        "/audit/exceptions",
        "/reports",
        "/cases",
        "/api/documents/templates",
    ]

    for ep in endpoints:
        res = client.get(ep, headers={"Authorization": f"Bearer {auditor_token}"})
        assert res.status_code == 200, f"Endpoint {ep} failed with {res.status_code}"
        text_payload = res.text
        match = emoji_pattern.search(text_payload)
        assert match is None, f"Emoji detected in {ep} response payload: {match.group(0)}"
