import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, FileText, CheckCircle2, AlertTriangle, AlertCircle, Scale, Calculator, Link as LinkIcon, Download, PenTool, Check, X, Activity, Loader2, RefreshCw } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { fetchCaseById, approveCaseInBackend, uploadDocument } from "@/lib/api";

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(status: string) {
  if (status.includes("FILED") || status.includes("RELEASED") || status.includes("ORDER_PASSED")) return "text-emerald-400";
  if (status.includes("APPROVED") || status.includes("DRAFT_READY") || status.includes("ELIGIBLE")) return "text-accent";
  if (status.includes("MISSING") || status.includes("MANUAL_REVIEW")) return "text-amber-400";
  return "text-white/60";
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

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCaseById(id);
      if (!data) throw new Error("Not found");
      setCaseData(data);
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

  const handleUploadDoc = async (docType: string) => {
    if (!id) return;
    setUploadingDoc(docType);
    try {
      await uploadDocument(id, docType);
      await load(); // Re-run orchestrator to get updated completeness
    } finally {
      setUploadingDoc(null);
    }
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
          <h2 className="text-xl font-semibold text-white mb-2">Backend Connection Lost</h2>
          <p className="text-muted-foreground text-sm">{error || "Live case data unavailable."}</p>
        </div>
        <div className="flex gap-3">
          <button onClick={load} className="px-4 py-2 bg-accent text-accent-foreground rounded-lg text-sm font-medium flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Retry Connection
          </button>
          <button onClick={() => navigate(-1)} className="px-4 py-2 bg-white/5 text-white rounded-lg text-sm font-medium">
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
  const draft = caseData.draft || {};
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
    <div className="p-8 max-w-7xl mx-auto space-y-12 animate-in fade-in duration-300">

      {/* Header */}
      <div className="space-y-6">
        <Link to="/cases" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Cases Directory
        </Link>

        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-semibold tracking-tight text-white">CASE #{c.case_id}</h1>
              {isManualReview ? (
                <span className="px-3 py-1 rounded-full text-xs font-semibold border uppercase tracking-wider bg-amber-500/10 text-amber-400 border-amber-500/20">MANUAL REVIEW</span>
              ) : eligibility.eligible ? (
                <span className="px-3 py-1 rounded-full text-xs font-semibold border uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border-emerald-500/20">ELIGIBLE</span>
              ) : (
                <span className="px-3 py-1 rounded-full text-xs font-semibold border uppercase tracking-wider bg-white/5 text-muted-foreground border-white/10">IN PROGRESS</span>
              )}
            </div>

            <div className="flex flex-wrap gap-6 text-sm">
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Case ID</span>
                <p className="text-white font-mono font-medium">{c.case_id}</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Custody Duration</span>
                <p className="text-white font-medium text-lg">{c.custody_days} days</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Offence</span>
                <p className="text-white font-medium">{c.offense_sections?.join(", ")}</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Age</span>
                <p className="text-white font-medium">{c.urgency_flags?.age} yrs {c.urgency_flags?.health_flag ? "🏥" : ""}</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="space-y-1">
                <span className="text-muted-foreground uppercase tracking-wider text-xs">Facility</span>
                <p className="text-white font-medium">{c.jail_location}</p>
              </div>
            </div>
          </div>

          <div className="bg-white/[0.03] border border-white/10 px-6 py-4 rounded-xl text-right">
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
          <section className="p-8 rounded-xl border border-white/5 bg-white/[0.02] space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-5"><AlertCircle className="w-48 h-48" /></div>
            <div className="relative z-10">
              <h2 className="text-xl font-medium tracking-tight text-white mb-6 uppercase">Why this case requires attention</h2>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                  <span className="text-white/90 leading-relaxed">
                    Served <strong>{eligibility.custody_days_served}</strong> days against a maximum sentence of <strong>{c.max_sentence_days_for_offense}</strong> days ({c.offense_sections?.join(", ")}).
                  </span>
                </div>
                <div className="flex items-start gap-3">
                  <Scale className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                  <span className="text-white/90 leading-relaxed">{eligibility.legal_basis}</span>
                </div>
                {eligibility.eligible && (
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                    <span className="text-white/90 leading-relaxed">
                      Required threshold: <strong>{eligibility.required_custody_days}</strong> days (using <code className="text-accent text-xs">math.ceil</code> for legal safety).
                      Overdue by <strong className="text-destructive">{eligibility.days_overdue}</strong> days.
                    </span>
                  </div>
                )}
                {isManualReview && (
                  <div className="mt-4 p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-sm">
                    ⚠️ This case requires manual legal review before any bail action can be taken.
                  </div>
                )}
              </div>

              {missingDocs.length > 0 && (
                <div className="mt-6 pt-6 border-t border-white/5 space-y-3">
                  {missingDocs.map((doc: string) => (
                    <div key={doc} className="flex items-start gap-3 text-amber-500">
                      <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">Missing: <strong>{doc.replace(/_/g, " ")}</strong></span>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-8 flex gap-4 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                <div className="flex items-center gap-1"><FileText className="w-4 h-4 text-emerald-500" /> FACT</div>
                <div className="flex items-center gap-1"><Calculator className="w-4 h-4 text-blue-500" /> CALCULATION</div>
                <div className="flex items-center gap-1"><Scale className="w-4 h-4 text-amber-500" /> LEGAL SOURCE</div>
                <div className="flex items-center gap-1"><Activity className="w-4 h-4 text-accent" /> AI INTERPRETATION</div>
              </div>
            </div>
          </section>

          {/* Evidence Chain */}
          <section className="space-y-4">
            <h2 className="text-xl font-medium tracking-tight uppercase text-white flex items-center gap-2">
              <LinkIcon className="w-5 h-5 text-accent" /> Evidence Chain
            </h2>
            <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-6 relative">
              <div className="absolute left-8 top-10 bottom-10 w-px bg-white/10" />
              {evidenceChain.map((node) => (
                <div key={node.id} className="relative z-10 pl-10">
                  <div className={`absolute left-0 top-1.5 w-4 h-4 rounded-full border-2 ${
                    node.type === "FACT" ? "border-emerald-500 bg-background" :
                    node.type === "CALCULATION" ? "border-blue-500 bg-background" :
                    node.type === "LEGAL_SOURCE" ? "border-amber-500 bg-background" :
                    "border-accent bg-accent"
                  }`} />
                  <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">{node.type}</div>
                  <div className="text-white font-medium">{node.title}</div>
                  <div className="text-sm text-muted-foreground mt-1">{node.description}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Legal Sources (RAG) */}
          {legalSources.length > 0 && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-white flex items-center gap-2">
                <Scale className="w-5 h-5 text-accent" /> Legal Evidence
                <span className="text-xs font-normal text-muted-foreground ml-2 normal-case">Grounded Legal Retrieval — keyword/indexed</span>
              </h2>
              {legalSources.map((source: any, idx: number) => (
                <div key={idx} className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-lg font-medium text-white mb-1">{source.section || source.title}</div>
                      <div className="text-xs text-muted-foreground uppercase tracking-wider">{source.source || "BNSS 2023"}</div>
                    </div>
                    <div className="bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 px-3 py-1 rounded-full text-xs font-semibold">
                      {source.relevance_score ? `${(source.relevance_score * 100).toFixed(0)}% RELEVANCE` : "HIGH RELEVANCE"}
                    </div>
                  </div>
                  <div className="p-4 bg-black/40 rounded-lg border border-white/5 text-sm text-white/80 font-serif leading-relaxed italic">
                    "{source.passage || source.content}"
                  </div>
                  {source.reasoning && (
                    <div>
                      <div className="text-xs font-medium text-accent uppercase tracking-wider mb-2">Why this source matters</div>
                      <p className="text-sm text-white/90">{source.reasoning}</p>
                    </div>
                  )}
                </div>
              ))}
            </section>
          )}

          {/* Draft */}
          {draftReady && draft.drafted_document && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-accent" /> Auto-Generated Bail Application Draft
              </h2>
              <div className="p-6 rounded-xl border border-accent/20 bg-accent/5 font-serif text-sm text-white/90 leading-relaxed whitespace-pre-wrap">
                {(draft.drafted_document as string).replaceAll("**", "")}
              </div>
            </section>
          )}

          {/* Plain-language explanation */}
          {explanation.explanation && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent" /> Family Explanation
                <span className="text-xs font-normal text-muted-foreground normal-case ml-2">Language: {c.preferred_language}</span>
              </h2>
              <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02] text-white/90 leading-relaxed">
                {explanation.explanation as string}
              </div>
            </section>
          )}

          {/* Agent Activity Log */}
          {agentLog.length > 0 && (
            <section className="space-y-4">
              <h2 className="text-xl font-medium tracking-tight uppercase text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-accent" /> Agent Execution Trace
                <span className="text-xs font-normal text-muted-foreground normal-case ml-2">Logged pipeline execution</span>
              </h2>

              {/* LLM Provider Badge — visible fault tolerance demo */}
              {llmProvider && (
                <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold ${
                  llmProvider.includes("Groq") ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" :
                  llmProvider.includes("Ollama") ? "bg-amber-500/10 border-amber-500/30 text-amber-400" :
                  "bg-white/5 border-white/10 text-white/50"
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    llmProvider.includes("Groq") ? "bg-emerald-400" :
                    llmProvider.includes("Ollama") ? "bg-amber-400" : "bg-white/30"
                  }`} />
                  LLM PROVIDER: {llmProvider}
                </div>
              )}

              <div className="p-6 rounded-xl border border-white/5 bg-black/40 space-y-3">
                {agentLog.map((entry: any, idx: number) => (
                  <div key={idx} className="flex items-center gap-4 text-sm">
                    <span className={`w-16 text-xs font-bold uppercase text-right shrink-0 ${
                      entry.status === "DONE" ? "text-emerald-500" :
                      entry.status === "SKIPPED" ? "text-white/30" :
                      entry.status === "RUNNING" ? "text-accent" : "text-amber-500"
                    }`}>{entry.status}</span>
                    <span className="font-mono text-white/70 w-36 shrink-0">{entry.agent}</span>
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
          <section className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-6">
            <h2 className="text-lg font-medium tracking-tight uppercase text-white">Document Readiness</h2>
            <div className="space-y-3">
              {(c.required_docs || []).map((doc: string) => {
                const isPresent = (c.present_docs || []).includes(doc);
                return (
                  <div key={doc} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {isPresent ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      ) : (
                        <X className="w-4 h-4 text-destructive" />
                      )}
                      <span className={`text-sm ${isPresent ? "text-white" : "text-muted-foreground"}`}>
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
              <div className="mt-4 p-4 bg-accent/5 border border-accent/10 rounded-lg">
                <div className="text-xs font-medium text-accent uppercase tracking-wider mb-2">Action Required</div>
                <p className="text-xs text-muted-foreground mb-3">Upload missing documents to trigger the Completeness Agent and unlock the drafting pipeline.</p>
                <button className="w-full py-2 bg-white/5 hover:bg-white/10 text-white text-xs font-medium rounded transition-colors flex items-center justify-center gap-2">
                  <Download className="w-3 h-3" /> Generate Request PDF
                </button>
              </div>
            )}
          </section>

          {/* Case Timeline (from status tracking + state) */}
          <section className="p-6 rounded-xl border border-white/5 bg-white/[0.02] space-y-6">
            <h2 className="text-lg font-medium tracking-tight uppercase text-white">Case Timeline</h2>
            <div className="space-y-4 relative">
              <div className="absolute left-2 top-2 bottom-2 w-px bg-white/10" />
              {[
                { title: "Arrested", date: c.arrest_date, done: true },
                { title: "BNSS 479 Threshold Evaluated", date: "Automated", done: true },
                { title: "Documents Verified", date: "Completeness Agent", done: missingDocs.length === 0 },
                { title: "Bail Draft Generated", date: "Drafting Agent", done: draftReady },
                { title: "Lawyer Review", date: "Human Gate", done: currentStatus === "APPROVED" || currentStatus === "FILED" },
                { title: "Filed in Court", date: "Status Tracking", done: currentStatus === "FILED" },
              ].map((event, idx) => (
                <div key={idx} className="relative z-10 pl-8">
                  <div className={`absolute left-1 top-1 w-2.5 h-2.5 rounded-full ${event.done ? "bg-emerald-500" : "bg-white/20"}`} />
                  <div className="text-xs text-muted-foreground mb-0.5">{event.date}</div>
                  <div className={`text-sm font-medium ${event.done ? "text-white" : "text-white/40"}`}>{event.title}</div>
                </div>
              ))}
            </div>
          </section>

          {/* Human Review Gateway */}
          <section className="p-6 rounded-xl border border-accent/30 bg-accent/5 space-y-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-accent/10 blur-3xl rounded-full" />
            <h2 className="text-lg font-semibold tracking-tight uppercase text-white relative z-10">Human Review Required</h2>

            <div className="space-y-3 relative z-10">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">AI analysis complete</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Documents verified</span>
                {missingDocs.length === 0
                  ? <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  : <X className="w-4 h-4 text-destructive" />}
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Draft prepared</span>
                {draftReady
                  ? <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  : <X className="w-4 h-4 text-muted-foreground" />}
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 space-y-4 relative z-10">
              {approvalDone || currentStatus === "FILED" ? (
                <div className="text-center">
                  <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Status</div>
                  <div className="text-xl font-bold text-emerald-400">FILED</div>
                  <p className="text-xs text-muted-foreground mt-2">Bail application has been submitted to court.</p>
                </div>
              ) : isManualReview ? (
                <div className="text-center p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-sm">
                  This case requires manual review — automated approval is not permitted.
                </div>
              ) : (
                <>
                  <div className="p-3 bg-black/40 border border-white/5 rounded text-xs text-muted-foreground leading-relaxed text-center">
                    "I confirm that I have reviewed the supporting documents and legal basis."
                  </div>
                  <div className="space-y-2">
                    <button
                      onClick={handleApprove}
                      disabled={approving || missingDocs.length > 0 || !draftReady}
                      className="w-full py-3 bg-white text-black font-semibold rounded hover:bg-white/90 transition-colors flex justify-center items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {approving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                      {approving ? "Filing…" : "Approve & File"}
                    </button>
                    {missingDocs.length > 0 && (
                      <p className="text-xs text-destructive text-center">Upload all missing documents before approving.</p>
                    )}
                    <div className="grid grid-cols-2 gap-2">
                      <button className="py-2 bg-white/5 hover:bg-white/10 text-white font-medium rounded transition-colors text-xs flex justify-center items-center gap-2">
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
