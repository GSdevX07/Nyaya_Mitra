import { useState, useEffect } from "react";
import {
  Building2, AlertTriangle, CheckCircle2,
  Search, Plus, ChevronRight, Send, X, FileText, Loader2
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  fetchJailInmates,
  referJailCaseToDlsa,
  uploadDocumentFile,
  fetchEvidenceChain,
  type JailInmateRecord
} from "../lib/api";
import { RoleEvidenceProvenanceModal } from "../components/RoleEvidenceProvenanceModal";

const PRISON_DOC_TYPES = [
  { value: "prison_admission_record", label: "Prison Admission Record" },
  { value: "custody_certificate", label: "Custody Certificate / Nominal Roll" },
  { value: "remand_order", label: "Remand Order Copy (Prison Held)" },
  { value: "prison_conduct_record", label: "Prison Conduct & Discipline Record" },
  { value: "medical_certificate", label: "Prison Medical Screening Certificate" },
  { value: "other_prison_record", label: "Other Authorized Prison Custody Record" },
];

export function JailWorkspace() {
  const [inmates, setInmates] = useState<JailInmateRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [referringId, setReferringId] = useState<string | null>(null);
  const [referralSuccess, setReferralSuccess] = useState<string | null>(null);

  // Upload Modal State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [selectedDocType, setSelectedDocType] = useState<string>("prison_admission_record");
  const [customText, setCustomText] = useState<string>("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Provenance Modal State
  const [provenanceModalCaseId, setProvenanceModalCaseId] = useState<string | null>(null);
  const [provenanceData, setProvenanceData] = useState<any>(null);
  const [provenanceLoading, setProvenanceLoading] = useState(false);

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

  const loadJailInmates = async () => {
    setLoading(true);
    try {
      const data = await fetchJailInmates();
      setInmates(data || []);
      if (data && data.length > 0 && !selectedCaseId) {
        setSelectedCaseId(data[0].inmate_id);
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

  const handleReferToDlsa = async (inmateId: string) => {
    setReferringId(inmateId);
    setReferralSuccess(null);
    try {
      await referJailCaseToDlsa(inmateId, "Formal legal-aid counsel assignment referral from Jail Superintendent.");
      setReferralSuccess(`Inmate ${inmateId} successfully referred to DLSA.`);
      await loadJailInmates();
    } catch (err: any) {
      alert(`Referral failed: ${err.message}`);
    } finally {
      setReferringId(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCaseId) {
      setUploadError("Please select an inmate record.");
      return;
    }
    if (!uploadFile && !customText.trim()) {
      setUploadError("Please choose a file or enter intake notes.");
      return;
    }

    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocumentFile(
        selectedCaseId,
        selectedDocType,
        uploadFile || undefined,
        customText.trim() || undefined
      );
      setShowUploadModal(false);
      setCustomText("");
      setUploadFile(null);
      await loadJailInmates();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload intake record.");
    } finally {
      setUploading(false);
    }
  };

  const filteredInmates = inmates.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.inmate_id.toLowerCase().includes(q) ||
      c.jail_location?.toLowerCase().includes(q)
    );
  });

  const docMissingCases = inmates.filter((c) => !c.is_docs_complete);
  const assignedCount = inmates.filter((c) => c.assignment_status === "ASSIGNED").length;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Prison Department & Custody Desk // Facility Operations
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Jail Inmate Custody & Legal Records Desk
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Track undertrial custody days, verify detention records, manage prison document intake, and coordinate legal aid representation for all admitted prisoners.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" /> Upload Intake Record
          </button>
        </div>
      </div>

      {referralSuccess && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300 rounded-sm text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>{referralSuccess}</span>
          </div>
          <button onClick={() => setReferralSuccess(null)} className="text-muted-foreground hover:text-foreground">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Facility Inmates Tracked</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{inmates.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">Authorized Facility Population</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Missing Prison Records</div>
          <div className="text-2xl font-serif font-bold text-amber-600 mt-1">{docMissingCases.length}</div>
          <div className="text-[10px] font-mono text-amber-600 mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Nominal roll / Remand copy required
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">DLSA Counsel Assigned</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
            {assignedCount} / {inmates.length}
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1">
            {assignedCount === inmates.length ? "Full Legal Aid Coverage" : `${inmates.length - assignedCount} Pending Assignment`}
          </div>
        </div>
      </div>

      {/* Custody List */}
      <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <span className="font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
            Facility Undertrial Custody Roll ({filteredInmates.length} active inmates)
          </span>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search inmate name or ID..."
              className="w-full pl-9 pr-3 py-1.5 bg-input border border-border text-xs font-mono rounded-sm focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {loading ? (
          <div className="p-8 text-center text-muted-foreground text-xs font-mono">
            Loading facility inmate custody roll...
          </div>
        ) : filteredInmates.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground text-xs font-mono">
            No active inmates matching your query in this facility.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredInmates.map((c) => {
              const isAssigned = c.assignment_status === "ASSIGNED";
              return (
                <div key={c.inmate_id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                        {c.inmate_id}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground">
                        {c.jail_location}
                      </span>
                      {c.potential_479_eligible && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                          Potential Sec 479 Threshold
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                      <span>Admission Date: <strong className="text-foreground">{c.admission_date}</strong></span>
                      <span>•</span>
                      <span>Calendar Custody: <strong className="text-foreground">{c.custody_days}d</strong></span>
                      <span>•</span>
                      <span>Delay Exclusions: <strong className="text-foreground">{c.excluded_delay_days || 0}d</strong></span>
                      <span>•</span>
                      <span>Countable Days: <strong className="text-primary font-bold">{c.countable_days}d</strong></span>
                    </div>

                    {/* Legal Aid Status Badge */}
                    <div className="pt-1 flex items-center gap-2 text-xs font-mono">
                      {isAssigned ? (
                        <span className="text-emerald-700 dark:text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> DLSA Counsel: {c.assigned_lawyer || "Assigned"}
                        </span>
                      ) : (
                        <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                          <AlertTriangle className="w-3.5 h-3.5" /> Legal-Aid Representation Pending
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    {!isAssigned && (
                      <button
                        onClick={() => handleReferToDlsa(c.inmate_id)}
                        disabled={referringId === c.inmate_id}
                        className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 border border-border rounded-sm text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
                        title="Flag legal-aid requirement to DLSA for counsel assignment"
                      >
                        {referringId === c.inmate_id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : (
                          <Send className="w-3 h-3 text-primary" />
                        )}
                        Refer to DLSA
                      </button>
                    )}

                    {!c.is_docs_complete ? (
                      <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-amber-500/10 text-amber-600 border border-amber-500/20 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" /> Missing Records ({c.missing_docs.length})
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" /> Records Complete
                      </span>
                    )}

                    <button
                      onClick={() => handleOpenProvenance(c.inmate_id)}
                      className="px-2.5 py-1.5 text-xs font-semibold rounded-sm bg-secondary hover:bg-secondary/80 text-foreground border border-border flex items-center gap-1 transition-colors"
                      title="Inspect Document Verification & Provenance"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" /> Document Verification &amp; Provenance
                    </button>

                    <Link
                      to={`/case/${c.inmate_id}`}
                      className="px-3 py-1.5 bg-primary text-primary-foreground rounded-sm text-xs font-serif font-semibold flex items-center gap-1"
                    >
                      View Dossier <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Upload Intake Record Modal */}
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

            {uploadError && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 text-red-700 dark:text-red-300 rounded-sm text-xs font-mono">
                {uploadError}
              </div>
            )}

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                  Select Inmate
                </label>
                <select
                  value={selectedCaseId}
                  onChange={(e) => setSelectedCaseId(e.target.value)}
                  className="w-full p-2 bg-input border border-border text-xs font-mono rounded-sm focus:outline-none focus:border-primary"
                >
                  {inmates.map((i) => (
                    <option key={i.inmate_id} value={i.inmate_id}>
                      {i.name} ({i.inmate_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                  Prison Document Category
                </label>
                <select
                  value={selectedDocType}
                  onChange={(e) => setSelectedDocType(e.target.value)}
                  className="w-full p-2 bg-input border border-border text-xs font-mono rounded-sm focus:outline-none focus:border-primary"
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
                <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                  Document File (PDF / Scanned Image)
                </label>
                <input
                  type="file"
                  accept=".pdf,image/*"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="w-full p-2 bg-input border border-border text-xs font-mono rounded-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-muted-foreground mb-1">
                  Custody Intake Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  placeholder="Enter custody dates, medical screening notes, or intake remarks..."
                  className="w-full p-2 bg-input border border-border text-xs font-mono rounded-sm focus:outline-none focus:border-primary"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border border-border rounded-sm text-xs font-mono hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-sm text-xs font-mono font-bold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
                >
                  {uploading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Submit Intake Record
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
