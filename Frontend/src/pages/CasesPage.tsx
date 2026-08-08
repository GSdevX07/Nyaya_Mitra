import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Search, Filter, ShieldAlert, ArrowUpRight, CheckCircle, Clock, AlertCircle, RefreshCw, WifiOff } from "lucide-react";
import { fetchCases, type BackendCaseSummary } from "@/lib/api";

export function CasesPage() {
  const [cases, setCases] = useState<BackendCaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"ALL" | "ELIGIBLE" | "MEDICAL" | "MISSING">("ALL");

  const loadData = async () => {
    setLoading(true);
    setBackendError(false);
    try {
      const data = await fetchCases();
      if (data.length === 0) throw new Error("Empty");
      setCases(data);
    } catch {
      setBackendError(true);
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const displayList = cases;

  const filtered = displayList.filter(item => {
    const c = item.case;
    const matchesSearch = 
      c.case_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.offense_sections.some(s => s.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (filterType === "ELIGIBLE") {
      // Use backend days_overdue as the canonical eligibility signal
      return item.days_overdue > 0 || (item.urgency_score > 0 && item.days_overdue >= 0);
    }
    if (filterType === "MEDICAL") {
      return c.urgency_flags.health_flag || c.urgency_flags.age >= 60;
    }
    if (filterType === "MISSING") {
      return c.required_docs.some(d => !c.present_docs.includes(d));
    }

    return true;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Live Case Registry
            </span>
            <span className="text-xs text-muted-foreground font-mono">Synced with FastAPI Backend</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Undertrial Cases Directory</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time monitoring of Section 479 BNSS eligibility, medical priorities, and legal document completeness.
          </p>
        </div>

        <button
          onClick={loadData}
          className="self-start md:self-auto px-4 py-2 bg-white/5 border border-white/10 text-white hover:bg-white/10 rounded-xl text-sm font-medium transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Refresh Registry
        </button>
      </div>

      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Search */}
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Filter cases by ID, name, IPC section..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/[0.03] border border-white/10 rounded-xl text-sm text-white placeholder:text-muted-foreground focus:outline-none focus:border-accent transition-colors"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto no-scrollbar">
          <Filter className="w-4 h-4 text-muted-foreground shrink-0 hidden sm:inline" />
          {[
            { id: "ALL", label: "All Cases" },
            { id: "ELIGIBLE", label: "BNSS 479 Eligible" },
            { id: "MEDICAL", label: "Medical & Senior" },
            { id: "MISSING", label: "Missing Docs" },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id as any)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all shrink-0 ${
                filterType === tab.id
                  ? "bg-accent text-accent-foreground shadow-lg shadow-accent/20"
                  : "bg-white/5 text-muted-foreground hover:bg-white/10 hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Cases Grid */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Fetching cases from Nyaya Mitra legal pipeline...
        </div>
      ) : backendError ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-6 text-center">
          <WifiOff className="w-12 h-12 text-muted-foreground" />
          <div>
            <h2 className="text-lg font-semibold text-white mb-2">Backend Connection Lost</h2>
            <p className="text-sm text-muted-foreground">Live case data unavailable. Ensure the FastAPI server is running on localhost:8000.</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-accent text-accent-foreground rounded-xl text-sm font-medium flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Retry Connection
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map(item => {
            const c = item.case;
            // Use backend days_overdue as canonical eligibility signal (comes from EligibilityAgent)
            const isEligible = item.days_overdue > 0;
            const isRepeat = c.urgency_flags.repeat_offender;
            const thresholdLabel = isRepeat ? "1/2 Threshold" : "1/3 Threshold";
            const thresholdDays = isRepeat
              ? Math.ceil(c.max_sentence_days_for_offense / 2)
              : Math.ceil(c.max_sentence_days_for_offense / 3);
            const missingDocs = c.required_docs.filter(d => !c.present_docs.includes(d));

            return (
              <div
                key={c.case_id}
                className="group relative bg-white/[0.02] border border-white/10 hover:border-accent/40 rounded-2xl p-6 transition-all duration-300 backdrop-blur-md flex flex-col justify-between hover:shadow-xl hover:shadow-accent/5"
              >
                <div className="space-y-4">
                  {/* Top Bar */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="font-mono text-xs font-semibold text-accent tracking-wider">
                        {c.case_id}
                      </span>
                      <h3 className="text-base font-semibold text-white group-hover:text-accent transition-colors">
                        {c.name}
                      </h3>
                    </div>
                    {isEligible ? (
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Eligible
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-white/5 text-muted-foreground border border-white/10 flex items-center gap-1">
                        <Clock className="w-3 h-3" /> In Progress
                      </span>
                    )}
                  </div>

                  {/* Offense & Detention Badges */}
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="px-2 py-0.5 rounded bg-white/5 text-white/80 border border-white/5 font-mono">
                      {c.offense_sections.join(", ")}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-white/5 text-muted-foreground border border-white/5">
                      Age: {c.urgency_flags.age}
                    </span>
                    {c.urgency_flags.health_flag && (
                      <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                        <ShieldAlert className="w-3 h-3" /> Medical Flag
                      </span>
                    )}
                  </div>

                  {/* Sentence Threshold Progress */}
                  <div className="space-y-1.5 pt-2">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Custody: {c.custody_days} days</span>
                      <span>{thresholdLabel}: {thresholdDays} days</span>
                    </div>
                    <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          isEligible ? "bg-emerald-500" : "bg-accent"
                        }`}
                        style={{
                          width: `${Math.min(100, (c.custody_days / thresholdDays) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* Document Warning */}
                  {missingDocs.length > 0 && (
                    <div className="p-2.5 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>Missing: {missingDocs.map(d => d.replace("_", " ")).join(", ")}</span>
                    </div>
                  )}
                </div>

                {/* Footer link */}
                <div className="pt-6 mt-4 border-t border-white/5 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground truncate max-w-[180px]">
                    {c.jail_location}
                  </span>
                  <Link
                    to={`/case/${c.case_id}`}
                    className="text-xs font-semibold text-white group-hover:text-accent flex items-center gap-1 transition-colors"
                  >
                    Analyze Case <ArrowUpRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
