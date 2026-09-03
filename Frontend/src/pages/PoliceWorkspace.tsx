import { useState, useEffect } from "react";
import {
  ShieldAlert, AlertTriangle, CheckCircle2,
  Search, Plus, ChevronRight, FileText, UserCheck, Check,
  Clock, Send, X, Inbox, Loader2
} from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import {
  fetchPoliceCases,
  fetchPoliceActions,
  acknowledgePoliceAction,
  completePoliceAction,
  uploadDocumentFile,
  type PoliceCaseSummary,
  type PoliceActionItem
} from "../lib/api";

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
        await completePoliceAction(
          linkedActionId,
          result.file_hash || `doc_${Date.now()}`,
          `Submitted by station IO. Ref: ${selectedDocType}`
        );
      }

      setUploadMsg({
        text: "Official police document deposited successfully. Awaiting judicial verification on court file.",
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
            onClick={() => openUploadModal()}
            className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
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
          <div className="text-2xl font-serif font-bold text-amber-600 mt-1">{chargesheetPending.length}</div>
          <div className="text-[10px] font-mono text-amber-600/80 mt-1">Pending Source Record</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Remand Record Status</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">{remandAvailable.length}</div>
          <div className="text-[10px] font-mono text-emerald-600/80 mt-1">Available on Record</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Institutional Requests</div>
          <div className="text-2xl font-serif font-bold text-indigo-600 mt-1">{pendingActions.length}</div>
          <div className="text-[10px] font-mono text-indigo-600/80 mt-1">DLSA & Court Inquiries</div>
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
                        <span className={`flex items-center gap-1 ${c.remand_order_present ? 'text-emerald-600' : 'text-amber-600'}`}>
                          {c.remand_order_present ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                          Remand Record: {c.remand_status}
                        </span>
                        <span className={`flex items-center gap-1 ${c.charge_sheet_present ? 'text-emerald-600' : 'text-amber-600'}`}>
                          {c.charge_sheet_present ? <CheckCircle2 className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                          Charge Sheet: {c.charge_sheet_status}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                      <button
                        onClick={() => openUploadModal(c.case_id)}
                        className="px-3 py-1.5 bg-secondary hover:bg-muted border border-border text-foreground font-mono text-xs font-semibold rounded-sm flex items-center gap-1"
                        title="Upload Police Record"
                      >
                        <Plus className="w-3.5 h-3.5" /> Submit Record
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
                              ? "bg-blue-100 text-blue-800 border border-blue-300"
                              : "bg-amber-100 text-amber-800 border border-amber-300"
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
    </div>
  );
}
