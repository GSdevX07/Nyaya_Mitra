import { useState, useEffect } from "react";
import {
  Building2,
  AlertTriangle,
  CheckCircle2,
  Search,
  Plus,
  ChevronRight,
  Send,
  X,
  FileText,
  Loader2,
  UserPlus,
  History,
  ShieldAlert,
  UserCheck,
  KeyRound,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  fetchJailInmates,
  referJailCaseToDlsa,
  uploadDocumentFile,
  fetchEvidenceChain,
  intakeCustodyRecordApi,
  recordCustodyEventApi,
  updateAccusedProfileApi,
  confirmPrisonReleaseApi,
  type JailInmateRecord,
  type CustodyIntakePayload,
  type CustodyEventPayload,
  type AccusedProfileUpdatePayload,
  type PrisonReleasePayload,
} from "../lib/api";
import { RoleEvidenceProvenanceModal } from "../components/RoleEvidenceProvenanceModal";
import { UniversalTaskQueue } from "../components/UniversalTaskQueue";
import { useAuth } from "../lib/auth";

const PRISON_DOC_TYPES = [
  { value: "prison_admission_record", label: "Prison Admission Record" },
  { value: "custody_certificate", label: "Custody Certificate / Nominal Roll" },
  { value: "remand_order", label: "Remand Order Copy (Prison Held)" },
  { value: "prison_conduct_record", label: "Prison Conduct & Discipline Record" },
  { value: "medical_certificate", label: "Prison Medical Screening Certificate" },
  { value: "other_prison_record", label: "Other Authorized Prison Custody Record" },
];

const CUSTODY_EVENT_TYPES = [
  { value: "REMAND_EXTENSION", label: "Remand Extension (Judicial Custody)" },
  { value: "COURT_PRODUCTION", label: "Physical / Video Court Production" },
  { value: "TRANSFER", label: "Inter-Prison Facility Transfer" },
  { value: "MEDICAL_EXAM", label: "Specialist Medical Examination" },
  { value: "SEARCH_AND_SEIZURE", label: "Custody Inventory & Search" },
];

export function JailWorkspace() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<"queue" | "inmates">("queue");
  const [inmates, setInmates] = useState<JailInmateRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "missing_docs" | "sec_479" | "unassigned">("all");
  const [referringId, setReferringId] = useState<string | null>(null);
  const [bannerNotice, setBannerNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Modals
  const [showIntakeModal, setShowIntakeModal] = useState(false);
  const [showEventModal, setShowEventModal] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showReleaseModal, setShowReleaseModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Modal targeted inmate
  const [targetCaseId, setTargetCaseId] = useState<string>("");

  // Submitting states
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Intake form state
  const [intakeForm, setIntakeForm] = useState<CustodyIntakePayload>({
    name: "",
    facility_id: user?.facility_ids?.[0] || "",
    facility_name: "",
    district: user?.district || "",
    court_name: "",
    arrest_date: new Date().toISOString().split("T")[0],
    admission_date: new Date().toISOString().split("T")[0],
    offense_sections: [],
    refer_to_dlsa: true,
    notes: "",
  });
  const [offenseSectionsInput, setOffenseSectionsInput] = useState("");

  // Custody Event form state
  const [eventForm, setEventForm] = useState<CustodyEventPayload>({
    event_type: "REMAND_EXTENSION",
    event_date: new Date().toISOString().split("T")[0],
    court_name: "",
    notes: "",
    verified: true,
  });

  // Profile Update form state
  const [profileForm, setProfileForm] = useState<AccusedProfileUpdatePayload>({
    father_name: "",
    date_of_birth: "",
    age: undefined,
    gender: "Male",
    permanent_address: "",
    contact_number: "",
    emergency_family_contact_name: "",
    emergency_family_contact_phone: "",
    emergency_family_contact_relation: "",
  });

  // Release Confirmation form state
  const [releaseForm, setReleaseForm] = useState<PrisonReleasePayload>({
    release_date: new Date().toISOString().split("T")[0],
    gate_pass_number: `GP-${Math.floor(100000 + Math.random() * 900000)}`,
    surety_verification_ref: "SURETY-VERIF-OK-2026",
    superintendent_notes: "Bail bond verified and accepted. Accused physically released from custody gate.",
  });

  // Upload modal state
  const [selectedDocType, setSelectedDocType] = useState<string>("prison_admission_record");
  const [customText, setCustomText] = useState<string>("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  // Provenance modal state
  const [provenanceModalCaseId, setProvenanceModalCaseId] = useState<string | null>(null);
  const [provenanceData, setProvenanceData] = useState<any>(null);
  const [provenanceLoading, setProvenanceLoading] = useState(false);

  const loadJailInmates = async () => {
    setLoading(true);
    try {
      const data = await fetchJailInmates();
      setInmates(data || []);
      if (data && data.length > 0 && !targetCaseId) {
        setTargetCaseId(data[0].inmate_id);
      }
    } catch (err) {
      console.error("Failed to load jail inmates:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJailInmates();
  }, []);

  const handleOpenProvenance = async (inmateId: string) => {
    setProvenanceModalCaseId(inmateId);
    setProvenanceLoading(true);
    try {
      const data = await fetchEvidenceChain(inmateId);
      setProvenanceData(data);
    } catch (err) {
      console.error("Failed to load provenance:", err);
    } finally {
      setProvenanceLoading(false);
    }
  };

  const handleReferToDlsa = async (inmateId: string) => {
    setReferringId(inmateId);
    try {
      await referJailCaseToDlsa(inmateId, "Formal legal-aid counsel assignment referral from Jail Superintendent.");
      setBannerNotice({
        type: "success",
        message: `Inmate ${inmateId} successfully referred to District Legal Services Authority (DLSA).`,
      });
      await loadJailInmates();
    } catch (err: any) {
      setBannerNotice({
        type: "error",
        message: `Referral failed: ${err.message}`,
      });
    } finally {
      setReferringId(null);
    }
  };

  // 1. Submit New Custody Intake
  const handleSubmitIntake = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      const sections = offenseSectionsInput
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await intakeCustodyRecordApi({
        ...intakeForm,
        offense_sections: sections.length > 0 ? sections : ["BNS 303(2)"],
      });
      setShowIntakeModal(false);
      setBannerNotice({
        type: "success",
        message: `New inmate ${intakeForm.name} admitted and authoritative custody record created.`,
      });
      await loadJailInmates();
    } catch (err: any) {
      setFormError(err.message || "Failed to intake custody record.");
    } finally {
      setSubmitting(false);
    }
  };

  // 2. Submit Custody Event
  const handleSubmitEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetCaseId) {
      setFormError("Please select an inmate record.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await recordCustodyEventApi(targetCaseId, eventForm);
      setShowEventModal(false);
      setBannerNotice({
        type: "success",
        message: `Custody event (${eventForm.event_type}) recorded for inmate ${targetCaseId}.`,
      });
      await loadJailInmates();
    } catch (err: any) {
      setFormError(err.message || "Failed to record custody event.");
    } finally {
      setSubmitting(false);
    }
  };

  // 3. Submit Profile Update
  const handleSubmitProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetCaseId) {
      setFormError("Please select an inmate record.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await updateAccusedProfileApi(targetCaseId, profileForm);
      setShowProfileModal(false);
      setBannerNotice({
        type: "success",
        message: `Accused profile and family contact data updated for ${targetCaseId}.`,
      });
      await loadJailInmates();
    } catch (err: any) {
      setFormError(err.message || "Failed to update profile.");
    } finally {
      setSubmitting(false);
    }
  };

  // 4. Submit Prison Release Confirmation
  const handleSubmitRelease = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetCaseId) {
      setFormError("Please select an inmate record.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await confirmPrisonReleaseApi(targetCaseId, releaseForm);
      setShowReleaseModal(false);
      setBannerNotice({
        type: "success",
        message: `Physical release confirmed for ${targetCaseId}. Gate pass ${releaseForm.gate_pass_number} logged in immutable ledger.`,
      });
      await loadJailInmates();
    } catch (err: any) {
      setFormError(err.message || "Failed to confirm release.");
    } finally {
      setSubmitting(false);
    }
  };

  // 5. Submit Document Upload
  const handleSubmitUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetCaseId) {
      setFormError("Please select an inmate record.");
      return;
    }
    if (!uploadFile && !customText.trim()) {
      setFormError("Please choose a file or enter intake notes.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      await uploadDocumentFile(
        targetCaseId,
        selectedDocType,
        uploadFile || undefined,
        customText.trim() || undefined
      );
      setShowUploadModal(false);
      setCustomText("");
      setUploadFile(null);
      setBannerNotice({
        type: "success",
        message: `Prison custody document uploaded for inmate ${targetCaseId}.`,
      });
      await loadJailInmates();
    } catch (err: any) {
      setFormError(err.message || "Failed to upload prison document.");
    } finally {
      setSubmitting(false);
    }
  };

  const filteredInmates = inmates.filter((c) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      c.name.toLowerCase().includes(q) ||
      c.inmate_id.toLowerCase().includes(q) ||
      c.jail_location?.toLowerCase().includes(q);

    if (!matchesSearch) return false;

    if (statusFilter === "missing_docs") return !c.is_docs_complete;
    if (statusFilter === "sec_479") return !!c.potential_479_eligible;
    if (statusFilter === "unassigned") return c.assignment_status !== "ASSIGNED";
    return true;
  });

  const docMissingCases = inmates.filter((c) => !c.is_docs_complete);
  const eligible479Cases = inmates.filter((c) => c.potential_479_eligible);
  const assignedCount = inmates.filter((c) => c.assignment_status === "ASSIGNED").length;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Facility Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Prison Department & Custody Desk // Facility Operations
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Jail Inmate Custody & Operations Workbench
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Admit undertrials, log verified remand extensions and transfers, capture missing inmate profile attributes, and execute physical release upon judicial bail orders.
          </p>
        </div>

        {/* Action Buttons for Jail Officers */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => {
              setFormError(null);
              setShowIntakeModal(true);
            }}
            className="px-3.5 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity shadow-sm"
          >
            <UserPlus className="w-4 h-4" /> Intake Inmate
          </button>

          <button
            onClick={() => {
              setFormError(null);
              setShowEventModal(true);
            }}
            className="px-3 py-2 bg-secondary text-foreground hover:bg-secondary/80 border border-border font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 transition-colors"
          >
            <History className="w-4 h-4 text-primary" /> Log Custody Event
          </button>

          <button
            onClick={() => {
              setFormError(null);
              setShowUploadModal(true);
            }}
            className="px-3 py-2 bg-secondary text-foreground hover:bg-secondary/80 border border-border font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 transition-colors"
          >
            <Plus className="w-4 h-4 text-primary" /> Upload Prison Doc
          </button>
        </div>
      </div>

      {/* Banner Notice */}
      {bannerNotice && (
        <div
          className={`p-3.5 border rounded-sm text-xs font-mono flex items-center justify-between ${
            bannerNotice.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {bannerNotice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span>{bannerNotice.message}</span>
          </div>
          <button
            onClick={() => setBannerNotice(null)}
            className="text-muted-foreground hover:text-foreground ml-2"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Facility Population</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{inmates.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">Authorized Custody Roll</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Sec 479 Thresholds</div>
          <div className="text-2xl font-serif font-bold text-red-600 mt-1">{eligible479Cases.length}</div>
          <div className="text-[10px] font-mono text-red-600 mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Potential Statutory Bail
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Incomplete Records</div>
          <div className="text-2xl font-serif font-bold text-rose-600 mt-1">{docMissingCases.length}</div>
          <div className="text-[10px] font-mono text-rose-600 mt-1">Nominal Roll / Remand Order Needed</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">DLSA Counsel Assigned</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
            {assignedCount} / {inmates.length}
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1">
            {inmates.length - assignedCount > 0 ? `${inmates.length - assignedCount} Pending Referral` : "100% Coverage"}
          </div>
        </div>
      </div>

      {/* Primary Tab Switcher */}
      <div className="flex items-center gap-2 border-b-2 border-border pb-2">
        <button
          onClick={() => setActiveTab("queue")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "queue"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="w-4 h-4" />
          Custody Operations Queue
        </button>

        <button
          onClick={() => setActiveTab("inmates")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "inmates"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserCheck className="w-4 h-4" />
          Facility Inmate Population Roll ({inmates.length})
        </button>
      </div>

      {/* TAB 1: Universal Task Queue */}
      {activeTab === "queue" && (
        <div className="space-y-4">
          <UniversalTaskQueue
            initialFilter={{ owner_role: "JAIL_OFFICER" }}
            title="Custody Desk Operational Tasks"
            subtitle="Prioritized custody actions, missing prison records, remand extension schedules, and physical discharge confirmations."
          />
        </div>
      )}

      {/* TAB 2: Inmate Population Roll */}
      {activeTab === "inmates" && (
        <div className="bg-card border-2 border-border rounded-sm overflow-hidden space-y-0">
          {/* Controls Bar */}
          <div className="p-4 border-b border-border bg-secondary/40 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground mr-2">
                Filter Roll:
              </span>
              {(
                [
                  { id: "all", label: `All (${inmates.length})` },
                  { id: "missing_docs", label: `Missing Docs (${docMissingCases.length})` },
                  { id: "sec_479", label: `Sec 479 Threshold (${eligible479Cases.length})` },
                  { id: "unassigned", label: `Pending DLSA (${inmates.length - assignedCount})` },
                ] as const
              ).map((f) => (
                <button
                  key={f.id}
                  onClick={() => setStatusFilter(f.id)}
                  className={`px-2.5 py-1 text-xs font-mono rounded-sm border transition-colors ${
                    statusFilter === f.id
                      ? "bg-primary text-primary-foreground border-primary font-bold"
                      : "bg-card text-muted-foreground border-border hover:bg-secondary"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="relative w-full md:w-72">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search inmate name, ID, location..."
                className="w-full pl-9 pr-3 py-1.5 bg-input border border-border text-xs font-mono rounded-sm focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {loading ? (
            <div className="p-12 text-center text-muted-foreground text-xs font-mono flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-primary" /> Loading facility inmate custody roll...
            </div>
          ) : filteredInmates.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground text-xs font-mono">
              No inmate records matching the selected criteria.
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredInmates.map((c) => {
                const isAssigned = c.assignment_status === "ASSIGNED";
                return (
                  <div
                    key={c.inmate_id}
                    className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                  >
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                          {c.inmate_id}
                        </span>
                        <span className="text-xs font-mono text-muted-foreground">
                          {c.jail_location}
                        </span>
                        {c.potential_479_eligible && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-red-500/10 text-red-600 dark:text-red-400 border border-border">
                            Sec 479 Threshold Met
                          </span>
                        )}
                        {!c.is_docs_complete && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20">
                            Missing Prison Docs ({c.missing_docs?.length || 1})
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                        <span>Admission: <strong className="text-foreground">{c.admission_date}</strong></span>
                        <span>•</span>
                        <span>Calendar Custody: <strong className="text-foreground">{c.custody_days}d</strong></span>
                        <span>•</span>
                        <span>Delay Exclusions: <strong className="text-foreground">{c.excluded_delay_days || 0}d</strong></span>
                        <span>•</span>
                        <span>Countable Custody: <strong className="text-primary font-bold">{c.countable_days}d</strong></span>
                      </div>

                      <div className="pt-1 flex flex-wrap items-center gap-3 text-xs font-mono">
                        {isAssigned ? (
                          <span className="text-emerald-700 dark:text-emerald-400 font-semibold flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> DLSA Counsel: {c.assigned_lawyer || "Assigned"}
                          </span>
                        ) : (
                          <span className="text-red-600 dark:text-red-400 flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" /> Legal-Aid Representation Pending
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Operational Action Gateways */}
                    <div className="flex flex-wrap items-center gap-2">
                      {!isAssigned && (
                        <button
                          onClick={() => handleReferToDlsa(c.inmate_id)}
                          disabled={referringId === c.inmate_id}
                          className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 border border-border rounded-sm text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
                          title="Refer inmate to DLSA for legal-aid counsel assignment"
                        >
                          {referringId === c.inmate_id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Send className="w-3.5 h-3.5 text-primary" />
                          )}
                          Refer to DLSA
                        </button>
                      )}

                      <button
                        onClick={() => {
                          setTargetCaseId(c.inmate_id);
                          setFormError(null);
                          setShowEventModal(true);
                        }}
                        className="px-2.5 py-1.5 text-xs font-mono font-semibold rounded-sm bg-secondary hover:bg-secondary/80 text-foreground border border-border flex items-center gap-1 transition-colors"
                        title="Log remand extension, court appearance, or transfer"
                      >
                        <History className="w-3.5 h-3.5 text-primary" /> Log Event
                      </button>

                      <button
                        onClick={() => {
                          setTargetCaseId(c.inmate_id);
                          setFormError(null);
                          setShowProfileModal(true);
                        }}
                        className="px-2.5 py-1.5 text-xs font-mono font-semibold rounded-sm bg-secondary hover:bg-secondary/80 text-foreground border border-border flex items-center gap-1 transition-colors"
                        title="Update accused permanent address, phone, and emergency relative contacts"
                      >
                        <UserCheck className="w-3.5 h-3.5 text-primary" /> Update Profile
                      </button>

                      <button
                        onClick={() => {
                          setTargetCaseId(c.inmate_id);
                          setFormError(null);
                          setShowReleaseModal(true);
                        }}
                        className="px-2.5 py-1.5 text-xs font-mono font-semibold rounded-sm bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 flex items-center gap-1 transition-colors"
                        title="Confirm physical discharge from prison facility"
                      >
                        <KeyRound className="w-3.5 h-3.5 text-emerald-600" /> Release Gate
                      </button>

                      <button
                        onClick={() => handleOpenProvenance(c.inmate_id)}
                        className="px-2.5 py-1.5 text-xs font-mono font-semibold rounded-sm bg-secondary hover:bg-secondary/80 text-foreground border border-border flex items-center gap-1 transition-colors"
                        title="Inspect Document Verification & Provenance"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-primary" /> Provenance
                      </button>

                      <Link
                        to={`/case/${c.inmate_id}`}
                        className="px-3 py-1.5 bg-primary text-primary-foreground rounded-sm text-xs font-serif font-semibold flex items-center gap-1 hover:opacity-90 transition-opacity"
                      >
                        Dossier <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* MODAL 1: Intake New Inmate Record */}
      {showIntakeModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-xl w-full shadow-lg space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-primary" />
                <h3 className="text-base font-serif font-bold uppercase">Custody Intake & Accused Admission</h3>
              </div>
              <button onClick={() => setShowIntakeModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-sm text-xs font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmitIntake} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Inmate Full Name *</label>
                  <input
                    type="text"
                    required
                    value={intakeForm.name}
                    onChange={(e) => setIntakeForm({ ...intakeForm, name: e.target.value })}
                    placeholder="e.g. Ramesh Kumar"
                    className="w-full p-2 bg-input border border-border rounded-sm focus:outline-none focus:border-primary font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Correctional Facility ID</label>
                  <input
                    type="text"
                    value={intakeForm.facility_id}
                    onChange={(e) => setIntakeForm({ ...intakeForm, facility_id: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Judicial District</label>
                  <input
                    type="text"
                    value={intakeForm.district}
                    onChange={(e) => setIntakeForm({ ...intakeForm, district: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Remand Court Name</label>
                  <input
                    type="text"
                    value={intakeForm.court_name}
                    onChange={(e) => setIntakeForm({ ...intakeForm, court_name: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Arrest Date *</label>
                  <input
                    type="date"
                    required
                    value={intakeForm.arrest_date}
                    onChange={(e) => setIntakeForm({ ...intakeForm, arrest_date: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Prison Admission Date</label>
                  <input
                    type="date"
                    value={intakeForm.admission_date}
                    onChange={(e) => setIntakeForm({ ...intakeForm, admission_date: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">
                  Charged Offenses (Comma separated) *
                </label>
                <input
                  type="text"
                  required
                  value={offenseSectionsInput}
                  onChange={(e) => setOffenseSectionsInput(e.target.value)}
                  placeholder="e.g. BNS 303(2), BNS 317"
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="refer_dlsa"
                  checked={intakeForm.refer_to_dlsa}
                  onChange={(e) => setIntakeForm({ ...intakeForm, refer_to_dlsa: e.target.checked })}
                  className="rounded border-border"
                />
                <label htmlFor="refer_dlsa" className="text-foreground cursor-pointer">
                  Immediately Flag Legal-Aid Requirement to DLSA Panel Desk
                </label>
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Intake Remarks / Physical Health Notes</label>
                <textarea
                  rows={2}
                  value={intakeForm.notes}
                  onChange={(e) => setIntakeForm({ ...intakeForm, notes: e.target.value })}
                  placeholder="Initial physical screening, identification marks, property seized..."
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowIntakeModal(false)}
                  className="px-4 py-2 border border-border rounded-sm hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-sm flex items-center gap-1.5 hover:opacity-90"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm Admission Intake
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Record Custody Event */}
      {showEventModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-lg w-full shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-primary" />
                <h3 className="text-base font-serif font-bold uppercase">Record Custody Event</h3>
              </div>
              <button onClick={() => setShowEventModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-sm text-xs font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmitEvent} className="space-y-4 text-xs font-mono">
              <div>
                <label className="block uppercase text-muted-foreground mb-1">Target Inmate Record *</label>
                <select
                  value={targetCaseId}
                  onChange={(e) => setTargetCaseId(e.target.value)}
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                >
                  {inmates.map((i) => (
                    <option key={i.inmate_id} value={i.inmate_id}>
                      {i.name} ({i.inmate_id}) — {i.jail_location}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Event Category *</label>
                  <select
                    value={eventForm.event_type}
                    onChange={(e) => setEventForm({ ...eventForm, event_type: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  >
                    {CUSTODY_EVENT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Event Date *</label>
                  <input
                    type="date"
                    required
                    value={eventForm.event_date}
                    onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Competent Court / Jurisdiction</label>
                <input
                  type="text"
                  value={eventForm.court_name || ""}
                  onChange={(e) => setEventForm({ ...eventForm, court_name: e.target.value })}
                  placeholder="e.g. Chief Metropolitan Magistrate Court No. 3"
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Event Record &amp; Judicial Reference *</label>
                <textarea
                  rows={3}
                  required
                  value={eventForm.notes}
                  onChange={(e) => setEventForm({ ...eventForm, notes: e.target.value })}
                  placeholder="Record remand warrant reference number, escort details, or medical findings..."
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="verified_event"
                  checked={eventForm.verified}
                  onChange={(e) => setEventForm({ ...eventForm, verified: e.target.checked })}
                  className="rounded border-border"
                />
                <label htmlFor="verified_event" className="text-foreground cursor-pointer">
                  Certified by Prison Record Clerk / Duty Superintendent
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowEventModal(false)}
                  className="px-4 py-2 border border-border rounded-sm hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-sm flex items-center gap-1.5 hover:opacity-90"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Record Event
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Update Accused Profile & Family Contacts */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-xl w-full shadow-lg space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-primary" />
                <h3 className="text-base font-serif font-bold uppercase">Update Inmate Profile &amp; Relative Contacts</h3>
              </div>
              <button onClick={() => setShowProfileModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-sm text-xs font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmitProfile} className="space-y-4 text-xs font-mono">
              <div>
                <label className="block uppercase text-muted-foreground mb-1">Inmate Record *</label>
                <select
                  value={targetCaseId}
                  onChange={(e) => setTargetCaseId(e.target.value)}
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                >
                  {inmates.map((i) => (
                    <option key={i.inmate_id} value={i.inmate_id}>
                      {i.name} ({i.inmate_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Father / Guardian Name</label>
                  <input
                    type="text"
                    value={profileForm.father_name || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, father_name: e.target.value })}
                    placeholder="e.g. Sh. Mohan Lal"
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Gender</label>
                  <select
                    value={profileForm.gender || "Male"}
                    onChange={(e) => setProfileForm({ ...profileForm, gender: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Transgender">Transgender</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Age</label>
                  <input
                    type="number"
                    value={profileForm.age ?? ""}
                    onChange={(e) => setProfileForm({ ...profileForm, age: e.target.value ? parseInt(e.target.value) : undefined })}
                    placeholder="e.g. 28"
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Primary Phone</label>
                  <input
                    type="text"
                    value={profileForm.contact_number || ""}
                    onChange={(e) => setProfileForm({ ...profileForm, contact_number: e.target.value })}
                    placeholder="+91 98765 43210"
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Permanent Residential Address</label>
                <textarea
                  rows={2}
                  value={profileForm.permanent_address || ""}
                  onChange={(e) => setProfileForm({ ...profileForm, permanent_address: e.target.value })}
                  placeholder="Village / Ward, District, State, PIN..."
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div className="border-t border-border pt-3 space-y-3">
                <span className="block font-bold uppercase text-primary text-[11px]">Emergency Family / Guardian Contact</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block uppercase text-muted-foreground mb-1">Relative Name</label>
                    <input
                      type="text"
                      value={profileForm.emergency_family_contact_name || ""}
                      onChange={(e) => setProfileForm({ ...profileForm, emergency_family_contact_name: e.target.value })}
                      placeholder="e.g. Smt. Sunita Devi"
                      className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                    />
                  </div>

                  <div>
                    <label className="block uppercase text-muted-foreground mb-1">Relationship</label>
                    <input
                      type="text"
                      value={profileForm.emergency_family_contact_relation || ""}
                      onChange={(e) => setProfileForm({ ...profileForm, emergency_family_contact_relation: e.target.value })}
                      placeholder="e.g. Mother / Brother"
                      className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                    />
                  </div>

                  <div>
                    <label className="block uppercase text-muted-foreground mb-1">Relative Phone</label>
                    <input
                      type="text"
                      value={profileForm.emergency_family_contact_phone || ""}
                      onChange={(e) => setProfileForm({ ...profileForm, emergency_family_contact_phone: e.target.value })}
                      placeholder="+91 98765 11223"
                      className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="px-4 py-2 border border-border rounded-sm hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-sm flex items-center gap-1.5 hover:opacity-90"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Save Inmate Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: Confirm Physical Release */}
      {showReleaseModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-lg w-full shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <KeyRound className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-serif font-bold uppercase">Confirm Physical Prison Release</h3>
              </div>
              <button onClick={() => setShowReleaseModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 rounded-sm text-xs font-mono flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                <strong>Consequential Action:</strong> Physical prison release marks the conclusion of custody and moves the matter into post-release preservation. Ensure the competent court bail order and surety verification have been certified.
              </span>
            </div>

            {formError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-sm text-xs font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmitRelease} className="space-y-4 text-xs font-mono">
              <div>
                <label className="block uppercase text-muted-foreground mb-1">Inmate Record *</label>
                <select
                  value={targetCaseId}
                  onChange={(e) => setTargetCaseId(e.target.value)}
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                >
                  {inmates.map((i) => (
                    <option key={i.inmate_id} value={i.inmate_id}>
                      {i.name} ({i.inmate_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Physical Discharge Date *</label>
                  <input
                    type="date"
                    required
                    value={releaseForm.release_date}
                    onChange={(e) => setReleaseForm({ ...releaseForm, release_date: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>

                <div>
                  <label className="block uppercase text-muted-foreground mb-1">Gate Pass / Discharge Memo Ref *</label>
                  <input
                    type="text"
                    required
                    value={releaseForm.gate_pass_number}
                    onChange={(e) => setReleaseForm({ ...releaseForm, gate_pass_number: e.target.value })}
                    className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Surety Verification Record Ref</label>
                <input
                  type="text"
                  value={releaseForm.surety_verification_ref || ""}
                  onChange={(e) => setReleaseForm({ ...releaseForm, surety_verification_ref: e.target.value })}
                  placeholder="e.g. SURETY-VERIF-DELHI-449"
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Superintendent Release Endorsement Notes</label>
                <textarea
                  rows={2}
                  value={releaseForm.superintendent_notes || ""}
                  onChange={(e) => setReleaseForm({ ...releaseForm, superintendent_notes: e.target.value })}
                  placeholder="Release memo verified against judicial order. Prisoner discharged with personal effects..."
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowReleaseModal(false)}
                  className="px-4 py-2 border border-border rounded-sm hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-emerald-600 text-white font-bold rounded-sm flex items-center gap-1.5 hover:bg-emerald-700"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Confirm Physical Discharge
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 5: Upload Prison Custody Record */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-lg w-full shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-primary" />
                <h3 className="text-base font-serif font-bold uppercase">Upload Prison Intake Record</h3>
              </div>
              <button onClick={() => setShowUploadModal(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-sm text-xs font-mono">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmitUpload} className="space-y-4 text-xs font-mono">
              <div>
                <label className="block uppercase text-muted-foreground mb-1">Select Inmate *</label>
                <select
                  value={targetCaseId}
                  onChange={(e) => setTargetCaseId(e.target.value)}
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                >
                  {inmates.map((i) => (
                    <option key={i.inmate_id} value={i.inmate_id}>
                      {i.name} ({i.inmate_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Prison Document Category *</label>
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                >
                  {PRISON_DOC_TYPES.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                </select>
                <p className="text-[10px] font-mono text-muted-foreground mt-1">
                  Authoritative origin: PRISON // Stored as PENDING_VERIFICATION until validated.
                </p>
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">
                  Document File (PDF / Scanned Image)
                </label>
                <input
                  type="file"
                  accept=".pdf,image/*"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div>
                <label className="block uppercase text-muted-foreground mb-1">Custody Intake Notes (Optional)</label>
                <textarea
                  rows={3}
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  placeholder="Enter custody dates, medical screening notes, or intake remarks..."
                  className="w-full p-2 bg-input border border-border rounded-sm font-mono text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border border-border rounded-sm hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-primary text-primary-foreground font-bold rounded-sm flex items-center gap-1.5 hover:opacity-90"
                >
                  {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Submit Prison Document
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Role-Specific Document Verification & Provenance Modal */}
      <RoleEvidenceProvenanceModal
        isOpen={!!provenanceModalCaseId}
        onClose={() => setProvenanceModalCaseId(null)}
        data={provenanceData}
        loading={provenanceLoading}
      />
    </div>
  );
}
