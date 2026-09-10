import { useState, useEffect } from "react";
import {
  ShieldAlert, AlertTriangle, CheckCircle2,
  Search, Plus, ChevronRight, FileText, UserCheck, Check,
  Clock, Send, X, Inbox, Loader2, Edit3
} from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import {
  fetchPoliceCases,
  fetchPoliceActions,
  acknowledgePoliceAction,
  completePoliceAction,
  uploadDocumentFile,
  fetchEvidenceChain,
  intakeFIRRecord,
  updateFIRRecord,
  type PoliceCaseSummary,
  type PoliceActionItem
} from "../lib/api";
import { RoleEvidenceProvenanceModal } from "../components/RoleEvidenceProvenanceModal";

const POLICE_DOC_TYPES = [
  { value: "fir", label: "FIR Copy (First Information Report)" },
  { value: "fir_amendment", label: "FIR Amendment / Supplementary Statement" },
  { value: "arrest_memo", label: "Arrest Memo (Formal Custody Record)" },
  { value: "case_diary_extract", label: "Case Diary Extract (Investigation Log)" },
  { value: "charge_sheet", label: "Final Police Report / Charge Sheet (Sec 193 BNSS / 173 CrPC)" },
  { value: "seizure_memo", label: "Seizure Memo / Panchnama" },
  { value: "police_status_report", label: "Police Status Report / Inquiry Report" },
  { value: "remand_application", label: "Police Remand / Custody Extension Application" },
  { value: "other_police_record", label: "Other Police Operational Record" },
];

export function PoliceWorkspace() {
  const { user } = useAuth();
  const [cases, setCases] = useState<PoliceCaseSummary[]>([]);
  const [actions, setActions] = useState<PoliceActionItem[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"cases" | "requests">("cases");

  // Modal State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [selectedDocType, setSelectedDocType] = useState(POLICE_DOC_TYPES[0].value);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customText, setCustomText] = useState("");
  const [linkedActionId, setLinkedActionId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // FIR Intake Modal State
  const [showFIRIntakeModal, setShowFIRIntakeModal] = useState(false);
  const [firForm, setFirForm] = useState({
    fir_number: "",
    accused_name: "",
    offense_sections: "BNS 303(2)",
    filing_date: new Date().toISOString().split("T")[0],
    arrest_date: new Date().toISOString().split("T")[0],
    court_name: "Chief Metropolitan Magistrate Court",
    incident_details: "",
    investigating_officer: "",
  });
  const [firSubmitting, setFirSubmitting] = useState(false);
  const [firMsg, setFirMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  // FIR Update Modal State
  const [showFIRUpdateModal, setShowFIRUpdateModal] = useState(false);
  const [updateCaseTarget, setUpdateCaseTarget] = useState<PoliceCaseSummary | null>(null);
  const [updateForm, setUpdateForm] = useState({
    offense_sections: "",
    charge_sheet_status: "PENDING_INVESTIGATION",
    remand_status: "INITIAL_REMAND",
    court_name: "",
    investigating_officer: "",
    investigation_notes: "",
  });
  const [updateSubmitting, setUpdateSubmitting] = useState(false);
  const [updateMsg, setUpdateMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const handleOpenUpdateModal = (c: PoliceCaseSummary) => {
    setUpdateCaseTarget(c);
    setUpdateForm({
      offense_sections: (c.offense_sections || []).join(", "),
      charge_sheet_status: c.charge_sheet_present ? "SUBMITTED_TO_COURT" : "PENDING_INVESTIGATION",
      remand_status: c.remand_order_present ? "AVAILABLE_ON_RECORD" : "INITIAL_REMAND",
      court_name: c.court_name || "",
      investigating_officer: "",
      investigation_notes: "",
    });
    setUpdateMsg(null);
    setShowFIRUpdateModal(true);
  };

  const handleFIRIntakeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firForm.fir_number.trim() || !firForm.accused_name.trim()) {
      setFirMsg({ text: "FIR number and accused name are required.", type: "error" });
      return;
    }
    setFirSubmitting(true);
    setFirMsg(null);
    try {
      const sections = firForm.offense_sections.split(",").map((s) => s.trim()).filter(Boolean);
      await intakeFIRRecord({
        fir_number: firForm.fir_number.trim(),
        accused_name: firForm.accused_name.trim(),
        police_station: user?.police_station || "Kotwali Police Station",
        police_station_id: user?.police_station_id || "ps_kotwali_central",
        district: user?.district || "Central Delhi",
        offense_sections: sections.length > 0 ? sections : ["BNS 303"],
        filing_date: firForm.filing_date,
        arrest_date: firForm.arrest_date,
        court_name: firForm.court_name,
        incident_details: firForm.incident_details,
        investigating_officer: firForm.investigating_officer,
      });
      setFirMsg({ text: "FIR docket registered successfully in station records.", type: "success" });
      await loadData();
      setTimeout(() => setShowFIRIntakeModal(false), 1400);
    } catch (err: any) {
      setFirMsg({ text: "Registration failed: " + (err.message || String(err)), type: "error" });
    } finally {
      setFirSubmitting(false);
    }
  };

  const handleFIRUpdateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updateCaseTarget) return;
    setUpdateSubmitting(true);
    setUpdateMsg(null);
    try {
      const sections = updateForm.offense_sections.split(",").map((s) => s.trim()).filter(Boolean);
      await updateFIRRecord(updateCaseTarget.case_id, {
        offense_sections: sections.length > 0 ? sections : undefined,
        charge_sheet_status: updateForm.charge_sheet_status,
        remand_status: updateForm.remand_status,
        court_name: updateForm.court_name || undefined,
        investigating_officer: updateForm.investigating_officer || undefined,
        investigation_notes: updateForm.investigation_notes || undefined,
      });
      setUpdateMsg({ text: "Station investigation record updated successfully.", type: "success" });
      await loadData();
      setTimeout(() => setShowFIRUpdateModal(false), 1400);
    } catch (err: any) {
      setUpdateMsg({ text: "Update failed: " + (err.message || String(err)), type: "error" });
    } finally {
      setUpdateSubmitting(false);
    }
  };

  // Provenance Modal State
  const [provenanceModalCaseId, setProvenanceModalCaseId] = useState<string | null>(null);
  const [provenanceData, setProvenanceData] = useState<any>(null);
  const [provenanceLoading, setProvenanceLoading] = useState(false);

  const handleOpenProvenance = async (caseId: string) => {
    setProvenanceModalCaseId(caseId);
    setProvenanceLoading(true);
    try {
      const data = await fetchEvidenceChain(caseId);
      setProvenanceData(data);
    } catch (err) {
      console.error("Failed to load police provenance:", err);
    } finally {
      setProvenanceLoading(false);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [caseData, actionData] = await Promise.all([
        fetchPoliceCases(),
        fetchPoliceActions(),
      ]);
      setCases(caseData);
      setActions(actionData);
    } catch (err) {
      console.error("Failed to load police workspace data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAcknowledge = async (actionId: string) => {
    try {
      await acknowledgePoliceAction(actionId);
      await loadData();
    } catch (err) {
      alert("Failed to acknowledge action: " + err);
    }
  };

  const openUploadModal = (caseId: string = "", actionId: string | null = null, defaultDocType: string = "") => {
    setSelectedCaseId(caseId || (cases[0]?.case_id || ""));
    setSelectedDocType(defaultDocType || POLICE_DOC_TYPES[0].value);
    setLinkedActionId(actionId);
    setSelectedFile(null);
    setCustomText("");
    setUploadMsg(null);
    setShowUploadModal(true);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCaseId) {
      setUploadMsg({ text: "Please select a valid Case ID.", type: "error" });
      return;
    }
    if (!selectedFile && !customText.trim()) {
      setUploadMsg({ text: "Please select a file or paste document text.", type: "error" });
      return;
    }

    setUploading(true);
    setUploadMsg(null);
    try {
      const result = await uploadDocumentFile(
        selectedCaseId,
        selectedDocType,
        selectedFile || undefined,
        customText.trim() || undefined,
      );

      if (linkedActionId) {
        const resAny = result as any;
        const docId = resAny.document_id || resAny.id || result.file_hash || `doc_${Date.now()}`;
        await completePoliceAction(
          linkedActionId,
          docId,
          `Submitted by station IO. Ref: ${selectedDocType} (Hash: ${result.file_hash?.substring(0, 12)}...)`
        );
      }

      setUploadMsg({
        text: "Official police document deposited successfully. Recorded in station investigation docket.",
        type: "success",
      });
      await loadData();
      setTimeout(() => setShowUploadModal(false), 1400);
    } catch (err: any) {
      setUploadMsg({ text: "Upload failed: " + (err.message || String(err)), type: "error" });
    } finally {
      setUploading(false);
    }
  };

  const filteredCases = cases.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.case_id.toLowerCase().includes(q) ||
      (c.fir_number && c.fir_number.toLowerCase().includes(q)) ||
      (c.police_station && c.police_station.toLowerCase().includes(q)) ||
      (c.offense_sections && c.offense_sections.join(" ").toLowerCase().includes(q))
    );
  });

  const chargesheetPending = cases.filter((c) => !c.charge_sheet_present);
  const remandAvailable = cases.filter((c) => c.remand_order_present);
  const pendingActions = actions.filter((a) => a.status !== "COMPLETED");

  const stationTitle = user?.police_station || "Authorized Police Station";
  const districtTitle = user?.district || "Jurisdiction";

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Police Case & Records Coordination Desk // {stationTitle}
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Police Investigation & Records Desk
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Maintain police-origin investigation records, upload FIRs and charge sheets, respond to DLSA document requests, and coordinate court production schedules.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => { setFirMsg(null); setShowFIRIntakeModal(true); }}
            className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" /> Register Station FIR
          </button>
          <button
            onClick={() => openUploadModal()}
            className="px-4 py-2 border border-border bg-secondary hover:bg-muted text-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-4 h-4" /> Upload Police Record
          </button>
          <Link
            to="/hearings"
            className="px-3 py-2 border border-border bg-secondary hover:bg-muted text-foreground font-mono text-xs font-semibold uppercase rounded-sm flex items-center gap-1.5"
          >
            <Clock className="w-4 h-4" /> Court Production Schedule
          </Link>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Station FIR Docket</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{cases.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">{stationTitle} // {districtTitle}</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Charge Sheet Status</div>
          <div className="text-2xl font-serif font-bold text-red-600 mt-1">{chargesheetPending.length}</div>
          <div className="text-[10px] font-mono text-red-600/80 mt-1">Pending Source Record</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Remand Record Status</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">{remandAvailable.length}</div>
          <div className="text-[10px] font-mono text-emerald-600/80 mt-1">Available on Record</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Institutional Requests</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{pendingActions.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">DLSA & Court Inquiries</div>
        </div>
      </div>

      {/* Workspace Tabs */}
      <div className="flex border-b border-border gap-2">
        <button
          onClick={() => setActiveTab("cases")}
          className={`px-4 py-2 text-xs font-mono font-bold uppercase border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "cases"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileText className="w-4 h-4" /> FIR & Investigation Docket ({cases.length})
        </button>
        <button
          onClick={() => setActiveTab("requests")}
          className={`px-4 py-2 text-xs font-mono font-bold uppercase border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "requests"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Inbox className="w-4 h-4" /> Institutional Requests & Compliance ({pendingActions.length})
        </button>
      </div>

      {/* TAB 1: FIR & Investigation Cases */}
      {activeTab === "cases" && (
        <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
          <div className="p-4 border-b border-border bg-secondary/30 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search by accused name, FIR no, offense section..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 text-xs bg-background border border-border rounded-sm font-sans focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
              />
            </div>
            <span className="text-xs font-mono text-muted-foreground self-center">
              Showing {filteredCases.length} of {cases.length} records
            </span>
          </div>

          {loading ? (
            <div className="p-12 text-center text-xs font-mono text-muted-foreground flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span>Loading police reference docket...</span>
            </div>
          ) : filteredCases.length === 0 ? (
            <div className="p-8 text-center text-xs font-mono text-muted-foreground">
              No matching records under authorized jurisdiction for "{searchQuery}".
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredCases.map((c) => {
                const accusedOpaqueId = `acc_${c.case_id.toLowerCase().replace("-", "_")}`;

                return (
                  <div
                    key={c.case_id}
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-sm font-serif text-foreground">{c.name}</span>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-secondary border border-border text-foreground">
                          {c.case_id}
                        </span>
                        {c.fir_number && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                            FIR: {c.fir_number}
                          </span>
                        )}
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-secondary text-muted-foreground border border-border">
                          {c.legal_code || "BNS_2023"}
                        </span>
                      </div>

                      <div className="text-xs font-sans text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1">
                        <span>PS: <strong className="text-foreground">{c.police_station || "Not provided by source system"}</strong></span>
                        <span>Offense: <strong className="text-foreground">{c.offense_sections?.join(", ") || "Sections on record"}</strong></span>
                        <span>Custody: <strong className="text-foreground">{c.custody_days || 0} days</strong></span>
                        <span>Detention: {c.jail_location || "Not specified"}</span>
                        <span>Court: {c.court_name}</span>
                      </div>

                      <div className="flex items-center gap-3 text-[11px] font-mono pt-1">
                        <span className={`flex items-center gap-1 ${c.remand_order_present ? 'text-emerald-600' : 'text-red-600'}`}>
                          {c.remand_order_present ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                          Remand Record: {c.remand_status}
                        </span>
                        <span className={`flex items-center gap-1 ${c.charge_sheet_present ? 'text-emerald-600' : 'text-red-600'}`}>
                          {c.charge_sheet_present ? <CheckCircle2 className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                          Charge Sheet: {c.charge_sheet_status}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                      <button
                        onClick={() => handleOpenUpdateModal(c)}
                        className="px-3 py-1.5 bg-secondary hover:bg-muted border border-border text-foreground font-mono text-xs font-semibold rounded-sm flex items-center gap-1"
                        title="Update Station Investigation Record"
                      >
                        <Edit3 className="w-3.5 h-3.5" /> Update Record
                      </button>
                      <button
                        onClick={() => openUploadModal(c.case_id)}
                        className="px-3 py-1.5 bg-secondary hover:bg-muted border border-border text-foreground font-mono text-xs font-semibold rounded-sm flex items-center gap-1"
                        title="Upload Police Record"
                      >
                        <Plus className="w-3.5 h-3.5" /> Submit Record
                      </button>
                      <button
                        onClick={() => handleOpenProvenance(c.case_id)}
                        className="px-3 py-1.5 bg-secondary hover:bg-muted border border-border text-foreground font-mono text-xs font-semibold rounded-sm flex items-center gap-1"
                        title="Police Record Provenance"
                      >
                        <ShieldAlert className="w-3.5 h-3.5 text-primary" /> Police Record Provenance
                      </button>
                      <Link
                        to={`/accused/${accusedOpaqueId}`}
                        className="px-3 py-1.5 bg-secondary hover:bg-muted border border-border text-foreground font-mono text-xs font-semibold rounded-sm flex items-center gap-1"
                        title="View Accused Dossier"
                      >
                        <UserCheck className="w-3.5 h-3.5" /> Profile
                      </Link>
                      <Link
                        to={`/case/${c.case_id}`}
                        className="px-3 py-1.5 bg-primary text-primary-foreground font-mono text-xs font-bold rounded-sm flex items-center gap-1 hover:opacity-90"
                      >
                        Case File <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Institutional Requests & Compliance */}
      {activeTab === "requests" && (
        <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
          <div className="p-4 border-b border-border bg-secondary/30">
            <h3 className="text-sm font-bold font-serif text-foreground uppercase">
              Pending Document & Production Tasks
            </h3>
            <p className="text-xs font-sans text-muted-foreground mt-0.5">
              Attested document requirements and court production notices directed to this police station.
            </p>
          </div>

          {loading ? (
            <div className="p-12 text-center text-xs font-mono text-muted-foreground flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
              <span>Loading institutional requests and compliance tasks...</span>
            </div>
          ) : actions.length === 0 ? (
            <div className="p-8 text-center text-xs font-mono text-muted-foreground">
              No outstanding document requests or court production tasks for this station.
            </div>
          ) : (
            <div className="divide-y divide-border">
              {actions.map((act) => {
                const isCompleted = act.status === "COMPLETED";
                const isAck = act.status === "ACKNOWLEDGED";

                return (
                  <div
                    key={act.id}
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-secondary/10"
                  >
                    <div className="space-y-1 max-w-2xl">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs font-mono text-primary">{act.id}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-secondary border border-border font-bold">
                          Case: {act.case_id}
                        </span>
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                            isCompleted
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                              : isAck
                              ? "bg-muted text-foreground border border-border"
                              : "bg-red-100 text-red-800 border border-red-300"
                          }`}
                        >
                          {act.status}
                        </span>
                        <span className="text-[10px] font-mono text-muted-foreground">
                          From: {act.requested_by || "DLSA_OFFICER"}
                        </span>
                      </div>

                      <div className="font-serif font-bold text-sm text-foreground">{act.title}</div>
                      {act.description && (
                        <p className="text-xs font-sans text-muted-foreground">{act.description}</p>
                      )}
                      {act.notes && (
                        <p className="text-xs font-mono text-foreground/80 italic">Notes: {act.notes}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                      {!isCompleted && !isAck && (
                        <button
                          onClick={() => handleAcknowledge(act.id)}
                          className="px-3 py-1.5 bg-secondary hover:bg-muted border border-border text-foreground font-mono text-xs font-semibold rounded-sm flex items-center gap-1"
                        >
                          <Check className="w-3.5 h-3.5" /> Acknowledge
                        </button>
                      )}
                      {!isCompleted && (
                        <button
                          onClick={() => openUploadModal(act.case_id, act.id, act.action_type.includes("CHARGE_SHEET") ? "charge_sheet" : "remand_application")}
                          className="px-3 py-1.5 bg-primary text-primary-foreground font-mono text-xs font-bold rounded-sm flex items-center gap-1 hover:opacity-90"
                        >
                          <Send className="w-3.5 h-3.5" /> Upload & Complete
                        </button>
                      )}
                      {isCompleted && (
                        <span className="text-xs font-mono text-emerald-600 font-bold flex items-center gap-1">
                          <CheckCircle2 className="w-4 h-4" /> Fulfilled
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Upload Police Record Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-card border-2 border-border w-full max-w-lg rounded-sm shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-primary" />
                <h3 className="text-sm font-serif font-bold uppercase text-foreground">
                  Upload Police Record
                </h3>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Target Case ID
                </label>
                <select
                  value={selectedCaseId}
                  onChange={(e) => setSelectedCaseId(e.target.value)}
                  className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  required
                >
                  {cases.map((c) => (
                    <option key={c.case_id} value={c.case_id}>
                      {c.case_id} — {c.name} ({c.fir_number})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Police Document Type
                </label>
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  required
                >
                  {POLICE_DOC_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Document File (PDF or Scanned Image)
                </label>
                <input
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,.tiff"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs font-mono bg-background border border-border p-1.5 rounded-sm"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Extracted / Attested Text (Optional Supplement)
                </label>
                <textarea
                  rows={3}
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  placeholder="Paste or enter attested investigation notes, charge summary, or remand details..."
                  className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="bg-secondary/40 p-3 rounded-sm text-xs font-sans text-muted-foreground space-y-1">
                <div>* Source Authority: <strong>Police Investigating Agency</strong></div>
                <div>* Docket Status: <strong>Deposited &amp; Awaiting Judicial File Confirmation</strong></div>
                <div>* Record Integrity: <strong>Digitally sealed and indexed in case docket</strong></div>
              </div>

              {uploadMsg && (
                <div
                  className={`p-3 rounded-sm text-xs font-mono ${
                    uploadMsg.type === "success"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-red-100 text-red-800 border border-red-300"
                  }`}
                >
                  {uploadMsg.text}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3 py-1.5 text-xs font-mono uppercase border border-border bg-secondary hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-4 py-1.5 text-xs font-mono uppercase bg-primary text-primary-foreground font-bold hover:opacity-90 disabled:opacity-50 flex items-center gap-1"
                >
                  {uploading ? "Submitting..." : "Submit Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Register Station FIR Modal */}
      {showFIRIntakeModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-card border-2 border-border w-full max-w-lg rounded-sm shadow-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-primary" />
                <h3 className="text-sm font-serif font-bold uppercase text-foreground">
                  Register Station FIR Docket
                </h3>
              </div>
              <button
                onClick={() => setShowFIRIntakeModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleFIRIntakeSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    FIR Number *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. FIR-2026-084"
                    value={firForm.fir_number}
                    onChange={(e) => setFirForm({ ...firForm, fir_number: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Accused Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ramesh Kumar"
                    value={firForm.accused_name}
                    onChange={(e) => setFirForm({ ...firForm, accused_name: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Offense Sections (comma-separated)
                </label>
                <input
                  type="text"
                  placeholder="e.g. BNS 303(2), BNS 317(2)"
                  value={firForm.offense_sections}
                  onChange={(e) => setFirForm({ ...firForm, offense_sections: e.target.value })}
                  className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Filing Date
                  </label>
                  <input
                    type="date"
                    value={firForm.filing_date}
                    onChange={(e) => setFirForm({ ...firForm, filing_date: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Arrest Date
                  </label>
                  <input
                    type="date"
                    value={firForm.arrest_date}
                    onChange={(e) => setFirForm({ ...firForm, arrest_date: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Producing Court
                  </label>
                  <input
                    type="text"
                    value={firForm.court_name}
                    onChange={(e) => setFirForm({ ...firForm, court_name: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Investigating Officer
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. SI Vikram Singh"
                    value={firForm.investigating_officer}
                    onChange={(e) => setFirForm({ ...firForm, investigating_officer: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Incident Summary / Initial Log
                </label>
                <textarea
                  rows={3}
                  value={firForm.incident_details}
                  onChange={(e) => setFirForm({ ...firForm, incident_details: e.target.value })}
                  placeholder="Summary of allegations and station intake notes..."
                  className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                />
              </div>

              <div className="bg-secondary/40 p-3 rounded-sm text-xs font-sans text-muted-foreground space-y-1">
                <div>* Designated Station: <strong>{user?.police_station || "Kotwali Police Station"}</strong></div>
                <div>* District Authority: <strong>{user?.district || "Central Delhi"}</strong></div>
                <div>* Legal Notification: <strong>DLSA legal aid desk will be automatically notified upon intake</strong></div>
              </div>

              {firMsg && (
                <div
                  className={`p-3 rounded-sm text-xs font-mono ${
                    firMsg.type === "success"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-red-100 text-red-800 border border-red-300"
                  }`}
                >
                  {firMsg.text}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowFIRIntakeModal(false)}
                  className="px-3 py-1.5 text-xs font-mono uppercase border border-border bg-secondary hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={firSubmitting}
                  className="px-4 py-1.5 text-xs font-mono uppercase bg-primary text-primary-foreground font-bold hover:opacity-90 disabled:opacity-50 flex items-center gap-1"
                >
                  {firSubmitting ? "Registering..." : "Register FIR"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Update Investigation Record Modal */}
      {showFIRUpdateModal && updateCaseTarget && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-card border-2 border-border w-full max-w-lg rounded-sm shadow-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-primary" />
                <h3 className="text-sm font-serif font-bold uppercase text-foreground">
                  Update Investigation Record // {updateCaseTarget.case_id}
                </h3>
              </div>
              <button
                onClick={() => setShowFIRUpdateModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleFIRUpdateSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Accused / Matter
                </label>
                <div className="p-2 bg-secondary/50 border border-border text-xs font-mono rounded-sm">
                  {updateCaseTarget.name} — FIR: {updateCaseTarget.fir_number || "Not Recorded"}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Amended Offense Sections (comma-separated)
                </label>
                <input
                  type="text"
                  value={updateForm.offense_sections}
                  onChange={(e) => setUpdateForm({ ...updateForm, offense_sections: e.target.value })}
                  className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Charge Sheet Status
                  </label>
                  <select
                    value={updateForm.charge_sheet_status}
                    onChange={(e) => setUpdateForm({ ...updateForm, charge_sheet_status: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  >
                    <option value="PENDING_INVESTIGATION">Pending Investigation</option>
                    <option value="DRAFT_PREPARED">Draft Prepared</option>
                    <option value="SUBMITTED_TO_COURT">Submitted to Court</option>
                    <option value="FILED_IN_REGISTRY">Filed in Registry</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Remand Status
                  </label>
                  <select
                    value={updateForm.remand_status}
                    onChange={(e) => setUpdateForm({ ...updateForm, remand_status: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  >
                    <option value="INITIAL_REMAND">Initial Remand</option>
                    <option value="EXTENDED_POLICE_CUSTODY">Extended Police Custody</option>
                    <option value="TRANSFERRED_TO_JUDICIAL_CUSTODY">Transferred to Judicial Custody</option>
                    <option value="AVAILABLE_ON_RECORD">Available on Record</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Competent Court
                  </label>
                  <input
                    type="text"
                    value={updateForm.court_name}
                    onChange={(e) => setUpdateForm({ ...updateForm, court_name: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                    Investigating Officer
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Insp. Vikram Singh"
                    value={updateForm.investigating_officer}
                    onChange={(e) => setUpdateForm({ ...updateForm, investigating_officer: e.target.value })}
                    className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-muted-foreground uppercase mb-1">
                  Investigation Log / Case Diary Extract
                </label>
                <textarea
                  rows={3}
                  value={updateForm.investigation_notes}
                  onChange={(e) => setUpdateForm({ ...updateForm, investigation_notes: e.target.value })}
                  placeholder="Record formal case diary entry or investigation update..."
                  className="w-full text-xs font-mono bg-background border border-border p-2 rounded-sm"
                />
              </div>

              <div className="bg-secondary/40 p-3 rounded-sm text-xs font-sans text-muted-foreground space-y-1">
                <div>* Provenance: <strong>Station Case Diary Update</strong></div>
                <div>* Verification: <strong>Recorded with timestamp and officer attribution</strong></div>
              </div>

              {updateMsg && (
                <div
                  className={`p-3 rounded-sm text-xs font-mono ${
                    updateMsg.type === "success"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-red-100 text-red-800 border border-red-300"
                  }`}
                >
                  {updateMsg.text}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowFIRUpdateModal(false)}
                  className="px-3 py-1.5 text-xs font-mono uppercase border border-border bg-secondary hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateSubmitting}
                  className="px-4 py-1.5 text-xs font-mono uppercase bg-primary text-primary-foreground font-bold hover:opacity-90 disabled:opacity-50 flex items-center gap-1"
                >
                  {updateSubmitting ? "Updating..." : "Update Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Role-Specific Police Record Provenance Modal */}
      <RoleEvidenceProvenanceModal
        isOpen={!!provenanceModalCaseId}
        onClose={() => setProvenanceModalCaseId(null)}
        data={provenanceData}
        loading={provenanceLoading}
      />
    </div>
  );
}
