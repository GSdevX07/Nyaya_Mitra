import { useState } from "react";
import {
  X, Shield, CheckCircle2,
  Download, RefreshCw, GitBranch, Key, ChevronDown, ChevronRight,
  ShieldCheck
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
    navigator.clipboard.writeText(hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-4xl bg-card border-2 border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/30">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
              <GitBranch className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
                {uiLabel}
              </h3>
              <p className="text-xs text-muted-foreground font-mono">
                Case: {data?.case_reference || data?.case_id || "Case Record"} &bull; Document: {data?.document_name || data?.file_name || "Official File"}
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
            <div className="py-16 text-center text-muted-foreground animate-pulse text-xs">
              Retrieving institutional document provenance...
            </div>
          ) : !data ? (
            <div className="text-center py-12 text-muted-foreground text-xs">
              No document provenance record found for this document.
            </div>
          ) : (
            <>
              {/* ============================================================== */}
              {/* 1. JAIL OFFICER VIEW */}
              {/* ============================================================== */}
              {roleView === "JAIL_OFFICER" && (
                <div className="space-y-4">
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                        Prison Custody Intake Record
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                          {data.verification_status}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
                          Version: {data.current_document_version}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Facility / Prison:</span>
                        <strong className="text-foreground">{data.facility_name}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Source Authority:</span>
                        <strong className="text-foreground">{data.source_authority}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Uploaded By:</span>
                        <span className="text-foreground">{data.uploaded_by}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Upload Timestamp:</span>
                        <span className="text-foreground">{data.uploaded_at ? new Date(data.uploaded_at).toLocaleString() : "Recorded on file"}</span>
                      </div>
                    </div>
                  </div>

                  {/* Security & Integrity Status */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl border border-border bg-card space-y-1.5">
                      <div className="flex items-center gap-2 text-emerald-600 font-bold text-xs">
                        <CheckCircle2 className="w-4 h-4" /> Security Screening: {data.security_screening?.status}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {data.security_screening?.message}
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-border bg-card space-y-1.5">
                      <div className="flex items-center gap-2 text-primary font-bold text-xs">
                        <ShieldCheck className="w-4 h-4 text-emerald-600" /> Record Integrity: {data.integrity_status}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        File matches original intake record. No tampering or alteration detected.
                      </p>
                    </div>
                  </div>

                  {/* Verification Record */}
                  <div className="p-4 bg-muted/30 border border-border rounded-xl text-xs flex justify-between items-center">
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Official Verification:</span>
                      <strong className="text-foreground">{data.verified_by}</strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[11px]">Verified On:</span>
                      <span className="text-foreground">{data.verified_on ? new Date(data.verified_on).toLocaleDateString() : "Pending review"}</span>
                    </div>
                  </div>

                  {/* Simple Version History */}
                  {data.version_history?.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Intake Version History:
                      </span>
                      <div className="border border-border rounded-xl divide-y divide-border text-xs">
                        {data.version_history.map((v: any, idx: number) => (
                          <div key={idx} className="p-3 flex justify-between items-center">
                            <span className="font-semibold text-foreground">{v.version_number} &mdash; {v.uploader}</span>
                            <span className="text-muted-foreground">{v.recorded_at ? new Date(v.recorded_at).toLocaleDateString() : "Current"}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ============================================================== */}
              {/* 2. POLICE OFFICER VIEW */}
              {/* ============================================================== */}
              {roleView === "POLICE_OFFICER" && (
                <div className="space-y-4">
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                        Police Record Dossier
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                        {data.verification_status}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Police Station:</span>
                        <strong className="text-foreground">{data.police_station}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">District Jurisdiction:</span>
                        <strong className="text-foreground">{data.district}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Source Authority:</span>
                        <span className="text-foreground">{data.source_authority}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Uploaded By:</span>
                        <span className="text-foreground">{data.uploaded_by}</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl border border-border bg-card space-y-1.5 text-xs">
                    <div className="flex items-center gap-2 text-emerald-600 font-bold">
                      <CheckCircle2 className="w-4 h-4" /> Integrity: {data.integrity_status}
                    </div>
                    <p className="text-muted-foreground">
                      Police source record is verified intact and indexed on the judicial docket.
                    </p>
                  </div>

                  {/* Verification Pipeline History */}
                  {data.verification_history?.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Record Stage Milestones:
                      </span>
                      <div className="border border-border rounded-xl divide-y divide-border text-xs">
                        {data.verification_history.map((vh: any, idx: number) => (
                          <div key={idx} className="p-3 flex justify-between items-center">
                            <span className="font-semibold text-foreground">{vh.stage}</span>
                            <span className="text-emerald-600 font-bold">{vh.status}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ============================================================== */}
              {/* 3. DEFENSE COUNSEL VIEW */}
              {/* ============================================================== */}
              {roleView === "DEFENSE_ADVOCATE" && (
                <div className="space-y-4">
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                        Assigned Matter Evidence Record
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                          {data.verification_status}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
                          {data.evidence_integrity_status}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-1">
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Source Authority:</span>
                        <strong className="text-foreground">{data.source_authority}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Document Date:</span>
                        <span className="text-foreground">{data.document_date}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Upload History:</span>
                        <span className="text-foreground">{data.upload_history}</span>
                      </div>
                    </div>
                  </div>

                  {/* Relevant Extracted Facts for Bail Drafting */}
                  {data.relevant_extracted_facts?.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
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

                  {/* Optional Technical Details Toggle */}
                  <div className="pt-2 border-t border-border">
                    <button
                      onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                      className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
                    >
                      {showTechnicalDetails ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      {showTechnicalDetails ? "Hide Technical Hash Details" : "View Technical Hash Details (Optional)"}
                    </button>
                    {showTechnicalDetails && (
                      <div className="mt-2 p-3 bg-muted/50 border border-border rounded-lg font-mono text-[11px] flex justify-between items-center">
                        <span className="truncate mr-2">SHA-256: {data.technical_hash}</span>
                        <button
                          onClick={() => copyHash(data.technical_hash)}
                          className="text-xs text-primary hover:underline shrink-0"
                        >
                          {copiedHash ? "Copied!" : "Copy"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* ============================================================== */}
              {/* 4. CONTROLLED EXTERNAL ADVOCATE VIEW */}
              {/* ============================================================== */}
              {roleView === "CONTROLLED_EXTERNAL_ADVOCATE" && (
                <div className="space-y-4">
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                        Explicitly Shared Record
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                        {data.integrity_status}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Access Authorization:</span>
                        <strong className="text-foreground">{data.access_type}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Shared Version:</span>
                        <strong className="text-foreground">{data.version_shared}</strong>
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground pt-1 italic">
                      * {data.permitted_usage}
                    </p>
                  </div>
                </div>
              )}

              {/* ============================================================== */}
              {/* 5. READ-ONLY AUDITOR VIEW */}
              {/* ============================================================== */}
              {roleView === "READ_ONLY_AUDITOR" && (
                <div className="space-y-4">
                  <div className="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-300 rounded-lg text-xs font-semibold flex items-center gap-2">
                    <Shield className="w-4 h-4 shrink-0" />
                    Read-Only Statutory Audit Mode &mdash; Complete Append-Only Event Trail
                  </div>

                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Document Status:</span>
                      <strong className="text-foreground">{data.document_status}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">SHA-256 Checksum:</span>
                      <span className="font-mono text-foreground break-all">{data.file_hash_sha256}</span>
                    </div>
                  </div>

                  {data.audit_events?.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Audit Trail Sequence:
                      </span>
                      <div className="border border-border rounded-xl divide-y divide-border text-xs">
                        {data.audit_events.map((ev: any, idx: number) => (
                          <div key={idx} className="p-3 flex flex-wrap justify-between items-center gap-2">
                            <div>
                              <strong className="text-foreground font-mono">{ev.action}</strong>
                              <span className="text-muted-foreground block text-[11px]">
                                Actor: {ev.actor_id} ({ev.actor_role})
                              </span>
                            </div>
                            <span className="text-muted-foreground font-mono text-[11px]">{ev.timestamp}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ============================================================== */}
              {/* 6. GOVERNMENT / SLSA ADMIN VIEW */}
              {/* ============================================================== */}
              {roleView === "GOV_ADMIN" && (
                <div className="space-y-4">
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                        Institutional Governance & Compliance Overview
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                        {data.integrity_status}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-1">
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Jurisdiction:</span>
                        <strong className="text-foreground">{data.district || "Not specified"}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Source Authority:</span>
                        <strong className="text-foreground">{data.source_authority}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Verification Status:</span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-primary/10 text-primary">
                          {data.verification_status}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Compliance Indicators */}
                  <div className="p-4 bg-card border border-border rounded-xl space-y-2">
                    <h4 className="text-xs font-serif font-bold text-foreground">Compliance & Legal Standards</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-2.5 bg-secondary/30 rounded border border-border">
                        <span className="text-muted-foreground block text-[11px]">Automated Screening:</span>
                        <strong className="text-foreground">{data.compliance_indicators?.security_screening || "Compliant"}</strong>
                      </div>
                      <div className="p-2.5 bg-secondary/30 rounded border border-border">
                        <span className="text-muted-foreground block text-[11px]">Chain of Custody:</span>
                        <strong className="text-foreground">
                          {data.compliance_indicators?.chain_of_custody_established ? "Established (Append-Only)" : "Pending"}
                        </strong>
                      </div>
                      <div className="p-2.5 bg-secondary/30 rounded border border-border">
                        <span className="text-muted-foreground block text-[11px]">Electronic Record Legal Reference:</span>
                        <strong className="text-foreground">{data.compliance_indicators?.electronic_record_legal_reference || "BSA Section 63 where applicable"}</strong>
                      </div>
                      <div className="p-2.5 bg-secondary/30 rounded border border-border">
                        <span className="text-muted-foreground block text-[11px]">Compliance Status:</span>
                        <strong className="text-foreground">{data.compliance_indicators?.electronic_record_compliance || "Applicable - On Record"}</strong>
                      </div>
                    </div>
                  </div>

                  {/* Case & Workflow Overview */}
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="p-3 bg-secondary/20 rounded-lg border border-border">
                      <span className="text-lg font-mono font-bold text-foreground">{data.version_count || 1}</span>
                      <span className="text-[11px] text-muted-foreground block">Version History</span>
                    </div>
                    <div className="p-3 bg-secondary/20 rounded-lg border border-border">
                      <span className="text-lg font-mono font-bold text-amber-600">{data.missing_records_count || 0}</span>
                      <span className="text-[11px] text-muted-foreground block">Missing Records</span>
                    </div>
                    <div className="p-3 bg-secondary/20 rounded-lg border border-border">
                      <span className="text-lg font-mono font-bold text-primary">{data.audit_trail_events_count || 0}</span>
                      <span className="text-[11px] text-muted-foreground block">Audit Events Logged</span>
                    </div>
                  </div>
                </div>
              )}

              {/* ============================================================== */}
              {/* 7. PLATFORM ADMIN VIEW (Technical Only) */}
              {/* ============================================================== */}
              {roleView === "PLATFORM_ADMIN" && (
                <div className="space-y-4">
                  <div className="p-3 bg-blue-500/10 border border-blue-500/30 text-blue-700 dark:text-blue-300 rounded-lg text-xs flex items-center gap-2">
                    <Key className="w-4 h-4 shrink-0" />
                    Technical System-Integrity Diagnostics &mdash; Segregated from Consequential Judicial Determinations
                  </div>

                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-2.5 text-xs font-mono">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Technical ID:</span>
                      <strong className="text-foreground">{data.technical_document_id}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Storage Vault:</span>
                      <span className="text-emerald-600 font-bold">{data.storage_vault}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block mb-1">SHA-256 Hash:</span>
                      <div className="p-2 bg-card rounded border border-border break-all flex justify-between items-center">
                        <span>{data.sha256_hash}</span>
                        <button onClick={() => copyHash(data.sha256_hash)} className="text-primary font-sans hover:underline ml-2">
                          {copiedHash ? "Copied" : "Copy"}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ============================================================== */}
              {/* 7. ACCUSED USER & FAMILY GUARDIAN VIEW */}
              {/* ============================================================== */}
              {(roleView === "ACCUSED_USER" || roleView === "FAMILY_GUARDIAN") && (
                <div className="space-y-4">
                  <div className="p-5 bg-card border border-border rounded-xl text-center space-y-3">
                    <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
                    <h4 className="text-lg font-serif font-bold text-foreground">
                      {data.document_name}
                    </h4>
                    <span className="inline-block px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                      Status: {data.simple_status || data.high_level_status}
                    </span>
                    <p className="text-xs text-muted-foreground max-w-md mx-auto">
                      {data.next_step || data.next_action}
                    </p>
                  </div>
                  <div className="p-4 bg-muted/40 rounded-xl text-xs text-muted-foreground text-center">
                    {data.support_note}
                  </div>
                </div>
              )}

              {/* ============================================================== */}
              {/* 8. DLSA & SUPERVISING LEGAL OFFICER VIEW */}
              {/* ============================================================== */}
              {(roleView === "DLSA_OFFICER" || roleView === "SUPERVISING_LEGAL_OFFICER") && (
                <div className="space-y-5">
                  <div className="p-4 bg-secondary/20 border border-border rounded-xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground">
                        Official Legal Aid Docket Record
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                          {data.verification_status}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
                          Version {data.current_document_version}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs pt-1">
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Source Authority:</span>
                        <strong className="text-foreground">{data.source_authority}</strong>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Uploaded By:</span>
                        <span className="text-foreground">{data.uploaded_by}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[11px]">Completeness Impact:</span>
                        <span className="text-emerald-600 font-semibold">{data.statutory_assessment_impact?.document_completeness_impact || data.document_completeness_impact}</span>
                      </div>
                    </div>
                  </div>

                  {/* Actions & Verification Buttons */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
                    {onDownload && (
                      <button
                        onClick={() => onDownload(data.document_id, data.document_name)}
                        className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border border-border transition-colors"
                      >
                        <Download className="w-3.5 h-3.5 text-primary" /> Download Certified Record
                      </button>
                    )}

                    <div className="flex items-center gap-2">
                      {user?.role === "DLSA_OFFICER" && data.verification_status !== "Verified" && data.verification_status !== "Reviewed" && onReview && (
                        <button
                          onClick={() => onReview(data.document_id)}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-sm transition-colors"
                          title="Mark reviewed for legal-aid intake processing"
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" /> Review Document
                        </button>
                      )}
                      {user?.role === "SUPERVISING_LEGAL_OFFICER" && data.verification_status !== "Verified" && onVerify && (
                        <button
                          onClick={() => onVerify(data.document_id)}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 shadow-sm transition-colors"
                          title="Supervisory verification: confirm presence and update case completeness"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" /> Supervisory Verify
                        </button>
                      )}
                      {canReview && onReprocess && (
                        <button
                          onClick={() => onReprocess(data.document_id)}
                          className="px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border border-primary/20 transition-colors"
                        >
                          <RefreshCw className="w-3.5 h-3.5" /> Re-Scan Text
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
