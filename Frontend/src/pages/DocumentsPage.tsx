import { useState, useEffect, useRef, useCallback } from "react";
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Search,
  Plus,
  ShieldCheck,
  X,
  Loader2,
  FileScan,
  GitBranch,
  CheckCheck,
  Clock,
} from "lucide-react";
import {
  fetchDocuments,
  fetchCases,
  uploadDocumentFile,
  fetchEvidenceChain,
  reprocessDocument,
  downloadSecureDocument,
  verifyUploadedDocument,
  reviewUploadedDocument,
  getUploadedDocuments,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  RoleEvidenceProvenanceModal,
  getEvidenceChainButtonLabel,
} from "../components/RoleEvidenceProvenanceModal";

interface DocItem {
  id: string;
  actual_doc_id?: string;
  case_id: string;
  case_reference?: string;
  prisoner_name: string;
  document_category?: string;
  document_type: string;
  raw_document_type?: string;
  status: string;
  verification_status?: string;
  document_status?: string;
  is_present: boolean;
  uploaded_by?: string;
  uploaded_by_id?: string;
  uploaded_date?: string;
  source_authority?: string;
  file_hash?: string;
  file_name?: string;
  jail_location: string;
  district?: string;
}

interface UploadResult {
  status: string;
  message: string;
  document_id?: string;
  version_number?: number;
  is_handwritten: boolean;
  ocr_engine: string;
  ocr_confidence?: number;
  manual_verification_required?: boolean;
  needs_human_verification_reason?: string;
  extracted_text: string;
  extracted_fields_with_spans?: Record<string, any>;
  file_name: string;
  file_size_bytes: number;
  file_hash: string;
  security_scan_status?: string;
  is_complete: boolean;
  present_docs: string[];
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/bmp",
  "image/tiff",
  "image/gif",
  "image/heic",
];

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export const STANDARD_DOC_TYPES = [
  { value: "fir", label: "First Information Report (FIR)" },
  { value: "charge_sheet", label: "Charge Sheet / Final Police Report" },
  { value: "remand_order", label: "Remand / Detention Order" },
  { value: "custody_certificate", label: "Custody Certificate" },
  { value: "nominal_roll", label: "Nominal Roll (Prison Record)" },
  { value: "prison_admission_record", label: "Prison Admission Record" },
  { value: "medical_certificate", label: "Medical Examination Record" },
  { value: "case_diary_extract", label: "Case Diary Extract" },
  { value: "arrest_memo", label: "Arrest Memo / Panchnama" },
  { value: "supervisory_review_note", label: "Supervisory Review Note" },
  { value: "other_record", label: "Other Official Case Document" },
];

export function getRoleAllowedDocTypes(role?: string) {
  switch (role) {
    case "JAIL_OFFICER":
      return [
        { value: "custody_certificate", label: "Custody Certificate (Prison Record)" },
        { value: "nominal_roll", label: "Nominal Roll (Prison Record)" },
        { value: "prison_admission_record", label: "Prison Admission Record" },
        { value: "medical_certificate", label: "Medical Examination Record" },
        { value: "remand_order", label: "Remand / Detention Order Copy (Prison Held)" },
        { value: "other_prison_record", label: "Other Official Prison Record" },
      ];
    case "POLICE_OFFICER":
      return [
        { value: "fir", label: "First Information Report (FIR)" },
        { value: "charge_sheet", label: "Charge Sheet / Final Police Report" },
        { value: "arrest_memo", label: "Arrest Memo / Inspection Report" },
        { value: "case_diary_extract", label: "Case Diary Extract" },
        { value: "remand_application", label: "Police Remand Application" },
        { value: "seizure_memo", label: "Seizure & Panchnama Memo" },
        { value: "police_status_report", label: "Police Status / Compliance Report" },
      ];
    case "DLSA_OFFICER":
      return [
        { value: "charge_sheet", label: "Charge Sheet / Final Report (Intake Copy)" },
        { value: "fir", label: "FIR Copy (Legal-Aid Intake)" },
        { value: "remand_order", label: "Remand / Detention Order Copy" },
        { value: "custody_certificate", label: "Custody Certificate Copy" },
        { value: "nominal_roll", label: "Nominal Roll Copy" },
        { value: "dlsa_application", label: "DLSA Legal Aid Application" },
        { value: "trial_court_judgment", label: "Trial Court Order / Judgment" },
      ];
    case "DEFENSE_ADVOCATE":
    case "CONTROLLED_EXTERNAL_ADVOCATE":
      return [
        { value: "bail_application", label: "Bail Petition / Legal Motion Draft" },
        { value: "vakalatnama", label: "Vakalatnama / Memo of Appearance" },
        { value: "defense_representation", label: "Written Legal Submission / Notes" },
        { value: "trial_court_judgment", label: "Trial Court Order / Certified Copy" },
      ];
    default:
      return STANDARD_DOC_TYPES;
  }
}

export function DocumentsPage() {
  const { user } = useAuth();
  const canReview = user?.role === "SUPERVISING_LEGAL_OFFICER" || user?.role === "DLSA_OFFICER" || user?.role === "DEFENSE_ADVOCATE" || user?.role === "PLATFORM_ADMIN";

  const [docs, setDocs] = useState<DocItem[]>([]);
  const [availableCases, setAvailableCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [uploadCaseId, setUploadCaseId] = useState("");
  const [uploadDocType, setUploadDocType] = useState("");
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [topFeedback, setTopFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Evidence Chain Inspector state
  const [evidenceChainModalDoc, setEvidenceChainModalDoc] = useState<string | null>(null);
  const [evidenceChainData, setEvidenceChainData] = useState<any | null>(null);
  const [chainLoading, setChainLoading] = useState(false);

  // Upload modal state
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customText, setCustomText] = useState("");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const data = await fetchDocuments();
      setDocs(data || []);
    } catch (err: any) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocs();
    fetchCases()
      .then((casesData) => {
        const flat = (casesData || []).map((item: any) => item.case || item).filter(Boolean);
        setAvailableCases(flat);
      })
      .catch((err) => console.warn("Could not prefetch cases list:", err));
  }, []);

  const resetModal = () => {
    setSelectedFile(null);
    setCustomText("");
    setUploadResult(null);
    setUploadError("");
    setDragOver(false);
  };

  const openModal = (caseId?: string, docType?: string) => {
    resetModal();
    if (caseId) setUploadCaseId(caseId);
    if (docType) setUploadDocType(docType);
    setShowUploadModal(true);
  };

  const closeModal = () => {
    setShowUploadModal(false);
    resetModal();
  };

  // Open Evidence Chain Inspector
  const handleOpenEvidenceChain = async (docIdOrCaseId: string, docType?: string) => {
    setChainLoading(true);
    setEvidenceChainModalDoc(docIdOrCaseId);
    setEvidenceChainData(null);
    try {
      let targetDocId = docIdOrCaseId;
      if (docIdOrCaseId.startsWith("UTP-") || docIdOrCaseId.startsWith("CASE-") || docIdOrCaseId.startsWith("DOC-") || docIdOrCaseId.startsWith("CONV-") || docIdOrCaseId.startsWith("REL-")) {
        let caseRef = docIdOrCaseId;
        if (docIdOrCaseId.startsWith("DOC-")) {
          const parts = docIdOrCaseId.split("-");
          if (parts.length >= 3) {
            caseRef = `${parts[1]}-${parts[2]}`;
          }
        }
        try {
          const uploadedList = await getUploadedDocuments(caseRef);
          if (docType && uploadedList.length > 0) {
            const cleanType = docType.toLowerCase().trim().replace(/ /g, "_");
            const match = uploadedList.find((u: any) => (u.document_type || "").toLowerCase().replace(/ /g, "_") === cleanType);
            if (match) targetDocId = match.id;
            else targetDocId = uploadedList[0].id;
          } else if (uploadedList.length > 0) {
            targetDocId = uploadedList[0].id;
          }
        } catch (e) {
          // Fall back to original targetDocId
        }
      }
      const data = await fetchEvidenceChain(targetDocId);
      setEvidenceChainData(data);
    } catch (err: any) {
      console.error("Failed to load evidence chain:", err);
      setTopFeedback({ type: "error", message: `Document verification record: ${err.message || err}` });
    } finally {
      setChainLoading(false);
    }
  };

  // Direct In-line Review (for DLSA Officer)
  const handleReviewDirect = async (docId: string) => {
    try {
      await reviewUploadedDocument(docId);
      await loadDocs();
      setTopFeedback({
        type: "success",
        message: "Document marked reviewed for legal-aid intake processing.",
      });
    } catch (err: any) {
      setTopFeedback({
        type: "error",
        message: `Document review failed: ${err.message || err}`,
      });
    }
  };

  // Direct In-line Verification (for Supervising Legal Officer)
  const handleVerifyDirect = async (docId: string) => {
    try {
      await verifyUploadedDocument(docId);
      await loadDocs();
      setTopFeedback({
        type: "success",
        message: "Document successfully verified and authorized! Case completeness updated.",
      });
    } catch (err: any) {
      setTopFeedback({
        type: "error",
        message: `Document verification failed: ${err.message || err}`,
      });
    }
  };

  // Submit Field Correction
  // Reprocess Document
  const handleReprocess = async (docId: string) => {
    if (!confirm("Reprocess document to generate Version N+1? Prior version will remain immutable.")) return;
    setChainLoading(true);
    try {
      await reprocessDocument(docId, { reason: "User requested re-extraction" });
      const refreshed = await fetchEvidenceChain(docId);
      setEvidenceChainData(refreshed);
    } catch (err: any) {
      alert(err.message || "Reprocessing failed.");
    } finally {
      setChainLoading(false);
    }
  };

  // Verify Legal Document

  const handleVerify = async (docId: string) => {
    if (!confirm("Verify and authorize this legal document? This will confirm presence and update case completeness.")) return;
    setChainLoading(true);
    try {
      await verifyUploadedDocument(docId);
      const refreshed = await fetchEvidenceChain(docId);
      setEvidenceChainData(refreshed);
      await loadDocs();
      setTopFeedback({
        type: "success",
        message: "Document successfully verified and authorized! Case completeness updated.",
      });
    } catch (err: any) {
      alert(err.message || "Document verification failed.");
    } finally {
      setChainLoading(false);
    }
  };

  // Review Legal Document (for DLSA Officer in Modal)
  const handleReview = async (docId: string) => {
    setChainLoading(true);
    try {
      await reviewUploadedDocument(docId);
      const refreshed = await fetchEvidenceChain(docId);
      setEvidenceChainData(refreshed);
      await loadDocs();
      setTopFeedback({
        type: "success",
        message: "Document marked reviewed for legal-aid intake processing.",
      });
    } catch (err: any) {
      alert(err.message || "Document review failed.");
    } finally {
      setChainLoading(false);
    }
  };

  // Secure File Download
  const handleDownload = async (docId: string, fileName: string) => {
    try {
      const blob = await downloadSecureDocument(docId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName || "document.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setTopFeedback({
        type: "success",
        message: `Secure download initiated for '${fileName || "document.pdf"}'.`,
      });
    } catch (err: any) {
      setTopFeedback({
        type: "error",
        message: err.message || "Secure download failed. Access may be restricted to your jurisdiction or role.",
      });
    }
  };

  // Drag-and-drop handlers
  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);
  const onDragLeave = useCallback(() => setDragOver(false), []);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }, []);

  const handleFileSelect = (file: File) => {
    setUploadError("");
    setUploadResult(null);
    const isValid =
      ACCEPTED_TYPES.includes(file.type) ||
      file.name.match(/\.(pdf|jpg|jpeg|png|webp|bmp|tiff?|gif|heic)$/i);
    if (!isValid) {
      setUploadError("Unsupported file format. Please upload a PDF or image (JPG, PNG, WEBP, TIFF, BMP).");
      return;
    }
    setSelectedFile(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadCaseId) {
      setUploadError("Please select a Case Reference.");
      return;
    }
    if (!uploadDocType) {
      setUploadError("Please select a Document Type.");
      return;
    }
    if (!selectedFile && !customText.trim()) {
      setUploadError("Please upload a file or paste text before submitting.");
      return;
    }
    setUploading(true);
    setUploadError("");
    try {
      const result = await uploadDocumentFile(
        uploadCaseId,
        uploadDocType,
        selectedFile ?? undefined,
        customText.trim() || undefined
      );
      closeModal();
      await loadDocs();
      setTopFeedback({
        type: "success",
        message: `Document "${result.file_name || uploadDocType}" uploaded successfully for Case ${uploadCaseId}! Status: Pending Verification.`,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed. Please try again.";
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  };

  const filtered = docs.filter(
    d =>
      d.case_id.toLowerCase().includes(search.toLowerCase()) ||
      d.document_type.toLowerCase().includes(search.toLowerCase()) ||
      d.prisoner_name.toLowerCase().includes(search.toLowerCase()) ||
      (d.uploaded_by && d.uploaded_by.toLowerCase().includes(search.toLowerCase()))
  );

  const presentCount = docs.filter(d => d.is_present || d.document_status === "VERIFIED").length;
  const missingCount = docs.filter(d => !d.is_present && d.document_status !== "VERIFIED").length;

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-sm text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              Evidence-Aware Document Service
            </span>
            <span className="text-xs text-muted-foreground font-mono">Magic Bytes & Security Screening Active</span>
          </div>
          <h1 className="text-3xl font-serif font-black tracking-tight text-foreground">
            Legal Records & Evidence Vault
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Official judicial document vault with tamper-evident cryptographic sealing, statutory completeness tracking, and BSA Sec 63 compliance where applicable.
          </p>
        </div>

        <button
          onClick={() => openModal()}
          className="px-4 py-2 bg-primary text-primary-foreground font-semibold rounded text-sm hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-primary/20"
        >
          <Plus className="w-4 h-4" /> Upload Document
        </button>
      </div>

      {topFeedback && (
        <div
          className={`p-4 rounded-xl text-xs font-mono flex items-center justify-between shadow-sm ${
            topFeedback.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-600"
              : "bg-destructive/10 border border-destructive/30 text-destructive"
          }`}
        >
          <span className="flex items-center gap-2">
            {topFeedback.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
            {topFeedback.message}
          </span>
          <button
            onClick={() => setTopFeedback(null)}
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl bg-card shadow-sm border border-border flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-serif font-bold text-foreground">{docs.length}</div>
            <div className="text-xs text-muted-foreground font-medium">Monitored Institutional Filings</div>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-card shadow-sm border border-border flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-serif font-bold text-foreground">{presentCount}</div>
            <div className="text-xs text-muted-foreground font-medium">Verified & Screened Present</div>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-card shadow-sm border border-border flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-600">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-serif font-bold text-foreground">{missingCount}</div>
            <div className="text-xs text-muted-foreground font-medium">Missing Procedural Records</div>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
        <input
          type="text"
          placeholder="Search document vault by case ID, doc type, or prisoner..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded text-sm text-foreground focus:outline-none focus:border-primary"
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse font-mono text-sm">
          Loading document inventory from FastAPI service...
        </div>
      ) : (
        <div className="bg-card shadow-sm border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-muted-foreground">
              <thead className="bg-secondary/40 text-xs font-semibold text-foreground uppercase border-b border-border">
                <tr>
                  <th className="px-6 py-4">Case ID</th>
                  <th className="px-6 py-4">Document Type</th>
                  <th className="px-6 py-4">Prisoner Record</th>
                  <th className="px-6 py-4">Verification Status</th>
                  <th className="px-6 py-4">Uploaded By / Provenance</th>
                  <th className="px-6 py-4">Facility</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map(d => (
                  <tr key={d.id} className="hover:bg-secondary/20 transition-colors">
                    <td className="px-6 py-4 font-mono text-primary font-bold">{d.case_id}</td>
                    <td className="px-6 py-4 text-foreground font-medium">
                      <div>{d.document_type}</div>
                      {d.file_name && <div className="text-[10px] font-mono text-muted-foreground truncate max-w-[150px]">{d.file_name}</div>}
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">{d.prisoner_name}</td>
                    <td className="px-6 py-4">
                      {d.document_status === "VERIFIED" || (d.is_present && d.document_status !== "PENDING_VERIFICATION" && d.document_status !== "REVIEWED") ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Present & Verified
                        </span>
                      ) : d.document_status === "REVIEWED" ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-600 border border-blue-500/30">
                          <CheckCheck className="w-3.5 h-3.5" /> Reviewed (Intake)
                        </span>
                      ) : d.document_status === "PENDING_VERIFICATION" ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-600 border border-amber-500/30">
                          <Clock className="w-3.5 h-3.5" /> Pending Verification
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-secondary text-muted-foreground border border-border">
                          <AlertTriangle className="w-3.5 h-3.5" /> Missing
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-xs">
                        <div className="font-semibold text-foreground">{d.uploaded_by || (d.is_present ? "Court Registry" : "Not Uploaded")}</div>
                        {d.uploaded_date && (
                          <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                            {d.uploaded_date.includes("T") ? new Date(d.uploaded_date).toLocaleDateString() : d.uploaded_date}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs">{d.jail_location}</td>
                    <td className="px-6 py-4 text-right space-x-2">
                      {d.document_status === "PENDING_VERIFICATION" || (d.document_status === "REVIEWED" && user?.role === "SUPERVISING_LEGAL_OFFICER") ? (
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          <button
                            onClick={() => handleOpenEvidenceChain(d.actual_doc_id || d.id, d.document_type)}
                            className="px-2.5 py-1 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-semibold border border-primary/20 transition-colors inline-flex items-center gap-1 shadow-sm"
                            title={`Inspect ${getEvidenceChainButtonLabel(user?.role)}`}
                          >
                            <GitBranch className="w-3.5 h-3.5" /> {getEvidenceChainButtonLabel(user?.role)}
                          </button>
                          {user?.role === "DLSA_OFFICER" && d.document_status === "PENDING_VERIFICATION" && (
                            <button
                              onClick={() => handleReviewDirect(d.actual_doc_id || d.id)}
                              className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition-colors inline-flex items-center gap-1 shadow-sm"
                              title="Mark reviewed for legal-aid intake processing"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" /> Review Document
                            </button>
                          )}
                          {user?.role === "SUPERVISING_LEGAL_OFFICER" && (
                            <button
                              onClick={() => handleVerifyDirect(d.actual_doc_id || d.id)}
                              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition-colors inline-flex items-center gap-1 shadow-sm"
                              title="Supervisory verification: confirm presence and update case completeness"
                            >
                              <CheckCheck className="w-3.5 h-3.5" /> Supervisory Verify
                            </button>
                          )}
                        </div>
                      ) : d.is_present || d.document_status === "VERIFIED" || d.document_status === "REVIEWED" ? (
                        <button
                          onClick={() => handleOpenEvidenceChain(d.actual_doc_id || d.id, d.document_type)}
                          className="px-3 py-1 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-semibold border border-primary/20 transition-colors inline-flex items-center gap-1.5 shadow-sm"
                          title={`Inspect ${getEvidenceChainButtonLabel(user?.role)}`}
                        >
                          <GitBranch className="w-3.5 h-3.5" /> {getEvidenceChainButtonLabel(user?.role)}
                        </button>
                      ) : (
                        <button
                          onClick={() => openModal(d.case_id, d.raw_document_type || d.document_type.toLowerCase().replace(/ /g, "_"))}
                          className="px-3 py-1 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-xs font-semibold transition-colors inline-flex items-center gap-1 shadow-sm"
                        >
                          <Upload className="w-3.5 h-3.5" /> Upload
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      {/* Role-Specific Evidence Chain & Provenance Inspector Modal */}
      <RoleEvidenceProvenanceModal
        isOpen={!!evidenceChainModalDoc}
        onClose={() => setEvidenceChainModalDoc(null)}
        data={evidenceChainData}
        loading={chainLoading}
        onDownload={handleDownload}
        onVerify={handleVerify}
        onReview={handleReview}
        onReprocess={handleReprocess}
        canReview={canReview}
      />


      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div
            className="w-full max-w-2xl bg-card border border-border rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
            style={{ boxShadow: "0 0 60px rgba(99,102,241,0.15)" }}
          >
            {/* Modal Header */}
            <div className="px-7 py-5 border-b border-border flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center">
                  <FileScan className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h3 className="text-base font-serif font-bold text-foreground">Secure Evidence Upload</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Official court document intake, automated screening & case file indexing
                  </p>
                </div>
              </div>
              <button
                onClick={closeModal}
                className="w-8 h-8 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-7 py-6 space-y-6 overflow-y-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5 font-medium">Case Reference *</label>
                  <select
                    required
                    value={uploadCaseId}
                    onChange={e => setUploadCaseId(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-secondary/50 border border-border rounded-xl text-sm font-mono text-foreground focus:outline-none focus:border-primary"
                  >
                    <option value="">Select Case Reference...</option>
                    {availableCases.map((item: any) => {
                      const c = item.case || item;
                      const caseId = c.case_id || c.id;
                      if (!caseId) return null;
                      const inmateName = c.name || c.prisoner_name || c.accused_name || "Undertrial Inmate";
                      const dist = c.district || c.jail_location || "Central Delhi";
                      return (
                        <option key={caseId} value={caseId}>
                          {caseId} — {inmateName} ({dist})
                        </option>
                      );
                    })}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5 font-medium">Document Type *</label>
                  <select
                    required
                    value={uploadDocType}
                    onChange={e => setUploadDocType(e.target.value)}
                    className="w-full px-3.5 py-2.5 bg-secondary/50 border border-border rounded-xl text-sm font-mono text-foreground focus:outline-none focus:border-primary"
                  >
                    <option value="">Select Document Type...</option>
                    {getRoleAllowedDocTypes(user?.role).map(dt => (
                      <option key={dt.value} value={dt.value}>
                        {dt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Drag & Drop File Zone */}
              <div>
                <label className="text-xs text-muted-foreground block mb-1.5 font-medium">
                  Document File (PDF / Image &mdash; Max 25MB)
                </label>
                <div
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                  onDrop={onDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
                    dragOver
                      ? "border-primary bg-primary/10 scale-[1.01]"
                      : selectedFile
                      ? "border-emerald-500/50 bg-emerald-500/5"
                      : "border-border hover:border-primary/50 hover:bg-secondary/30"
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.webp,.bmp,.tiff,.tif,.gif,.heic"
                    className="hidden"
                    onChange={e => {
                      const f = e.target.files?.[0];
                      if (f) handleFileSelect(f);
                    }}
                  />
                  {selectedFile ? (
                    <div className="flex items-center justify-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-primary/15 border border-primary/30 flex items-center justify-center">
                        <FileText className="w-5 h-5 text-primary" />
                      </div>
                      <div className="text-left">
                        <div className="text-sm font-semibold text-foreground">{selectedFile.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {formatBytes(selectedFile.size)} &bull; {selectedFile.type || "binary"}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Upload className="w-8 h-8 text-primary mx-auto opacity-70" />
                      <div className="text-sm font-semibold text-foreground">
                        Drop document here or click to browse
                      </div>
                      <div className="text-xs text-muted-foreground">
                        PDF, PNG, JPG, WEBP &bull; Cryptographically Verified & Sealed with SHA-256
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Error Message */}
              {uploadError && (
                <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-xl flex items-start gap-3 text-destructive text-xs">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Upload Result Preview */}
              {uploadResult && (
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center gap-2 text-emerald-600 font-bold">
                    <CheckCircle2 className="w-4 h-4" /> Document Intake &amp; Verification Successful!
                  </div>
                  {user?.role === "PLATFORM_ADMIN" ? (
                    <div className="grid grid-cols-2 gap-2 text-muted-foreground font-mono">
                      <div>Engine: <span className="text-foreground">{uploadResult.ocr_engine}</span></div>
                      <div>Conf: <span className="text-foreground">{Math.round((uploadResult.ocr_confidence || 1) * 100)}%</span></div>
                      <div>SHA-256: <span className="text-foreground">{uploadResult.file_hash?.substring(0, 16)}...</span></div>
                      <div>Screening: <span className="text-foreground">{uploadResult.security_scan_status || "PASSED"}</span></div>
                    </div>
                  ) : (
                    <div className="text-muted-foreground font-sans space-y-1">
                      <div>Document Status: <span className="text-foreground font-semibold">Official Court Record Linked</span></div>
                      <div>Digital Seal: <span className="text-emerald-600 font-semibold">Cryptographically Sealed (BSA Sec 63 where applicable)</span></div>
                    </div>
                  )}
                </div>
              )}

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-5 py-2.5 bg-primary text-primary-foreground rounded-xl text-xs font-bold shadow-lg shadow-primary/20 hover:bg-primary/90 flex items-center gap-2"
                >
                  {uploading && <Loader2 className="w-4 h-4 animate-spin" />}
                  {uploading ? "Screening & Extracting..." : "Upload & Screen Document"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
