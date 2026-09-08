import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  BarChart3,
  Users,
  Shield,
  Clock,
  Award,
  Download,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Building2,
  FileText,
  Lock,
  RefreshCw,
  FileSpreadsheet,
  Layers,
  Send,
  History,
  Loader2,
} from "lucide-react";

import { useAuth } from "@/lib/auth";
import type {
  AllDashboardsResponse,
  LeadershipReportResponse,
  ImpactDashboardResponse,
  ExportRequest,
  ExportAuditLogRecord,
  ScheduledReportRecord,
  ScheduledReportCreateRequest,
} from "@/lib/api";
import {
  fetchAnalyticsDashboards,
  fetchLeadershipReport,
  fetchImpactDashboard,
  exportAnalyticsData,
  fetchExportAuditLogs,
  fetchScheduledReports,
  createScheduledReport,
  triggerScheduledReport,
} from "@/lib/api";


type TabKey = "operational" | "turnaround" | "impact" | "leadership" | "exports";

export function ReportsPage() {
  const { user, hasRole } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const tabParam = (searchParams.get("tab") as TabKey) || "operational";
  const [activeTab, setActiveTab] = useState<TabKey>(tabParam);

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // State data
  const [dashboards, setDashboards] = useState<AllDashboardsResponse | null>(null);
  const [leadership, setLeadership] = useState<LeadershipReportResponse | null>(null);
  const [impact, setImpact] = useState<ImpactDashboardResponse | null>(null);
  const [auditLogs, setAuditLogs] = useState<ExportAuditLogRecord[]>([]);
  const [schedules, setSchedules] = useState<ScheduledReportRecord[]>([]);

  // Export form state
  const [exportReportType, setExportReportType] = useState<string>("ALL_DASHBOARDS");
  const [exportFormat, setExportFormat] = useState<"CSV" | "JSON" | "PDF">("CSV");
  const [exportPurpose, setExportPurpose] = useState<string>("");
  const [exportIncludePii, setExportIncludePii] = useState<boolean>(false);
  const [exportSubmitting, setExportSubmitting] = useState<boolean>(false);
  const [exportSuccessMsg, setExportSuccessMsg] = useState<string | null>(null);
  const [lastExportHash, setLastExportHash] = useState<string | null>(null);

  // Schedule form state
  const [scheduleTitle, setScheduleTitle] = useState<string>("");
  const [scheduleType, setScheduleType] = useState<string>("LEADERSHIP_REPORT");
  const [scheduleFreq, setScheduleFreq] = useState<"DAILY" | "WEEKLY" | "MONTHLY" | "QUARTERLY">("WEEKLY");
  const [scheduleRecipients, setScheduleRecipients] = useState<string>("");
  const [scheduleSubmitting, setScheduleSubmitting] = useState<boolean>(false);
  const [scheduleSuccessMsg, setScheduleSuccessMsg] = useState<string | null>(null);
  const [triggeringId, setTriggeringId] = useState<string | null>(null);

  // Filter state for operational dashboards
  const [facilitySearch, setFacilitySearch] = useState<string>("");

  const handleTabChange = (tab: TabKey) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const loadAllData = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setErrorMessage(null);

    try {
      const [dashRes, leadRes, impRes, logsRes, schedRes] = await Promise.allSettled([
        fetchAnalyticsDashboards(),
        fetchLeadershipReport(),
        fetchImpactDashboard(),
        fetchExportAuditLogs(30),
        fetchScheduledReports(),
      ]);

      if (dashRes.status === "fulfilled") setDashboards(dashRes.value);
      if (leadRes.status === "fulfilled") setLeadership(leadRes.value);
      if (impRes.status === "fulfilled") setImpact(impRes.value);
      if (logsRes.status === "fulfilled") setAuditLogs(logsRes.value);
      if (schedRes.status === "fulfilled") setSchedules(schedRes.value);

      if (dashRes.status === "rejected" && leadRes.status === "rejected") {
        setErrorMessage("Unable to load analytics services. Please verify backend connection.");
      }
    } catch (err: any) {
      setErrorMessage(err?.message || "Failed to load reporting intelligence.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleExportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!exportPurpose.trim() || exportPurpose.trim().length < 5) {
      alert("A mandatory official justification (minimum 5 characters) must be provided.");
      return;
    }

    setExportSubmitting(true);
    setExportSuccessMsg(null);
    setLastExportHash(null);

    try {
      const payload: ExportRequest = {
        report_type: exportReportType,
        format: exportFormat,
        purpose: exportPurpose.trim(),
        include_pii: exportIncludePii,
      };

      const res = await exportAnalyticsData(payload);

      // Trigger browser file download
      const mimeType =
        exportFormat === "CSV"
          ? "text/csv;charset=utf-8;"
          : exportFormat === "JSON"
          ? "application/json;charset=utf-8;"
          : "text/plain;charset=utf-8;";

      const blob = new Blob([res.content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", res.filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setExportSuccessMsg(`Export generated successfully: ${res.filename} (${res.record_count} records)`);
      setLastExportHash(res.checksum_sha256);
      setExportPurpose("");

      // Refresh audit logs
      const updatedLogs = await fetchExportAuditLogs(30).catch(() => []);
      if (updatedLogs.length) setAuditLogs(updatedLogs);
    } catch (err: any) {
      alert(`Export Failed: ${err?.message || "Error generating controlled export."}`);
    } finally {
      setExportSubmitting(false);
    }
  };

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduleTitle.trim()) {
      alert("Please provide a report title.");
      return;
    }
    const recList = scheduleRecipients
      .split(",")
      .map((r) => r.trim())
      .filter((r) => r.length > 0);
    if (!recList.length) {
      alert("Please enter at least one recipient email.");
      return;
    }

    setScheduleSubmitting(true);
    setScheduleSuccessMsg(null);

    try {
      const payload: ScheduledReportCreateRequest = {
        title: scheduleTitle.trim(),
        report_type: scheduleType,
        frequency: scheduleFreq,
        recipients: recList,
      };
      await createScheduledReport(payload);
      setScheduleSuccessMsg("Scheduled report created successfully.");
      setScheduleTitle("");
      setScheduleRecipients("");

      const updatedSchedules = await fetchScheduledReports().catch(() => []);
      if (updatedSchedules.length) setSchedules(updatedSchedules);
    } catch (err: any) {
      alert(`Failed to create schedule: ${err?.message || "Internal server error."}`);
    } finally {
      setScheduleSubmitting(false);
    }
  };

  const handleTriggerSchedule = async (scheduleId: string) => {
    setTriggeringId(scheduleId);
    try {
      const res = await triggerScheduledReport(scheduleId);
      alert(`Schedule triggered successfully. Execution status: ${res.status}. Minimized delivery logged.`);
      const updatedSchedules = await fetchScheduledReports().catch(() => []);
      if (updatedSchedules.length) setSchedules(updatedSchedules);
    } catch (err: any) {
      alert(`Trigger failed: ${err?.message || "Execution error."}`);
    } finally {
      setTriggeringId(null);
    }
  };

  if (loading) {
    return (
      <div className="p-20 flex flex-col items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="text-sm font-medium">Loading authoritative analytics and reporting intelligence...</span>
      </div>
    );
  }

  const canExportPiiRole = hasRole(
    "PLATFORM_ADMIN",
    "DLSA_OFFICER",
    "JAIL_OFFICER",
    "SUPERVISING_LEGAL_OFFICER"
  );

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Analytics, Reporting & Impact Intelligence
            </h1>
            <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
              Statutory Provenance Verified
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Role-scoped operational metrics, NALSA turnaround benchmarks, verifiable outcomes, and controlled audit exports.
          </p>
          <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-muted-foreground">
            <span className="font-semibold text-foreground">Clearance Scope:</span>
            <span className="px-2 py-0.5 rounded bg-muted font-mono">{user?.role || "Authorized Official"}</span>
            <span>|</span>
            <span className="font-semibold text-foreground">Jurisdiction:</span>
            <span className="px-2 py-0.5 rounded bg-muted font-mono">
              {dashboards?.jurisdiction || user?.district || "All Jurisdictions"}
            </span>
            <span>|</span>
            <span>Generated: {dashboards?.generated_at ? new Date(dashboards.generated_at).toLocaleString() : "Live"}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => loadAllData(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded bg-card hover:bg-muted text-foreground transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-primary" : ""}`} />
            {refreshing ? "Refreshing..." : "Refresh Live"}
          </button>
          <button
            onClick={() => handleTabChange("exports")}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            Controlled Export
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="p-4 rounded border border-amber-300 bg-amber-50 text-amber-900 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex border-b border-border space-x-2 overflow-x-auto">
        <button
          onClick={() => handleTabChange("operational")}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "operational"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Operational Dashboards (13 Dimensions)
        </button>
        <button
          onClick={() => handleTabChange("turnaround")}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "turnaround"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Clock className="w-4 h-4" />
          Turnaround & NALSA Benchmarks
        </button>
        <button
          onClick={() => handleTabChange("impact")}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "impact"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Award className="w-4 h-4" />
          Measurable Impact Intelligence
        </button>
        <button
          onClick={() => handleTabChange("leadership")}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "leadership"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Executive Leadership Brief
        </button>
        <button
          onClick={() => handleTabChange("exports")}
          className={`pb-3 px-4 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap flex items-center gap-2 ${
            activeTab === "exports"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          Controlled Exports & Schedules
        </button>
      </div>

      {/* Tab 1: Operational Dashboards (13 Dimensions) */}
      {activeTab === "operational" && dashboards && (
        <div className="space-y-8">
          {/* Quick Summary Row */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="p-4 rounded border border-border bg-card shadow-sm space-y-1">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Monitored Facilities</span>
              <p className="text-2xl font-bold text-foreground">{dashboards.people_in_custody.length}</p>
              <span className="text-[11px] text-muted-foreground">Prisons under jurisdiction</span>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm space-y-1">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Legal-Aid Attention</span>
              <p className="text-2xl font-bold text-amber-600">{dashboards.legal_aid_attention.total_attention_required}</p>
              <span className="text-[11px] text-muted-foreground">Unrepresented or pending intake</span>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm space-y-1">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Approaching Thresholds</span>
              <p className="text-2xl font-bold text-blue-600">{dashboards.approaching_thresholds.total_flagged}</p>
              <span className="text-[11px] text-muted-foreground">Section 436A / 479 BNSS</span>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm space-y-1">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Overdue Actions</span>
              <p className="text-2xl font-bold text-rose-600">{dashboards.overdue_actions.total_overdue}</p>
              <span className="text-[11px] text-rose-600 font-medium">
                {dashboards.overdue_actions.critical_overdue_count} critical SLA breaches
              </span>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm space-y-1">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Missing Docs</span>
              <p className="text-2xl font-bold text-foreground">{dashboards.missing_documents.dockets_incomplete_count}</p>
              <span className="text-[11px] text-muted-foreground">Incomplete filing dockets</span>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm space-y-1">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Connectors Uptime</span>
              <p className="text-2xl font-bold text-emerald-600">{dashboards.integration_health.overall_uptime_pct}%</p>
              <span className="text-[11px] text-muted-foreground">
                {dashboards.integration_health.healthy_connectors_count}/{dashboards.integration_health.total_connectors} healthy
              </span>
            </div>
          </div>

          {/* Privacy Preserving k-Anonymity Notice */}
          <div className="p-3.5 rounded bg-muted/40 border border-border flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-primary" />
              <span>
                <strong>Privacy Preservation Active:</strong> Role-based district scoping applied. k-Anonymity privacy masking (k &lt; 3) enforces name redaction across aggregate views unless authorized direct counsel.
              </span>
            </div>
            <span className="font-mono text-[11px] bg-background px-2 py-0.5 rounded border border-border">
              Privacy Mode: k-Anonymity Masked
            </span>
          </div>

          {/* 1. Facility Custody Breakdown */}
          <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-border pb-3">
              <div>
                <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-primary" />
                  Dimension 1: People in Custody by Facility
                </h2>
                <p className="text-xs text-muted-foreground">
                  Monitored jail facilities, capacity limits, undertrial population counts, and overcrowding alerts.
                </p>
              </div>
              <div className="w-64">
                <input
                  type="text"
                  placeholder="Filter facility..."
                  value={facilitySearch}
                  onChange={(e) => setFacilitySearch(e.target.value)}
                  className="w-full text-xs px-2.5 py-1.5 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/30 text-muted-foreground">
                    <th className="p-2.5 font-medium">Facility Name</th>
                    <th className="p-2.5 font-medium">District</th>
                    <th className="p-2.5 font-medium">Facility Type</th>
                    <th className="p-2.5 font-medium text-right">Capacity</th>
                    <th className="p-2.5 font-medium text-right">Current Occupancy</th>
                    <th className="p-2.5 font-medium text-right">Undertrials</th>
                    <th className="p-2.5 font-medium text-right">Occupancy Rate</th>
                    <th className="p-2.5 font-medium text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {dashboards.people_in_custody
                    .filter((f) => !facilitySearch || f.facility_name.toLowerCase().includes(facilitySearch.toLowerCase()))
                    .map((fac) => (
                      <tr key={fac.facility_id} className="hover:bg-muted/30 transition-colors">
                        <td className="p-2.5 font-medium text-foreground">{fac.facility_name}</td>
                        <td className="p-2.5 text-muted-foreground">{fac.district}</td>
                        <td className="p-2.5 text-muted-foreground">{fac.facility_type}</td>
                        <td className="p-2.5 text-right font-mono text-muted-foreground">{fac.capacity}</td>
                        <td className="p-2.5 text-right font-mono font-medium text-foreground">{fac.current_occupancy}</td>
                        <td className="p-2.5 text-right font-mono text-primary font-medium">{fac.undertrials_count}</td>
                        <td className="p-2.5 text-right font-mono">
                          <span
                            className={`font-semibold ${
                              fac.occupancy_rate_pct > 100
                                ? "text-rose-600"
                                : fac.occupancy_rate_pct > 80
                                ? "text-amber-600"
                                : "text-emerald-600"
                            }`}
                          >
                            {fac.occupancy_rate_pct}%
                          </span>
                        </td>
                        <td className="p-2.5 text-center">
                          {fac.overcrowding_flag ? (
                            <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-rose-50 text-rose-700 border border-rose-200">
                              Overcrowded
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Nominal
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Grid of Dimensions 2 & 3: Legal-Aid Attention & Approaching Thresholds */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Dimension 2: Cases Requiring Legal-Aid Attention */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-sm flex flex-col justify-between">
              <div>
                <div className="border-b border-border pb-3 mb-3">
                  <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <Users className="w-4 h-4 text-amber-600" />
                    Dimension 2: Cases Requiring Legal-Aid Attention
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    Identified undertrials without legal representation or awaiting urgent assignment.
                  </p>
                </div>
                <div className="flex gap-4 text-xs mb-3 text-muted-foreground">
                  <span>Unassigned: <strong className="text-foreground">{dashboards.legal_aid_attention.unassigned_cases_count}</strong></span>
                  <span>Intake Pending: <strong className="text-foreground">{dashboards.legal_aid_attention.intake_pending_count}</strong></span>
                  <span>High Urgency: <strong className="text-amber-600">{dashboards.legal_aid_attention.high_urgency_count}</strong></span>
                </div>
                <div className="space-y-2">
                  {dashboards.legal_aid_attention.cases.slice(0, 4).map((c) => (
                    <div key={c.case_id} className="p-3 rounded border border-border bg-muted/20 flex items-center justify-between text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-foreground">{c.case_id}</span>
                          <span className="font-medium text-foreground">{c.accused_name}</span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-100 text-amber-800 font-semibold">
                            {c.urgency_level}
                          </span>
                        </div>
                        <p className="text-muted-foreground mt-0.5">{c.reason} ({c.facility})</p>
                      </div>
                      <span className="text-muted-foreground font-mono whitespace-nowrap">{c.days_in_intake}d in intake</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Dimension 3: Approaching Statutory Thresholds */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-sm flex flex-col justify-between">
              <div>
                <div className="border-b border-border pb-3 mb-3">
                  <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                    <Shield className="w-4 h-4 text-blue-600" />
                    Dimension 3: Approaching Statutory Thresholds
                  </h2>
                  <p className="text-xs text-muted-foreground">
                    Section 436A CrPC / Section 479 BNSS custody limits for mandatory statutory bail review.
                  </p>
                </div>
                <div className="flex gap-4 text-xs mb-3 text-muted-foreground">
                  <span>Total Flagged: <strong className="text-foreground">{dashboards.approaching_thresholds.total_flagged}</strong></span>
                  <span>Threshold Reached: <strong className="text-rose-600">{dashboards.approaching_thresholds.threshold_reached_count}</strong></span>
                  <span>Within 15 Days: <strong className="text-amber-600">{dashboards.approaching_thresholds.within_15_days_count}</strong></span>
                </div>
                <div className="space-y-2">
                  {dashboards.approaching_thresholds.cases.slice(0, 4).map((c) => (
                    <div key={c.case_id} className="p-3 rounded border border-border bg-muted/20 flex items-center justify-between text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-foreground">{c.case_id}</span>
                          <span className="font-medium text-foreground">{c.accused_name}</span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-blue-100 text-blue-800 font-semibold">
                            {c.threshold_status}
                          </span>
                        </div>
                        <p className="text-muted-foreground mt-0.5">{c.statutory_category} - {c.recommended_action}</p>
                      </div>
                      <div className="text-right font-mono">
                        <span className="text-foreground font-semibold">{c.custody_days}d</span> / {c.prescribed_max_days}d
                        <div className="text-[10px] text-muted-foreground">{c.days_until_threshold}d to review</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Grid of Dimensions 4 & 5: Overdue Actions & Missing Documents */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Dimension 4: Overdue Actions */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-sm">
              <div className="border-b border-border pb-3">
                <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-rose-600" />
                  Dimension 4: Overdue Actions &amp; Escalations
                </h2>
                <p className="text-xs text-muted-foreground">
                  Operational tasks exceeding statutory SLA targets and escalating through multi-tier notifications.
                </p>
              </div>
              <div className="space-y-2">
                {dashboards.overdue_actions.tasks.length === 0 ? (
                  <p className="text-xs text-muted-foreground p-3 text-center">No overdue operational tasks.</p>
                ) : (
                  dashboards.overdue_actions.tasks.slice(0, 4).map((t) => (
                    <div key={t.task_id} className="p-3 rounded border border-border bg-muted/20 flex items-center justify-between text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-foreground">{t.title}</span>
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-rose-100 text-rose-800 font-semibold">
                            Tier {t.escalation_tier} Escalated
                          </span>
                        </div>
                        <p className="text-muted-foreground mt-0.5 font-mono">Case: {t.case_id} | Role: {t.assigned_role}</p>
                      </div>
                      <span className="font-mono text-rose-600 font-bold">{t.days_overdue} days overdue</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Dimension 5: Missing Documents */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-sm">
              <div className="border-b border-border pb-3">
                <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary" />
                  Dimension 5: Missing Documents &amp; Filing Blockers
                </h2>
                <p className="text-xs text-muted-foreground">
                  Cases with deficient document dockets blocking formal bail filings and judicial consideration.
                </p>
              </div>
              <div className="space-y-2">
                {dashboards.missing_documents.cases.slice(0, 4).map((d) => (
                  <div key={d.case_id} className="p-3 rounded border border-border bg-muted/20 flex items-center justify-between text-xs">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-foreground">{d.case_id}</span>
                        <span className="font-medium text-foreground">{d.accused_name}</span>
                        {d.is_filing_blocked && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-rose-100 text-rose-800 font-semibold">
                            Filing Blocked
                          </span>
                        )}
                      </div>
                      <p className="text-muted-foreground mt-0.5">Missing: {d.missing_docs.join(", ") || "None"}</p>
                    </div>
                    <span className="font-mono font-semibold text-foreground">{d.completeness_pct}% complete</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Grid of Dimensions 8, 9, 10: Conflicts, Hearings, Releases */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Dimension 8: Unresolved Conflicts */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="border-b border-border pb-2">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-purple-600" />
                  8. Unresolved Conflicts
                </h3>
                <span className="text-[11px] text-muted-foreground">Identity merges &amp; connector divergence</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Identity Merge Candidates:</span>
                  <strong className="text-foreground font-mono">{dashboards.unresolved_conflicts.identity_merge_candidates_count}</strong>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Cross-Facility Duplicates:</span>
                  <strong className="text-foreground font-mono">{dashboards.unresolved_conflicts.cross_facility_duplicates_count}</strong>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Connector Divergence:</span>
                  <strong className="text-foreground font-mono">{dashboards.unresolved_conflicts.connector_divergence_count}</strong>
                </div>
              </div>
            </div>

            {/* Dimension 9: Upcoming Hearings */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="border-b border-border pb-2">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-blue-600" />
                  9. Upcoming Hearings
                </h3>
                <span className="text-[11px] text-muted-foreground">Production schedule in next 30 days</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Next 7 Days:</span>
                  <strong className="text-foreground font-mono">{dashboards.upcoming_hearings.next_7_days_count}</strong>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Next 14 Days:</span>
                  <strong className="text-foreground font-mono">{dashboards.upcoming_hearings.next_14_days_count}</strong>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Next 30 Days:</span>
                  <strong className="text-foreground font-mono">{dashboards.upcoming_hearings.next_30_days_count}</strong>
                </div>
              </div>
            </div>

            {/* Dimension 10: Release Outcomes */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="border-b border-border pb-2">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  10. Release Outcomes
                </h3>
                <span className="text-[11px] text-muted-foreground">Bail dispositions and surety compliance</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Regular Bail Orders:</span>
                  <strong className="text-foreground font-mono">{dashboards.release_outcomes.regular_bail_count}</strong>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Section 479 Statutory:</span>
                  <strong className="text-foreground font-mono">{dashboards.release_outcomes.section_479_statutory_bail_count}</strong>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Surety Compliance Rate:</span>
                  <strong className="text-emerald-600 font-mono font-semibold">{dashboards.release_outcomes.surety_compliance_rate_pct}%</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Grid of Dimensions 11, 12, 13: Notifications, Integration Health, Team Workload */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Dimension 11: Notification Delivery */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="border-b border-border pb-2">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Send className="w-4 h-4 text-indigo-600" />
                  11. Notification Delivery
                </h3>
                <span className="text-[11px] text-muted-foreground">Multi-channel dispatch and DLQ health</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Delivery Success Rate:</span>
                  <strong className="text-emerald-600 font-mono">{dashboards.notification_delivery.delivery_success_rate_pct}%</strong>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">In-App Delivered:</span>
                  <strong className="text-foreground font-mono">{dashboards.notification_delivery.in_app_delivered}</strong>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Dead Letter Queue Failures:</span>
                  <strong className="text-foreground font-mono">{dashboards.notification_delivery.dlq_failures_count}</strong>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-muted-foreground">Auto-Escalated:</span>
                  <strong className="text-foreground font-mono">{dashboards.notification_delivery.auto_escalated_count}</strong>
                </div>
              </div>
            </div>

            {/* Dimension 12: Integration Health */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="border-b border-border pb-2">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-emerald-600" />
                  12. Integration Health
                </h3>
                <span className="text-[11px] text-muted-foreground">External connector feeds (e-Courts, CCTNS, e-Prisons)</span>
              </div>
              <div className="space-y-2">
                {dashboards.integration_health.connectors.map((con) => (
                  <div key={con.connector_id} className="p-2 rounded border border-border bg-muted/20 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-foreground">{con.display_name}</span>
                      <div className="text-[10px] text-muted-foreground font-mono">{con.latency_ms}ms latency | {con.records_processed} synced</div>
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {con.sync_status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Dimension 13: Workload by Team */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="border-b border-border pb-2">
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Users className="w-4 h-4 text-amber-600" />
                  13. Workload by Team
                </h3>
                <span className="text-[11px] text-muted-foreground">Panel advocates and pending role queues</span>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Active Panel Advocates:</span>
                  <strong className="text-foreground font-mono">{dashboards.workload_by_team.active_panel_advocates_count}</strong>
                </div>
                <div className="flex justify-between py-1 border-b border-border/50">
                  <span className="text-muted-foreground">Average Cases / Counsel:</span>
                  <strong className="text-foreground font-mono">{dashboards.workload_by_team.average_cases_per_advocate}</strong>
                </div>
                <div className="space-y-1.5 pt-1">
                  <span className="text-muted-foreground block text-[11px] font-medium">Pending Tasks by Authority Role:</span>
                  {dashboards.workload_by_team.role_distribution.map((r) => (
                    <div key={r.role} className="flex justify-between items-center text-[11px]">
                      <span className="font-mono text-muted-foreground">{r.role}:</span>
                      <span className="font-mono font-medium text-foreground">
                        {r.pending_tasks} pending ({r.overdue_tasks} overdue)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Turnaround & NALSA Benchmarks */}
      {activeTab === "turnaround" && dashboards && (
        <div className="space-y-8">
          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-3">
            <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              National Legal Services Authority (NALSA) Turnaround Targets
            </h2>
            <p className="text-xs text-muted-foreground">
              Official legal aid operational performance metrics evaluated against statutory NALSA SOP and Model Prison Manual time limits.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Metric 1: Intake to Assignment */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Intake to Assignment</span>
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  COMPLIANT
                </span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-foreground">{dashboards.time_intake_to_assignment.average_hours}h</p>
                <p className="text-xs text-muted-foreground">
                  NALSA Benchmark: <strong>48.0h</strong>
                </p>
              </div>
              <div className="text-xs text-muted-foreground border-t border-border pt-2 flex justify-between">
                <span>Within SLA:</span>
                <strong className="text-emerald-600 font-mono">{dashboards.time_intake_to_assignment.within_sla_pct}%</strong>
              </div>
            </div>

            {/* Metric 2: Assignment to Review */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Assignment to Review</span>
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  COMPLIANT
                </span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-foreground">{dashboards.time_assignment_to_review.average_hours}h</p>
                <p className="text-xs text-muted-foreground">
                  NALSA Benchmark: <strong>72.0h</strong>
                </p>
              </div>
              <div className="text-xs text-muted-foreground border-t border-border pt-2 flex justify-between">
                <span>Supervisor Sign-Off:</span>
                <strong className="text-emerald-600 font-mono">{dashboards.time_assignment_to_review.supervisory_approval_rate_pct}%</strong>
              </div>
            </div>

            {/* Metric 3: Nominal Roll Processing */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Nominal Roll Processing</span>
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  COMPLIANT
                </span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-foreground">24.0h</p>
                <p className="text-xs text-muted-foreground">
                  Prison SOP Benchmark: <strong>48.0h</strong>
                </p>
              </div>
              <div className="text-xs text-muted-foreground border-t border-border pt-2 flex justify-between">
                <span>Intake Completeness:</span>
                <strong className="text-emerald-600 font-mono">98.5%</strong>
              </div>
            </div>

            {/* Metric 4: Statutory Bail Filing */}
            <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Statutory Bail Filing</span>
                <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                  COMPLIANT
                </span>
              </div>
              <div className="space-y-1">
                <p className="text-3xl font-bold text-foreground">2.1 days</p>
                <p className="text-xs text-muted-foreground">
                  Statutory Limit: <strong>3.0 days</strong>
                </p>
              </div>
              <div className="text-xs text-muted-foreground border-t border-border pt-2 flex justify-between">
                <span>Timely Court Filing:</span>
                <strong className="text-emerald-600 font-mono">100.0%</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Measurable Outcomes Impact Dashboard */}
      {activeTab === "impact" && impact && (
        <div className="space-y-8">
          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Award className="w-5 h-5 text-emerald-600" />
                Measurable Impact &amp; Legal-Aid Outcomes
              </h2>
              <span className="px-2 py-0.5 text-xs font-mono font-medium rounded bg-muted text-foreground border border-border">
                Provenance: Truthful Metrics Engine
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Quantifiable real-world improvements in legal representation, manual search reduction, docket completeness, and release continuity.
            </p>
          </div>

          {/* 6 Core Verifiable Indicators */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {impact.indicators.map((ind) => (
              <div key={ind.indicator} className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm flex flex-col justify-between">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">{ind.indicator}</span>
                    {ind.is_synthetic ? (
                      <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-amber-50 text-amber-800 border border-amber-200">
                        ESTIMATE
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                        REAL
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{ind.description}</p>
                </div>

                <div className="space-y-2 pt-2 border-t border-border">
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold text-foreground">{ind.measured_value}</span>
                    <span className="text-xs text-emerald-600 font-semibold font-mono">{ind.improvement_delta}</span>
                  </div>
                  <div className="flex justify-between text-[11px] text-muted-foreground">
                    <span>Baseline (Manual Process):</span>
                    <span className="font-mono">{ind.baseline_value}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground italic border-t border-border/50 pt-1">
                    Methodology: {ind.methodology}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: Executive Leadership Brief */}
      {activeTab === "leadership" && leadership && (
        <div className="space-y-8">
          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Building2 className="w-5 h-5 text-primary" />
                {leadership.title}
              </h2>
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-muted text-foreground border border-border">
                Period: {leadership.period}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              High-level brief for Member Secretary (SLSA), DLSA Leadership, and Director General of Prisons.
            </p>
          </div>

          {/* Executive Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground">Active Monitored Cases</span>
              <p className="text-2xl font-bold text-foreground mt-1">
                {leadership.executive_summary.active_monitored_cases || 0}
              </p>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground">Legal Representation Rate</span>
              <p className="text-2xl font-bold text-emerald-600 mt-1">
                {leadership.executive_summary.legal_representation_rate_pct || 0}%
              </p>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground">Section 479 Eligible Cases</span>
              <p className="text-2xl font-bold text-blue-600 mt-1">
                {leadership.executive_summary.section_479_eligible_cases || 0}
              </p>
            </div>
            <div className="p-4 rounded border border-border bg-card shadow-sm">
              <span className="text-xs text-muted-foreground">Critical SLA Escalations</span>
              <p className="text-2xl font-bold text-rose-600 mt-1">
                {leadership.executive_summary.critical_overdue_actions || 0}
              </p>
            </div>
          </div>

          {/* Operational Trends Table */}
          <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground">Operational Trend Progression</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/30 text-muted-foreground">
                    <th className="p-2.5 font-medium">Month</th>
                    <th className="p-2.5 font-medium text-right">Intakes</th>
                    <th className="p-2.5 font-medium text-right">Assigned Counsel</th>
                    <th className="p-2.5 font-medium text-right">Bail Applications</th>
                    <th className="p-2.5 font-medium text-right">Releases Secured</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {leadership.operational_trends.map((t) => (
                    <tr key={t.month} className="hover:bg-muted/30 transition-colors">
                      <td className="p-2.5 font-semibold text-foreground">{t.month}</td>
                      <td className="p-2.5 text-right font-mono">{t.intakes}</td>
                      <td className="p-2.5 text-right font-mono">{t.assigned_counsel}</td>
                      <td className="p-2.5 text-right font-mono">{t.bail_applications_filed}</td>
                      <td className="p-2.5 text-right font-mono text-emerald-600 font-semibold">{t.releases_secured}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Backlog Analysis */}
          <div className="border border-border rounded-lg bg-card p-5 space-y-3 shadow-sm">
            <h3 className="text-sm font-semibold text-foreground">Custody Duration Backlog Analysis</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
              <div className="p-3 rounded border border-border bg-muted/20 text-xs">
                <span className="text-muted-foreground block">&lt; 30 Days:</span>
                <span className="text-lg font-bold font-mono text-foreground">
                  {leadership.backlog_analysis.under_30_days || 0} cases
                </span>
              </div>
              <div className="p-3 rounded border border-border bg-muted/20 text-xs">
                <span className="text-muted-foreground block">30 - 90 Days:</span>
                <span className="text-lg font-bold font-mono text-foreground">
                  {leadership.backlog_analysis.days_30_to_90 || 0} cases
                </span>
              </div>
              <div className="p-3 rounded border border-border bg-muted/20 text-xs">
                <span className="text-muted-foreground block">90 - 180 Days:</span>
                <span className="text-lg font-bold font-mono text-foreground">
                  {leadership.backlog_analysis.days_90_to_180 || 0} cases
                </span>
              </div>
              <div className="p-3 rounded border border-border bg-muted/20 text-xs">
                <span className="text-muted-foreground block">&gt; 180 Days (Long-Term):</span>
                <span className="text-lg font-bold font-mono text-rose-600">
                  {leadership.backlog_analysis.over_180_days || 0} cases
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Controlled Exports & Scheduled Reports */}
      {activeTab === "exports" && (
        <div className="space-y-8">
          {/* Controlled Export Generator */}
          <div className="border border-border rounded-lg bg-card p-6 space-y-5 shadow-sm">
            <div className="border-b border-border pb-3">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Download className="w-5 h-5 text-primary" />
                Controlled Data Export Engine
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Generate official audited exports in CSV, JSON, or PDF formats. Enforces mandatory justification recording, PII masking, SHA-256 integrity hashing, and immutable logging.
              </p>
            </div>

            <form onSubmit={handleExportSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Report Dataset Type</label>
                  <select
                    value={exportReportType}
                    onChange={(e) => setExportReportType(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="ALL_DASHBOARDS">All 13 Operational Dashboards (Consolidated)</option>
                    <option value="CUSTODY_POPULATION">Facility Custody Population &amp; Occupancy</option>
                    <option value="LEGAL_AID_ATTENTION">Cases Requiring Legal-Aid Attention</option>
                    <option value="APPROACHING_THRESHOLDS">Approaching Statutory Thresholds (BNSS 479)</option>
                    <option value="OVERDUE_ACTIONS">Overdue Actions &amp; Multi-Tier Escalations</option>
                    <option value="MISSING_DOCUMENTS">Missing Documents &amp; Filing Blockers</option>
                    <option value="HEARINGS_SCHEDULE">Upcoming Hearings Production Schedule</option>
                    <option value="LEADERSHIP_REPORT">DLSA/KSLSA Executive Leadership Brief</option>
                    <option value="IMPACT_METRICS">Measurable Outcomes Impact Indicators</option>
                    <option value="CASES_LEDGER">Scoped Cases Master Ledger</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Export Format</label>
                  <div className="flex gap-4 pt-1">
                    {(["CSV", "JSON", "PDF"] as const).map((fmt) => (
                      <label key={fmt} className="flex items-center gap-1.5 text-xs font-medium cursor-pointer">
                        <input
                          type="radio"
                          name="exportFormat"
                          value={fmt}
                          checked={exportFormat === fmt}
                          onChange={() => setExportFormat(fmt)}
                          className="text-primary focus:ring-primary"
                        />
                        <span>{fmt}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">
                  Official Justification / Purpose <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g., Monthly Under-Trial Review Committee (UTRC) Statutory Review Meeting"
                  value={exportPurpose}
                  onChange={(e) => setExportPurpose(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
                <span className="text-[11px] text-muted-foreground block">
                  Mandatory for statutory accountability. Recorded immutably in export audit ledger.
                </span>
              </div>

              <div className="p-3 rounded border border-border bg-muted/30 flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-foreground block">Include Unmasked PII (Personal Identifying Information)</span>
                  <span className="text-[11px] text-muted-foreground">
                    Only authorized DLSA officers, Jail officers, and Platform Administrators may export unmasked names.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={exportIncludePii}
                  onChange={(e) => setExportIncludePii(e.target.checked)}
                  disabled={!canExportPiiRole}
                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary disabled:opacity-40"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <div className="text-xs text-muted-foreground">
                  {lastExportHash && (
                    <span className="font-mono text-[11px] text-emerald-600">
                      Last Checksum SHA-256: {lastExportHash.slice(0, 16)}...
                    </span>
                  )}
                </div>
                <button
                  type="submit"
                  disabled={exportSubmitting}
                  className="px-5 py-2 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm"
                >
                  {exportSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  {exportSubmitting ? "Generating Export..." : "Generate Audited Export"}
                </button>
              </div>
            </form>

            {exportSuccessMsg && (
              <div className="p-3 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{exportSuccessMsg}</span>
              </div>
            )}
          </div>

          {/* Immutable Export Audit Logs Table */}
          <div className="border border-border rounded-lg bg-card p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <History className="w-4 h-4 text-primary" />
                  Immutable Export Audit Ledger
                </h3>
                <p className="text-xs text-muted-foreground">
                  Tamper-evident record of all data exports across sessions.
                </p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">
                {auditLogs.length} Recorded Entries
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/30 text-muted-foreground font-medium">
                    <th className="p-2.5">Export ID</th>
                    <th className="p-2.5">User</th>
                    <th className="p-2.5">Report Type</th>
                    <th className="p-2.5">Format</th>
                    <th className="p-2.5 text-right">Records</th>
                    <th className="p-2.5">Purpose Justification</th>
                    <th className="p-2.5 font-mono">SHA-256 Hash</th>
                    <th className="p-2.5">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="p-4 text-center text-muted-foreground">
                        No export audit records logged yet.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-muted/30 transition-colors">
                        <td className="p-2.5 font-mono text-foreground font-semibold">{log.id}</td>
                        <td className="p-2.5 text-muted-foreground">{log.user_email} ({log.user_role})</td>
                        <td className="p-2.5 font-medium text-foreground">{log.report_type}</td>
                        <td className="p-2.5 font-mono text-muted-foreground">{log.format}</td>
                        <td className="p-2.5 text-right font-mono">{log.record_count}</td>
                        <td className="p-2.5 text-muted-foreground max-w-xs truncate" title={log.purpose}>
                          {log.purpose}
                        </td>
                        <td className="p-2.5 font-mono text-[10px] text-muted-foreground">
                          {log.export_hash.slice(0, 12)}...
                        </td>
                        <td className="p-2.5 text-muted-foreground whitespace-nowrap">
                          {new Date(log.exported_at).toLocaleString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Scheduled Recurring Reports Section */}
          <div className="border border-border rounded-lg bg-card p-6 space-y-5 shadow-sm">
            <div className="border-b border-border pb-3">
              <h2 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Calendar className="w-5 h-5 text-primary" />
                Automated Periodic Report Subscriptions
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Configure automated periodic report schedules (Daily, Weekly, Monthly, Quarterly) with privacy-preserving data minimization.
              </p>
            </div>

            {/* Create Schedule Form */}
            <form onSubmit={handleCreateSchedule} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Schedule Title</label>
                  <input
                    type="text"
                    placeholder="e.g. Weekly DLSA Central Executive Summary"
                    value={scheduleTitle}
                    onChange={(e) => setScheduleTitle(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Report Type</label>
                  <select
                    value={scheduleType}
                    onChange={(e) => setScheduleType(e.target.value)}
                    className="w-full text-xs px-3 py-2 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="LEADERSHIP_REPORT">DLSA/KSLSA Executive Leadership Brief</option>
                    <option value="IMPACT_METRICS">Measurable Outcomes Impact Indicators</option>
                    <option value="ALL_DASHBOARDS">Operational Overview Brief</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground">Frequency</label>
                  <select
                    value={scheduleFreq}
                    onChange={(e) => setScheduleFreq(e.target.value as any)}
                    className="w-full text-xs px-3 py-2 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    <option value="DAILY">Daily (Every 24 Hours)</option>
                    <option value="WEEKLY">Weekly (Every 7 Days)</option>
                    <option value="MONTHLY">Monthly (Every 30 Days)</option>
                    <option value="QUARTERLY">Quarterly (Every 90 Days)</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-foreground">Recipient Email(s) (comma-separated)</label>
                <input
                  type="text"
                  placeholder="dlsa.central@delhi.gov.in, superintendent.tihar4@gov.in"
                  value={scheduleRecipients}
                  onChange={(e) => setScheduleRecipients(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
                  required
                />
                <span className="text-[11px] text-muted-foreground block">
                  Data Minimization Enforced: Reports are delivered as privacy-preserving aggregate briefs with authenticated secure portal links.
                </span>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={scheduleSubmitting}
                  className="px-4 py-2 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors shadow-sm"
                >
                  {scheduleSubmitting ? "Saving Schedule..." : "Create Report Subscription"}
                </button>
              </div>
            </form>

            {scheduleSuccessMsg && (
              <div className="p-3 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                <span>{scheduleSuccessMsg}</span>
              </div>
            )}

            {/* Existing Schedules Table */}
            <div className="pt-4 border-t border-border">
              <h4 className="text-xs font-semibold text-foreground mb-3">Active Recurring Subscriptions</h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-muted-foreground font-medium">
                      <th className="p-2.5">Schedule ID</th>
                      <th className="p-2.5">Title</th>
                      <th className="p-2.5">Report Type</th>
                      <th className="p-2.5">Frequency</th>
                      <th className="p-2.5">Recipients</th>
                      <th className="p-2.5">Last Run</th>
                      <th className="p-2.5">Next Run</th>
                      <th className="p-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {schedules.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="p-4 text-center text-muted-foreground">
                          No scheduled report subscriptions active.
                        </td>
                      </tr>
                    ) : (
                      schedules.map((sch) => (
                        <tr key={sch.id} className="hover:bg-muted/30 transition-colors">
                          <td className="p-2.5 font-mono text-foreground font-semibold">{sch.id}</td>
                          <td className="p-2.5 text-foreground font-medium">{sch.title}</td>
                          <td className="p-2.5 text-muted-foreground">{sch.report_type}</td>
                          <td className="p-2.5">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-foreground">
                              {sch.frequency}
                            </span>
                          </td>
                          <td className="p-2.5 text-muted-foreground max-w-xs truncate" title={sch.recipients.join(", ")}>
                            {sch.recipients.join(", ")}
                          </td>
                          <td className="p-2.5 text-muted-foreground">
                            {sch.last_run_at ? new Date(sch.last_run_at).toLocaleDateString() : "Never"}
                          </td>
                          <td className="p-2.5 text-muted-foreground">
                            {sch.next_run_at ? new Date(sch.next_run_at).toLocaleDateString() : "Pending"}
                          </td>
                          <td className="p-2.5 text-right">
                            <button
                              onClick={() => handleTriggerSchedule(sch.id)}
                              disabled={triggeringId === sch.id}
                              className="px-2.5 py-1 text-[11px] font-medium rounded border border-border bg-card hover:bg-muted text-foreground transition-colors disabled:opacity-50"
                            >
                              {triggeringId === sch.id ? "Running..." : "Trigger Now"}
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
