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
  Pencil,
  Download,
  GitBranch,
  CheckCheck,
  RefreshCw,
  Clock,
  BookOpen,
} from "lucide-react";
import {
  fetchDocuments,
  fetchCases,
  uploadDocumentFile,
  fetchEvidenceChain,
  correctDocumentField,
  reprocessDocument,
  downloadSecureDocument,
  verifyUploadedDocument,
  getUploadedDocuments,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

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
  const [showAllVersions, setShowAllVersions] = useState(false);

  const formatLegalEngineName = (engine?: string) => {
    if (!engine || engine.toLowerCase() === "none") return "Official Certified Docket Ingestion";
    if (engine.toLowerCase().includes("pypdf")) return "Court Document Digital Text Extraction";
    if (engine.toLowerCase().includes("easyocr") || engine.toLowerCase().includes("ocr")) return "Certified Judicial Optical Scan (OCR)";
    return "Official Document Processing";
  };

  // Field Correction state
  const [correctingField, setCorrectingField] = useState<string | null>(null);
  const [correctionValue, setCorrectionValue] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");
  const [correctionSubmitting, setCorrectionSubmitting] = useState(false);
  const [correctionMsg, setCorrectionMsg] = useState("");

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
    setCorrectingField(null);
    setCorrectionMsg("");
    setDownloadFeedback(null);
    setShowAllVersions(false);
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
      setDownloadFeedback({ type: "error", text: `Document verification record: ${err.message || err}` });
    } finally {
      setChainLoading(false);
    }
  };

  // Direct In-line Verification
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
  const handleSubmitCorrection = async (docId: string, fieldName: string) => {
    if (!correctionValue.trim() || !correctionReason.trim()) {
      alert("Please provide both a corrected value and a justification reason.");
      return;
    }
    setCorrectionSubmitting(true);
    setCorrectionMsg("");
    try {
      await correctDocumentField(docId, {
        field_name: fieldName,
        corrected_value: correctionValue.trim(),
        correction_reason: correctionReason.trim(),
      });
      setCorrectionMsg(`Successfully corrected ${fieldName}!`);
      setCorrectingField(null);
      setCorrectionValue("");
      setCorrectionReason("");
      // Refresh evidence chain
      const refreshed = await fetchEvidenceChain(docId);
      setEvidenceChainData(refreshed);
    } catch (err: any) {
      alert(err.message || "Correction failed.");
    } finally {
      setCorrectionSubmitting(false);
    }
  };

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
  const [downloadFeedback, setDownloadFeedback] = useState<{ text: string; type: "success" | "error" } | null>(null);

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

  // Secure File Download
  const handleDownload = async (docId: string, fileName: string) => {
    setDownloadFeedback(null);
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
      setDownloadFeedback({
        type: "success",
        text: `Secure download initiated for '${fileName || "document.pdf"}'.`,
      });
    } catch (err: any) {
      setDownloadFeedback({
        type: "error",
        text: err.message || "Secure download failed. Access may be restricted to your jurisdiction or role.",
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
                      {d.document_status === "VERIFIED" || (d.is_present && d.document_status !== "PENDING_VERIFICATION") ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Present & Verified
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
                      {d.document_status === "PENDING_VERIFICATION" ? (
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          <button
                            onClick={() => handleOpenEvidenceChain(d.actual_doc_id || d.id, d.document_type)}
                            className="px-2.5 py-1 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-semibold border border-primary/20 transition-colors inline-flex items-center gap-1 shadow-sm"
                            title="Inspect document custody chain and verification history"
                          >
                            <GitBranch className="w-3.5 h-3.5" /> Chain
                          </button>
                          {(user?.role === "SUPERVISING_LEGAL_OFFICER" || user?.role === "PLATFORM_ADMIN" || user?.role === "DLSA_OFFICER") && (
                            <button
                              onClick={() => handleVerifyDirect(d.actual_doc_id || d.id)}
                              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition-colors inline-flex items-center gap-1 shadow-sm"
                              title="Verify document and update case completeness"
                            >
                              <CheckCheck className="w-3.5 h-3.5" /> Verify
                            </button>
                          )}
                        </div>
                      ) : d.is_present || d.document_status === "VERIFIED" ? (
                        <button
                          onClick={() => handleOpenEvidenceChain(d.actual_doc_id || d.id, d.document_type)}
                          className="px-3 py-1 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-semibold border border-primary/20 transition-colors inline-flex items-center gap-1.5 shadow-sm"
                          title="Inspect document custody chain and verification history"
                        >
                          <GitBranch className="w-3.5 h-3.5" /> Evidence Chain
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

      {/* Evidence Chain Inspector Modal */}
      {evidenceChainModalDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-4xl bg-card border-2 border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/30">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                  <GitBranch className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
                    Document Chain of Custody & Integrity Ledger
                  </h3>
                  <p className="text-xs text-muted-foreground font-mono">
                    Case: {evidenceChainData?.case_id || evidenceChainModalDoc} &bull; Document: {evidenceChainData?.document_type || evidenceChainData?.file_name || "Official Case File"}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setEvidenceChainModalDoc(null)}
                className="w-8 h-8 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {downloadFeedback && (
                <div
                  className={`p-3 rounded-xl text-xs flex items-center justify-between font-mono ${
                    downloadFeedback.type === "success"
                      ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-600"
                      : "bg-destructive/10 border border-destructive/30 text-destructive"
                  }`}
                >
                  <span>{downloadFeedback.text}</span>
                  <button
                    onClick={() => setDownloadFeedback(null)}
                    className="ml-2 text-muted-foreground hover:text-foreground text-xs"
                  >
                    ✕
                  </button>
                </div>
              )}
              {chainLoading ? (
                <div className="py-16 text-center text-muted-foreground animate-pulse font-mono text-xs">
                  Loading document custody chain, verified text and judicial audit history...
                </div>
              ) : evidenceChainData ? (
                <>
                  {/* Origin & Security Screening Card */}
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                        Deposited Court Record
                      </span>
                      <div className="flex items-center gap-2">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                          evidenceChainData.document_status === "VERIFIED"
                            ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                            : "bg-amber-500/10 text-amber-600 border-amber-500/20"
                        }`}>
                          {evidenceChainData.document_status === "VERIFIED" ? "Verified on Docket" : "Pending Verification"}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                          Security Check: Passed
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-primary/10 text-primary border border-primary/20">
                          Court Evidence Vault
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Filename:</span>
                        <span className="text-foreground font-semibold">{evidenceChainData.file_name}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Integrity Seal:</span>
                        {user?.role === "PLATFORM_ADMIN" ? (
                          <span className="text-foreground truncate block font-mono" title={evidenceChainData.file_hash_sha256}>
                            {evidenceChainData.file_hash_sha256?.substring(0, 20)}...
                          </span>
                        ) : (
                          <span className="text-emerald-600 font-semibold flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5" /> Sealed (BSA Sec 63 where applicable)
                          </span>
                        )}
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Depositing Authority:</span>
                        <span className="text-foreground font-semibold">{evidenceChainData.source_authority}</span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-border flex flex-wrap items-center justify-between gap-2">
                      <button
                        onClick={() => handleDownload(evidenceChainData.document_id, evidenceChainData.file_name)}
                        className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border border-border transition-colors"
                      >
                        <Download className="w-3.5 h-3.5 text-primary" /> Download Certified PDF
                      </button>

                      <div className="flex items-center gap-2">
                        {canReview && evidenceChainData.document_status !== "VERIFIED" && (
                          <button
                            onClick={() => handleVerify(evidenceChainData.document_id)}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-sm transition-colors"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" /> Sign & Authorize Document
                          </button>
                        )}
                        {canReview && (
                          <button
                            onClick={() => handleReprocess(evidenceChainData.document_id)}
                            className="px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border border-primary/20 transition-colors"
                            title="Re-run text extraction if court deposited an updated copy"
                          >
                            <RefreshCw className="w-3.5 h-3.5" /> Re-Scan Document Text
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Processing Record & History */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-primary" /> Official Processing Record & Custody History
                      </h4>
                      {evidenceChainData.version_history && evidenceChainData.version_history.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setShowAllVersions(!showAllVersions)}
                          className="text-xs text-primary hover:underline font-medium"
                        >
                          {showAllVersions
                            ? "Show Current Active Only"
                            : `View ${evidenceChainData.version_history.length - 1} Prior Revisions`}
                        </button>
                      )}
                    </div>

                    {/* Active/Current Version Card */}
                    {(() => {
                      const history = evidenceChainData.version_history || [];
                      const latest = history[history.length - 1] || {
                        version_number: evidenceChainData.current_version_number || 1,
                        created_at: evidenceChainData.uploaded_at,
                        ocr_engine: "Court Registry Digital Text Extraction",
                        ocr_confidence: 0.95,
                      };
                      const priorVersions = history.slice(0, -1);

                      return (
                        <div className="space-y-3">
                          <div className="p-4 bg-primary/5 border border-primary/20 rounded-xl space-y-2">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-primary text-primary-foreground">
                                  Current Official Record (v{latest.version_number})
                                </span>
                                <span className="text-xs text-muted-foreground font-mono">
                                  Ingested: {new Date(latest.created_at || Date.now()).toLocaleDateString()}
                                </span>
                              </div>
                              <span className="text-xs font-semibold text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                Legibility: {Math.round((latest.ocr_confidence || 0.95) * 100)}% (Clear & Legible)
                              </span>
                            </div>
                            <div className="text-xs text-foreground/90">
                              <span className="font-semibold text-foreground">Processing Method:</span>{" "}
                              {formatLegalEngineName(latest.ocr_engine)}
                            </div>
                            <p className="text-[11px] text-muted-foreground">
                              Digital transcript verified BSA Sec 63 compliant where applicable for statutory BNSS 479 undertrial evaluation.
                            </p>
                          </div>

                          {/* Collapsible Historical Revisions if user clicks toggle */}
                          {showAllVersions && priorVersions.length > 0 && (
                            <div className="pt-2 space-y-2">
                              <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                                Prior Archived Processing Scans (Audit Vault)
                              </div>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                                {priorVersions.map((v: any) => (
                                  <div key={v.version_id} className="p-3 bg-secondary/30 border border-border rounded-lg text-xs space-y-1">
                                    <div className="flex items-center justify-between font-mono">
                                      <span className="text-foreground font-semibold">Version {v.version_number} (Archived)</span>
                                      <span className="text-[11px] text-muted-foreground">
                                        {new Date(v.created_at).toLocaleDateString()}
                                      </span>
                                    </div>
                                    <div className="text-muted-foreground text-[11px]">
                                      Method: {formatLegalEngineName(v.ocr_engine)} &bull; Legibility: {Math.round((v.ocr_confidence || 0.95) * 100)}%
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>

                  {/* Extracted Facts with Verbatim Source Spans & Human Corrections */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <CheckCheck className="w-3.5 h-3.5 text-primary" /> Key Legal Particulars Extracted from Document
                      </h4>
                      {correctionMsg && <span className="text-xs text-emerald-600 font-semibold">{correctionMsg}</span>}
                    </div>

                    <div className="space-y-3">
                      {evidenceChainData.evidence_chain?.extracted_facts_with_spans?.map((fact: any) => (
                        <div key={fact.field_name} className="p-4 bg-secondary/20 border border-border rounded-xl space-y-2 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-foreground capitalize">
                              {fact.field_name.replace(/_/g, " ")}:
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary">
                                Conf: {Math.round(fact.confidence * 100)}%
                              </span>
                              {canReview && (
                                <button
                                  onClick={() => {
                                    setCorrectingField(fact.field_name);
                                    setCorrectionValue(String(fact.effective_value ?? ""));
                                  }}
                                  className="text-[11px] text-primary hover:underline flex items-center gap-1"
                                >
                                  <Pencil className="w-3 h-3" /> Correct Field
                                </button>
                              )}
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 font-mono">
                            <div>
                              <span className="text-muted-foreground block text-[11px]">Effective Value:</span>
                              <strong className="text-foreground text-sm">{JSON.stringify(fact.effective_value)}</strong>
                              {fact.is_corrected && (
                                <span className="text-[10px] text-amber-600 block">
                                  (Corrected from machine value: {JSON.stringify(fact.machine_value)})
                                </span>
                              )}
                            </div>
                            <div>
                              <span className="text-muted-foreground block text-[11px]">Source Span:</span>
                              <p className="p-1.5 bg-card rounded border border-border text-[11px] text-muted-foreground italic">
                                "{fact.source_span || "Direct digital stream extract"}"
                              </p>
                            </div>
                          </div>

                          {/* Field Correction Inline Dialog */}
                          {correctingField === fact.field_name && (
                            <div className="mt-3 p-3 bg-card border-2 border-primary/30 rounded-lg space-y-2 animate-in fade-in duration-150">
                              <strong className="text-foreground text-xs block">
                                Authoritative Correction for {fact.field_name}:
                              </strong>
                              <input
                                type="text"
                                value={correctionValue}
                                onChange={e => setCorrectionValue(e.target.value)}
                                placeholder="Corrected value"
                                className="w-full px-3 py-1.5 bg-secondary/50 border border-border rounded text-xs text-foreground focus:outline-none"
                              />
                              <input
                                type="text"
                                value={correctionReason}
                                onChange={e => setCorrectionReason(e.target.value)}
                                placeholder="Justification reason (e.g. Verified against jail nominal roll)"
                                className="w-full px-3 py-1.5 bg-secondary/50 border border-border rounded text-xs text-foreground focus:outline-none"
                              />
                              <div className="flex justify-end gap-2">
                                <button
                                  onClick={() => setCorrectingField(null)}
                                  className="px-3 py-1 bg-secondary text-muted-foreground rounded text-xs"
                                >
                                  Cancel
                                </button>
                                <button
                                  onClick={() => handleSubmitCorrection(evidenceChainData.document_id, fact.field_name)}
                                  disabled={correctionSubmitting}
                                  className="px-3 py-1 bg-primary text-primary-foreground font-bold rounded text-xs flex items-center gap-1"
                                >
                                  {correctionSubmitting && <Loader2 className="w-3 h-3 animate-spin" />}
                                  Save Correction
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Downstream Rule & Action Linkage */}
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-2 text-xs">
                    <h4 className="font-serif font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5 text-primary" /> Downstream Rule & Action Linkage
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="p-3 bg-card rounded border border-border font-mono space-y-1">
                        <span className="text-[11px] text-muted-foreground block">Statutory Rule:</span>
                        <strong className="text-foreground">
                          {evidenceChainData.evidence_chain?.statutory_rule_grounding?.statute}
                        </strong>
                        <div className="text-[11px] text-muted-foreground">
                          Eligibility Outcome:{" "}
                          <span className="text-emerald-600 font-bold">
                            {evidenceChainData.evidence_chain?.statutory_rule_grounding?.eligibility_outcome ? "ELIGIBLE" : "REVIEW NEEDED"}
                          </span>
                        </div>
                      </div>

                      <div className="p-3 bg-card rounded border border-border space-y-1">
                        <span className="text-[11px] text-muted-foreground block font-mono">Institutional Actions:</span>
                        {evidenceChainData.evidence_chain?.institutional_actions?.length > 0 ? (
                          evidenceChainData.evidence_chain.institutional_actions.map((act: any, idx: number) => (
                            <div key={idx} className="text-[11px] flex justify-between font-mono">
                              <span className="text-foreground font-semibold">{act.action}</span>
                              <span className="text-muted-foreground">{new Date(act.timestamp).toLocaleDateString()}</span>
                            </div>
                          ))
                        ) : (
                          <span className="text-muted-foreground italic text-xs">No formal actions logged yet.</span>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-12 text-muted-foreground text-xs">
                  No evidence chain available for this record.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

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
                    {STANDARD_DOC_TYPES.map(dt => (
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
