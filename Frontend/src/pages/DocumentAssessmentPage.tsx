import { useState, useEffect } from "react";
import {
  FileText,
  Cpu,
  Database,
  Brain,
  CheckCircle2,
  Sparkles,
  Copy,
  RefreshCw,
  ShieldCheck,
  Search,
  BookOpen,
} from "lucide-react";
import { assessDocument, fetchSampleDocuments } from "@/lib/api";
import { InkStamp } from "@/components/ui/InkStamp";

interface SampleDoc {
  id: string;
  title: string;
  subtitle: string;
  document_name: string;
  preview_text: string;
}

interface PipelineResult {
  document_name: string;
  is_scanned_handwritten: boolean;
  detection_confidence: number;
  ocr_engine_used: string;
  raw_ocr_text: string;
  extracted_text?: string;
  data_prep_kit_clean_text: string;
  structured_metadata: {
    case_id?: string;
    accused_name?: string;
    legal_sections?: string[];
    custody_days?: number;
    max_sentence_days?: number;
    custody_fraction?: number;
    is_senior_citizen?: boolean;
    has_medical_condition?: boolean;
    data_prep_kit_status?: string;
  };
  rag_statute_citations: Array<{
    code: string;
    title: string;
    relevance: string;
    snippet: string;
  }>;
  granite_assessment: {
    assessment_id: string;
    model_name: string;
    case_id: string;
    eligibility_status: string;
    confidence_score: number;
    urgency_rating: string;
    statutory_ground: string;
    legal_summary: string;
    key_findings: string[];
    recommended_action: string;
    ai_generated_report_draft: string;
  };
  llm_used?: string;
  processing_time_ms: number;
}

export function DocumentAssessmentPage() {
  const [samples, setSamples] = useState<SampleDoc[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>("sample-1");
  const [customText, setCustomText] = useState<string>("");
  const [useCustomInput, setUseCustomInput] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeStep, setActiveStep] = useState<number>(6); // Default all completed
  const [activeTab, setActiveTab] = useState<"granite" | "trocr" | "dataprep" | "rag">("granite");
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  // Load sample documents on mount
  useEffect(() => {
    async function init() {
      const data = await fetchSampleDocuments();
      if (data && data.length > 0) {
        setSamples(data);
      }
    }
    init();
  }, []);

  // Run pipeline assessment
  const handleRunAssessment = async (docName?: string, textContent?: string) => {
    setLoading(true);
    setActiveStep(1);

    // Simulate animated step progression through the flowchart
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev < 6 ? prev + 1 : 6));
    }, 250);

    try {
      const currentSample = samples.find((s) => s.id === selectedSampleId);
      const nameToAssess = docName || (useCustomInput ? "Custom_Uploaded_Document.pdf" : currentSample?.document_name);
      const textToAssess = textContent || (useCustomInput ? customText : currentSample?.preview_text);

      const res = await assessDocument(nameToAssess, textToAssess);
      setResult(res);
    } catch (err) {
      console.error("Pipeline assessment failed:", err);
    } finally {
      clearInterval(timer);
      setActiveStep(6);
      setLoading(false);
    }
  };

  // Initial auto-assessment on first load
  useEffect(() => {
    handleRunAssessment();
  }, [selectedSampleId]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-3 py-1 rounded-md text-xs font-mono font-semibold bg-[#1F2A44] text-[#B08D57] border border-[#B08D57]/30 shadow-sm uppercase tracking-wider">
              TrOCR + IBM Data Prep Kit + RAG + IBM Granite
            </span>
            <span className="text-xs text-muted-foreground font-mono">End-to-End Legal Operations</span>
          </div>
          <h1 className="text-3xl font-serif font-bold tracking-tight text-white flex items-center gap-3">
            Legal Document AI &amp; Preliminary Assessment Pipeline
          </h1>
          <p className="text-sm text-muted-foreground font-sans mt-1 max-w-3xl leading-relaxed">
            Automated intake for scanned &amp; handwritten undertrial legal records. Extract text using HuggingFace TrOCR, clean structure via IBM Data Prep Kit, retrieve BNSS §479 statutes via RAG, and generate preliminary legal assessments with IBM Granite.
          </p>
        </div>

        <button
          onClick={() => handleRunAssessment()}
          disabled={loading}
          className="px-5 py-2.5 bg-[#1F2A44] text-white font-semibold rounded-lg text-sm border-b-2 border-[#B08D57] hover:bg-[#253454] transition-all flex items-center gap-2 shadow-md disabled:opacity-50"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin text-[#B08D57]" />
              Processing Stage {activeStep}/6...
            </>
          ) : (
            <>
              <FileText className="w-4 h-4 text-[#B08D57]" />
              Execute Pipeline Assessment
            </>
          )}
        </button>
      </div>

      {/* Case-File Transmittal & Routing Slip */}
      <div className="p-5 rounded-xl bg-[#0F141C] border border-white/10 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#B08D57]" />
            <h2 className="text-xs font-mono font-bold uppercase tracking-widest text-white/80">
              Case-File Transmittal &amp; Routing Slip — Pipeline Operations
            </h2>
          </div>
          {result && (
            <InkStamp
              text={`EXECUTED IN ${result.processing_time_ms}MS`}
              variant="sage"
            />
          )}
        </div>

        {/* 7-Step Routing Slip Nodes */}
        <div className="grid grid-cols-1 md:grid-cols-7 gap-2 relative">
          {/* Node 1: Legal Document */}
          <div
            className={`p-3 rounded-lg border text-center transition-all relative ${
              activeStep >= 1
                ? "bg-[#162030] border-[#B08D57]/50 text-white shadow-md"
                : "bg-white/[0.02] border-white/10 text-muted-foreground"
            }`}
          >
            <div className="text-[10px] font-mono font-bold text-[#B08D57] mb-1">01 / INTAKE</div>
            <div className="text-xs font-semibold font-serif">1. Legal Doc</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-1 truncate">
              {result ? result.document_name : "Upload / Presets"}
            </div>
          </div>

          {/* Node 2: Scanned Check */}
          <div
            className={`p-3 rounded-lg border text-center transition-all relative ${
              activeStep >= 2
                ? "bg-[#162030] border-[#B08D57]/50 text-white shadow-md"
                : "bg-white/[0.02] border-white/10 text-muted-foreground"
            }`}
          >
            <div className="text-[10px] font-mono font-bold text-[#B08D57] mb-1">02 / OCR</div>
            <div className="text-xs font-semibold font-serif">2. Scanned Check</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-1 truncate">
              {result ? (result.is_scanned_handwritten ? "TrOCR Vision" : "PyPDF Native") : "Format Detect"}
            </div>
          </div>

          {/* Node 3: Text Extract */}
          <div
            className={`p-3 rounded-lg border text-center transition-all relative ${
              activeStep >= 3
                ? "bg-[#162030] border-[#B08D57]/50 text-white shadow-md"
                : "bg-white/[0.02] border-white/10 text-muted-foreground"
            }`}
          >
            <div className="text-[10px] font-mono font-bold text-[#B08D57] mb-1">03 / EXTRACT</div>
            <div className="text-xs font-semibold font-serif">3. Text Extract</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-1 truncate">
              {result ? `${result.extracted_text?.length ?? 0} chars` : "Text Buffer"}
            </div>
          </div>

          {/* Node 4: IBM Data Prep */}
          <div
            className={`p-3 rounded-lg border text-center transition-all relative ${
              activeStep >= 4
                ? "bg-[#162030] border-[#B08D57]/50 text-white shadow-md"
                : "bg-white/[0.02] border-white/10 text-muted-foreground"
            }`}
          >
            <div className="text-[10px] font-mono font-bold text-[#B08D57] mb-1">04 / CLEAN</div>
            <div className="text-xs font-semibold font-serif">4. Data Prep Kit</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-1 truncate">
              {result ? "Cleaned JSON" : "IBM Sanitizer"}
            </div>
          </div>

          {/* Node 5: RAG Grounding */}
          <div
            className={`p-3 rounded-lg border text-center transition-all relative ${
              activeStep >= 5
                ? "bg-[#162030] border-[#B08D57]/50 text-white shadow-md"
                : "bg-white/[0.02] border-white/10 text-muted-foreground"
            }`}
          >
            <div className="text-[10px] font-mono font-bold text-[#B08D57] mb-1">05 / RAG</div>
            <div className="text-xs font-semibold font-serif">5. Statute Vector</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-1 truncate">
              {result ? "ChromaDB Match" : "BNSS §479 Embed"}
            </div>
          </div>

          {/* Node 6: Granite LLM */}
          <div
            className={`p-3 rounded-lg border text-center transition-all relative ${
              activeStep >= 6
                ? "bg-[#162030] border-[#B08D57]/50 text-white shadow-md"
                : "bg-white/[0.02] border-white/10 text-muted-foreground"
            }`}
          >
            <div className="text-[10px] font-mono font-bold text-[#B08D57] mb-1">06 / REASON</div>
            <div className="text-xs font-semibold font-serif">6. Granite Engine</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-1 truncate">
              {result ? (result.llm_used ?? "IBM Granite 3.1") : "Bail Assessment"}
            </div>
          </div>

          {/* Node 7: Legal Officer Review */}
          <div
            className={`p-3 rounded-lg border text-center transition-all relative ${
              activeStep >= 6
                ? "bg-[#162030] border-emerald-500/50 text-white shadow-md"
                : "bg-white/[0.02] border-white/10 text-muted-foreground"
            }`}
          >
            <div className="text-[10px] font-mono font-bold text-emerald-400 mb-1">07 / APPROVE</div>
            <div className="text-xs font-semibold font-serif">7. Officer Review</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-1 truncate">
              Human-in-the-Loop
            </div>
          </div>
        </div>
      </div>


      {/* Preset Selector & Upload Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Sample Document Selector */}
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-4">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-accent" /> Select Scanned Legal Document
          </h3>
          <div className="space-y-2">
            {samples.map((sample) => (
              <button
                key={sample.id}
                onClick={() => {
                  setUseCustomInput(false);
                  setSelectedSampleId(sample.id);
                }}
                className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                  !useCustomInput && selectedSampleId === sample.id
                    ? "bg-accent/15 border-accent text-white shadow-md shadow-accent/10"
                    : "bg-white/[0.02] border-white/10 text-muted-foreground hover:bg-white/[0.05]"
                }`}
              >
                <div className="font-semibold text-xs text-white">{sample.title}</div>
                <div className="text-[11px] text-muted-foreground mt-1">{sample.subtitle}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Text / Upload Field */}
        <div className="md:col-span-2 p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent" /> Custom Legal Document Input
            </h3>
            <button
              onClick={() => setUseCustomInput(!useCustomInput)}
              className={`text-xs px-3 py-1 rounded-lg border transition-all ${
                useCustomInput ? "bg-accent text-accent-foreground border-accent font-semibold" : "bg-white/5 border-white/10 text-muted-foreground"
              }`}
            >
              {useCustomInput ? "Using Custom Input" : "Switch to Custom Text"}
            </button>
          </div>

          <textarea
            disabled={!useCustomInput}
            value={useCustomInput ? customText : samples.find((s) => s.id === selectedSampleId)?.preview_text || ""}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="Paste raw handwritten/scanned legal remand order or FIR text here..."
            className="w-full h-36 p-3.5 rounded-xl bg-black/40 border border-white/10 text-xs font-mono text-slate-300 focus:outline-none focus:border-accent disabled:opacity-60 resize-none"
          />
        </div>
      </div>

      {/* Multi-Tab Workspace Inspector */}
      {result && (
        <div className="space-y-6">
          {/* Tabs */}
          <div className="flex border-b border-white/10 gap-2">
            <button
              onClick={() => setActiveTab("granite")}
              className={`px-5 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-all ${
                activeTab === "granite"
                  ? "border-accent text-accent bg-accent/10 rounded-t-xl"
                  : "border-transparent text-muted-foreground hover:text-white"
              }`}
            >
              <Brain className="w-4 h-4" /> 🧠 IBM Granite Preliminary Assessment
            </button>
            <button
              onClick={() => setActiveTab("trocr")}
              className={`px-5 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-all ${
                activeTab === "trocr"
                  ? "border-blue-400 text-blue-400 bg-blue-500/10 rounded-t-xl"
                  : "border-transparent text-muted-foreground hover:text-white"
              }`}
            >
              <Sparkles className="w-4 h-4 text-blue-400" /> ✍️ TrOCR Extracted Text
            </button>
            <button
              onClick={() => setActiveTab("dataprep")}
              className={`px-5 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-all ${
                activeTab === "dataprep"
                  ? "border-emerald-400 text-emerald-400 bg-emerald-500/10 rounded-t-xl"
                  : "border-transparent text-muted-foreground hover:text-white"
              }`}
            >
              <Database className="w-4 h-4 text-emerald-400" /> 📦 IBM Data Prep Kit Output
            </button>
            <button
              onClick={() => setActiveTab("rag")}
              className={`px-5 py-3 text-xs font-semibold border-b-2 flex items-center gap-2 transition-all ${
                activeTab === "rag"
                  ? "border-cyan-400 text-cyan-400 bg-cyan-500/10 rounded-t-xl"
                  : "border-transparent text-muted-foreground hover:text-white"
              }`}
            >
              <Search className="w-4 h-4 text-cyan-400" /> 🔎 RAG Statutory Citations
            </button>
          </div>

          {/* TAB 1: IBM Granite Preliminary Assessment */}
          {activeTab === "granite" && (
            <div className="space-y-6 animate-in fade-in duration-200">
              {/* Executive Summary Card */}
              <div className="p-6 rounded-2xl bg-accent/10 border border-accent/30 space-y-6 relative overflow-hidden shadow-xl">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-accent/20 pb-4">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-accent">
                      {result.granite_assessment.model_name}
                    </span>
                    <h2 className="text-2xl font-bold text-white mt-0.5">
                      Preliminary Legal Assessment Report — {result.granite_assessment.case_id}
                    </h2>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="px-3.5 py-1.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4" /> {result.granite_assessment.eligibility_status}
                    </span>
                    <span className="px-3.5 py-1.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      {result.granite_assessment.urgency_rating}
                    </span>
                  </div>
                </div>

                {/* Legal Summary */}
                <div className="space-y-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Executive Assessment Summary</h3>
                  <p className="text-sm text-slate-200 leading-relaxed bg-black/30 p-4 rounded-xl border border-white/5 font-sans">
                    {result.granite_assessment.legal_summary}
                  </p>
                </div>

                {/* Key Findings List */}
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Key Statutory & Case Findings</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {result.granite_assessment.key_findings.map((finding, idx) => (
                      <div key={idx} className="p-3 rounded-xl bg-white/[0.03] border border-white/10 flex items-start gap-3">
                        <ShieldCheck className="w-5 h-5 text-accent shrink-0 mt-0.5" />
                        <span className="text-xs text-slate-200 leading-snug">{finding}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Action Box */}
                <div className="p-4 rounded-xl bg-accent/20 border border-accent/40 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-bold text-accent uppercase tracking-wider">Recommended DLSA Action</div>
                    <div className="text-sm font-semibold text-white mt-0.5">{result.granite_assessment.recommended_action}</div>
                  </div>
                  <button
                    onClick={() => copyToClipboard(result.granite_assessment.ai_generated_report_draft)}
                    className="px-4 py-2 bg-accent text-accent-foreground font-semibold rounded-xl text-xs hover:opacity-90 transition-all flex items-center gap-2 shrink-0"
                  >
                    {copied ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    {copied ? "Copied Legal Petition" : "Copy Form 479 Petition Draft"}
                  </button>
                </div>

                {/* AI Draft Report Body */}
                <div className="space-y-2 pt-2">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Full Generated Assessment Draft</h3>
                  <pre className="p-4 rounded-xl bg-black/60 border border-white/10 text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed overflow-x-auto max-h-64">
                    {result.granite_assessment.ai_generated_report_draft?.replaceAll("**", "")}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: TrOCR Extracted Text */}
          {activeTab === "trocr" && (
            <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-4 animate-in fade-in duration-200">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-blue-400" /> TrOCR Handwriting Optical Character Recognition
                  </h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Engine: <span className="font-mono text-blue-300">{result.ocr_engine_used}</span> • Confidence:{" "}
                    <span className="font-bold text-emerald-400">{(result.detection_confidence * 100).toFixed(1)}%</span>
                  </p>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-mono bg-blue-500/10 text-blue-300 border border-blue-500/20">
                  Scanned Doc Identified: YES
                </span>
              </div>

              <div className="space-y-2">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Raw Extracted Text Stream</div>
                <pre className="p-5 rounded-xl bg-black/50 border border-white/10 text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed">
                  {result.raw_ocr_text}
                </pre>
              </div>
            </div>
          )}

          {/* TAB 3: IBM Data Prep Kit Output */}
          {activeTab === "dataprep" && (
            <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-6 animate-in fade-in duration-200">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Database className="w-4 h-4 text-emerald-400" /> IBM Data Prep Kit Transformation Engine
                  </h3>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Status: <span className="font-mono text-emerald-300">{result.structured_metadata.data_prep_kit_status}</span>
                  </p>
                </div>
              </div>

              {/* Extracted JSON Metadata Card */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <div className="text-[11px] text-muted-foreground">Extracted Case ID</div>
                  <div className="text-lg font-bold text-white font-mono mt-1">{result.structured_metadata.case_id}</div>
                </div>
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <div className="text-[11px] text-muted-foreground">Custody Duration</div>
                  <div className="text-lg font-bold text-accent font-mono mt-1">{result.structured_metadata.custody_days} Days</div>
                </div>
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <div className="text-[11px] text-muted-foreground">Custody Ratio</div>
                  <div className="text-lg font-bold text-emerald-400 font-mono mt-1">
                    {((result.structured_metadata.custody_fraction || 0) * 100).toFixed(0)}% of Max
                  </div>
                </div>
                <div className="p-4 rounded-xl bg-black/40 border border-white/10">
                  <div className="text-[11px] text-muted-foreground">Senior / Health Flag</div>
                  <div className="text-lg font-bold text-amber-300 mt-1">
                    {result.structured_metadata.is_senior_citizen ? "Yes (Senior)" : "No"}
                  </div>
                </div>
              </div>

              {/* Clean Prose Output */}
              <div className="space-y-2">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Cleaned & Structured Prose Body</div>
                <pre className="p-5 rounded-xl bg-black/50 border border-white/10 text-xs font-mono text-emerald-200/90 whitespace-pre-wrap leading-relaxed">
                  {result.data_prep_kit_clean_text}
                </pre>
              </div>
            </div>
          )}

          {/* TAB 4: RAG Statutory Citations */}
          {activeTab === "rag" && (
            <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 space-y-6 animate-in fade-in duration-200">
              <div className="border-b border-white/10 pb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Search className="w-4 h-4 text-cyan-400" /> RAG Knowledge Retrieval Layer
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Matched Indian Statutory Provisions & High Court / Supreme Court Constitutional Precedents
                </p>
              </div>

              <div className="space-y-4">
                {result.rag_statute_citations.map((citation, idx) => (
                  <div key={idx} className="p-5 rounded-xl bg-cyan-950/20 border border-cyan-500/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                        {citation.code}
                      </span>
                      <span className="text-[11px] text-muted-foreground">Relevant for Bail Grounds</span>
                    </div>
                    <div className="text-sm font-semibold text-white">{citation.title}</div>
                    <p className="text-xs text-slate-300 leading-relaxed font-sans">{citation.relevance}</p>
                    <div className="p-3 rounded-lg bg-black/40 border border-white/5 text-xs font-mono text-cyan-200/90">
                      "{citation.snippet}"
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
