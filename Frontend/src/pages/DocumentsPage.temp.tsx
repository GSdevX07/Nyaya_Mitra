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
  FileImage,
  FileScan,
  Pencil,
  ClipboardPaste,
  Sparkles,
  Eye,
  Hash,
} from "lucide-react";
import { fetchDocuments, uploadDocumentFile } from "@/lib/api";

interface DocItem {
  id: string;
  case_id: string;
  prisoner_name: string;
  document_type: string;
  status: string;
  is_present: boolean;
  uploaded_date?: string;
  jail_location: string;
}

interface UploadResult {
  is_handwritten: boolean;
  ocr_engine: string;
  extracted_text: string;
  file_name: string;
  file_size_bytes: number;
  file_hash: string;
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

const ACCEPTED_EXTENSIONS = ".pdf,.jpg,.jpeg,.png,.webp,.bmp,.tiff,.tif,.gif,.heic";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function getFileTypeIcon(file: File) {
  if (file.type === "application/pdf") return <FileText className="w-5 h-5 text-red-400" />;
  if (file.type.startsWith("image/")) return <FileImage className="w-5 h-5 text-blue-400" />;
  return <FileScan className="w-5 h-5 text-accent" />;
}

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [uploadCaseId, setUploadCaseId] = useState("UTP-0015");
  const [uploadDocType, setUploadDocType] = useState("charge_sheet");
  const [uploading, setUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Upload modal state
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customText, setCustomText] = useState("");
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [step, setStep] = useState<"idle" | "preview" | "done">("idle");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocs = async () => {
    setLoading(true);
    const data = await fetchDocuments();
    setDocs(data);
    setLoading(false);
  };

  useEffect(() => {
    loadDocs();
  }, []);

  const resetModal = () => {
    setSelectedFile(null);
    setCustomText("");
    setUploadResult(null);
    setUploadError("");
    setStep("idle");
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
      setUploadError("Unsupported file type. Please upload a PDF or image (JPG, PNG, WEBP, etc.).");
      return;
    }
    setSelectedFile(file);
    setStep("preview");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
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
      setUploadResult(result);
      setStep("done");
      await loadDocs();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed. Please try again.";
      setUploadError(msg);
    } finally {
      setUploading(false);
    }
  };

  const filtered = docs.filter(
    (d) =>
      d.case_id.toLowerCase().includes(search.toLowerCase()) ||
      d.document_type.toLowerCase().includes(search.toLowerCase()) ||
      d.prisoner_name.toLowerCase().includes(search.toLowerCase())
  );

  const presentCount = docs.filter((d) => d.is_present).length;
  const missingCount = docs.filter((d) => !d.is_present).length;

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Document Vault
            </span>
            <span className="text-xs text-muted-foreground font-mono">Completeness Agent Sync</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Legal Records & File Vault</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Central repository for Remand Orders, Charge Sheets, and DLSA certificates. Upload PDFs or
            photos ΓÇö handwriting is auto-recognised via OCR.
          </p>
        </div>
        <button
          onClick={() => openModal()}
          className="px-4 py-2 bg-accent text-accent-foreground font-semibold rounded-xl text-sm hover:opacity-90 transition-opacity flex items-center gap-2 shadow-lg shadow-accent/20 whitespace-nowrap"
        >
          <Plus className="w-4 h-4" /> Upload Document
        </button>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{docs.length}</div>
            <div className="text-xs text-muted-foreground">Total Documents Tracked</div>
          </div>
        </div>
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{presentCount}</div>
            <div className="text-xs text-muted-foreground">Verified & On Record</div>
          </div>
        </div>
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-destructive/10 border border-destructive/20 flex items-center justify-center text-destructive">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{missingCount}</div>
            <div className="text-xs text-muted-foreground">Missing Document Gaps</div>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-muted-foreground absolute left-3.5 top-3" />
        <input
          type="text"
          placeholder="Search document vault by case ID or doc name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-white/[0.03] border border-white/10 rounded-xl text-sm text-white focus:outline-none focus:border-accent"
        />
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Loading document inventory from backendΓÇª
        </div>
      ) : (
        <div className="bg-white/[0.02] border border-white/10 rounded-2xl overflow-hidden backdrop-blur-md">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-muted-foreground">
              <thead className="bg-white/[0.03] text-xs font-semibold text-white uppercase border-b border-white/10">
                <tr>
                  <th className="px-6 py-4">Case ID</th>
                  <th className="px-6 py-4">Document Type</th>
                  <th className="px-6 py-4">Prisoner Record</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4">Facility</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filtered.map((d) => (
                  <tr key={d.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4 font-mono text-accent font-semibold">{d.case_id}</td>
                    <td className="px-6 py-4 text-white font-medium">{d.document_type}</td>
                    <td className="px-6 py-4 text-white/80">{d.prisoner_name}</td>
                    <td className="px-6 py-4">
                      {d.is_present ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Present
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-destructive/10 text-destructive border border-destructive/20">
                          <AlertTriangle className="w-3.5 h-3.5" /> Missing
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">{d.jail_location}</td>
                    <td className="px-6 py-4 text-right">
                      {!d.is_present && (
                        <button
                          onClick={() => {
                            openModal(
                              d.case_id,
                              d.document_type.toLowerCase().replace(/ /g, "_")
                            );
                          }}
                          className="px-3 py-1 bg-white/5 hover:bg-white/10 text-white rounded-lg text-xs font-medium border border-white/10 transition-colors inline-flex items-center gap-1"
                        >
                          <Upload className="w-3 h-3" /> Upload
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

      {/* ΓöÇΓöÇΓöÇ Upload Modal ΓöÇΓöÇΓöÇ */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div
            className="w-full max-w-2xl bg-[#0f1117] border border-white/10 rounded-3xl shadow-2xl overflow-hidden"
            style={{ boxShadow: "0 0 60px rgba(99,102,241,0.15)" }}
          >
            {/* Modal Header */}
            <div className="px-7 py-5 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center">
                  <FileScan className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Upload Document</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    PDF or photo &mdash; handwriting is auto-recognised
                  </p>
                </div>
              </div>
              <button
                onClick={closeModal}
                className="w-8 h-8 rounded-lg hover:bg-white/10 flex items-center justify-center text-muted-foreground hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-7 py-6 space-y-6">
              {/* Case ID & Doc Type row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5 font-medium">
                    Target Case ID
                  </label>
                  <input
                    type="text"
                    value={uploadCaseId}
                    onChange={(e) => setUploadCaseId(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-accent/60 transition-colors"
                    required
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5 font-medium">
                    Document Type
                  </label>
                  <select
                    value={uploadDocType}
                    onChange={(e) => setUploadDocType(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-xl text-white text-sm focus:outline-none focus:border-accent/60 transition-colors"
                  >
                    <option value="charge_sheet" className="bg-[#0f1117]">Charge Sheet</option>
                    <option value="remand_order" className="bg-[#0f1117]">Remand Order</option>
                    <option value="prior_bail_order_if_any" className="bg-[#0f1117]">Prior Bail Order</option>
                    <option value="medical_certificate" className="bg-[#0f1117]">Medical Certificate</option>
                    <option value="identity_proof" className="bg-[#0f1117]">Identity Proof</option>
                    <option value="other" className="bg-[#0f1117]">Other Document</option>
                  </select>
                </div>
              </div>

              {/* Two-column input: File zone + Text area */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Left ΓÇö File drop zone */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5 font-medium flex items-center gap-1.5">
                    <FileImage className="w-3.5 h-3.5" /> Scan / Upload Document
                  </label>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={onDragOver}
                    onDragLeave={onDragLeave}
                    onDrop={onDrop}
                    className={`relative cursor-pointer rounded-2xl border-2 border-dashed transition-all duration-200 flex flex-col items-center justify-center gap-3 py-8 px-4 text-center min-h-[160px] ${
                      dragOver
                        ? "border-accent bg-accent/10"
                        : selectedFile
                        ? "border-emerald-500/50 bg-emerald-500/5"
                        : "border-white/15 bg-white/[0.02] hover:border-accent/50 hover:bg-accent/5"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept={ACCEPTED_EXTENSIONS}
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFileSelect(f);
                      }}
                    />
                    {selectedFile ? (
                      <>
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                          {getFileTypeIcon(selectedFile)}
                        </div>
                        <div>
                          <p className="text-sm text-white font-medium truncate max-w-[160px]">
                            {selectedFile.name}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {formatBytes(selectedFile.size)}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedFile(null);
                            setStep("idle");
                            if (fileInputRef.current) fileInputRef.current.value = "";
                          }}
                          className="absolute top-2 right-2 w-6 h-6 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors"
                        >
                          <X className="w-3 h-3 text-white" />
                        </button>
                      </>
                    ) : (
                      <>
                        <div className="w-10 h-10 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center">
                          <Upload className="w-5 h-5 text-accent" />
                        </div>
                        <div>
                          <p className="text-sm text-white font-medium">Drop file here</p>
                          <p className="text-xs text-muted-foreground mt-0.5">
                            PDF, JPG, PNG, WEBP, BMP, TIFF, GIF, HEIC
                          </p>
                        </div>
                        <span className="text-xs text-accent/70 border border-accent/20 rounded-lg px-3 py-1">
                          or click to browse
                        </span>
                      </>
                    )}
                  </div>

                  {/* OCR capability badge */}
                  <div className="mt-2 flex items-center gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    <span className="text-xs text-muted-foreground">
                      Handwriting in photos is auto-recognised via OCR
                    </span>
                  </div>
                </div>

                {/* Right ΓÇö Custom text paste area */}
                <div>
                  <label className="text-xs text-muted-foreground block mb-1.5 font-medium flex items-center gap-1.5">
                    <ClipboardPaste className="w-3.5 h-3.5" /> Or Paste / Type Text
                  </label>
                  <textarea
                    value={customText}
                    onChange={(e) => setCustomText(e.target.value)}
                    placeholder="Paste extracted text, type case details, or enter manually hereΓÇª"
                    rows={7}
                    className="w-full px-3 py-3 bg-white/5 border border-white/10 rounded-2xl text-white text-sm focus:outline-none focus:border-accent/60 transition-colors resize-none placeholder:text-muted-foreground/50 leading-relaxed"
                  />
                  <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1">
                    <Pencil className="w-3 h-3" />
                    Used when no file is uploaded, or to supplement file content
                  </p>
                </div>
              </div>

              {/* Error */}
              {uploadError && (
                <div className="flex items-start gap-3 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}

              {/* Success result panel */}
              {step === "done" && uploadResult && (
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5 space-y-4">
                  <div className="flex items-center gap-2 text-emerald-400 font-semibold text-sm">
                    <CheckCircle2 className="w-4 h-4" />
                    Document saved to vault &amp; synced with Supabase
                  </div>

                  {/* Badges */}
                  <div className="flex flex-wrap gap-2">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${
                      uploadResult.is_handwritten
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                    }`}>
                      {uploadResult.is_handwritten ? (
                        <><Pencil className="w-3 h-3" /> Handwriting Detected</>
                      ) : (
                        <><FileText className="w-3 h-3" /> Typed / Digital Text</>
                      )}
                    </span>
                    {uploadResult.ocr_engine && uploadResult.ocr_engine !== "none" && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-accent/10 text-accent border border-accent/20">
                        <FileScan className="w-3 h-3" /> {uploadResult.ocr_engine}
                      </span>
                    )}
                    {uploadResult.file_name && uploadResult.file_name !== "manual_entry.txt" && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-white/5 text-white/70 border border-white/10">
                        <FileImage className="w-3 h-3" /> {uploadResult.file_name}
                      </span>
                    )}
                    {uploadResult.is_complete && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                        <ShieldCheck className="w-3 h-3" /> Case Now Complete
                      </span>
                    )}
                  </div>

                  {/* Extracted text preview */}
                  {uploadResult.extracted_text && (
                    <div className="space-y-1.5">
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Eye className="w-3 h-3" /> Extracted Text Preview
                      </p>
                      <div className="bg-black/30 rounded-xl p-3 max-h-28 overflow-y-auto border border-white/5">
                        <p className="text-xs text-white/80 whitespace-pre-wrap leading-relaxed font-mono">
                          {uploadResult.extracted_text.slice(0, 600)}
                          {uploadResult.extracted_text.length > 600 && "ΓÇª"}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* SHA-256 hash */}
                  {uploadResult.file_hash && (
                    <div className="flex items-start gap-2">
                      <Hash className="w-3.5 h-3.5 text-muted-foreground mt-0.5 shrink-0" />
                      <p className="text-xs text-muted-foreground font-mono break-all">
                        SHA-256: {uploadResult.file_hash}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-between items-center pt-2 border-t border-white/10">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2.5 bg-white/5 text-white rounded-xl text-sm font-medium hover:bg-white/10 transition-colors"
                >
                  {step === "done" ? "Close" : "Cancel"}
                </button>

                {step !== "done" && (
                  <button
                    type="submit"
                    disabled={uploading || (!selectedFile && !customText.trim())}
                    className="px-5 py-2.5 bg-accent text-accent-foreground rounded-xl text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-accent/20"
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {selectedFile ? "Processing OCRΓÇª" : "SavingΓÇª"}
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4" />
                        Upload & Extract Text
                      </>
                    )}
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
