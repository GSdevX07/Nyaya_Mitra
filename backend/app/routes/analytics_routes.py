"""
routes/analytics_routes.py — REST API Endpoints for Analytics, Aggregations,
Leadership Reports, Impact Intelligence, Controlled Exports, and Scheduled Reports.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user, require_role
from app.auth.roles import Role
from app.auth.user_store import AuthUser
from app.analytics.schemas import (
    AllDashboardsResponse,
    LeadershipReportResponse,
    ImpactDashboardResponse,
    ExportRequest,
    ExportResponse,
    ExportAuditLogRecord,
    ScheduledReportCreateRequest,
    ScheduledReportRecord,
    ScheduledExecutionRecord,
)
from app.analytics.service import AnalyticsService
from app.analytics.export_service import ExportService
from app.analytics.scheduled_reports import ScheduledReportManager

logger = logging.getLogger("nyaya_mitra.analytics.routes")

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboards", response_model=AllDashboardsResponse)
def get_dashboards(
    current_user: AuthUser = Depends(get_current_user),
) -> AllDashboardsResponse:
    """Retrieve all 13 operational dashboards aggregated with role-based scoping."""
    return AnalyticsService.get_all_dashboards(current_user)


@router.get("/dashboards/{dashboard_type}")
def get_single_dashboard(
    dashboard_type: str,
    current_user: AuthUser = Depends(get_current_user),
):
    """Retrieve a single specific dashboard dimension."""
    dtype = dashboard_type.lower()
    if dtype in ("custody", "people_in_custody", "facilities"):
        return AnalyticsService.get_people_in_custody(current_user)
    elif dtype in ("legal_aid", "legal_aid_attention", "attention"):
        return AnalyticsService.get_legal_aid_attention(current_user)
    elif dtype in ("thresholds", "approaching_thresholds"):
        return AnalyticsService.get_approaching_thresholds(current_user)
    elif dtype in ("overdue", "overdue_actions"):
        return AnalyticsService.get_overdue_actions(current_user)
    elif dtype in ("missing_docs", "missing_documents"):
        return AnalyticsService.get_missing_documents(current_user)
    elif dtype in ("turnaround_intake", "time_intake_to_assignment"):
        return AnalyticsService.get_turnaround_intake_to_assignment(current_user)
    elif dtype in ("turnaround_review", "time_assignment_to_review"):
        return AnalyticsService.get_turnaround_assignment_to_review(current_user)
    elif dtype in ("conflicts", "unresolved_conflicts"):
        return AnalyticsService.get_unresolved_conflicts(current_user)
    elif dtype in ("hearings", "upcoming_hearings"):
        return AnalyticsService.get_upcoming_hearings(current_user)
    elif dtype in ("releases", "release_outcomes"):
        return AnalyticsService.get_release_outcomes(current_user)
    elif dtype in ("notifications", "notification_delivery"):
        return AnalyticsService.get_notification_delivery(current_user)
    elif dtype in ("integration", "integration_health", "connectors"):
        return AnalyticsService.get_integration_health(current_user)
    elif dtype in ("workload", "workload_by_team", "team"):
        return AnalyticsService.get_workload_by_team(current_user)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard dimension '{dashboard_type}' not recognized.",
        )


@router.get("/leadership-report", response_model=LeadershipReportResponse)
def get_leadership_report(
    current_user: AuthUser = Depends(get_current_user),
) -> LeadershipReportResponse:
    """
    Retrieve executive leadership report for DLSA/KSLSA leadership and jail administration.
    Includes operational trends, backlog, turnaround times against NALSA targets, and service coverage.
    """
    return AnalyticsService.get_leadership_report(current_user)


@router.get("/impact", response_model=ImpactDashboardResponse)
def get_impact_dashboard(
    current_user: AuthUser = Depends(get_current_user),
) -> ImpactDashboardResponse:
    """
    Retrieve measurable outcomes impact dashboard.
    Tracks fewer missed legal-aid actions, faster assignment, improved document completeness,
    reduced manual searching, upcoming deadline visibility, and post-release continuity.
    """
    return AnalyticsService.get_impact_dashboard(current_user)


@router.post("/export", response_model=ExportResponse)
def export_analytics_data(
    request: ExportRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> ExportResponse:
    """
    Generate controlled data export (CSV, JSON, PDF).
    Enforces mandatory justification/purpose, role-based scoping, PII redaction,
    SHA-256 integrity checksum, and immutable audit logging.
    """
    return ExportService.generate_export(current_user, request)


@router.get("/export/audit-logs", response_model=List[ExportAuditLogRecord])
def get_export_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: AuthUser = Depends(get_current_user),
) -> List[ExportAuditLogRecord]:
    """Retrieve immutable export audit logs."""
    return ExportService.get_audit_logs(current_user, limit=limit)


@router.get("/schedules", response_model=List[ScheduledReportRecord])
def list_scheduled_reports(
    current_user: AuthUser = Depends(get_current_user),
) -> List[ScheduledReportRecord]:
    """List scheduled recurring reports within user jurisdiction."""
    return ScheduledReportManager.list_schedules(current_user)


@router.post("/schedules", response_model=ScheduledReportRecord)
def create_scheduled_report(
    request: ScheduledReportCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
) -> ScheduledReportRecord:
    """Create a periodic scheduled report subscription."""
    return ScheduledReportManager.create_schedule(current_user, request)


@router.post("/schedules/{schedule_id}/trigger", response_model=ScheduledExecutionRecord)
def trigger_scheduled_report(
    schedule_id: str,
    current_user: AuthUser = Depends(get_current_user),
) -> ScheduledExecutionRecord:
    """Trigger immediate execution of a scheduled report generating a minimized summary."""
    return ScheduledReportManager.trigger_schedule(current_user, schedule_id)
