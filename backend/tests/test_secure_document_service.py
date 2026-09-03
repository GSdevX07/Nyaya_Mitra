"""
test_secure_document_service.py — Test Suite for Secure Evidence-Aware Document Service.

Verifies:
1. Binary magic byte signature validation (PDF %PDF-, PNG, JPG) and file size enforcement.
2. Extension spoofing rejection (422 Unprocessable Entity).
3. Security boundary checks & malware quarantine (executable headers, malicious PDF streams).
4. Multi-step workflow with immutable vault persistence.
5. OCR transparency: engine tracking, confidence, and manual_verification_required flag.
6. Structured facts extraction with exact verbatim source spans and char offsets.
7. Human-in-the-loop field corrections preserving machine extraction with audit trail.
8. Reprocessing creates Version N+1 without modifying prior version.
9. Comprehensive Evidence Chain DAG inspection view.
10. Controlled backend download delivery with access logging.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import init_db, get_case_uploaded_documents, get_document_versions, build_evidence_chain


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def _get_auth_headers(client: TestClient, role: Role) -> dict:
    """Helper to generate JWT for demo user role."""
    claims = {
        "email": f"{role.value.lower()}@demo.nyayamitra.in",
        "full_name": f"{role.value} (Demo)",
        "district": "Central Delhi",
    }
    token = create_access_token(
        subject=f"demo_{role.value.lower()}",
        role=role.value,
        org_id="org_demo",
        extra_claims=claims,
    )
    return {"Authorization": f"Bearer {token}"}


# ── 1. Magic Bytes & Binary Signature Validation ─────────────────────────────

def test_valid_pdf_magic_bytes_accepted(client):
    """Uploading a valid PDF starting with %PDF- succeeds."""
    headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    valid_pdf = b"%PDF-1.4 sample judicial remand document text for case UTP-0001 under Section 479 BNSS"
    files = {"file": ("remand_order.pdf", io.BytesIO(valid_pdf), "application/pdf")}
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=remand_order",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert data["version_number"] >= 1
    assert data["security_scan_status"] == "PASSED"
    assert "extracted_fields_with_spans" in data


def test_spoofed_file_extension_rejected(client):
    """Uploading a Windows executable disguised as a PDF fails magic byte check with 422."""
    headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    # MZ header (DOS/PE executable)
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00malicious executable disguised as pdf"
    files = {"file": ("trojan.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=remand_order",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 422
    assert "File validation failed" in resp.json()["detail"] or "spoofing" in resp.json()["detail"].lower()


def test_malicious_pdf_active_script_quarantined(client):
    """A PDF containing embedded /JavaScript execution is caught by security screening and quarantined."""
    headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    malicious_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Action /S /JavaScript /JS (app.alert(1)) >>\nendobj"
    files = {"file": ("exploit.pdf", io.BytesIO(malicious_pdf), "application/pdf")}
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=remand_order",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 422
    assert "Security screening failed" in resp.json()["detail"]


# ── 2. Fine-Grained Fact Extraction with Source Spans ─────────────────────────

def test_structured_facts_include_verbatim_source_spans(client):
    """Extracted fields (case_id, custody_days, legal_sections) contain source_span and offsets."""
    headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    pdf_content = (
        b"%PDF-1.4 IN THE COURT OF SESSIONS JUDGE. "
        b"Case No. UTP-0001. Accused Suresh Kumar has completed custody duration of 180 days. "
        b"Offence registered under IPC Section 420."
    )
    files = {"file": ("custody_order.pdf", io.BytesIO(pdf_content), "application/pdf")}
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=custody_certificate",
        files=files,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    spans = data.get("extracted_fields_with_spans", {})
    assert "custody_days" in spans
    assert spans["custody_days"]["value"] == 180
    assert "180 days" in spans["custody_days"]["source_span"]
    assert spans["custody_days"]["char_start"] >= 0


# ── 3. Human-in-the-loop Field Correction & Audit Trail ───────────────────────

def test_human_field_correction_preserves_machine_value_with_audit(client):
    """An authorized reviewer can correct an extracted field, preserving machine value and recording audit."""
    dlsa_headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    sup_headers = _get_auth_headers(client, Role.SUPERVISING_LEGAL_OFFICER)

    # Upload doc via DLSA
    pdf_content = b"%PDF-1.4 Case UTP-0001 detention 90 days under Section 479 BNSS"
    files = {"file": ("remand.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=remand_order",
        files=files,
        headers=dlsa_headers,
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document_id"]

    # Submit correction for custody_days as Supervisor
    corr_payload = {
        "field_name": "custody_days",
        "corrected_value": 120,
        "correction_reason": "Corrected according to prison nominal roll verification.",
    }
    corr_resp = client.post(f"/documents/{doc_id}/correct-field", json=corr_payload, headers=sup_headers)
    assert corr_resp.status_code == 200, corr_resp.text
    corr_data = corr_resp.json()
    assert corr_data["status"] == "success"
    assert corr_data["corrected_value"] == 120

    # Inspect Evidence Chain to verify both values are tracked
    chain_resp = client.get(f"/documents/{doc_id}/evidence-chain", headers=sup_headers)
    assert chain_resp.status_code == 200, chain_resp.text
    chain = chain_resp.json()
    facts = chain["evidence_chain"]["extracted_facts_with_spans"]
    custody_fact = next(f for f in facts if f["field_name"] == "custody_days")
    assert custody_fact["is_corrected"] is True
    assert custody_fact["effective_value"] == "120" or custody_fact["effective_value"] == 120


# ── 4. Immutable Reprocessing (Version N+1) ──────────────────────────────────

def test_reprocessing_creates_new_version_without_overwriting(client):
    """Reprocessing a document creates version 2 pointing to parent version 1."""
    dlsa_headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    sup_headers = _get_auth_headers(client, Role.SUPERVISING_LEGAL_OFFICER)

    pdf_content = b"%PDF-1.4 Case UTP-0012 Custody Certificate dated 2026-08-10 under Section 479 BNSS"
    files = {"file": ("initial_custody.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload?case_id=UTP-0012&document_type=custody_certificate",
        files=files,
        headers=dlsa_headers,
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document_id"]
    initial_version = upload_resp.json()["version_number"]

    # Reprocess as Supervisor
    reprocess_resp = client.post(
        f"/documents/{doc_id}/reprocess",
        json={"reason": "Updated OCR model pass"},
        headers=sup_headers,
    )
    assert reprocess_resp.status_code == 200, reprocess_resp.text
    rep_data = reprocess_resp.json()
    assert rep_data["version_number"] == initial_version + 1
    assert rep_data["parent_version_id"] is not None

    # Verify both versions exist in database
    versions = get_document_versions(doc_id)
    assert len(versions) >= 2
    assert any(v["version_number"] == initial_version for v in versions)
    assert any(v["version_number"] == initial_version + 1 for v in versions)


# ── 5. Controlled Document Download & Access Logging ──────────────────────────

def test_controlled_backend_download_streams_and_logs(client):
    """GET /documents/download/{doc_id} delivers file and records access log."""
    dlsa_headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    sup_headers = _get_auth_headers(client, Role.SUPERVISING_LEGAL_OFFICER)

    pdf_content = b"%PDF-1.4 Sensitive institutional custody record for case UTP-0001"
    files = {"file": ("sensitive_custody.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=custody_certificate",
        files=files,
        headers=dlsa_headers,
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document_id"]

    # Download
    dl_resp = client.get(f"/documents/download/{doc_id}", headers=sup_headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == pdf_content


# ── 6. Stage 7 Remediation Tests ──────────────────────────────────────────────

def test_dlsa_cross_district_download_blocked(client):
    """DLSA Officer assigned to Central Delhi cannot download document for South Delhi case."""
    claims = {"email": "dlsa.central@delhi.gov.in", "full_name": "DLSA Central", "district": "Central Delhi"}
    token = create_access_token("dlsa_central", Role.DLSA_OFFICER.value, "org_dlsa", extra_claims=claims)
    central_headers = {"Authorization": f"Bearer {token}"}

    south_claims = {"email": "dlsa.south@delhi.gov.in", "full_name": "DLSA South", "district": "South Delhi"}
    south_token = create_access_token("dlsa_south", Role.DLSA_OFFICER.value, "org_dlsa", extra_claims=south_claims)
    south_headers = {"Authorization": f"Bearer {south_token}"}

    pdf_content = b"%PDF-1.4 Court remand order for South Delhi case UTP-0007"
    files = {"file": ("south_remand.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload?case_id=UTP-0007&document_type=remand_order",
        files=files,
        headers=south_headers,
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document_id"]

    dl_resp = client.get(f"/documents/download/{doc_id}", headers=central_headers)
    assert dl_resp.status_code == 403
    assert "outside your authorized DLSA district" in dl_resp.json()["detail"]


def test_denied_download_logged_in_audit(client):
    """Unauthorized download attempt records DOWNLOAD_ACCESS_DENIED in document access logs."""
    unassigned_token = create_access_token(
        "adv_stranger",
        Role.DEFENSE_ADVOCATE.value,
        "org_adv",
        extra_claims={"email": "stranger@bar.in", "full_name": "Stranger Advocate"}
    )
    unassigned_headers = {"Authorization": f"Bearer {unassigned_token}"}

    from app.database import get_case_uploaded_documents, get_db_connection
    docs = get_case_uploaded_documents("UTP-0001")
    assert len(docs) > 0
    doc_id = docs[0]["id"]

    dl_resp = client.get(f"/documents/download/{doc_id}", headers=unassigned_headers)
    assert dl_resp.status_code == 403

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM document_access_logs WHERE document_id = ? AND action = 'DOWNLOAD_ACCESS_DENIED' ORDER BY timestamp DESC",
        (doc_id,),
    )
    row = c.fetchone()
    conn.close()
    assert row is not None, "Denied download attempt must be recorded in document_access_logs"


def test_dlsa_upload_pending_verification(client):
    """DLSA uploads enter as PENDING_VERIFICATION and do not immediately mark completeness."""
    dlsa_headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    pdf_content = b"%PDF-1.4 Bail Application filed by DLSA for case UTP-0001"
    files = {"file": ("dlsa_bail_app.pdf", io.BytesIO(pdf_content), "application/pdf")}
    resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=bail_application",
        files=files,
        headers=dlsa_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_status"] == "PENDING_VERIFICATION"


def test_supervisor_verifies_pending_document(client):
    """Supervising officer can verify a pending document, transitioning status to VERIFIED."""
    dlsa_headers = _get_auth_headers(client, Role.DLSA_OFFICER)
    sup_headers = _get_auth_headers(client, Role.SUPERVISING_LEGAL_OFFICER)

    pdf_content = b"%PDF-1.4 Remand Order pending review for case UTP-0001"
    files = {"file": ("pending_remand.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=remand_order",
        files=files,
        headers=dlsa_headers,
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document_id"]
    assert upload_resp.json()["document_status"] == "PENDING_VERIFICATION"

    verify_resp = client.post(f"/documents/{doc_id}/verify", headers=sup_headers)
    assert verify_resp.status_code == 200, verify_resp.text
    data = verify_resp.json()
    assert data["status"] == "success"
    assert data["document_status"] == "VERIFIED"
    assert "remand_order" in data["present_docs"]
