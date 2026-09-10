import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate, useParams } from "react-router-dom";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Download,
  RefreshCw,
  History,
  Scale,
  FileCheck,
  ShieldCheck,
  MessageSquare,
  Plus,
  Send,
  ChevronRight,
  BookOpen,
  Database,
  Layers,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import type {
  LegalDocumentDraft,
  DocumentTemplate,
  ReadinessReport,
  DraftDiffResult,
  SubmissionPackageManifest,
  InstitutionalDelegation,
} from "../lib/api";
import {
  fetchDocumentTemplates,
  fetchCaseDrafts,
  fetchCases,
  generateGroundedDraft,
  updateDraftContent,
  validateDraftReadiness,
  addDraftComment,
  approveDraft,
  rejectDraft,
  createDraftRevision,
  prepareSubmissionPackage,
  recordExternalFiling,
  fetchDraftDiff,
  exportDraftDocument,
  exportDraftPDF,
  fetchMyActiveDelegationApi,
  requestDocumentPreparationApi,
} from "../lib/api";
import DocumentDiffViewer from "../components/documents/DocumentDiffViewer";
import DocumentReadinessCard from "../components/documents/DocumentReadinessCard";

export const DocumentWorkspacePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { id: paramCaseId } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { hasRole } = useAuth();

  const caseIdFromUrl = paramCaseId || searchParams.get("case_id") || "UTP-0001";
  const draftIdFromUrl = searchParams.get("draft_id");

  // State
  const [caseId, setCaseId] = useState<string>(caseIdFromUrl);
  const [allCases, setAllCases] = useState<Array<{ case_id: string; name: string; jail_location?: string }>>([]);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("tmpl_bnss_479_bail_v1");
  const [caseDrafts, setCaseDrafts] = useState<LegalDocumentDraft[]>([]);
  const [activeDraft, setActiveDraft] = useState<LegalDocumentDraft | null>(null);

  // Role capability flags aligned with Section 37 11-Role Matrix (Stage 19)
  const isAdvocate = hasRole("DEFENSE_ADVOCATE");
  const isSupervisor = hasRole("SUPERVISING_LEGAL_OFFICER");
  const isDlsa = hasRole("DLSA_OFFICER");
  const isPlatformAdmin = hasRole("PLATFORM_ADMIN");
  const isAuditor = hasRole("READ_ONLY_AUDITOR");
  const isGovAdmin = hasRole("GOV_ADMIN");

  const [delegationInfo, setDelegationInfo] = useState<InstitutionalDelegation | null>(null);
  const [isCheckingDelegation, setIsCheckingDelegation] = useState<boolean>(false);
  const [isDelegatedDrafting, setIsDelegatedDrafting] = useState<boolean>(false);

  // Requisition Modal State
  const [showReqModal, setShowReqModal] = useState<boolean>(false);
  const [reqUrgency, setReqUrgency] = useState<"ROUTINE" | "URGENT" | "CRITICAL">("URGENT");
  const [reqReason, setReqReason] = useState<string>("");
  const [reqMissingPrereqs, setReqMissingPrereqs] = useState<string[]>([]);
  const [reqSending, setReqSending] = useState<boolean>(false);

  // Human-only legal approval reserved for assigned counsel and supervising legal officers
  const canEditDraft = (isAdvocate || isSupervisor || (isDlsa && isDelegatedDrafting && delegationInfo?.capability === "CAN_EDIT_DOCUMENT_DRAFT")) && !activeDraft?.is_immutable;
  const canApproveDraft = (isAdvocate || isSupervisor) && !activeDraft?.is_immutable;
  const canRejectDraft = (isAdvocate || isSupervisor || isDlsa) && !activeDraft?.is_immutable;
  const canGenerateDraft = isAdvocate || isSupervisor || (isDlsa && isDelegatedDrafting && (delegationInfo?.capability === "CAN_INITIATE_DOCUMENT_DRAFT" || delegationInfo?.capability === "CAN_EDIT_DOCUMENT_DRAFT"));
  const canComment = isAdvocate || isSupervisor || isDlsa;
  const canPackage = isAdvocate || isSupervisor;
  const canRecordFiling = isAdvocate || isSupervisor;
  const canExportInternalNotes = isAdvocate || isSupervisor || isAuditor;

  // Editor states
  const [workingContent, setWorkingContent] = useState<string>("");
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  // Inspection states
  const [activeTab, setActiveTab] = useState<"readiness" | "facts" | "rules" | "comments" | "filing">("readiness");
  const [editorMode, setEditorMode] = useState<"editor" | "diff_ai" | "diff_version">("editor");
  const [readiness, setReadiness] = useState<ReadinessReport | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [diffData, setDiffData] = useState<DraftDiffResult | null>(null);
  const [compareDraftId, setCompareDraftId] = useState<string>("");

  // Modals / forms
  const [newComment, setNewComment] = useState<string>("");
  const [isSubmittingComment, setIsSubmittingComment] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filing modal state
  const [filingRef, setFilingRef] = useState<string>("");
  const [filingCourt, setFilingCourt] = useState<string>("");
  const [filingDate, setFilingDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [submissionPackage, setSubmissionPackage] = useState<SubmissionPackageManifest | null>(null);

  // Load cases dynamically
  useEffect(() => {
    fetchCases()
      .then((data) => {
        if (Array.isArray(data)) {
          setAllCases(
            data.map((c: any) => ({
              case_id: c.case_id,
              name: c.name || c.accused_name || "Accused Inmate",
              jail_location: c.jail_location || c.facility_name || "Custody",
            }))
          );
        }
      })
      .catch((err) => console.error("Error loading cases for workspace:", err));
  }, []);

  // Sync caseId when URL params change
  useEffect(() => {
    const targetId = paramCaseId || searchParams.get("case_id");
    if (targetId && targetId !== caseId) {
      setCaseId(targetId);
    }
  }, [paramCaseId, searchParams]);

  // Load templates on mount
  useEffect(() => {
    fetchDocumentTemplates()
      .then((data) => {
        setTemplates(data);
        if (data.length > 0 && !selectedTemplateId) {
          setSelectedTemplateId(data[0].template_id || data[0].id || "");
        }
      })
      .catch((err) => console.error("Error loading templates:", err));
  }, []);

  // Load drafts for selected case
  const loadCaseDrafts = useCallback(async (cId: string, preferredDraftId?: string) => {
    try {
      const drafts = await fetchCaseDrafts(cId);
      setCaseDrafts(drafts);
      if (drafts.length > 0) {
        const target = preferredDraftId
          ? drafts.find((d) => d.draft_id === preferredDraftId) || drafts[0]
          : drafts[0];
        setActiveDraft(target);
        setWorkingContent(target.content_text);
        if (target.readiness_check_result) {
          setReadiness(target.readiness_check_result);
        }
        setSearchParams({ case_id: cId, draft_id: target.draft_id });
      } else {
        setActiveDraft(null);
        setWorkingContent("");
        setReadiness(null);
        setSearchParams({ case_id: cId });
      }
    } catch (err: any) {
      console.error("Failed to load case drafts:", err);
      setActionError(err.message || "Failed to load drafts for this matter.");
    }
  }, [setSearchParams]);

  useEffect(() => {
    loadCaseDrafts(caseId, draftIdFromUrl || undefined);
  }, [caseId, loadCaseDrafts]);

  const handleCaseSelect = (newCaseId: string) => {
    setCaseId(newCaseId);
    setSearchParams({ case_id: newCaseId });
    loadCaseDrafts(newCaseId);
  };

  // Load readiness check when active draft changes
  useEffect(() => {
    if (activeDraft) {
      validateDraftReadiness(activeDraft.draft_id)
        .then(setReadiness)
        .catch((err) => console.error("Readiness check error:", err));
    }
  }, [activeDraft?.draft_id]);

  // Query active delegation for DLSA Officer
  useEffect(() => {
    if (isDlsa && caseId) {
      setIsCheckingDelegation(true);
      fetchMyActiveDelegationApi({
        case_id: caseId,
        capability: "CAN_INITIATE_DOCUMENT_DRAFT",
        document_type: selectedTemplateId,
      })
        .then((res) => {
          if (res.is_delegated && res.delegation) {
            setDelegationInfo(res.delegation);
            setIsDelegatedDrafting(true);
          } else {
            setDelegationInfo(null);
            setIsDelegatedDrafting(false);
          }
        })
        .catch(() => {
          setDelegationInfo(null);
          setIsDelegatedDrafting(false);
        })
        .finally(() => {
          setIsCheckingDelegation(false);
        });
    } else {
      setDelegationInfo(null);
      setIsDelegatedDrafting(false);
    }
  }, [isDlsa, caseId, selectedTemplateId]);

  // Handle Draft Generation
  const handleGenerateDraft = async () => {
    setIsActionLoading(true);
    setActionError(null);
    try {
      const newDraft = await generateGroundedDraft(caseId, selectedTemplateId);
      await loadCaseDrafts(caseId, newDraft.draft_id);
      setActiveDraft(newDraft);
      setWorkingContent(newDraft.content_text);
      setActionSuccess(`Generated provisional draft v${newDraft.version_number} grounded in case facts.`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setActionError(err.message || "Failed to generate draft.");
    } finally {
      setIsActionLoading(false);
    }
  };

  // DLSA Requisition to Assigned Defence Counsel
  const handleOpenRequisitionModal = () => {
    const tmpl = templates.find((t) => t.template_id === selectedTemplateId);
    const tmplName = tmpl?.name || "Bail Application";
    setReqReason(`Formal legal aid drafting requisition: Undertrial inmate in case ${caseId} requires ${tmplName} prepared under statutory provisions.`);
    setReqMissingPrereqs([]);
    setShowReqModal(true);
  };

  const handleConfirmRequisition = async (e: React.FormEvent) => {
    e.preventDefault();
    setReqSending(true);
    setActionError(null);
    try {
      const tmpl = templates.find((t) => t.template_id === selectedTemplateId);
      const docType = tmpl?.doc_type || "BAIL_APPLICATION";
      const res = await requestDocumentPreparationApi({
        case_id: caseId,
        template_id: selectedTemplateId,
        document_type: docType,
        urgency: reqUrgency,
        reason: reqReason,
        missing_prerequisites: reqMissingPrereqs,
      });
      setShowReqModal(false);
      setActionSuccess(res.message || `Requisition dispatched: Task created for assigned counsel in UniversalTaskQueue for ${caseId}.`);
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err: any) {
      setActionError(err.message || "Failed to dispatch document preparation requisition.");
    } finally {
      setReqSending(false);
    }
  };

  // Save draft content
  const handleSaveContent = async () => {
    if (!activeDraft || activeDraft.is_immutable) return;
    setIsSaving(true);
    setSaveStatus(null);
    try {
      const updated = await updateDraftContent(activeDraft.draft_id, workingContent);
      setActiveDraft(updated);
      setSaveStatus("Saved working changes.");
      setTimeout(() => setSaveStatus(null), 3000);
      validateDraftReadiness(updated.draft_id).then(setReadiness);
    } catch (err: any) {
      setActionError(err.message || "Failed to save draft changes.");
    } finally {
      setIsSaving(false);
    }
  };

  // Trigger manual readiness check
  const handleRunReadiness = async () => {
    if (!activeDraft) return;
    setIsValidating(true);
    try {
      const rep = await validateDraftReadiness(activeDraft.draft_id);
      setReadiness(rep);
    } catch (err: any) {
      setActionError(err.message || "Failed to run readiness evaluation.");
    } finally {
      setIsValidating(false);
    }
  };

  // Approve Draft
  const handleApprove = async () => {
    if (!activeDraft) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const approved = await approveDraft(activeDraft.draft_id);
      setActiveDraft(approved);
      setActionSuccess("Document approved and sealed as immutable legal instrument.");
      await loadCaseDrafts(caseId, approved.draft_id);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setActionError(err.message || "Approval rejected by readiness check.");
    } finally {
      setIsActionLoading(false);
    }
  };

  // Reject Draft
  const handleReject = async () => {
    if (!activeDraft) return;
    const reason = window.prompt("Enter statutory or factual reason for rejecting this draft:");
    if (!reason) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const rejected = await rejectDraft(activeDraft.draft_id, reason);
      setActiveDraft(rejected);
      await loadCaseDrafts(caseId, rejected.draft_id);
      setActionSuccess("Draft petition rejected and marked for revision.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setActionError(err.message || "Failed to reject draft.");
    } finally {
      setIsActionLoading(false);
    }
  };

  // Initiate Revision Workflow
  const handleCreateRevision = async () => {
    if (!activeDraft) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const rev = await createDraftRevision(activeDraft.draft_id);
      await loadCaseDrafts(caseId, rev.draft_id);
      setActiveDraft(rev);
      setWorkingContent(rev.content_text);
      setActionSuccess(`Initiated Revision Version ${rev.version_number}. Previous version preserved.`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setActionError(err.message || "Failed to create draft revision.");
    } finally {
      setIsActionLoading(false);
    }
  };

  // Add Comment
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDraft || !newComment.trim()) return;
    setIsSubmittingComment(true);
    try {
      const updated = await addDraftComment(activeDraft.draft_id, newComment.trim());
      setActiveDraft(updated);
      setNewComment("");
    } catch (err: any) {
      setActionError(err.message || "Failed to submit comment.");
    } finally {
      setIsSubmittingComment(false);
    }
  };

  // Prepare Submission Package
  const handlePreparePackage = async () => {
    if (!activeDraft) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const pkg = await prepareSubmissionPackage(activeDraft.draft_id, [
        "Custody Certificate",
        "Remand Order",
        "Undertrial Nominal Roll",
        "Vakalatnama",
      ]);
      setSubmissionPackage(pkg);
      setActionSuccess("Submission package prepared. Automatic filing is prohibited by policy.");
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err: any) {
      setActionError(err.message || "Failed to prepare submission package.");
    } finally {
      setIsActionLoading(false);
    }
  };

  // Record External Filing
  const handleRecordFiling = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDraft || !filingRef.trim()) return;
    setIsActionLoading(true);
    setActionError(null);
    try {
      const updated = await recordExternalFiling(activeDraft.draft_id, {
        filing_reference: filingRef.trim(),
        filing_date: filingDate,
        court_name: filingCourt.trim() || "Principal Sessions Court",
      });
      setActiveDraft(updated);
      await loadCaseDrafts(caseId, updated.draft_id);
      setActionSuccess(`Court filing verified and recorded: ${filingRef}`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setActionError(err.message || "Failed to record filing.");
    } finally {
      setIsActionLoading(false);
    }
  };

  // Export clean or internal text
  const handleExport = async (includeInternalNotes: boolean) => {
    if (!activeDraft) return;
    try {
      const payload = await exportDraftDocument(activeDraft.draft_id, includeInternalNotes);
      const blob = new Blob([payload.exported_text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const typeLabel = includeInternalNotes ? "INTERNAL_CERTIFIED" : "EXTERNAL_COURT";
      link.download = `${activeDraft.case_id}_v${activeDraft.version_number}_${typeLabel}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setActionError(err.message || "Failed to export document.");
    }
  };

  // Export certified court PDF (%PDF-1.4)
  const handleExportPDF = async (includeInternalNotes: boolean = false) => {
    if (!activeDraft) return;
    try {
      const blob = await exportDraftPDF(activeDraft.draft_id, includeInternalNotes);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const typeLabel = includeInternalNotes ? "INTERNAL_CERTIFIED" : "EXTERNAL_COURT";
      link.download = `Petition_${activeDraft.case_id}_v${activeDraft.version_number}_${typeLabel}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setActionError(err.message || "Failed to export PDF document.");
    }
  };

  // Load version diff
  const handleFetchVersionDiff = async (otherDraftId: string) => {
    if (!activeDraft || !otherDraftId) return;
    setCompareDraftId(otherDraftId);
    try {
      const diff = await fetchDraftDiff(otherDraftId, activeDraft.draft_id);
      setDiffData(diff);
      setEditorMode("diff_version");
    } catch (err) {
      console.error("Diff fetch failed:", err);
    }
  };

  const wordCount = workingContent.trim() ? workingContent.trim().split(/\s+/).length : 0;
  const lineCount = workingContent ? workingContent.split("\n").length : 0;

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header Container in Newspaper Style */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground mb-1">
            <span
              onClick={() => navigate("/command-center")}
              className="hover:text-foreground cursor-pointer"
            >
              Operations
            </span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span
              onClick={() => navigate(`/case/${caseId}`)}
              className="hover:text-foreground cursor-pointer font-bold text-foreground"
            >
              Case {caseId}
            </span>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-primary font-bold">Document Workspace</span>
          </div>

          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase flex items-center gap-3">
            <Scale className="w-7 h-7 text-primary shrink-0" />
            <span>Professional Legal Document Workspace</span>
          </h1>
          <p className="text-xs font-serif text-muted-foreground mt-1 max-w-2xl leading-relaxed">
            Statutory drafting console with mandatory Section 479 BNSS rule verification, exact factual anchoring,
            pre-approval readiness gating, and tamper-resistant versioning.
          </p>
        </div>

        {/* Matter Selector */}
        <div className="flex items-center space-x-2 shrink-0">
          <div className="flex items-center space-x-2 bg-secondary/80 px-3 py-1.5 rounded-sm border border-border text-xs font-mono">
            <span className="text-muted-foreground uppercase font-bold text-[10px]">Matter:</span>
            <select
              value={caseId}
              onChange={(e) => handleCaseSelect(e.target.value)}
              className="bg-card border border-border rounded-sm px-2 py-1 text-foreground font-mono font-bold text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {allCases.length > 0 ? (
                <>
                  {!allCases.some((c) => c.case_id === caseId) && (
                    <option value={caseId}>{caseId} — Active Matter</option>
                  )}
                  {allCases.map((c) => (
                    <option key={c.case_id} value={c.case_id}>
                      {c.case_id} — {c.name} — {c.jail_location || "Custody"}
                    </option>
                  ))}
                </>
              ) : (
                <option value={caseId}>{caseId} — Active Matter</option>
              )}
            </select>
          </div>

          <button
            type="button"
            onClick={() => loadCaseDrafts(caseId)}
            className="p-2 rounded-sm bg-secondary hover:bg-muted text-foreground border border-border transition-colors"
            title="Refresh Matter Drafts"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Prominent Legal Advisory Banner */}
      <div className="bg-secondary/70 border-l-4 border-foreground p-4 rounded-sm flex items-start space-x-3 text-xs font-mono shadow-sm">
        <ShieldCheck className="w-5 h-5 text-foreground shrink-0 mt-0.5" />
        <div>
          <div className="font-bold text-foreground tracking-wide uppercase">
            AI-GENERATED PROVISIONAL DRAFT — MANDATORY HUMAN REVIEW & LEGAL SIGN-OFF REQUIRED
          </div>
          <div className="text-muted-foreground font-serif text-[11px] mt-0.5 leading-relaxed">
            All AI-assisted drafting outputs are strictly provisional candidate drafts and never constitute final judicial pleadings or filings. Formal scrutiny, citation grounding, and assigned legal counsel sign-off are required prior to court submission.
          </div>
        </div>
      </div>

      {/* Action Notification Banners */}
      {actionError && (
        <div className="bg-destructive/10 border-2 border-destructive/40 text-destructive text-xs font-mono p-3.5 rounded-sm flex items-start justify-between shadow-sm">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
            <span className="font-bold">{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-destructive hover:opacity-80 font-bold ml-4 text-sm"
          >
            &times;
          </button>
        </div>
      )}

      {actionSuccess && (
        <div className="bg-emerald-500/10 border-2 border-emerald-600/40 text-emerald-800 text-xs font-mono p-3.5 rounded-sm flex items-start justify-between shadow-sm">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span className="font-bold">{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            className="text-emerald-800 hover:opacity-80 font-bold ml-4 text-sm"
          >
            &times;
          </button>
        </div>
      )}

      {/* Control Bar: Version Lineage & Grounded Draft Generation */}
      <div className="bg-card border-2 border-border rounded-sm p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
        {/* Version Switcher */}
        <div className="flex items-center space-x-3">
          <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground flex items-center space-x-1.5">
            <History className="w-4 h-4 text-primary" />
            <span>Draft Lineage:</span>
          </span>
          {caseDrafts.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              {caseDrafts.map((d) => {
                const isSelected = activeDraft?.draft_id === d.draft_id;
                const statusStyle =
                  d.status === "APPROVED"
                    ? "border-emerald-700 bg-emerald-500/15 text-emerald-900"
                    : d.status === "FILED"
                    ? "border-purple-700 bg-purple-500/15 text-purple-950"
                    : d.status === "REJECTED"
                    ? "border-destructive bg-destructive/15 text-destructive"
                    : "border-border bg-secondary/80 text-foreground";

                return (
                  <button
                    key={d.draft_id}
                    type="button"
                    onClick={() => {
                      setActiveDraft(d);
                      setWorkingContent(d.content_text);
                      setSearchParams({ case_id: caseId, draft_id: d.draft_id });
                    }}
                    className={`px-3 py-1.5 rounded-sm text-xs font-mono border transition-all flex items-center space-x-1.5 ${statusStyle} ${
                      isSelected ? "ring-2 ring-primary font-bold shadow" : "hover:border-foreground"
                    }`}
                  >
                    <span>v{d.version_number}</span>
                    <span className="text-[10px] uppercase font-serif">({d.status})</span>
                    {d.is_immutable && <Lock className="w-3 h-3 text-foreground shrink-0" />}
                  </button>
                );
              })}
            </div>
          ) : (
            <span className="text-xs font-serif text-muted-foreground italic">No drafts initiated for this matter.</span>
          )}
        </div>

        {/* Template Selector & Requisition / Generation Controls */}
        <div className="flex items-center space-x-2">
          {isPlatformAdmin ? (
            <div className="px-3 py-1.5 rounded-sm bg-muted/60 border border-border text-[11px] font-mono text-muted-foreground">
              Technical Infrastructure View &bull; Drafting Restricted
            </div>
          ) : isGovAdmin ? (
            <div className="px-3 py-1.5 rounded-sm bg-muted/60 border border-border text-[11px] font-mono text-muted-foreground">
              Statewide Governance Oversight &bull; Read Only
            </div>
          ) : isAuditor ? (
            <div className="px-3 py-1.5 rounded-sm bg-muted/60 border border-border text-[11px] font-mono text-muted-foreground">
              Audit Scrutiny Console &bull; Read Only
            </div>
          ) : (
            <>
              <select
                value={selectedTemplateId}
                onChange={(e) => setSelectedTemplateId(e.target.value)}
                className="bg-background border border-border text-xs font-mono text-foreground rounded-sm px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary max-w-xs"
              >
                {templates.map((t) => (
                  <option key={t.template_id} value={t.template_id}>
                    {t.name} ({t.doc_type} | v{t.version} | {t.jurisdiction || "National"})
                  </option>
                ))}
              </select>

              {isDlsa && !isDelegatedDrafting ? (
                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={handleOpenRequisitionModal}
                    className="px-3.5 py-1.5 bg-primary hover:opacity-90 text-primary-foreground rounded-sm text-xs font-mono font-bold uppercase tracking-wider flex items-center space-x-1.5 shadow-sm transition-opacity"
                    title="Route document preparation requirement to assigned Panel Lawyer"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Send to Assigned Counsel</span>
                  </button>
                  {isCheckingDelegation && (
                    <span className="text-[10px] font-mono text-muted-foreground animate-pulse">Checking delegation...</span>
                  )}
                </div>
              ) : (
                canGenerateDraft && (
                  <div className="flex items-center space-x-2">
                    {isDlsa && delegationInfo && (
                      <span className="hidden md:inline-flex items-center px-2 py-1 bg-emerald-500/10 border border-emerald-600/40 text-emerald-800 text-[10px] font-mono font-bold rounded-sm">
                        <ShieldCheck className="w-3 h-3 mr-1 text-emerald-700" />
                        Delegation Active: {delegationInfo.delegation_id}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={handleGenerateDraft}
                      disabled={isActionLoading}
                      className="px-3.5 py-1.5 bg-primary hover:opacity-90 text-primary-foreground rounded-sm text-xs font-mono font-bold uppercase tracking-wider flex items-center space-x-1.5 disabled:opacity-50 transition-opacity shadow-sm"
                    >
                      <Plus className="w-4 h-4" />
                      <span>{isDlsa ? "Generate (Delegated)" : "Generate Grounded Draft"}</span>
                    </button>
                  </div>
                )
              )}
            </>
          )}
        </div>
      </div>

      {/* Main Workspace Layout */}
      {activeDraft ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left / Primary Column: Editor & Diff View (7 Cols) */}
          <div className="lg:col-span-7 space-y-4">
            {/* Header bar of editor */}
            <div className="bg-card border-2 border-border rounded-t-sm px-4 py-3 flex flex-wrap items-center justify-between gap-3 shadow-sm">
              <div className="flex items-center space-x-3 font-mono">
                <span className="text-xs font-bold text-foreground">
                  v{activeDraft.version_number} &bull; {activeDraft.status}
                </span>
                {activeDraft.is_immutable ? (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-sm bg-secondary border border-border text-foreground text-[10px] font-mono font-bold uppercase">
                    <Lock className="w-3 h-3 mr-1 text-primary" />
                    Sealed Legal Instrument
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-sm bg-primary/10 border border-primary/30 text-primary text-[10px] font-mono font-bold uppercase">
                    <FileText className="w-3 h-3 mr-1" />
                    Working Draft
                  </span>
                )}
                {saveStatus && <span className="text-xs text-emerald-700 font-serif italic">{saveStatus}</span>}
              </div>

              {/* Mode Toggles */}
              <div className="inline-flex rounded-sm shadow-sm bg-secondary p-0.5 border border-border font-mono text-xs">
                <button
                  type="button"
                  onClick={() => setEditorMode("editor")}
                  className={`px-3 py-1 rounded-sm font-bold uppercase transition-colors ${
                    editorMode === "editor" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Editor
                </button>
                <button
                  type="button"
                  onClick={() => setEditorMode("diff_ai")}
                  className={`px-3 py-1 rounded-sm font-bold uppercase transition-colors ${
                    editorMode === "diff_ai" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Machine Diff
                </button>
                {caseDrafts.length > 1 && (
                  <button
                    type="button"
                    onClick={() => {
                      const other = caseDrafts.find((d) => d.draft_id !== activeDraft.draft_id);
                      if (other) handleFetchVersionDiff(other.draft_id);
                    }}
                    className={`px-3 py-1 rounded-sm font-bold uppercase transition-colors ${
                      editorMode === "diff_version" ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    Version Diff
                  </button>
                )}
              </div>
            </div>

            {/* Immutability Notice if sealed */}
            {activeDraft.is_immutable && (
              <div className="bg-amber-500/10 border-x-2 border-b-2 border-amber-600/30 px-4 py-2.5 text-xs text-amber-900 font-mono flex items-center justify-between">
                <span>
                  This draft is approved by <strong>{activeDraft.approved_by || "Legal Officer"}</strong> and locked.
                  Modifications require initiating a new revision workflow.
                </span>
                {canGenerateDraft && (
                  <button
                    type="button"
                    onClick={handleCreateRevision}
                    className="px-2.5 py-1 rounded-sm bg-primary text-primary-foreground font-mono text-xs font-bold uppercase hover:opacity-90 shrink-0 ml-3"
                  >
                    Branch v{activeDraft.version_number + 1}
                  </button>
                )}
              </div>
            )}

            {/* Scrutiny Notice if user does not have drafting/editing privileges */}
            {!activeDraft.is_immutable && !canEditDraft && (
              <div className="bg-secondary border-x-2 border-b-2 border-border px-4 py-2.5 text-xs text-foreground font-mono flex items-center justify-between">
                <span>
                  Scrutiny & Review Mode: Legal pleading text editing is reserved for assigned defense counsel and supervising legal officers.
                </span>
                <span className="px-2 py-0.5 rounded-sm bg-muted text-muted-foreground font-mono text-[10px] font-bold uppercase">
                  Read Only
                </span>
              </div>
            )}

            {/* Editor or Diff Display */}
            {editorMode === "editor" ? (
              <div className="border-x-2 border-b-2 border-border bg-card rounded-b-sm overflow-hidden shadow-sm">
                <textarea
                  value={workingContent}
                  onChange={(e) => setWorkingContent(e.target.value)}
                  disabled={!canEditDraft}
                  rows={25}
                  className="w-full bg-[#FCFBF9] text-foreground font-mono text-xs p-5 leading-relaxed focus:outline-none resize-y disabled:bg-muted/20 disabled:text-muted-foreground select-text"
                  placeholder="Draft petition text..."
                />
                <div className="bg-muted/40 px-4 py-2.5 border-t border-border flex items-center justify-between text-xs text-muted-foreground font-mono">
                  <div>
                    <span>{lineCount} lines</span> &bull; <span>{wordCount} words</span> &bull;{" "}
                    <span>{workingContent.length} chars</span>
                  </div>
                  {canEditDraft && (
                    <button
                      type="button"
                      onClick={handleSaveContent}
                      disabled={isSaving}
                      className="px-3.5 py-1 rounded-sm bg-primary text-primary-foreground hover:opacity-90 font-mono text-xs font-bold uppercase tracking-wider disabled:opacity-50 transition-opacity"
                    >
                      {isSaving ? "Saving..." : "Save Working Text"}
                    </button>
                  )}
                </div>
              </div>
            ) : editorMode === "diff_ai" ? (
              <DocumentDiffViewer
                leftTitle="AI Machine-Generated Baseline"
                rightTitle="Current Working Petition Text"
                originalText={activeDraft.original_ai_text}
                currentText={workingContent}
              />
            ) : (
              <DocumentDiffViewer
                leftTitle={`Version Prior (${(compareDraftId || "").slice(0, 8)})`}
                rightTitle={`Active Version (v${activeDraft.version_number})`}
                diffData={diffData}
              />
            )}

            {/* Bottom Action Bar */}
            <div className="bg-card border-2 border-border rounded-sm p-4 flex flex-wrap items-center justify-between gap-3 shadow-sm font-mono text-xs">
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleRunReadiness}
                  disabled={isValidating}
                  className="px-3 py-1.5 rounded-sm bg-secondary hover:bg-muted text-foreground font-bold uppercase flex items-center space-x-1.5 border border-border transition-colors"
                >
                  <ShieldCheck className="w-4 h-4 text-primary" />
                  <span>{isValidating ? "Auditing..." : "Audit Readiness"}</span>
                </button>

                {/* Clean Court Copy Export (Text & PDF) */}
                <button
                  type="button"
                  onClick={() => handleExport(false)}
                  className="px-2.5 py-1.5 rounded-sm bg-secondary hover:bg-muted text-foreground font-bold uppercase flex items-center space-x-1.5 border border-border transition-colors text-[11px]"
                  title="Export Clean Court Copy without internal reviewer comments"
                >
                  <Download className="w-3.5 h-3.5 text-primary" />
                  <span>Court TXT</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleExportPDF(false)}
                  className="px-2.5 py-1.5 rounded-sm bg-secondary hover:bg-muted text-foreground font-bold uppercase flex items-center space-x-1.5 border border-border transition-colors text-[11px]"
                  title="Export Certified Court-Grade PDF (%PDF-1.4)"
                >
                  <FileText className="w-3.5 h-3.5 text-primary" />
                  <span>Court PDF</span>
                </button>

                {/* Internal Certified Copy Export for Authorized Roles */}
                {canExportInternalNotes && (
                  <>
                    <button
                      type="button"
                      onClick={() => handleExport(true)}
                      className="px-2.5 py-1.5 rounded-sm bg-secondary hover:bg-muted text-foreground font-bold uppercase flex items-center space-x-1.5 border border-border transition-colors text-[11px]"
                      title="Export Internal Certified Copy with Reviewer Commentary"
                    >
                      <Download className="w-3.5 h-3.5 text-primary" />
                      <span>Internal TXT</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleExportPDF(true)}
                      className="px-2.5 py-1.5 rounded-sm bg-secondary hover:bg-muted text-foreground font-bold uppercase flex items-center space-x-1.5 border border-border transition-colors text-[11px]"
                      title="Export Internal Certified PDF with Reviewer Commentary"
                    >
                      <FileText className="w-3.5 h-3.5 text-primary" />
                      <span>Internal PDF</span>
                    </button>
                  </>
                )}
              </div>

              {/* Approval / Packaging Controls */}
              <div className="flex items-center space-x-2">
                {!activeDraft.is_immutable ? (
                  <>
                    {canRejectDraft && (
                      <button
                        type="button"
                        onClick={handleReject}
                        disabled={isActionLoading}
                        className="px-3 py-1.5 rounded-sm bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/40 font-bold uppercase disabled:opacity-50 transition-colors"
                      >
                        Reject Draft
                      </button>
                    )}
                    {canApproveDraft && (
                      <button
                        type="button"
                        onClick={handleApprove}
                        disabled={isActionLoading || !(readiness?.can_approve ?? readiness?.is_ready)}
                        className="px-4 py-1.5 rounded-sm bg-primary hover:opacity-90 text-primary-foreground font-bold uppercase tracking-wider shadow disabled:opacity-40 disabled:cursor-not-allowed flex items-center space-x-1.5 transition-opacity"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Approve & Seal</span>
                      </button>
                    )}
                  </>
                ) : (
                  <>
                    {canPackage && (
                      <button
                        type="button"
                        onClick={handlePreparePackage}
                        disabled={isActionLoading}
                        className="px-3.5 py-1.5 rounded-sm bg-primary hover:opacity-90 text-primary-foreground font-bold uppercase tracking-wider shadow flex items-center space-x-1.5 transition-opacity"
                      >
                        <FileCheck className="w-4 h-4" />
                        <span>Prepare Submission Package</span>
                      </button>
                    )}
                    {canGenerateDraft && (
                      <button
                        type="button"
                        onClick={handleCreateRevision}
                        disabled={isActionLoading}
                        className="px-3 py-1.5 rounded-sm bg-secondary hover:bg-muted text-foreground border border-border font-bold uppercase transition-colors"
                      >
                        New Revision (v{activeDraft.version_number + 1})
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Right / Side Column: Inspection & Gating Tabs (5 Cols) */}
          <div className="lg:col-span-5 space-y-4">
            {/* Tab navigation */}
            <div className="flex border-2 border-border bg-muted/40 rounded-t-sm overflow-x-auto text-xs font-mono font-bold uppercase">
              <button
                type="button"
                onClick={() => setActiveTab("readiness")}
                className={`px-3 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-1.5 transition-colors ${
                  activeTab === "readiness"
                    ? "border-primary text-primary bg-card"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Readiness</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("facts")}
                className={`px-3 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-1.5 transition-colors ${
                  activeTab === "facts"
                    ? "border-primary text-primary bg-card"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                <span>Facts</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("rules")}
                className={`px-3 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-1.5 transition-colors ${
                  activeTab === "rules"
                    ? "border-primary text-primary bg-card"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>BNSS 479</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("comments")}
                className={`px-3 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-1.5 transition-colors ${
                  activeTab === "comments"
                    ? "border-primary text-primary bg-card"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Notes ({activeDraft.reviewer_comments?.length || 0})</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("filing")}
                className={`px-3 py-2.5 border-b-2 whitespace-nowrap flex items-center space-x-1.5 transition-colors ${
                  activeTab === "filing"
                    ? "border-primary text-primary bg-card"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                }`}
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Filing</span>
              </button>
            </div>

            {/* Tab 1: Readiness Gate */}
            {activeTab === "readiness" && (
              <div className="space-y-4">
                <DocumentReadinessCard
                  readiness={readiness}
                  loading={isValidating}
                  onRefresh={handleRunReadiness}
                />

                <div className="bg-card border-2 border-border rounded-sm p-4 text-xs space-y-2 shadow-sm">
                  <h5 className="font-serif font-bold text-foreground uppercase tracking-wide">
                    Institutional Gating Policy
                  </h5>
                  <p className="text-muted-foreground leading-relaxed font-serif">
                    Under the Nyaya Mitra Governance Protocol, an AI-generated draft cannot be signed off if there
                    are unresolved template placeholders, unsupported factual claims, ungrounded statutory citations,
                    or missing formal prayer clauses.
                  </p>
                </div>
              </div>
            )}

            {/* Tab 2: Anchored Case Facts Snapshot */}
            {activeTab === "facts" && (
              <div className="bg-card border-2 border-border rounded-sm p-4 text-xs space-y-3 shadow-sm">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <h4 className="font-serif font-bold text-foreground uppercase tracking-wide">
                    Exact Case Facts Snapshot
                  </h4>
                  <span className="text-muted-foreground font-mono text-[10px]">
                    Model: {activeDraft.ai_model_name}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-foreground font-mono">
                  <div className="bg-secondary/50 p-2.5 rounded-sm border border-border">
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Accused Inmate</span>
                    <span className="font-bold">{activeDraft.exact_case_facts?.accused_name || "N/A"}</span>
                  </div>
                  <div className="bg-secondary/50 p-2.5 rounded-sm border border-border">
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Custody Completed</span>
                    <span className="font-bold">{activeDraft.exact_case_facts?.custody_days ?? "N/A"} days</span>
                  </div>
                  <div className="bg-secondary/50 p-2.5 rounded-sm border border-border">
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Police Station & FIR</span>
                    <span className="font-bold">
                      {activeDraft.exact_case_facts?.fir_number || "N/A"} ({activeDraft.exact_case_facts?.police_station || "N/A"})
                    </span>
                  </div>
                  <div className="bg-secondary/50 p-2.5 rounded-sm border border-border">
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Trial Court</span>
                    <span className="font-bold">{activeDraft.exact_case_facts?.court_name || "Designated Trial Court"}</span>
                  </div>
                  <div className="col-span-2 bg-secondary/50 p-2.5 rounded-sm border border-border">
                    <span className="text-muted-foreground block text-[10px] uppercase font-bold">Offense Sections</span>
                    <span className="font-bold">{activeDraft.exact_case_facts?.offense_sections || "N/A"}</span>
                  </div>
                </div>

                {/* Source Documents */}
                <div className="pt-2 border-t border-border">
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground block mb-1">
                    Underlying Docket Records ({activeDraft.source_documents?.length || 0})
                  </span>
                  <div className="space-y-1">
                    {activeDraft.source_documents?.map((doc, idx) => (
                      <div
                        key={idx}
                        className="bg-secondary/40 p-2 rounded-sm border border-border flex items-center justify-between text-[11px] font-mono"
                      >
                        <span className="font-bold text-foreground">{doc.document_type}</span>
                        <span className="text-muted-foreground text-[10px]">
                          SHA: {doc.sha256_hash ? doc.sha256_hash.slice(0, 12) + "..." : "VERIFIED"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 3: Section 479 Legal Rules & Sources */}
            {activeTab === "rules" && (
              <div className="bg-card border-2 border-border rounded-sm p-4 text-xs space-y-3 shadow-sm font-mono">
                <div className="flex items-center justify-between border-b border-border pb-2">
                  <h4 className="font-serif font-bold text-foreground uppercase tracking-wide">
                    Section 479 BNSS Rule Engine
                  </h4>
                  <span
                    className={`px-2 py-0.5 rounded-sm text-[10px] font-bold uppercase tracking-wider ${
                      (activeDraft.legal_rule_result?.eligible ?? activeDraft.legal_rule_result?.is_eligible)
                        ? "bg-emerald-500/15 text-emerald-900 border border-emerald-700"
                        : "bg-destructive/15 text-destructive border border-destructive"
                    }`}
                  >
                    {(activeDraft.legal_rule_result?.eligible ?? activeDraft.legal_rule_result?.is_eligible)
                      ? "MANDATORY BAIL ELIGIBLE"
                      : "THRESHOLD NOT MET"}
                  </span>
                </div>

                <p className="text-foreground leading-relaxed font-serif">
                  <strong>Statutory Authority:</strong>{" "}
                  {activeDraft.legal_rule_result?.statute || "Section 479, Bharatiya Nagarik Suraksha Sanhita, 2023"}
                </p>

                {/* Retrieved Legal Sources */}
                <div className="space-y-2 pt-2 border-t border-border">
                  <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground block">
                    Retrieved Statutory Authorities
                  </span>
                  {activeDraft.retrieved_legal_sources && activeDraft.retrieved_legal_sources.length > 0 ? (
                    activeDraft.retrieved_legal_sources.map((src, idx) => (
                      <div key={idx} className="bg-secondary/40 p-3 rounded-sm border border-border space-y-1">
                        <div className="font-serif font-bold text-foreground text-xs uppercase">
                          {src.title || (src as any).statute || "Statutory Excerpt"}
                        </div>
                        <p className="text-muted-foreground text-[11px] leading-relaxed italic font-serif">
                          {src.excerpt || (src as any).statute_text || (src as any).text || "No text excerpt available."}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-muted-foreground italic font-serif text-xs">
                      No statutory sources retrieved for this draft.
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Tab 4: Reviewer Comments */}
            {activeTab === "comments" && (
              <div className="bg-card border-2 border-border rounded-sm p-4 text-xs space-y-3 shadow-sm">
                <h4 className="font-serif font-bold text-foreground uppercase tracking-wide border-b border-border pb-2">
                  Advocate & Supervisory Review Notes
                </h4>

                <div className="max-h-72 overflow-y-auto space-y-2 font-mono">
                  {activeDraft.reviewer_comments && activeDraft.reviewer_comments.length > 0 ? (
                    activeDraft.reviewer_comments.map((c) => (
                      <div key={c.comment_id} className="bg-secondary/40 p-3 rounded-sm border border-border space-y-1">
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1 font-bold uppercase">
                          <span className="text-foreground">
                            {c.author_name} ({c.author_role})
                          </span>
                          <span>{new Date(c.created_at).toLocaleString()}</span>
                        </div>
                        <p className="text-foreground text-xs leading-relaxed font-serif">{c.comment}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-muted-foreground italic font-serif text-center py-4">No review comments recorded yet.</p>
                  )}
                </div>

                {/* Comment Form */}
                {canComment ? (
                  <form onSubmit={handleAddComment} className="pt-2 border-t border-border space-y-2">
                    <textarea
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      placeholder="Enter review notes, citation queries, or verification instructions..."
                      rows={3}
                      className="w-full bg-background border border-border rounded-sm p-2 text-foreground font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <button
                      type="submit"
                      disabled={isSubmittingComment || !newComment.trim()}
                      className="px-3.5 py-1.5 bg-primary hover:opacity-90 text-primary-foreground rounded-sm text-xs font-mono font-bold uppercase tracking-wider disabled:opacity-50 flex items-center space-x-1.5 transition-opacity"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{isSubmittingComment ? "Submitting..." : "Post Review Note"}</span>
                    </button>
                  </form>
                ) : (
                  <p className="text-[11px] font-mono text-muted-foreground pt-2 border-t border-border italic">
                    Scrutiny commentary is restricted to assigned counsel and legal officers.
                  </p>
                )}
              </div>
            )}

            {/* Tab 5: Filing & Package Manifest */}
            {activeTab === "filing" && (
              <div className="bg-card border-2 border-border rounded-sm p-4 text-xs space-y-4 shadow-sm">
                <div className="border-b border-border pb-2">
                  <h4 className="font-serif font-bold text-foreground uppercase tracking-wide">
                    Court Filing Manifest & Anti-Auto-Filing Policy
                  </h4>
                  <p className="text-muted-foreground text-[11px] mt-1 font-serif">
                    Nyaya Mitra prepares verified submission packages with signed attestations. Statutory court filing
                    must be executed manually or through authenticated court registry callbacks.
                  </p>
                </div>

                {/* Manifest Status */}
                {activeDraft.submission_package || submissionPackage ? (
                  <div className="bg-secondary/60 border-2 border-border p-3 rounded-sm space-y-2 font-mono">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground uppercase">Submission Package Assembled</span>
                      <span className="text-[10px] text-muted-foreground font-bold">
                        {activeDraft.submission_package?.package_id || submissionPackage?.package_id}
                      </span>
                    </div>
                    <div className="text-foreground text-[11px]">
                      <strong>Filing Mode:</strong> MANUAL_OR_VERIFIED_INTEGRATION_ONLY
                    </div>
                    <div className="text-muted-foreground text-[11px] font-serif">
                      Automatic court submission is disabled by system policy. Download the verified court copy and
                      file through eCourts portal or physical registry.
                    </div>
                  </div>
                ) : (
                  canPackage && (
                    <button
                      type="button"
                      onClick={handlePreparePackage}
                      disabled={isActionLoading || !activeDraft.is_immutable}
                      className="w-full py-2 bg-secondary hover:bg-muted text-foreground rounded-sm border border-border font-mono text-xs font-bold uppercase tracking-wider disabled:opacity-50 transition-colors"
                    >
                      Assemble Submission Package Manifest
                    </button>
                  )
                )}

                {/* Record Court Filing Form */}
                {canRecordFiling ? (
                  <form onSubmit={handleRecordFiling} className="pt-3 border-t border-border space-y-2.5 font-mono">
                    <span className="font-bold text-foreground uppercase block text-xs">
                      Record External Court Filing Reference
                    </span>
                    <div>
                      <label className="text-muted-foreground block text-[10px] uppercase font-bold mb-1">
                        CNR Number / Court Diary Reference
                      </label>
                      <input
                        type="text"
                        value={filingRef}
                        onChange={(e) => setFilingRef(e.target.value)}
                        placeholder="e.g. CNR-DLCT01-002934-2026 or Diary No."
                        className="w-full bg-background border border-border rounded-sm p-2 text-foreground text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-muted-foreground block text-[10px] uppercase font-bold mb-1">
                          Filing Date
                        </label>
                        <input
                          type="date"
                          value={filingDate}
                          onChange={(e) => setFilingDate(e.target.value)}
                          className="w-full bg-background border border-border rounded-sm p-1.5 text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                      </div>
                      <div>
                        <label className="text-muted-foreground block text-[10px] uppercase font-bold mb-1">
                          Court Forum
                        </label>
                        <input
                          type="text"
                          value={filingCourt}
                          onChange={(e) => setFilingCourt(e.target.value)}
                          placeholder="e.g. Tis Hazari Courts"
                          className="w-full bg-background border border-border rounded-sm p-1.5 text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                      </div>
                    </div>
                    <button
                      type="submit"
                      disabled={isActionLoading || !filingRef.trim() || !activeDraft.is_immutable}
                      className="px-4 py-2 bg-primary hover:opacity-90 text-primary-foreground rounded-sm text-xs font-mono font-bold uppercase tracking-wider disabled:opacity-50 transition-opacity"
                    >
                      {isActionLoading ? "Recording..." : "Confirm & Log Court Filing"}
                    </button>
                  </form>
                ) : (
                  <p className="text-[11px] font-mono text-muted-foreground pt-3 border-t border-border italic">
                    External court filing logging is strictly restricted to assigned defense counsel and supervising legal officers.
                  </p>
                )}

                {/* Recorded Reference */}
                {activeDraft.filing_reference && (
                  <div className="bg-secondary/80 border border-border p-2.5 rounded-sm text-foreground text-[11px] font-mono">
                    <strong>Recorded Filing CNR:</strong> {activeDraft.filing_reference}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-card border-2 border-border rounded-sm p-12 text-center space-y-3 shadow-sm">
          <FileText className="w-12 h-12 text-muted-foreground mx-auto" />
          <h3 className="text-lg font-serif font-bold text-foreground uppercase tracking-wide">
            No Drafts Initiated for this Matter
          </h3>
          <p className="text-xs font-serif text-muted-foreground max-w-md mx-auto leading-relaxed">
            Click &ldquo;Generate Grounded Draft&rdquo; above to initiate a provisional legal petition anchored to verified case facts and statutory Section 479 BNSS guidelines.
          </p>
          {isDlsa && !isDelegatedDrafting ? (
            <button
              type="button"
              onClick={handleOpenRequisitionModal}
              className="px-4 py-2 bg-primary hover:opacity-90 text-primary-foreground rounded-sm text-xs font-mono font-bold uppercase tracking-wider inline-flex items-center space-x-1.5 shadow-sm transition-opacity"
            >
              <Send className="w-4 h-4" />
              <span>Send to Assigned Counsel</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleGenerateDraft}
              disabled={isActionLoading}
              className="px-4 py-2 bg-primary hover:opacity-90 text-primary-foreground rounded-sm text-xs font-mono font-bold uppercase tracking-wider inline-flex items-center space-x-1.5 disabled:opacity-50 transition-opacity shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>{isDlsa ? "Generate (Delegated)" : "Generate Grounded Draft"}</span>
            </button>
          )}
        </div>
      )}

      {/* DLSA Document Preparation Requisition Modal */}
      {showReqModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border max-w-lg w-full rounded-sm shadow-xl p-6 font-mono space-y-4">
            <div className="flex items-start justify-between border-b border-border pb-3">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wide text-foreground">
                  Institutional Document Preparation Requisition
                </h3>
                <p className="text-[11px] font-serif text-muted-foreground mt-0.5">
                  Matter: {caseId} &bull; Requisitioning Authority: DLSA Officer
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowReqModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-bold"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleConfirmRequisition} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-bold text-foreground text-[10px] uppercase mb-1">
                  Document Template / Type
                </label>
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className="w-full bg-background border border-border rounded-sm p-2 text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  {templates.map((t) => (
                    <option key={t.template_id} value={t.template_id}>
                      {t.name} ({t.doc_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-bold text-foreground text-[10px] uppercase mb-1">
                  Urgency Classification
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(["ROUTINE", "URGENT", "CRITICAL"] as const).map((urg) => (
                    <button
                      key={urg}
                      type="button"
                      onClick={() => setReqUrgency(urg)}
                      className={`py-1.5 px-2 border rounded-sm font-bold text-[10px] uppercase transition-colors ${
                        reqUrgency === urg
                          ? "border-primary bg-primary/10 text-primary shadow-sm"
                          : "border-border bg-secondary hover:bg-muted text-foreground"
                      }`}
                    >
                      {urg}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-bold text-foreground text-[10px] uppercase mb-1">
                  Missing Prerequisites Checklist (Optional)
                </label>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  {[
                    { id: "custody_certificate", label: "Custody Certificate" },
                    { id: "remand_order", label: "Remand Order" },
                    { id: "fir_copy", label: "FIR Copy" },
                    { id: "charge_sheet", label: "Charge Sheet" },
                  ].map((p) => {
                    const isChecked = reqMissingPrereqs.includes(p.id);
                    return (
                      <label
                        key={p.id}
                        className="flex items-center space-x-2 border border-border p-1.5 rounded-sm bg-secondary/50 cursor-pointer text-foreground"
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setReqMissingPrereqs([...reqMissingPrereqs, p.id]);
                            } else {
                              setReqMissingPrereqs(reqMissingPrereqs.filter((x) => x !== p.id));
                            }
                          }}
                          className="rounded-sm border-border"
                        />
                        <span>{p.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block font-bold text-foreground text-[10px] uppercase mb-1">
                  Factual Grounds & Institutional Coordination Notes
                </label>
                <textarea
                  value={reqReason}
                  onChange={(e) => setReqReason(e.target.value)}
                  rows={3}
                  placeholder="Enter statutory grounds or specific instructions for assigned counsel..."
                  className="w-full bg-background border border-border rounded-sm p-2 text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary text-xs"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowReqModal(false)}
                  className="px-3 py-1.5 border border-border bg-secondary hover:bg-muted text-foreground rounded-sm text-xs font-mono uppercase"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={reqSending || !reqReason.trim()}
                  className="px-4 py-1.5 bg-primary hover:opacity-90 text-primary-foreground rounded-sm text-xs font-mono font-bold uppercase tracking-wider disabled:opacity-50 transition-opacity"
                >
                  {reqSending ? "Dispatching..." : "Dispatch to Assigned Counsel"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentWorkspacePage;
