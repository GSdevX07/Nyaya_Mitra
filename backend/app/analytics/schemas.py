"""
app.analytics.schemas — Pydantic models for Analytics, Reporting, Impact Intelligence, Exports, and Schedules.
"""
from __future__ import annotations

import enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DataProvenanceMode(str, enum.Enum):
    REAL = "REAL"
    DEMO_SIMULATION = "DEMO_SIMULATION"
    ESTIMATE = "ESTIMATE"


class ExportFormat(str, enum.Enum):
    CSV = "CSV"
    JSON = "JSON"
    PDF = "PDF"


class ReportFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


# ── 1. People in Custody by Facility ──────────────────────────────────────────

class FacilityCustodyMetric(BaseModel):
    facility_id: str
    facility_name: str
    facility_type: str
    state: str
    district: str
    capacity: int
    current_occupancy: int
    undertrials_count: int
    occupancy_rate_pct: float
    overcrowding_flag: bool


# ── 2. Cases Requiring Legal-Aid Attention ─────────────────────────────────────

class LegalAidAttentionItem(BaseModel):
    case_id: str
    accused_name: str
    facility: str
    status: str
    days_in_intake: int
    urgency_level: str
    assigned_lawyer_id: Optional[str] = None
    reason: str


class LegalAidAttentionMetric(BaseModel):
    total_attention_required: int
    unassigned_cases_count: int
    intake_pending_count: int
    legal_need_identified_count: int
    panel_requests_pending: int
    high_urgency_count: int
    cases: List[LegalAidAttentionItem]


# ── 3. Approaching Statutory Thresholds ────────────────────────────────────────

class ApproachingThresholdItem(BaseModel):
    case_id: str
    accused_name: str
    facility: str
    offense_sections: str
    custody_days: int
    prescribed_max_days: int
    half_sentence_days: int
    third_sentence_days: int
    statutory_category: str
    days_until_threshold: int
    threshold_status: str
    recommended_action: str


class ApproachingThresholdMetric(BaseModel):
    total_flagged: int
    threshold_reached_count: int
    within_15_days_count: int
    within_30_days_count: int
    cases: List[ApproachingThresholdItem]


# ── 4. Overdue Actions ────────────────────────────────────────────────────────

class OverdueActionItem(BaseModel):
    task_id: str
    case_id: str
    title: str
    action_type: str
    assigned_role: str
    assigned_user: Optional[str] = None
    days_overdue: int
    escalation_tier: int
    sla_target_hours: int
    status: str


class OverdueActionMetric(BaseModel):
    total_overdue: int
    critical_overdue_count: int
    tier_2_escalated: int
    tier_3_escalated: int
    tasks: List[OverdueActionItem]


# ── 5. Missing Documents ──────────────────────────────────────────────────────

class MissingDocumentItem(BaseModel):
    case_id: str
    accused_name: str
    facility: str
    total_required: int
    total_present: int
    completeness_pct: float
    missing_docs: List[str]
    present_docs: List[str]
    is_filing_blocked: bool


class MissingDocumentMetric(BaseModel):
    total_cases_evaluated: int
    dockets_complete_count: int
    dockets_incomplete_count: int
    average_completeness_pct: float
    most_frequent_missing: List[Dict[str, Any]]
    cases: List[MissingDocumentItem]


# ── 6. Time from Intake to Assignment ─────────────────────────────────────────

class TurnaroundIntakeToAssignmentMetric(BaseModel):
    total_cases_measured: int
    average_hours: float
    median_hours: float
    target_hours: float = 48.0
    within_sla_pct: float
    trend_direction: str


# ── 7. Time from Assignment to Review ─────────────────────────────────────────

class TurnaroundAssignmentToReviewMetric(BaseModel):
    total_reviews_measured: int
    average_hours: float
    median_hours: float
    target_hours: float = 72.0
    supervisory_approval_rate_pct: float
    trend_direction: str


# ── 8. Unresolved Data Conflicts ──────────────────────────────────────────────

class UnresolvedConflictItem(BaseModel):
    conflict_id: str
    conflict_type: str
    entity_id: str
    description: str
    source_system: str
    confidence_score: float
    requires_human_review: bool
    detected_at: str


class UnresolvedConflictMetric(BaseModel):
    total_unresolved: int
    identity_merge_candidates_count: int
    cross_facility_duplicates_count: int
    connector_divergence_count: int
    conflicts: List[UnresolvedConflictItem]


# ── 9. Upcoming Hearings ──────────────────────────────────────────────────────

class UpcomingHearingItem(BaseModel):
    hearing_id: str
    case_id: str
    accused_name: str
    court_name: str
    hearing_date: str
    days_away: int
    hearing_type: str
    assigned_advocate: str
    purpose: str


class UpcomingHearingMetric(BaseModel):
    next_7_days_count: int
    next_14_days_count: int
    next_30_days_count: int
    by_court_breakdown: List[Dict[str, Any]]
    by_purpose_breakdown: List[Dict[str, Any]]
    hearings: List[UpcomingHearingItem]


# ── 10. Release Outcomes ──────────────────────────────────────────────────────

class ReleaseOutcomeMetric(BaseModel):
    total_releases_recorded: int
    regular_bail_count: int
    section_479_statutory_bail_count: int
    default_bail_count: int
    acquittal_discharge_count: int
    post_release_support_active: int
    surety_compliance_rate_pct: float
    monthly_trend: List[Dict[str, Any]]


# ── 11. Notification Delivery ─────────────────────────────────────────────────

class NotificationDeliveryMetric(BaseModel):
    total_dispatched: int
    in_app_delivered: int
    email_delivered: int
    sms_delivered: int
    whatsapp_delivered: int
    dlq_failures_count: int
    delivery_success_rate_pct: float
    acknowledgement_rate_pct: float
    auto_escalated_count: int


# ── 12. Integration Health ────────────────────────────────────────────────────

class ConnectorHealthSummaryItem(BaseModel):
    connector_id: str
    display_name: str
    connector_type: str
    sync_status: str
    last_sync: Optional[str]
    latency_ms: float
    error_rate_pct: float
    records_processed: int
    records_rejected: int
    is_simulated: bool


class IntegrationHealthMetric(BaseModel):
    total_connectors: int
    healthy_connectors_count: int
    degraded_connectors_count: int
    overall_uptime_pct: float
    connectors: List[ConnectorHealthSummaryItem]


# ── 13. Workload by Team ──────────────────────────────────────────────────────

class AdvocateWorkloadItem(BaseModel):
    advocate_id: str
    name: str
    bar_registration_no: str
    active_cases: int
    district: str
    panel_status: str


class RoleTaskWorkloadItem(BaseModel):
    role: str
    pending_tasks: int
    overdue_tasks: int
    completed_today: int


class WorkloadByTeamMetric(BaseModel):
    active_panel_advocates_count: int
    average_cases_per_advocate: float
    top_advocates: List[AdvocateWorkloadItem]
    role_distribution: List[RoleTaskWorkloadItem]


# ── Complete 13-Dashboard Aggregated Response ─────────────────────────────────

class AllDashboardsResponse(BaseModel):
    user_role: str
    jurisdiction: str
    data_provenance: str
    is_synthetic: bool
    methodology_disclaimer: str
    generated_at: str

    people_in_custody: List[FacilityCustodyMetric]
    legal_aid_attention: LegalAidAttentionMetric
    approaching_thresholds: ApproachingThresholdMetric
    overdue_actions: OverdueActionMetric
    missing_documents: MissingDocumentMetric
    time_intake_to_assignment: TurnaroundIntakeToAssignmentMetric
    time_assignment_to_review: TurnaroundAssignmentToReviewMetric
    unresolved_conflicts: UnresolvedConflictMetric
    upcoming_hearings: UpcomingHearingMetric
    release_outcomes: ReleaseOutcomeMetric
    notification_delivery: NotificationDeliveryMetric
    integration_health: IntegrationHealthMetric
    workload_by_team: WorkloadByTeamMetric


# ── Executive Leadership Report ───────────────────────────────────────────────

class LeadershipReportResponse(BaseModel):
    title: str
    jurisdiction: str
    period: str
    generated_at: str
    data_provenance: str
    is_synthetic: bool
    methodology_disclaimer: str

    executive_summary: Dict[str, Any]
    operational_trends: List[Dict[str, Any]]
    backlog_analysis: Dict[str, Any]
    turnaround_benchmarks: Dict[str, Any]
    service_coverage: Dict[str, Any]


# ── Measurable Outcomes Impact Dashboard ──────────────────────────────────────

class ImpactMetricItem(BaseModel):
    indicator: str
    measured_value: str
    baseline_value: str
    improvement_delta: str
    description: str
    is_synthetic: bool
    methodology: str


class ImpactDashboardResponse(BaseModel):
    title: str
    generated_at: str
    data_provenance: str
    is_synthetic: bool
    methodology_disclaimer: str

    fewer_missed_actions_pct: float
    faster_assignment_reduction_pct: float
    document_completeness_rate_pct: float
    manual_search_hours_avoided: float
    deadline_visibility_rate_pct: float
    post_release_continuity_rate_pct: float

    indicators: List[ImpactMetricItem]


# ── Controlled Export Models ──────────────────────────────────────────────────

class ExportRequest(BaseModel):
    report_type: str = "ALL_DASHBOARDS"
    format: ExportFormat = ExportFormat.CSV
    jurisdiction: Optional[str] = "ALL"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    purpose: str = Field(..., min_length=5, description="Mandatory official justification for data export")
    include_pii: bool = False


class ExportResponse(BaseModel):
    export_id: str
    filename: str
    format: str
    record_count: int
    content: str
    checksum_sha256: str
    exported_at: str
    data_minimized: bool
    jurisdiction_scope: str


class ExportAuditLogRecord(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_role: str
    report_type: str
    format: str
    record_count: int
    scope_filter: str
    purpose: str
    export_hash: str
    exported_at: str


# ── Scheduled Reports Models ──────────────────────────────────────────────────

class ScheduledReportCreateRequest(BaseModel):
    title: str
    report_type: str
    frequency: ReportFrequency
    recipients: List[str]
    jurisdiction: str = "ALL"
    data_minimization_level: str = "AGGREGATE_ONLY"


class ScheduledReportRecord(BaseModel):
    id: str
    title: str
    report_type: str
    frequency: str
    recipients: List[str]
    jurisdiction: str
    data_minimization_level: str
    is_active: bool
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    created_at: str


class ScheduledExecutionRecord(BaseModel):
    id: str
    schedule_id: str
    executed_at: str
    status: str
    summary_content: str
    delivery_channel: str
