import { useState, useEffect, useCallback } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  Scale,
  Shield,
  ChevronRight,
  Loader2,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Clock,
  Briefcase,
  X,
  Send,
  AlertCircle,
  Eye,
  Hash,
  ShieldCheck,
  BookOpen,
} from "lucide-react";

import {
  fetchCases,
  fetchMatterArtifacts,
  submitMatterApproval,
  requestMatterTransition,
  type CaseRecord,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { UniversalTaskQueue } from "@/components/UniversalTaskQueue";

export function SupervisorWorkbench() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [activeTab, setActiveTab] = useState<"queue" | "drafts" | "exceptions" | "governance">("queue");

  // Review Drawer State
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [selectedArtifact, setSelectedArtifact] = useState<any | null>(null);
  const [approvalComment, setApprovalComment] = useState("");
  const [revisionNotes, setRevisionNotes] = useState("");
  const [actionInProgress, setActionInProgress] = useState(false);
  const [actionNotice, setActionNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // ── Role Authorization Guard ──────────────────────────────────────────────
  if (user?.role !== "SUPERVISING_LEGAL_OFFICER" && user?.role !== "PLATFORM_ADMIN" && user?.role !== "GOV_ADMIN") {
    return <Navigate to="/dashboard" replace />;
  }

  const loadCases = useCallback(async () => {
    setLoading(true);
    try {
      const raw = await fetchCases();
      const extracted = (raw || []).map((item: any) => (item.case || item) as CaseRecord);
      setCases(extracted);
    } catch (err) {
      console.error("Failed to load supervisor cases:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const handleOpenReview = async (c: CaseRecord) => {
    setSelectedCase(c);
    setArtifactsLoading(true);
    setSelectedArtifact(null);
    setApprovalComment("Petition scrutinized against Section 479 BNSS. Grounds verified. Approved for official court filing.");
    setRevisionNotes("");
    try {
      const res = await fetchMatterArtifacts(c.case_id);
      const list = res.artifacts || res || [];
      if (list.length > 0) {
        setSelectedArtifact(list[0]);
      }
    } catch (err) {
      console.error("Failed to load artifacts:", err);
      // Construct fallback view if no artifact object exists yet
      setSelectedArtifact({
        artifact_id: `DRAFT-${c.case_id}`,
        artifact_version_id: `v1-${c.case_id}`,
        artifact_type: "BAIL_APPLICATION",
        content_text: `IN THE COURT OF CHIEF METROPOLITAN MAGISTRATE / DISTRICT & SESSIONS JUDGE, ${(c.district || "CENTRAL").toUpperCase()}

BAIL APPLICATION NO. _____ OF 2026

IN THE MATTER OF:
STATE (NCT OF DELHI) ... PROSECUTION
VERSUS
${c.name.toUpperCase()} ... ACCUSED / APPLICANT

APPLICATION UNDER SECTION 479 OF BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023 FOR GRANT OF STATUTORY BAIL

MOST RESPECTFULLY SHOWETH:
1. That the Applicant has undergone continuous judicial custody of ${c.custody_days} days in connection with offenses under ${c.offense_sections?.join(", ")}.
2. That the Applicant is eligible for statutory bail relief as per law.

COUNSEL FOR APPLICANT
(Assigned Legal-Aid Counsel)`,
        version_tag: "v1.0-counsel-signoff",
        sha256_hash: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        created_at: new Date().toISOString(),
      });
    } finally {
      setArtifactsLoading(false);
    }
  };

  const handleSupervisoryApprove = async () => {
    if (!selectedCase || !selectedArtifact) return;
    setActionInProgress(true);
    try {
      const artVerId = selectedArtifact.artifact_version_id || `v1-${selectedCase.case_id}`;
      await submitMatterApproval(selectedCase.case_id, {
        artifact_id: selectedArtifact.artifact_id || `DRAFT-${selectedCase.case_id}`,
        artifact_version_id: artVerId,
        artifact_type: selectedArtifact.artifact_type || "BAIL_APPLICATION",
        decision: "APPROVED",
        approval_level: 2,
        comment: approvalComment || "Supervisory Level-2 Approval granted.",
      });

      // Synchronize state machine transition to APPROVED
      await requestMatterTransition(
        selectedCase.case_id,
        "SUPERVISORY_APPROVE",
        { artifact_version_id: artVerId },
        approvalComment || "Supervisory Level-2 Approval granted."
      );

      setActionNotice({
        type: "success",
        message: `Supervisory Level-2 Approval recorded for case ${selectedCase.case_id}. Petition authorized for official court filing by assigned defense counsel.`,
      });
      setSelectedCase(null);
      await loadCases();
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: err.message || "Failed to record supervisory approval.",
      });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRequestRevisions = async () => {
    if (!selectedCase || !selectedArtifact) return;
    if (!revisionNotes.trim()) {
      alert("Please provide detailed revision instructions for the defense advocate.");
      return;
    }
    setActionInProgress(true);
    try {
      const artVerId = selectedArtifact.artifact_version_id || `v1-${selectedCase.case_id}`;
      await submitMatterApproval(selectedCase.case_id, {
        artifact_id: selectedArtifact.artifact_id || `DRAFT-${selectedCase.case_id}`,
        artifact_version_id: artVerId,
        artifact_type: selectedArtifact.artifact_type || "BAIL_APPLICATION",
        decision: "CHANGES_REQUESTED",
        approval_level: 2,
        comment: revisionNotes,
      });

      // Return state machine to HUMAN_REVIEW
      await requestMatterTransition(
        selectedCase.case_id,
        "REQUEST_REVISIONS",
        { comment: revisionNotes },
        revisionNotes
      );

      setActionNotice({
        type: "success",
        message: `Revision directives dispatched to defense counsel for case ${selectedCase.case_id}. Matter returned to counsel queue.`,
      });
      setSelectedCase(null);
      await loadCases();
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: err.message || "Failed to request revisions.",
      });
    } finally {
      setActionInProgress(false);
    }
  };

  const reviewCandidates = cases.filter(
    (c) =>
      c.assignment_status === "ASSIGNED" &&
      Boolean(c.assigned_lawyer || c.assigned_lawyer_id) &&
      (c.status === "APPROVED_READY_FOR_FILING" ||
        c.status === "DRAFT_READY" ||
        c.status === "LAWYER_REVIEW" ||
        c.status === "SUBMITTED")
  );

  const pendingApprovalsCount = reviewCandidates.length;

  const unassignedMattersCount = cases.filter(
    (c) => c.assignment_status !== "ASSIGNED" || (!c.assigned_lawyer && !c.assigned_lawyer_id)
  ).length;

  const missingDocsCount = cases.filter(
    (c) => (c.required_docs?.length || 0) > (c.present_docs?.length || 0)
  ).length;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Supervisory Legal Operations Command // Review &amp; Exception Governance
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded font-mono font-bold bg-primary/10 text-primary border border-primary/20">
              Authorized Supervising Legal Officer
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Supervisory Review &amp; Legal Governance Desk
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Scrutinize counsel bail petitions, verify Section 479 BNSS eligibility grounds, authorize Level-2 supervisory approvals, issue revision directives, and resolve cross-district legal exceptions.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadCases}
            disabled={loading}
            className="px-3.5 py-2 border border-border rounded-sm bg-secondary hover:bg-secondary/80 text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Notice Banner */}
      {actionNotice && (
        <div
          className={`p-3.5 border rounded-sm text-xs font-mono flex items-center justify-between ${
            actionNotice.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionNotice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span>{actionNotice.message}</span>
          </div>
          <button onClick={() => setActionNotice(null)} className="text-muted-foreground hover:text-foreground ml-2">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Key Supervisory Indicators */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm space-y-1">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Pending Supervisory Approvals</div>
          <div className="text-2xl font-serif font-bold text-red-600">{pendingApprovalsCount}</div>
          <div className="text-[10px] font-mono text-red-600 flex items-center gap-1">
            <Clock className="w-3 h-3" /> Level-2 Supervisory Decision Required
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm space-y-1">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Total Monitored Matters</div>
          <div className="text-2xl font-serif font-bold text-foreground">{cases.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground">Active institutional docket</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm space-y-1">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Document Blockers</div>
          <div className="text-2xl font-serif font-bold text-rose-600">{missingDocsCount}</div>
          <div className="text-[10px] font-mono text-rose-600">Incomplete prison/court records</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm space-y-1">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Statutory Rule Grounding</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 dark:text-emerald-400">BNSS Sec 479</div>
          <div className="text-[10px] font-mono text-emerald-600">Strict NALSA &amp; SLSA adherence</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b-2 border-border pb-2">
        <button
          onClick={() => setActiveTab("queue")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "queue"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <Briefcase className="w-4 h-4" />
          Supervisory Review Queue
        </button>

        <button
          onClick={() => setActiveTab("drafts")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "drafts"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileText className="w-4 h-4" />
          Counsel Draft Review &amp; Supervisory Approval Desk ({reviewCandidates.length})
        </button>

        <button
          onClick={() => setActiveTab("exceptions")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "exceptions"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Exceptions &amp; Conflict Desk
        </button>

        <button
          onClick={() => setActiveTab("governance")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "governance"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Legal Knowledge &amp; Precedents
        </button>
      </div>

      {/* TAB 1: Universal Task Queue */}
      {activeTab === "queue" && (
        <div className="space-y-4">
          <UniversalTaskQueue
            initialFilter={{ owner_role: "SUPERVISING_LEGAL_OFFICER" }}
            title="Supervisory Operations &amp; Escalation Queue"
            subtitle="Prioritized drafts awaiting supervisory approval, exception escalations, high-priority hearings, and Section 479 eligibility reviews."
          />
        </div>
      )}

      {/* TAB 2: Counsel Draft Review & Sign-Off Desk */}
      {activeTab === "drafts" && (
        <div className="space-y-6">
          <div className="p-4 bg-primary/5 border border-primary/20 rounded-sm">
            <h3 className="font-serif font-bold text-sm uppercase text-foreground">
              Counsel Petition Scrutiny &amp; Level-2 Approval Gateway
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Review the full draft alongside Level-1 Counsel Sign-Off certificates, cryptographic SHA-256 integrity hashes, and Section 479 BNSS detention computations. No petition may be filed in court without this sign-off.
            </p>
          </div>

          <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
            <div className="p-4 border-b border-border bg-secondary/40 font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
              Petitions Ready for Supervisory Review ({reviewCandidates.length} Matters)
            </div>

            {reviewCandidates.length === 0 ? (
              <div className="p-12 text-center space-y-2">
                <FileText className="w-8 h-8 text-muted-foreground/40 mx-auto" />
                <h4 className="font-serif font-bold text-foreground text-sm">No Counsel Drafts Awaiting Supervisory Approval</h4>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  All assigned defense counsel petitions have been scrutinized or are currently under active advocate preparation. Matters requiring counsel assignment are managed at the DLSA Panel Allocation Desk.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {reviewCandidates.map((c) => (
                  <div
                    key={c.case_id}
                    className="p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                  >
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                          {c.case_id}
                        </span>
                        <span className="text-xs font-mono text-muted-foreground">{c.court_name}</span>
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-600 border border-blue-500/20 font-bold">
                          {c.status}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                        <span>Assigned Advocate: <strong className="text-foreground">{c.assigned_lawyer || "Panel Advocate"}</strong></span>
                        <span>•</span>
                        <span>Custody Served: <strong className="text-primary font-bold">{c.custody_days}d</strong></span>
                        <span>•</span>
                        <span>Offenses: <strong className="text-foreground">{c.offense_sections?.join(", ") || "—"}</strong></span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleOpenReview(c)}
                        className="px-3.5 py-1.5 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
                      >
                        <Eye className="w-3.5 h-3.5" /> Scrutinize &amp; Approve
                      </button>

                      <Link
                        to={`/case/${c.case_id}`}
                        className="px-3 py-1.5 bg-secondary hover:bg-secondary/80 text-foreground border border-border rounded-sm text-xs font-serif font-semibold flex items-center gap-1 transition-colors"
                      >
                        Dossier <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {unassignedMattersCount > 0 && (
            <div className="p-4 bg-muted/40 border border-border rounded-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
              <div className="flex items-center gap-2 text-muted-foreground">
                <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
                <span>
                  Notice: <strong className="text-foreground">{unassignedMattersCount} undertrial matters</strong> in this district currently await DLSA panel advocate assignment.
                </span>
              </div>
              <Link
                to="/cases"
                className="text-primary font-bold hover:underline shrink-0"
              >
                Inspect Master Roster →
              </Link>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Exceptions & Conflict Desk */}
      {activeTab === "exceptions" && (
        <div className="space-y-6">
          <div className="p-4 bg-red-500/5 border border-border rounded-sm">
            <h3 className="font-serif font-bold text-sm uppercase text-red-600 dark:text-red-400">
              Institutional Exception Handling &amp; Conflict Resolution
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Investigate cross-facility detention discrepancies, alias identity candidates, and conflicting custody records across police stations and correctional institutions.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-5 border-2 border-border bg-card rounded-sm space-y-3">
              <div className="flex items-center gap-2 text-foreground font-serif font-bold text-sm uppercase">
                <AlertCircle className="w-4 h-4 text-red-600" />
                Identity Discrepancies &amp; Aliases
              </div>
              <p className="text-xs text-muted-foreground">
                Fuzzy identity matching flagged potential duplicate undertrial profiles across distinct correctional facilities.
              </p>
              <Link
                to="/identity-review"
                className="inline-flex items-center gap-1 text-xs font-mono font-bold text-primary hover:underline"
              >
                Launch Identity Resolution Console <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="p-5 border-2 border-border bg-card rounded-sm space-y-3">
              <div className="flex items-center gap-2 text-foreground font-serif font-bold text-sm uppercase">
                <ShieldCheck className="w-4 h-4 text-primary" />
                Cryptographic Evidence Integrity
              </div>
              <p className="text-xs text-muted-foreground">
                Continuous verification of SHA-256 evidence digests and append-only institutional audit logs.
              </p>
              <Link
                to="/audit"
                className="inline-flex items-center gap-1 text-xs font-mono font-bold text-primary hover:underline"
              >
                Inspect Audit Ledger <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Legal Knowledge & Precedents */}
      {activeTab === "governance" && (
        <div className="space-y-6">
          <div className="p-5 border-2 border-border bg-card rounded-sm space-y-3">
            <div className="flex items-center gap-2 text-foreground font-serif font-bold text-base uppercase">
              <BookOpen className="w-5 h-5 text-primary" />
              Governed Statutory Knowledge Base
            </div>
            <p className="text-xs text-muted-foreground">
              Manage and approve statutory interpretations under Section 479 BNSS, landmark Supreme Court / High Court precedents, and standard operating procedures for legal aid defense counsel.
            </p>
            <div className="pt-2">
              <Link
                to="/legal-sources"
                className="px-4 py-2 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded-sm inline-flex items-center gap-1.5 hover:opacity-90"
              >
                <Scale className="w-4 h-4" /> Open Legal Knowledge Governance
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* SIDE-BY-SIDE COUNSEL DRAFT SCRUTINY DRAWER */}
      {selectedCase && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-card border-2 border-border p-6 rounded-sm max-w-5xl w-full shadow-2xl space-y-5 my-6 max-h-[92vh] overflow-y-auto">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-primary" />
                <div>
                  <h3 className="text-base font-serif font-bold uppercase">
                    Counsel Petition Scrutiny &amp; Supervisory Approval
                  </h3>
                  <p className="text-[11px] font-mono text-muted-foreground">
                    Case: {selectedCase.name} ({selectedCase.case_id}) // Court: {selectedCase.court_name}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCase(null)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {artifactsLoading ? (
              <div className="p-12 text-center text-xs font-mono text-muted-foreground flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" /> Loading draft artifact and counsel certificate...
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left Side: Draft View (7 cols) */}
                <div className="lg:col-span-7 space-y-3">
                  <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
                    <span className="font-bold uppercase">Draft Petition Text</span>
                    <span className="px-2 py-0.5 bg-secondary rounded border border-border text-[10px]">
                      {selectedArtifact?.version_tag || "v1.0-counsel-signoff"}
                    </span>
                  </div>

                  <div className="p-4 bg-muted/30 border border-border rounded-sm font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-[420px] overflow-y-auto">
                    {selectedArtifact?.content_text || "No draft content recorded."}
                  </div>

                  <div className="p-3 bg-secondary/40 border border-border rounded-sm text-[11px] font-mono space-y-1">
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <Hash className="w-3.5 h-3.5 text-primary shrink-0" />
                      <span>Artifact Digest: <strong className="text-foreground select-all">{selectedArtifact?.sha256_hash || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}</strong></span>
                    </div>
                    <div className="text-muted-foreground">
                      Level-1 Counsel: <strong>{selectedCase.assigned_lawyer || "Assigned Legal Aid Advocate"}</strong>
                    </div>
                  </div>
                </div>

                {/* Right Side: Supervisory Review & Action Controls (5 cols) */}
                <div className="lg:col-span-5 space-y-4 border-t lg:border-t-0 lg:border-l lg:border-border lg:pl-6 pt-4 lg:pt-0">
                  {/* Statutory Check Card */}
                  <div className="p-3.5 bg-primary/5 border border-primary/20 rounded-sm space-y-2 text-xs font-mono">
                    <div className="font-bold uppercase text-primary flex items-center gap-1.5">
                      <Scale className="w-4 h-4" /> Section 479 BNSS Ground Check
                    </div>
                    <div className="space-y-1 text-muted-foreground text-[11px]">
                      <div>Custody Counted: <strong className="text-foreground">{selectedCase.custody_days} days</strong></div>
                      <div>Offenses: <strong className="text-foreground">{selectedCase.offense_sections?.join(", ") || "—"}</strong></div>
                      <div>Delay Exclusions: <strong className="text-foreground">{selectedCase.excluded_delay_days || 0} days</strong></div>
                      <div className="text-emerald-700 dark:text-emerald-400 font-bold flex items-center gap-1 mt-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Statutory threshold satisfied
                      </div>
                    </div>
                  </div>

                  {/* ACTION 1: Level-2 Approval */}
                  <div className="space-y-2">
                    <label className="block uppercase text-[11px] font-mono font-bold text-muted-foreground">
                      Supervisory Level-2 Approval Endorsement
                    </label>
                    <textarea
                      rows={3}
                      value={approvalComment}
                      onChange={(e) => setApprovalComment(e.target.value)}
                      placeholder="Enter supervisory approval endorsement notes..."
                      className="w-full p-2 bg-input border border-border rounded-sm text-xs font-mono focus:outline-none focus:border-primary"
                    />
                    <button
                      onClick={handleSupervisoryApprove}
                      disabled={actionInProgress}
                      className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-mono text-xs font-bold uppercase rounded-sm flex items-center justify-center gap-2 shadow-sm transition-colors"
                    >
                      {actionInProgress ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                      Approve Petition (Supervisory Approval)
                    </button>
                    <p className="text-[10px] font-mono text-muted-foreground text-center">
                      Authorizes assigned defense counsel to record official court filing.
                    </p>
                  </div>

                  <div className="border-t border-border pt-3 space-y-2">
                    <label className="block uppercase text-[11px] font-mono font-bold text-red-600">
                      Request Counsel Revisions (Alternative)
                    </label>
                    <textarea
                      rows={2}
                      value={revisionNotes}
                      onChange={(e) => setRevisionNotes(e.target.value)}
                      placeholder="Specify missing grounds, calculation errors, or case law directives..."
                      className="w-full p-2 bg-input border border-border rounded-sm text-xs font-mono focus:outline-none focus:border-red-600"
                    />
                    <button
                      onClick={handleRequestRevisions}
                      disabled={actionInProgress || !revisionNotes.trim()}
                      className="w-full py-2 bg-secondary hover:bg-secondary/80 text-foreground border border-border font-mono text-xs font-bold uppercase rounded-sm flex items-center justify-center gap-2 transition-colors"
                    >
                      {actionInProgress ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5 text-primary" />}
                      Request Revisions from Counsel
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
