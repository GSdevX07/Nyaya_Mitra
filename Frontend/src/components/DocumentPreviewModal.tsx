import { useState, useEffect } from "react";
import {
  X,
  FileText,
  Download,
  CheckCircle2,
  Clock,
  Copy,
  Check,
  ShieldCheck,
  Loader2,
  AlertCircle,
  AlertTriangle,
  CheckCheck,
} from "lucide-react";
import {
  fetchDocumentContent,
  downloadCaseDocument,
  verifyUploadedDocument,
  reviewUploadedDocument,
  type DocumentContentPreview,
} from "../lib/api";
import { useAuth } from "../lib/auth";

interface DocumentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  docId: string | null;
  docTitle?: string;
  onVerified?: () => void;
  onReviewed?: () => void;
}

export function DocumentPreviewModal({
  isOpen,
  onClose,
  docId,
  docTitle,
  onVerified,
  onReviewed,
}: DocumentPreviewModalProps) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [docData, setDocData] = useState<DocumentContentPreview | null>(null);
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !docId) {
      setDocData(null);
      setError(null);
      return;
    }

    let isCancelled = false;
    setLoading(true);
    setError(null);

    fetchDocumentContent(docId)
      .then((data) => {
        if (!isCancelled) {
          setDocData(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          setError(err.message || "Failed to load document preview.");
          setLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [isOpen, docId]);

  if (!isOpen) return null;

  const handleCopyHash = () => {
    if (docData?.file_hash) {
      navigator.clipboard.writeText(docData.file_hash);
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  const handleCopyText = () => {
    if (docData?.extracted_text) {
      navigator.clipboard.writeText(docData.extracted_text);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    }
  };

  const handleDownload = async () => {
    if (!docId) return;
    try {
      setDownloading(true);
      const filename = docData?.file_name || `${docTitle || "document"}.txt`;
      await downloadCaseDocument(docId, filename);
    } catch (err: any) {
      alert(`Download failed: ${err.message || err}`);
    } finally {
      setDownloading(false);
    }
  };

  const handleVerify = async () => {
    if (!docId) return;
    try {
      setVerifying(true);
      setActionSuccess(null);
      await verifyUploadedDocument(docId);
      setDocData((prev) => (prev ? { ...prev, document_status: "VERIFIED" } : null));
      setActionSuccess("Document successfully verified and authorized in the judicial vault!");
      onVerified?.();
    } catch (err: any) {
      alert(`Verification failed: ${err.message || err}`);
    } finally {
      setVerifying(false);
    }
  };

  const handleReview = async () => {
    if (!docId) return;
    try {
      setReviewing(true);
      setActionSuccess(null);
      await reviewUploadedDocument(docId);
      setDocData((prev) => (prev ? { ...prev, document_status: "REVIEWED" } : null));
      setActionSuccess("Document marked as reviewed for DLSA legal-aid intake.");
      onReviewed?.();
    } catch (err: any) {
      alert(`Review failed: ${err.message || err}`);
    } finally {
      setReviewing(false);
    }
  };

  const isSupervisor = user?.role === "SUPERVISING_LEGAL_OFFICER" || user?.role === "PLATFORM_ADMIN" || user?.role === "GOV_ADMIN";
  const isDlsa = user?.role === "DLSA_OFFICER" || user?.role === "PLATFORM_ADMIN";
  const isMissingDoc = docData?.document_status === "MISSING_REQUISITIONED" || docData?.document_status === "MISSING";
  const canVerifyDoc = !isMissingDoc && (isSupervisor || isDlsa) && (docData?.document_status === "PENDING_VERIFICATION" || docData?.document_status === "REVIEWED");
  const canReviewDoc = !isMissingDoc && isDlsa && docData?.document_status === "PENDING_VERIFICATION";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-4xl bg-card border border-border rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/30">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-serif font-bold text-foreground truncate">
                  {docTitle || docData?.file_name || "Document Preview"}
                </h3>
                {docData?.document_status === "VERIFIED" ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> VERIFIED IN VAULT
                  </span>
                ) : docData?.document_status === "REVIEWED" ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> REVIEWED (INTAKE) &bull; STORED IN VAULT
                  </span>
                ) : docData?.document_status === "MISSING_REQUISITIONED" || docData?.document_status === "MISSING" ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> STATUTORY REQUISITION NOTICE
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-secondary text-foreground border border-border flex items-center gap-1">
                    <Clock className="w-3 h-3 text-muted-foreground" /> PENDING VERIFICATION &bull; STORED IN VAULT
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground font-mono truncate">
                ID: {docId} &bull; Case: {docData?.case_id || "..."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {/* Inline Verification Controls in Header */}
            {canReviewDoc && (
              <button
                onClick={handleReview}
                disabled={reviewing || verifying}
                className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-sm"
                title="Review document for legal-aid intake"
              >
                {reviewing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                <span>Review Intake</span>
              </button>
            )}
            {canVerifyDoc && (
              <button
                onClick={handleVerify}
                disabled={verifying || reviewing}
                className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-sm"
                title="Supervisory verification: authenticate record for court filing"
              >
                {verifying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCheck className="w-3.5 h-3.5" />}
                <span>{isSupervisor ? "Supervisory Verify" : "Verify Document"}</span>
              </button>
            )}
            <button
              onClick={handleDownload}
              disabled={downloading || loading || !!error || isMissingDoc}
              className="px-3 py-1.5 bg-primary text-primary-foreground hover:opacity-90 rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-opacity disabled:opacity-50"
              title={isMissingDoc ? "Record has not yet been uploaded to vault" : "Download official file"}
            >
              {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
              <span>Download</span>
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {actionSuccess && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-600 dark:text-emerald-400 text-xs font-mono flex items-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{actionSuccess}</span>
            </div>
          )}
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3 text-muted-foreground">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
              <p className="text-xs font-mono">Retrieving encrypted evidentiary document...</p>
            </div>
          ) : error ? (
            <div className="py-12 px-6 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive flex flex-col items-center justify-center gap-2 text-center">
              <AlertCircle className="w-8 h-8" />
              <p className="text-sm font-bold">Document Content Unavailable</p>
              <p className="text-xs font-mono max-w-md">{error}</p>
            </div>
          ) : docData ? (
            <>
              {/* Metadata Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3 bg-secondary/30 rounded-lg border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase block">
                    Document Category
                  </span>
                  <span className="text-xs font-mono font-bold text-foreground">
                    {docData.document_type || "Official Record"}
                  </span>
                </div>
                <div className="p-3 bg-secondary/30 rounded-lg border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase block">
                    Origin / Uploader
                  </span>
                  <span className="text-xs font-mono font-semibold text-foreground truncate block">
                    {docData.uploaded_by || (isMissingDoc ? "Pending Institutional Submission" : "Institutional Registry")}
                  </span>
                </div>
                <div className="p-3 bg-secondary/30 rounded-lg border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase block">
                    Record Date
                  </span>
                  <span className="text-xs font-mono font-semibold text-foreground">
                    {docData.uploaded_at ? new Date(docData.uploaded_at).toLocaleDateString() : (isMissingDoc ? "Awaiting Upload" : "Baseline")}
                  </span>
                </div>
              </div>

              {/* Integrity Hash or Requisition Notice */}
              {isMissingDoc ? (
                <div className="p-3 bg-red-500/10 rounded-lg border border-red-500/30 flex items-center justify-between gap-3">
                  <div className="min-w-0 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="text-[10px] font-mono text-muted-foreground uppercase block">
                        Evidentiary Vault Status
                      </span>
                      <span className="text-[11px] font-mono font-bold text-red-600 dark:text-red-400 truncate block">
                        Awaiting Institutional Upload &bull; No Cryptographic Seal Recorded
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-secondary/20 rounded-lg border border-border flex items-center justify-between gap-3">
                  <div className="min-w-0 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-primary shrink-0" />
                    <div className="min-w-0">
                      <span className="text-[10px] font-mono text-muted-foreground uppercase block">
                        Cryptographic SHA-256 Seal
                      </span>
                      <span className="text-[11px] font-mono text-foreground truncate block">
                        {docData.file_hash || "SHA256-AUTHENTICATED"}
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={handleCopyHash}
                    className="px-2.5 py-1 text-[11px] font-mono rounded bg-secondary hover:bg-muted border border-border flex items-center gap-1 shrink-0"
                  >
                    {copiedHash ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedHash ? "Copied" : "Copy"}</span>
                  </button>
                </div>
              )}

              {/* Extracted Content Viewer */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase text-muted-foreground flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5" />
                    Document Extracted Text & Content
                  </span>
                  <button
                    onClick={handleCopyText}
                    className="text-[11px] font-mono text-primary hover:underline flex items-center gap-1"
                  >
                    {copiedText ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedText ? "Copied Content" : "Copy Text"}</span>
                  </button>
                </div>
                <div className="p-4 bg-muted/40 border border-border rounded-lg text-foreground font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-[420px] overflow-y-auto select-all">
                  {docData.extracted_text || "No text could be extracted from this document."}
                </div>
              </div>
            </>
          ) : null}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-border bg-secondary/20 flex flex-wrap items-center justify-between gap-3">
          <span className="text-[11px] font-mono text-muted-foreground">
            Nyaya Mitra Evidentiary Vault &bull; Zero-Trust Verifiable Dossier &bull; BSA Sec 63 Compliant
          </span>
          <div className="flex items-center gap-2">
            {canReviewDoc && (
              <button
                onClick={handleReview}
                disabled={reviewing || verifying}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-sm"
              >
                {reviewing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                <span>Review for DLSA Intake</span>
              </button>
            )}
            {canVerifyDoc && (
              <button
                onClick={handleVerify}
                disabled={verifying || reviewing}
                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-sm"
              >
                {verifying ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCheck className="w-3.5 h-3.5" />}
                <span>{isSupervisor ? "Supervisory Verify" : "Verify Document"}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-1.5 bg-secondary hover:bg-muted border border-border rounded text-xs font-mono font-semibold text-foreground transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
