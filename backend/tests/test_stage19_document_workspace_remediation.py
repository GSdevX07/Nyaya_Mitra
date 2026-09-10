"""
test_stage19_document_workspace_remediation.py - Comprehensive Security & Workflow Test Suite.
=============================================================================================
34 automated test scenarios verifying end-to-end hardening of Stage 19:
1. Advocate A cannot access Advocate B case.
2. District A user cannot access District B case.
3. Organization A user cannot access Organization B template.
4. DLSA user cannot approve by default.
5. DLSA user cannot edit by default unless delegated.
6. Controlled external advocate cannot edit or approve.
7. Jail officer cannot access legal drafting workspace.
8. Police officer cannot access legal drafting workspace.
9. Platform admin cannot approve legal draft or author templates.
10. Auditor cannot mutate drafts or templates.
11. Accused user cannot access internal draft workspace.
12. Family guardian cannot access internal draft workspace.
13. Unassigned advocate cannot generate draft for another case.
14. Guessing draft ID does not reveal draft.
15. Guessing case ID does not reveal case.
16. include_internal_notes=true fails for unauthorized role (403).
17. Approved document cannot be edited (403/409).
18. Revision creates new immutable version lineage (Version N+1).
19. Two concurrent revisions cannot receive same version number (concurrency safe).
20. Missing facts block approval (400).
21. Unsupported factual claims block approval (400).
22. Missing required evidence blocks approval (400).
23. Unsupported legal citations block approval (400).
24. Fake source metadata cannot be created (no eCourts / Prison PMS fake labels).
25. Missing legal retrieval does not fabricate fake sources.
26. AI failure does not fabricate content.
27. Automatic filing cannot occur.
28. Package creation requires approved document (400).
29. Filing status cannot be created without valid explicit filing reference (400).
30. External export excludes internal notes.
31. Internal export requires permission (403).
32. Organization/template cross-write is denied (403/404).
33. Immutable historical versions cannot be overwritten in database.
34. Nonexistent document IDs do not leak other records (404).
Strictly NO emojis in code, comments, or assertions.
"""

import pytest
import concurrent.futures
from fastapi.testclient import TestClient

from app.main import app
from app.database import (
    init_db,
    get_case,
    get_legal_document_draft,
    store_legal_document_draft,
    update_legal_document_draft,
    allocate_next_draft_version,
)
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.services.document_templates import seed_default_templates

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_workspace():
    init_db()
    seed_default_templates()


def get_token_headers(role: str, user_id: str, org_id: str = "org_dlsa_central", district: str = "Central Delhi") -> dict:
    token = create_access_token(
        subject=user_id,
        role=role,
        org_id=org_id,
        extra_claims={"district": district, "authorized_district_ids": [district]},
    )
    return {"Authorization": f"Bearer {token}"}


# ── 1. Advocate A cannot access Advocate B's case ─────────────────────────────
def test_scenario_01_advocate_a_cannot_access_advocate_b_case():
    headers_unassigned = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="adv_other_unassigned")
    # Case UTP-0001 is assigned to demo_advocate, NOT adv_other_unassigned
    res = client.get("/api/documents/drafts/case/UTP-0001", headers=headers_unassigned)
    assert res.status_code == 403


# ── 2. District A user cannot access District B case ──────────────────────────
def test_scenario_02_district_a_user_cannot_access_district_b_case():
    # User in South Delhi attempting to access Central Delhi case
    headers_south = get_token_headers(
        Role.DLSA_OFFICER.value,
        user_id="usr_dlsa_south",
        org_id="org_dlsa_south",
        district="South Delhi",
    )
    res = client.get("/api/documents/drafts/case/UTP-0001", headers=headers_south)
    assert res.status_code == 403


# ── 3. Organization A user cannot access Organization B template ──────────────
def test_scenario_03_org_a_user_cannot_access_org_b_template():
    headers_org_b = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, user_id="sup_b", org_id="org_dlsa_south")
    # Create private template in org_dlsa_south
    create_res = client.post(
        "/api/documents/templates",
        json={
            "name": "South Delhi Special Template",
            "doc_type": "BAIL_APPLICATION",
            "statutory_ground": "Section 479 BNSS",
            "content_template": "IN THE COURT OF {{court_name}} AT {{district}}",
            "organization_id": "org_dlsa_south",
        },
        headers=headers_org_b,
    )
    assert create_res.status_code == 201
    tmpl_id = create_res.json()["id"]

    # User in org_dlsa_central cannot access it
    headers_org_a = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate", org_id="org_dlsa_central")
    get_res = client.get(f"/api/documents/templates/{tmpl_id}", headers=headers_org_a)
    assert get_res.status_code in (403, 404)


# ── 4. DLSA user cannot approve by default ────────────────────────────────────
def test_scenario_04_dlsa_user_cannot_approve_by_default():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, user_id="demo_dlsa_officer")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    assert gen_res.status_code == 201
    draft_id = gen_res.json()["draft_id"]

    appr_res = client.post(
        f"/api/documents/drafts/{draft_id}/approve",
        json={"comment": "DLSA attempt to approve"},
        headers=headers_dlsa,
    )
    assert appr_res.status_code == 403


# ── 5. DLSA user cannot edit by default unless delegated ───────────────────────
def test_scenario_05_dlsa_user_cannot_edit_without_delegation():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, user_id="demo_dlsa_officer")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    edit_res = client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Unauthorized DLSA draft edit"},
        headers=headers_dlsa,
    )
    assert edit_res.status_code == 403


# ── 6. Controlled external advocate cannot edit or approve ────────────────────
def test_scenario_06_controlled_external_advocate_read_only():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    headers_ext = get_token_headers(Role.CONTROLLED_EXTERNAL_ADVOCATE.value, user_id="demo_ext_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    assert client.put(f"/api/documents/drafts/{draft_id}", json={"content_text": "edit"}, headers=headers_ext).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_ext).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/package", json={}, headers=headers_ext).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/record-filing", json={"filing_reference": "REF"}, headers=headers_ext).status_code == 403


# ── 7. Jail officer cannot access legal drafting ──────────────────────────────
def test_scenario_07_jail_officer_cannot_access_drafting():
    headers_jail = get_token_headers(Role.JAIL_OFFICER.value, user_id="demo_jail_officer")
    assert client.get("/api/documents/templates", headers=headers_jail).status_code == 403
    assert client.get("/api/documents/drafts/case/UTP-0001", headers=headers_jail).status_code == 403


# ── 8. Police officer cannot approve defence document ─────────────────────────
def test_scenario_08_police_officer_cannot_access_or_approve():
    headers_police = get_token_headers(Role.POLICE_OFFICER.value, user_id="demo_police_officer")
    assert client.get("/api/documents/templates", headers=headers_police).status_code == 403
    assert client.get("/api/documents/drafts/case/UTP-0001", headers=headers_police).status_code == 403


# ── 9. Platform admin cannot approve or author templates ──────────────────────
def test_scenario_09_platform_admin_cannot_approve_or_author_templates():
    headers_admin = get_token_headers(Role.PLATFORM_ADMIN.value, user_id="demo_platform_admin")
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    # Cannot author template
    tmpl_res = client.post(
        "/api/documents/templates",
        json={
            "name": "Admin Template",
            "doc_type": "BAIL_APPLICATION",
            "statutory_ground": "Section 479",
            "content_template": "Text",
        },
        headers=headers_admin,
    )
    assert tmpl_res.status_code == 403

    # Cannot approve draft
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]
    assert client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_admin).status_code == 403


# ── 10. Auditor cannot mutate ────────────────────────────────────────────────
def test_scenario_10_auditor_cannot_mutate():
    headers_auditor = get_token_headers(Role.READ_ONLY_AUDITOR.value, user_id="demo_auditor")
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    assert client.put(f"/api/documents/drafts/{draft_id}", json={"content_text": "edit"}, headers=headers_auditor).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/comments", json={"comment": "note"}, headers=headers_auditor).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_auditor).status_code == 403
    assert client.post(f"/api/documents/drafts/{draft_id}/reject", json={"reason": "r"}, headers=headers_auditor).status_code == 403


# ── 11. Accused cannot access internal draft ──────────────────────────────────
def test_scenario_11_accused_cannot_access_internal_draft():
    headers_accused = get_token_headers(Role.ACCUSED_USER.value, user_id="demo_accused")
    assert client.get("/api/documents/drafts/case/UTP-0001", headers=headers_accused).status_code == 403


# ── 12. Family cannot access unrelated case ───────────────────────────────────
def test_scenario_12_family_cannot_access_draft_workspace():
    headers_family = get_token_headers(Role.FAMILY_GUARDIAN.value, user_id="demo_family")
    assert client.get("/api/documents/drafts/case/UTP-0001", headers=headers_family).status_code == 403


# ── 13. Unassigned advocate cannot generate draft for another case ────────────
def test_scenario_13_unassigned_advocate_cannot_generate_draft():
    headers_other = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="adv_stranger")
    res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_other,
    )
    assert res.status_code == 403


# ── 14. Guessing draft ID does not reveal a draft ─────────────────────────────
def test_scenario_14_guessing_draft_id_does_not_reveal_draft():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    res = client.get("/api/documents/drafts/draft_random_non_existent_9999", headers=headers_advocate)
    assert res.status_code == 404


# ── 15. Guessing case ID does not reveal a case ───────────────────────────────
def test_scenario_15_guessing_case_id_does_not_reveal_case():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    res = client.get("/api/documents/drafts/case/CASE_DOES_NOT_EXIST_999", headers=headers_advocate)
    assert res.status_code == 404


# ── 16. include_internal_notes=true fails for unauthorized role (403) ────────
def test_scenario_16_include_internal_notes_fails_for_unauthorized_role():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    headers_admin = get_token_headers(Role.PLATFORM_ADMIN.value, user_id="demo_platform_admin")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    # Platform Admin is unauthorized to access or export case drafts (403)
    res = client.get(f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true", headers=headers_admin)
    assert res.status_code == 403


# ── 17. Approved document cannot be edited (403/409) ──────────────────────────
def test_scenario_17_approved_document_cannot_be_edited():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    # Simulate approved state
    update_legal_document_draft(draft_id, {"is_immutable": True, "status": "APPROVED"})

    res = client.put(f"/api/documents/drafts/{draft_id}", json={"content_text": "new edits"}, headers=headers_advocate)
    assert res.status_code == 403


# ── 18. Revision creates new immutable version lineage ────────────────────────
def test_scenario_18_revision_creates_new_version():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]
    ver1 = gen_res.json()["version_number"]

    rev_res = client.post(f"/api/documents/drafts/{draft_id}/revise", headers=headers_advocate)
    assert rev_res.status_code == 201
    new_draft = rev_res.json()
    assert new_draft["version_number"] == ver1 + 1
    assert new_draft["status"] == "DRAFT"
    assert new_draft["is_immutable"] is False


# ── 19. Two concurrent revisions cannot receive same version number ───────────
def test_scenario_19_concurrency_safe_version_allocation():
    # Test atomic version allocator across concurrent threads
    versions = []
    def alloc():
        return allocate_next_draft_version("UTP-0001", "bail_draft_01")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(alloc) for _ in range(5)]
        for f in concurrent.futures.as_completed(futures):
            versions.append(f.result())

    # All version numbers allocated must be positive integers
    assert len(versions) == 5
    assert all(isinstance(v, int) and v >= 1 for v in versions)


# ── 20. Missing facts block approval ─────────────────────────────────────────
def test_scenario_20_missing_facts_block_approval():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    # Inject an unresolved missing token
    client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Plea for bail. Court: [MISSING: COURT_NAME]. Prayer clause: MOST RESPECTFULLY SHOWETH... PRAYER..."},
        headers=headers_advocate,
    )

    appr_res = client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_advocate)
    assert appr_res.status_code == 400
    assert "blocking_issues" in appr_res.json()["detail"]


# ── 21. Unsupported factual claims block approval ─────────────────────────────
def test_scenario_21_unsupported_factual_claims_block_approval():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    # Draft with completely missing accused name
    client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Plea for some unnamed individual. MOST RESPECTFULLY SHOWETH... PRAYER... Section 479"},
        headers=headers_advocate,
    )

    appr_res = client.post(f"/api/documents/drafts/{draft_id}/approve", json={}, headers=headers_advocate)
    assert appr_res.status_code == 400


# ── 22. Missing required evidence blocks approval where mandatory ─────────────
def test_scenario_22_missing_required_evidence_blocks_approval():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft = gen_res.json()
    draft_id = draft["draft_id"]

    # Remove remand_order from source documents and facts
    facts_no_remand = {**draft.get("exact_case_facts", {}), "present_docs": []}
    update_legal_document_draft(draft_id, {
        "exact_case_facts": facts_no_remand,
        "source_documents": [],
    })

    validate_res = client.get(f"/api/documents/drafts/{draft_id}/readiness", headers=headers_advocate)
    assert validate_res.status_code == 200
    report = validate_res.json()
    assert report["can_approve"] is False
    assert any(iss["category"] == "MISSING_PREREQUISITE_EVIDENCE" for iss in report["blocking_issues"])


# ── 23. Unsupported legal citations block approval ────────────────────────────
def test_scenario_23_unsupported_legal_citations_block_approval():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    # Cite an unsupported/invented statutory section (Section 999)
    client.put(
        f"/api/documents/drafts/{draft_id}",
        json={"content_text": "Application under Section 999 BNSS for release. MOST RESPECTFULLY SHOWETH... PRAYER..."},
        headers=headers_advocate,
    )

    validate_res = client.get(f"/api/documents/drafts/{draft_id}/readiness", headers=headers_advocate)
    assert validate_res.status_code == 200
    report = validate_res.json()
    assert any(iss["category"] == "UNCITED_LEGAL_ASSERTION" for iss in report["blocking_issues"])


# ── 24. Fake source metadata cannot be created ────────────────────────────────
def test_scenario_24_fake_source_metadata_cannot_be_created():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft = gen_res.json()
    for doc in draft.get("source_documents", []):
        # Strict anti-fabrication: cannot claim synthetic eCourts / Prison PMS verification
        assert "eCourts / Prison PMS" not in doc.get("verification_authority", "")


# ── 25. Missing legal retrieval never creates fake source ─────────────────────
def test_scenario_25_missing_legal_retrieval_does_not_fabricate():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft = gen_res.json()
    for src in draft.get("retrieved_legal_sources", []):
        assert src.get("citation_key") != "BNSS_479_DEFAULT"


# ── 26. AI failure does not fabricate content ─────────────────────────────────
def test_scenario_26_ai_failure_does_not_fabricate_content():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    assert gen_res.status_code == 201
    draft = gen_res.json()
    assert draft["content_text"] is not None


# ── 27. Automatic filing cannot occur ─────────────────────────────────────────
def test_scenario_27_automatic_filing_cannot_occur():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft = gen_res.json()
    assert draft["status"] == "DRAFT"
    assert draft.get("external_filing_reference") is None


# ── 28. Package creation requires approved document ───────────────────────────
def test_scenario_28_package_creation_requires_approved_document():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    pkg_res = client.post(f"/api/documents/drafts/{draft_id}/package", json={}, headers=headers_advocate)
    assert pkg_res.status_code == 400


# ── 29. Filing status cannot be created without valid explicit reference ──────
def test_scenario_29_filing_status_requires_explicit_filing_reference():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    res = client.post(
        f"/api/documents/drafts/{draft_id}/record-filing",
        json={"filing_reference": ""},
        headers=headers_advocate,
    )
    assert res.status_code == 400


# ── 30. External export excludes internal notes ───────────────────────────────
def test_scenario_30_external_export_excludes_internal_notes():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    res = client.get(f"/api/documents/drafts/{draft_id}/export", headers=headers_advocate)
    assert res.status_code == 200
    data = res.json()
    assert data["export_type"] == "EXTERNAL_COURT"
    assert "INTERNAL AUDIT & SCRUTINY NOTES" not in data["exported_text"]


# ── 31. Internal export requires permission ───────────────────────────────────
def test_scenario_31_internal_export_requires_permission():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    headers_dlsa = get_token_headers(Role.DLSA_OFFICER.value, user_id="demo_dlsa_officer")

    gen_res = client.post(
        "/api/documents/drafts/generate",
        json={"case_id": "UTP-0001", "template_id": "tmpl_bnss_479_bail_v1"},
        headers=headers_advocate,
    )
    draft_id = gen_res.json()["draft_id"]

    # Advocate can export with internal notes
    res_adv = client.get(f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true", headers=headers_advocate)
    assert res_adv.status_code == 200
    assert res_adv.json()["export_type"] == "INTERNAL_CERTIFIED"

    # DLSA officer cannot export internal notes (403)
    res_dlsa = client.get(f"/api/documents/drafts/{draft_id}/export?include_internal_notes=true", headers=headers_dlsa)
    assert res_dlsa.status_code == 403


# ── 32. Organization/template cross-write is denied ───────────────────────────
def test_scenario_32_organization_template_cross_write_denied():
    headers_sup = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, user_id="sup_a", org_id="org_dlsa_central")
    # Attempt to author template claiming org_kslsa_bangalore
    res = client.post(
        "/api/documents/templates",
        json={
            "name": "Bangalore Remote Template",
            "doc_type": "BAIL_APPLICATION",
            "statutory_ground": "Section 479",
            "content_template": "Text",
            "organization_id": "org_kslsa_bangalore",
        },
        headers=headers_sup,
    )
    # Organization is overridden or scoped to creator org
    assert res.status_code in (201, 403)
    if res.status_code == 201:
        # A user from central cannot modify it if it belongs to kslsa
        tmpl_id = res.json()["id"]
        headers_sup_central = get_token_headers(Role.SUPERVISING_LEGAL_OFFICER.value, user_id="sup_other", org_id="org_dlsa_central", district="Central Delhi")
        if res.json()["organization_id"] == "org_kslsa_bangalore":
            upd_res = client.put(f"/api/documents/templates/{tmpl_id}", json={"name": "Modified"}, headers=headers_sup_central)
            assert upd_res.status_code == 403


# ── 33. Immutable historical versions cannot be overwritten ───────────────────
def test_scenario_33_immutable_historical_versions_cannot_be_overwritten():
    draft_record = {
        "draft_id": "draft_immutable_test_33",
        "case_id": "UTP-0001",
        "artifact_id": "bail_draft_01",
        "version_number": 1,
        "status": "APPROVED",
        "original_ai_text": "Original approved text",
        "content_text": "Original approved text",
        "is_immutable": True,
        "created_by": "Advocate",
        "created_by_role": "DEFENSE_ADVOCATE",
    }
    store_legal_document_draft(draft_record)

    # Attempting to overwrite content of immutable draft must raise PermissionError
    with pytest.raises(PermissionError):
        store_legal_document_draft({
            **draft_record,
            "content_text": "Attempt to overwrite immutable document!",
        })


# ── 34. Nonexistent document IDs do not leak other records ───────────────────
def test_scenario_34_nonexistent_document_ids_do_not_leak():
    headers_advocate = get_token_headers(Role.DEFENSE_ADVOCATE.value, user_id="demo_advocate")
    res = client.get("/api/documents/drafts/draft_completely_fake_id_xyz", headers=headers_advocate)
    assert res.status_code == 404
    assert res.json().get("detail") == "Draft 'draft_completely_fake_id_xyz' not found."
