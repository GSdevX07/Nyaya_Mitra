import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Search,
  Shield,
  Calendar,
  ChevronRight,
  Loader2,
  CheckSquare,
  AlertCircle,
  Scale,
  RefreshCw,
  ExternalLink,
  Filter,
  RotateCcw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  fetchTaskQueue,
  executeBulkTaskActionApi,
  type TaskQueueItem,
  type TaskFilterParams,
} from "../lib/api";
import { useAuth } from "../lib/auth";

interface UniversalTaskQueueProps {
  initialFilter?: TaskFilterParams;
  title?: string;
  subtitle?: string;
  onActionClick?: (task: TaskQueueItem, actionType: string) => void;
  allowedTaskTypes?: string[];
  hideHeader?: boolean;
}

export function UniversalTaskQueue({
  initialFilter = {},
  title = "Operational Task Queue",
  subtitle = "Prioritized authority tasks requiring action, investigation, or institutional review.",
  onActionClick,
  allowedTaskTypes,
  hideHeader = false,
}: UniversalTaskQueueProps) {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<TaskQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [activePreset, setActivePreset] = useState<"ALL" | "OVERDUE" | "CRITICAL" | "WAITING_DOCS" | "MY_TASKS">("ALL");
  const [filterFacility, setFilterFacility] = useState(initialFilter.facility || "");
  const [filterDistrict, setFilterDistrict] = useState(initialFilter.district || "");
  const [filterPriority, setFilterPriority] = useState(initialFilter.priority || "");
  const [custodyDurationMin, setCustodyDurationMin] = useState<string>(
    initialFilter.custody_duration_min !== undefined ? String(initialFilter.custody_duration_min) : ""
  );
  const [documentCompletenessMax, setDocumentCompletenessMax] = useState<string>(
    initialFilter.document_completeness_max !== undefined ? String(initialFilter.document_completeness_max) : ""
  );
  const [legalAidNeed, setLegalAidNeed] = useState<string>(
    initialFilter.legal_aid_need !== undefined ? String(initialFilter.legal_aid_need) : ""
  );
  const [hearingDateFrom, setHearingDateFrom] = useState<string>(initialFilter.hearing_date_from || "");
  const [hearingDateTo, setHearingDateTo] = useState<string>(initialFilter.hearing_date_to || "");
  const [hasDataConflict, setHasDataConflict] = useState<string>(
    initialFilter.has_data_conflict !== undefined ? String(initialFilter.has_data_conflict) : ""
  );
  const [matterStatus, setMatterStatus] = useState<string>(initialFilter.matter_status || "");
  const filterStatus = initialFilter.status || "";
  const [sortBy, setSortBy] = useState("due_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">((initialFilter.sort_order as any) || "asc");
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);

  // Active filters count
  const activeFilterCount = [
    Boolean(search.trim()),
    activePreset !== "ALL",
    Boolean(filterPriority),
    Boolean(filterFacility.trim()),
    Boolean(filterDistrict.trim()),
    Boolean(custodyDurationMin),
    Boolean(documentCompletenessMax),
    Boolean(legalAidNeed),
    Boolean(hearingDateFrom),
    Boolean(hearingDateTo),
    Boolean(hasDataConflict),
    Boolean(matterStatus),
  ].filter(Boolean).length;

  const handleClearAllFilters = () => {
    setSearch("");
    setActivePreset("ALL");
    setFilterPriority("");
    setFilterFacility("");
    setFilterDistrict("");
    setCustodyDurationMin("");
    setDocumentCompletenessMax("");
    setLegalAidNeed("");
    setHearingDateFrom("");
    setHearingDateTo("");
    setHasDataConflict("");
    setMatterStatus("");
    setSortBy("due_date");
    setSortOrder("asc");
  };

  // Selection for bulk action
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([]);
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [bulkActionResult, setBulkActionResult] = useState<{
    type: "success" | "warning" | "error";
    text: string;
  } | null>(null);

  // Consequential action blocked dialog
  const [consequentialModalTask, setConsequentialModalTask] = useState<TaskQueueItem | null>(null);

  const loadTasks = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: TaskFilterParams = {
        ...initialFilter,
        search: search.trim() || undefined,
        facility: filterFacility.trim() || undefined,
        district: filterDistrict.trim() || undefined,
        priority: filterPriority || undefined,
        custody_duration_min: custodyDurationMin ? parseInt(custodyDurationMin, 10) : undefined,
        document_completeness_max: documentCompletenessMax ? parseInt(documentCompletenessMax, 10) : undefined,
        legal_aid_need: legalAidNeed === "true" ? true : legalAidNeed === "false" ? false : undefined,
        hearing_date_from: hearingDateFrom || undefined,
        hearing_date_to: hearingDateTo || undefined,
        has_data_conflict: hasDataConflict === "true" ? true : hasDataConflict === "false" ? false : undefined,
        matter_status: matterStatus || undefined,
        status: filterStatus || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      };

      if (activePreset === "OVERDUE") {
        params.status = "OVERDUE";
      } else if (activePreset === "CRITICAL") {
        params.priority = "CRITICAL";
      } else if (activePreset === "WAITING_DOCS") {
        params.status = "WAITING_FOR_DOCUMENTS";
      }

      const data = await fetchTaskQueue(params);
      let filtered = data || [];
      if (allowedTaskTypes && allowedTaskTypes.length > 0) {
        filtered = filtered.filter((t) => allowedTaskTypes.includes(t.task_type));
      }
      if (activePreset === "MY_TASKS" && user) {
        filtered = filtered.filter(
          (t) => t.owner_user_id === user.id || t.owner_role === user.role
        );
      }
      setTasks(filtered);
    } catch (err: any) {
      console.error("Failed to load task queue:", err);
      setError(err.message || "Failed to load operational tasks.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [
    search,
    activePreset,
    filterFacility,
    filterDistrict,
    filterPriority,
    custodyDurationMin,
    documentCompletenessMax,
    legalAidNeed,
    hearingDateFrom,
    hearingDateTo,
    hasDataConflict,
    matterStatus,
    filterStatus,
    sortBy,
    sortOrder,
  ]);

  const handleSelectAll = () => {
    if (selectedTaskIds.length === tasks.length) {
      setSelectedTaskIds([]);
    } else {
      setSelectedTaskIds(tasks.map((t) => t.id));
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedTaskIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSafeBulkAction = async (action: "ASSIGN_OWNER" | "MARK_REVIEWED" | "ACKNOWLEDGE") => {
    if (selectedTaskIds.length === 0) return;
    setBulkActionLoading(true);
    setBulkActionResult(null);
    try {
      const res = await executeBulkTaskActionApi(action, selectedTaskIds, {
        owner_user_id: user?.id,
        owner_name: user?.full_name,
      });
      if (res.updated_count === 0) {
        setBulkActionResult({
          type: "warning",
          text: `Notice: 0 tasks updated. ${res.skipped_count || 0} task(s) skipped (consequential legal actions require individual case review).`,
        });
      } else {
        setBulkActionResult({
          type: "success",
          text: `Success: ${res.message}`,
        });
      }
      setSelectedTaskIds([]);
      await loadTasks();
    } catch (err: any) {
      setBulkActionResult({
        type: "error",
        text: `Bulk Action Failed: ${err.message || err}`,
      });
    } finally {
      setBulkActionLoading(false);
    }
  };

  const getPriorityBadgeClass = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30";
      case "HIGH":
        return "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30";
      case "MEDIUM":
        return "bg-secondary text-foreground border-border";
      default:
        return "bg-secondary/50 text-muted-foreground border-border";
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "OVERDUE":
      case "EXCEPTION":
        return "bg-rose-600 text-white font-bold";
      case "UNDER_REVIEW":
        return "bg-secondary text-foreground border-border";
      case "WAITING_FOR_DOCUMENTS":
        return "bg-red-500/10 text-red-600 border-red-500/30";
      case "COMPLETED":
        return "bg-emerald-500/10 text-emerald-600 border-emerald-500/30";
      default:
        return "bg-secondary text-foreground border-border";
    }
  };

  const formatDueDateSLA = (dueDateStr: string) => {
    try {
      const due = new Date(dueDateStr);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      due.setHours(0, 0, 0, 0);
      const diffDays = Math.round((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

      if (diffDays < 0) {
        return (
          <span className="text-rose-600 dark:text-rose-400 font-bold flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Overdue ({Math.abs(diffDays)}d ago)
          </span>
        );
      } else if (diffDays === 0) {
        return (
          <span className="text-red-600 dark:text-red-400 font-bold flex items-center gap-1">
            <Clock className="w-3 h-3" /> Due Today
          </span>
        );
      } else {
        return (
          <span className="text-muted-foreground flex items-center gap-1">
            <Calendar className="w-3 h-3" /> Due in {diffDays}d
          </span>
        );
      }
    } catch {
      return dueDateStr;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      {!hideHeader && (
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border-b border-border pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" />
              <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
                Authoritative Work Queue
              </span>
            </div>
            <h2 className="text-xl font-bold font-serif text-foreground mt-0.5">{title}</h2>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadTasks}
              disabled={loading}
              className="px-3 py-1.5 bg-secondary text-secondary-foreground text-xs font-mono rounded-sm border border-border flex items-center gap-1.5 hover:bg-secondary/80 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>
        </div>
      )}

      {/* Preset Tabs Ribbon */}
      <div className="flex flex-wrap items-center gap-1.5 border-b border-border pb-2 text-xs font-mono">
        <button
          onClick={() => setActivePreset("ALL")}
          className={`px-3 py-1 rounded-sm border transition-colors ${
            activePreset === "ALL"
              ? "bg-primary text-primary-foreground border-primary font-bold"
              : "bg-secondary text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          All Tasks ({tasks.length})
        </button>
        <button
          onClick={() => setActivePreset("CRITICAL")}
          className={`px-3 py-1 rounded-sm border transition-colors ${
            activePreset === "CRITICAL"
              ? "bg-rose-600 text-white border-rose-600 font-bold"
              : "bg-secondary text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          Critical / High Urgency
        </button>
        <button
          onClick={() => setActivePreset("OVERDUE")}
          className={`px-3 py-1 rounded-sm border transition-colors ${
            activePreset === "OVERDUE"
              ? "bg-red-600 text-white border-red-600 font-bold"
              : "bg-secondary text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          Overdue SLA
        </button>
        <button
          onClick={() => setActivePreset("WAITING_DOCS")}
          className={`px-3 py-1 rounded-sm border transition-colors ${
            activePreset === "WAITING_DOCS"
              ? "bg-red-600 text-white border-red-600 font-bold"
              : "bg-secondary text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          Waiting for Documents
        </button>
        <button
          onClick={() => setActivePreset("MY_TASKS")}
          className={`px-3 py-1 rounded-sm border transition-colors ${
            activePreset === "MY_TASKS"
              ? "bg-primary text-primary-foreground border-primary font-bold"
              : "bg-secondary text-muted-foreground border-border hover:text-foreground"
          }`}
        >
          My Role Tasks
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-2.5">
        <div className="relative md:col-span-5">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by inmate name, case ID, or statutory reason…"
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-card border border-border rounded-sm focus:outline-none focus:ring-1 focus:ring-primary font-sans"
          />
        </div>

        <div className="md:col-span-2">
          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="w-full py-1.5 px-2.5 text-xs bg-card border border-border rounded-sm text-foreground focus:outline-none font-mono"
          >
            <option value="">All Priorities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>

        <div className="md:col-span-3">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="w-full py-1.5 px-2.5 text-xs bg-card border border-border rounded-sm text-foreground focus:outline-none font-mono"
          >
            <option value="due_date">Sort by Due Date (SLA)</option>
            <option value="priority">Sort by Urgency Priority</option>
            <option value="custody_duration_days">Sort by Days in Custody</option>
            <option value="created_at">Sort by Created Date</option>
          </select>
        </div>

        <div className="md:col-span-2 flex items-center gap-1.5">
          <button
            onClick={() => setShowFiltersPanel(!showFiltersPanel)}
            className={`flex-1 py-1.5 px-2.5 text-xs font-mono rounded-sm border flex items-center justify-between transition-colors ${
              showFiltersPanel || activeFilterCount > 0
                ? "bg-secondary text-foreground border-primary font-bold"
                : "bg-card text-muted-foreground border-border hover:text-foreground hover:bg-secondary"
            }`}
          >
            <span className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5" />
              <span>Filters</span>
              {activeFilterCount > 0 && (
                <span className="px-1.5 py-0.2 bg-emerald-500/10 text-emerald-600 border border-emerald-500/30 text-[10px] rounded-full font-bold">
                  {activeFilterCount}
                </span>
              )}
            </span>
            {showFiltersPanel ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {activeFilterCount > 0 && (
            <button
              onClick={handleClearAllFilters}
              title="Clear all filters"
              className="p-1.5 bg-secondary text-muted-foreground hover:text-foreground border border-border rounded-sm transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Dedicated Stage 10 Operational Filters Panel */}
      {showFiltersPanel && (
        <div className="p-3.5 bg-card border border-border rounded-sm space-y-3 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-2 text-xs font-mono">
            <div className="flex items-center gap-2 text-foreground font-bold">
              <Filter className="w-3.5 h-3.5 text-primary" />
              <span>Stage 10 Operational Filter Criteria</span>
              {activeFilterCount > 0 && (
                <span className="px-2 py-0.5 text-[10px] bg-emerald-500/10 text-emerald-600 border border-emerald-500/30 rounded-full font-bold">
                  {activeFilterCount} active
                </span>
              )}
            </div>
            {activeFilterCount > 0 && (
              <button
                onClick={handleClearAllFilters}
                className="text-muted-foreground hover:text-foreground text-[11px] flex items-center gap-1 font-mono hover:underline"
              >
                <RotateCcw className="w-3 h-3" /> Clear All Filters
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            {/* 1. Facility */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                1. Facility / Prison
              </label>
              <input
                type="text"
                value={filterFacility}
                onChange={(e) => setFilterFacility(e.target.value)}
                placeholder="e.g. Tihar Jail No. 04"
                className="w-full px-2.5 py-1.5 bg-secondary border border-border rounded-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary font-sans text-xs"
              />
            </div>

            {/* 2. District */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                2. Judicial District
              </label>
              <input
                type="text"
                value={filterDistrict}
                onChange={(e) => setFilterDistrict(e.target.value)}
                placeholder="e.g. Central Delhi"
                className="w-full px-2.5 py-1.5 bg-secondary border border-border rounded-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary font-sans text-xs"
              />
            </div>

            {/* 3. Custody Duration */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                3. Min Custody Duration
              </label>
              <select
                value={custodyDurationMin}
                onChange={(e) => setCustodyDurationMin(e.target.value)}
                className="w-full py-1.5 px-2.5 bg-secondary border border-border rounded-sm text-foreground focus:outline-none text-xs font-mono"
              >
                <option value="">Any Custody Duration</option>
                <option value="30">≥ 30 Days (1 Month)</option>
                <option value="60">≥ 60 Days (2 Months)</option>
                <option value="90">≥ 90 Days (Quarter)</option>
                <option value="180">≥ 180 Days (Half-Year)</option>
                <option value="365">≥ 365 Days (1 Year+)</option>
                <option value="730">≥ 730 Days (2 Years+)</option>
              </select>
            </div>

            {/* 4. Document Completeness */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                4. Max Doc Completeness
              </label>
              <select
                value={documentCompletenessMax}
                onChange={(e) => setDocumentCompletenessMax(e.target.value)}
                className="w-full py-1.5 px-2.5 bg-secondary border border-border rounded-sm text-foreground focus:outline-none text-xs font-mono"
              >
                <option value="">Any Completeness</option>
                <option value="25">≤ 25% (Critical Missing)</option>
                <option value="50">≤ 50% (Substantial Missing)</option>
                <option value="75">≤ 75% (Minor Missing)</option>
                <option value="99">&lt; 100% (Any Incomplete)</option>
              </select>
            </div>

            {/* 5. Legal-Aid Need */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                5. Legal-Aid Need
              </label>
              <select
                value={legalAidNeed}
                onChange={(e) => setLegalAidNeed(e.target.value)}
                className="w-full py-1.5 px-2.5 bg-secondary border border-border rounded-sm text-foreground focus:outline-none text-xs font-mono"
              >
                <option value="">All Matters</option>
                <option value="true">Legal-Aid Required</option>
                <option value="false">Private Counsel / Covered</option>
              </select>
            </div>

            {/* 6. Unresolved Data Conflicts */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                6. Data Conflicts / Exceptions
              </label>
              <select
                value={hasDataConflict}
                onChange={(e) => setHasDataConflict(e.target.value)}
                className="w-full py-1.5 px-2.5 bg-secondary border border-border rounded-sm text-foreground focus:outline-none text-xs font-mono"
              >
                <option value="">All Matters</option>
                <option value="true">Unresolved Conflicts Only</option>
                <option value="false">Verified / Clean Only</option>
              </select>
            </div>

            {/* 7. Current Verdict / Matter State */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                7. Matter State / Stage
              </label>
              <select
                value={matterStatus}
                onChange={(e) => setMatterStatus(e.target.value)}
                className="w-full py-1.5 px-2.5 bg-secondary border border-border rounded-sm text-foreground focus:outline-none text-xs font-mono"
              >
                <option value="">All Matter Stages</option>
                <option value="INTAKE">INTAKE</option>
                <option value="VERIFICATION">VERIFICATION</option>
                <option value="REVIEW">REVIEW</option>
                <option value="LEGAL_AID_REQUIRED">LEGAL_AID_REQUIRED</option>
                <option value="ASSIGNED">ASSIGNED</option>
                <option value="DOCUMENT_PENDING">DOCUMENT_PENDING</option>
                <option value="ANALYSIS_READY">ANALYSIS_READY</option>
                <option value="SUBMITTED">SUBMITTED</option>
                <option value="APPROVED">APPROVED</option>
                <option value="FILED">FILED</option>
                <option value="HEARING_SCHEDULED">HEARING_SCHEDULED</option>
                <option value="ORDER_RECEIVED">ORDER_RECEIVED</option>
                <option value="RELEASE_WORKFLOW">RELEASE_WORKFLOW</option>
                <option value="POST_RELEASE_FOLLOW_UP">POST_RELEASE_FOLLOW_UP</option>
                <option value="CLOSED">CLOSED</option>
                <option value="DATA_CONFLICT">DATA_CONFLICT</option>
              </select>
            </div>

            {/* 8. Hearing Date Range */}
            <div>
              <label className="block text-[10px] uppercase tracking-wider text-muted-foreground mb-1 font-bold">
                8. Hearing Date Range
              </label>
              <div className="grid grid-cols-2 gap-1.5">
                <input
                  type="date"
                  value={hearingDateFrom}
                  onChange={(e) => setHearingDateFrom(e.target.value)}
                  title="Hearing Date From"
                  className="w-full px-1.5 py-1 bg-secondary border border-border rounded-sm text-[11px] font-mono text-foreground focus:outline-none"
                />
                <input
                  type="date"
                  value={hearingDateTo}
                  onChange={(e) => setHearingDateTo(e.target.value)}
                  title="Hearing Date To"
                  className="w-full px-1.5 py-1 bg-secondary border border-border rounded-sm text-[11px] font-mono text-foreground focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Safe Bulk Action Toolbar */}
      {selectedTaskIds.length > 0 && (
        <div className="p-2.5 bg-primary/10 border border-primary/30 rounded-sm flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-primary" />
            <span className="font-bold text-foreground">
              {selectedTaskIds.length} tasks selected
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleSafeBulkAction("ACKNOWLEDGE")}
              disabled={bulkActionLoading}
              className="px-2.5 py-1 bg-secondary border border-border text-foreground rounded-sm hover:bg-secondary/80"
            >
              Acknowledge
            </button>
            <button
              onClick={() => handleSafeBulkAction("ASSIGN_OWNER")}
              disabled={bulkActionLoading}
              className="px-2.5 py-1 bg-primary text-primary-foreground rounded-sm hover:opacity-90"
            >
              Assign to Me
            </button>
            <button
              onClick={() => handleSafeBulkAction("MARK_REVIEWED")}
              disabled={bulkActionLoading}
              className="px-2.5 py-1 bg-secondary border border-border text-foreground rounded-sm hover:bg-secondary/80"
            >
              Mark Reviewed
            </button>
          </div>
        </div>
      )}

      {bulkActionResult && (
        <div
          className={`p-2.5 text-xs font-mono rounded-sm border flex items-center gap-2 ${
            bulkActionResult.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : bulkActionResult.type === "warning"
              ? "bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400"
              : "bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-400"
          }`}
        >
          {bulkActionResult.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          ) : bulkActionResult.type === "warning" ? (
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          )}
          <span>{bulkActionResult.text}</span>
        </div>
      )}

      {/* Table & Cards */}
      {loading ? (
        <div className="p-12 flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
          <span className="text-xs font-mono text-muted-foreground">
            Loading authoritative operational queue…
          </span>
        </div>
      ) : error ? (
        <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-sm text-center">
          <AlertCircle className="w-6 h-6 text-rose-600 mx-auto mb-2" />
          <p className="text-xs font-mono text-rose-700 dark:text-rose-300">{error}</p>
        </div>
      ) : tasks.length === 0 ? (
        <div className="p-8 text-center border-2 border-dashed border-border rounded-sm bg-card">
          <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
          <h3 className="text-sm font-bold font-serif text-foreground">Operational Queue Clear</h3>
          <p className="text-xs text-muted-foreground mt-1">
            No pending tasks matching your role and current filter criteria.
          </p>
        </div>
      ) : (
        <div className="border border-border rounded-sm overflow-hidden bg-card shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-secondary/60 border-b border-border text-[11px] font-mono text-muted-foreground uppercase">
                  <th className="p-3 w-10 text-center">
                    <input
                      type="checkbox"
                      checked={selectedTaskIds.length === tasks.length && tasks.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-border"
                    />
                  </th>
                  <th className="p-3">Task & Accused</th>
                  <th className="p-3">Priority</th>
                  <th className="p-3">SLA Due Date</th>
                  <th className="p-3">Facility / District</th>
                  <th className="p-3">Owner</th>
                  <th className="p-3">Statutory Rationale</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border font-sans">
                {tasks.map((task) => (
                  <tr
                    key={task.id}
                    className={`hover:bg-secondary/30 transition-colors ${
                      selectedTaskIds.includes(task.id) ? "bg-primary/5" : ""
                    }`}
                  >
                    <td className="p-3 text-center">
                      <input
                        type="checkbox"
                        checked={selectedTaskIds.includes(task.id)}
                        onChange={() => handleToggleSelect(task.id)}
                        className="rounded border-border"
                      />
                    </td>

                    <td className="p-3">
                      <div className="font-bold text-foreground font-serif text-sm">
                        {task.accused_name}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <Link
                          to={`/case/${task.case_id}`}
                          className="font-mono text-[10px] text-primary hover:underline font-bold"
                        >
                          {task.case_id}
                        </Link>
                        <span className="text-muted-foreground text-[10px]">•</span>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          {task.custody_duration_days} days custody
                        </span>
                      </div>
                      <div className="text-[11px] text-foreground font-medium mt-1">
                        {task.title}
                      </div>
                    </td>

                    <td className="p-3 whitespace-nowrap space-x-1">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold ${getPriorityBadgeClass(
                          task.priority
                        )}`}
                      >
                        {task.priority}
                      </span>
                      <span
                        className={`inline-block px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold ${getStatusBadgeClass(
                          task.status
                        )}`}
                      >
                        {task.status}
                      </span>
                    </td>

                    <td className="p-3 whitespace-nowrap text-xs font-mono">
                      {formatDueDateSLA(task.due_date)}
                    </td>

                    <td className="p-3 text-[11px] text-muted-foreground">
                      <div>{task.facility || "—"}</div>
                      <div className="text-[10px] font-mono text-muted-foreground/80">
                        {task.district || "—"}
                      </div>
                    </td>

                    <td className="p-3 text-[11px]">
                      <div className="font-mono font-bold text-foreground text-[10px]">
                        {task.owner_role.replace(/_/g, " ")}
                      </div>
                      <div className="text-[10px] text-muted-foreground">
                        {task.owner_name || "Unassigned"}
                      </div>
                    </td>

                    <td className="p-3 text-[11px] text-muted-foreground max-w-xs">
                      <p className="line-clamp-2">{task.reason}</p>
                      <div className="text-[9px] font-mono text-primary/80 mt-1">
                        Escalation: {task.escalation_path}
                      </div>
                    </td>

                    <td className="p-3 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        {task.is_consequential ? (
                          <button
                            onClick={() => setConsequentialModalTask(task)}
                            className="px-2.5 py-1 bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-[11px] font-mono rounded-sm flex items-center gap-1 hover:bg-red-500/20"
                          >
                            <Scale className="w-3 h-3" /> Consequential Action
                          </button>
                        ) : onActionClick ? (
                          <button
                            onClick={() => onActionClick(task, task.task_type)}
                            className="px-2.5 py-1 bg-primary text-primary-foreground text-[11px] font-mono font-bold rounded-sm hover:opacity-90"
                          >
                            Act
                          </button>
                        ) : (
                          <Link
                            to={`/case/${task.case_id}${task.task_type === "PREPARE_AND_SIGN_OFF_DRAFT" ? "?tab=draft" : ""}`}
                            className={`px-2.5 py-1 border text-[11px] font-mono rounded-sm flex items-center gap-1 transition-colors ${
                              task.task_type === "PREPARE_AND_SIGN_OFF_DRAFT"
                                ? "bg-primary text-primary-foreground border-primary hover:opacity-90 font-bold"
                                : "bg-secondary border-border text-foreground hover:bg-secondary/80"
                            }`}
                          >
                            {task.task_type === "PREPARE_AND_SIGN_OFF_DRAFT" ? (
                              <>⚡ Draft Petition <ChevronRight className="w-3 h-3" /></>
                            ) : (
                              <>Inspect <ChevronRight className="w-3 h-3" /></>
                            )}
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Consequential Action Safeguard Dialog */}
      {consequentialModalTask && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border p-6 rounded-sm shadow-xl max-w-lg w-full space-y-4">
            <div className="flex items-center gap-2.5 text-red-600">
              <Scale className="w-6 h-6" />
              <h3 className="text-base font-serif font-bold text-foreground">
                Legally Consequential Action Safeguard
              </h3>
            </div>
            <div className="text-xs text-muted-foreground space-y-2">
              <p>
                The action for task <strong>{consequentialModalTask.id}</strong> (
                <em>{consequentialModalTask.title}</em>) is legally or operationally consequential.
              </p>
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-sm font-mono text-[11px] text-red-700 dark:text-red-300">
                <strong>Mandatory Statutory Rule:</strong> Consequential legal actions (Supervisory
                Approval, Court Registry Filing, Prison Release Confirmation, or Matter Closure)
                cannot be executed in bulk or via generic task updates.
              </div>
              <p>
                Each action requires certified case document verification, cryptographic hash
                generation, and immutable audit logging.
              </p>
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setConsequentialModalTask(null)}
                className="px-3 py-1.5 bg-secondary text-foreground text-xs font-mono rounded-sm border border-border"
              >
                Close
              </button>
              <Link
                to={`/case/${consequentialModalTask.case_id}${consequentialModalTask.task_type === "PREPARE_AND_SIGN_OFF_DRAFT" ? "?tab=draft" : ""}`}
                className="px-4 py-1.5 bg-primary text-primary-foreground text-xs font-mono font-bold rounded-sm flex items-center gap-1.5 hover:opacity-90"
              >
                {consequentialModalTask.task_type === "PREPARE_AND_SIGN_OFF_DRAFT" ? "Open Bail Petition Draft" : "Open Case Dossier"} <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
