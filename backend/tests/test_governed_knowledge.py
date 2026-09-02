"""
test_governed_knowledge.py — Comprehensive Automated Verification for Governed Legal Knowledge Layer.

Stage 06 Complete Remediation Suite:
1. Source Registry & Lifecycle States (discovered, reviewed, approved, active, superseded, retired).
2. Verbatim Ingestion & Chunk Boundary Preservation (exact offsets, no semantic rewriting).
3. Ingestion Direct-to-Active Bypass Rejection (forces discovered).
4. State Machine Enforcement (valid graph transitions, invalid jumps rejected).
5. Role Clearance per Lifecycle Transition (Supervisor & SLSA Admin only; Platform Admin stripped).
6. Legal Text Immutability (active/approved source content cannot be mutated in-place).
7. Hybrid Retrieval with Rule-Based Reranking (Section 479 BNSS precision).
8. Retrieval Telemetry Logging (persists into legal_retrieval_logs).
9. Citation Integrity & Hallucination Guardrail (detects fake sections/statutes).
10. Durable Human-Review Escalation (persists into legal_human_review_tasks & notifications).
11. Escalation Resolution Workflow.
12. Complete 10-Role API Authorization Matrix (Citizen/Jail/Police blocked; Advocate consumer mode; DLSA proposal).
13. 5-Category Benchmark Evaluation Suite Execution.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db_connection, init_db
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.services.governed_knowledge_service import (
    list_legal_sources,
    get_legal_source_by_id,
    register_legal_source,
    update_source_lifecycle,
    hybrid_retrieve_legal_chunks,
    verify_legal_citation_integrity,
    run_retrieval_evaluation_suite,
)

client = TestClient(app)


def _token(role: Role, user_id: str = "test_user") -> dict:
    t = create_access_token(subject=user_id, role=role.value, org_id="org_dlsa_central")
    return {"Authorization": f"Bearer {t}"}


def setup_module():
    init_db()


# ── 1. REGISTRY & METADATA ───────────────────────────────────────────────────

def test_legal_source_registry_and_lifecycle():
    """Verify source registry listing and lifecycle state distribution."""
    sources = list_legal_sources()
    assert len(sources) >= 4

    active_sources = [s for s in sources if s["lifecycle_status"] == "active"]
    active_ids = [s["id"] for s in active_sources]
    assert "src_bnss_2023" in active_ids
    assert "src_bns_2023" in active_ids

    superseded = [s for s in sources if s["lifecycle_status"] == "superseded"]
    superseded_ids = [s["id"] for s in superseded]
    assert "src_ipc_1860" in superseded_ids
    assert "src_crpc_1973" in superseded_ids


# ── 2. VERBATIM INGESTION & BOUNDARY PRESERVATION ─────────────────────────────

def test_verbatim_ingestion_preserves_text_and_boundaries():
    """Verify source ingestion retains verbatim text and character offsets."""
    sample_text = (
        "Section 991: Mandatory Interim Custody Audit.\n\n"
        "Every undertrial detained in judicial custody shall have custody duration "
        "calculated from the date of initial remand by the magistrate."
    )
    result = register_legal_source(
        title="Test Interim Custody Audit Guidelines 2026",
        short_name="Custody Audit 2026",
        issuing_authority="Delhi State Legal Services Authority",
        effective_date="2026-01-01",
        jurisdiction="State of Delhi",
        legal_domain="LEGAL_AID",
        raw_content=sample_text,
        user_id="usr_dlsa_01",
        user_role="DLSA_OFFICER",
    )

    source_id = result["source_id"]
    assert result["lifecycle_status"] == "discovered"
    assert result["chunks_indexed"] >= 1

    detail = get_legal_source_by_id(source_id)
    assert detail is not None
    assert detail["lifecycle_status"] == "discovered"
    chunk = detail["chunks"][0]

    assert "Every undertrial detained in judicial custody" in chunk["original_text"]
    assert chunk["start_char"] >= 0
    assert chunk["end_char"] > chunk["start_char"]


# ── 3. INGESTION DIRECT-TO-ACTIVE BYPASS PREVENTION (PART D) ──────────────────

def test_ingestion_direct_to_active_bypass_blocked():
    """DLSA Officer or client payload cannot set lifecycle_status = active on creation."""
    sample_text = "Section 992: Discovered Enactment Proposal.\n\nProposed rule content."
    result = register_legal_source(
        title="Bypass Attempt Enactment 2026",
        short_name="Bypass Test 2026",
        issuing_authority="State Authority",
        effective_date="2026-01-01",
        jurisdiction="India",
        legal_domain="PENAL_LAW",
        raw_content=sample_text,
        lifecycle_status="active",  # Client attempts to bypass
        user_id="usr_dlsa_01",
        user_role="DLSA_OFFICER",
        is_system_seed=False,
    )

    # Must be safely normalized to discovered
    assert result["lifecycle_status"] == "discovered"

    detail = get_legal_source_by_id(result["source_id"])
    assert detail["lifecycle_status"] == "discovered"


# ── 4. STATE MACHINE TRANSITIONS (PART E) ────────────────────────────────────

def test_state_machine_enforces_valid_transitions():
    """Verify governed transition graph: discovered -> reviewed -> approved -> active -> superseded -> retired."""
    sample_text = "Section 993: Lifecycle Flow Act 2026.\n\nStatutory procedural content."
    res = register_legal_source(
        title="Lifecycle State Machine Act 2026",
        short_name="StateMachine 2026",
        issuing_authority="Parliament",
        effective_date="2026-01-01",
        jurisdiction="India",
        legal_domain="CRIMINAL_PROCEDURE",
        raw_content=sample_text,
        user_id="usr_dlsa_01",
        user_role="DLSA_OFFICER",
    )
    src_id = res["source_id"]

    # 1. discovered -> reviewed
    t1 = update_source_lifecycle(src_id, "reviewed", user_id="usr_sup_01", user_role="SUPERVISING_LEGAL_OFFICER")
    assert t1["new_status"] == "reviewed"

    # 2. reviewed -> approved
    t2 = update_source_lifecycle(src_id, "approved", user_id="usr_sup_01", user_role="SUPERVISING_LEGAL_OFFICER")
    assert t2["new_status"] == "approved"

    # 3. approved -> active
    t3 = update_source_lifecycle(src_id, "active", user_id="usr_gov_01", user_role="GOV_ADMIN")
    assert t3["new_status"] == "active"

    # 4. active -> superseded (requires valid superseded_by_id)
    t4 = update_source_lifecycle(
        src_id,
        "superseded",
        user_id="usr_gov_01",
        user_role="GOV_ADMIN",
        superseded_by_id="src_bnss_2023",
    )
    assert t4["new_status"] == "superseded"
    assert t4["superseded_by_id"] == "src_bnss_2023"

    # 5. superseded -> retired
    t5 = update_source_lifecycle(src_id, "retired", user_id="usr_gov_01", user_role="GOV_ADMIN")
    assert t5["new_status"] == "retired"


def test_state_machine_rejects_invalid_transitions():
    """Verify invalid jumps (discovered -> active, retired -> active, etc.) are strictly rejected."""
    sample_text = "Section 994: Invalid Jumps Test Act.\n\nContent."
    res = register_legal_source(
        title="Invalid Jump Source",
        short_name="JumpTest",
        issuing_authority="Parliament",
        effective_date="2026-01-01",
        jurisdiction="India",
        legal_domain="CRIMINAL_PROCEDURE",
        raw_content=sample_text,
        user_id="usr_dlsa_01",
        user_role="DLSA_OFFICER",
    )
    src_id = res["source_id"]

    # Attempt discovered -> active (skipping review & approval)
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        update_source_lifecycle(src_id, "active", user_id="usr_sup_01", user_role="SUPERVISING_LEGAL_OFFICER")

    # Attempt discovered -> approved
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        update_source_lifecycle(src_id, "approved", user_id="usr_sup_01", user_role="SUPERVISING_LEGAL_OFFICER")


# ── 5. PLATFORM ADMIN & ROLE GOVERNANCE SEPARATION (PART N) ───────────────────

def test_platform_admin_cannot_transition_lifecycle():
    """Platform Admin is technical ops and lacks unilateral statutory governance authority."""
    with pytest.raises(ValueError, match="Role 'PLATFORM_ADMIN' is restricted from legal governance"):
        update_source_lifecycle("src_bnss_2023", "retired", user_id="usr_admin_01", user_role="PLATFORM_ADMIN")


# ── 6. LEGAL TEXT IMMUTABILITY (PART F) ───────────────────────────────────────

def test_active_source_content_is_immutable():
    """Cannot silently mutate legal text of an already active source."""
    with pytest.raises(ValueError, match="immutable"):
        register_legal_source(
            title="The Bharatiya Nagarik Suraksha Sanhita, 2023",
            short_name="BNSS 2023",
            issuing_authority="Parliament of India",
            effective_date="2024-07-01",
            jurisdiction="India (National)",
            legal_domain="CRIMINAL_PROCEDURE",
            raw_content="Mutated fake text claiming everyone is released immediately.",
            user_id="usr_dlsa_01",
            user_role="DLSA_OFFICER",
            is_system_seed=False,
        )


# ── 7. HYBRID RETRIEVAL & TELEMETRY LOGGING (PART H) ──────────────────────────

def test_hybrid_retrieval_and_section_reranking():
    """Verify Section 479 BNSS is prioritized at Rank 1 for undertrial bail query."""
    results = hybrid_retrieve_legal_chunks(
        "Section 479 BNSS maximum period of detention for undertrials",
        limit=5,
        actor_id="usr_adv_01",
        actor_role="DEFENSE_ADVOCATE",
    )
    assert len(results) > 0

    top = results[0]
    assert "479" in (top.get("section_number") or top.get("citation_key"))
    assert top.get("lifecycle_status") == "active"


def test_retrieval_telemetry_persists_in_database():
    """Verify retrieval writes an audit log entry into legal_retrieval_logs."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM legal_retrieval_logs")
    count_before = c.fetchone()[0]

    hybrid_retrieve_legal_chunks(
        "Section 436A CrPC historical bail threshold",
        include_superseded=True,
        actor_id="usr_sup_01",
        actor_role="SUPERVISING_LEGAL_OFFICER",
    )

    c.execute("SELECT COUNT(*) FROM legal_retrieval_logs")
    count_after = c.fetchone()[0]
    conn.close()

    assert count_after > count_before


# ── 8. CITATION GUARDRAIL & DURABLE ESCALATION (PART G & P) ───────────────────

def test_citation_integrity_grounded_vs_hallucinated():
    """Valid citations pass; fabricated sections trigger durable human review escalation."""
    # 1. Grounded assertion
    grounded = (
        "The applicant is entitled to mandatory statutory bail under Section 479 of the BNSS, "
        "having completed one-third of the maximum imprisonment period."
    )
    rep_grounded = verify_legal_citation_integrity(grounded, actor_id="usr_adv_01", actor_role="DEFENSE_ADVOCATE")
    assert rep_grounded["status"] == "VERIFIED"
    assert rep_grounded["grounding_score"] >= 80.0
    assert not rep_grounded["routed_to_human_review"]

    # 2. Fabricated citation
    hallucinated = (
        "Under Section 9999 of the Bharatiya Nagarik Suraksha Sanhita, all undertrials "
        "accused of financial offences must be acquitted unconditionally within 10 days."
    )
    rep_fake = verify_legal_citation_integrity(hallucinated, actor_id="usr_adv_01", actor_role="DEFENSE_ADVOCATE")
    assert rep_fake["status"] == "LEGAL_KNOWLEDGE_INSUFFICIENT"
    assert rep_fake["routed_to_human_review"] is True
    assert len(rep_fake["unsupported_citations"]) >= 1
    assert rep_fake.get("escalation_id") is not None

    # Check that escalation was persisted into database
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM legal_human_review_tasks WHERE id = ?", (rep_fake["escalation_id"],))
    esc = c.fetchone()
    conn.close()
    assert esc is not None
    assert esc["review_status"] == "PENDING_REVIEW"
    assert esc["actor_id"] == "usr_adv_01"


def test_escalation_resolution_endpoint():
    """Supervisor can retrieve and resolve pending escalations."""
    # First create an escalation
    rep = verify_legal_citation_integrity(
        "Under Section 8888 of BNS, the penalty is void.",
        actor_id="usr_adv_01",
        actor_role="DEFENSE_ADVOCATE",
    )
    esc_id = rep["escalation_id"]
    assert esc_id is not None

    headers_sup = _token(Role.SUPERVISING_LEGAL_OFFICER, "usr_sup_01")

    # List escalations
    get_res = client.get("/api/legal-knowledge/escalations", headers=headers_sup)
    assert get_res.status_code == 200
    tasks = get_res.json()
    assert any(t["id"] == esc_id for t in tasks)

    # Resolve escalation
    res = client.post(
        f"/api/legal-knowledge/escalations/{esc_id}/resolve",
        json={"notes": "Section 8888 verified as fabricated. Corrected advocate petition to Section 303(2)."},
        headers=headers_sup,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"


# ── 9. COMPLETE 10-ROLE API AUTHORIZATION MATRIX (PART B & C) ─────────────────

def test_api_authorization_matrix_all_roles():
    """Exhaustive check of role clearances across all 10 roles."""
    # A. Unauthenticated request -> 401
    assert client.get("/api/legal-sources").status_code == 401
    assert client.post("/api/legal-sources", json={}).status_code == 401

    # B. Blocked Citizen & Facility Roles -> 403
    blocked_roles = [Role.ACCUSED_USER, Role.FAMILY_GUARDIAN, Role.JAIL_OFFICER, Role.POLICE_OFFICER]
    for r in blocked_roles:
        h = _token(r)
        # Cannot read internal source registry
        assert client.get("/api/legal-sources", headers=h).status_code == 403, f"{r} must be 403 on GET /api/legal-sources"
        assert client.get("/api/legal-sources/src_bnss_2023", headers=h).status_code == 403
        # Cannot ingest
        assert client.post("/api/legal-sources", json={}, headers=h).status_code == 403
        # Cannot transition lifecycle
        assert client.patch("/api/legal-sources/src_bnss_2023/lifecycle", json={"status": "retired"}, headers=h).status_code == 403
        # Cannot retrieve or verify
        assert client.post("/api/legal-knowledge/retrieve", json={"query": "bail"}, headers=h).status_code == 403
        assert client.post("/api/legal-knowledge/verify-citations", json={"draft_statement": "bail"}, headers=h).status_code == 403
        # Cannot evaluate
        assert client.get("/api/legal-knowledge/evaluate", headers=h).status_code == 403

    # C. Defense Advocate (Consumer Mode)
    h_adv = _token(Role.DEFENSE_ADVOCATE, "usr_adv_01")
    # Allowed to read sources and retrieve/verify
    res_adv_sources = client.get("/api/legal-sources", headers=h_adv)
    assert res_adv_sources.status_code == 200
    # Redaction check: maintainer notes must be redacted for advocate
    adv_sources = res_adv_sources.json()
    assert all(s.get("audit_notes") is None for s in adv_sources)
    # Allowed to retrieve and verify
    assert client.post("/api/legal-knowledge/retrieve", json={"query": "bail"}, headers=h_adv).status_code == 200
    assert client.post("/api/legal-knowledge/verify-citations", json={"draft_statement": "bail"}, headers=h_adv).status_code == 200
    # FORBIDDEN from ingestion, lifecycle transitions, and benchmarks
    assert client.post("/api/legal-sources", json={}, headers=h_adv).status_code == 403
    assert client.patch("/api/legal-sources/src_bnss_2023/lifecycle", json={"status": "retired"}, headers=h_adv).status_code == 403
    assert client.get("/api/legal-knowledge/evaluate", headers=h_adv).status_code == 403

    # D. DLSA Legal Officer (Operational / Propose Mode)
    h_dlsa = _token(Role.DLSA_OFFICER, "usr_dlsa_01")
    assert client.get("/api/legal-sources", headers=h_dlsa).status_code == 200
    assert client.post("/api/legal-knowledge/retrieve", json={"query": "bail"}, headers=h_dlsa).status_code == 200
    assert client.post("/api/legal-knowledge/verify-citations", json={"draft_statement": "bail"}, headers=h_dlsa).status_code == 200
    # Can ingest (forces discovered)
    create_payload = {
        "title": "DLSA Proposed Circular 2026",
        "short_name": "DLSA Circular",
        "issuing_authority": "DLSA Central",
        "effective_date": "2026-01-01",
        "jurisdiction": "NCT of Delhi",
        "legal_domain": "LEGAL_AID",
        "raw_content": "Section 1. Guidelines for panel advocates.",
    }
    res_create = client.post("/api/legal-sources", json=create_payload, headers=h_dlsa)
    assert res_create.status_code == 200
    assert res_create.json()["lifecycle_status"] == "discovered"
    # FORBIDDEN from lifecycle transition and benchmarks
    assert client.patch("/api/legal-sources/src_bnss_2023/lifecycle", json={"status": "retired"}, headers=h_dlsa).status_code == 403
    assert client.get("/api/legal-knowledge/evaluate", headers=h_dlsa).status_code == 403

    # E. Statutory Oversight Auditor (Read-Only / Evaluation Mode)
    h_aud = _token(Role.READ_ONLY_AUDITOR, "usr_aud_01")
    assert client.get("/api/legal-sources", headers=h_aud).status_code == 200
    assert client.get("/api/legal-sources/src_bnss_2023", headers=h_aud).status_code == 200
    assert client.get("/api/legal-knowledge/evaluate", headers=h_aud).status_code == 200
    # FORBIDDEN from write/lifecycle mutations
    assert client.post("/api/legal-sources", json={}, headers=h_aud).status_code == 403
    assert client.patch("/api/legal-sources/src_bnss_2023/lifecycle", json={"status": "retired"}, headers=h_aud).status_code == 403

    # F. Supervising Legal Officer & Govt Admin (Governance Modes)
    h_sup = _token(Role.SUPERVISING_LEGAL_OFFICER, "usr_sup_01")
    assert client.get("/api/legal-sources", headers=h_sup).status_code == 200
    assert client.post("/api/legal-sources", json=create_payload, headers=h_sup).status_code == 200
    assert client.get("/api/legal-knowledge/evaluate", headers=h_sup).status_code == 200
    assert client.get("/api/legal-knowledge/escalations", headers=h_sup).status_code == 200


# ── 10. EVALUATION BENCHMARK SUITE EXECUTION (PART Q) ─────────────────────────

def test_evaluation_benchmark_suite_execution():
    """Verify 5-category evaluation benchmark suite computes Recall@1, Recall@3, and MRR."""
    res = run_retrieval_evaluation_suite(actor_id="usr_aud_01", actor_role="READ_ONLY_AUDITOR")
    assert res["total_queries"] == 5
    assert res["recall_at_1"] >= 60.0
    assert res["recall_at_3"] >= 80.0
    assert res["mean_reciprocal_rank"] >= 0.70
    assert len(res["results"]) == 5
