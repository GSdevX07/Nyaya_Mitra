import { useState, useEffect } from "react";
import { Search, Filter, Clock, ArrowLeft, ArrowUpRight, ShieldAlert, CheckCircle, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchCases, type BackendCaseSummary } from "@/lib/api";
type TimeframeWindow = "Today" | "7 days" | "30 days" | "90 days";

export function EligibilityRadar() {
  const [selectedTimeframe, setSelectedTimeframe] = useState<TimeframeWindow>("30 days");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | "OVERDUE" | "APPROACHING" | "DOCS_REQUIRED">("ALL");
  const [cases, setCases] = useState<BackendCaseSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      const data = await fetchCases();
      // Only show cases assigned to this lawyer
      setCases(data.filter((c: any) => c.case.assignment_status === "ASSIGNED"));
      setLoading(false);
    }
    load();
  }, []);

  // Map backend cases
  const caseList = cases.map((c) => ({
    id: c.case.case_id,
    prisonerName: c.case.name,
    offence: c.case.offense_sections.join(", "),
    custodyDays: c.case.custody_days,
    maxSentenceDays: c.case.max_sentence_days_for_offense,
    daysOverdue: c.days_overdue,
    isEligible: c.case.custody_days >= Math.floor(c.case.max_sentence_days_for_offense / 2),
    urgency: c.urgency_score > 200 ? "URGENT" : "MEDIUM",
    missingDocs: c.case.required_docs.filter((d) => !c.case.present_docs.includes(d)),
    healthFlag: c.case.urgency_flags.health_flag,
    age: c.case.urgency_flags.age,
    court: c.case.jail_location,
  }));

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

  // Calculate REAL stats
  const countApproaching = filteredCases.filter(c => {
    const daysUntil = (c.maxSentenceDays / 2) - c.custodyDays;
    return daysUntil > 0 && daysUntil <= thresholdWindow;
  }).length;
  const countDocsRequired = filteredCases.filter(c => c.missingDocs.length > 0).length;
  const countOverdue = filteredCases.filter(c => c.daysOverdue > 0).length;

  // Group cases for timeline
  const activeWindowCases = filteredCases.filter(c => {
    const daysUntil = (c.maxSentenceDays / 2) - c.custodyDays;
    return c.daysOverdue > 0 || c.missingDocs.length > 0 || (daysUntil > 0 && daysUntil <= thresholdWindow);
  });
  
  const futureCases = filteredCases.filter(c => !activeWindowCases.includes(c));

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10 animate-in fade-in duration-300">
      {/* Header */}
      <div className="space-y-6">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> Back to Command Center
        </Link>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-4xl font-semibold tracking-tight text-white uppercase">Eligibility Radar</h1>
            <p className="text-xl text-muted-foreground">Proactive monitoring for upcoming statutory thresholds.</p>
          </div>

          {/* Dynamic Timeframe Sort/Filter Buttons */}
          <div className="flex gap-2 bg-white/[0.03] p-1.5 rounded-xl border border-white/10">
            {(["Today", "7 days", "30 days", "90 days"] as TimeframeWindow[]).map((tf) => (
              <button
                key={tf}
                onClick={() => setSelectedTimeframe(tf)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-all ${
                  selectedTimeframe === tf
                    ? "bg-accent text-accent-foreground shadow-lg shadow-accent/20 font-semibold"
                    : "text-muted-foreground hover:text-white hover:bg-white/5"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Dynamic Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-md">
          <div className="text-2xl font-bold text-white mb-2 uppercase tracking-wide">NEXT {selectedTimeframe}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
            Active Monitoring Window
          </div>
        </div>
        <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-md">
          <div className="text-3xl font-bold text-accent mb-2">{countApproaching}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
            Approaching Threshold
          </div>
        </div>
        <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-md">
          <div className="text-3xl font-bold text-amber-500 mb-2">{countDocsRequired}</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
            Requiring Documentation
          </div>
        </div>
        <div className="p-6 rounded-2xl border border-white/10 bg-white/[0.02] backdrop-blur-md">
          <div className="text-3xl font-bold text-destructive mb-2">{countOverdue}</div>
          <div className="text-xs text-destructive/80 uppercase tracking-wider font-semibold">
            Overdue Actions
          </div>
        </div>
      </div>

      {/* Radar Timeline */}
      <div className="p-8 rounded-2xl border border-white/10 bg-black/40 space-y-8 relative overflow-hidden backdrop-blur-xl">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] mix-blend-overlay pointer-events-none" />

        {/* Timeline Search & Filter Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div className="flex items-center gap-2 text-white font-medium">
            <Clock className="w-4 h-4 text-accent" /> Timeline View ({selectedTimeframe})
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search cases..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent"
              />
            </div>

            <div className="flex items-center gap-1">
              <Filter className="w-4 h-4 text-muted-foreground shrink-0" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="bg-white/5 border border-white/10 text-white text-xs rounded-xl px-2.5 py-2 focus:outline-none focus:border-accent"
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
          <div className="p-12 text-center text-muted-foreground animate-pulse">
            Loading eligibility radar pipeline...
          </div>
        ) : (
          <div className="space-y-12">
            {/* THIS WEEK Section */}
            <div className="relative">
              <div className="absolute -left-4 top-0 bottom-0 w-px bg-accent/40" />
              <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-accent ring-4 ring-black" />

              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  Active Window <span className="text-xs font-normal text-muted-foreground">({activeWindowCases.length} cases)</span>
                </h3>
              </div>

              <div className="space-y-4 pl-4">
                {activeWindowCases.map((c) => (
                  <div
                    key={c.id}
                    className={`p-5 rounded-2xl border transition-all duration-300 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                      c.daysOverdue > 0
                        ? "border-destructive/30 bg-destructive/10 hover:border-destructive/60"
                        : c.missingDocs.length > 0
                        ? "border-amber-500/30 bg-amber-500/10 hover:border-amber-500/60"
                        : "border-white/10 bg-white/[0.03] hover:border-accent/50"
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="text-white font-mono font-bold text-sm">{c.id}</span>
                        {c.daysOverdue > 0 && (
                          <span className="px-2 py-0.5 bg-destructive/20 text-destructive text-[10px] font-bold uppercase tracking-wider rounded-md border border-destructive/30 flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3" /> Overdue by {c.daysOverdue} days
                          </span>
                        )}
                        {c.missingDocs.length > 0 && (
                          <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 text-[10px] font-bold uppercase tracking-wider rounded-md border border-amber-500/30 flex items-center gap-1">
                            <FileText className="w-3 h-3" /> Docs Required ({c.missingDocs.length})
                          </span>
                        )}
                        {c.isEligible && c.daysOverdue === 0 && (
                          <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-wider rounded-md border border-emerald-500/30 flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" /> Eligible
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-white/90 font-medium">
                        {c.prisonerName} • <span className="text-muted-foreground font-mono">{c.offence}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Custody: {c.custodyDays} days | Facility: {c.court}
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {/* Interactive Review Button - Navigates directly to Case Dossier */}
                      <Link
                        to={`/case/${c.id}`}
                        className="px-4 py-2 bg-accent text-accent-foreground font-semibold rounded-xl text-xs hover:opacity-90 transition-opacity flex items-center gap-1.5 shadow-md shadow-accent/20 shrink-0"
                      >
                        Review Case <ArrowUpRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                ))}

                {activeWindowCases.length === 0 && (
                  <div className="p-6 text-center text-sm text-muted-foreground bg-white/[0.01] rounded-xl border border-white/5">
                    No cases matching criteria for this week.
                  </div>
                )}
              </div>
            </div>

            {/* NEXT WEEK Section */}
            <div className="relative">
              <div className="absolute -left-4 top-0 bottom-0 w-px bg-white/10" />
              <div className="absolute -left-[19px] top-1 w-2 h-2 rounded-full bg-white/30 ring-4 ring-black" />

              <h3 className="text-lg font-bold text-white mb-6 uppercase tracking-wider flex items-center gap-2">
                Future / Safe <span className="text-xs font-normal text-muted-foreground">({futureCases.length} cases)</span>
              </h3>

              <div className="space-y-4 pl-4">
                {futureCases.map((c) => (
                  <div
                    key={c.id}
                    className="p-5 rounded-2xl border border-white/5 bg-white/[0.02] hover:border-white/20 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  >
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-white font-mono font-medium text-sm">{c.id}</span>
                        <span className="text-xs text-muted-foreground font-mono">Custody: {c.custodyDays} days</span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {c.prisonerName} • Approaching statutory threshold window ({selectedTimeframe})
                      </div>
                    </div>
                    <Link
                      to={`/case/${c.id}`}
                      className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-xl text-xs font-medium border border-white/10 transition-colors flex items-center gap-1 shrink-0"
                    >
                      Inspect <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </div>
                ))}

                {futureCases.length === 0 && (
                  <div className="p-6 text-center text-sm text-muted-foreground bg-white/[0.01] rounded-xl border border-white/5">
                    No future cases scheduled.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
