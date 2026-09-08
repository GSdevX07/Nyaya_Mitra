"""
tests/test_analytics_and_reporting.py — Automated Test Suite for Nyaya Mitra
Analytics, Reporting, Measurable Impact Intelligence, Controlled Exports, and Scheduled Reports.
"""
from __future__ import annotations

import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.auth.user_store import get_user_by_id
from app.analytics.service import AnalyticsService
from app.analytics.export_service import ExportService
from app.analytics.scheduled_reports import ScheduledReportManager
from app.analytics.schemas import (
    ExportRequest,
    ExportFormat,
    ScheduledReportCreateRequest,
    ReportFrequency,
)
from app.database import init_db, get_db_connection


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database tables and demo seed are active."""
    init_db()


@pytest.fixture
def dlsa_user():
    user = get_user_by_id("demo_dlsa_officer")
    assert user is not None
    return user


@pytest.fixture
def admin_user():
    user = get_user_by_id("demo_platform_admin")
    assert user is not None
    return user


@pytest.fixture
def advocate_user():
    user = get_user_by_id("demo_advocate")
    assert user is not None
    return user


@pytest.fixture
def dlsa_client(dlsa_user):
    role_val = dlsa_user.role.value if hasattr(dlsa_user.role, "value") else str(dlsa_user.role)
    token = create_access_token(
        subject=dlsa_user.id,
        role=role_val,
        org_id=getattr(dlsa_user, "org_id", "org_dlsa_central"),
        facility_ids=dlsa_user.facility_ids,
        extra_claims={"district": dlsa_user.district},
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def admin_client(admin_user):
    role_val = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)
    token = create_access_token(
        subject=admin_user.id,
        role=role_val,
        org_id=getattr(admin_user, "org_id", "org_dlsa_central"),
        facility_ids=admin_user.facility_ids,
        extra_claims={"district": admin_user.district},
    )
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


# ── 1. 13 Operational Dashboards Tests ────────────────────────────────────────

def test_13_dashboards_generation(dlsa_user):
    dash = AnalyticsService.get_all_dashboards(dlsa_user)
    assert dash is not None

    # Verify all 13 dimensions exist and are populated
    assert len(dash.people_in_custody) > 0
    assert dash.legal_aid_attention.total_attention_required >= 0
    assert dash.approaching_thresholds.total_flagged >= 0
    assert dash.overdue_actions.total_overdue >= 0
    assert dash.missing_documents.total_cases_evaluated > 0
    assert dash.time_intake_to_assignment.total_cases_measured >= 0
    assert dash.time_intake_to_assignment.average_hours > 0
    assert dash.time_assignment_to_review.average_hours > 0
    assert dash.unresolved_conflicts.total_unresolved >= 0
    assert dash.upcoming_hearings.next_30_days_count >= 0
    assert dash.release_outcomes.total_releases_recorded >= 0
    assert dash.notification_delivery.total_dispatched >= 0
    assert dash.notification_delivery.delivery_success_rate_pct >= 90.0
    assert dash.integration_health.total_connectors > 0
    assert dash.integration_health.overall_uptime_pct > 90.0
    assert dash.workload_by_team.active_panel_advocates_count > 0


def test_role_based_district_scoping(dlsa_user, admin_user, advocate_user):
    # DLSA user is district scoped
    assert AnalyticsService._is_district_scoped(dlsa_user) is True
    # Admin is not district scoped
    assert AnalyticsService._is_district_scoped(admin_user) is False

    admin_dash = AnalyticsService.get_all_dashboards(admin_user)
    dlsa_dash = AnalyticsService.get_all_dashboards(dlsa_user)

    # Both return valid responses
    assert admin_dash.jurisdiction in ("ALL", "All Jurisdictions") or len(admin_dash.people_in_custody) >= len(dlsa_dash.people_in_custody)

    # Privacy preserving masking test:
    masked_name = AnalyticsService._mask_name_for_privacy("Suresh Kumar", "UTP-0001", count_in_cohort=1, user=dlsa_user)
    assert "S." in masked_name and "Protected Cohort" in masked_name


# ── 2. Executive Leadership Report Tests ──────────────────────────────────────

def test_leadership_report_nalsa_benchmarks(dlsa_user):
    rep = AnalyticsService.get_leadership_report(dlsa_user)
    assert rep is not None
    assert "DLSA / KSLSA" in rep.title
    assert "intake_to_assignment_hours" in rep.turnaround_benchmarks
    assert rep.turnaround_benchmarks["intake_to_assignment_hours"]["nalsa_benchmark"] == 48.0
    assert rep.turnaround_benchmarks["assignment_to_review_hours"]["nalsa_benchmark"] == 72.0
    assert len(rep.operational_trends) > 0
    assert "total_undertrials_monitored" in rep.executive_summary


# ── 3. Measurable Impact Intelligence Tests ───────────────────────────────────

def test_impact_dashboard_truthful_metrics(dlsa_user):
    imp = AnalyticsService.get_impact_dashboard(dlsa_user)
    assert imp is not None
    assert len(imp.indicators) == 6

    # Verify indicators and truthful tags
    indicator_names = [ind.indicator for ind in imp.indicators]
    assert "Fewer Missed Legal-Aid Actions" in indicator_names
    assert "Faster Legal Aid Counsel Assignment" in indicator_names
    assert "Improved Document Completeness" in indicator_names
    assert "Reduced Manual Docket Searching" in indicator_names
    assert "Visibility of Upcoming Court Deadlines" in indicator_names
    assert "Post-Release Continuity & Rehabilitation" in indicator_names

    for ind in imp.indicators:
        assert ind.methodology != ""
        assert ind.improvement_delta != ""
        assert isinstance(ind.is_synthetic, bool)


# ── 4. Controlled Export Engine Tests ─────────────────────────────────────────

def test_controlled_export_csv_and_checksum(dlsa_user):
    req = ExportRequest(
        report_type="LEADERSHIP_REPORT",
        format=ExportFormat.CSV,
        purpose="Quarterly SLSA Monitoring Meeting",
        include_pii=False,
    )
    res = ExportService.generate_export(dlsa_user, req)
    assert res is not None
    assert res.export_id.startswith("exp_")
    assert res.filename.endswith(".csv")
    assert res.record_count > 0
    assert res.checksum_sha256 != ""
    assert res.data_minimized is True

    # Verify SHA-256
    expected_hash = hashlib.sha256(res.content.encode("utf-8")).hexdigest()
    assert res.checksum_sha256 == expected_hash

    # Verify immutable log in export_audit_logs
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, report_type, format, purpose, export_hash FROM export_audit_logs WHERE id = ?", (res.export_id,))
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == res.export_id
    assert row[1] == "LEADERSHIP_REPORT"
    assert row[2] == "CSV"
    assert row[3] == "Quarterly SLSA Monitoring Meeting"
    assert row[4] == res.checksum_sha256


def test_export_mandatory_purpose_validation(dlsa_user):
    from pydantic import ValidationError
    # Short purpose (< 5 characters) must be rejected
    with pytest.raises(ValidationError):
        ExportRequest(
            report_type="ALL_DASHBOARDS",
            format=ExportFormat.JSON,
            purpose="abc",  # too short
        )


def test_export_pii_redaction_for_unprivileged(dlsa_user):
    # Export cases ledger without PII
    req = ExportRequest(
        report_type="CASES_LEDGER",
        format=ExportFormat.JSON,
        purpose="Statistical analysis only",
        include_pii=False,
    )
    res = ExportService.generate_export(dlsa_user, req)
    data = json.loads(res.content)
    assert data["metadata"]["data_minimized"] is True
    for rec in data["records"]:
        assert "***" in rec["accused_name"] or rec["accused_name"] == "REDACTED"


# ── 5. Scheduled Reports Framework Tests ──────────────────────────────────────

def test_scheduled_report_lifecycle(dlsa_user):
    req = ScheduledReportCreateRequest(
        title="Bi-Weekly DLSA Operational Summary",
        report_type="LEADERSHIP_REPORT",
        frequency=ReportFrequency.WEEKLY,
        recipients=["dlsa.officer@delhi.gov.in"],
    )
    record = ScheduledReportManager.create_schedule(dlsa_user, req)
    assert record.id.startswith("sch_")
    assert record.is_active is True
    assert record.frequency == "WEEKLY"
    assert record.next_run_at is not None

    # List schedules
    schedules = ScheduledReportManager.list_schedules(dlsa_user)
    assert any(s.id == record.id for s in schedules)

    # Trigger execution
    exec_record = ScheduledReportManager.trigger_schedule(dlsa_user, record.id)
    assert exec_record.id.startswith("exec_")
    assert exec_record.status == "SUCCESS"
    assert "secure_link" in exec_record.summary_content


# ── 6. REST API Endpoints Integration Tests ───────────────────────────────────

def test_api_get_dashboards(dlsa_client):
    res = dlsa_client.get("/api/analytics/dashboards")
    assert res.status_code == 200
    data = res.json()
    assert "people_in_custody" in data
    assert "legal_aid_attention" in data
    assert "integration_health" in data


def test_api_get_single_dashboard(dlsa_client):
    res = dlsa_client.get("/api/analytics/dashboards/custody")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_api_get_leadership_report(dlsa_client):
    res = dlsa_client.get("/api/analytics/leadership-report")
    assert res.status_code == 200
    data = res.json()
    assert "turnaround_benchmarks" in data
    assert "operational_trends" in data


def test_api_get_impact(dlsa_client):
    res = dlsa_client.get("/api/analytics/impact")
    assert res.status_code == 200
    data = res.json()
    assert "indicators" in data
    assert len(data["indicators"]) == 6


def test_api_post_export(dlsa_client):
    payload = {
        "report_type": "IMPACT_METRICS",
        "format": "JSON",
        "purpose": "Statutory Annual Performance Audit",
        "include_pii": False,
    }
    res = dlsa_client.post("/api/analytics/export", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "checksum_sha256" in data
    assert data["format"] == "JSON"


def test_api_get_export_audit_logs(dlsa_client):
    res = dlsa_client.get("/api/analytics/export/audit-logs")
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)


def test_api_schedules_endpoints(admin_client):
    # 1. Create schedule
    payload = {
        "title": "Statewide Monthly Oversight",
        "report_type": "LEADERSHIP_REPORT",
        "frequency": "MONTHLY",
        "recipients": ["secretary.slsa@delhi.gov.in"],
    }
    res = admin_client.post("/api/analytics/schedules", json=payload)
    assert res.status_code == 200
    sch_data = res.json()
    schedule_id = sch_data["id"]

    # 2. List schedules
    list_res = admin_client.get("/api/analytics/schedules")
    assert list_res.status_code == 200
    assert any(s["id"] == schedule_id for s in list_res.json())

    # 3. Trigger schedule
    trigger_res = admin_client.post(f"/api/analytics/schedules/{schedule_id}/trigger")
    assert trigger_res.status_code == 200
    assert trigger_res.json()["status"] == "SUCCESS"
