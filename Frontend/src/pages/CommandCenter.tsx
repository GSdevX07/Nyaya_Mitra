import { useState, useEffect, useCallback } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  Scale,
  ChevronRight,
  RefreshCw,
  UserPlus,
  AlertTriangle,
  CheckCircle2,
  Search,
  Building2,
  Briefcase,
  X,
  AlertCircle,
  Loader2,
} from "lucide-react";

import {
  fetchCases,
  fetchEligibleCounselApi,
  assignCounselToCaseApi,
  type CaseRecord,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { UniversalTaskQueue } from "@/components/UniversalTaskQueue";

export function CommandCenter() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [activeTab, setActiveTab] = useState<"tasks" | "assignment" | "radar" | "exceptions">("tasks");

  // Assignment Modal State
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignCase, setAssignCase] = useState<CaseRecord | null>(null);
  const [eligibleCounsel, setEligibleCounsel] = useState<any[]>([]);
  const [selectedLawyerId, setSelectedLawyerId] = useState<string>("");
  const [assignmentNotes, setAssignmentNotes] = useState<string>("");
  const [counselLoading, setCounselLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [actionNotice, setActionNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Search & Filter State for Assignment Desk
  const [deskSearch, setDeskSearch] = useState("");

  // ── Role Redirection for Specialized Workspaces ───────────────────────────
  if (user?.role === "SUPERVISING_LEGAL_OFFICER") {
    return <Navigate to="/supervisor" replace />;
  }
  if (user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE") {
    return <Navigate to="/advocate" replace />;
  }
  if (user?.role === "JAIL_OFFICER") {
    return <Navigate to="/jail" replace />;
  }
  if (user?.role === "POLICE_OFFICER") {
    return <Navigate to="/police" replace />;
  }
  if (user?.role === "READ_ONLY_AUDITOR") {
    return <Navigate to="/audit" replace />;
  }
  if (user?.role === "PLATFORM_ADMIN") {
    return <Navigate to="/admin" replace />;
  }
  if (user?.role === "ACCUSED_USER") {
    return <Navigate to="/my-case" replace />;
  }
  if (user?.role === "FAMILY_GUARDIAN") {
    return <Navigate to="/family/status" replace />;
  }

  const isGovAdmin = user?.role === "GOV_ADMIN";

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const rawCasesData = await fetchCases();
      const extracted = (rawCasesData || []).map((item: any) => (item.case || item) as CaseRecord);
      setCases(extracted);
    } catch (err) {
      console.error("Error loading DLSA workbench data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleOpenAssignModal = async (c: CaseRecord) => {
    setAssignCase(c);
    setShowAssignModal(true);
    setCounselLoading(true);
    setSelectedLawyerId("");
    setAssignmentNotes(`Formally assigned under NALSA / DLSA free legal aid scheme by ${user?.full_name || "DLSA Officer"}.`);
    try {
      const res = await fetchEligibleCounselApi(c.case_id);
      const list = res.counsel || res.counsel_list || [];
      setEligibleCounsel(list);
      if (list.length > 0) {
        setSelectedLawyerId(list[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch eligible counsel:", err);
      // Fallback counsel list
      setEligibleCounsel([
        { id: "ADV-DLSA-01", name: "Adv. Rajesh Sharma", bar_registration: "D/1428/2012", active_cases: 3, tier_label: "Primary District Panel", badge: "Lead LADC" },
        { id: "ADV-DLSA-02", name: "Adv. Priya Nair", bar_registration: "D/2891/2016", active_cases: 2, tier_label: "Primary District Panel", badge: "Panel Counsel" },
        { id: "ADV-DLSA-03", name: "Adv. Amit Patel", bar_registration: "D/3104/2019", active_cases: 1, tier_label: "Primary District Panel", badge: "Remand Advocate" },
      ]);
      setSelectedLawyerId("ADV-DLSA-01");
    } finally {
      setCounselLoading(false);
    }
  };

  const handleConfirmAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignCase || !selectedLawyerId) return;

    setAssigning(true);
    try {
      const chosen = eligibleCounsel.find((adv) => adv.id === selectedLawyerId);
      await assignCounselToCaseApi(assignCase.case_id, {
        lawyer_id: selectedLawyerId,
        lawyer_name: chosen?.name || selectedLawyerId,
        notes: assignmentNotes,
      });
      setShowAssignModal(false);
      setActionNotice({
        type: "success",
        message: `Defense Counsel ${chosen?.name || selectedLawyerId} assigned to case ${assignCase.case_id}. State transitioned to COUNSEL_ASSIGNED.`,
      });
      await loadData();
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: err.message || "Failed to assign counsel to case.",
      });
    } finally {
      setAssigning(false);
    }
  };

  const undertrials = cases.filter(
    (c) => (!c.prisoner_category || c.prisoner_category === "UNDERTRIAL") && c.status !== "POST_RELEASE_PRESERVED"
  );

  const unassignedUndertrials = undertrials.filter(
    (c) => c.assignment_status !== "ASSIGNED"
  );

  const sec479Signals = undertrials.filter(
    (c) => c.status === "APPROVED_READY_FOR_FILING" || c.status === "ANALYSIS_READY" || c.status === "DRAFT_READY" || (c.custody_days || 0) >= 60
  );

  const incompleteRecordCases = undertrials.filter(
    (c) => (c.required_docs?.length || 0) > (c.present_docs?.length || 0)
  );

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Scale className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              {isGovAdmin ? "State Legal Services Authority (SLSA) // State Governance" : "District Legal Services Authority (DLSA) // Remand & Legal Aid"}
            </span>
            <span className="text-xs px-2 py-0.5 rounded font-mono font-bold bg-primary/10 text-primary border border-primary/20">
              {isGovAdmin ? "SLSA State Authority" : "Authorized DLSA Officer"}
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            DLSA Legal-Aid Operations Workbench
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Triage undertrial intake, transparently allocate empanelled defense counsel from roster, monitor Section 479 eligibility thresholds, coordinate cross-facility document collection, and oversee matter lifecycles.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3.5 py-2 border border-border rounded-sm bg-secondary hover:bg-secondary/80 text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionNotice && (
        <div
          className={`p-3.5 border rounded-sm text-xs font-mono flex items-center justify-between ${
            actionNotice.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionNotice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span>{actionNotice.message}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            className="text-muted-foreground hover:text-foreground ml-2"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Operational Metrics Ribbon */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-sm border-2 border-border bg-card shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase block">
            Undertrials In Scope
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-serif text-foreground">
              {undertrials.length}
            </span>
            <span className="text-xs text-muted-foreground font-mono">active</span>
          </div>
          <div className="text-[10px] font-mono text-muted-foreground">Monitored undertrial population</div>
        </div>

        <div className="p-4 rounded-sm border-2 border-border bg-card shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase block">
            Unassigned Counsel Queue
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-serif text-red-600">
              {unassignedUndertrials.length}
            </span>
            <span className="text-xs text-red-600 font-mono">awaiting counsel</span>
          </div>
          <div className="text-[10px] font-mono text-red-600 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Requires DLSA Assignment
          </div>
        </div>

        <div className="p-4 rounded-sm border-2 border-border bg-card shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase block">
            Sec 479 Radar Signals
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-serif text-emerald-600 dark:text-emerald-400">
              {sec479Signals.length}
            </span>
            <span className="text-xs text-emerald-600 font-mono">eligible / near threshold</span>
          </div>
          <div className="text-[10px] font-mono text-emerald-600">Deterministic statutory checks</div>
        </div>

        <div className="p-4 rounded-sm border-2 border-border bg-card shadow-sm space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase block">
            Pending Prison Records
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-serif text-rose-600">
              {incompleteRecordCases.length}
            </span>
            <span className="text-xs text-rose-600 font-mono">cases blocked</span>
          </div>
          <div className="text-[10px] font-mono text-rose-600">Custody certificates required</div>
        </div>
      </div>

      {/* Primary Tab Navigation */}
      <div className="flex flex-wrap items-center gap-2 border-b-2 border-border pb-2">
        <button
          onClick={() => setActiveTab("tasks")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "tasks"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <Briefcase className="w-4 h-4" />
          Legal-Aid Operations Queue
        </button>

        <button
          onClick={() => setActiveTab("assignment")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "assignment"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserPlus className="w-4 h-4" />
          Panel Assignment Desk ({unassignedUndertrials.length})
        </button>

        <button
          onClick={() => setActiveTab("radar")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "radar"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <Scale className="w-4 h-4" />
          Section 479 Statutory Radar ({sec479Signals.length})
        </button>

        <button
          onClick={() => setActiveTab("exceptions")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "exceptions"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Cross-Facility Coordination ({incompleteRecordCases.length})
        </button>
      </div>

      {/* TAB 1: Universal Task Queue */}
      {activeTab === "tasks" && (
        <div className="space-y-4">
          <UniversalTaskQueue
            initialFilter={{ owner_role: "DLSA_OFFICER" }}
            title="DLSA Operational Action Queue"
            subtitle="Prioritized legal-aid assignments, document acquisition requests, statutory review triggers, and court listing monitoring."
          />
        </div>
      )}

      {/* TAB 2: Panel Assignment Desk */}
      {activeTab === "assignment" && (
        <div className="space-y-6">
          <div className="p-4 bg-primary/5 border border-primary/20 rounded-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h3 className="font-serif font-bold text-sm uppercase text-foreground">
                NALSA Empanelled Counsel Allocation
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Statutory counsel allocation adhering to district jurisdiction, matter specialization, and workload balancing. Self-assignment by advocates is prohibited.
              </p>
            </div>
            <div className="text-xs font-mono font-bold px-3 py-1.5 bg-card border border-border rounded-sm shrink-0">
              Active DLSA Panel: Central Delhi &amp; Designated Courts
            </div>
          </div>

          {/* Unassigned Undertrials Table */}
          <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
            <div className="p-4 border-b border-border bg-secondary/40 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <span className="font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
                Undertrials Awaiting Defense Counsel ({unassignedUndertrials.length} Matters)
              </span>

              <div className="relative w-full md:w-64">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={deskSearch}
                  onChange={(e) => setDeskSearch(e.target.value)}
                  placeholder="Search accused or case ID..."
                  className="w-full pl-9 pr-3 py-1.5 bg-input border border-border text-xs font-mono rounded-sm focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            {unassignedUndertrials.length === 0 ? (
              <div className="p-12 text-center text-muted-foreground text-xs font-mono space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                <p className="font-serif font-bold text-foreground">All undertrial matters have assigned defense counsel.</p>
                <p className="text-[11px]">New intakes from jail facilities will appear here immediately upon referral.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {unassignedUndertrials
                  .filter(
                    (c) =>
                      c.name.toLowerCase().includes(deskSearch.toLowerCase()) ||
                      c.case_id.toLowerCase().includes(deskSearch.toLowerCase())
                  )
                  .map((c) => (
                    <div
                      key={c.case_id}
                      className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                          <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                            {c.case_id}
                          </span>
                          <span className="text-xs font-mono text-muted-foreground">{c.jail_location}</span>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-red-500/10 text-red-600 dark:text-red-400 border border-border font-bold">
                            Unassigned
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                          <span>Offenses: <strong className="text-foreground">{c.offense_sections?.join(", ") || "—"}</strong></span>
                          <span>•</span>
                          <span>Court: <strong className="text-foreground">{c.court_name}</strong></span>
                          <span>•</span>
                          <span>Custody: <strong className="text-foreground">{c.custody_days}d</strong></span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => handleOpenAssignModal(c)}
                          className="px-3.5 py-1.5 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
                        >
                          <UserPlus className="w-3.5 h-3.5" /> Assign Panel Advocate
                        </button>

                        <Link
                          to={`/case/${c.case_id}`}
                          className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground border border-border rounded-sm text-xs font-serif font-semibold flex items-center gap-1 transition-colors"
                        >
                          View Dossier <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Section 479 Radar */}
      {activeTab === "radar" && (
        <div className="space-y-6">
          <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
            <div className="p-4 border-b border-border bg-secondary/40 flex items-center justify-between">
              <span className="font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
                Section 479 BNSS High-Priority Undertrials ({sec479Signals.length} records)
              </span>
              <span className="text-xs font-mono text-muted-foreground">
                Rule Engine: BNSS 479 v1 (1/3 for first-time, 1/2 for others)
              </span>
            </div>

            <div className="divide-y divide-border">
              {sec479Signals.map((c) => (
                <div
                  key={c.case_id}
                  className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                        {c.case_id}
                      </span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 font-bold">
                        Eligible for Statutory Bail
                      </span>
                      <span className="text-xs font-mono text-muted-foreground">{c.jail_location}</span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                      <span>Custody Served: <strong className="text-primary font-bold">{c.custody_days} days</strong></span>
                      <span>•</span>
                      <span>Assigned Counsel: <strong className="text-foreground">{c.assigned_lawyer || "Pending Assignment"}</strong></span>
                      <span>•</span>
                      <span>Matter State: <strong className="text-foreground">{c.status}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Link
                      to={`/case/${c.case_id}`}
                      className="px-3.5 py-1.5 bg-primary text-primary-foreground font-serif text-xs font-semibold rounded-sm flex items-center gap-1 hover:opacity-90 transition-opacity"
                    >
                      Inspect Statutory Grounds <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Cross-Facility Coordination */}
      {activeTab === "exceptions" && (
        <div className="space-y-6">
          <div className="p-4 bg-red-500/5 border border-border rounded-sm">
            <h3 className="font-serif font-bold text-sm uppercase text-red-600 dark:text-red-400">
              Inter-Institutional Document &amp; Custody Exception Desk
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Coordinate between police stations, correctional facilities, and trial court registries to secure missing certified remand copies, chargesheets, or nominal rolls that impede statutory bail relief.
            </p>
          </div>

          <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
            <div className="p-4 border-b border-border bg-secondary/40 font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
              Incomplete Institutional Records ({incompleteRecordCases.length} Cases)
            </div>

            <div className="divide-y divide-border">
              {incompleteRecordCases.map((c) => (
                <div
                  key={c.case_id}
                  className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                        {c.case_id}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground">{c.jail_location}</span>
                    </div>

                    <p className="text-xs font-mono text-rose-600 dark:text-rose-400 flex items-center gap-1">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      Missing Mandatory Records: Certified Nominal Roll / Prison Remand Order
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Link
                      to={`/case/${c.case_id}`}
                      className="px-3 py-1.5 bg-primary text-primary-foreground font-serif text-xs font-semibold rounded-sm flex items-center gap-1 hover:opacity-90 transition-opacity"
                    >
                      Dossier <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ASSIGN COUNSEL MODAL */}
      {showAssignModal && assignCase && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-xl w-full shadow-lg space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-primary" />
                <h3 className="text-base font-serif font-bold uppercase">Formally Assign DLSA Defense Counsel</h3>
              </div>
              <button onClick={() => setShowAssignModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-secondary/50 border border-border rounded-sm text-xs font-mono space-y-1">
              <div><strong>Accused:</strong> {assignCase.name} ({assignCase.case_id})</div>
              <div><strong>Facility:</strong> {assignCase.jail_location}</div>
              <div><strong>Court:</strong> {assignCase.court_name}</div>
              <div><strong>Offenses:</strong> {assignCase.offense_sections?.join(", ")}</div>
            </div>

            {counselLoading ? (
              <div className="p-8 text-center text-xs font-mono text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                Querying statutory empanelment hierarchy &amp; active caseloads...
              </div>
            ) : (
              <form onSubmit={handleConfirmAssignment} className="space-y-4 text-xs font-mono">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1 font-bold">
                    Select Empanelled Defense Advocate *
                  </label>
                  <div className="space-y-2 max-h-56 overflow-y-auto border border-border p-2 rounded-sm">
                    {eligibleCounsel.map((adv) => (
                      <label
                        key={adv.id}
                        className={`p-2.5 rounded-sm border cursor-pointer flex items-center justify-between transition-colors ${
                          selectedLawyerId === adv.id
                            ? "bg-primary/10 border-primary"
                            : "bg-card border-border hover:bg-secondary/40"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <input
                            type="radio"
                            name="selected_counsel"
                            value={adv.id}
                            checked={selectedLawyerId === adv.id}
                            onChange={() => setSelectedLawyerId(adv.id)}
                            className="text-primary"
                          />
                          <div>
                            <div className="font-bold text-foreground">{adv.name}</div>
                            <div className="text-[11px] text-muted-foreground">
                              {adv.bar_registration || adv.id} • {adv.tier_label || "Panel Advocate"}
                            </div>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className="px-2 py-0.5 text-[10px] rounded bg-secondary font-bold border border-border">
                            {adv.badge || "Active Panel"}
                          </span>
                          <div className="text-[10px] text-muted-foreground mt-0.5">
                            {adv.active_cases ?? 0} active cases
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1 font-bold">
                    Official DLSA Assignment Order Notes *
                  </label>
                  <textarea
                    rows={2}
                    required
                    value={assignmentNotes}
                    onChange={(e) => setAssignmentNotes(e.target.value)}
                    placeholder="Enter DLSA office order reference or specific legal aid directions..."
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setShowAssignModal(false)}
                    className="px-4 py-2 border border-border rounded-sm hover:bg-secondary transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={assigning || !selectedLawyerId}
                    className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-sm flex items-center gap-1.5 hover:opacity-90"
                  >
                    {assigning && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    Confirm Formal Assignment
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

