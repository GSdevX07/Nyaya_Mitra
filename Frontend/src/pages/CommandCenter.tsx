import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Building2,
  Scale,
  Shield,
  Briefcase,
  AlertTriangle,
  Clock,
  ChevronRight,
  Loader2,
  RefreshCw,
  UserCheck,
} from "lucide-react";
import { fetchStakeholdersOverview, fetchCases, type CaseRecord } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type StakeholderRole = "jail" | "dlsa" | "slsa" | "advocate";

function getInitialStakeholderRole(role?: string): StakeholderRole {
  if (role === "JAIL_OFFICER") return "jail";
  if (role === "DEFENSE_ADVOCATE" || role === "CONTROLLED_EXTERNAL_ADVOCATE") return "advocate";
  if (role === "GOV_ADMIN" || role === "READ_ONLY_AUDITOR") return "slsa";
  return "dlsa";
}

export function CommandCenter() {
  const { user } = useAuth();
  const [role, setRole] = useState<StakeholderRole>(() => getInitialStakeholderRole(user?.role));
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>(null);
  const [cases, setCases] = useState<CaseRecord[]>([]);

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
  const convicted = cases.filter((c) => c.prisoner_category === "CONVICTED");
  const postRelease = cases.filter(
    (c) => c.status === "POST_RELEASE_PRESERVED" || c.status === "RELEASED"
  );

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header & Role Switcher */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Multi-Stakeholder Legal Operations
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-primary/10 text-primary border border-primary/20">
              Institutional Visibility
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold font-serif text-foreground mt-1">
            Nyaya Mitra Command Center
          </h1>
          <p className="text-xs md:text-sm text-muted-foreground mt-1">
            Coordinating legal services across Prisons, Remand Courts, DLSAs, SLSAs, and Legal Aid Advocates.
          </p>
        </div>

        {/* Stakeholder Role Selector */}
        <div className="flex items-center gap-1.5 p-1 bg-secondary border border-border rounded-sm">
          <button
            onClick={() => setRole("dlsa")}
            className={`px-3 py-1.5 rounded-sm text-xs font-semibold font-serif flex items-center gap-1.5 transition-all ${
              role === "dlsa"
                ? "bg-card text-foreground shadow-sm font-bold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Scale className="w-3.5 h-3.5 text-primary" /> DLSA Remand Desk
          </button>
          <button
            onClick={() => setRole("jail")}
            className={`px-3 py-1.5 rounded-sm text-xs font-semibold font-serif flex items-center gap-1.5 transition-all ${
              role === "jail"
                ? "bg-card text-foreground shadow-sm font-bold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Building2 className="w-3.5 h-3.5 text-primary" /> Jail Operations
          </button>
          <button
            onClick={() => setRole("advocate")}
            className={`px-3 py-1.5 rounded-sm text-xs font-semibold font-serif flex items-center gap-1.5 transition-all ${
              role === "advocate"
                ? "bg-card text-foreground shadow-sm font-bold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Briefcase className="w-3.5 h-3.5 text-primary" /> Defence Counsel
          </button>
          <button
            onClick={() => setRole("slsa")}
            className={`px-3 py-1.5 rounded-sm text-xs font-semibold font-serif flex items-center gap-1.5 transition-all ${
              role === "slsa"
                ? "bg-card text-foreground shadow-sm font-bold"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Shield className="w-3.5 h-3.5 text-primary" /> SLSA Supervisory
          </button>
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

          {/* VIEW 1: DLSA REMAND & FIRST PRODUCTION QUEUE */}
          {role === "dlsa" && (
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

          {/* VIEW 2: JAIL OPERATIONS VIEW */}
          {role === "jail" && (
            <div className="space-y-6">
              <div className="p-5 border border-primary/20 bg-primary/5 rounded-sm">
                <h2 className="font-bold font-serif text-base text-foreground">
                  Jail Administration & Custody Records Coordination
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Timely / near-real-time visibility into legal-assistance and advocate requirements where institutional data is connected.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-5 border border-border bg-card rounded-sm space-y-4">
                  <h3 className="text-sm font-bold font-serif uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <Clock className="w-4 h-4 text-primary" /> Undertrial Detention & Delay Exclusions
                  </h3>
                  <div className="space-y-3 text-xs">
                    {undertrials.map((c) => (
                      <div key={c.case_id} className="p-3 rounded bg-secondary/30 border border-border/60 flex justify-between items-center">
                        <div>
                          <span className="font-bold text-foreground">{c.name}</span> ({c.case_id})
                          <p className="text-muted-foreground text-[11px] mt-0.5">
                            Calendar Time: {c.custody_days}d | Attributable Delay Excluded: {c.excluded_delay_days || 0}d
                          </p>
                        </div>
                        <span className="text-xs font-mono font-bold text-primary">
                          {c.custody_days - (c.excluded_delay_days || 0)}d countable
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="p-5 border border-border bg-card rounded-sm space-y-4">
                  <h3 className="text-sm font-bold font-serif uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" /> Pending Remand / Chargesheet Records
                  </h3>
                  <div className="space-y-3 text-xs">
                    {cases
                      .filter((c) => (c.required_docs?.length || 0) > (c.present_docs?.length || 0))
                      .map((c) => (
                        <div key={c.case_id} className="p-3 rounded bg-amber-500/5 border border-amber-500/20 space-y-1.5">
                          <div className="flex justify-between">
                            <span className="font-bold text-foreground">{c.name} ({c.case_id})</span>
                            <span className="font-mono text-[10px] text-amber-600 uppercase font-bold">Document Block</span>
                          </div>
                          <p className="text-muted-foreground text-[11px]">
                            Missing from record:{" "}
                            <strong className="text-foreground">
                              {c.required_docs
                                ?.filter((d: string) => !c.present_docs?.includes(d))
                                .join(", ")
                                .toUpperCase()}
                            </strong>
                          </p>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* VIEW 3: DEFENCE COUNSEL / LEGAL AID ADVOCATE WORKSPACE */}
          {role === "advocate" && (
            <div className="space-y-6">
              <div className="p-5 border border-primary/20 bg-primary/5 rounded-sm">
                <h2 className="font-bold font-serif text-base text-foreground">
                  Legal Aid Defence Counsel Briefing Workspace
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Assigned cases, AI-grounded draft Section 479 petitions, evidence verification, and filing registry.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 border border-border rounded-sm bg-card overflow-hidden">
                  <div className="p-4 border-b border-border bg-secondary/40 font-bold font-serif text-xs uppercase tracking-wider text-muted-foreground">
                    Assigned Undertrial Matters
                  </div>
                  <div className="divide-y divide-border">
                    {undertrials.map((c) => (
                      <div key={c.case_id} className="p-4 flex items-center justify-between gap-4 hover:bg-secondary/20">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold font-serif text-sm text-foreground">{c.name}</span>
                            <span className="text-xs font-mono text-muted-foreground">{c.case_id}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {c.court_name} • DLSA File: {c.dlsa_reference_number}
                          </p>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <Link
                            to={`/accused/acc_${c.case_id.toLowerCase().replace("-", "_")}`}
                            className="px-2.5 py-1.5 bg-secondary hover:bg-muted text-foreground border border-border rounded-sm text-xs font-serif font-semibold flex items-center gap-1 transition-colors"
                            title="View Accused Dossier"
                          >
                            <UserCheck className="w-3.5 h-3.5" /> Profile
                          </Link>
                          <Link
                            to={`/cases/${c.case_id}`}
                            className="px-3 py-1.5 bg-primary text-primary-foreground rounded-sm text-xs font-serif font-semibold flex items-center gap-1"
                          >
                            Open Dossier <ChevronRight className="w-3.5 h-3.5" />
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                    <h3 className="text-xs font-mono font-bold uppercase text-muted-foreground">
                      Human Legal Gateway Rule
                    </h3>
                    <p className="text-xs text-foreground/80 leading-relaxed font-sans">
                      All draft petitions generated by Nyaya Mitra require explicit review and signature by the assigned advocate. The system enforces a mandatory human sign-off gate before marking any matter ready for filing.
                    </p>
                  </div>

                  <div className="p-5 border border-border bg-card rounded-sm space-y-3">
                    <h3 className="text-xs font-mono font-bold uppercase text-muted-foreground">
                      Appeals & Post-Release Coordination
                    </h3>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between border-b border-border/50 pb-1.5">
                        <span className="text-muted-foreground">Convicted Appeals:</span>
                        <span className="font-bold font-mono">{convicted.length}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Post-Release Records:</span>
                        <span className="font-bold font-mono">{postRelease.length}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* VIEW 4: SLSA SUPERVISORY MONITORING */}
          {role === "slsa" && (
            <div className="space-y-6">
              <div className="p-5 border border-primary/20 bg-primary/5 rounded-sm">
                <h2 className="font-bold font-serif text-base text-foreground">
                  State Legal Services Authority (SLSA) — Supervisory Overview
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Macro-level monitoring across districts, compliance tracking with Section 479 BNSS, and systemic delay prevention.
                </p>
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
