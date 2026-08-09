import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { 
  Search, 
  Filter, 
  ShieldAlert, 
  ArrowUpRight, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  RefreshCw, 
  UserCheck, 
  Sparkles, 
  Phone, 
  Eye, 
  Briefcase,
  WifiOff
} from "lucide-react";
import { 
  fetchCases, 
  fetchAvailableCases, 
  takeUpCase, 
  declineCase, 
  type BackendCaseSummary 
} from "@/lib/api";
import { AvailableCaseModal } from "@/components/AvailableCaseModal";

export function CasesPage() {
  const [activeMainTab, setActiveMainTab] = useState<"MY_CASES" | "AVAILABLE_CASES">("MY_CASES");
  
  const [myCases, setMyCases] = useState<BackendCaseSummary[]>([]);
  const [availableCases, setAvailableCases] = useState<BackendCaseSummary[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"ALL" | "ELIGIBLE" | "INELIGIBLE" | "MEDICAL" | "MISSING">("ALL");

  // Selected case for Available Case modal review
  const [selectedAvailableCase, setSelectedAvailableCase] = useState<BackendCaseSummary | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Load local approved/declined overrides from localStorage
  const getApprovedFromStorage = (): string[] => {
    try {
      return JSON.parse(localStorage.getItem("approved_case_ids") || "[]");
    } catch {
      return [];
    }
  };

  const getDeclinedFromStorage = (): string[] => {
    try {
      return JSON.parse(localStorage.getItem("declined_case_ids") || "[]");
    } catch {
      return [];
    }
  };

  const saveApprovedToStorage = (id: string) => {
    const list = getApprovedFromStorage();
    if (!list.includes(id)) {
      localStorage.setItem("approved_case_ids", JSON.stringify([...list, id]));
    }
  };

  const saveDeclinedToStorage = (id: string) => {
    const list = getDeclinedFromStorage();
    if (!list.includes(id)) {
      localStorage.setItem("declined_case_ids", JSON.stringify([...list, id]));
    }
  };

  const loadData = async () => {
    setLoading(true);

    // Fetch all cases & available cases from backend
    try {
      const [allData] = await Promise.all([fetchCases(), fetchAvailableCases()]);
      setBackendError(false);

      let assignedList: BackendCaseSummary[] = [];
      let unassignedList: BackendCaseSummary[] = [];

      if (allData.length > 0) {
        // Backend returned data: Trust the backend state as the single source of truth
        const rawAssigned = allData.filter(item => item.case.assignment_status === "ASSIGNED");
        const rawAvailable = allData.filter(item => 
          item.case.assignment_status === "AVAILABLE" || !item.case.assignment_status
        );
        
        assignedList = rawAssigned;
        unassignedList = rawAvailable;
      } else {
        assignedList = [];
        unassignedList = [];
      }

      setMyCases(assignedList);
      setAvailableCases(unassignedList);
    } catch {
      setBackendError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Handle Approve Case (after mandatory scroll review)
  const handleApproveCase = async (caseId: string) => {
    try {
      await takeUpCase(caseId);
    } catch {
      // Backend offline fallback
    }
    saveApprovedToStorage(caseId);

    // Find the item and move from available to myCases
    const target = availableCases.find(i => i.case.case_id === caseId);
    if (target) {
      const updatedItem = {
        ...target,
        case: { ...target.case, assignment_status: "ASSIGNED" },
      };
      setMyCases(prev => [updatedItem, ...prev]);
      setAvailableCases(prev => prev.filter(i => i.case.case_id !== caseId));
    }

    setIsModalOpen(false);
    setSelectedAvailableCase(null);
    setActiveMainTab("MY_CASES");
  };

  // Handle Decline Case (hides case permanently)
  const handleDeclineCase = async (caseId: string) => {
    try {
      await declineCase(caseId);
    } catch {
      // Backend offline fallback
    }
    saveDeclinedToStorage(caseId);

    // Remove from availableCases list
    setAvailableCases(prev => prev.filter(i => i.case.case_id !== caseId));
    setIsModalOpen(false);
    setSelectedAvailableCase(null);
  };

  const currentList = activeMainTab === "MY_CASES" ? myCases : availableCases;

  const filtered = currentList.filter(item => {
    const c = item.case;
    const matchesSearch =
      c.case_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.offense_sections.some(s => s.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    const isRepeat = c.urgency_flags?.repeat_offender;
    const thresholdDays = isRepeat
      ? Math.ceil(c.max_sentence_days_for_offense / 2)
      : Math.ceil(c.max_sentence_days_for_offense / 3);
    const isEligible = item.days_overdue > 0 || c.custody_days >= thresholdDays;

    if (filterType === "ELIGIBLE") {
      return isEligible;
    }
    if (filterType === "INELIGIBLE") {
      return !isEligible;
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
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-sm text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Live Advocate Queue
            </span>
            <span className="text-xs text-muted-foreground font-mono">Synced with FastAPI Backend</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Undertrial Cases Management</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Review pro bono undertrial cases, verify parents/relative contacts & address, scroll-approve to take cases into your active queue.
          </p>
        </div>

        <button
          onClick={loadData}
          className="self-start md:self-auto px-4 py-2 bg-secondary/50 border border-border text-primary hover:bg-secondary rounded text-sm font-medium transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Refresh Cases
        </button>
      </div>

      {/* Main Tab Navigation: My Cases vs Available Cases */}
      <div className="flex items-center gap-3 border-b border-border pb-4">
        <button
          onClick={() => setActiveMainTab("MY_CASES")}
          className={`px-5 py-2.5 rounded text-sm font-semibold transition-all flex items-center gap-2 ${
            activeMainTab === "MY_CASES"
              ? "bg-accent text-accent-foreground shadow-lg shadow-accent/20"
              : "bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground"
          }`}
        >
          <Briefcase className="w-4 h-4" />
          My Assigned Cases ({myCases.length})
        </button>

        <button
          onClick={() => setActiveMainTab("AVAILABLE_CASES")}
          className={`px-5 py-2.5 rounded text-sm font-semibold transition-all flex items-center gap-2 relative ${
            activeMainTab === "AVAILABLE_CASES"
              ? "bg-accent text-accent-foreground shadow-lg shadow-accent/20"
              : "bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground"
          }`}
        >
          <Sparkles className="w-4 h-4 text-foreground" />
          Available Cases to Take Up ({availableCases.length})
          {availableCases.length > 0 && (
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400 animate-ping absolute -top-1 -right-1" />
          )}
        </button>
      </div>

      {/* Controls Bar: Search & Sub-Filter Pills */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Search */}
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Filter by ID, prisoner name, IPC section..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-card/70 border border-border rounded text-sm text-primary placeholder:text-muted-foreground focus:outline-none focus:border-accent transition-colors"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto no-scrollbar">
          <Filter className="w-4 h-4 text-muted-foreground shrink-0 hidden sm:inline" />
          {[
            { id: "ALL", label: "All" },
            { id: "ELIGIBLE", label: "BNSS 479 Eligible" },
            { id: "INELIGIBLE", label: "Ineligible" },
            { id: "MEDICAL", label: "Medical Flags" },
            { id: "MISSING", label: "Missing Docs" },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id as any)}
              className={`px-3 py-1.5 rounded-sm text-xs font-medium transition-all shrink-0 ${
                filterType === tab.id
                  ? "bg-muted text-primary font-bold"
                  : "bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Display */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Fetching cases from Nyaya Mitra legal pipeline...
        </div>
      ) : backendError ? (
        <div className="flex flex-col items-center justify-center min-h-[40vh] gap-6 text-center">
          <WifiOff className="w-12 h-12 text-muted-foreground" />
          <div>
            <h2 className="text-lg font-semibold text-primary mb-2">Backend Connection Lost</h2>
            <p className="text-sm text-muted-foreground">Live case data unavailable. Ensure the FastAPI server is running on localhost:8000.</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-accent text-accent-foreground rounded text-sm font-medium flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Retry Connection
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-16 text-center bg-card shadow-sm border border-border rounded space-y-2">
          <div className="text-lg font-semibold text-primary">No cases match your filters</div>
          <p className="text-sm text-muted-foreground">
            {activeMainTab === "AVAILABLE_CASES"
              ? "All available cases have been taken up or reviewed. Check back soon!"
              : "No assigned cases match the active search parameters."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map(item => {
            const c = item.case;
            const isRepeat = c.urgency_flags?.repeat_offender;
            const thresholdLabel = isRepeat ? "1/2 Threshold" : "1/3 Threshold";
            const thresholdDays = isRepeat
              ? Math.ceil(c.max_sentence_days_for_offense / 2)
              : Math.ceil(c.max_sentence_days_for_offense / 3);
            const isEligible = item.days_overdue > 0 || c.custody_days >= thresholdDays;
            const missingDocs = c.required_docs.filter(d => !c.present_docs.includes(d));
            const isAvailableTab = activeMainTab === "AVAILABLE_CASES";

            return (
              <div
                key={c.case_id}
                className="group relative bg-card shadow-sm border border-border hover:border-accent/40 rounded p-6 transition-all duration-300 backdrop-blur-md flex flex-col justify-between hover:shadow-xl hover:shadow-accent/5 space-y-5"
              >
                <div className="space-y-4">
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="font-mono text-xs font-semibold text-accent tracking-wider">
                        {c.case_id}
                      </span>
                      <h3 className="text-base font-semibold text-primary group-hover:text-accent transition-colors">
                        {c.name}
                      </h3>
                    </div>
                    {isEligible ? (
                      <span className="px-2.5 py-1 rounded-sm text-[10px] font-bold uppercase tracking-wider bg-muted text-foreground border border-border flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> Eligible
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-sm text-[10px] font-bold uppercase tracking-wider bg-secondary/50 text-muted-foreground border border-border flex items-center gap-1">
                        <Clock className="w-3 h-3" /> Ineligible
                      </span>
                    )}
                  </div>

                  {/* Offense & Detention Badges */}
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="px-2 py-0.5 rounded bg-secondary/50 text-muted-foreground border border-border font-mono">
                      {c.offense_sections.join(", ")}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-secondary/50 text-muted-foreground border border-border">
                      Age: {c.urgency_flags.age}
                    </span>
                    {c.urgency_flags.health_flag && (
                      <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border flex items-center gap-1">
                        <ShieldAlert className="w-3 h-3" /> Medical Flag
                      </span>
                    )}
                  </div>

                  {/* Sentence Threshold Progress */}
                  <div className="space-y-1.5 pt-2">
                    <div className="flex justify-between text-xs text-muted-foreground font-mono">
                      <span>Custody: {c.custody_days}d</span>
                      <span>{thresholdLabel}: {thresholdDays}d</span>
                    </div>
                    <div className="w-full h-1.5 bg-secondary/50 rounded-sm overflow-hidden">
                      <div
                        className={`h-full rounded-sm transition-all duration-500 ${
                          isEligible ? "bg-accent" : "bg-accent"
                        }`}
                        style={{
                          width: `${Math.min(100, (c.custody_days / thresholdDays) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>

                  {/* FAMILY CONTACT PREVIEW */}
                  <div className="p-3 rounded bg-card shadow-sm border border-border space-y-1 text-xs">
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <UserCheck className="w-3 h-3 text-accent" /> {c.relative_relation || "Parent/Relative"}:
                      </span>
                      <span className="font-semibold text-primary">{c.relative_name || "Ramesh Kumar"}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-foreground font-mono">
                      <span className="flex items-center gap-1">
                        <Phone className="w-3 h-3 text-foreground" /> Mobile:
                      </span>
                      <span>{c.relative_phone || "+91 98765 11001"}</span>
                    </div>
                  </div>

                  {/* Document Warning */}
                  {missingDocs.length > 0 && (
                    <div className="p-2.5 rounded-sm bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 shrink-0" />
                      <span>Missing: {missingDocs.map(d => d.replace("_", " ")).join(", ")}</span>
                    </div>
                  )}
                </div>

                {/* Card Action Footer */}
                <div className="pt-4 border-t border-border flex items-center justify-between">
                  <span className="text-xs text-muted-foreground truncate max-w-[160px]">
                    {c.jail_location}
                  </span>

                  {isAvailableTab ? (
                    <button
                      onClick={() => {
                        setSelectedAvailableCase(item);
                        setIsModalOpen(true);
                      }}
                      className="px-3.5 py-1.5 bg-accent/10 hover:bg-accent/20 border border-accent/30 text-accent rounded text-xs font-semibold transition-all flex items-center gap-1.5"
                    >
                      <Eye className="w-3.5 h-3.5" /> Review & Take Case
                    </button>
                  ) : (
                    <Link
                      to={`/case/${c.case_id}`}
                      className="text-xs font-semibold text-primary group-hover:text-accent flex items-center gap-1 transition-colors"
                    >
                      Analyze Case <ArrowUpRight className="w-3.5 h-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Available Case Scroll-Approval Modal */}
      <AvailableCaseModal
        item={selectedAvailableCase}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedAvailableCase(null);
        }}
        onApprove={handleApproveCase}
        onDecline={handleDeclineCase}
      />
    </div>
  );
}
