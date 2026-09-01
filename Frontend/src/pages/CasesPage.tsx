import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  ChevronRight,
  Loader2,
  RefreshCw,
  HeartPulse,
  UserCheck,
} from "lucide-react";
import { fetchCases, type CaseRecord } from "@/lib/api";

type CategoryFilter = "ALL" | "UNDERTRIAL" | "CONVICTED" | "POST_RELEASE";
type LegalCodeFilter = "ALL" | "BNS_2023" | "IPC_1860";

export function CasesPage() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("ALL");
  const [legalCodeFilter, setLegalCodeFilter] = useState<LegalCodeFilter>("ALL");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchCases();
      const extracted = (data || []).map((item: any) => (item.case || item) as CaseRecord);
      setCases(extracted);
    } catch (err) {
      console.error("Failed to load cases:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const filteredCases = cases.filter((c) => {
    // Search Filter
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      c.name?.toLowerCase().includes(query) ||
      c.case_id?.toLowerCase().includes(query) ||
      c.court_name?.toLowerCase().includes(query) ||
      c.fir_number?.toLowerCase().includes(query) ||
      c.offense_sections?.some((sec: string) => sec.toLowerCase().includes(query));

    if (!matchesSearch) return false;

    // Category Filter
    if (categoryFilter === "POST_RELEASE") {
      if (c.status !== "POST_RELEASE_PRESERVED" && c.status !== "RELEASED") return false;
    } else if (categoryFilter === "CONVICTED") {
      if (c.prisoner_category !== "CONVICTED") return false;
    } else if (categoryFilter === "UNDERTRIAL") {
      if (c.prisoner_category !== "UNDERTRIAL" || c.status === "POST_RELEASE_PRESERVED") return false;
    }

    // Legal Code Filter
    if (legalCodeFilter !== "ALL") {
      if (c.legal_code !== legalCodeFilter) return false;
    }

    return true;
  });

  const countUndertrial = cases.filter(
    (c) => (!c.prisoner_category || c.prisoner_category === "UNDERTRIAL") && c.status !== "POST_RELEASE_PRESERVED"
  ).length;
  const countConvicted = cases.filter((c) => c.prisoner_category === "CONVICTED").length;
  const countPostRelease = cases.filter(
    (c) => c.status === "POST_RELEASE_PRESERVED" || c.status === "RELEASED"
  ).length;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Master Registry
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded font-mono bg-primary/10 text-primary border border-primary/20">
              {cases.length} Total Matters
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold font-serif text-foreground mt-1">
            Accused Case Roster
          </h1>
          <p className="text-xs md:text-sm text-muted-foreground mt-1">
            Comprehensive directory of undertrials, convicted appeals, and post-release support records.
          </p>
        </div>

        <button
          onClick={loadData}
          className="px-3.5 py-2 border border-border rounded-sm bg-card hover:bg-secondary text-xs font-semibold flex items-center gap-2 self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Roster
        </button>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-3">
        <button
          onClick={() => setCategoryFilter("ALL")}
          className={`px-3.5 py-1.5 rounded-sm text-xs font-serif font-semibold transition-all ${
            categoryFilter === "ALL"
              ? "bg-primary text-primary-foreground font-bold shadow-sm"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          All Categories ({cases.length})
        </button>
        <button
          onClick={() => setCategoryFilter("UNDERTRIAL")}
          className={`px-3.5 py-1.5 rounded-sm text-xs font-serif font-semibold transition-all ${
            categoryFilter === "UNDERTRIAL"
              ? "bg-primary text-primary-foreground font-bold shadow-sm"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          Undertrials ({countUndertrial})
        </button>
        <button
          onClick={() => setCategoryFilter("CONVICTED")}
          className={`px-3.5 py-1.5 rounded-sm text-xs font-serif font-semibold transition-all ${
            categoryFilter === "CONVICTED"
              ? "bg-primary text-primary-foreground font-bold shadow-sm"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          Convicted Appeals ({countConvicted})
        </button>
        <button
          onClick={() => setCategoryFilter("POST_RELEASE")}
          className={`px-3.5 py-1.5 rounded-sm text-xs font-serif font-semibold transition-all ${
            categoryFilter === "POST_RELEASE"
              ? "bg-primary text-primary-foreground font-bold shadow-sm"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          Post-Release Records ({countPostRelease})
        </button>
      </div>

      {/* Search Bar & Legal Code Badges */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by accused name, case ID, FIR, court, or section..."
            className="w-full pl-9 pr-4 py-2 bg-card border border-border rounded-sm text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary font-sans"
          />
        </div>

        {/* Legal Code Filter Dropdown */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-muted-foreground">Legal Code:</span>
          <select
            value={legalCodeFilter}
            onChange={(e) => setLegalCodeFilter(e.target.value as LegalCodeFilter)}
            className="bg-card border border-border text-foreground text-xs rounded-sm px-3 py-2 font-mono focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="ALL">All Legal Codes</option>
            <option value="BNS_2023">Bharatiya Nyaya Sanhita, 2023</option>
            <option value="IPC_1860">Indian Penal Code, 1860 (Historical)</option>
          </select>
        </div>
      </div>

      {/* Main Cases Grid */}
      {loading ? (
        <div className="p-12 flex flex-col items-center justify-center min-h-[40vh] gap-3">
          <Loader2 className="w-6 h-6 text-primary animate-spin" />
          <span className="text-xs font-mono text-muted-foreground">
            Loading canonical case registry…
          </span>
        </div>
      ) : filteredCases.length === 0 ? (
        <div className="p-12 border border-dashed border-border rounded-sm text-center space-y-2">
          <p className="text-sm font-semibold font-serif text-foreground">No case records match your query.</p>
          <p className="text-xs text-muted-foreground font-mono">
            Adjust search keywords or clear the category and legal-code filters.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredCases.map((c) => {
            const isConvicted = c.prisoner_category === "CONVICTED";
            const isPostRelease = c.status === "POST_RELEASE_PRESERVED" || c.status === "RELEASED";
            const isReady = c.status === "APPROVED_READY_FOR_FILING";
            const isFiled = c.status === "FILED";

            return (
              <div
                key={c.case_id}
                className="p-5 border border-border bg-card rounded-sm shadow-sm hover:border-primary/50 transition-all flex flex-col justify-between space-y-4"
              >
                <div className="space-y-3">
                  {/* Top Badges */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                        {c.case_id}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-secondary border border-border text-foreground font-semibold">
                        {c.legal_code}
                      </span>
                    </div>

                    <span
                      className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                        isFiled
                          ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                          : isReady
                          ? "bg-blue-500/10 text-blue-600 border-blue-500/30"
                          : isPostRelease
                          ? "bg-purple-500/10 text-purple-600 border-purple-500/30"
                          : "bg-secondary text-muted-foreground border-border"
                      }`}
                    >
                      {c.status?.replace(/_/g, " ")}
                    </span>
                  </div>

                  {/* Accused Name & Details */}
                  <div>
                    <h3 className="font-bold font-serif text-lg text-foreground hover:text-primary transition-colors">
                      {c.name}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {c.court_name} • FIR: {c.fir_number}
                    </p>
                  </div>

                  {/* Offences & Detention Time */}
                  <div className="space-y-1.5 text-xs text-foreground/80 border-t border-border/60 pt-2.5">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Offences Charged:</span>
                      <span className="font-bold text-foreground">{c.offense_sections?.join(", ")}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Detention in Custody:</span>
                      <span className="font-mono font-bold text-foreground">
                        {c.custody_days} days
                        {c.excluded_delay_days ? ` (${c.excluded_delay_days}d excluded)` : ""}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Facility / Location:</span>
                      <span className="text-foreground">{c.jail_location}</span>
                    </div>
                  </div>

                  {/* Urgency Alert Badges */}
                  {c.urgency_flags && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      {c.urgency_flags.health_flag && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-500/10 text-red-600 border border-red-500/20 flex items-center gap-1">
                          <HeartPulse className="w-3 h-3" /> Medical Alert
                        </span>
                      )}
                      {c.urgency_flags.age >= 60 && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-600 border border-amber-500/20">
                          Senior ({c.urgency_flags.age} yrs)
                        </span>
                      )}
                      {isConvicted && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-600 border border-indigo-500/20">
                          Convicted Appeal
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Card Action Link */}
                <div className="border-t border-border pt-3 flex items-center justify-between gap-2 flex-wrap">
                  <span className="text-[11px] font-mono text-muted-foreground">
                    Category: <strong>{c.prisoner_category || "UNDERTRIAL"}</strong>
                  </span>
                  <div className="flex items-center gap-1.5">
                    <Link
                      to={`/accused/acc_${c.case_id.toLowerCase().replace("-", "_")}`}
                      className="px-2.5 py-1.5 bg-secondary hover:bg-muted text-foreground border border-border rounded-sm text-xs font-serif font-semibold flex items-center gap-1 transition-colors"
                      title="View Accused Dossier"
                    >
                      <UserCheck className="w-3.5 h-3.5" /> Profile
                    </Link>
                    <Link
                      to={`/case/${c.case_id}`}
                      className="px-3 py-1.5 bg-primary text-primary-foreground rounded-sm text-xs font-serif font-semibold hover:opacity-90 flex items-center gap-1 transition-opacity"
                    >
                      View Dossier <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
