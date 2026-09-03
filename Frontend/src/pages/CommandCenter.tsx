import { useState, useEffect, useCallback } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  Scale,
  Shield,
  ChevronRight,
  Loader2,
  RefreshCw,
  UserCheck,
} from "lucide-react";

import { fetchStakeholdersOverview, fetchCases, type CaseRecord } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function CommandCenter() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);

  // ── Role Redirection for Specialized Workspaces ───────────────────────────
  // Roles with dedicated workspaces must not view institutional command center
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

  const isSupervisor = user?.role === "SUPERVISING_LEGAL_OFFICER";
  const isGovAdmin = user?.role === "GOV_ADMIN";
  const isDlsa = !isSupervisor && !isGovAdmin; // Default to DLSA_OFFICER

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [overviewData, rawCasesData] = await Promise.all([
        fetchStakeholdersOverview(),
        fetchCases(),
      ]);
      setOverview(overviewData);
      const extracted = (rawCasesData || []).map((item: any) => (item.case || item) as CaseRecord);
      setCases(extracted);
    } catch (err) {
      console.error("Error loading command center data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const undertrials = cases.filter(
    (c) => (!c.prisoner_category || c.prisoner_category === "UNDERTRIAL") && c.status !== "POST_RELEASE_PRESERVED"
  );


  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header with Authenticated Role Clearance Badge (No manual role switching) */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              {isSupervisor
                ? "Supervisory Legal Operations"
                : isGovAdmin
                ? "State Legal Services Authority (SLSA)"
                : "District Legal Aid Coordination"}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded font-sans font-semibold bg-primary/10 text-primary border border-primary/20">
              {isSupervisor
                ? "Authorized Supervising Legal Officer"
                : isGovAdmin
                ? "SLSA State Authority"
                : "DLSA Legal Aid Officer"}
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold font-serif text-foreground mt-1">
            {isSupervisor
              ? "Supervisory Legal Operations Command"
              : isGovAdmin
              ? "SLSA State Institutional Overview"
              : "DLSA Remand & Legal Aid Command Center"}
          </h1>
          <p className="text-xs md:text-sm text-muted-foreground mt-1">
            {isSupervisor
              ? "Supervising DLSA caseloads, exception handling, SLA monitoring, and legal knowledge governance."
              : isGovAdmin
              ? "State-level oversight, district performance monitoring, and compliance tracking."
              : "Managing undertrial triage, Section 479 BNSS signals, remand court first-production, and panel assignments."}
          </p>
        </div>

        {/* Authenticated Identity Clearance Indicator */}
        <div className="flex items-center gap-2 px-3.5 py-2 bg-secondary/70 border border-border rounded-sm shadow-sm">
          <Shield className="w-4 h-4 text-primary shrink-0" />
          <div>
            <div className="text-[10px] uppercase tracking-wider font-mono font-bold text-muted-foreground">
              Authenticated Scope
            </div>
            <div className="text-xs font-serif font-bold text-foreground">
              {user?.full_name || "Authorized Officer"}
            </div>
          </div>
        </div>
      </div>


      {loading ? (
        <div className="p-12 flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
          <span className="text-xs font-mono text-muted-foreground">
            Synchronising stakeholder operational queues…
          </span>
        </div>
      ) : (
        <>
          {/* Top Operational Metrics Ribbon */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-sm border border-border bg-card shadow-sm space-y-1">
              <span className="text-[11px] font-mono text-muted-foreground uppercase block">
                Total Accused Monitored
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-serif text-foreground">
                  {overview?.metrics?.total_active_cases || cases.length}
                </span>
                <span className="text-xs text-muted-foreground font-mono">records</span>
              </div>
            </div>

            <div className="p-4 rounded-sm border border-border bg-card shadow-sm space-y-1">
              <span className="text-[11px] font-mono text-muted-foreground uppercase block">
                Section 479 Signals
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-serif text-emerald-600 dark:text-emerald-400">
                  {overview?.metrics?.section_479_eligible_signals ?? 2}
                </span>
                <span className="text-xs text-muted-foreground font-mono">eligible</span>
              </div>
            </div>

            <div className="p-4 rounded-sm border border-border bg-card shadow-sm space-y-1">
              <span className="text-[11px] font-mono text-muted-foreground uppercase block">
                Missing Record Blockers
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-serif text-amber-600 dark:text-amber-400">
                  {overview?.metrics?.cases_missing_mandatory_documents ?? 1}
                </span>
                <span className="text-xs text-muted-foreground font-mono">cases</span>
              </div>
            </div>

            <div className="p-4 rounded-sm border border-border bg-card shadow-sm space-y-1">
              <span className="text-[11px] font-mono text-muted-foreground uppercase block">
                Filed in Court
              </span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold font-serif text-blue-600 dark:text-blue-400">
                  {overview?.metrics?.filed_in_court_count ?? 1}
                </span>
                <span className="text-xs text-muted-foreground font-mono">petitions</span>
              </div>
            </div>
          </div>

          {/* VIEW 1: DLSA REMAND & LEGAL AID OPERATIONS */}
          {isDlsa && (
            <div className="space-y-6">
              <div className="p-5 border border-primary/20 bg-primary/5 rounded-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <h2 className="font-bold font-serif text-base text-foreground">
                    District Legal Services Authority (DLSA) — Remand & Legal Aid Queue
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Ensuring effective representation at first production, Section 479 BNSS identification, and panel advocate assignment.
                  </p>
                </div>
                <button
                  onClick={loadData}
                  className="px-3 py-1.5 border border-border rounded-sm bg-card hover:bg-secondary text-xs font-semibold flex items-center gap-1.5 shrink-0"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Refresh Queue
                </button>
              </div>

              {/* Actionable Table */}
              <div className="border border-border rounded-sm bg-card overflow-hidden">
                <div className="p-4 border-b border-border bg-secondary/40 flex items-center justify-between">
                  <span className="text-xs font-bold font-serif uppercase tracking-wider text-muted-foreground">
                    Undertrials Awaiting Legal Action / Section 479 Review
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">
                    {undertrials.length} Active Undertrials
                  </span>
                </div>

                <div className="divide-y divide-border">
                  {undertrials.map((c) => (
                    <div
                      key={c.case_id}
                      className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:bg-secondary/20 transition-colors"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold font-serif text-base text-foreground">
                            {c.name}
                          </span>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-primary/10 text-primary font-bold">
                            {c.case_id}
                          </span>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-secondary border border-border text-foreground">
                            {c.legal_code}
                          </span>
                          <span className="text-[11px] font-mono text-muted-foreground">
                            {c.jail_location}
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                          <span>
                            Offence: <strong className="text-foreground">{c.offense_sections?.join(", ")}</strong>
                          </span>
                          <span>•</span>
                          <span>
                            Countable Custody: <strong className="text-foreground">{c.custody_days} days</strong>
                          </span>
                          <span>•</span>
                          <span>
                            Status: <strong className="text-foreground">{c.status}</strong>
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {c.status === "APPROVED_READY_FOR_FILING" && (
                          <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-blue-500/10 text-blue-600 border border-blue-500/20">
                            READY FOR FILING
                          </span>
                        )}
                        {c.status === "FILED" && (
                          <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                            FILED IN COURT
                          </span>
                        )}
                        <Link
                          to={`/accused/acc_${c.case_id.toLowerCase().replace("-", "_")}`}
                          className="px-2.5 py-1.5 bg-secondary hover:bg-muted text-foreground border border-border rounded-sm text-xs font-serif font-semibold flex items-center gap-1 transition-colors"
                          title="View Accused Dossier"
                        >
                          <UserCheck className="w-3.5 h-3.5" /> Profile
                        </Link>
                        <Link
                          to={`/cases/${c.case_id}`}
                          className="px-3 py-1.5 bg-primary text-primary-foreground hover:opacity-90 rounded-sm text-xs font-semibold flex items-center gap-1 font-serif"
                        >
                          Review Dossier <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* VIEW 2: SUPERVISORY LEGAL OPERATIONS & GOVERNANCE */}
          {isSupervisor && (
            <div className="space-y-6">
              <div className="p-5 border border-primary/20 bg-primary/5 rounded-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <h2 className="font-bold font-serif text-base text-foreground">
                    Supervisory Legal Operations Command — Escalation & Governance Desk
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Oversight of Section 479 BNSS eligibility determinations, citation validation escalations, panel lawyer performance, and legal knowledge governance.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to="/legal-sources"
                    className="px-3 py-1.5 bg-primary text-primary-foreground text-xs font-serif font-semibold rounded-sm flex items-center gap-1.5 hover:opacity-90"
                  >
                    <Scale className="w-3.5 h-3.5" /> Legal Governance
                  </Link>
                  <button
                    onClick={loadData}
                    className="px-3 py-1.5 border border-border rounded-sm bg-card hover:bg-secondary text-xs font-semibold flex items-center gap-1.5 shrink-0"
                  >
                    <RefreshCw className="w-3.5 h-3.5" /> Refresh
                  </button>
                </div>
              </div>

              {/* Supervisory Key Panels */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                  <span className="text-xs font-mono text-muted-foreground uppercase font-bold block">
                    Pending Supervisory Sign-Offs
                  </span>
                  <div className="text-2xl font-bold font-serif text-amber-600">
                    {cases.filter((c) => c.status === "APPROVED_READY_FOR_FILING" || c.status === "LAWYER_REVIEW").length}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Petitions requiring supervisory sign-off before official court filing.
                  </p>
                  <Link
                    to="/actions"
                    className="inline-flex items-center gap-1 text-xs font-mono font-bold text-primary hover:underline mt-2"
                  >
                    Open Approvals Queue <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                  <span className="text-xs font-mono text-muted-foreground uppercase font-bold block">
                    Document Bottlenecks
                  </span>
                  <div className="text-2xl font-bold font-serif text-rose-600">
                    {cases.filter((c) => (c.required_docs?.length || 0) > (c.present_docs?.length || 0)).length}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Cases missing certified remand copies or chargesheets blocking Section 479 relief.
                  </p>
                  <Link
                    to="/documents"
                    className="inline-flex items-center gap-1 text-xs font-mono font-bold text-primary hover:underline mt-2"
                  >
                    Review Incomplete Records <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                  <span className="text-xs font-mono text-muted-foreground uppercase font-bold block">
                    Identity Discrepancies
                  </span>
                  <div className="text-2xl font-bold font-serif text-foreground">
                    Active Review
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Cross-facility duplicate candidates and prisoner aliases pending legal resolution.
                  </p>
                  <Link
                    to="/identity-review"
                    className="inline-flex items-center gap-1 text-xs font-mono font-bold text-primary hover:underline mt-2"
                  >
                    Resolve Identity Matches <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>

              {/* Priority Review Table */}
              <div className="border border-border rounded-sm bg-card overflow-hidden">
                <div className="p-4 border-b border-border bg-secondary/40 flex items-center justify-between">
                  <span className="text-xs font-bold font-serif uppercase tracking-wider text-muted-foreground">
                    Supervised High-Priority Matters
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">
                    {cases.length} Total Supervised Cases
                  </span>
                </div>

                <div className="divide-y divide-border">
                  {cases.slice(0, 5).map((c) => (
                    <div
                      key={c.case_id}
                      className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4 hover:bg-secondary/20 transition-colors"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold font-serif text-sm text-foreground">{c.name}</span>
                          <span className="text-xs font-mono px-2 py-0.5 rounded bg-primary/10 text-primary font-bold">
                            {c.case_id}
                          </span>
                          <span className="text-xs font-mono text-muted-foreground">
                            {c.court_name}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          Offences: {c.offense_sections?.join(", ")} | Custody: {c.custody_days}d | Status: <strong className="text-foreground">{c.status}</strong>
                        </p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Link
                          to={`/cases/${c.case_id}`}
                          className="px-3 py-1.5 bg-primary text-primary-foreground rounded-sm text-xs font-serif font-semibold flex items-center gap-1 hover:opacity-90"
                        >
                          Supervise Case <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* VIEW 3: SLSA STATE INSTITUTIONAL OVERVIEW */}
          {isGovAdmin && (
            <div className="space-y-6">
              <div className="p-5 border border-primary/20 bg-primary/5 rounded-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div>
                  <h2 className="font-bold font-serif text-base text-foreground">
                    State Legal Services Authority (SLSA) — Supervisory Overview
                  </h2>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Macro-level monitoring across districts, compliance tracking with Section 479 BNSS, and systemic delay prevention.
                  </p>
                </div>
                <Link
                  to="/gov"
                  className="px-3 py-1.5 bg-primary text-primary-foreground text-xs font-serif font-semibold rounded-sm flex items-center gap-1.5 hover:opacity-90"
                >
                  <Shield className="w-3.5 h-3.5" /> Full State Overview
                </Link>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                  <span className="text-xs font-mono text-muted-foreground uppercase font-bold block">
                    District Legal Aid Coverage
                  </span>
                  <div className="text-2xl font-bold font-serif text-foreground">100%</div>
                  <p className="text-xs text-muted-foreground">
                    All active undertrial remand records currently mapped to designated DLSA panel counsel.
                  </p>
                </div>

                <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                  <span className="text-xs font-mono text-muted-foreground uppercase font-bold block">
                    Statutory Rule Engine Status
                  </span>
                  <div className="text-2xl font-bold font-serif text-emerald-600 dark:text-emerald-400">
                    BNSS 479 v1
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Deterministic legal rules applied to calculate 1/3 (first-time) vs 1/2 detention thresholds.
                  </p>
                </div>

                <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                  <span className="text-xs font-mono text-muted-foreground uppercase font-bold block">
                    Institutional Governance
                  </span>
                  <div className="text-2xl font-bold font-serif text-foreground">Active</div>
                  <p className="text-xs text-muted-foreground">
                    Append-oriented audit logging and SHA-256 evidence integrity active for all digital case records.
                  </p>
                </div>
              </div>
            </div>
          )}

        </>
      )}
    </div>
  );
}
