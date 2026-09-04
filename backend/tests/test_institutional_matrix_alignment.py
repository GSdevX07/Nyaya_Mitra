"""
tests/test_institutional_matrix_alignment.py — Comprehensive Test Suite for the 41-Point
Canonical Institutional Permission, Workflow, and Enforcement Matrix.

Verifies:
1. Medical Data Quarantining under DPDP (strictly DLSA & Supervising Legal Officer; redacted for all others).
2. Accused Legal Identity Updates (strictly Supervising Legal Officer; 403 for DLSA, Admin, Advocate).
3. Ingestion Routes Hardening (strictly Platform Admin; 403 for DLSA, Supervisor, Jail, Police, Gov).
4. Case Dossier Export with SHA-256 Seal (strictly Supervising Legal Officer; 403 for Admin, DLSA, Counsel).
5. Reports Access (DLSA, Supervisor, Gov, Auditor; 403 for Platform Admin).
6. Audit Events Log Access (Auditor, Supervisor, Platform Admin; 403 for DLSA).
7. Duplicate Identity Candidate Review (DLSA, Supervisor, Gov, Platform Admin; 403 for Jail, Police, Counsel).
8. Legal-Aid Counsel Assignment (strictly DLSA Officer; 403 for Admin, Police).
"""
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.roles import Role
from app.auth.tokens import create_access_token
from app.database import init_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    init_db()


def make_token(username: str, role: Role, extra: dict = None):
    claims = {
        "full_name": f"{username} User",
        "district": "Central Delhi",
        **(extra or {}),
    }
    return create_access_token(
        subject=username,
        role=role.value,
        org_id="org_dlsa_central",
        extra_claims=claims,
    )


@pytest.fixture
def supervising_token():
    return make_token("demo_supervising", Role.SUPERVISING_LEGAL_OFFICER)


@pytest.fixture
def dlsa_token():
    return make_token("demo_dlsa", Role.DLSA_OFFICER)


@pytest.fixture
def admin_token():
    return make_token("demo_admin", Role.PLATFORM_ADMIN)


@pytest.fixture
def gov_token():
    return make_token("demo_gov", Role.GOV_ADMIN)


@pytest.fixture
def jail_token():
    return make_token("demo_jail", Role.JAIL_OFFICER, {"facility_ids": ["Central Jail No. 4, Tihar"]})


@pytest.fixture
def police_token():
    return make_token("demo_police", Role.POLICE_OFFICER, {"police_station": "Kashmere Gate"})


@pytest.fixture
def advocate_token():
    return make_token("demo_advocate", Role.DEFENSE_ADVOCATE, {"linked_case_id": "UTP-0001"})


@pytest.fixture
def auditor_token():
    return make_token("demo_auditor", Role.READ_ONLY_AUDITOR)


# ── 1. Medical Data Quarantining Tests ────────────────────────────────────────

def test_medical_data_unredacted_for_authorized_roles(dlsa_token, supervising_token):
    """DLSA and Supervising Legal Officer must receive full, unredacted medical data."""
    for token, role_name in [(dlsa_token, "DLSA"), (supervising_token, "SUPERVISOR")]:
        res = client.get("/accused/acc_utp_0001", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200 for {role_name}"
        data = res.json()
        med = data.get("medical_record", {})
        assert med.get("is_redacted") is False or med.get("is_redacted") is None
        assert "Access Restricted" not in med.get("details_restricted", "")


def test_medical_data_redacted_for_unauthorized_roles(
    admin_token, jail_token, police_token, advocate_token, auditor_token
):
    """Platform Admin, Jail, Police, Defense Advocate, and Auditor must receive redacted medical envelopes."""
    tokens = [
        ("PLATFORM_ADMIN", admin_token),
        ("JAIL_OFFICER", jail_token),
        ("POLICE_OFFICER", police_token),
        ("DEFENSE_ADVOCATE", advocate_token),
        ("READ_ONLY_AUDITOR", auditor_token),
    ]
    for role_name, token in tokens:
        res = client.get("/accused/acc_utp_0001", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200 for {role_name}"
        data = res.json()
        med = data.get("medical_record", {})
        assert med.get("is_redacted") is True, f"Expected is_redacted=True for {role_name}"
        assert "RESTRICTED" in med.get("details_restricted", "")


# ── 2. Accused Identity Update Tests ──────────────────────────────────────────

def test_supervising_legal_officer_can_update_identity(supervising_token):
    """Supervisor can update accused identity attributes with statutory justification."""
    payload = {
        "update_reason": "Verified biometric cross-reference with Aadhaar institutional sync",
        "full_name": "Suresh Kumar (Verified)",
        "aliases": ["Suraj", "Suri"],
        "gender": "Male",
        "age": 34,
    }
    res = client.patch(
        "/accused/acc_utp_0001/identity",
        json=payload,
        headers={"Authorization": f"Bearer {supervising_token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("SUCCESS", "UPDATED")
    assert data["accused_id"] == "acc_utp_0001"
    assert "Suresh Kumar (Verified)" in data["updated_attributes"]["full_name"]


def test_non_supervisor_cannot_update_identity(dlsa_token, admin_token, advocate_token):
    """DLSA, Admin, and Advocate must be denied (403) from updating accused identity."""
    payload = {
        "update_reason": "Unauthorized identity rewrite attempt",
        "full_name": "Intruder Attempt",
    }
    for token, role in [(dlsa_token, "DLSA"), (admin_token, "ADMIN"), (advocate_token, "ADVOCATE")]:
        res = client.patch(
            "/accused/acc_utp_0001/identity",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403, f"Expected 403 Forbidden for {role}"


# ── 3. Duplicate Candidate Viewing Tests ──────────────────────────────────────

def test_duplicate_candidate_viewing_permissions(
    dlsa_token, supervising_token, gov_token, admin_token, jail_token, police_token, advocate_token
):
    """DLSA, Supervisor, Gov, and Platform Admin can view candidates; operational roles cannot."""
    allowed = [("DLSA", dlsa_token), ("SUPERVISOR", supervising_token), ("GOV", gov_token), ("ADMIN", admin_token)]
    for role, token in allowed:
        res = client.get("/accused/duplicates/candidates", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200 for {role}"

    forbidden = [("JAIL", jail_token), ("POLICE", police_token), ("ADVOCATE", advocate_token)]
    for role, token in forbidden:
        res = client.get("/accused/duplicates/candidates", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403, f"Expected 403 for {role}"


# ── 4. Ingestion Routes Hardening Tests ────────────────────────────────────────

def test_ingestion_routes_restricted_to_platform_admin(
    admin_token, dlsa_token, supervising_token, gov_token, jail_token, police_token
):
    """Only Platform Admin can access ingestion connectors; all other roles must receive 403."""
    res_admin = client.get("/ingestion/connectors", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200

    disallowed = [
        ("DLSA", dlsa_token),
        ("SUPERVISOR", supervising_token),
        ("GOV", gov_token),
        ("JAIL", jail_token),
        ("POLICE", police_token),
    ]
    for role, token in disallowed:
        res = client.get("/ingestion/connectors", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403, f"Expected 403 for {role}"


# ── 5. Case File Export with SHA-256 Seal Tests ───────────────────────────────

def test_case_file_export_permissions(supervising_token, dlsa_token, admin_token, advocate_token):
    """Only Supervising Legal Officer can export sealed case file; DLSA, Admin, Advocate receive 403."""
    res = client.get(
        "/cases/UTP-0001/export?export_reason=AuditReview",
        headers={"Authorization": f"Bearer {supervising_token}"},
    )
    assert res.status_code == 200
    export_pkg = res.json()
    assert "export_metadata" in export_pkg
    assert export_pkg["export_metadata"]["case_id"] == "UTP-0001"
    assert "sha256_seal" in export_pkg["export_metadata"]
    assert len(export_pkg["export_metadata"]["sha256_seal"]) == 64

    forbidden = [("DLSA", dlsa_token), ("ADMIN", admin_token), ("ADVOCATE", advocate_token)]
    for role, token in forbidden:
        r = client.get("/cases/UTP-0001/export", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403, f"Expected 403 for {role}"


# ── 6. Reports Access Tests ───────────────────────────────────────────────────

def test_reports_access_permissions(dlsa_token, supervising_token, gov_token, auditor_token, admin_token):
    """DLSA, Supervisor, Gov, and Auditor can access reports; Platform Admin receives 403."""
    for token, role in [
        (dlsa_token, "DLSA"),
        (supervising_token, "SUPERVISOR"),
        (gov_token, "GOV"),
        (auditor_token, "AUDITOR"),
    ]:
        res = client.get("/reports", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200 for {role}"

    res_admin = client.get("/reports", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 403, "Expected 403 for PLATFORM_ADMIN"


# ── 7. Audit Events Access Tests ──────────────────────────────────────────────

def test_audit_events_access_permissions(auditor_token, supervising_token, admin_token, dlsa_token):
    """Auditor, Supervisor, and Admin can view audit logs; DLSA receives 403."""
    for token, role in [
        (auditor_token, "AUDITOR"),
        (supervising_token, "SUPERVISOR"),
        (admin_token, "ADMIN"),
    ]:
        res = client.get("/audit-events", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200 for {role}"

    res_dlsa = client.get("/audit-events", headers={"Authorization": f"Bearer {dlsa_token}"})
    assert res_dlsa.status_code == 403, "Expected 403 for DLSA_OFFICER"


# ── 8. DLSA Counsel Assignment Tests ──────────────────────────────────────────

def test_counsel_assignment_permissions(dlsa_token, admin_token, police_token):
    """DLSA Officer can assign legal-aid counsel; Admin and Police are denied (403)."""
    payload = {
        "lawyer_id": "LWYR-TEST-01",
        "lawyer_name": "Adv. Tested Legal Aid",
        "notes": "Formal DLSA allocation for test case",
    }
    res_dlsa = client.post(
        "/cases/UTP-0001/assign-counsel",
        json=payload,
        headers={"Authorization": f"Bearer {dlsa_token}"},
    )
    assert res_dlsa.status_code == 200
    assert res_dlsa.json()["status"] == "success"
    assert res_dlsa.json()["assigned_lawyer_id"] == "LWYR-TEST-01"

    for token, role in [(admin_token, "ADMIN"), (police_token, "POLICE")]:
        r = client.post(
            "/cases/UTP-0001/assign-counsel",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403, f"Expected 403 for {role}"


# ── 9. Document Review vs Supervisory Verification Separation Tests ───────────

def test_document_review_and_verification_separation(dlsa_token, supervising_token, admin_token):
    """
    DLSA can review a document for intake (/documents/{id}/review) -> 200 (REVIEWED).
    DLSA CANNOT supervisory verify (/documents/{id}/verify) -> 403 Forbidden.
    Supervising Legal Officer can verify (/documents/{id}/verify) -> 200 (VERIFIED).
    Platform Admin cannot review or verify -> 403 Forbidden on both.
    """
    # 1. Upload a document as DLSA
    pdf_content = b"%PDF-1.4 DLSA test document for intake review"
    files = {"file": ("test_intake_review.pdf", io.BytesIO(pdf_content), "application/pdf")}
    upload_resp = client.post(
        "/documents/upload?case_id=UTP-0001&document_type=bail_application",
        files=files,
        headers={"Authorization": f"Bearer {dlsa_token}"},
    )
    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document_id"]

    # 2. Platform Admin cannot review or verify
    res_admin_rev = client.post(f"/documents/{doc_id}/review", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_rev.status_code == 403, "Platform Admin must be denied document review"

    res_admin_ver = client.post(f"/documents/{doc_id}/verify", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_ver.status_code == 403, "Platform Admin must be denied supervisory verify"

    # 3. DLSA CANNOT supervisory verify (403 Forbidden)
    res_dlsa_ver = client.post(f"/documents/{doc_id}/verify", headers={"Authorization": f"Bearer {dlsa_token}"})
    assert res_dlsa_ver.status_code == 403, "DLSA Officer must be denied supervisory verify"

    # 4. DLSA CAN review document for intake (200 OK)
    res_dlsa_rev = client.post(f"/documents/{doc_id}/review", headers={"Authorization": f"Bearer {dlsa_token}"})
    assert res_dlsa_rev.status_code == 200, f"DLSA review failed: {res_dlsa_rev.text}"
    data_rev = res_dlsa_rev.json()
    assert data_rev["status"] == "success"
    assert data_rev["document_status"] == "REVIEWED"

    # 5. Supervising Legal Officer CAN supervisory verify the reviewed document (200 OK)
    res_sup_ver = client.post(f"/documents/{doc_id}/verify", headers={"Authorization": f"Bearer {supervising_token}"})
    assert res_sup_ver.status_code == 200, f"Supervisory verify failed: {res_sup_ver.text}"
    data_ver = res_sup_ver.json()
    assert data_ver["status"] == "success"
    assert data_ver["document_status"] == "VERIFIED"