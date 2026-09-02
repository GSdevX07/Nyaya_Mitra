import React, { useState, useEffect } from "react";
import {
  BookOpen,
  ShieldCheck,
  Search,
  Plus,
  Layers,
  CheckCircle2,
  AlertTriangle,
  History,
  Scale,
  Sparkles,
  RefreshCw,
  FileCheck,
  X,
  Calendar,
  Check,
  Clock,
  Eye,
} from "lucide-react";


import {
  fetchLegalSources,
  fetchLegalSourceDetail,
  createLegalSource,
  updateLegalSourceLifecycle,
  retrieveLegalKnowledge,
  verifyCitationIntegrity,
  runLegalKnowledgeEvaluation,
  fetchLegalEscalations,
  resolveLegalEscalation,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

const ALLOWED_LIFECYCLE_TRANSITIONS: Record<string, string[]> = {
  discovered: ["reviewed"],
  reviewed: ["approved", "discovered"],
  approved: ["active", "reviewed"],
  active: ["superseded"],
  superseded: ["retired"],
  retired: [],
};

export function LegalSourcesAdmin() {
  const { user } = useAuth();
  const role = user?.role || "DLSA_OFFICER";

  // Role permissions
  const isAdvocate = role === "DEFENSE_ADVOCATE" || role === "CONTROLLED_EXTERNAL_ADVOCATE";
  const isAuditor = role === "READ_ONLY_AUDITOR";
  const isSupervisor = role === "SUPERVISING_LEGAL_OFFICER";
  const isGovAdmin = role === "GOV_ADMIN";
  const isDlsa = role === "DLSA_OFFICER";
  const isPlatformAdmin = role === "PLATFORM_ADMIN";

  const canIngest = isSupervisor || isGovAdmin || isDlsa;
  const canUpdateLifecycle = isSupervisor || isGovAdmin;
  const canRunBenchmark = isSupervisor || isGovAdmin || isAuditor || isPlatformAdmin;
  const canManageEscalations = isSupervisor || isGovAdmin;

  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"registry" | "sandbox" | "benchmark" | "escalations">(
    isAuditor ? "benchmark" : "registry"
  );

  // Filters
  const [domainFilter, setDomainFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Modals
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedSourceDetail, setSelectedSourceDetail] = useState<any | null>(null);
  const [lifecycleModalSource, setLifecycleModalSource] = useState<any | null>(null);
  const [targetStatus, setTargetStatus] = useState("");
  const [lifecycleNotes, setLifecycleNotes] = useState("");
  const [supersededById, setSupersededById] = useState("");

  // Upload Form
  const [newTitle, setNewTitle] = useState("");
  const [newShortName, setNewShortName] = useState("");
  const [newAuthority, setNewAuthority] = useState("Parliament of India");
  const [newDomain, setNewDomain] = useState("CRIMINAL_PROCEDURE");
  const [newJurisdiction, setNewJurisdiction] = useState("India (National)");
  const [newEffectiveDate, setNewEffectiveDate] = useState("2024-07-01");
  const [newRawContent, setNewRawContent] = useState("");
  const [uploading, setUploading] = useState(false);

  // Hybrid Retrieval Sandbox
  const [sandboxQuery, setSandboxQuery] = useState("bail under section 479 for first-time undertrial prisoner");
  const [includeSuperseded, setIncludeSuperseded] = useState(false);
  const [retrievedResults, setRetrievedResults] = useState<any[]>([]);
  const [retrieving, setRetrieving] = useState(false);

  // Citation Verifier
  const [verifierStatement, setVerifierStatement] = useState(
    "The applicant is entitled to mandatory statutory bail under Section 479 of Bharatiya Nagarik Suraksha Sanhita 2023, having completed one-third of maximum detention."
  );
  const [verifierReport, setVerifierReport] = useState<any | null>(null);
  const [verifying, setVerifying] = useState(false);

  // Benchmarks
  const [benchmarks, setBenchmarks] = useState<any | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  // Escalations
  const [escalations, setEscalations] = useState<any[]>([]);
  const [loadingEscalations, setLoadingEscalations] = useState(false);
  const [resolvingEscalationId, setResolvingEscalationId] = useState<string | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");

  // Initial Data Load
  useEffect(() => {
    loadSources();
    if (canManageEscalations) {
      loadEscalations();
    }
  }, [domainFilter, statusFilter, role]);

  const loadSources = async () => {
    setLoading(true);
    try {
      const data = await fetchLegalSources(
        domainFilter !== "ALL" ? domainFilter : undefined,
        statusFilter !== "ALL" ? statusFilter : undefined
      );
      setSources(data || []);
    } catch (err) {
      console.error("Failed to load legal sources:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadEscalations = async () => {
    setLoadingEscalations(true);
    try {
      const data = await fetchLegalEscalations("PENDING_REVIEW");
      setEscalations(data || []);
    } catch (err) {
      console.error("Failed to load escalations:", err);
    } finally {
      setLoadingEscalations(false);
    }
  };

  const handleCreateSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newRawContent.trim()) {
      alert("Please provide both document title and statutory text.");
      return;
    }

    setUploading(true);
    try {
      await createLegalSource({
        title: newTitle.trim(),
        short_name: newShortName.trim() || newTitle.trim(),
        issuing_authority: newAuthority,
        effective_date: newEffectiveDate,
        jurisdiction: newJurisdiction,
        legal_domain: newDomain,
        raw_content: newRawContent.trim(),
        version: "1.0",
        audit_notes: `Source proposed by ${user?.full_name || "Officer"} (${role}) via Nyaya Mitra`,
      });
      setIsUploadOpen(false);
      setNewTitle("");
      setNewShortName("");
      setNewRawContent("");
      await loadSources();
      alert("Legal document submitted successfully! Initial status: 'discovered'.");
    } catch (err: any) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleUpdateLifecycle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lifecycleModalSource || !targetStatus) return;

    if (targetStatus === "superseded" && !supersededById.trim()) {
      alert("Superseding an active source requires providing the replacement source ID.");
      return;
    }

    try {
      await updateLegalSourceLifecycle(
        lifecycleModalSource.id,
        targetStatus,
        lifecycleNotes || `Transition to ${targetStatus} by ${user?.full_name || "Officer"} (${role})`,
        supersededById.trim() || undefined
      );

      setLifecycleModalSource(null);
      setLifecycleNotes("");
      setSupersededById("");
      await loadSources();
      alert(`Source status transitioned successfully to '${targetStatus}'.`);
    } catch (err: any) {
      alert("Lifecycle update failed: " + err.message);
    }
  };

  const handleViewDetail = async (sourceId: string) => {
    try {
      const detail = await fetchLegalSourceDetail(sourceId);
      setSelectedSourceDetail(detail);
    } catch (err: any) {
      alert("Failed to load source details: " + err.message);
    }
  };

  const handleRetrieve = async () => {
    if (!sandboxQuery.trim()) return;
    setRetrieving(true);
    try {
      const res = await retrieveLegalKnowledge(
        sandboxQuery.trim(),
        domainFilter !== "ALL" ? domainFilter : undefined,
        includeSuperseded,
        5
      );
      setRetrievedResults(res.chunks || []);
    } catch (err: any) {
      alert("Retrieval failed: " + err.message);
    } finally {
      setRetrieving(false);
    }
  };

  const handleVerifyCitations = async () => {
    if (!verifierStatement.trim()) return;
    setVerifying(true);
    try {
      const report = await verifyCitationIntegrity(verifierStatement.trim());
      setVerifierReport(report);
      if (canManageEscalations && report.routed_to_human_review) {
        await loadEscalations();
      }
    } catch (err: any) {
      alert("Verification failed: " + err.message);
    } finally {
      setVerifying(false);
    }
  };

  const handleRunEvaluation = async () => {
    setEvaluating(true);
    try {
      const res = await runLegalKnowledgeEvaluation();
      setBenchmarks(res);
    } catch (err: any) {
      alert("Evaluation failed: " + err.message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleResolveEscalation = async () => {
    if (!resolvingEscalationId || !resolutionNotes.trim()) {
      alert("Please provide supervisory resolution notes.");
      return;
    }
    try {
      await resolveLegalEscalation(resolvingEscalationId, resolutionNotes.trim(), "RESOLVED");
      setResolvingEscalationId(null);
      setResolutionNotes("");
      await loadEscalations();
      alert("Escalation resolved successfully and recorded in audit log.");
    } catch (err: any) {
      alert("Resolution failed: " + err.message);
    }
  };

  // Filter sources for display
  const filteredSources = sources.filter((s) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (s.title || "").toLowerCase().includes(q) ||
      (s.issuing_authority || "").toLowerCase().includes(q) ||
      (s.id || "").toLowerCase().includes(q) ||
      (s.jurisdiction || "").toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-600 border border-emerald-500/30 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Active Enactment</span>;
      case "approved":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-blue-500/15 text-blue-600 border border-blue-500/30 flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Approved</span>;
      case "reviewed":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-500/15 text-indigo-600 border border-indigo-500/30 flex items-center gap-1"><Eye className="w-3 h-3" /> Reviewed</span>;
      case "discovered":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-gray-500/15 text-gray-600 border border-gray-500/30 flex items-center gap-1"><Clock className="w-3 h-3" /> Discovered / Proposed</span>;
      case "superseded":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-600 border border-amber-500/30 flex items-center gap-1"><History className="w-3 h-3" /> Superseded (Historical)</span>;
      case "retired":
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-rose-500/15 text-rose-600 border border-rose-500/30 flex items-center gap-1"><X className="w-3 h-3" /> Retired</span>;
      default:
        return <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-muted text-muted-foreground">{status}</span>;
    }
  };

  const getHeaderTitle = () => {
    if (isAdvocate) return "Legal Knowledge Base (Advocate Consumer Mode)";
    if (isAuditor) return "Legal Knowledge Audit & Evaluation (Auditor Mode)";
    if (isDlsa) return "Governed Legal Knowledge (DLSA Operational Mode)";
    if (isSupervisor) return "Legal Knowledge Governance (Supervising Officer Mode)";
    if (isGovAdmin) return "Statutory Repository Administration (SLSA Admin Mode)";
    return "Legal Knowledge Infrastructure (Technical Admin Mode)";
  };

  return (
    <div className="space-y-8 pb-16 max-w-7xl mx-auto text-base">
      {/* Header Banner — Zoomed & Spacious */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-5 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <Scale className="w-6 h-6 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-primary px-2.5 py-0.5 rounded-md bg-primary/10 border border-primary/20">
              {role.replace(/_/g, " ")} CLEARANCE
            </span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-foreground">
            {getHeaderTitle()}
          </h1>
          <p className="text-base text-muted-foreground mt-2 max-w-4xl leading-relaxed">
            {isAdvocate
              ? "Access approved statutory enactments, judicial precedents, and verify legal draft citations against active authority."
              : isAuditor
              ? "Statutory oversight and compliance audit. Inspect source provenance, boundary tracking, and execute evaluation benchmark suites."
              : "Source registry and provenance layer governing statutory acts (BNSS, BNS), judicial precedents, and prison rules. Enforces citation integrity and prevents hallucinated statutes."}
          </p>
        </div>

        {canIngest && (
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => setIsUploadOpen(true)}
              className="px-5 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition-all flex items-center gap-2.5 shadow-md hover:shadow-lg"
            >
              <Plus className="w-4 h-4" />
              {isDlsa ? "Propose Legal Document" : "Ingest Legal Document"}
            </button>
          </div>
        )}
      </div>

      {/* Quick Metrics Bar — Zoomed Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="p-6 bg-card border-2 border-border rounded-2xl shadow-sm hover:border-primary/40 transition-colors">
          <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Registered Sources</div>
          <div className="text-4xl font-extrabold text-foreground mt-2">{sources.length}</div>
          <div className="text-xs text-muted-foreground mt-2 flex items-center gap-1.5">
            <BookOpen className="w-4 h-4 text-primary" /> Multi-Domain Corpus
          </div>
        </div>

        <div className="p-6 bg-card border-2 border-border rounded-2xl shadow-sm hover:border-emerald-500/40 transition-colors">
          <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Active Enactments</div>
          <div className="text-4xl font-extrabold text-emerald-600 mt-2">
            {sources.filter((s) => s.lifecycle_status === "active").length}
          </div>
          <div className="text-xs text-muted-foreground mt-2">BNSS 2023, BNS 2023 &amp; SC Precedents</div>
        </div>

        <div className="p-6 bg-card border-2 border-border rounded-2xl shadow-sm hover:border-amber-500/40 transition-colors">
          <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Historical / Superseded</div>
          <div className="text-4xl font-extrabold text-amber-600 mt-2">
            {sources.filter((s) => s.lifecycle_status === "superseded").length}
          </div>
          <div className="text-xs text-muted-foreground mt-2">IPC 1860 &amp; CrPC 1973 (Transitional)</div>
        </div>

        <div className="p-6 bg-card border-2 border-border rounded-2xl shadow-sm hover:border-primary/40 transition-colors">
          <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Citation Guardrail</div>
          <div className="text-4xl font-extrabold text-primary mt-2">100%</div>
          <div className="text-xs text-muted-foreground mt-2">Statutory Hallucination Block</div>
        </div>
      </div>

      {/* Tabs — Larger & Clearer */}
      <div className="flex border-b border-border bg-card px-3 pt-2 rounded-t-2xl text-base font-semibold overflow-x-auto gap-2">
        {!isAuditor && (
          <button
            onClick={() => setActiveTab("registry")}
            className={`py-3.5 px-6 border-b-2 flex items-center gap-2.5 transition-colors whitespace-nowrap text-sm font-bold ${
              activeTab === "registry"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <BookOpen className="w-4 h-4" /> Legal Source Registry ({sources.length})
          </button>
        )}

        {!isAuditor && (
          <button
            onClick={() => setActiveTab("sandbox")}
            className={`py-3.5 px-6 border-b-2 flex items-center gap-2.5 transition-colors whitespace-nowrap text-sm font-bold ${
              activeTab === "sandbox"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Sparkles className="w-4 h-4" /> Hybrid Retrieval &amp; Citation Verifier
          </button>
        )}

        {canRunBenchmark && (
          <button
            onClick={() => setActiveTab("benchmark")}
            className={`py-3.5 px-6 border-b-2 flex items-center gap-2.5 transition-colors whitespace-nowrap text-sm font-bold ${
              activeTab === "benchmark"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <FileCheck className="w-4 h-4" /> Evaluation Benchmark Suite (5 Categories)
          </button>
        )}

        {canManageEscalations && (
          <button
            onClick={() => setActiveTab("escalations")}
            className={`py-3.5 px-6 border-b-2 flex items-center gap-2.5 transition-colors whitespace-nowrap text-sm font-bold ${
              activeTab === "escalations"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <AlertTriangle className="w-4 h-4 text-amber-500" /> Human Review Queue ({escalations.length})
          </button>
        )}
      </div>


      {/* TAB 1: Source Registry */}
      {activeTab === "registry" && (
        <div className="space-y-6">
          {/* Filter Bar */}
          <div className="bg-card border-2 border-border p-4 rounded-xl flex flex-col md:flex-row items-center gap-3 shadow-sm">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search legal documents by title, authority, section, or source ID..."
                className="w-full pl-9 pr-4 py-2.5 bg-input border border-border text-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-foreground"
              />
            </div>

            <div className="flex items-center gap-2 w-full md:w-auto">
              <select
                value={domainFilter}
                onChange={(e) => setDomainFilter(e.target.value)}
                aria-label="Filter by legal domain"
                className="bg-input border border-border text-xs rounded-lg px-3 py-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="ALL">All Legal Domains</option>
                <option value="CRIMINAL_PROCEDURE">Criminal Procedure (BNSS/CrPC)</option>
                <option value="PENAL_LAW">Penal Law (BNS/IPC)</option>
                <option value="JUDICIAL_PRECEDENT">Judicial Precedents (SC SOP)</option>
                <option value="PRISON_RULES">Prison Rules (Delhi Prison Rules)</option>
              </select>

              {!isAdvocate && (
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  aria-label="Filter by lifecycle status"
                  className="bg-input border border-border text-xs rounded-lg px-3 py-2.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="ALL">All Lifecycle States</option>
                  <option value="active">Active</option>
                  <option value="approved">Approved</option>
                  <option value="reviewed">Reviewed</option>
                  <option value="discovered">Discovered</option>
                  <option value="superseded">Superseded</option>
                  <option value="retired">Retired</option>
                </select>
              )}

              <button
                onClick={loadSources}
                className="p-2.5 border border-border rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
                title="Refresh Sources"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          {/* Sources List */}
          {loading ? (
            <div className="p-12 text-center text-muted-foreground font-medium">Loading authoritative sources...</div>
          ) : filteredSources.length === 0 ? (
            <div className="p-12 text-center bg-card border-2 border-border rounded-xl">
              <BookOpen className="w-10 h-10 text-muted-foreground mx-auto mb-3 opacity-40" />
              <div className="text-base font-bold text-foreground">No Legal Sources Found</div>
              <p className="text-xs text-muted-foreground mt-1">Try adjusting your search query or domain filters.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {filteredSources.map((src) => (
                <div
                  key={src.id}
                  className="bg-card border-2 border-border p-5 rounded-xl hover:border-primary/40 transition-all shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
                >
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {getStatusBadge(src.lifecycle_status)}
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                        {src.id}
                      </span>
                      <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                        {src.legal_domain}
                      </span>
                      <span className="text-xs text-muted-foreground flex items-center gap-1 font-medium">
                        <Calendar className="w-3.5 h-3.5" /> Effective: {src.effective_date}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-lg font-bold text-foreground hover:text-primary transition-colors">
                        {src.title}
                      </h3>
                      <div className="text-xs text-muted-foreground mt-0.5 flex flex-wrap items-center gap-x-4 gap-y-1">
                        <span><strong>Authority:</strong> {src.issuing_authority}</span>
                        <span><strong>Jurisdiction:</strong> {src.jurisdiction}</span>
                        <span><strong>Version:</strong> {src.version}</span>
                        <span><strong>Indexed Chunks:</strong> {src.chunk_count || 0}</span>
                      </div>
                    </div>

                    <div className="text-[11px] font-mono text-muted-foreground truncate max-w-xl">
                      <strong>SHA-256:</strong> {src.document_hash}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-start md:self-center">
                    <button
                      onClick={() => handleViewDetail(src.id)}
                      className="px-3 py-1.5 rounded bg-secondary hover:bg-secondary/80 text-foreground font-medium text-xs border border-border flex items-center gap-1.5 transition-colors"
                    >
                      <Layers className="w-3.5 h-3.5 text-primary" /> View Chunks &amp; Boundaries
                    </button>

                    {canUpdateLifecycle && (
                      <button
                        onClick={() => {
                          setLifecycleModalSource(src);
                          const allowed = ALLOWED_LIFECYCLE_TRANSITIONS[src.lifecycle_status] || [];
                          setTargetStatus(allowed[0] || "");
                          setSupersededById("");
                        }}
                        className="px-3 py-1.5 rounded bg-primary/10 hover:bg-primary/20 text-primary font-bold text-xs border border-primary/30 flex items-center gap-1.5 transition-colors"
                      >
                        <History className="w-3.5 h-3.5" /> Lifecycle State
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Hybrid Retrieval & Citation Integrity Sandbox */}
      {activeTab === "sandbox" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Panel 1: Hybrid Retrieval */}
          <div className="bg-card border-2 border-border p-5 rounded-xl space-y-4 shadow-sm">
            <div>
              <div className="flex items-center gap-2 text-primary font-bold text-sm">
                <Search className="w-4 h-4" /> Hybrid Section-Aware Retrieval Engine
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Executes exact section regex, lexical token matching, and authority reranking with active status prioritization.
              </p>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-foreground uppercase tracking-wider block mb-1">
                  Legal Query / Case Context
                </label>
                <textarea
                  rows={3}
                  value={sandboxQuery}
                  onChange={(e) => setSandboxQuery(e.target.value)}
                  className="w-full p-3 bg-input border border-border rounded-lg text-sm focus:ring-2 focus:ring-primary focus:outline-none text-foreground font-mono"
                  placeholder="e.g. bail section 479 undertrial detention period"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeSuperseded}
                    onChange={(e) => setIncludeSuperseded(e.target.checked)}
                    className="rounded border-border text-primary focus:ring-primary"
                  />
                  Include Superseded Laws (with -10.0 ranking penalty)
                </label>

                <button
                  onClick={handleRetrieve}
                  disabled={retrieving}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-all flex items-center gap-2"
                >
                  {retrieving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  Execute Hybrid Search
                </button>
              </div>
            </div>

            {/* Retrieval Results */}
            <div className="space-y-3 pt-2">
              <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                Retrieved Passages ({retrievedResults.length})
              </div>

              {retrievedResults.length === 0 ? (
                <div className="p-6 text-center border border-dashed border-border rounded-lg text-xs text-muted-foreground">
                  Run a query to inspect ranked legal passages and exact offsets.
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[480px] overflow-y-auto pr-1">
                  {retrievedResults.map((chunk, idx) => (
                    <div
                      key={chunk.id || idx}
                      className="p-3.5 rounded-lg border border-border bg-background space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-primary font-mono">{chunk.citation_key}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-semibold">
                            Score: {chunk.relevance_score}
                          </span>
                          {getStatusBadge(chunk.lifecycle_status)}
                        </div>
                      </div>

                      <div className="text-xs font-bold text-foreground">{chunk.section_title || chunk.source_title}</div>
                      <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed">
                        {chunk.normalized_text}
                      </p>

                      <div className="text-[10px] font-mono text-muted-foreground flex items-center justify-between pt-1 border-t border-border">
                        <span>Offset: [{chunk.start_char}..{chunk.end_char}]</span>
                        <span>{chunk.source_title}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

            {/* Panel 2: Citation Integrity Guardrail */}
            <div className="bg-card border-2 border-border p-5 rounded-xl space-y-4 shadow-sm">
            <div>
              <div className="flex items-center gap-2 text-primary font-bold text-sm">
                <ShieldCheck className="w-4 h-4" /> Citation Integrity &amp; Hallucination Guardrail
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Verifies that assertions cite active, existing legal authority. Flags ungrounded statements and escalates to human review.
              </p>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-foreground uppercase tracking-wider block mb-1">
                  Draft Legal Statement to Verify
                </label>
                <textarea
                  rows={4}
                  value={verifierStatement}
                  onChange={(e) => setVerifierStatement(e.target.value)}
                  className="w-full p-3 bg-input border border-border rounded-lg text-sm focus:ring-2 focus:ring-primary focus:outline-none text-foreground font-mono"
                  placeholder="e.g. As per Section 479 of BNSS, the accused is eligible for bail..."
                />
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleVerifyCitations}
                  disabled={verifying}
                  className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 transition-all flex items-center gap-2"
                >
                  {verifying ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                  Verify Citation Integrity
                </button>
              </div>
            </div>

            {/* Verifier Report */}
            {verifierReport && (
              <div
                className={`p-4 rounded-xl border-2 space-y-3 ${
                  verifierReport.status === "VERIFIED"
                    ? "bg-emerald-500/10 border-emerald-500/40"
                    : "bg-rose-500/10 border-rose-500/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    {verifierReport.status === "VERIFIED" ? (
                      <>
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        <span className="text-emerald-700 dark:text-emerald-400">CITATION INTEGRITY VERIFIED</span>
                      </>
                    ) : (
                      <>
                        <AlertTriangle className="w-4 h-4 text-rose-600" />
                        <span className="text-rose-700 dark:text-rose-400">LEGAL KNOWLEDGE INSUFFICIENT</span>
                      </>
                    )}
                  </div>
                  <div className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-background border border-border">
                    Grounding: {verifierReport.grounding_score}%
                  </div>
                </div>

                <p className="text-xs text-foreground leading-relaxed">{verifierReport.message}</p>

                {verifierReport.routed_to_human_review && (
                  <div className="p-2.5 rounded bg-amber-500/15 border border-amber-500/30 text-xs text-amber-700 dark:text-amber-400 font-medium">
                    ⚠️ <strong>Durable Human Review Task Created:</strong> This ungrounded statement has been routed to the Supervising Legal Officer queue for manual verification.
                  </div>
                )}

                {verifierReport.unsupported_citations?.length > 0 && (
                  <div className="text-xs text-rose-600 dark:text-rose-400 space-y-1">
                    <strong>Unsupported or Fabricated Citations:</strong>
                    <ul className="list-disc pl-5 font-mono">
                      {verifierReport.unsupported_citations.map((u: any, i: number) => (
                        <li key={i}>{u.raw_text} (Statute: {u.statute}, Section: {u.section})</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: Evaluation Benchmark Suite */}
      {activeTab === "benchmark" && canRunBenchmark && (
        <div className="bg-card border-2 border-border p-6 rounded-xl space-y-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-4">
            <div>
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-primary" /> Evaluation Benchmark Suite (5 Categories)
              </h2>
              <p className="text-xs text-muted-foreground mt-1">
                Runs 5 canonical test queries covering statute sections, offences, bail thresholds, procedure, and case documents. Measures Recall@1, Recall@3, and MRR.
              </p>
            </div>

            <button
              onClick={handleRunEvaluation}
              disabled={evaluating}
              className="px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-all flex items-center gap-2 shadow-sm self-start"
            >
              {evaluating ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileCheck className="w-4 h-4" />}
              Execute Benchmark Suite
            </button>
          </div>

          {benchmarks ? (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="p-4 bg-background border border-border rounded-lg text-center">
                  <div className="text-xs font-bold text-muted-foreground uppercase">Recall @ 1</div>
                  <div className="text-2xl font-bold text-emerald-600 mt-1">{benchmarks.recall_at_1}%</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">Top-1 Statutory Accuracy</div>
                </div>

                <div className="p-4 bg-background border border-border rounded-lg text-center">
                  <div className="text-xs font-bold text-muted-foreground uppercase">Recall @ 3</div>
                  <div className="text-2xl font-bold text-primary mt-1">{benchmarks.recall_at_3}%</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">Top-3 Passage Accuracy</div>
                </div>

                <div className="p-4 bg-background border border-border rounded-lg text-center">
                  <div className="text-xs font-bold text-muted-foreground uppercase">Mean Reciprocal Rank (MRR)</div>
                  <div className="text-2xl font-bold text-indigo-600 mt-1">{benchmarks.mean_reciprocal_rank}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">Rank Position Quality</div>
                </div>
              </div>

              {/* Per-query table */}
              <div className="border border-border rounded-lg overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-muted text-muted-foreground uppercase font-bold border-b border-border">
                    <tr>
                      <th className="p-3">Category</th>
                      <th className="p-3">Query Text</th>
                      <th className="p-3">Target Statute</th>
                      <th className="p-3">Expected Keys</th>
                      <th className="p-3">Top Retrieved</th>
                      <th className="p-3">Rank</th>
                      <th className="p-3">Reciprocal Rank</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {benchmarks.results?.map((b: any) => (
                      <tr key={b.id} className="hover:bg-secondary/40 transition-colors">
                        <td className="p-3 font-mono font-bold text-primary">{b.query_category}</td>
                        <td className="p-3 text-foreground font-medium max-w-xs truncate">{b.query_text}</td>
                        <td className="p-3 text-muted-foreground">{b.target_statute || "General"}</td>
                        <td className="p-3 font-mono text-[11px] text-muted-foreground">
                          {b.expected_citations?.join(", ")}
                        </td>
                        <td className="p-3 font-mono font-bold text-emerald-600">{b.top_retrieved_key || "None"}</td>
                        <td className="p-3 font-bold">
                          {b.rank === 1 ? (
                            <span className="px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-600">Rank 1</span>
                          ) : b.rank ? (
                            <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-600">Rank {b.rank}</span>
                          ) : (
                            <span className="px-2 py-0.5 rounded bg-rose-500/15 text-rose-600">Miss</span>
                          )}
                        </td>
                        <td className="p-3 font-mono">{b.reciprocal_rank}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-muted-foreground">
              Click &quot;Execute Benchmark Suite&quot; above to run the 5 canonical retrieval categories.
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Human Review Queue */}
      {activeTab === "escalations" && canManageEscalations && (
        <div className="bg-card border-2 border-border p-6 rounded-xl space-y-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div>
              <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" /> Statutory Citation Escalations Queue
              </h2>
              <p className="text-xs text-muted-foreground mt-1">
                Review assertions flagged by the Citation Integrity guardrail where citations were unsupported, invented, or unverified.
              </p>
            </div>

            <button
              onClick={loadEscalations}
              className="p-2 border border-border rounded-lg hover:bg-secondary text-muted-foreground"
              title="Refresh Escalations"
            >
              <RefreshCw className={`w-4 h-4 ${loadingEscalations ? "animate-spin" : ""}`} />
            </button>
          </div>

          {loadingEscalations ? (
            <div className="p-8 text-center text-muted-foreground">Loading review tasks...</div>
          ) : escalations.length === 0 ? (
            <div className="p-12 text-center bg-background border border-dashed border-border rounded-xl">
              <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3 opacity-60" />
              <div className="text-base font-bold text-foreground">Zero Pending Escalations</div>
              <p className="text-xs text-muted-foreground mt-1">All legal assertions verified or resolved.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {escalations.map((esc) => (
                <div key={esc.id} className="p-4 border-2 border-border rounded-xl bg-background space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono font-bold text-amber-600">{esc.id}</span>
                    <span className="text-muted-foreground">Created: {esc.created_at}</span>
                  </div>

                  <div>
                    <div className="text-xs font-bold text-muted-foreground uppercase">Flagged Draft Statement:</div>
                    <p className="text-sm font-mono text-foreground bg-muted/40 p-2.5 rounded-lg mt-1">
                      {esc.draft_statement}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-border">
                    <div className="text-xs text-muted-foreground">
                      <strong>Actor:</strong> {esc.actor_role} ({esc.actor_id}) | <strong>Grounding:</strong> {esc.grounding_score}%
                    </div>

                    <button
                      onClick={() => setResolvingEscalationId(esc.id)}
                      className="px-3 py-1.5 rounded bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-all flex items-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" /> Resolve Escalation
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL: View Chunks & Boundaries */}
      {selectedSourceDetail && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-foreground">{selectedSourceDetail.title}</h3>
                <div className="text-xs text-muted-foreground font-mono mt-0.5">
                  ID: {selectedSourceDetail.id} | Hash: {selectedSourceDetail.document_hash}
                </div>
              </div>
              <button
                onClick={() => setSelectedSourceDetail(null)}
                className="p-1 rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4">
              <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Document Chunks with Character Offsets ({selectedSourceDetail.chunks?.length || 0})
              </div>

              <div className="space-y-3">
                {selectedSourceDetail.chunks?.map((chk: any) => (
                  <div key={chk.id} className="p-3.5 rounded-lg border border-border bg-background space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-primary font-mono">{chk.citation_key}</span>
                      <span className="font-mono text-[11px] text-muted-foreground">
                        [{chk.start_char}..{chk.end_char}] ({chk.end_char - chk.start_char} chars)
                      </span>
                    </div>

                    <div className="text-xs font-bold text-foreground">{chk.section_title || "Statutory Segment"}</div>
                    <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap leading-relaxed bg-muted/30 p-2.5 rounded border border-border">
                      {chk.normalized_text}
                    </pre>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Lifecycle Transition */}
      {lifecycleModalSource && (
        <div className="fixed inset-0 z-[100] bg-black/75 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 overflow-y-auto pt-24 sm:pt-20">
          <div className="bg-card border-2 border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden my-auto max-h-[85vh] flex flex-col">

            <div className="p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-foreground">Update Lifecycle State</h3>
                <div className="text-xs text-muted-foreground truncate max-w-xs">{lifecycleModalSource.title}</div>
              </div>
              <button
                onClick={() => setLifecycleModalSource(null)}
                className="p-1 rounded-lg hover:bg-secondary text-muted-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateLifecycle} className="p-5 space-y-4">
              <div className="text-xs text-muted-foreground">
                Current Status: <strong className="text-foreground uppercase">{lifecycleModalSource.lifecycle_status}</strong>
              </div>

              <div>
                <label className="text-xs font-bold text-foreground block mb-1">Target Lifecycle State</label>
                <select
                  value={targetStatus}
                  onChange={(e) => setTargetStatus(e.target.value)}
                  className="w-full p-2.5 bg-input border border-border rounded-lg text-sm text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                >
                  {(ALLOWED_LIFECYCLE_TRANSITIONS[lifecycleModalSource.lifecycle_status] || []).map((st) => (
                    <option key={st} value={st}>
                      {st.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              {targetStatus === "superseded" && (
                <div>
                  <label className="text-xs font-bold text-foreground block mb-1">
                    Superseded By Source ID <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={supersededById}
                    onChange={(e) => setSupersededById(e.target.value)}
                    placeholder="e.g. src_bnss_2023_a1b2c3d4"
                    className="w-full p-2.5 bg-input border border-border rounded-lg text-sm font-mono text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="text-xs font-bold text-foreground block mb-1">Justification Notes / Gazette Ref</label>
                <textarea
                  rows={3}
                  value={lifecycleNotes}
                  onChange={(e) => setLifecycleNotes(e.target.value)}
                  placeholder="Provide statutory reference, date of enactment, or administrative approval reason..."
                  className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setLifecycleModalSource(null)}
                  className="px-4 py-2 rounded-lg border border-border text-xs font-bold hover:bg-secondary text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90"
                >
                  Confirm Transition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Ingest / Propose Legal Document */}
      {isUploadOpen && canIngest && (
        <div className="fixed inset-0 z-[100] bg-black/75 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 overflow-y-auto pt-24 sm:pt-20">
          <div className="bg-card border-2 border-border rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden my-auto">

            <div className="p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-foreground">
                  {isDlsa ? "Propose New Legal Source" : "Ingest Authoritative Legal Source"}
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Verbatim statutory text preservation. Text is normalized without semantic alterations.
                </p>
              </div>
              <button
                onClick={() => setIsUploadOpen(false)}
                className="p-1 rounded-lg hover:bg-secondary text-muted-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSource} className="p-5 overflow-y-auto space-y-4">
              {isDlsa && (
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-xs text-blue-700 dark:text-blue-400">
                  ℹ️ <strong>Governance Notice:</strong> Legal sources proposed by DLSA Legal Officers are placed in the <strong>&apos;discovered&apos;</strong> state pending review and approval by the Supervising Legal Officer.
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-foreground block mb-1">
                    Official Document Title <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="e.g. Bharatiya Nagarik Suraksha Sanhita, 2023"
                    className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-foreground block mb-1">Short Name / Code</label>
                  <input
                    type="text"
                    value={newShortName}
                    onChange={(e) => setNewShortName(e.target.value)}
                    placeholder="e.g. BNSS 2023"
                    className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-bold text-foreground block mb-1">Issuing Authority</label>
                  <input
                    type="text"
                    value={newAuthority}
                    onChange={(e) => setNewAuthority(e.target.value)}
                    placeholder="Parliament / Supreme Court / Prison Dept"
                    className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-foreground block mb-1">Legal Domain</label>
                  <select
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                  >
                    <option value="CRIMINAL_PROCEDURE">Criminal Procedure</option>
                    <option value="PENAL_LAW">Penal Law</option>
                    <option value="JUDICIAL_PRECEDENT">Judicial Precedent</option>
                    <option value="PRISON_RULES">Prison Rules</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-foreground block mb-1">Effective Date</label>
                  <input
                    type="date"
                    value={newEffectiveDate}
                    onChange={(e) => setNewEffectiveDate(e.target.value)}
                    className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-foreground block mb-1">Jurisdiction</label>
                <input
                  type="text"
                  value={newJurisdiction}
                  onChange={(e) => setNewJurisdiction(e.target.value)}
                  placeholder="e.g. India (National) or NCT of Delhi"
                  className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                />
              </div>


              <div>
                <label className="text-xs font-bold text-foreground block mb-1">
                  Verbatim Statutory Content (Full Text or Sections) <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={8}
                  required
                  value={newRawContent}
                  onChange={(e) => setNewRawContent(e.target.value)}
                  placeholder="Paste verbatim act text or rules here. Section headers like 'Section 479. Maximum period for which undertrial prisoner can be detained' will be automatically segmented..."
                  className="w-full p-3 bg-input border border-border rounded-lg text-xs font-mono text-foreground focus:ring-2 focus:ring-primary focus:outline-none leading-relaxed"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-4 py-2 rounded-lg border border-border text-xs font-bold hover:bg-secondary text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 flex items-center gap-2"
                >
                  {uploading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                  {isDlsa ? "Submit for Review" : "Ingest & Index Document"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Resolve Escalation */}
      {resolvingEscalationId && canManageEscalations && (
        <div className="fixed inset-0 z-[100] bg-black/75 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 overflow-y-auto pt-24 sm:pt-20">
          <div className="bg-card border-2 border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden my-auto max-h-[85vh] flex flex-col">

            <div className="p-5 border-b border-border flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-foreground">Resolve Legal Citation Escalation</h3>
                <div className="text-xs text-muted-foreground font-mono mt-0.5">Task ID: {resolvingEscalationId}</div>
              </div>
              <button
                onClick={() => setResolvingEscalationId(null)}
                className="p-1 rounded-lg hover:bg-secondary text-muted-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-bold text-foreground block mb-1">
                  Supervisory Resolution Justification <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={4}
                  required
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="Record judicial verification notes, corrections made, or confirmation of statutory grounding..."
                  className="w-full p-2.5 bg-input border border-border rounded-lg text-xs text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setResolvingEscalationId(null)}
                  className="px-4 py-2 rounded-lg border border-border text-xs font-bold hover:bg-secondary text-foreground"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleResolveEscalation}
                  className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-xs font-bold hover:bg-emerald-700 flex items-center gap-1.5"
                >
                  <Check className="w-3.5 h-3.5" /> Confirm Resolution
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
export default LegalSourcesAdmin;
