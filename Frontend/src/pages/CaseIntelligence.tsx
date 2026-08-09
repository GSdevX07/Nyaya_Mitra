import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, FileText, CheckCircle2, AlertTriangle, AlertCircle, Scale, Calculator, Link as LinkIcon, Download, PenTool, Check, X, Activity, Loader2, RefreshCw } from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import { fetchCaseById, approveCaseInBackend, uploadDocumentFile } from "@/lib/api";
import { jsPDF } from "jspdf";

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(status: string) {
  if (status.includes("FILED") || status.includes("RELEASED") || status.includes("ORDER_PASSED")) return "text-foreground";
  if (status.includes("APPROVED") || status.includes("DRAFT_READY") || status.includes("ELIGIBLE")) return "text-accent";
  if (status.includes("MISSING") || status.includes("MANUAL_REVIEW")) return "text-muted-foreground";
  return "text-muted-foreground";
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CaseIntelligence() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);
  const [approvalDone, setApprovalDone] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const [editableDraft, setEditableDraft] = useState<string>("");

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
      if (data.draft_ready && data.draft?.drafted_document) {
        setEditableDraft((data.draft.drafted_document as string).replaceAll("**", ""));
      }
    } catch {
      setError(`Could not load case ${id}. Is the backend running at localhost:8000?`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const handleApprove = async () => {
    if (!id) return;
    setApproving(true);
    try {
      await approveCaseInBackend(id);
      setApprovalDone(true);
      await load(); // Refresh data to reflect new FILED status
    } finally {
      setApproving(false);
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
      await load(); // Re-run orchestrator to get updated completeness
    } catch (err: any) {
      alert("Failed to upload document: " + err.message);
    } finally {
      setUploadingDoc(null);
      setPendingDocType(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const generatePDF = () => {
    if (!c.case_id) return;
    const doc = new jsPDF();
    doc.setFont("helvetica", "bold");
    doc.text(`REQUEST FOR MISSING DOCUMENTS`, 20, 20);
    doc.setFont("helvetica", "normal");
    doc.text(`Case ID: ${c.case_id}`, 20, 30);
    doc.text(`Date: ${new Date().toLocaleDateString()}`, 20, 40);
    doc.text(`The following documents are missing and required to proceed:`, 20, 50);
    
    let y = 60;
    (caseData?.completeness?.missing_docs || []).forEach((docName: string, index: number) => {
      doc.text(`${index + 1}. ${docName.replace(/_/g, " ")}`, 25, y);
      y += 10;
    });
    
    doc.text("Please submit these documents to the system immediately.", 20, y + 10);
    doc.save(`Missing_Docs_Request_${c.case_id}.pdf`);
  };

  // ── Loading / Error states ────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <Loader2 className="w-8 h-8 text-accent animate-spin" />
        <p className="text-muted-foreground">Running 8-agent pipeline for Case #{id}…</p>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-8 max-w-xl mx-auto flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
        <AlertCircle className="w-12 h-12 text-destructive" />
        <div>
          <h2 className="text-xl font-semibold text-primary mb-2">Backend Connection Lost</h2>
          <p className="text-muted-foreground text-sm">{error || "Live case data unavailable."}</p>
        </div>
        <div className="flex gap-3">
          <button onClick={load} className="px-4 py-2 bg-accent text-accent-foreground rounded-sm text-sm font-medium flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Retry Connection
          </button>
          <button onClick={() => navigate(-1)} className="px-4 py-2 bg-secondary/50 text-primary rounded-sm text-sm font-medium">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // ── Destructure orchestrator response ─────────────────────────────────────
  const c = caseData.case || {};
  const eligibility = caseData.eligibility || {};
  const completeness = caseData.completeness || {};
  const retrieval = caseData.retrieval || {};
  // const draft = caseData.draft || {};
  const explanation = caseData.explanation || {};
  const statusTracking = caseData.status_tracking || {};
  const agentLog = caseData.agent_activity_log || [];
  const draftReady = caseData.draft_ready || false;
  const llmProvider: string = caseData.llm_provider || "";

  const missingDocs: string[] = completeness.missing_docs || [];
  const legalSources: any[] = retrieval.sources || [];
  const currentStatus: string = c.status || statusTracking.current_status || "DETECTED";
  const isManualReview = eligibility.legal_basis?.includes("MANUAL_REVIEW");

  // Build evidence chain from eligibility data
  const evidenceChain = [
    { id: 1, type: "FACT", title: "Arrest & Custody Record", description: `Arrested: ${c.arrest_date} | In custody: ${eligibility.custody_days_served ?? c.custody_days} days` },
    { id: 2, type: "LEGAL_SOURCE", title: "Section 479 BNSS", description: `Threshold: ${(eligibility.threshold_fraction * 100).toFixed(0)}% of max sentence (${eligibility.required_custody_days} days required)` },
    { id: 3, type: "CALCULATION", title: "Threshold Calculation", description: `ceil(${c.max_sentence_days_for_offense} × ${eligibility.threshold_fraction?.toFixed(4)}) = ${eligibility.required_custody_days} days` },
    {
      id: 4, type: eligibility.eligible ? "AI_INTERPRETATION" : "FACT",
      title: eligibility.eligible ? "ELIGIBLE — Threshold Exceeded" : "NOT YET ELIGIBLE",
      description: eligibility.eligible
        ? `${eligibility.days_overdue} days overdue — bail application recommended`
        : `${eligibility.required_custody_days - (eligibility.custody_days_served ?? 0)} more days needed`
    },
  ];

  return (
    <div className="p-4 md:p-8 w-full space-y-12 animate-in fade-in duration-300">

      {/* Header */}
      <div className="space-y-6">
        <Link to="/cases" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Cases Directory
        </Link>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-semibold tracking-tight text-primary">CASE #{c.case_id}</h1>
              {isManualReview ? (
                <span className="px-3 py-1 rounded-sm text-xs font-semibold border uppercase tracking-wider bg-muted text-muted-foreground border-border">MANUAL REVIEW</span>
              ) : eligibility.eligible ? (
                <span className="px-3 py-1 rounded-sm text-xs font-semibold border uppercase tracking-wider bg-muted text-foreground border-border">ELIGIBLE</span>
              ) : (
                <span className="px-3 py-1 rounded-sm text-xs font-semibold border uppercase tracking-wider bg-secondary/50 text-muted-foreground border-border">IN PROGRESS</span>
              )}
            </div>

            <div className="flex flex-wrap gap-6 text-sm">
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Case ID</span>
                <p className="text-primary font-mono font-medium">{c.case_id}</p>
              </div>
              <div className="w-px bg-secondary" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Custody Duration</span>
                <p className="text-primary font-medium text-lg">{c.custody_days} days</p>
              </div>
              <div className="w-px bg-secondary" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Offence</span>
                <p className="text-primary font-medium">{c.offense_sections?.join(", ")}</p>
              </div>
              <div className="w-px bg-secondary" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Age</span>
                <p className="text-primary font-medium">{c.urgency_flags?.age} yrs {c.urgency_flags?.health_flag ? "🏥" : ""}</p>
              </div>
              <div className="w-px bg-secondary" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Facility</span>
                <p className="text-primary font-medium">{c.jail_location}</p>
              </div>
            </div>
          </div>

          <div className="bg-card/70 border border-border px-6 py-4 rounded text-right">
            <div className="text-xs text-muted-foreground uppercase tracking-wider font-semibold mb-1">Case Status</div>
            <div className={`text-lg font-semibold ${statusColor(currentStatus)}`}>{currentStatus.replace(/_/g, " ")}</div>
            {eligibility.eligible && eligibility.days_overdue > 0 && (
              <div className="text-xs text-destructive mt-1">{eligibility.days_overdue} DAYS OVERDUE</div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left Column */}
        <div className="lg:col-span-2 space-y-8">

          {/* Why Flagged */}
          <section className="p-8 rounded border border-border bg-card shadow-sm space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-5"><AlertCircle className="w-48 h-48" /></div>
            <div className="relative z-10">
              <h2 className="text-xl font-medium tracking-tight text-primary mb-6 uppercase">Why this case requires attention</h2>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-foreground shrink-0 mt-0.5" />
                  <span className="text-primary leading-relaxed">
                    Served <strong>{eligibility.custody_days_served}</strong> days against a maximum sentence of <strong>{c.max_sentence_days_for_offense}</strong> days ({c.offense_sections?.join(", ")}).
                  </span>
                </div>
                <div className="flex items-start gap-3">
                  <Scale className="w-5 h-5 text-muted-foreground shrink-0 mt-0.5" />
                  <span className="text-primary leading-relaxed">{eligibility.legal_basis}</span>
                </div>
                {eligibility.eligible && (
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-foreground shrink-0 mt-0.5" />
                    <span className="text-primary leading-relaxed">
                      Required threshold: <strong>{eligibility.required_custody_days}</strong> days (using <code className="text-accent text-xs">math.ceil</code> for legal safety).
                      Overdue by <strong className="text-destructive">{eligibility.days_overdue}</strong> days.
                    </span>
                  </div>
                )}
                {isManualReview && (
                  <div className="mt-4 p-4 bg-muted border border-border rounded-sm text-muted-foreground text-sm">
                    ⚠️ This case requires manual legal review before any bail action can be taken.
                  </div>
                )}
              </div>

              {missingDocs.length > 0 && (
                <div className="mt-6 pt-6 border-t border-border space-y-3">
                  {missingDocs.map((doc: string) => (
                    <div key={doc} className="flex items-start gap-3 text-muted-foreground">
                      <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">Missing: <strong>{doc.replace(/_/g, " ")}</strong></span>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-8 flex gap-4 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                <div className="flex items-center gap-1"><FileText className="w-4 h-4 text-foreground" /> FACT</div>
                <div className="flex items-center gap-1"><Calculator className="w-4 h-4 text-muted-foreground" /> CALCULATION</div>
                <div className="flex items-center gap-1"><Scale className="w-4 h-4 text-muted-foreground" /> LEGAL SOURCE</div>
                <div className="flex items-center gap-1"><Activity className="w-4 h-4 text-accent" /> AI INTERPRETATION</div>
              </div>
            </div>
          </section>

          {/* Evidence Chain */}
          <section className="space-y-4">
            <h2 className="text-xl font-medium tracking-tight uppercase text-primary flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-accent" /> Evidence Chain
            </h2>
            <div className="p-6 rounded border border-border bg-card shadow-sm space-y-6 relative">
              <div className="absolute left-8 top-10 bottom-10 w-px bg-secondary" />
              {evidenceChain.map((node) => (
                <div key={node.id} className="relative z-10 pl-10">
                  <div className={`absolute left-0 top-1.5 w-4 h-4 rounded-sm border-2 ${
                    node.type === "FACT" ? "border-emerald-500 bg-background" :
                    node.type === "CALCULATION" ? "border-blue-500 bg-background" :
                    node.type === "LEGAL_SOURCE" ? "border-amber-500 bg-background" :
                    "border-accent bg-accent"
                  }`} />
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">{node.type}</div>
                  <div className="text-primary font-medium">{node.title}</div>
                  <div className="text-sm text-muted-foreground mt-1">{node.description}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Legal Sources (RAG) */}
          {legalSources.length > 0 && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-primary flex items-center gap-2">
                <Scale className="w-5 h-5 text-accent" /> Legal Evidence
                <span className="text-xs font-normal text-muted-foreground ml-2 normal-case">Grounded Legal Retrieval — keyword/indexed</span>
              </h2>
              {legalSources.map((source: any, idx: number) => (
                <div key={idx} className="p-6 rounded border border-border bg-card shadow-sm space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-lg font-medium text-primary mb-1">{source.section || source.title}</div>
                      <div className="text-xs text-muted-foreground uppercase tracking-wider">{source.source || "BNSS 2023"}</div>
                    </div>
                    <div className="bg-muted text-foreground border border-border px-3 py-1 rounded-sm text-xs font-semibold">
                      {source.relevance_score ? `${(source.relevance_score * 100).toFixed(0)}% RELEVANCE` : "HIGH RELEVANCE"}
                    </div>
                  </div>
                  <div className="p-4 bg-muted rounded-sm border border-border text-sm text-muted-foreground font-serif leading-relaxed italic">
                    "{source.passage || source.content}"
                  </div>
                  {source.reasoning && (
                    <div>
                      <div className="text-xs font-medium text-accent uppercase tracking-wider mb-2">Why this source matters</div>
                      <p className="text-sm text-primary">{source.reasoning}</p>
                    </div>
                  )}
                </div>
              ))}
            </section>
          )}

          {/* Draft */}
          {draftReady && editableDraft && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-primary flex items-center gap-2">
                <FileText className="w-5 h-5 text-accent" /> Auto-Generated Bail Application Draft
              </h2>
              <textarea
                value={editableDraft}
                onChange={(e) => setEditableDraft(e.target.value)}
                className="w-full h-[400px] p-6 rounded border border-accent/20 bg-accent/5 font-serif text-sm text-primary leading-relaxed whitespace-pre-wrap focus:outline-none focus:ring-1 focus:ring-accent resize-y"
              />
            </section>
          )}

          {/* Plain-language explanation */}
          {explanation.explanation && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-primary flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent" /> Family Explanation
                <span className="text-xs font-normal text-muted-foreground normal-case ml-2">Language: {c.preferred_language}</span>
              </h2>
              <div className="space-y-4">
                <div className="p-6 rounded border border-border bg-card shadow-sm text-foreground leading-relaxed">
                  {explanation.explanation as string}
                </div>
                
                {explanation.english_translation && explanation.english_translation !== explanation.explanation && (
                  <div className="p-5 rounded border border-border bg-muted text-muted-foreground leading-relaxed relative">
                    <div className="absolute -top-2.5 left-4 px-2 py-0.5 bg-background border border-border rounded text-[10px] uppercase tracking-widest text-accent font-medium">
                      English Translation
                    </div>
                    <div className="pt-2 text-sm">
                      {explanation.english_translation as string}
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Agent Activity Log */}
          {agentLog.length > 0 && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-primary flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent" /> Agent Execution Trace
                <span className="text-xs font-normal text-muted-foreground normal-case ml-2">Logged pipeline execution</span>
              </h2>

              {/* LLM Provider Badge — visible fault tolerance demo */}
              {llmProvider && (
                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-sm border text-xs font-semibold ${
                  llmProvider.includes("Groq") ? "bg-muted border-emerald-500/30 text-foreground" :
                  llmProvider.includes("Ollama") ? "bg-muted border-border text-muted-foreground" :
                  "bg-secondary/50 border-border text-muted-foreground"
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-sm ${
                    llmProvider.includes("Groq") ? "bg-emerald-400" :
                    llmProvider.includes("Ollama") ? "bg-amber-400" : "bg-white/30"
                  }`} />
                  LLM PROVIDER: {llmProvider}
                </div>
              )}

              <div className="p-6 rounded border border-border bg-card shadow-sm space-y-3">
                {agentLog.map((entry: any, idx: number) => (
                  <div key={idx} className="flex items-center gap-4 text-sm">
                    <span className={`w-16 text-xs font-bold uppercase text-right shrink-0 ${
                      entry.status === "DONE" ? "text-foreground" :
                      entry.status === "SKIPPED" ? "text-muted-foreground" :
                      entry.status === "RUNNING" ? "text-accent" : "text-muted-foreground"
                    }`}>{entry.status}</span>
                    <span className="font-mono text-muted-foreground w-36 shrink-0">{entry.agent}</span>
                    <span className="text-muted-foreground">{entry.detail}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Right Column */}
        <div className="space-y-8">

          {/* Document Readiness */}
          <section className="p-6 rounded border border-border bg-card shadow-sm space-y-6">
            <h2 className="text-lg font-medium tracking-tight uppercase text-primary">Document Readiness</h2>

            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept=".pdf,image/png,image/jpeg,image/jpg" 
              onChange={handleFileChange} 
            />

            <div className="space-y-3">
              {(c.required_docs || []).map((doc: string) => {
                const isPresent = (c.present_docs || []).includes(doc);
                return (
                  <div key={doc} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {isPresent ? (
                        <CheckCircle2 className="w-4 h-4 text-foreground" />
                      ) : (
                        <X className="w-4 h-4 text-destructive" />
                      )}
                      <span className={`text-sm ${isPresent ? "text-primary" : "text-muted-foreground"}`}>
                        {doc.replace(/_/g, " ")}
                      </span>
                    </div>
                    {!isPresent && (
                      <button
                        onClick={() => handleUploadDoc(doc)}
                        disabled={uploadingDoc === doc}
                        className="text-xs text-accent hover:text-accent/80 font-medium flex items-center gap-1"
                      >
                        {uploadingDoc === doc ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                        Upload
                      </button>
                    )}
                  </div>
                );
              })}
            </div>

            {missingDocs.length > 0 && (
              <div className="mt-4 p-4 bg-accent/5 border border-accent/10 rounded-sm">
                <div className="text-xs font-medium text-accent uppercase tracking-wider mb-2">Action Required</div>
                <p className="text-xs text-muted-foreground mb-3">Upload missing documents to trigger the Completeness Agent and unlock the drafting pipeline.</p>
                <button 
                  onClick={generatePDF}
                  className="w-full py-2 bg-secondary/50 hover:bg-secondary text-primary text-xs font-medium rounded transition-colors flex items-center justify-center gap-2"
                >
                  <Download className="w-3 h-3" /> Generate Request PDF
                </button>
              </div>
            )}
          </section>

          {/* Case Timeline (from status tracking + state) */}
          <section className="p-6 rounded border border-border bg-card shadow-sm space-y-6">
            <h2 className="text-lg font-medium tracking-tight uppercase text-primary">Case Timeline</h2>
            <div className="space-y-4 relative">
              <div className="absolute left-2 top-2 bottom-2 w-px bg-secondary" />
              {[
                { title: "Arrested", date: c.arrest_date, done: true },
                { title: "BNSS 479 Threshold Evaluated", date: "Automated", done: true },
                { title: "Documents Verified", date: "Completeness Agent", done: missingDocs.length === 0 },
                { title: "Bail Draft Generated", date: "Drafting Agent", done: draftReady },
                { title: "Lawyer Review", date: "Human Gate", done: currentStatus === "APPROVED" || currentStatus === "FILED" },
                { title: "Filed in Court", date: "Status Tracking", done: currentStatus === "FILED" },
              ].map((event, idx) => (
                <div key={idx} className="relative z-10 pl-8">
                  <div className={`absolute left-1 top-1 w-2.5 h-2.5 rounded-sm ${event.done ? "bg-accent" : "bg-muted"}`} />
                  <div className="text-xs text-muted-foreground mb-0.5">{event.date}</div>
                  <div className={`text-sm font-medium ${event.done ? "text-primary" : "text-muted-foreground"}`}>{event.title}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Human Review Gateway */}
          <section className="p-6 rounded border border-accent/30 bg-accent/5 space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-accent/10 blur-3xl rounded-sm" />
            <h2 className="text-lg font-semibold tracking-tight uppercase text-primary relative z-10">Human Review Required</h2>

            <div className="space-y-3 relative z-10">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">AI analysis complete</span>
                <CheckCircle2 className="w-4 h-4 text-foreground" />
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Documents verified</span>
                {missingDocs.length === 0
                  ? <CheckCircle2 className="w-4 h-4 text-foreground" />
                  : <X className="w-4 h-4 text-destructive" />}
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Draft prepared</span>
                {draftReady
                  ? <CheckCircle2 className="w-4 h-4 text-foreground" />
                  : <X className="w-4 h-4 text-muted-foreground" />}
              </div>
            </div>

            <div className="pt-4 border-t border-border space-y-4 relative z-10">
              {approvalDone || currentStatus === "FILED" ? (
                <div className="text-center">
                  <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Status</div>
                  <div className="text-xl font-bold text-foreground">FILED</div>
                  <p className="text-xs text-muted-foreground mt-2">Bail application has been submitted to court.</p>
                </div>
              ) : isManualReview ? (
                <div className="text-center p-4 bg-muted border border-border rounded-sm text-muted-foreground text-sm">
                  This case requires manual review — automated approval is not permitted.
                </div>
              ) : (
                <>
                  <div className="p-3 bg-muted border border-border rounded text-xs text-muted-foreground leading-relaxed text-center">
                    "I confirm that I have reviewed the supporting documents and legal basis."
                  </div>
                  <div className="space-y-2">
                    <button
                      onClick={handleApprove}
                      disabled={approving || missingDocs.length > 0 || !draftReady || approvalDone || currentStatus === "FILED" || currentStatus === "APPROVED"}
                      className={`w-full py-3 font-semibold rounded transition-colors flex justify-center items-center gap-2 ${
                        approvalDone || currentStatus === "FILED" || currentStatus === "APPROVED"
                          ? "bg-secondary text-primary cursor-not-allowed opacity-80"
                          : "bg-card text-black hover:bg-card disabled:opacity-40 disabled:cursor-not-allowed"
                      }`}
                    >
                      {approving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                      {approvalDone || currentStatus === "FILED" || currentStatus === "APPROVED" 
                        ? "Filed Successfully" 
                        : approving 
                        ? "Filing..." 
                        : "Approve & File"}
                    </button>
                    {missingDocs.length > 0 && (
                      <p className="text-xs text-destructive text-center">Upload all missing documents before approving.</p>
                    )}
                    <div className="grid grid-cols-2 gap-2">
                      <button className="py-2 bg-secondary/50 hover:bg-secondary text-primary font-medium rounded transition-colors text-xs flex justify-center items-center gap-2">
                        <PenTool className="w-3 h-3" /> Request Changes
                      </button>
                      <button className="py-2 bg-destructive/10 hover:bg-destructive/20 text-destructive font-medium rounded transition-colors text-xs flex justify-center items-center gap-2">
                        <X className="w-3 h-3" /> Reject
                      </button>
                    </div>
                  </div>
                </>
              )}
              <div className="text-center text-[10px] text-muted-foreground uppercase tracking-widest mt-4">
                AI NEVER FILES AUTONOMOUSLY
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
