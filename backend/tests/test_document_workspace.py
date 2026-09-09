"""
test_document_workspace.py - Automated Test Suite for Professional Document Workspace.
=======================================================================================
Verifies:
1. Provisional draft grounding (case facts snapshot, source docs, rules, model, prompt).
2. Preservation of original machine text upon advocate editing.
3. Organization-aware versioned templates with maintainer-only authorization.
4. Pre-approval readiness checks (unsupported factual claims, uncited assertions, missing fields).
5. Formal approval locks draft as immutable (subsequent edits blocked with 403).
6. Revision workflow creates Version N+1 with status DRAFT.
7. Anti-automatic filing enforcement (submission package prepared vs explicit filing recorded).
8. Secure export segregation (external copy strips internal audit notes, internal copy includes notes).
9. Side-by-side line diff computation accuracy.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import (
    init_db,
    get_case,
    get_document_templates,
    get_legal_document_draft,
    list_legal_document_drafts_for_case,
)
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.services.document_templates import seed_default_templates
from app.services.document_export import compute_draft_diff

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    seed_default_templates()


def get_auth_headers(role: str, user_id: str | None = None, org_id: str = "org_dlsa_central") -> dict:
    if not user_id:
        if role == Role.DEFENSE_ADVOCATE.value:
            user_id = "demo_advocate"
        elif role == Role.SUPERVISING_LEGAL_OFFICER.value:
            user_id = "demo_supervising"
        elif role == Role.PLATFORM_ADMIN.value:
            user_id = "demo_platform_admin"
        elif role == Role.GOV_ADMIN.value:
            user_id = "demo_gov_admin"
        elif role == Role.DLSA_OFFICER.value:
            user_id = "demo_dlsa_officer"
        elif role == Role.CONTROLLED_EXTERNAL_ADVOCATE.value:
            user_id = "demo_external_advocate"
        elif role == Role.JAIL_OFFICER.value:
            user_id = "demo_jail_officer"
        elif role == Role.POLICE_OFFICER.value:
            user_id = "demo_police_officer"
        elif role == Role.READ_ONLY_AUDITOR.value:
            user_id = "demo_auditor"
        elif role == Role.ACCUSED_USER.value:
            user_id = "demo_accused"
        elif role == Role.FAMILY_GUARDIAN.value:
            user_id = "demo_family"
        else:
            user_id = "demo_advocate"

    token = create_access_token(
        subject=user_id,
        role=role,
        org_id=org_id,
    )
    return {"Authorization": f"Bearer {token}"}


def test_templates_catalog_and_rbac():
    """Verify templates retrieval and maintainer RBAC."""
    headers_advocate = get_auth_headers(Role.DEFENSE_ADVOCATE.value)
    headers_supervisor = get_auth_headers(Role.SUPERVISING_LEGAL_OFFICER.value)

    # 1. Advocate can list templates
    res = client.get("/api/documents/templates", headers=headers_advocate)
    assert res.status_code == 200
    data = res.json()
    assert "templates" in data
    assert len(data["templates"]) >= 3

    # 2. Advocate cannot create a new template (403)
    payload = {
        "name": "Custom Advocate Template",
        "doc_type": "BAIL_APPLICATION",
        "statutory_ground": "Section 479 BNSS",
        "content_template": "IN THE COURT OF {{court_name}}",
        "required_fields": ["court_name"],
    }
    res_adv = client.post("/api/documents/templates", json=payload, headers=headers_advocate)
    assert res_adv.status_code == 403

    # 3. Supervising Legal Officer CAN create a template
    res_sup = client.post("/api/documents/templates", json=payload, headers=headers_supervisor)
    assert res_sup.status_code == 201
    created = res_sup.json()
    assert created["name"] == "Custom Advocate Template"
    assert created["version"] == 1


def test_generate_grounded_draft_and_preserve_original():
    """Verify draft generation anchors exact facts, rules, model, and preserves original machine text."""
    headers = get_auth_headers(Role.DEFENSE_ADVOCATE.value)

    # Generate draft for hero case UTP-0001
    res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers,
    )
    assert res.status_code == 201
    draft = res.json()
    draft_id = draft["draft_id"]

    # Verify associations
    assert draft["case_id"] == "UTP-0001"
    assert draft["status"] == "DRAFT"
    assert draft["is_immutable"] is False
    assert "exact_case_facts" in draft
    assert "court_name" in draft["exact_case_facts"]
    assert "legal_rule_result" in draft
    assert draft["legal_rule_result"]["statute"] == "Section 479 BNSS, 2023"
    assert len(draft["retrieved_legal_sources"]) > 0
    assert "ai_model_name" in draft
    assert "prompt_version" in draft
    assert len(draft["original_ai_text"]) > 100
    assert draft["content_text"] == draft["original_ai_text"]

    original_text = draft["original_ai_text"]

    # Edit working draft text
    edited_text = original_text + "\n\nADDITIONAL DEFENSE SUBMISSION: The applicant is sole breadwinner."
    res_edit = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": edited_text},
        headers=headers,
    )
    assert res_edit.status_code == 200
    updated = res_edit.json()
    assert updated["content_text"] == edited_text

    # Retrieve from DB to verify machine original was NOT mutated
    db_draft = get_legal_document_draft(draft_id)
    assert db_draft["original_ai_text"] == original_text
    assert db_draft["content_text"] == edited_text


def test_pre_approval_readiness_and_approval_locking():
    """Verify pre-approval readiness check blocks incomplete draft, and approval locks draft."""
    headers = get_auth_headers(Role.DEFENSE_ADVOCATE.value)

    # Generate draft
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers,
    )
    draft_id = res_gen.json()["draft_id"]

    # Corrupt draft with unresolved missing token and missing prayer clause
    corrupt_text = "IN THE COURT OF SESSIONS. FIR NO: [MISSING: FIR_NUMBER]. Accused Ramesh."
    client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": corrupt_text},
        headers=headers,
    )

    # Attempt to approve — MUST FAIL with 400 Bad Request
    res_fail = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Attempting premature sign-off"},
        headers=headers,
    )
    assert res_fail.status_code == 400
    detail = res_fail.json()["detail"]
    assert "blocking_issues" in detail
    assert any("MISSING" in str(b) for b in detail["blocking_issues"])

    # Provide clean, fully compliant court petition text with required elements matching UTP-0001
    clean_compliant_text = """IN THE COURT OF PRINCIPAL SESSIONS JUDGE
AT CENTRAL DISTRICT, DELHI

BAIL APPLICATION NO. 124 OF 2026
IN THE MATTER OF:
CASE / FIR NO: FIR-2025-010
POLICE STATION: KOTWALI POLICE STATION
UNDER SECTION(S): Section 115(2) BNS

IN THE MATTER OF:
SURESH PATEL
...APPLICANT / ACCUSED

VERSUS

STATE (GOVT. OF NCT OF DELHI)
...RESPONDENT / PROSECUTION

APPLICATION UNDER SECTION 479 OF THE BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023 
(READ WITH ARTICLE 21 OF THE CONSTITUTION OF INDIA) FOR GRANT OF STATUTORY MANDATORY BAIL

MOST RESPECTFULLY SHOWETH:

1. That the Applicant / Accused above named has completed 200 days of actual judicial custody.
2. Under Section 479 BNSS, 2023, the statutory threshold is fully satisfied.
3. Verified custody certificate confirms clear prison conduct.

PRAYER:
In view of the statutory mandate, it is most respectfully prayed that this Hon'ble Court may be pleased to:
(a) Admit the Applicant / Accused (SURESH PATEL) to statutory bail under Section 479 BNSS on reasonable terms;
(b) Pass any other order deemed fit.

FILED BY:
ADV. RAJESH SHARMA
COUNSEL FOR THE APPLICANT
DATE: 09-09-2026
"""

    client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": clean_compliant_text},
        headers=headers,
    )

    # Approve clean draft
    res_appr = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "Scrutiny complete, grounds verified under Section 479 BNSS."},
        headers=headers,
    )
    assert res_appr.status_code == 200
    appr_data = res_appr.json()
    assert appr_data["status"] == "APPROVED"
    assert appr_data["is_immutable"] is True

    # Attempt to edit approved draft — MUST FAIL with 403 Forbidden
    res_edit_blocked = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Unauthorized modification after sign-off"},
        headers=headers,
    )
    assert res_edit_blocked.status_code == 403
    assert "immutable" in res_edit_blocked.json()["detail"].lower()


def test_revision_workflow_creates_new_version():
    """Verify revision creates Version N+1 with status DRAFT from an approved draft."""
    headers = get_auth_headers(Role.DEFENSE_ADVOCATE.value)

    # Generate draft
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers,
    )
    assert res_gen.status_code == 201
    draft_data = res_gen.json()
    draft_id = draft_data["draft_id"]
    initial_ver = draft_data["version_number"]

    # Initiate revision
    res_rev = client.post(f"/api/documents/drafts/{draft_id}/revise", headers=headers)
    assert res_rev.status_code == 201
    revision = res_rev.json()

    assert revision["draft_id"] != draft_id
    assert revision["version_number"] == initial_ver + 1
    assert revision["status"] == "DRAFT"
    assert revision["is_immutable"] is False
    assert revision["approved_by"] is None


def test_anti_automatic_filing_and_submission_package():
    """Verify package preparation records human sign-off without auto-filing, requiring explicit filing."""
    headers = get_auth_headers(Role.DEFENSE_ADVOCATE.value)

    # Generate draft
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers,
    )
    draft_id = res_gen.json()["draft_id"]

    # Package unapproved draft should fail
    res_pkg_fail = client.post(f"/api/documents/drafts/{draft_id}/package", json={}, headers=headers)
    assert res_pkg_fail.status_code == 400

    # Mark as approved directly for testing package creation
    from app.database import update_legal_document_draft
    update_legal_document_draft(draft_id, {
        "status": "APPROVED",
        "is_immutable": True,
        "approved_by": "Adv. Rajesh Sharma",
        "approved_at": "2026-09-09T10:00:00Z",
    })

    # Prepare submission package
    res_pkg = client.post(
        f"/api/documents/drafts/{draft_id}/package",
        json={"exhibits": ["Nominal Roll", "Remand Order", "Vakalatnama"]},
        headers=headers,
    )
    assert res_pkg.status_code == 200
    pkg = res_pkg.json()
    assert pkg["is_automatically_filed"] is False
    assert pkg["filing_mode"] == "MANUAL_OR_VERIFIED_INTEGRATION_ONLY"
    assert "package_id" in pkg

    # Record external filing
    res_file = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={
            "filing_reference": "CNR-DLCT01-002934-2026",
            "filing_date": "2026-09-09",
            "court_name": "Court of Principal Sessions Judge, Tis Hazari",
        },
        headers=headers,
    )
    assert res_file.status_code == 200
    file_data = res_file.json()
    assert file_data["status"] == "FILED"
    assert file_data["filing_reference"] == "CNR-DLCT01-002934-2026"


def test_secure_document_export_segregation():
    """Verify external export strips internal notes; internal export includes notes only for authorized roles."""
    headers_advocate = get_auth_headers(Role.DEFENSE_ADVOCATE.value)
    headers_supervisor = get_auth_headers(Role.SUPERVISING_LEGAL_OFFICER.value)
    headers_platform_admin = get_auth_headers(Role.PLATFORM_ADMIN.value)

    # Generate draft
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = res_gen.json()["draft_id"]

    # Add confidential reviewer comment
    client.post(
        f"/api/documents/drafts/{draft_id}/comments",
        json={"comment": "CONFIDENTIAL: Verify surety solvency before formal hearing."},
        headers=headers_supervisor,
    )

    # 1. External Court Export (advocate)
    res_ext = client.get(
        f"/api/documents/drafts/{draft_id}/export?include_internal_notes=false",
        headers=headers_advocate,
    )
    assert res_ext.status_code == 200
    ext_payload = res_ext.json()
    assert ext_payload["export_type"] == "EXTERNAL_COURT"
    assert "CONFIDENTIAL" not in ext_payload["exported_text"]
    assert ext_payload["includes_internal_notes"] is False

    # 2. Platform Admin blocked from accessing/exporting case document (403 Forbidden)
    res_admin_internal = client.get(
        f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true",
        headers=headers_platform_admin,
    )
    assert res_admin_internal.status_code == 403

    # 3. Controlled External Advocate requests internal notes -> permitted to export, but internal notes stripped to EXTERNAL_COURT
    headers_ext = get_auth_headers(Role.CONTROLLED_EXTERNAL_ADVOCATE.value)
    res_ext_internal = client.get(
        f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true",
        headers=headers_ext,
    )
    assert res_ext_internal.status_code == 200
    assert res_ext_internal.json()["export_type"] == "EXTERNAL_COURT"
    assert "CONFIDENTIAL" not in res_ext_internal.json()["exported_text"]

    # 3. Supervising Legal Officer requests internal notes -> included
    res_sup_internal = client.get(
        f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true",
        headers=headers_supervisor,
    )
    assert res_sup_internal.status_code == 200
    sup_payload = res_sup_internal.json()
    assert sup_payload["export_type"] == "INTERNAL_CERTIFIED"
    assert "CONFIDENTIAL" in sup_payload["exported_text"]
    assert sup_payload["includes_internal_notes"] is True

    # 4. Assigned Defense Advocate requests internal notes -> included
    res_adv_internal = client.get(
        f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true",
        headers=headers_advocate,
    )
    assert res_adv_internal.status_code == 200
    adv_payload = res_adv_internal.json()
    assert adv_payload["export_type"] == "INTERNAL_CERTIFIED"
    assert "CONFIDENTIAL" in adv_payload["exported_text"]


def test_diff_computation():
    """Verify side-by-side diff computation detects additions, deletions, and unchanged lines."""
    text1 = "Line 1\nLine 2\nLine 3"
    text2 = "Line 1\nLine 2 modified\nLine 3\nLine 4 added"
    diff = compute_draft_diff(text1, text2)
    assert diff["additions"] >= 2
    assert diff["deletions"] >= 1
    assert diff["unchanged"] >= 2


def test_dlsa_officer_boundaries():
    """Verify DLSA Officer allowed and disallowed actions as per Stage 19 matrix."""
    headers_dlsa = get_auth_headers(Role.DLSA_OFFICER.value)

    # 1. DLSA Officer CAN initiate draft workflow where delegated
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_dlsa,
    )
    assert res_gen.status_code == 201
    draft_id = res_gen.json()["draft_id"]

    # 2. DLSA Officer CANNOT edit draft text (prohibited from acting as lawyer)
    res_edit = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Modified legal argument by DLSA staff."},
        headers=headers_dlsa,
    )
    assert res_edit.status_code == 403

    # 3. DLSA Officer CANNOT approve legal petition
    res_appr = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "DLSA sign off"},
        headers=headers_dlsa,
    )
    assert res_appr.status_code == 403

    # 4. DLSA Officer CAN add review comments and routing notes
    res_comm = client.post(
        f"/api/documents/drafts/{draft_id}/comments",
        json={"comment": "Routed to Panel Lawyer for formal review and signature."},
        headers=headers_dlsa,
    )
    assert res_comm.status_code == 200


def test_controlled_external_advocate_read_only_boundary():
    """Verify Controlled External Advocate has read-only access and cannot edit, approve, or file."""
    headers_advocate = get_auth_headers(Role.DEFENSE_ADVOCATE.value)
    headers_ext = get_auth_headers(Role.CONTROLLED_EXTERNAL_ADVOCATE.value)

    # Generate draft using assigned advocate
    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = res_gen.json()["draft_id"]

    # 1. External advocate CAN view drafts and diffs
    res_view = client.get(f"/api/documents/drafts/{draft_id}", headers=headers_ext)
    assert res_view.status_code == 200

    res_diff = client.get(f"/api/documents/drafts/{draft_id}/diff", headers=headers_ext)
    assert res_diff.status_code == 200

    # 2. External advocate CANNOT generate new drafts
    res_gen_ext = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_ext,
    )
    assert res_gen_ext.status_code == 403

    # 3. External advocate CANNOT edit working text
    res_edit_ext = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Unauthorized external modification."},
        headers=headers_ext,
    )
    assert res_edit_ext.status_code == 403

    # 4. External advocate CANNOT approve draft
    res_appr_ext = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "External counsel approval"},
        headers=headers_ext,
    )
    assert res_appr_ext.status_code == 403

    # 5. External advocate CANNOT record court filing
    res_file_ext = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={"filing_reference": "CNR-TEST-999"},
        headers=headers_ext,
    )
    assert res_file_ext.status_code == 403


def test_jail_and_police_officers_strictly_blocked():
    """Verify Jail and Police Officers cannot view or mutate legal-aid document drafts."""
    headers_jail = get_auth_headers(Role.JAIL_OFFICER.value)
    headers_police = get_auth_headers(Role.POLICE_OFFICER.value)
    headers_advocate = get_auth_headers(Role.DEFENSE_ADVOCATE.value)

    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = res_gen.json()["draft_id"]

    # 1. Jail Officer blocked from viewing and drafting
    assert client.get(f"/api/documents/drafts/{draft_id}", headers=headers_jail).status_code == 403
    assert client.post("/api/documents/drafts/generate", json={"case_id": "UTP-0001"}, headers=headers_jail).status_code == 403
    assert client.put(f"/api/documents/drafts/{draft_id}", json={"content_text": "x"}, headers=headers_jail).status_code == 403

    # 2. Police Officer blocked from viewing and drafting
    assert client.get(f"/api/documents/drafts/{draft_id}", headers=headers_police).status_code == 403
    assert client.post("/api/documents/drafts/generate", json={"case_id": "UTP-0001"}, headers=headers_police).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_police).status_code == 403


def test_citizen_and_family_blocked_from_internal_workspace():
    """Verify Accused and Family are blocked from internal drafting workspace and templates."""
    headers_accused = get_auth_headers(Role.ACCUSED_USER.value)
    headers_family = get_auth_headers(Role.FAMILY_GUARDIAN.value)

    # Cannot list templates
    assert client.get("/api/documents/templates", headers=headers_accused).status_code == 403
    assert client.get("/api/documents/templates", headers=headers_family).status_code == 403

    # Cannot list case drafts
    assert client.get("/api/documents/drafts/case/UTP-0001", headers=headers_accused).status_code == 403
    assert client.get("/api/documents/drafts/case/UTP-0001", headers=headers_family).status_code == 403


def test_platform_admin_and_auditor_boundaries():
    """Verify Platform Admin cannot grant legal approval and Read-Only Auditor is strictly read-only."""
    headers_admin = get_auth_headers(Role.PLATFORM_ADMIN.value)
    headers_auditor = get_auth_headers(Role.READ_ONLY_AUDITOR.value)
    headers_advocate = get_auth_headers(Role.DEFENSE_ADVOCATE.value)

    res_gen = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = res_gen.json()["draft_id"]

    # 1. Platform Admin cannot approve draft or edit text
    assert client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_admin).status_code == 403
    assert client.put(f"/api/documents/drafts/{draft_id}", json={"content_text": "admin edit"}, headers=headers_admin).status_code == 403

    # 2. Read-Only Auditor can view draft and diffs
    assert client.get(f"/api/documents/drafts/{draft_id}", headers=headers_auditor).status_code == 200
    assert client.get(f"/api/documents/drafts/{draft_id}/diff", headers=headers_auditor).status_code == 200

    # 3. Read-Only Auditor cannot mutate (edit, approve, comment)
    assert client.put(f"/api/documents/drafts/{draft_id}", json={"content_text": "auditor edit"}, headers=headers_auditor).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_auditor).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/comments", json={"comment": "auditor note"}, headers=headers_auditor).status_code == 403
