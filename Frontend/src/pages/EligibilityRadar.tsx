import { useState, useEffect } from "react";
import {
  Search,
  Filter,
  Clock,
  ArrowLeft,
  ArrowUpRight,
  ShieldAlert,
  CheckCircle,
  FileText,
  Loader2,
  Scale,
  AlertTriangle,
  HelpCircle,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import { fetchCases, type BackendCaseSummary, type RuleExplanationData } from "@/lib/api";
import { RuleExplanationModal } from "@/components/RuleExplanationModal";

type TimeframeWindow = "Today" | "7 days" | "30 days" | "90 days";

export function EligibilityRadar() {
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeframeWindow>("30 days");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "OVERDUE" | "APPROACHING" | "DOCS_REQUIRED">("ALL");
  const [cases, setCases] = useState<BackendCaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedExplanation, setSelectedExplanation] = useState<{
    explanation?: RuleExplanationData;
    caseId?: string;
    accusedName?: string;
  } | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const data = await fetchCases();
      setCases(data);
      setLoading(false);
    }
    load();
  }, []);

  // Map backend cases consuming the backend deterministic legal rules engine (no browser-side math duplication)
  const caseList = cases.map((c) => {
    const eligibility = c.eligibility;
    const isEligible = eligibility?.is_eligible ?? (c.days_overdue > 0);
    const thresholdDays = eligibility?.threshold_days ?? 0;
    const countableCustody = eligibility?.countable_custody_days ?? c.case.custody_days;
    const thresholdFraction = eligibility?.statutory_threshold_fraction ?? (c.case.urgency_flags?.repeat_offender ? "1/2" : "1/3");
    const machineStatus = eligibility?.machine_status ?? (isEligible ? "THRESHOLD_REACHED" : "THRESHOLD_NOT_REACHED");
    const explanation = eligibility?.explanation;

    return {
      id: c.case.case_id,
      prisonerName: c.case.name,
      offence: c.case.offense_sections.join(", "),
      custodyDays: c.case.custody_days,
      countableCustodyDays: countableCustody,
      maxSentenceDays: c.case.max_sentence_days_for_offense,
      thresholdDays,
      thresholdFraction,
      daysOverdue: c.days_overdue,
      isEligible,
      machineStatus,
      explanation,
      urgency: c.urgency_score > 200 ? "URGENT" : "MEDIUM",
      missingDocs: c.case.required_docs.filter((d: string) => !c.case.present_docs.includes(d)),
      healthFlag: c.case.urgency_flags.health_flag,
      age: c.case.urgency_flags.age,
      court: c.case.jail_location,
    };
  });

  // Filter based on search and status filter
  const filteredCases = caseList.filter((item) => {
    const matchesSearch =
      item.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.prisonerName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.offence.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (statusFilter === "OVERDUE") return item.daysOverdue > 0;
    if (statusFilter === "APPROACHING") return item.daysOverdue === 0 && item.isEligible;
    if (statusFilter === "DOCS_REQUIRED") return item.missingDocs.length > 0;

    return true;
  });

  const thresholdWindow = 
    selectedTimeframe === "Today" ? 1
    : selectedTimeframe === "7 days" ? 7
    : selectedTimeframe === "30 days" ? 30
    : 90;

  // Stats using authoritative backend values
  const countApproaching = filteredCases.filter(c => {
    const daysUntil = c.thresholdDays - c.countableCustodyDays;
    return !c.isEligible && daysUntil > 0 && daysUntil <= thresholdWindow;
  }).length;
  const countDocsRequired = filteredCases.filter(c => c.missingDocs.length > 0).length;
  const countOverdue = filteredCases.filter(c => c.daysOverdue > 0).length;

  // Group cases for timeline
  const activeWindowCases = filteredCases.filter(c => {
    const daysUntil = c.thresholdDays - c.countableCustodyDays;
    return c.daysOverdue > 0 || c.isEligible || c.missingDocs.length > 0 || (daysUntil > 0 && daysUntil <= thresholdWindow);
  });
  
  const futureCases = filteredCases.filter(c => !activeWindowCases.includes(c));

  const renderStatusPill = (c: typeof caseList[0]) => {
    if (c.daysOverdue > 0) {
      return (
        <span className="px-2 py-0.5 bg-destructive/20 text-destructive text-[10px] font-bold uppercase tracking-wider rounded-md border border-destructive/30 flex items-center gap-1">
          <ShieldAlert className="w-3 h-3" /> Overdue ({c.daysOverdue}d)
        </span>
      );
    }
    if (c.machineStatus === "THRESHOLD_REACHED" || c.isEligible) {
      return (
        <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-wider rounded-md border border-emerald-500/30 flex items-center gap-1">
          <CheckCircle className="w-3 h-3" /> Threshold Reached
        </span>
      );
    }
    if (c.machineStatus === "EXCLUDED") {
      return (
        <span className="px-2 py-0.5 bg-destructive/20 text-destructive text-[10px] font-bold uppercase tracking-wider rounded-md border border-destructive/30 flex items-center gap-1">
          <XCircle className="w-3 h-3" /> Statutory Exclusion
        </span>
      );
    }
    if (c.machineStatus === "POTENTIALLY_APPLICABLE") {
      return (
        <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-[10px] font-bold uppercase tracking-wider rounded-md border border-amber-500/30 flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" /> Approaching Threshold
        </span>
      );
    }
    if (c.machineStatus === "INSUFFICIENT_DATA") {
      return (
        <span className="px-2 py-0.5 bg-rose-500/20 text-rose-400 text-[10px] font-bold uppercase tracking-wider rounded-md border border-rose-500/30 flex items-center gap-1">
          <HelpCircle className="w-3 h-3" /> Missing Data
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-bold uppercase tracking-wider rounded-md border border-blue-500/30 flex items-center gap-1">
        <Clock className="w-3 h-3" /> Safe ({c.thresholdDays - c.countableCustodyDays}d remaining)
      </span>
    );
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10 animate-in fade-in duration-300">
      {/* Header */}
      <div className="space-y-6">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> Back to Command Center
        </Link>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-4xl font-semibold tracking-tight text-primary uppercase">Eligibility Radar</h1>
            <p className="text-xl text-muted-foreground">Deterministic statutory threshold tracking & audit explanation.</p>
          </div>

          {/* Dynamic Timeframe Sort/Filter Buttons */}
          <div className="flex gap-2 bg-card/70 p-1.5 rounded border border-border">
            {(["Today", "7 days", "30 days", "90 days"] as TimeframeWindow[]).map((tf) => (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                className={`px-4 py-2 text-sm font-medium rounded-sm transition-all ${
                  selectedTimeframe === tf
                    ? "bg-accent text-accent-foreground shadow-lg shadow-accent/20 font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Metrics Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="p-5 rounded bg-card border border-border flex items-center gap-4">
          <div className="p-3 rounded-lg bg-destructive/10 text-destructive border border-destructive/20">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground font-mono">{countOverdue}</div>
            <div className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Statutory Overdue Cases</div>
          </div>
        </div>
        <div className="p-5 rounded bg-card border border-border flex items-center gap-4">
          <div className="p-3 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground font-mono">{countApproaching}</div>
            <div className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Approaching Window ({selectedTimeframe})</div>
          </div>
        </div>
        <div className="p-5 rounded bg-card border border-border flex items-center gap-4">
          <div className="p-3 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-foreground font-mono">{countDocsRequired}</div>
            <div className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Mandatory Document Bottlenecks</div>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-center bg-card/40 p-4 rounded border border-border">
          <div className="relative w-full sm:w-96">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by case ID, prisoner name, or offense..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-secondary/50 border border-border rounded pl-9 pr-4 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-accent"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-muted-foreground" />
              <select
                value={statusFilter}
                onChange={(e: any) => setStatusFilter(e.target.value)}
                className="bg-secondary/50 border border-border text-primary text-xs rounded px-2.5 py-2 focus:outline-none focus:border-accent"
              >
                <option value="ALL" className="bg-background">All Statuses</option>
                <option value="OVERDUE" className="bg-background">Overdue Only</option>
                <option value="APPROACHING" className="bg-background">Approaching Threshold</option>
                <option value="DOCS_REQUIRED" className="bg-background">Missing Docs</option>
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="p-16 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
            <span className="text-sm font-mono">Evaluating deterministic legal rules across custody registry...</span>
          </div>
        ) : (
          <div className="space-y-12">
            {/* Active Window */}
            <div className="relative">
              <div className="absolute -left-4 top-0 bottom-0 w-px bg-border" />
              <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-sm bg-accent ring-4 ring-background" />

              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-primary uppercase tracking-wider flex items-center gap-2">
                  Active Window <span className="text-xs font-normal text-muted-foreground">({activeWindowCases.length} cases)</span>
                </h3>
              </div>

              <div className="space-y-4 pl-4">
                {activeWindowCases.map((c) => (
                  <div
                    key={c.id}
                    className={`p-5 rounded border transition-all duration-300 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                      c.daysOverdue > 0
                        ? "border-destructive/30 bg-destructive/10 hover:border-destructive"
                        : c.missingDocs.length > 0
                        ? "border-border bg-secondary/50 hover:border-amber-500"
                        : "border-border bg-card hover:border-accent"
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="text-primary font-mono font-bold text-sm">{c.id}</span>
                        {renderStatusPill(c)}
                        {c.missingDocs.length > 0 && (
                          <span className="px-2 py-0.5 bg-muted-foreground/20 text-muted-foreground text-[10px] font-bold uppercase tracking-wider rounded-md border border-border flex items-center gap-1">
                            <FileText className="w-3 h-3" /> Docs Required ({c.missingDocs.length})
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-primary font-medium">
                        {c.prisonerName} • <span className="text-muted-foreground font-mono">{c.offence}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Countable Custody: <strong className="text-foreground">{c.countableCustodyDays}d</strong> / {c.thresholdDays}d threshold ({c.thresholdFraction}) | Facility: {c.court}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {c.explanation && (
                        <button
                          onClick={() => setSelectedExplanation({
                            explanation: c.explanation,
                            caseId: c.id,
                            accusedName: c.prisonerName,
                          })}
                          className="px-3 py-2 bg-secondary text-secondary-foreground font-medium rounded text-xs hover:bg-secondary/80 transition-colors flex items-center gap-1.5 border border-border shrink-0"
                          title="View complete deterministic rule calculation, provenance, and legal explanation"
                        >
                          <Scale className="w-3.5 h-3.5 text-primary" /> Rule & Explanation
                        </button>
                      )}
                      <Link
                        to={`/cases/${c.id}`}
                        className="px-4 py-2 bg-accent text-accent-foreground font-semibold rounded text-xs hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-md shadow-accent/20 shrink-0"
                      >
                        Review Case <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                ))}

                {activeWindowCases.length === 0 && (
                  <div className="p-6 text-center text-sm text-muted-foreground bg-card shadow-sm rounded border border-border">
                    No cases matching criteria for this window.
                  </div>
                )}
              </div>
            </div>

            {/* Safe / Future Cases */}
            <div className="relative">
              <div className="absolute -left-4 top-0 bottom-0 w-px bg-secondary" />
              <div className="absolute -left-[19px] top-1 w-2 h-2 rounded-sm bg-white/30 ring-4 ring-background" />

              <h3 className="text-lg font-bold text-primary mb-6 uppercase tracking-wider flex items-center gap-2">
                Future / Safe Window <span className="text-xs font-normal text-muted-foreground">({futureCases.length} cases)</span>
              </h3>

              <div className="space-y-4 pl-4">
                {futureCases.map((c) => (
                  <div
                    key={c.id}
                    className="p-5 rounded border border-border bg-card shadow-sm hover:border-border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-primary font-mono font-medium text-sm">{c.id}</span>
                        {renderStatusPill(c)}
                        <span className="text-xs text-muted-foreground font-mono">Countable: {c.countableCustodyDays}d / {c.thresholdDays}d</span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {c.prisonerName} • {c.offence}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {c.explanation && (
                        <button
                          onClick={() => setSelectedExplanation({
                            explanation: c.explanation,
                            caseId: c.id,
                            accusedName: c.prisonerName,
                          })}
                          className="px-3 py-2 bg-secondary text-secondary-foreground font-medium rounded text-xs hover:bg-secondary/80 transition-colors flex items-center gap-1.5 border border-border shrink-0"
                        >
                          <Scale className="w-3.5 h-3.5 text-primary" /> Rule & Explanation
                        </button>
                      )}
                      <Link
                        to={`/cases/${c.id}`}
                        className="px-4 py-2 bg-secondary/50 hover:bg-white/20 text-primary rounded text-xs font-medium border border-border transition-colors flex items-center gap-1 shrink-0"
                      >
                        Inspect <ArrowUpRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                ))}

                {futureCases.length === 0 && (
                  <div className="p-6 text-center text-sm text-muted-foreground bg-card shadow-sm rounded border border-border">
                    No future cases scheduled.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Structured Legal Rule Explanation Modal */}
      {selectedExplanation && (
        <RuleExplanationModal
          isOpen={true}
          onClose={() => setSelectedExplanation(null)}
          explanation={selectedExplanation.explanation}
          caseId={selectedExplanation.caseId}
          accusedName={selectedExplanation.accusedName}
        />
      )}
    </div>
  );
}
