import { useState } from "react";
import {
  X,
  CheckCircle2,
  Clock,
  AlertTriangle,
  HelpCircle,
  Download,
  RefreshCw,
  GitBranch,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Copy,
  Check,
} from "lucide-react";
import { useAuth } from "../lib/auth";

interface RoleEvidenceProvenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: any;
  loading?: boolean;
  onDownload?: (docId: string, filename: string) => void;
  onVerify?: (docId: string) => void;
  onReview?: (docId: string) => void;
  onReprocess?: (docId: string) => void;
  canReview?: boolean;
}

export function getEvidenceChainButtonLabel(role?: string): string {
  switch (role) {
    case "JAIL_OFFICER":
      return "Document Verification & Provenance";
    case "POLICE_OFFICER":
      return "Police Record Provenance";
    case "DLSA_OFFICER":
      return "Evidence Chain & Legal Record History";
    case "SUPERVISING_LEGAL_OFFICER":
      return "Full Evidence Chain & Supervisory Audit";
    case "DEFENSE_ADVOCATE":
      return "Case Evidence & Document History";
    case "CONTROLLED_EXTERNAL_ADVOCATE":
      return "Authorized Document History";
    case "READ_ONLY_AUDITOR":
      return "Audit Evidence Chain";
    case "GOV_ADMIN":
      return "Evidence & Compliance Overview";
    case "PLATFORM_ADMIN":
      return "Technical Document Integrity";
    case "ACCUSED_USER":
      return "Document Status";
    case "FAMILY_GUARDIAN":
      return "Case Document Status";
    default:
      return "Document Provenance";
  }
}

function getNormalizedStatus(data: any): {
  label: string;
  variant: "verified" | "pending" | "rejected" | "unknown";
} {
  if (!data) return { label: "Not available", variant: "unknown" };
  const raw = (
    data.verification_status ||
    data.status ||
    data.chain_status ||
    data.document_status ||
    data.simple_status ||
    data.high_level_status ||
    data.integrity_status ||
    ""
  ).toString().trim();

  if (!raw) return { label: "Unknown", variant: "unknown" };

  const upper = raw.toUpperCase();
  if (
    upper.includes("REJECT") ||
    upper.includes("TAMPER") ||
    upper.includes("MISMATCH") ||
    upper.includes("MALICIOUS") ||
    upper.includes("QUARANTINE") ||
    upper.includes("FAILED")
  ) {
    return { label: "Rejected", variant: "rejected" };
  }
  if (
    upper.includes("PENDING") ||
    upper.includes("AWAIT") ||
    upper.includes("UNDER") ||
    upper.includes("REVIEW_REQUIRED") ||
    upper.includes("INTAKE")
  ) {
    return { label: "Pending Verification", variant: "pending" };
  }
  if (
    upper.includes("VERIF") ||
    upper.includes("INTACT") ||
    upper.includes("CLEAN") ||
    upper.includes("PASSED") ||
    upper.includes("APPROVED") ||
    upper.includes("TAMPER_FREE")
  ) {
    return { label: "Verified", variant: "verified" };
  }

  return { label: raw, variant: "unknown" };
}

function formatDate(val?: string | null): string {
  if (!val) return "Not available";
  try {
    const d = new Date(val);
    if (!isNaN(d.getTime())) {
      return d.toLocaleString("en-IN", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  } catch {}
  return String(val);
}

function getHistoryItems(data: any): Array<{
  title: string;
  actor: string;
  timestamp: string;
  status?: string;
  details?: string;
}> {
  if (!data) return [];
  const list: any[] =
    data.version_history ||
    data.verification_history ||
    data.audit_events ||
    data.all_versions ||
    data.system_audit_events ||
    data.complete_audit_trail ||
    [];

  if (!Array.isArray(list) || list.length === 0) {
    if (data.uploaded_at || data.uploaded_by || data.source_authority) {
      return [
        {
          title: "Initial Record Deposit",
          actor: data.uploaded_by || data.source_authority || "Official Institutional Desk",
          timestamp: formatDate(data.uploaded_at || data.created_at || data.document_date),
          status: "Verified",
          details: "Certified copy received and entered into authoritative case record.",
        },
      ];
    }
    return [];
  }

  return list.map((item, idx) => {
    const title =
      item.version_number
        ? `Version ${item.version_number}`
        : item.stage
        ? item.stage
        : item.action
        ? item.action.replace(/_/g, " ")
        : `Record Event #${idx + 1}`;

    const actor =
      item.uploader ||
      item.processed_by ||
      item.authority ||
      item.actor_id ||
      item.actor_role ||
      item.ocr_engine ||
      "Not available";

    const timestamp = formatDate(item.recorded_at || item.created_at || item.timestamp);
    const status = item.status || item.verification_status || item.stage_status;
    const details = item.details || item.notes || item.needs_human_verification_reason;

    return { title, actor, timestamp, status, details };
  });
}

export function RoleEvidenceProvenanceModal({
  isOpen,
  onClose,
  data,
  loading = false,
  onDownload,
  onVerify,
  onReview,
  onReprocess,
  canReview = false,
}: RoleEvidenceProvenanceModalProps) {
  const { user } = useAuth();
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [copiedHash, setCopiedHash] = useState(false);

  if (!isOpen) return null;

  const roleView = data?.role_view || user?.role || "UNKNOWN";
  const uiLabel = data?.ui_label || "Document Verification & Provenance";

  const copyHash = (hash: string) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  // Extract universal provenance fields
  const statusInfo = getNormalizedStatus(data);
  const docName = data?.document_name || data?.file_name || data?.title || "Not available";
  const caseRef = data?.case_reference || data?.case_id || data?.target_record_id || "Not available";
  const sourceOrigin =
    data?.source_authority ||
    data?.source_agency ||
    data?.facility_name ||
    data?.police_station ||
    "Not available";
  const uploadedBy = data?.uploaded_by || data?.uploader || data?.processed_by || "Not available";
  const uploadDateTime = formatDate(data?.uploaded_at || data?.created_at || data?.document_date);
  const historyEvents = getHistoryItems(data);

  const rawHash =
    data?.file_hash_sha256 ||
    data?.sha256_hash ||
    data?.technical_hash ||
    data?.cryptographic_sha256 ||
    "";

  const securityScreeningStatus =
    data?.security_screening?.status ||
    data?.security_screening_scan?.status ||
    (statusInfo.variant === "rejected" ? "Review required" : "Integrity check passed");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-3xl bg-card border-2 border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/30">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <GitBranch className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
                {uiLabel}
              </h3>
              <p className="text-xs text-muted-foreground font-mono truncate max-w-md">
                Case: {caseRef} &bull; Document: {docName}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <div className="w-9 h-9 border-3 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" />
              <p className="text-xs font-mono text-muted-foreground">
                Retrieving institutional document provenance...
              </p>
            </div>
          ) : !data ? (
            <div className="text-center py-12 space-y-2">
              <HelpCircle className="w-8 h-8 text-muted-foreground mx-auto" />
              <p className="text-xs font-mono text-muted-foreground">
                No document provenance record found for this document.
              </p>
            </div>
          ) : (
            <>
              {/* ── 1. Core Provenance & Verification Metadata Grid ── */}
              <div className="bg-secondary/20 border-2 border-border rounded-xl p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border/60">
                  <div className="space-y-0.5">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground block">
                      Verification Status
                    </span>
                    <div className="flex items-center gap-2 pt-0.5">
                      {statusInfo.variant === "verified" && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-serif font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shadow-xs">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                          {statusInfo.label}
                        </span>
                      )}
                      {statusInfo.variant === "pending" && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-serif font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30 shadow-xs">
                          <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                          {statusInfo.label}
                        </span>
                      )}
                      {statusInfo.variant === "rejected" && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-serif font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30 shadow-xs">
                          <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                          {statusInfo.label}
                        </span>
                      )}
                      {statusInfo.variant === "unknown" && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-serif font-bold bg-secondary text-muted-foreground border border-border shadow-xs">
                          <HelpCircle className="w-4 h-4 text-muted-foreground" />
                          {statusInfo.label}
                        </span>
                      )}

                      {data.current_document_version && (
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-primary/10 text-primary border border-primary/20">
                          {data.current_document_version}
                        </span>
                      )}
                    </div>
                  </div>

                  {data.integrity_status && (
                    <div className="text-left sm:text-right">
                      <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-muted-foreground block">
                        Record Integrity
                      </span>
                      <span className="text-xs font-serif font-bold text-foreground inline-flex items-center gap-1 mt-0.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                        {data.integrity_status}
                      </span>
                    </div>
                  )}
                </div>

                {/* Minimum 6 Mandated Provenance Fields */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs pt-1">
                  <div>
                    <span className="text-muted-foreground block text-[11px] font-medium">Document Name:</span>
                    <strong className="text-foreground text-sm font-serif block mt-0.5 truncate" title={docName}>
                      {docName}
                    </strong>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[11px] font-medium">Case Reference:</span>
                    <strong className="text-foreground font-mono block mt-0.5">
                      {caseRef}
                    </strong>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[11px] font-medium">Source / Origin:</span>
                    <strong className="text-foreground block mt-0.5">
                      {sourceOrigin}
                    </strong>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[11px] font-medium">Uploaded By:</span>
                    <span className="text-foreground block mt-0.5">
                      {uploadedBy}
                    </span>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[11px] font-medium">Upload Date / Time:</span>
                    <span className="text-foreground block mt-0.5">
                      {uploadDateTime}
                    </span>
                  </div>

                  <div>
                    <span className="text-muted-foreground block text-[11px] font-medium">Security Screening:</span>
                    <span className="text-foreground block mt-0.5">
                      {securityScreeningStatus}
                    </span>
                  </div>
                </div>
              </div>

              {/* ── 2. Verification & Provenance History Timeline ── */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-serif font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                    <GitBranch className="w-3.5 h-3.5 text-primary" />
                    Verification & Provenance History
                  </h4>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {historyEvents.length} Event{historyEvents.length === 1 ? "" : "s"} Recorded
                  </span>
                </div>

                {historyEvents.length > 0 ? (
                  <div className="border border-border rounded-xl divide-y divide-border overflow-hidden bg-card text-xs">
                    {historyEvents.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-secondary/20 transition-colors"
                      >
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-serif font-bold text-foreground">{item.title}</span>
                            {item.status && (
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-semibold bg-primary/10 text-primary border border-primary/20">
                                {item.status}
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] text-muted-foreground block">
                            Actor / Authority: <span className="text-foreground font-medium">{item.actor}</span>
                          </span>
                          {item.details && (
                            <p className="text-[11px] text-muted-foreground italic pt-0.5">{item.details}</p>
                          )}
                        </div>
                        <div className="text-left sm:text-right shrink-0">
                          <span className="text-[11px] font-mono text-muted-foreground block">
                            {item.timestamp}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl text-center text-xs text-muted-foreground">
                    No prior version recorded. Current document is the authoritative verified copy on file.
                  </div>
                )}
              </div>

              {/* ── 3. Role-Tailored Supplementary Panels ── */}
              
              {/* Accused & Family View: Next Steps and Legal Services Support */}
              {(roleView === "ACCUSED_USER" || roleView === "FAMILY_GUARDIAN") && (
                <div className="p-4 bg-primary/5 border border-primary/20 rounded-xl space-y-2 text-xs">
                  <div className="font-serif font-bold text-foreground">
                    Next Procedural Step:
                  </div>
                  <p className="text-muted-foreground leading-relaxed">
                    {data.next_step ||
                      data.next_action ||
                      "Your assigned legal-aid defense counsel is reviewing this document to prepare court bail and release petitions."}
                  </p>
                  <div className="text-[11px] text-muted-foreground pt-1 border-t border-primary/10">
                    * {data.support_note ||
                      "DLSA legal aid services and court representation are 100% free under the Legal Services Authorities Act."}
                  </div>
                </div>
              )}

              {/* Defense / Legal Aid Brief Facts */}
              {data.relevant_extracted_facts && data.relevant_extracted_facts.length > 0 && (
                <div className="space-y-2">
                  <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                    Verified Facts Grounding Legal Brief:
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {data.relevant_extracted_facts.map((f: any, idx: number) => (
                      <div key={idx} className="p-3 bg-card border border-border rounded-lg text-xs space-y-1">
                        <span className="text-[11px] text-muted-foreground font-semibold block">{f.field_name}:</span>
                        <strong className="text-foreground block">{f.value}</strong>
                        {f.source_context && (
                          <span className="text-[10px] text-muted-foreground italic block truncate">
                            Context: &ldquo;{f.source_context}&rdquo;
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Technical Hash Details (Optional Toggle) */}
              {rawHash && (
                <div className="pt-2 border-t border-border">
                  <button
                    onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                    className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
                  >
                    {showTechnicalDetails ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    {showTechnicalDetails ? "Hide Cryptographic Hash Details" : "View Cryptographic SHA-256 Details (Optional)"}
                  </button>
                  {showTechnicalDetails && (
                    <div className="mt-2 p-3 bg-muted/40 border border-border rounded-lg font-mono text-[11px] flex justify-between items-center">
                      <span className="truncate mr-2">SHA-256: {rawHash}</span>
                      <button
                        onClick={() => copyHash(rawHash)}
                        className="text-xs text-primary hover:underline shrink-0 font-sans flex items-center gap-1"
                      >
                        {copiedHash ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedHash ? "Copied" : "Copy"}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* ── 4. Action & Operational Buttons ── */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border">
                {onDownload && (
                  <button
                    onClick={() => onDownload(data.document_id || data.id, docName)}
                    className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border border-border transition-colors"
                  >
                    <Download className="w-3.5 h-3.5 text-primary" /> Download Certified Copy
                  </button>
                )}

                <div className="flex items-center gap-2 ml-auto">
                  {user?.role === "DLSA_OFFICER" &&
                    statusInfo.variant !== "verified" &&
                    onReview && (
                      <button
                        onClick={() => onReview(data.document_id || data.id)}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-sm transition-colors"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Mark Reviewed
                      </button>
                    )}
                  {user?.role === "SUPERVISING_LEGAL_OFFICER" &&
                    statusInfo.variant !== "verified" &&
                    onVerify && (
                      <button
                        onClick={() => onVerify(data.document_id || data.id)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-sm transition-colors"
                      >
                        <ShieldCheck className="w-3.5 h-3.5" /> Supervisory Verify
                      </button>
                    )}
                  {canReview && onReprocess && (
                    <button
                      onClick={() => onReprocess(data.document_id || data.id)}
                      className="px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border border-primary/20 transition-colors"
                    >
                      <RefreshCw className="w-3.5 h-3.5" /> Re-Scan Text
                    </button>
                  )}
                  <button
                    onClick={onClose}
                    className="px-4 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground rounded-lg text-xs font-semibold border border-border transition-colors"
                  >
                    Close
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
