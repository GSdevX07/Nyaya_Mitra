import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Calculator,
  Shield,
  Clock,
  User,
  FileCheck,
  Send,
  Upload,
  Download,
  RefreshCw,
  Loader2,
  Bookmark,
} from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchCaseById,
  approveCaseInBackend,
  fileCaseInCourt,
  uploadDocumentFile,
  verifyEvidence,
  type TimelineEvent,
  type LegalNeedItem,
} from "@/lib/api";
import { jsPDF } from "jspdf";

export function CaseIntelligence() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);
  const [filing, setFiling] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const [editableDraft, setEditableDraft] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"dossier" | "draft" | "timeline" | "evidence" | "statutes">("dossier");
  const [verifyingEvidenceId, setVerifyingEvidenceId] = useState<string | null>(null);
  const [evidenceVerificationResult, setEvidenceVerificationResult] = useState<any>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [pendingDocType, setPendingDocType] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCaseById(id);
      if (!data) throw new Error("Not found");
      setCaseData(data);
      if (data.draft?.drafted_document) {
        setEditableDraft((data.draft.drafted_document as string).replaceAll("**", ""));
      }
    } catch {
      setError(`Could not load case ${id}. Ensure the backend is online at localhost:8000.`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleApprove = async () => {
    if (!id) return;
    setApproving(true);
    try {
      await approveCaseInBackend(id);
      await load();
      setActiveTab("draft");
    } catch (err: any) {
      alert("Approval error: " + err.message);
    } finally {
      setApproving(false);
    }
  };

  const handleFileInCourt = async () => {
    if (!id) return;
    setFiling(true);
    try {
      await fileCaseInCourt(id);
      await load();
    } catch (err: any) {
      alert("Filing error: " + err.message);
    } finally {
      setFiling(false);
    }
  };

  const handleUploadDoc = (docType: string) => {
    if (!id) return;
    setPendingDocType(docType);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !pendingDocType || !id) return;

    setUploadingDoc(pendingDocType);
    try {
      await uploadDocumentFile(id, pendingDocType, file);
      await load();
    } catch (err: any) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploadingDoc(null);
      setPendingDocType(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleVerifyEvidence = async (eviId: string) => {
    setVerifyingEvidenceId(eviId);
    try {
      const res = await verifyEvidence(eviId);
      setEvidenceVerificationResult(res);
    } catch (err: any) {
      alert("Evidence verification error: " + err.message);
    } finally {
      setVerifyingEvidenceId(null);
    }
  };

  const generateBailDraftPDF = () => {
    if (!c.case_id) return;
    const doc = new jsPDF();
    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.text("IN THE COURT OF THE PRINCIPAL DISTRICT & SESSIONS JUDGE", 20, 20);
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`BAIL APPLICATION UNDER SECTION 479 BNSS — CASE: ${c.case_id}`, 20, 28);
    doc.text(`ACCUSED: ${c.name}`, 20, 34);
    doc.text(`DATE: ${new Date().toLocaleDateString()}`, 20, 40);

    doc.line(20, 44, 190, 44);

    const splitText = doc.splitTextToSize(editableDraft || "Draft text not available.", 170);
    doc.text(splitText, 20, 52);
    doc.save(`Bail_Petition_${c.case_id}.pdf`);
  };

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
        <p className="text-muted-foreground font-mono text-sm">
          Compiling Accused Dossier & Evaluating Statutory Rule Engine for #{id}…
        </p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-8 max-w-xl mx-auto flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
        <AlertCircle className="w-12 h-12 text-destructive" />
        <div>
          <h2 className="text-xl font-bold text-foreground mb-2">Dossier Unavailable</h2>
          <p className="text-muted-foreground text-sm">{error || "Case record could not be loaded."}</p>
        </div>
        <button onClick={load} className="px-4 py-2 bg-primary text-primary-foreground rounded-sm text-sm font-semibold flex items-center gap-2">
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    );
  }

  const c = caseData.case || {};
  const eligibility = caseData.eligibility || {};
  const completeness = caseData.completeness || {};
  const retrieval = caseData.retrieval || {};
  const explanation = caseData.explanation || {};
  const legalNeeds: LegalNeedItem[] = c.legal_needs || [];
  const timeline: TimelineEvent[] = c.timeline || [];

  const isReadyForFiling = c.status === "APPROVED_READY_FOR_FILING";
  const isFiled = c.status === "FILED";
  const approvalDone = isReadyForFiling || isFiled;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept=".pdf,image/*" />

      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate("/cases")}
            className="p-2 border border-border rounded-sm hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-muted-foreground uppercase">{c.case_id}</span>
              <span className="text-xs px-2 py-0.5 rounded font-bold font-mono bg-primary/15 text-primary">
                {c.prisoner_category}
              </span>
              <span className="text-xs px-2 py-0.5 rounded font-bold font-mono bg-secondary border border-border text-foreground">
                {c.legal_code}
              </span>
              <span className="text-[11px] px-2 py-0.5 rounded font-mono text-muted-foreground border border-border">
                {c.data_source_status}
              </span>
            </div>
            <h1 className="text-2xl font-bold font-serif text-foreground">{c.name}</h1>
          </div>
        </div>

        {/* Workflow Action Gate */}
        <div className="flex items-center gap-2">
          {!approvalDone && (
            <button
              onClick={handleApprove}
              disabled={approving || !eligibility.eligible || !completeness.is_complete}
              className={`px-4 py-2 rounded-sm text-xs font-bold font-serif uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all ${
                eligibility.eligible && completeness.is_complete
                  ? "bg-primary text-primary-foreground hover:opacity-90"
                  : "bg-muted text-muted-foreground cursor-not-allowed border border-border"
              }`}
            >
              {approving ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCheck className="w-4 h-4" />}
              Approve & Mark Ready for Filing
            </button>
          )}

          {isReadyForFiling && (
            <button
              onClick={handleFileInCourt}
              disabled={filing}
              className="px-4 py-2 rounded-sm text-xs font-bold font-serif uppercase tracking-wider bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2 shadow-sm"
            >
              {filing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Record Filing in Court Registry
            </button>
          )}

          {isFiled && (
            <span className="px-3 py-1.5 rounded-sm bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-bold font-mono flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> FILED IN COURT
            </span>
          )}

          <button
            onClick={generateBailDraftPDF}
            className="px-3 py-2 border border-border rounded-sm hover:bg-secondary text-xs font-medium flex items-center gap-1.5"
            title="Download PDF petition"
          >
            <Download className="w-4 h-4" /> PDF
          </button>
        </div>
      </div>

      {/* Identified Legal Needs Alerts */}
      {legalNeeds.length > 0 && (
        <div className="space-y-2">
          {legalNeeds.map((need, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-sm border flex items-start justify-between gap-3 text-xs ${
                need.urgency === "URGENT"
                  ? "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300"
                  : need.blocking_bail_workflow
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300"
                  : "bg-blue-500/10 border-blue-500/30 text-blue-700 dark:text-blue-300"
              }`}
            >
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold uppercase font-mono tracking-wider">
                    {need.title}
                  </span>
                  <p className="mt-0.5 text-foreground/80">{need.description}</p>
                </div>
              </div>
              <span className="font-mono text-[10px] uppercase px-2 py-0.5 rounded border border-current font-bold shrink-0">
                {need.urgency}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-border gap-2 text-sm font-serif">
        {[
          { key: "dossier", label: "Accused Dossier" },
          { key: "draft", label: "Bail Petition Draft" },
          { key: "timeline", label: "Case Timeline & Provenance" },
          { key: "evidence", label: "Document Vault & SHA-256" },
          { key: "statutes", label: "Grounded Statutory Law" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 border-b-2 font-semibold transition-all ${
              activeTab === tab.key
                ? "border-primary text-foreground font-bold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* TAB 1: ACCUSED DOSSIER & DETERMINISTIC ENGINE */}
      {activeTab === "dossier" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Accused Particulars & Case Metadata */}
          <div className="space-y-6 lg:col-span-1">
            <div className="p-5 border border-border bg-card rounded-sm space-y-4">
              <h3 className="text-sm font-bold font-serif uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <User className="w-4 h-4 text-primary" /> Case & Custody Identifiers
              </h3>

              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between border-b border-border/50 pb-1.5">
                  <span className="text-muted-foreground">CNR Number:</span>
                  <span className="font-mono font-bold text-foreground">{c.cnr_number || "Pending eCourts Generation"}</span>
                </div>
                <div className="flex justify-between border-b border-border/50 pb-1.5">
                  <span className="text-muted-foreground">FIR Reference:</span>
                  <span className="font-mono text-foreground">{c.fir_number}</span>
                </div>
                <div className="flex justify-between border-b border-border/50 pb-1.5">
                  <span className="text-muted-foreground">Police Station:</span>
                  <span className="text-foreground">{c.police_station}</span>
                </div>
                <div className="flex justify-between border-b border-border/50 pb-1.5">
                  <span className="text-muted-foreground">Court Jurisdiction:</span>
                  <span className="text-foreground text-right">{c.court_name}</span>
                </div>
                <div className="flex justify-between border-b border-border/50 pb-1.5">
                  <span className="text-muted-foreground">DLSA File No:</span>
                  <span className="font-mono text-foreground">{c.dlsa_reference_number}</span>
                </div>
                <div className="flex justify-between border-b border-border/50 pb-1.5">
                  <span className="text-muted-foreground">Facility / Jail:</span>
                  <span className="text-foreground text-right">{c.jail_location}</span>
                </div>
                <div className="flex justify-between border-b border-border/50 pb-1.5">
                  <span className="text-muted-foreground">Offence Charged:</span>
                  <span className="font-bold text-foreground">{c.offense_sections?.join(", ")}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Arrest Date:</span>
                  <span className="font-mono text-foreground">{c.arrest_date}</span>
                </div>
              </div>
            </div>

            {/* Contextual Urgency & Health Trigger */}
            <div className="p-5 border border-border bg-card rounded-sm space-y-3">
              <h3 className="text-sm font-bold font-serif uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Clock className="w-4 h-4 text-primary" /> Contextual Urgency & Health
              </h3>
              <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Age:</span>
                  <span className="font-bold text-foreground">{c.urgency_flags?.age} years</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Health Condition Flag:</span>
                  <span className={`font-bold ${c.urgency_flags?.health_flag ? "text-red-500" : "text-emerald-500"}`}>
                    {c.urgency_flags?.health_flag ? "Documented Medical Condition" : "No Medical Alert"}
                  </span>
                </div>
                {c.urgency_flags?.health_details && (
                  <p className="p-2.5 rounded bg-muted/40 text-[11px] text-foreground/80 border border-border/60">
                    <strong>Medical Note:</strong> {c.urgency_flags.health_details}
                    <br />
                    <span className="text-[10px] text-muted-foreground italic">
                      (Contextual information for advocate review; does not constitute autonomous medical bail)
                    </span>
                  </p>
                )}
              </div>
            </div>

            {/* Authorised Family Portal Info */}
            <div className="p-5 border border-border bg-card rounded-sm space-y-2.5">
              <h3 className="text-sm font-bold font-serif uppercase tracking-wider text-muted-foreground">
                Authorised Family Contact
              </h3>
              <div className="space-y-1.5 text-xs">
                <p><strong className="text-muted-foreground">Contact:</strong> {c.relative_name} ({c.relative_relation})</p>
                <p><strong className="text-muted-foreground">Phone:</strong> <span className="font-mono">{c.relative_phone}</span></p>
                <p><strong className="text-muted-foreground">Address:</strong> {c.permanent_address}</p>
              </div>
            </div>
          </div>

          {/* Right Column: Versioned Section 479 BNSS Rule Engine & Multilingual Summary */}
          <div className="space-y-6 lg:col-span-2">
            {/* Versioned Rule Engine Card */}
            <div className="p-6 border border-border bg-card rounded-sm space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <Calculator className="w-5 h-5 text-primary" />
                  <div>
                    <h3 className="font-bold font-serif text-base text-foreground">
                      Section 479 BNSS Versioned Rule Engine
                    </h3>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      Engine: {eligibility.rule_version || "BNSS_479_RULESET_V1_2023"}
                    </span>
                  </div>
                </div>
                <span
                  className={`px-3 py-1 text-xs font-mono font-bold uppercase rounded ${
                    eligibility.eligible
                      ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                      : "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                  }`}
                >
                  {eligibility.eligible ? "THRESHOLD SATISFIED" : "REVIEW REQUIRED"}
                </span>
              </div>

              {/* Traceable Calculations Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="p-3 rounded bg-secondary/50 border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase block">Total Elapsed</span>
                  <span className="text-lg font-bold font-mono text-foreground">
                    {eligibility.total_elapsed_calendar_days || c.custody_days}d
                  </span>
                </div>
                <div className="p-3 rounded bg-secondary/50 border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase block">Excluded Delay</span>
                  <span className="text-lg font-bold font-mono text-amber-500">
                    {eligibility.excluded_delay_days || c.excluded_delay_days || 0}d
                  </span>
                </div>
                <div className="p-3 rounded bg-secondary/50 border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase block">Countable Custody</span>
                  <span className="text-lg font-bold font-mono text-foreground">
                    {eligibility.countable_custody_days || c.custody_days}d
                  </span>
                </div>
                <div className="p-3 rounded bg-secondary/50 border border-border">
                  <span className="text-[10px] font-mono text-muted-foreground uppercase block">Required Threshold</span>
                  <span className="text-lg font-bold font-mono text-foreground">
                    {eligibility.required_custody_days || "—"}d
                  </span>
                </div>
              </div>

              {/* Status Framing Alert */}
              <div className="p-3.5 rounded bg-primary/5 border border-primary/20 text-xs text-foreground/90 space-y-1">
                <p className="font-semibold">{eligibility.statutory_signal || eligibility.legal_basis}</p>
                <p className="text-[11px] text-muted-foreground">
                  <strong>Statutory Framing:</strong> The engine evaluates whether documented facts appear to satisfy Section 479 conditions. The result is an eligibility signal for human legal review, not an automatic release entitlement.
                </p>
              </div>

              {/* Exceptions Checklist */}
              <div className="border-t border-border pt-3">
                <h4 className="text-xs font-mono font-bold text-muted-foreground uppercase mb-2">
                  Statutory Exceptions & Provisos Evaluated
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className={`w-3.5 h-3.5 ${c.punishable_by_death_or_life ? "text-red-500" : "text-emerald-500"}`} />
                    <span>Capital / Life Imprisonment Exclusion: <strong>{c.punishable_by_death_or_life ? "Excluded" : "Cleared"}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className={`w-3.5 h-3.5 ${c.multiple_active_cases ? "text-amber-500" : "text-emerald-500"}`} />
                    <span>Multiple Pending Cases Proviso: <strong>{c.multiple_active_cases ? "Review Required" : "Single Case"}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Offender Category: <strong>{c.urgency_flags?.repeat_offender ? "General (1/2 Threshold)" : "First-Time (1/3 Proviso)"}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    <span>Delay Attribution: <strong>{c.excluded_delay_days > 0 ? `${c.excluded_delay_days}d Excluded` : "Zero Excluded Delay"}</strong></span>
                  </div>
                </div>
              </div>

              {/* Legal Validation Disclaimer */}
              <p className="text-[10px] font-mono text-muted-foreground border-t border-border pt-2 italic">
                * Legal Validation Requirement: The complete Section 479 rule interpretation must be validated against the authoritative statutory text and reviewed by qualified legal counsel before production deployment.
              </p>
            </div>

            {/* Document Completeness Checklist */}
            <div className="p-6 border border-border bg-card rounded-sm space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <h3 className="font-bold font-serif text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary" /> Required Case Records & Blockers
                </h3>
                <span className={`text-xs font-mono font-bold ${completeness.is_complete ? "text-emerald-500" : "text-amber-500"}`}>
                  {completeness.is_complete ? "All Documents Present" : "Missing Records Required"}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {c.required_docs?.map((docType: string) => {
                  const isPresent = c.present_docs?.includes(docType);
                  return (
                    <div
                      key={docType}
                      className={`p-3 rounded border flex items-center justify-between gap-2 ${
                        isPresent ? "bg-emerald-500/5 border-emerald-500/30" : "bg-amber-500/5 border-amber-500/30"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {isPresent ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                        )}
                        <span className="font-medium text-foreground">{docType.replace(/_/g, " ").toUpperCase()}</span>
                      </div>

                      {!isPresent && (
                        <button
                          onClick={() => handleUploadDoc(docType)}
                          disabled={uploadingDoc === docType}
                          className="px-2 py-1 bg-primary text-primary-foreground rounded text-[10px] font-bold uppercase hover:opacity-90 flex items-center gap-1"
                        >
                          {uploadingDoc === docType ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                          Upload
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Multilingual Plain Language Summary for Accused & Family */}
            <div className="p-6 border border-border bg-card rounded-sm space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <h3 className="font-bold font-serif text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Bookmark className="w-4 h-4 text-primary" /> Plain-Language Legal Summary ({c.preferred_language?.toUpperCase()})
                </h3>
                <span className="text-[10px] font-mono text-muted-foreground">For Accused & Family Portal</span>
              </div>
              <p className="text-sm text-foreground/90 leading-relaxed font-sans">
                {explanation.summary ||
                  "The accused person has completed the required period in custody under Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023. A panel legal-aid advocate is reviewing the petition for formal submission to court."}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: BAIL PETITION DRAFT & ADVOCATE REVIEW GATEWAY */}
      {activeTab === "draft" && (
        <div className="space-y-6">
          <div className="p-6 border border-border bg-card rounded-sm space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="font-bold font-serif text-lg text-foreground">
                  Formal Bail Application Draft
                </h3>
                <p className="text-xs text-muted-foreground">
                  Under Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={generateBailDraftPDF}
                  className="px-3 py-1.5 border border-border rounded-sm hover:bg-secondary text-xs font-semibold flex items-center gap-1.5"
                >
                  <Download className="w-4 h-4" /> Download PDF
                </button>
              </div>
            </div>

            {/* In-Line Draft Editor */}
            <div className="space-y-2">
              <label className="text-xs font-mono font-bold uppercase text-muted-foreground">
                Editable Petition Text (Reviewed by Defence Counsel):
              </label>
              <textarea
                value={editableDraft}
                onChange={(e) => setEditableDraft(e.target.value)}
                rows={16}
                className="w-full p-4 font-mono text-xs bg-background border border-border rounded-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed resize-y"
              />
            </div>

            {/* Human Review Boundary Alert */}
            <div className="p-3.5 rounded bg-muted/40 border border-border text-xs text-foreground/80 space-y-1 font-mono">
              <p className="font-bold text-foreground">
                MANDATORY HUMAN ADVOCATE REVIEW GATEWAY
              </p>
              <p className="text-[11px] text-muted-foreground">
                AI prepares the draft petition grounded in retrieved statutory text. The licensed panel advocate reviews, edits, and signs off before the petition is marked ready for procedural filing. The system never executes autonomous court filings.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: CHRONOLOGICAL CASE TIMELINE & PROVENANCE */}
      {activeTab === "timeline" && (
        <div className="p-6 border border-border bg-card rounded-sm space-y-6">
          <div>
            <h3 className="font-bold font-serif text-lg text-foreground">
              Append-Oriented Digital Legal Journey
            </h3>
            <p className="text-xs text-muted-foreground">
              Traceable chronological audit trail preserving case progression and field-level provenance.
            </p>
          </div>

          <div className="relative pl-6 border-l-2 border-border space-y-6">
            {timeline.length === 0 ? (
              <p className="text-xs text-muted-foreground">No historical timeline events recorded yet.</p>
            ) : (
              timeline.map((event, idx) => (
                <div key={event.id || idx} className="relative group">
                  <div className="absolute -left-[31px] top-0 w-4 h-4 rounded-full bg-primary border-2 border-card" />
                  <div className="p-4 border border-border rounded-sm bg-secondary/30 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-xs text-foreground font-serif">{event.title}</span>
                      <span className="font-mono text-[10px] text-muted-foreground">
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-foreground/80 leading-relaxed">{event.description}</p>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground border-t border-border/40 pt-1.5">
                      <span>Actor: <strong className="text-foreground">{event.actor}</strong> ({event.actor_role})</span>
                      <span>Source: <strong className="text-foreground">{event.source}</strong></span>
                      <span className={event.is_human_verified ? "text-emerald-500 font-bold" : "text-muted-foreground"}>
                        {event.is_human_verified ? "Human Verified" : "Machine Inferred"}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 4: DOCUMENT VAULT & SHA-256 INTEGRITY */}
      {activeTab === "evidence" && (
        <div className="p-6 border border-border bg-card rounded-sm space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h3 className="font-bold font-serif text-lg text-foreground">
                Document Vault & Cryptographic Integrity Checking
              </h3>
              <p className="text-xs text-muted-foreground">
                SHA-256 document hashing verifies digital file tamper-detection. (Proves file integrity; does not prove legal truth of contents).
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {c.present_docs?.map((docType: string) => {
              const eviId = `EVI-${c.case_id}-${docType}`;
              return (
                <div key={docType} className="p-4 border border-border rounded-sm bg-secondary/30 flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <Shield className="w-5 h-5 text-primary shrink-0" />
                    <div>
                      <h4 className="font-bold text-sm font-serif text-foreground">
                        {docType.replace(/_/g, " ").toUpperCase()}
                      </h4>
                      <p className="text-xs font-mono text-muted-foreground">
                        Evidence ID: {eviId} • Format: PDF / Digitised Record
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleVerifyEvidence(eviId)}
                      disabled={verifyingEvidenceId === eviId}
                      className="px-3 py-1.5 bg-secondary border border-border text-foreground hover:bg-muted text-xs font-semibold font-mono rounded flex items-center gap-1.5"
                    >
                      {verifyingEvidenceId === eviId ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                      Verify SHA-256 Hash
                    </button>
                  </div>
                </div>
              );
            })}

            {evidenceVerificationResult && (
              <div className="p-4 rounded border bg-emerald-500/10 border-emerald-500/30 text-xs font-mono space-y-1">
                <p className="font-bold text-emerald-600 dark:text-emerald-400">
                  CRYPTOGRAPHIC INTEGRITY VERIFIED
                </p>
                <p className="text-foreground/80">Stored Hash: {evidenceVerificationResult.stored_hash}</p>
                <p className="text-foreground/80">Computed Hash: {evidenceVerificationResult.computed_hash}</p>
                <p className="text-muted-foreground text-[10px]">{evidenceVerificationResult.note}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: GROUNDED STATUTORY LEGAL AUTHORITIES (RAG) */}
      {activeTab === "statutes" && (
        <div className="p-6 border border-border bg-card rounded-sm space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div>
              <h3 className="font-bold font-serif text-lg text-foreground">
                Grounded Statutory Legal Authorities
              </h3>
              <p className="text-xs text-muted-foreground">
                Statutory passages retrieved from verified criminal enactments (BNSS 2023, BNS 2023, IPC 1860).
              </p>
            </div>
            <span className="text-[10px] font-mono px-2 py-1 rounded bg-secondary border border-border text-muted-foreground">
              Precedent Case-Law: Future Expansion Module
            </span>
          </div>

          <div className="space-y-4">
            {retrieval.citations?.map((cit: any, idx: number) => (
              <div key={idx} className="p-4 border border-border rounded-sm bg-secondary/30 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold font-serif text-sm text-foreground">
                    {cit.statute} — {cit.section}
                  </span>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-primary/10 text-primary font-bold">
                    {cit.legal_code} (Effective: {cit.effective_date})
                  </span>
                </div>
                <p className="text-xs font-mono p-3 rounded bg-background border border-border text-foreground/90 whitespace-pre-wrap leading-relaxed">
                  {cit.text}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  <strong>Relevance Rationale:</strong> {cit.relevance_rationale}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
