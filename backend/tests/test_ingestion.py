"""
test_ingestion.py — Comprehensive Unit & Integration Tests for Stage 04 Data Ingestion Layer.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.ingestion.connectors.spreadsheet_connector import SpreadsheetConnector
from app.ingestion.connectors.manual_entry_connector import ManualEntryConnector
from app.ingestion.models import ConflictStatus, MatchConfidence
from app.ingestion.pipeline import get_ingestion_pipeline, resolve_field_conflict, _PENDING_CONFLICTS

client = TestClient(app)

_admin_token = create_access_token(
    subject="admin_ingestion_test",
    role=Role.PLATFORM_ADMIN.value,
    org_id="org_dlsa_central",
)
AUTH_HEADERS = {"Authorization": f"Bearer {_admin_token}"}


def test_connector_registry():
    """Verify all 5 core connectors are registered and accessible."""
    resp = client.get("/ingestion/connectors", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    connectors = resp.json()
    assert len(connectors) >= 5
    types = [c["connector_type"] for c in connectors]
    assert "FILE_IMPORT_CSV" in types
    assert "MANUAL_CONTROLLED_ENTRY" in types
    assert "SIMULATED_GOV_INTEGRATION" in types


def test_ingestion_dashboard_telemetry():
    """Verify ingestion operations dashboard returns healthy telemetry."""
    resp = client.get("/ingestion/dashboard", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "connectors" in data
    assert "total_records_ingested" in data
    assert "conflicts_awaiting_review" in data
    assert data["active_feeds_count"] >= 3


def test_spreadsheet_csv_import():
    """Verify CSV upload parsing, field normalization, and case ingestion."""
    csv_content = (
        "prisoner_name,age,gender,offense,arrest_date,custody_days,jail_location,court_name\n"
        "Ramanujam Iyer,48,Male,BNS 303(2),2024-09-15,350,Central Jail 3,District Sessions Court\n"
        "Deepak Verma,26,Male,IPC 379,2024-11-01,290,Mandoli Jail,CJM Court Delhi\n"
    )

    files = {"file": ("inmate_roll.csv", csv_content.encode("utf-8"), "text/csv")}
    resp = client.post("/ingestion/upload", files=files, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "success"
    assert res["total_records"] == 2
    assert res["valid_records"] == 2


def test_manual_intake_gateway():
    """Verify controlled manual entry intake desk validation and ingestion."""
    payload = {
        "full_name": "Aakash Banerjee",
        "gender": "Male",
        "age": 31,
        "offense_sections": ["BNS 303(2)", "BNS 317(2)"],
        "arrest_date": "2024-10-10",
        "custody_days": 310,
        "max_sentence_days_for_offense": 730,
        "jail_location": "Tihar Jail No 1",
        "police_station": "Kotwali PS",
        "relative_name": "Soma Banerjee",
        "relative_phone": "+91 98300 11223",
    }

    resp = client.post("/ingestion/manual-entry", json=payload, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "Aakash Banerjee" in data["message"]


def test_simulated_eprisons_sync():
    """Verify manual/automated sync trigger on [SIMULATED] ePrisons connector."""
    resp = client.post("/ingestion/connectors/conn_simulated_eprisons/sync", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    res = resp.json()
    assert res["status"] == "success"
    assert res["records_ingested"] >= 2
    assert res["valid_records"] >= 2


def test_conflict_detection_and_human_resolution():
    """
    Verify that submitting conflicting arrest date on an existing case
    does not silently overwrite, but generates a FieldConflict in the review queue.
    """
    # 1. Submit conflicting observation for UTP-0001
    pipeline = get_ingestion_pipeline()
    spreadsheet_conn = SpreadsheetConnector()

    conflicting_record = {
        "prisoner_name": "Suresh Patel",  # UTP-0001
        "cnr_number": "DLCT010049212025",
        "arrest_date": "2024-06-01",  # Conflicting with canonical 2025-01-10
        "custody_days": 420,           # Conflicting with canonical 200
        "offense_sections": ["IPC 323", "IPC 341"],
    }

    batch = pipeline.ingest_record_batch(spreadsheet_conn, [conflicting_record])
    assert batch.conflicts_detected >= 1

    # 2. Query pending conflicts endpoint
    conflicts_resp = client.get("/ingestion/conflicts", headers=AUTH_HEADERS)
    assert conflicts_resp.status_code == 200
    conflicts = conflicts_resp.json()
    assert len(conflicts) >= 1

    target_conflict = next((c for c in conflicts if c["case_id"] == "UTP-0001"), None)
    assert target_conflict is not None
    assert target_conflict["severity"] in ("CRITICAL", "MEDIUM")

    # 3. Resolve conflict via human review gateway
    conflict_id = target_conflict["id"]
    resolve_resp = client.post(
        f"/ingestion/conflicts/{conflict_id}/resolve",
        json={"resolution": "KEPT_CANONICAL", "notes": "Verified against physical remand sheet."},
        headers=AUTH_HEADERS,
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["resolution"] == "KEPT_CANONICAL"


def test_probabilistic_identity_matcher():
    """Verify probabilistic composite matcher generates certain, probable, or uncertain candidates."""
    pipeline = get_ingestion_pipeline()
    from app.database import get_all_cases
    cases = get_all_cases()

    # Exact CNR Match -> Certain
    rec_certain = {"full_name": "Different Name", "cnr_number": "DLCT010049212025"}
    _, conf_1, score_1, _ = pipeline.match_existing_identity(rec_certain, cases)
    assert conf_1 == MatchConfidence.CERTAIN
    assert score_1 == 1.0

    # Composite Probable / Uncertain match
    rec_prob = {
        "full_name": "Suresh Patel",
        "age": 28,
        "police_station": "Kotwali PS",
        "relative_name": "Mahesh Patel",
    }
    _, conf_2, score_2, _ = pipeline.match_existing_identity(rec_prob, cases)
    assert score_2 >= 0.50

    # Completely New Entity
    rec_new = {"full_name": "Zorawar Singh Gill", "age": 55, "police_station": "Amritsar Cantt"}
    _, conf_3, score_3, _ = pipeline.match_existing_identity(rec_new, cases)
    assert conf_3 == MatchConfidence.NEW_ENTITY
