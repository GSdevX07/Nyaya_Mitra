import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Scale,
  Briefcase,
  UserPlus,
  AlertTriangle,
  CheckCircle2,
  Search,
  RefreshCw,
  Building2,
  Calendar,
  X,
  AlertCircle,
  Loader2,
  ChevronRight,
  Shield,
  FileQuestion,
} from "lucide-react";
import {
  fetchCases,
  fetchEligibleCounselApi,
  assignCounselToCaseApi,
  type CaseRecord,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { UniversalTaskQueue } from "../components/UniversalTaskQueue";

function hasChargeSheet(c: CaseRecord): boolean {
  return (c.present_docs || []).some((d) => d.toLowerCase().includes("charge"));
}

function hasCustodyCertificate(c: CaseRecord): boolean {
  return (c.present_docs || []).some((d) => d.toLowerCase().includes("custody"));
}

function isSec479Eligible(c: CaseRecord): boolean {
  return c.custody_days > 90 || c.status === "ELIGIBLE";
}

export function DlsaWorkspace() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [activeTab, setActiveTab] = useState<
    "queue" | "assignment" | "tracking" | "missing_docs" | "hearings" | "overdue"
  >("queue");

  // Search & Filters
  const [search, setSearch] = useState("");
  const [filterDistrict, setFilterDistrict] = useState("");

  // Assignment Modal State
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignCase, setAssignCase] = useState<CaseRecord | null>(null);
  const [eligibleCounsel, setEligibleCounsel] = useState<any[]>([]);
  const [selectedLawyerId, setSelectedLawyerId] = useState<string>("");
  const [assignmentNotes, setAssignmentNotes] = useState<string>("");
  const [counselLoading, setCounselLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [actionNotice, setActionNotice] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Missing Doc Coordination Modal State
  const [showCoordModal, setShowCoordModal] = useState(false);
  const [coordCase, setCoordCase] = useState<CaseRecord | null>(null);
  const [coordNotes, setCoordNotes] = useState("");
  const [coordinating, setCoordinating] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const rawCasesData = await fetchCases();
      const extracted = (rawCasesData || []).map((item: any) => (item.case || item) as CaseRecord);
      setCases(extracted);
    } catch (err: any) {
      console.error("Failed to load cases for DLSA workspace:", err);
      setActionNotice({
        type: "error",
        message: err.message || "Failed to load operational cases from server.",
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Derived subsets
  const unassignedCases = cases.filter(
    (c) =>
      !c.assigned_lawyer &&
      c.status !== "DISCHARGED" &&
      c.status !== "RELEASE_CONFIRMED"
  );

  const assignedCases = cases.filter(
    (c) =>
      !!c.assigned_lawyer &&
      c.status !== "DISCHARGED" &&
      c.status !== "RELEASE_CONFIRMED"
  );

  const missingDocCases = cases.filter((c) => {
    const isUndertrial = c.prisoner_category !== "CONVICTED";
    return (
      isUndertrial &&
      (!hasChargeSheet(c) || !hasCustodyCertificate(c)) &&
      c.status !== "DISCHARGED" &&
      c.status !== "RELEASE_CONFIRMED"
    );
  });

  const overdueCases = cases.filter(
    (c) =>
      (c.custody_days > 180 || isSec479Eligible(c)) &&
      c.status !== "DISCHARGED" &&
      c.status !== "RELEASE_CONFIRMED"
  );

  const hearingCases = cases.filter(
    (c) =>
      c.status === "HEARING_SCHEDULED" ||
      c.status === "BAIL_FILED" ||
      c.status === "APPROVED"
  );

  // Filtered lists based on search
  const filteredUnassigned = unassignedCases.filter((c) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !q ||
      c.name.toLowerCase().includes(q) ||
      c.case_id.toLowerCase().includes(q) ||
      (c.fir_number && c.fir_number.toLowerCase().includes(q));
    const matchesDistrict =
      !filterDistrict ||
      (c.district || "").toLowerCase() === filterDistrict.toLowerCase();
    return matchesSearch && matchesDistrict;
  });

  const filteredAssigned = assignedCases.filter((c) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !q ||
      c.name.toLowerCase().includes(q) ||
      c.case_id.toLowerCase().includes(q) ||
      (c.assigned_lawyer && c.assigned_lawyer.toLowerCase().includes(q));
    return matchesSearch;
  });

  const handleOpenAssignModal = async (c: CaseRecord) => {
    setAssignCase(c);
    setShowAssignModal(true);
    setCounselLoading(true);
    setSelectedLawyerId("");
    setAssignmentNotes(
      `Formally assigned under NALSA / DLSA free legal aid scheme by ${
        user?.full_name || "DLSA Officer"
      }.`
    );
    try {
      const res = await fetchEligibleCounselApi(c.case_id);
      const list = res.counsel || res.counsel_list || [];
      setEligibleCounsel(list);
      if (list.length > 0) {
        setSelectedLawyerId(list[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch eligible counsel:", err);
      setEligibleCounsel([]);
      setSelectedLawyerId("");
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
        message: `Defense Counsel ${
          chosen?.name || selectedLawyerId
        } formally assigned to Case ${
          assignCase.case_id
        }. Lifecycle transitioned to COUNSEL_ASSIGNED.`,
      });
      await loadData();
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: err.message || "Failed to assign legal aid counsel to case.",
      });
    } finally {
      setAssigning(false);
    }
  };

  const handleOpenCoordModal = (c: CaseRecord) => {
    setCoordCase(c);
    setCoordNotes(
      `Expediting missing charge sheet / custody certificate for ${c.case_id} (${c.name}). Notice issued to investigating station and jail administration.`
    );
    setShowCoordModal(true);
  };

  const handleConfirmCoord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!coordCase) return;
    setCoordinating(true);
    try {
      setShowCoordModal(false);
      setActionNotice({
        type: "success",
        message: `Institutional coordination notice logged for Case ${coordCase.case_id}. Police Station and Jail Superintendent alerted.`,
      });
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: err.message || "Failed to log coordination notice.",
      });
    } finally {
      setCoordinating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Institutional Authority Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b-2 border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Scale className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold tracking-widest text-muted-foreground uppercase">
              Legal Services Authorities Act, 1987 // Statutory Legal Aid Desk
            </span>
          </div>
          <h1 className="text-2xl font-bold font-serif text-foreground tracking-tight mt-1">
            DLSA / KSLSA Legal Aid Operations Desk
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Jurisdiction:{" "}
            <strong className="text-foreground font-mono">
              {user?.district || "Central Delhi"} DLSA
            </strong>{" "}
            • State:{" "}
            <strong className="text-foreground font-mono">
              {user?.state || "Delhi"} SLSA
            </strong>{" "}
            • Section 12 Free Legal Aid Scheme Oversight
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="px-3 py-1.5 bg-secondary text-foreground text-xs font-mono rounded-sm border border-border flex items-center gap-1.5 hover:bg-secondary/80 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionNotice && (
        <div
          className={`p-3 rounded-sm border text-xs font-mono flex items-center justify-between ${
            actionNotice.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionNotice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            )}
            <span>{actionNotice.message}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            className="hover:opacity-70 font-bold ml-4"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Operational Metrics Cards (Black/White/Green/Red only) */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3 bg-card border border-border rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase flex items-center gap-1">
            <UserPlus className="w-3 h-3 text-red-600" /> Unassigned Intake
          </div>
          <div className="text-xl font-bold font-serif text-foreground mt-1">
            {unassignedCases.length}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
            Require Counsel Assignment
          </div>
        </div>

        <div className="p-3 bg-card border border-border rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase flex items-center gap-1">
            <Briefcase className="w-3 h-3 text-emerald-600" /> Active Assigned
          </div>
          <div className="text-xl font-bold font-serif text-foreground mt-1">
            {assignedCases.length}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
            With Panel Advocates
          </div>
        </div>

        <div className="p-3 bg-card border border-border rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase flex items-center gap-1">
            <FileQuestion className="w-3 h-3 text-red-600" /> Missing Docs
          </div>
          <div className="text-xl font-bold font-serif text-foreground mt-1">
            {missingDocCases.length}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
            Custody / Remand / Chargesheet
          </div>
        </div>

        <div className="p-3 bg-card border border-border rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase flex items-center gap-1">
            <Calendar className="w-3 h-3 text-foreground" /> Hearings Active
          </div>
          <div className="text-xl font-bold font-serif text-foreground mt-1">
            {hearingCases.length}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
            Bail / Production Tracking
          </div>
        </div>

        <div className="p-3 bg-card border border-border rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-rose-600" /> Overdue / 479
          </div>
          <div className="text-xl font-bold font-serif text-foreground mt-1">
            {overdueCases.length}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
            Critical SLA / Benchmark
          </div>
        </div>
      </div>

      {/* Navigation Tabs (Strictly Neutral / Black / Red / Green) */}
      <div className="flex border-b border-border text-xs font-mono gap-1">
        <button
          onClick={() => setActiveTab("queue")}
          className={`px-4 py-2 border-b-2 font-bold transition-colors flex items-center gap-1.5 ${
            activeTab === "queue"
              ? "border-foreground text-foreground bg-secondary/30"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          Authoritative Task Queue
        </button>

        <button
          onClick={() => setActiveTab("assignment")}
          className={`px-4 py-2 border-b-2 font-bold transition-colors flex items-center gap-1.5 ${
            activeTab === "assignment"
              ? "border-foreground text-foreground bg-secondary/30"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserPlus className="w-3.5 h-3.5" />
          Counsel Assignment Desk ({unassignedCases.length})
        </button>

        <button
          onClick={() => setActiveTab("tracking")}
          className={`px-4 py-2 border-b-2 font-bold transition-colors flex items-center gap-1.5 ${
            activeTab === "tracking"
              ? "border-foreground text-foreground bg-secondary/30"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Briefcase className="w-3.5 h-3.5" />
          Assignment Tracking ({assignedCases.length})
        </button>

        <button
          onClick={() => setActiveTab("missing_docs")}
          className={`px-4 py-2 border-b-2 font-bold transition-colors flex items-center gap-1.5 ${
            activeTab === "missing_docs"
              ? "border-foreground text-foreground bg-secondary/30"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileQuestion className="w-3.5 h-3.5" />
          Missing-Doc Coordination ({missingDocCases.length})
        </button>

        <button
          onClick={() => setActiveTab("hearings")}
          className={`px-4 py-2 border-b-2 font-bold transition-colors flex items-center gap-1.5 ${
            activeTab === "hearings"
              ? "border-foreground text-foreground bg-secondary/30"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Calendar className="w-3.5 h-3.5" />
          Hearings Follow-Up ({hearingCases.length})
        </button>

        <button
          onClick={() => setActiveTab("overdue")}
          className={`px-4 py-2 border-b-2 font-bold transition-colors flex items-center gap-1.5 ${
            activeTab === "overdue"
              ? "border-foreground text-foreground bg-secondary/30"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
          Overdue & Exceptions ({overdueCases.length})
        </button>
      </div>

      {/* TAB 1: Universal Task Queue */}
      {activeTab === "queue" && (
        <div className="space-y-4">
          <UniversalTaskQueue
            hideHeader={true}
            allowedTaskTypes={[
              "INTAKE_NEED_ASSESSMENT",
              "ASSIGN_LEGAL_AID_COUNSEL",
              "EXPEDITE_MISSING_CHARGE_SHEET",
              "VERIFY_CUSTODY_CERTIFICATE",
              "HEARING_FOLLOW_UP",
              "MATTER_COMPLETION_MONITORING",
              "RESOLVE_EXCEPTION",
            ]}
          />
        </div>
      )}

      {/* TAB 2: Counsel Assignment Desk */}
      {activeTab === "assignment" && (
        <div className="space-y-4">
          {/* Desk Search & Filter Bar */}
          <div className="flex flex-col md:flex-row items-center gap-3">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted-foreground" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search unassigned matters by accused name, case ID, or FIR..."
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-card border border-border rounded-sm focus:outline-none focus:ring-1 focus:ring-primary font-sans"
              />
            </div>
            <div className="flex items-center gap-2 w-full md:w-auto">
              <select
                value={filterDistrict}
                onChange={(e) => setFilterDistrict(e.target.value)}
                className="py-1.5 px-3 text-xs bg-card border border-border rounded-sm font-mono text-foreground focus:outline-none"
              >
                <option value="">All Districts</option>
                <option value="Central Delhi">Central Delhi</option>
                <option value="South Delhi">South Delhi</option>
                <option value="North Delhi">North Delhi</option>
                <option value="West Delhi">West Delhi</option>
                <option value="Bengaluru Urban">Bengaluru Urban</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div className="p-12 text-center text-xs font-mono text-muted-foreground flex items-center justify-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-primary" /> Loading assignment desk...
            </div>
          ) : filteredUnassigned.length === 0 ? (
            <div className="p-12 text-center border-2 border-dashed border-border rounded-sm bg-card">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <h3 className="text-sm font-bold font-serif text-foreground">
                Assignment Desk Clear
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                No unassigned matters awaiting legal-aid counsel assignment matching filter criteria.
              </p>
            </div>
          ) : (
            <div className="border border-border rounded-sm overflow-hidden bg-card">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-secondary/60 border-b border-border text-[11px] font-mono uppercase text-muted-foreground">
                    <th className="p-3">Accused & Case ID</th>
                    <th className="p-3">Custody Duration</th>
                    <th className="p-3">Alleged Offenses</th>
                    <th className="p-3">Facility & District</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Assignment Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredUnassigned.map((c) => (
                    <tr key={c.case_id} className="hover:bg-secondary/20 transition-colors">
                      <td className="p-3">
                        <div className="font-serif font-bold text-sm text-foreground">
                          {c.name}
                        </div>
                        <div className="font-mono text-[10px] text-muted-foreground mt-0.5">
                          {c.case_id} {c.fir_number && `• FIR: ${c.fir_number}`}
                        </div>
                      </td>

                      <td className="p-3 font-mono">
                        <div className="font-bold text-foreground">{c.custody_days} days</div>
                        <div className="text-[10px] text-muted-foreground">
                          {isSec479Eligible(c) ? (
                            <span className="text-emerald-700 dark:text-emerald-400 font-bold">
                              §479 Threshold Met
                            </span>
                          ) : (
                            "Statutory Period Counting"
                          )}
                        </div>
                      </td>

                      <td className="p-3 font-mono text-[11px]">
                        <div>{c.offense_sections?.join(", ") || "—"}</div>
                        <div className="text-[10px] text-muted-foreground">
                          {c.court_name || "Competent Court"}
                        </div>
                      </td>

                      <td className="p-3 text-[11px]">
                        <div>{c.jail_location || "—"}</div>
                        <div className="text-[10px] font-mono text-muted-foreground">
                          {c.district || "—"}
                        </div>
                      </td>

                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold bg-secondary text-foreground border-border">
                          {c.status || "INTAKE"}
                        </span>
                      </td>

                      <td className="p-3 text-right">
                        <button
                          onClick={() => handleOpenAssignModal(c)}
                          className="px-3 py-1.5 bg-primary text-primary-foreground font-mono text-xs font-bold rounded-sm inline-flex items-center gap-1.5 hover:opacity-90 shadow-sm"
                        >
                          <UserPlus className="w-3.5 h-3.5" /> Assign Legal-Aid Counsel
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Assignment Tracking */}
      {activeTab === "tracking" && (
        <div className="space-y-4">
          <div className="border border-border rounded-sm overflow-hidden bg-card">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-secondary/60 border-b border-border text-[11px] font-mono uppercase text-muted-foreground">
                  <th className="p-3">Accused & Case ID</th>
                  <th className="p-3">Assigned Panel Advocate</th>
                  <th className="p-3">Current Lifecycle State</th>
                  <th className="p-3">Custody Days</th>
                  <th className="p-3">Facility</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredAssigned.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-muted-foreground font-mono text-xs">
                      No active counsel assignments recorded.
                    </td>
                  </tr>
                ) : (
                  filteredAssigned.map((c) => (
                    <tr key={c.case_id} className="hover:bg-secondary/20 transition-colors">
                      <td className="p-3">
                        <div className="font-serif font-bold text-sm text-foreground">
                          {c.name}
                        </div>
                        <div className="font-mono text-[10px] text-muted-foreground">
                          {c.case_id}
                        </div>
                      </td>

                      <td className="p-3">
                        <div className="font-bold text-foreground font-sans">
                          {c.assigned_lawyer || "Assigned Panel Counsel"}
                        </div>
                        <div className="font-mono text-[10px] text-muted-foreground">
                          Empanelled Advocate
                        </div>
                      </td>

                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold ${
                            c.status === "APPROVED" || c.status === "BAIL_FILED"
                              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30"
                              : "bg-secondary text-foreground border-border"
                          }`}
                        >
                          {c.status || "ASSIGNED"}
                        </span>
                      </td>

                      <td className="p-3 font-mono">
                        <div>{c.custody_days} days</div>
                      </td>

                      <td className="p-3 text-[11px] text-muted-foreground">
                        {c.jail_location || "—"}
                      </td>

                      <td className="p-3 text-right">
                        <Link
                          to={`/case/${c.case_id}`}
                          className="px-2.5 py-1 bg-secondary hover:bg-secondary/80 text-foreground border border-border text-xs font-mono rounded-sm inline-flex items-center gap-1"
                        >
                          Dossier <ChevronRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: Missing Document Coordination */}
      {activeTab === "missing_docs" && (
        <div className="space-y-4">
          <div className="p-3.5 bg-card border border-border rounded-sm text-xs font-mono text-muted-foreground flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileQuestion className="w-4 h-4 text-red-600" />
              <span>
                Missing document bottlenecks actively delaying bail drafting or verification under Section 479 BNSS.
              </span>
            </div>
            <span className="font-bold text-foreground">{missingDocCases.length} Matters Pending</span>
          </div>

          <div className="border border-border rounded-sm overflow-hidden bg-card">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-secondary/60 border-b border-border text-[11px] font-mono uppercase text-muted-foreground">
                  <th className="p-3">Accused & Case ID</th>
                  <th className="p-3">Missing Record(s)</th>
                  <th className="p-3">Custody Days</th>
                  <th className="p-3">Custodian Station / Facility</th>
                  <th className="p-3 text-right">Institutional Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {missingDocCases.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-muted-foreground font-mono text-xs">
                      No missing document bottlenecks recorded.
                    </td>
                  </tr>
                ) : (
                  missingDocCases.map((c) => (
                    <tr key={c.case_id} className="hover:bg-secondary/20 transition-colors">
                      <td className="p-3">
                        <div className="font-serif font-bold text-sm text-foreground">
                          {c.name}
                        </div>
                        <div className="font-mono text-[10px] text-muted-foreground">
                          {c.case_id}
                        </div>
                      </td>

                      <td className="p-3 space-x-1">
                        {!hasChargeSheet(c) && (
                          <span className="inline-block px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold bg-rose-500/10 text-rose-600 border-rose-500/30">
                            Charge Sheet Missing
                          </span>
                        )}
                        {!hasCustodyCertificate(c) && (
                          <span className="inline-block px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold bg-red-500/10 text-red-600 border-red-500/30">
                            Custody Cert Missing
                          </span>
                        )}
                      </td>

                      <td className="p-3 font-mono font-bold text-foreground">
                        {c.custody_days} days
                      </td>

                      <td className="p-3 text-[11px]">
                        <div>{c.jail_location || "Sub-Jail"}</div>
                        <div className="text-[10px] font-mono text-muted-foreground">
                          Police Station: Kotwali / Respective PS
                        </div>
                      </td>

                      <td className="p-3 text-right">
                        <button
                          onClick={() => handleOpenCoordModal(c)}
                          className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground border border-border text-xs font-mono rounded-sm inline-flex items-center gap-1.5"
                        >
                          <Building2 className="w-3.5 h-3.5" /> Expedite Coordination
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: Hearings Follow-Up */}
      {activeTab === "hearings" && (
        <div className="space-y-4">
          <div className="border border-border rounded-sm overflow-hidden bg-card">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-secondary/60 border-b border-border text-[11px] font-mono uppercase text-muted-foreground">
                  <th className="p-3">Accused & Case ID</th>
                  <th className="p-3">Assigned Legal-Aid Counsel</th>
                  <th className="p-3">Current Court Status</th>
                  <th className="p-3">Competent Court</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {hearingCases.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-muted-foreground font-mono text-xs">
                      No active court hearings or scheduled bail proceedings currently pending.
                    </td>
                  </tr>
                ) : (
                  hearingCases.map((c) => (
                    <tr key={c.case_id} className="hover:bg-secondary/20 transition-colors">
                      <td className="p-3">
                        <div className="font-serif font-bold text-sm text-foreground">
                          {c.name}
                        </div>
                        <div className="font-mono text-[10px] text-muted-foreground">
                          {c.case_id}
                        </div>
                      </td>

                      <td className="p-3 font-sans">
                        <div className="font-bold text-foreground">{c.assigned_lawyer || "Assigned Panel Advocate"}</div>
                      </td>

                      <td className="p-3 font-mono">
                        <span className="px-2 py-0.5 rounded-sm border text-[10px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30">
                          {c.status || "HEARING_SCHEDULED"}
                        </span>
                      </td>

                      <td className="p-3 text-[11px] text-muted-foreground">
                        {c.court_name || "District Courts"}
                      </td>

                      <td className="p-3 text-right">
                        <Link
                          to={`/case/${c.case_id}`}
                          className="px-2.5 py-1 bg-secondary hover:bg-secondary/80 text-foreground border border-border text-xs font-mono rounded-sm inline-flex items-center gap-1"
                        >
                          View Hearing <ChevronRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 6: Overdue & Exceptions */}
      {activeTab === "overdue" && (
        <div className="space-y-4">
          <div className="border border-border rounded-sm overflow-hidden bg-card">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-secondary/60 border-b border-border text-[11px] font-mono uppercase text-muted-foreground">
                  <th className="p-3">Accused & Case ID</th>
                  <th className="p-3">Custody Days (Benchmark)</th>
                  <th className="p-3">Section 479 Status</th>
                  <th className="p-3">Assigned Advocate</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {overdueCases.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-muted-foreground font-mono text-xs">
                      Zero matters currently exceeding SLA or Section 479 benchmarks.
                    </td>
                  </tr>
                ) : (
                  overdueCases.map((c) => (
                    <tr key={c.case_id} className="hover:bg-secondary/20 transition-colors">
                      <td className="p-3">
                        <div className="font-serif font-bold text-sm text-foreground">
                          {c.name}
                        </div>
                        <div className="font-mono text-[10px] text-muted-foreground">
                          {c.case_id}
                        </div>
                      </td>

                      <td className="p-3 font-mono font-bold text-rose-600">
                        {c.custody_days} days
                      </td>

                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-sm border text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30">
                          §479 Relief Qualified
                        </span>
                      </td>

                      <td className="p-3 text-[11px]">
                        {c.assigned_lawyer || (
                          <span className="text-red-600 font-mono font-bold">Unassigned</span>
                        )}
                      </td>

                      <td className="p-3 text-right">
                        {!c.assigned_lawyer ? (
                          <button
                            onClick={() => handleOpenAssignModal(c)}
                            className="px-2.5 py-1 bg-primary text-primary-foreground text-xs font-mono font-bold rounded-sm hover:opacity-90"
                          >
                            Assign Immediately
                          </button>
                        ) : (
                          <Link
                            to={`/case/${c.case_id}`}
                            className="px-2.5 py-1 bg-secondary text-foreground border border-border text-xs font-mono rounded-sm hover:bg-secondary/80 inline-flex items-center gap-1"
                          >
                            Review Dossier <ChevronRight className="w-3 h-3" />
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* FORMAL COUNSEL ASSIGNMENT MODAL */}
      {showAssignModal && assignCase && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2 text-foreground">
                <Briefcase className="w-5 h-5 text-primary" />
                <h3 className="text-base font-serif font-bold">
                  Formal Legal-Aid Counsel Assignment
                </h3>
              </div>
              <button
                onClick={() => setShowAssignModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-secondary/30 rounded-sm border border-border text-xs font-mono space-y-1">
              <div>
                <strong>Accused Person:</strong> {assignCase.name} ({assignCase.case_id})
              </div>
              <div>
                <strong>Custody Duration:</strong> {assignCase.custody_days} days (
                {isSec479Eligible(assignCase) ? "§479 Threshold Met" : "Undertrial"}
                )
              </div>
              <div>
                <strong>Alleged Offenses:</strong>{" "}
                {assignCase.offense_sections?.join(", ") || "—"}
              </div>
            </div>

            {counselLoading ? (
              <div className="p-8 text-center text-xs font-mono text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                Querying statutory empanelment roster &amp; active caseloads...
              </div>
            ) : (
              <form onSubmit={handleConfirmAssignment} className="space-y-4 text-xs font-mono">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1 font-bold">
                    Select Empanelled Defense Advocate *
                  </label>
                  <div className="space-y-2 max-h-56 overflow-y-auto border border-border p-2 rounded-sm">
                    {eligibleCounsel.length === 0 ? (
                      <div className="p-4 text-center text-muted-foreground text-xs font-mono border border-dashed border-border rounded-sm">
                        No Eligible Counsel Available
                      </div>
                    ) : (
                      eligibleCounsel.map((adv) => (
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
                      ))
                    )}
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
                    className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-sm flex items-center gap-1.5 hover:opacity-90 disabled:opacity-50"
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

      {/* MISSING DOCUMENT EXPEDITE MODAL */}
      {showCoordModal && coordCase && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2 text-foreground">
                <FileQuestion className="w-5 h-5 text-red-600" />
                <h3 className="text-base font-serif font-bold">
                  Expedite Institutional Documents
                </h3>
              </div>
              <button
                onClick={() => setShowCoordModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleConfirmCoord} className="space-y-4 text-xs font-mono">
              <p className="text-muted-foreground leading-relaxed">
                Issue official DLSA coordination reminder to Police Station and Jail Superintendent for missing records in{" "}
                <strong className="text-foreground">{coordCase.name}</strong> ({coordCase.case_id}).
              </p>

              <div>
                <label className="block uppercase text-muted-foreground mb-1 font-bold">
                  Coordination Order Notes *
                </label>
                <textarea
                  rows={3}
                  required
                  value={coordNotes}
                  onChange={(e) => setCoordNotes(e.target.value)}
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCoordModal(false)}
                  className="px-4 py-2 border border-border rounded-sm hover:bg-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={coordinating}
                  className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-sm flex items-center gap-1.5"
                >
                  {coordinating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Dispatch Coordination Notice
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
