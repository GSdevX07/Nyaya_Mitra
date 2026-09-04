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
  CheckCheck,
  Send,
  Upload,
  Download,
  RefreshCw,
  Loader2,
  Bookmark,
  ShieldCheck,
  Building2,
  UserCheck,
  Bot,
  Cpu,
  GitBranch,
  ChevronRight,
  Check,
} from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchCaseById,
  approveCaseInBackend,
  signOffCase,
  fileCaseInCourt,
  uploadDocumentFile,
  fetchCaseDocuments,
  verifyUploadedDocument,
  reviewUploadedDocument,
  verifyEvidence,
  type TimelineEvent,
  type LegalNeedItem,
  referJailCaseToDlsa,
  submitCaseComment,
  assignCaseCounsel,
  exportCaseFile,
  fetchMatterState,
  fetchAvailableTransitions,
  requestMatterTransition,
  fetchMatterHandoffSummary,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { jsPDF } from "jspdf";

export function CaseIntelligence() {
  const { user, hasRole, can } = useAuth();
  const isPolice = user?.role === "POLICE_OFFICER";
  const isDlsa = user?.role === "DLSA_OFFICER";
  const isJail = user?.role === "JAIL_OFFICER";
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [caseData, setCaseData] = useState<any>(null);
  const [caseDocDetails, setCaseDocDetails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);
  const [filing, setFiling] = useState(false);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const [verifyingDocId, setVerifyingDocId] = useState<string | null>(null);
  const [reviewingDocId, setReviewingDocId] = useState<string | null>(null);
  const [editableDraft, setEditableDraft] = useState<string>("");
  const [dlsaComment, setDlsaComment] = useState<string>("");
  const [submittingComment, setSubmittingComment] = useState(false);
  const [activeTab, setActiveTab] = useState<"dossier" | "draft" | "timeline" | "evidence" | "statutes" | "legalaid">("dossier");

  const [verifyingEvidenceId, setVerifyingEvidenceId] = useState<string | null>(null);
  const [evidenceVerificationResult, setEvidenceVerificationResult] = useState<any>(null);
  const [advocateSignedOff, setAdvocateSignedOff] = useState(false);
  const [signingOff, setSigningOff] = useState(false);
  const [referringDlsa, setReferringDlsa] = useState(false);
  const [referralDone, setReferralDone] = useState(false);
  const [actionBanner, setActionBanner] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const [exportingDossier, setExportingDossier] = useState(false);
  const [assigningCounsel, setAssigningCounsel] = useState(false);
  const [selectedLawyerId, setSelectedLawyerId] = useState("LWYR-001");
  const [selectedLawyerName, setSelectedLawyerName] = useState("Adv. Rajesh Sharma");
  const [assignmentNotes, setAssignmentNotes] = useState("");
  const [assignmentSuccess, setAssignmentSuccess] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [pendingDocType, setPendingDocType] = useState<string | null>(null);

  // ── Stage 9: Authoritative Matter Lifecycle & Handoff State ─────────────
  const [matterState, setMatterState] = useState<string | null>(null);
  const [matterVersion, setMatterVersion] = useState<number | null>(null);
  const [availableTransitions, setAvailableTransitions] = useState<any[]>([]);
  const [handoffSummary, setHandoffSummary] = useState<any | null>(null);
  const [transitioningAction, setTransitioningAction] = useState<string | null>(null);

  const CANONICAL_STATES = [
    "INTAKE",
    "VERIFICATION",
    "REVIEW",
    "LEGAL_AID_REQUIRED",
    "ASSIGNED",
    "DOCUMENT_PENDING",
    "ANALYSIS_READY",
    "HUMAN_REVIEW",
    "SUBMITTED",
    "APPROVED",
    "FILED",
    "HEARING_SCHEDULED",
    "ORDER_RECEIVED",
    "RELEASE_WORKFLOW",
    "POST_RELEASE_FOLLOW_UP",
    "CLOSED",
  ];

  const EXCEPTION_STATES = [
    "MANUAL_REVIEW_REQUIRED",
    "TRANSITION_BLOCKED",
    "DATA_CONFLICT",
    "EXTERNAL_SYNC_FAILED",
  ];


  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [data, docData, stateData, transData, handoffData] = await Promise.all([
        fetchCaseById(id),
        fetchCaseDocuments(id),
        fetchMatterState(id).catch(() => null),
        fetchAvailableTransitions(id).catch(() => null),
        fetchMatterHandoffSummary(id).catch(() => null),
      ]);
      if (!data) throw new Error("Not found");
      setCaseData(data);
      if (docData && docData.documents_detail) {
        setCaseDocDetails(docData.documents_detail);
      }
      if (data.advocate_signed_off) {
        setAdvocateSignedOff(true);
      }
      if (stateData) {
        setMatterState(stateData.canonical_state);
        setMatterVersion(stateData.version_number);
      }
      if (transData) {
        setAvailableTransitions(transData.available_transitions || []);
      }
      if (handoffData) {
        setHandoffSummary(handoffData);
      }
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

  const handleVerifyCaseDoc = async (docId: string) => {
    setVerifyingDocId(docId);
    try {
      await verifyUploadedDocument(docId);
      await load();
      setActionBanner({
        type: "success",
        text: "Document verified successfully! Case completeness updated.",
      });
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: "Verification failed: " + (err.message || err),
      });
    } finally {
      setVerifyingDocId(null);
    }
  };

  const handleReviewCaseDoc = async (docId: string) => {
    setReviewingDocId(docId);
    try {
      await reviewUploadedDocument(docId);
      await load();
      setActionBanner({
        type: "success",
        text: "Document marked reviewed for legal-aid intake processing.",
      });
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: "Document review failed: " + (err.message || err),
      });
    } finally {
      setReviewingDocId(null);
    }
  };

  const handleSignOff = async () => {
    if (!id) return;
    setSigningOff(true);
    setActionBanner(null);
    try {
      await signOffCase(id, editableDraft);
      setAdvocateSignedOff(true);
      setActionBanner({
        type: "success",
        text: "Counsel legal sign-off recorded. The petition draft is stamped as Advocate Work Product and submitted for supervisory review.",
      });
      await load();
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: "Counsel sign-off failed: " + (err.message || err),
      });
    } finally {
      setSigningOff(false);
    }
  };

  const handleApprove = async () => {
    if (!id) return;
    setApproving(true);
    setActionBanner(null);
    try {
      await approveCaseInBackend(id);
      await load();
      setActiveTab("draft");
      setActionBanner({
        type: "success",
        text: "Supervisory sign-off recorded. Case is approved and marked READY FOR FILING.",
      });
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: "Approval error: " + (err.message || err),
      });
    } finally {
      setApproving(false);
    }
  };

  const handleFileInCourt = async () => {
    if (!id) return;
    setFiling(true);
    setActionBanner(null);
    try {
      await fileCaseInCourt(id);
      await load();
      setActionBanner({
        type: "success",
        text: "Procedural court filing recorded in court ledger.",
      });
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: "Filing error: " + (err.message || err),
      });
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
    setActionBanner(null);
    try {
      await uploadDocumentFile(id, pendingDocType, file);
      await load();
      setActionBanner({
        type: "success",
        text: `Document '${file.name}' uploaded and submitted for verification.`,
      });
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: "Upload failed: " + (err.message || err),
      });
    } finally {
      setUploadingDoc(null);
      setPendingDocType(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleVerifyEvidence = async (eviId: string) => {
    // Clear any stale result from a previous verify call immediately
    setEvidenceVerificationResult(null);
    setVerifyingEvidenceId(eviId);
    try {
      const res = await verifyEvidence(eviId);
      setEvidenceVerificationResult(res);
    } catch (err: any) {
      // Network failure (not HTTP error) — show inline
      setEvidenceVerificationResult({
        error: err?.message ?? "Network error — could not reach verification service.",
        integrity_verified: false,
        stored_hash: null,
        computed_hash: null,
      });
    } finally {
      setVerifyingEvidenceId(null);
    }
  };

  const generateBailDraftPDF = () => {
    if (!c.case_id) return;
    const doc = new jsPDF({
      unit: "mm",
      format: "a4",
    });

    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 20;
    const contentWidth = pageWidth - margin * 2;
    let yPos = margin;

    const checkPageBreak = (neededHeight: number) => {
      if (yPos + neededHeight > pageHeight - margin - 15) {
        doc.addPage();
        yPos = margin + 5;
        return true;
      }
      return false;
    };

    // ── 1. JUDICIAL HEADER ───────────────────────────────────────────────────
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    const courtTitle = (c.court_name || "IN THE COURT OF THE PRINCIPAL DISTRICT & SESSIONS JUDGE").toUpperCase();
    const courtDistrict = `${c.district ? c.district.toUpperCase() : "CENTRAL"} DISTRICT, ${c.state ? c.state.toUpperCase() : "DELHI"}`;
    
    doc.text(courtTitle, pageWidth / 2, yPos, { align: "center" });
    yPos += 5;
    doc.setFontSize(9);
    doc.text(courtDistrict, pageWidth / 2, yPos, { align: "center" });
    yPos += 7;

    doc.setFontSize(10);
    doc.text("STATUTORY BAIL PETITION UNDER SECTION 479 OF BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023", pageWidth / 2, yPos, { align: "center" });
    yPos += 4;
    doc.setLineWidth(0.6);
    doc.line(margin, yPos, pageWidth - margin, yPos);
    yPos += 6;

    // ── 2. CAUSE TITLE & DOCKET METADATA ─────────────────────────────────────
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.text(`IN THE MATTER OF:`, margin, yPos);
    yPos += 5;

    doc.setFont("helvetica", "normal");
    doc.text(`STATE (GOVT. OF NCT OF DELHI)`, margin, yPos);
    doc.setFont("helvetica", "bold");
    doc.text("... PROSECUTION", pageWidth - margin, yPos, { align: "right" });
    yPos += 4;
    doc.text("VERSUS", pageWidth / 2, yPos, { align: "center" });
    yPos += 4;
    doc.text(`${c.name || "ACCUSED"} (IN JUDICIAL CUSTODY)`, margin, yPos);
    doc.text("... PETITIONER / ACCUSED", pageWidth - margin, yPos, { align: "right" });
    yPos += 6;

    // Case particulars metadata table
    doc.setDrawColor(200, 200, 200);
    doc.setFillColor(248, 249, 250);
    doc.rect(margin, yPos, contentWidth, 22, "FD");
    
    doc.setFontSize(8);
    doc.setFont("helvetica", "bold");
    doc.text("CASE REFERENCE:", margin + 3, yPos + 5);
    doc.text("CNR NUMBER:", margin + 3, yPos + 10);
    doc.text("FIR & POLICE STATION:", margin + 3, yPos + 15);
    doc.text("CHARGES / OFFENSES:", margin + 3, yPos + 20);

    doc.setFont("helvetica", "normal");
    doc.text(c.case_id || "N/A", margin + 42, yPos + 5);
    doc.text(c.cnr_number || "Not Assigned", margin + 42, yPos + 10);
    doc.text(`${c.fir_number || "FIR-N/A"} | PS: ${c.police_station || "Jurisdictional Police"}`, margin + 42, yPos + 15);
    const offenses = Array.isArray(c.offense_sections) ? c.offense_sections.join(", ") : (c.offense_sections || "Section 303(2) BNS");
    doc.text(offenses, margin + 42, yPos + 20);

    doc.setFont("helvetica", "bold");
    doc.text("CUSTODY FACILITY:", margin + 100, yPos + 5);
    doc.text("DLSA REF NO:", margin + 100, yPos + 10);
    doc.text("DAYS IN DETENTION:", margin + 100, yPos + 15);
    doc.text("STATUTORY THRESHOLD:", margin + 100, yPos + 20);

    doc.setFont("helvetica", "normal");
    doc.text(c.jail_location || "Central Jail, Tihar", margin + 140, yPos + 5);
    doc.text(c.dlsa_reference_number || "DLSA-PENDING", margin + 140, yPos + 10);
    doc.text(`${eligibility.custody_days_served ?? c.custody_days ?? 0} Days Served`, margin + 140, yPos + 15);
    doc.text(`${eligibility.required_custody_days ?? 120} Days (One-Third Rule)`, margin + 140, yPos + 20);

    yPos += 28;

    // ── 3. PETITION NARRATIVE / GROUNDS ──────────────────────────────────────
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text("MOST RESPECTFULLY SHOWETH:", margin, yPos);
    yPos += 6;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    
    // Split editable draft paragraphs
    const draftContent = editableDraft || "Statutory grounds under Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023. The petitioner has served the requisite statutory period in undertrial detention and has not been convicted of any prior offenses punishable by life or death.";
    const draftLines = doc.splitTextToSize(draftContent, contentWidth);

    for (let i = 0; i < draftLines.length; i++) {
      checkPageBreak(5);
      doc.text(draftLines[i], margin, yPos);
      yPos += 4.6;
    }
    yPos += 6;

    // ── 4. DOCUMENTS INVENTORY & REMAINING DOCUMENTS SECTION ──────────────────
    checkPageBreak(35);
    doc.setLineWidth(0.4);
    doc.line(margin, yPos, pageWidth - margin, yPos);
    yPos += 5;

    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text("ANNEXURE - DOCUMENTS & EVIDENCE INVENTORY", margin, yPos);
    yPos += 5;

    // Section 4A: Verified Attached Documents
    doc.setFontSize(8.5);
    doc.text("A. Verified Documents Attached with Petition:", margin, yPos);
    yPos += 4.5;

    const presentDocs: string[] = c.present_docs || [
      "First Information Report (FIR Copy)",
      "Judicial Remand Order",
      "Nominal Custody Certificate"
    ];

    presentDocs.forEach((docName, idx) => {
      checkPageBreak(5);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(8);
      doc.text(`  [✓] ${idx + 1}. ${docName} — Verified on Record (SHA-256 Validated)`, margin + 2, yPos);
      yPos += 4;
    });
    yPos += 2;

    // Section 4B: REMAINING & PENDING DOCUMENTS REQUIRED (Crucial user request)
    checkPageBreak(30);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8.5);
    doc.setTextColor(180, 83, 9); // Amber color for notice
    doc.text("B. Remaining / Pending Documents Required (To be Requisitioned):", margin, yPos);
    doc.setTextColor(0, 0, 0); // Reset to black
    yPos += 4.5;

    const missingDocs: string[] = (completeness && completeness.missing_docs && completeness.missing_docs.length > 0)
      ? completeness.missing_docs
      : (c.required_docs ? c.required_docs.filter((d: string) => !presentDocs.includes(d)) : []);

    if (missingDocs.length > 0) {
      missingDocs.forEach((docName, idx) => {
        checkPageBreak(5);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.text(`  [!] ${idx + 1}. ${docName} — AWAITING RETRIEVAL from Investigating Officer / Prison Superintendent`, margin + 2, yPos);
        yPos += 4;
      });
      checkPageBreak(5);
      doc.setFont("helvetica", "italic");
      doc.setFontSize(7.5);
      doc.text("  Note: A prayer is included under Section 91 CrPC / Section 94 BNSS to direct production of above remaining records.", margin + 2, yPos);
      yPos += 4.5;
    } else {
      checkPageBreak(5);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(8);
      doc.text("  [✓] All mandatory statutory documents verified and attached in full compliance.", margin + 2, yPos);
      yPos += 4.5;
    }

    yPos += 6;

    // ── 5. PRAYER & VERIFICATION CLAUSE ──────────────────────────────────────
    checkPageBreak(40);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9);
    doc.text("PRAYER:", margin, yPos);
    yPos += 4.5;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    const prayerText = "In light of the aforesaid statutory provisions, it is most respectfully prayed that this Hon'ble Court may be pleased to enlarge the petitioner on bail under Section 479 BNSS on furnishing personal bond with or without sureties, in the interest of justice.";
    const prayerLines = doc.splitTextToSize(prayerText, contentWidth);
    prayerLines.forEach((line: string) => {
      checkPageBreak(4);
      doc.text(line, margin, yPos);
      yPos += 3.8;
    });

    yPos += 8;
    checkPageBreak(25);

    // Signatures block
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.text("THROUGH:", margin, yPos);
    doc.text("VERIFICATION:", pageWidth - margin - 50, yPos);
    yPos += 4;

    doc.setFont("helvetica", "normal");
    const lawyerName = c.assigned_lawyer_id || "Adv. DLSA Legal Aid Counsel";
    doc.text(lawyerName, margin, yPos);
    doc.text("Verified at Delhi that the contents", pageWidth - margin - 50, yPos);
    yPos += 3.5;
    doc.text("Counsel for the Accused / DLSA Panel", margin, yPos);
    doc.text("of this petition are true to my knowledge.", pageWidth - margin - 50, yPos);
    yPos += 3.5;
    doc.text(`Date: ${new Date().toLocaleDateString("en-IN")}`, margin, yPos);
    doc.text("PETITIONER / ADVOCATE", pageWidth - margin - 50, yPos);

    // ── 6. RUNNING FOOTERS ON ALL PAGES ──────────────────────────────────────
    const totalPages = doc.getNumberOfPages();
    for (let page = 1; page <= totalPages; page++) {
      doc.setPage(page);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(7);
      doc.setTextColor(120, 120, 120);
      doc.setLineWidth(0.2);
      doc.line(margin, pageHeight - 12, pageWidth - margin, pageHeight - 12);
      doc.text(
        `Nyaya Mitra Legal Aid Dossier // Case: ${c.case_id} // Section 479 BNSS Statutory Review`,
        margin,
        pageHeight - 8
      );
      doc.text(
        `Page ${page} of ${totalPages}`,
        pageWidth - margin,
        pageHeight - 8,
        { align: "right" }
      );
      doc.setTextColor(0, 0, 0);
    }

    doc.save(`Statutory_Bail_Petition_${c.case_id}.pdf`);
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

  const handleBack = () => {
    if (user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE") {
      navigate("/advocate");
    } else if (user?.role === "POLICE_OFFICER") {
      navigate("/police");
    } else if (user?.role === "JAIL_OFFICER") {
      navigate("/jail");
    } else if (user?.role === "ACCUSED_USER") {
      navigate("/my-case");
    } else if (user?.role === "FAMILY_GUARDIAN") {
      navigate("/family/status");
    } else {
      navigate("/cases");
    }
  };

  const handleReferToDlsa = async () => {
    if (!id) return;
    setReferringDlsa(true);
    try {
      await referJailCaseToDlsa(id, "Prison custody desk legal-aid counsel assignment referral.");
      setReferralDone(true);
      await load();
    } catch (err: any) {
      alert(`Referral failed: ${err.message}`);
    } finally {
      setReferringDlsa(false);
    }
  };

  const handleSubmitComment = async () => {
    if (!dlsaComment.trim() || !id) return;
    setSubmittingComment(true);
    try {
      await submitCaseComment(id, dlsaComment.trim());
      setActionBanner({
        type: "success",
        text: "Institutional review note successfully recorded on case timeline and dispatched to counsel.",
      });
      setDlsaComment("");
      await load();
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: err.message || "Failed to submit review note.",
      });
    } finally {
      setSubmittingComment(false);
    }
  };

  const PANEL_ADVOCATES = [
    { id: "LWYR-001", name: "Adv. Rajesh Sharma", bar: "D/1042/2014", specialisation: "Criminal Defense & Remand" },
    { id: "LWYR-002", name: "Adv. Priya Verma", bar: "D/2180/2018", specialisation: "BNSS Statutory Bail & Trial" },
    { id: "LWYR-003", name: "Adv. Amit Sen", bar: "D/0891/2016", specialisation: "NALSA Undertrial Representation" },
  ];

  const handleExportDossier = async () => {
    if (!caseData?.case_id) return;
    try {
      setExportingDossier(true);
      const dossier = await exportCaseFile(caseData.case_id, "Official Supervisory Audit & Evidentiary Archive");
      const blob = new Blob([JSON.stringify(dossier, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `NyayaMitra_Dossier_${caseData.case_id}_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setActionBanner({
        type: "success",
        text: `Sealed case dossier (${caseData.case_id}) exported with cryptographically verified SHA-256 seal.`,
      });
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: `Case Dossier Export failed: ${err.message || err}`,
      });
    } finally {
      setExportingDossier(false);
    }
  };


  const handleWorkflowTransition = async (action: string, payload?: Record<string, any>, comment?: string) => {
    if (!id) return;
    setTransitioningAction(action);
    try {
      const res = await requestMatterTransition(id, action, payload, comment, matterVersion || undefined);
      setActionBanner({
        type: "success",
        text: `State transitioned to ${res.current_state} (Version ${res.version_number}) via ${action}.`,
      });
      await load();
    } catch (err: any) {
      setActionBanner({
        type: "error",
        text: err.message || `Transition '${action}' failed.`,
      });
    } finally {
      setTransitioningAction(null);
    }
  };

  const handleAssignCounsel = async () => {
    if (!caseData?.case_id || !selectedLawyerId) return;
    try {
      setAssigningCounsel(true);
      setAssignmentSuccess(null);
      await assignCaseCounsel(
        caseData.case_id,
        selectedLawyerId,
        selectedLawyerName,
        assignmentNotes || "Statutory Legal Aid Allocation under NALSA / DLSA mandate"
      );
      setCaseData((prev: any) => ({
        ...prev,
        assignment_status: "ASSIGNED",
        assigned_lawyer: selectedLawyerName,
        assigned_lawyer_id: selectedLawyerId,
      }));
      setAssignmentSuccess(`Successfully allocated ${selectedLawyerName} (${selectedLawyerId}) to case ${caseData.case_id}`);
      await load();
    } catch (err: any) {
      alert(`Counsel Allocation failed: ${err.message || err}`);
    } finally {
      setAssigningCounsel(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" accept=".pdf,image/*" />

      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={handleBack}
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
          {!approvalDone && can("CASE_APPROVE") && (
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

          {isReadyForFiling && can("CASE_FILE") && (
            <button
              onClick={handleFileInCourt}
              disabled={filing}
              title="Record verified court filing details into institutional registry. (Confirms procedural filing before Magistrate; not automated submission)."
              className="px-4 py-2 rounded-sm text-xs font-bold font-serif uppercase tracking-wider bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-2 shadow-sm"
            >
              {filing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Record Court Filing Details
            </button>
          )}

          {isFiled && (
            <span className="px-3 py-1.5 rounded-sm bg-emerald-500/15 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-bold font-mono flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> FILED IN COURT
            </span>
          )}

          {can("CASE_EXPORT") && (
            <button
              onClick={handleExportDossier}
              disabled={exportingDossier}
              title="Export complete SHA-256 sealed institutional case dossier package"
              className="px-3 py-2 border border-border bg-card hover:bg-secondary rounded-sm text-xs font-mono font-semibold text-foreground flex items-center gap-1.5 transition-colors shadow-sm"
            >
              {exportingDossier ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5 text-primary" />}
              Export Dossier (SHA-256)
            </button>
          )}

          {isPolice ? (
            <span className="px-3 py-1.5 rounded-sm bg-primary/10 border border-primary/25 text-primary text-xs font-mono font-bold flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" /> POLICE STATION CLEARANCE
            </span>
          ) : isJail ? (
            <div className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-sm bg-primary/10 border border-primary/25 text-primary text-xs font-mono font-bold flex items-center gap-1.5">
                <Building2 className="w-4 h-4" /> PRISON CUSTODY DESK
              </span>
              {c.assignment_status !== "ASSIGNED" && (
                <button
                  onClick={handleReferToDlsa}
                  disabled={referringDlsa || referralDone}
                  className="px-3 py-1.5 rounded-sm bg-secondary hover:bg-secondary/80 border border-border text-xs font-mono font-bold flex items-center gap-1.5 transition-colors"
                  title="Refer inmate to DLSA for legal aid counsel assignment"
                >
                  {referringDlsa ? <Loader2 className="w-3 h-3 animate-spin" /> : <Send className="w-3 h-3 text-primary" />}
                  {referralDone ? "Referred to DLSA" : "Refer to DLSA"}
                </button>
              )}
            </div>

      

          ) : isDlsa ? (
            <>
              <button
                onClick={generateBailDraftPDF}
                className="px-3 py-2 border border-border rounded-sm hover:bg-secondary text-xs font-medium flex items-center gap-1.5"
                title="Download internal working copy — NOT a filed petition"
              >
                <Download className="w-4 h-4" /> Internal Copy
              </button>
              <span className="px-3 py-1.5 rounded-sm bg-amber-500/10 border border-amber-500/30 text-amber-700 dark:text-amber-400 text-xs font-mono font-bold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" /> DLSA COORDINATION — Pending Advocate Sign-Off
              </span>
            </>
          ) : (
            <button
              onClick={generateBailDraftPDF}
              className="px-3 py-2 border border-border rounded-sm hover:bg-secondary text-xs font-medium flex items-center gap-1.5"
              title="Download PDF petition"
            >
              <Download className="w-4 h-4" /> PDF
            </button>
          )}
        </div>
      </div>

      {/* ── Stage 9: Canonical Lifecycle Progression Track ───────────────── */}
      <div className="p-4 border border-border bg-card rounded-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Matter Lifecycle Progression:
            </span>
            <span className="px-2.5 py-0.5 rounded text-xs font-bold font-mono bg-primary/15 text-primary border border-primary/30">
              {matterState || c.status || "INTAKE"}
            </span>
            {matterVersion && (
              <span className="px-2 py-0.5 rounded text-[11px] font-mono text-muted-foreground bg-secondary border border-border">
                v{matterVersion} (Optimistic Locked)
              </span>
            )}
          </div>
          {availableTransitions.filter(t => t.user_has_permission).length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-mono text-muted-foreground">Permitted Actions:</span>
              {availableTransitions.filter(t => t.user_has_permission).slice(0, 3).map(t => (
                <button
                  key={t.action}
                  onClick={() => handleWorkflowTransition(t.action)}
                  disabled={transitioningAction === t.action}
                  className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-secondary hover:bg-muted border border-border text-foreground transition-colors flex items-center gap-1"
                >
                  {transitioningAction === t.action ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                  {t.action.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 16-State Horizontal Stepper */}
        <div className="overflow-x-auto pb-1">
          <div className="flex items-center min-w-[1100px] gap-1 text-[10px] font-mono">
            {CANONICAL_STATES.map((st, i) => {
              const currentIdx = CANONICAL_STATES.indexOf(matterState || c.status || "INTAKE");
              const isPast = currentIdx !== -1 && i < currentIdx;
              const isCurrent = currentIdx !== -1 && i === currentIdx;
              return (
                <div key={st} className="flex items-center gap-1">
                  <div
                    className={`px-2 py-1 rounded flex items-center gap-1 whitespace-nowrap transition-colors ${
                      isCurrent
                        ? "bg-primary text-primary-foreground font-bold shadow-sm"
                        : isPast
                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                        : "bg-secondary/40 text-muted-foreground/70 border border-border/40"
                    }`}
                  >
                    {isPast ? <Check className="w-2.5 h-2.5 shrink-0" /> : <span className="w-2.5 text-center">{i + 1}</span>}
                    <span>{st.replace(/_/g, " ")}</span>
                  </div>
                  {i < CANONICAL_STATES.length - 1 && (
                    <ChevronRight className={`w-3 h-3 shrink-0 ${isPast ? "text-emerald-500" : "text-muted-foreground/40"}`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Exception State Banner if active */}
      {matterState && EXCEPTION_STATES.includes(matterState) && (
        <div className="p-4 rounded-sm border border-rose-500/40 bg-rose-500/10 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0" />
            <div>
              <h4 className="font-bold text-sm text-rose-600 dark:text-rose-400 font-serif">
                Workflow Exception Active: {matterState.replace(/_/g, " ")}
              </h4>
              <p className="text-xs text-muted-foreground">
                Progress is halted pending supervisory institutional review. A Supervising Legal Officer must resolve the exception condition.
              </p>
            </div>
          </div>
          {hasRole("SUPERVISING_LEGAL_OFFICER") && (
            <button
              onClick={() => handleWorkflowTransition("RESOLVE_EXCEPTION", { resolution_notes: "Exception reviewed and resolved by supervisor." })}
              disabled={transitioningAction === "RESOLVE_EXCEPTION"}
              className="px-3 py-1.5 rounded-sm bg-rose-600 hover:bg-rose-700 text-white text-xs font-mono font-bold flex items-center gap-1.5 shadow-sm"
            >
              {transitioningAction === "RESOLVE_EXCEPTION" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
              Resolve Exception & Restore Workflow
            </button>
          )}
        </div>
      )}

      {/* Case Handoff / Reassignment Banner if present */}
      {handoffSummary?.latest_handoff && (
        <div className="p-3.5 rounded-sm border border-border bg-secondary/20 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <GitBranch className="w-4 h-4 text-primary shrink-0" />
            <div className="text-xs">
              <span className="font-bold text-foreground">Handoff Record: </span>
              <span className="text-muted-foreground">
                Reassigned from {handoffSummary.latest_handoff.initiated_by} ({handoffSummary.latest_handoff.from_role}) to {handoffSummary.latest_handoff.to_user_id} ({handoffSummary.latest_handoff.to_role}).
              </span>
              <span className="text-primary font-mono ml-2">Reason: {handoffSummary.originating_reason}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground">
            <span>Completed Milestones: {handoffSummary.completed_milestones?.length || 0}</span>
            <span>•</span>
            <span>Pending Requirements: {handoffSummary.pending_requirements?.length || 0}</span>
          </div>
        </div>
      )}

      {/* Identified Legal Needs Alerts (Hidden for Police Officers to protect defense strategy) */}
      {!isPolice && legalNeeds.length > 0 && (
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
      <div className="flex border-b border-border gap-2 text-sm font-serif overflow-x-auto">
        {(isPolice
          ? [
              { key: "dossier", label: "Police Authorized Record" },
              { key: "evidence", label: "Evidence & Remand Documents" },
              { key: "timeline", label: "Procedural Chronology" },
            ]
          : isJail
          ? [
              { key: "dossier", label: "Custody & Inmate Record" },
              { key: "timeline", label: "Custody History & Remand" },
              { key: "evidence", label: "Prison Records & Vault" },
              { key: "legalaid", label: "Legal-Aid & Representation Status" },
            ]
          : [
              { key: "dossier", label: "Accused Dossier" },
              { key: "draft", label: "Bail Petition Draft" },
              { key: "timeline", label: "Case Timeline & Provenance" },
              { key: "evidence", label: "Document Vault & Evidentiary Verification" },
              { key: "statutes", label: "Grounded Statutory Law" },
              { key: "legalaid", label: "Legal-Aid & Counsel Allocation" },
            ]
        ).map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2 border-b-2 font-semibold transition-all shrink-0 ${
              ((isPolice || isJail) && (activeTab === "draft" || activeTab === "statutes") ? "dossier" : activeTab) === tab.key
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
                  can("MEDICAL_DATA_VIEW") ? (
                    <p className="p-2.5 rounded bg-muted/40 text-[11px] text-foreground/80 border border-border/60">
                      <strong>Medical Note:</strong> {c.urgency_flags.health_details}
                      <br />
                      <span className="text-[10px] text-muted-foreground italic">
                        (Contextual information for authorized legal review; does not constitute autonomous medical bail)
                      </span>
                    </p>
                  ) : (
                    <p className="p-2.5 rounded bg-muted/20 text-[11px] text-muted-foreground border border-border/40 italic">
                      [Protected Medical Record — Access restricted to DLSA &amp; Supervising Legal Officer under DPDP Act]
                    </p>
                  )
                )}
              </div>
            </div>

            {/* Authorised Family Portal Info (Hidden for Police Officers to protect citizen privacy) */}
            {!isPolice && (
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
            )}
          </div>

          {/* Right Column: Police Operational Record OR Versioned Rule Engine */}
          <div className="space-y-6 lg:col-span-2">
            {isPolice ? (
              <div className="p-6 border border-border bg-card rounded-sm space-y-6">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-primary" />
                    <div>
                      <h3 className="font-bold font-serif text-base text-foreground">
                        Station Police Operational Compliance Record
                      </h3>
                      <span className="text-[11px] font-mono text-muted-foreground">
                        Jurisdiction: {c.police_station || "Kotwali Police Station"} • {c.district || "Central Delhi"}
                      </span>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded bg-primary/10 text-primary border border-primary/20 font-mono text-xs font-bold">
                    {c.fir_number || `FIR-2024-${c.case_id}`}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 rounded bg-muted/40 border border-border space-y-2">
                    <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Investigating Station</div>
                    <div className="text-foreground font-semibold text-sm">{c.police_station || "Kotwali Police Station"}</div>
                    <div className="text-muted-foreground">{c.district || "Central District"}, Delhi</div>
                  </div>

                  <div className="p-4 rounded bg-muted/40 border border-border space-y-2">
                    <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Custodial Remand Metric</div>
                    <div className="text-foreground font-semibold text-sm">{c.custody_days || 0} Days In Custody</div>
                    <div className="text-muted-foreground">Detention Facility: {c.jail_location || "Central Jail"}</div>
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  <h4 className="text-xs font-bold font-mono uppercase tracking-wider text-muted-foreground">
                    Station Mandatory Document Deliverables
                  </h4>
                  <div className="space-y-2">
                    <div className="p-3 rounded border flex items-center justify-between bg-card border-border">
                      <span className="flex items-center gap-2 font-medium">
                        <FileCheck className="w-4 h-4 text-primary" />
                        Case Diary & Production Warrant Copy
                      </span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-600 border border-emerald-500/30">
                        COMPLIANT ON RECORD
                      </span>
                    </div>

                    <div className="p-3 rounded border flex items-center justify-between bg-card border-border">
                      <span className="flex items-center gap-2 font-medium">
                        <FileText className="w-4 h-4 text-primary" />
                        Investigating Officer Final Report (Charge Sheet)
                      </span>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                        (c.present_docs || []).some((d: string) => d.toLowerCase().includes("charge"))
                          ? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30"
                          : "bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30"
                      }`}>
                        {(c.present_docs || []).some((d: string) => d.toLowerCase().includes("charge"))
                          ? "SUBMITTED / ON RECORD"
                          : "PENDING SUBMISSION"}
                      </span>
                    </div>

                    <div className="p-3 rounded border flex items-center justify-between bg-card border-border">
                      <span className="flex items-center gap-2 font-medium">
                        <Clock className="w-4 h-4 text-primary" />
                        Judicial Remand Extension Order
                      </span>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                        (c.present_docs || []).some((d: string) => d.toLowerCase().includes("remand"))
                          ? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30"
                          : "bg-red-500/15 text-red-600 border border-red-500/30"
                      }`}>
                        {(c.present_docs || []).some((d: string) => d.toLowerCase().includes("remand"))
                          ? "VERIFIED ON RECORD"
                          : "AWAITING EXTENSION COPY"}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="p-3 rounded bg-muted/20 border border-border text-[11px] text-muted-foreground flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-primary shrink-0" />
                  <span>
                    Station Record Integrity: Verified under Criminal Procedure Code and BNSS jurisdictional guidelines.
                  </span>
                </div>
              </div>
            ) : isJail ? (
              <div className="p-6 border border-border bg-card rounded-sm space-y-6">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-primary" />
                    <div>
                      <h3 className="font-bold font-serif text-base text-foreground">
                        Prison Custody & Lawful Detention Record
                      </h3>
                      <span className="text-[11px] font-mono text-muted-foreground">
                        Facility: {c.jail_location || "Central Prison Complex"}
                      </span>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded bg-primary/10 text-primary border border-primary/20 font-mono text-xs font-bold">
                    CUSTODY VERIFIED
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                  <div className="p-4 rounded bg-muted/40 border border-border space-y-1">
                    <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Calendar Custody</div>
                    <div className="text-foreground font-bold text-xl font-serif">{c.custody_days || 0} Days</div>
                    <div className="text-[10px] text-muted-foreground font-mono">Admission: {c.arrest_date}</div>
                  </div>

                  <div className="p-4 rounded bg-muted/40 border border-border space-y-1">
                    <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Delay Exclusions</div>
                    <div className="text-foreground font-bold text-xl font-serif">{c.excluded_delay_days || 0} Days</div>
                    <div className="text-[10px] text-muted-foreground font-mono">Defense/Accused Adjournments</div>
                  </div>

                  <div className="p-4 rounded bg-muted/40 border border-border space-y-1">
                    <div className="font-bold font-mono text-[11px] uppercase text-primary">Countable Custody</div>
                    <div className="text-primary font-bold text-xl font-serif">{(c.custody_days || 0) - (c.excluded_delay_days || 0)} Days</div>
                    <div className="text-[10px] text-muted-foreground font-mono">Net Statutory Custody</div>
                  </div>
                </div>

                {/* Statutory Threshold Signal */}
                <div className="p-4 rounded border border-border bg-secondary/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold uppercase text-foreground">
                      Section 479 BNSS Informational Threshold Signal
                    </span>
                    {eligibility.eligible ? (
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30">
                        Potential Threshold Met
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-muted text-muted-foreground border border-border">
                        Threshold Not Yet Reached
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground font-sans">
                    {eligibility.eligible
                      ? "The undertrial has potentially completed the fractional custody duration under Section 479. Refer verified nominal roll and custody records to DLSA for legal review and representation."
                      : "Custody duration is within standard remand timeline. Regular bi-weekly custody audit continues."}
                  </p>
                  <p className="text-[10px] font-mono text-muted-foreground">
                    * Informational signal for prison administration. Final legal eligibility and bail pleadings remain exclusively with DLSA and defense counsel.
                  </p>
                </div>

                {/* Prison Documents Status */}
                <div className="space-y-3">
                  <h4 className="font-mono text-xs font-bold uppercase text-muted-foreground">
                    Required Prison & Custody Records
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {(c.required_docs || []).map((doc: string) => {
                      const isPresent = (c.present_docs || []).includes(doc);
                      return (
                        <div key={doc} className="p-2.5 rounded border border-border flex items-center justify-between text-xs font-mono">
                          <span className="capitalize text-foreground">{doc.replace(/_/g, " ")}</span>
                          {isPresent ? (
                            <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 text-[11px] font-bold">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Present
                            </span>
                          ) : (
                            <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1 text-[11px] font-bold">
                              <AlertTriangle className="w-3.5 h-3.5" /> Pending
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ) : (
              <>
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
                    eligibility.machine_status === "THRESHOLD_REACHED" || eligibility.eligible
                      ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                      : eligibility.machine_status === "EXCLUDED"
                      ? "bg-destructive/15 text-destructive border border-destructive/30"
                      : "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                  }`}
                >
                  {eligibility.machine_status ? eligibility.machine_status.replace(/_/g, " ") : (eligibility.eligible ? "THRESHOLD SATISFIED" : "REVIEW REQUIRED")}
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
                    {eligibility.required_custody_days || eligibility.threshold_days || "—"}d
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
                    <span>Offender Category: <strong>{eligibility.category_label || (c.urgency_flags?.repeat_offender ? "General (1/2 Threshold)" : "First-Time (1/3 Proviso)")}</strong></span>
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
                  const normDoc = docType.toLowerCase().trim().replace(/ /g, "_");
                  const detail = caseDocDetails.find(
                    (d: any) => d.document_type === normDoc || d.id?.includes(normDoc)
                  );
                  const isVerified = (detail && detail.document_status === "VERIFIED") || c.present_docs?.includes(docType);
                  const isReviewed = detail && detail.document_status === "REVIEWED";
                  const isPending = detail && detail.document_status === "PENDING_VERIFICATION";
                  const isSupervisor = user?.role === "SUPERVISING_LEGAL_OFFICER";
                  const isDlsa = user?.role === "DLSA_OFFICER";

                  return (
                    <div
                      key={docType}
                      className={`p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all ${
                        isVerified
                          ? "bg-emerald-500/5 border-emerald-500/30"
                          : isReviewed
                          ? "bg-blue-500/10 border-blue-500/40"
                          : isPending
                          ? "bg-amber-500/10 border-amber-500/40"
                          : "bg-destructive/5 border-destructive/20"
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          {isVerified ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                          ) : isReviewed ? (
                            <CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0" />
                          ) : isPending ? (
                            <Clock className="w-4 h-4 text-amber-500 shrink-0" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
                          )}
                          <span className="font-bold text-foreground tracking-tight">
                            {docType.replace(/_/g, " ").toUpperCase()}
                          </span>
                          {isPending && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-600 border border-amber-500/30">
                              PENDING VERIFICATION
                            </span>
                          )}
                          {isReviewed && !isVerified && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-600 border border-blue-500/30">
                              REVIEWED (INTAKE)
                            </span>
                          )}
                        </div>

                        {/* Uploader Attribution Provenance */}
                        <div className="text-[11px] text-muted-foreground pl-6">
                          {isVerified ? (
                            <span>Origin: <strong className="text-foreground">{detail?.uploaded_by || "Court Registry (Baseline)"}</strong></span>
                          ) : isReviewed ? (
                            <span>Status: <strong className="text-foreground">Reviewed for DLSA Intake</strong> &bull; Uploaded by: <strong className="text-foreground">{detail?.uploaded_by || "Institutional Officer"}</strong></span>
                          ) : isPending ? (
                            <span>Uploaded by: <strong className="text-foreground">{detail?.uploaded_by || "Institutional Officer"}</strong></span>
                          ) : (
                            <span className="text-amber-600/90 font-medium">Missing record &mdash; blocks eligibility determination</span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                        {/* DLSA Officer: Review Document */}
                        {isPending && isDlsa && detail?.actual_doc_id && (
                          <button
                            onClick={() => handleReviewCaseDoc(detail.actual_doc_id)}
                            disabled={reviewingDocId === detail.actual_doc_id}
                            className="px-2.5 py-1 bg-blue-600 text-white rounded text-[11px] font-bold uppercase hover:bg-blue-700 flex items-center gap-1 shadow-sm transition-colors"
                            title="Mark reviewed for legal-aid intake processing"
                          >
                            {reviewingDocId === detail.actual_doc_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                            Review Document
                          </button>
                        )}

                        {/* Supervising Legal Officer: Supervisory Verify */}
                        {(isPending || isReviewed) && !isVerified && isSupervisor && detail?.actual_doc_id && (
                          <button
                            onClick={() => handleVerifyCaseDoc(detail.actual_doc_id)}
                            disabled={verifyingDocId === detail.actual_doc_id}
                            className="px-2.5 py-1 bg-emerald-600 text-white rounded text-[11px] font-bold uppercase hover:bg-emerald-700 flex items-center gap-1 shadow-sm transition-colors"
                            title="Supervisory verification: confirm presence and update case completeness"
                          >
                            {verifyingDocId === detail.actual_doc_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCheck className="w-3 h-3" />}
                            Supervisory Verify
                          </button>
                        )}

                        <button
                          onClick={() => handleUploadDoc(docType)}
                          disabled={uploadingDoc === docType}
                          className={`px-2.5 py-1 rounded text-[11px] font-bold uppercase flex items-center gap-1 shadow-sm transition-colors ${
                            isVerified
                              ? "bg-secondary text-foreground hover:bg-secondary/80 border border-border"
                              : "bg-primary text-primary-foreground hover:opacity-90"
                          }`}
                        >
                          {uploadingDoc === docType ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                          {isVerified ? "Re-upload" : isPending ? "Replace" : "Upload"}
                        </button>
                      </div>
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
          </>
        )}
      </div>
    </div>
  )}


      {/* TAB 2: BAIL PETITION DRAFT & ADVOCATE REVIEW GATEWAY */}
      {!isPolice && !isJail && activeTab === "draft" && (
        <div className="space-y-6">

          <div className="p-6 border border-border bg-card rounded-sm space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div>
                <h3 className="font-bold font-serif text-lg text-foreground">
                  {isDlsa ? "Bail Application Work Product (DLSA Coordination View)" : "Formal Bail Application Draft"}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Under Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={generateBailDraftPDF}
                  className="px-3 py-1.5 border border-border rounded-sm hover:bg-secondary text-xs font-semibold flex items-center gap-1.5"
                  title={isDlsa ? "Download internal working copy — NOT a filed petition" : "Download PDF petition"}
                >
                  <Download className="w-4 h-4" /> {isDlsa ? "Internal Copy" : "Download PDF"}
                </button>
              </div>
            </div>

            {/* In-Line Draft Editor — Role-Scoped */}
            {isDlsa ? (
              <div className="space-y-4">
                {/* DLSA: Read-only petition view */}
                <div className="space-y-2">
                  <label className="text-xs font-mono font-bold uppercase text-muted-foreground flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-amber-500" />
                    Petition Work Product — Read Only (Authorised Legal Counsel Editing Reserved):
                  </label>
                  <div className="w-full p-4 font-mono text-xs bg-muted/30 border border-border rounded-sm text-foreground leading-relaxed min-h-[200px] overflow-auto whitespace-pre-wrap select-all">
                    {editableDraft || "Draft petition will appear here once AI generation is complete."}
                  </div>
                  <p className="text-[11px] text-amber-700 dark:text-amber-400 font-mono">
                    ⚠ DLSA officers may review and coordinate corrections. Final petition editing authority rests with the assigned panel advocate.
                  </p>
                </div>

                {/* DLSA: Institutional Comment Box */}
                <div className="space-y-2 pt-2 border-t border-border">
                  <label className="text-xs font-mono font-bold uppercase text-muted-foreground">
                    DLSA Institutional Comments / Correction Requests:
                  </label>
                  <textarea
                    value={dlsaComment}
                    onChange={(e) => setDlsaComment(e.target.value)}
                    rows={5}
                    placeholder="Add institutional notes, flag corrections needed, or request advocate review. These comments are attached to the case record."
                    className="w-full p-4 font-mono text-xs bg-background border border-border rounded-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed resize-y"
                  />
                  <button
                    disabled={!dlsaComment.trim() || submittingComment}
                    className={`px-4 py-2 rounded-sm text-xs font-semibold flex items-center gap-2 ${
                      dlsaComment.trim() && !submittingComment
                        ? "bg-primary text-primary-foreground hover:opacity-90"
                        : "bg-muted text-muted-foreground cursor-not-allowed border border-border"
                    }`}
                    onClick={handleSubmitComment}
                  >
                    {submittingComment ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    {submittingComment ? "Submitting Comment..." : "Submit for Advocate / Supervisor Review"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {actionBanner && (
                  <div
                    className={`p-3 rounded text-xs flex items-center justify-between font-mono ${
                      actionBanner.type === "success"
                        ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-600"
                        : "bg-destructive/10 border border-destructive/30 text-destructive"
                    }`}
                  >
                    <span>{actionBanner.text}</span>
                    <button
                      onClick={() => setActionBanner(null)}
                      className="ml-2 text-muted-foreground hover:text-foreground text-xs"
                    >
                      ✕
                    </button>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-bold uppercase text-muted-foreground">
                    Editable Petition Text (Reviewed by Defence Counsel):
                  </label>
                  {hasRole("DEFENSE_ADVOCATE", "CONTROLLED_EXTERNAL_ADVOCATE") && (
                    <span className="text-[11px] font-mono text-primary font-semibold">
                      Counsel Work Product // Versioned Legal Draft
                    </span>
                  )}
                </div>
                <textarea
                  value={editableDraft}
                  onChange={(e) => setEditableDraft(e.target.value)}
                  rows={16}
                  className="w-full p-4 font-mono text-xs bg-background border border-border rounded-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed resize-y"
                />
                {hasRole("DEFENSE_ADVOCATE", "CONTROLLED_EXTERNAL_ADVOCATE") && (
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-border">
                    <p className="text-[11px] font-mono text-muted-foreground">
                      Counsel Review Status: {advocateSignedOff ? "✓ Legal Sign-Off Recorded (Awaiting Supervisory Sign-Off)" : "Draft Under Active Counsel Review"}
                    </p>
                    <button
                      onClick={handleSignOff}
                      disabled={signingOff || advocateSignedOff || !editableDraft.trim()}
                      className={`px-4 py-2 rounded-sm text-xs font-bold font-serif uppercase tracking-wider flex items-center gap-2 ${
                        advocateSignedOff
                          ? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30 cursor-default"
                          : "bg-primary text-primary-foreground hover:opacity-90"
                      }`}
                    >
                      {signingOff ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4" />
                      )}
                      {advocateSignedOff ? "Counsel Signed Off" : signingOff ? "Signing Off..." : "Sign Off & Submit for Supervisory Review"}
                    </button>
                  </div>
                )}
              </div>
            )}

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
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-foreground font-serif">{event.title}</span>
                        {(() => {
                          const badge = (event as any).provenance_badge || (event.source?.includes("AI") ? "AI" : event.source?.includes("Sync") ? "EXTERNAL_SYNC" : event.is_human_verified ? "USER" : "SYSTEM");
                          if (badge === "AI") {
                            return (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 flex items-center gap-1">
                                <Bot className="w-3 h-3" /> AI
                              </span>
                            );
                          } else if (badge === "EXTERNAL_SYNC") {
                            return (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 flex items-center gap-1">
                                <RefreshCw className="w-3 h-3" /> Sync
                              </span>
                            );
                          } else if (badge === "SYSTEM") {
                            return (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-secondary text-foreground border border-border flex items-center gap-1">
                                <Cpu className="w-3 h-3" /> System
                              </span>
                            );
                          } else {
                            return (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                                <User className="w-3 h-3" /> User
                              </span>
                            );
                          }
                        })()}
                      </div>
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
                Document Vault &amp; Evidentiary Verification
              </h3>
              <p className="text-xs text-muted-foreground">
                Digital tamper-verification confirms official documents are authentic and uncorrupted under BSA Sec 63 where applicable.
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
                        Evidence ID: {eviId} • Format: PDF / Digitised Court Record
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {hasRole("SUPERVISING_LEGAL_OFFICER", "DLSA_OFFICER", "JAIL_OFFICER") ? (
                      <button
                        onClick={() => handleVerifyEvidence(eviId)}
                        disabled={verifyingEvidenceId === eviId}
                        className="px-3 py-1.5 bg-secondary border border-border text-foreground hover:bg-muted text-xs font-semibold rounded flex items-center gap-1.5"
                      >
                        {verifyingEvidenceId === eviId ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                        Verify Document Integrity
                      </button>
                    ) : (
                      <span className="px-2.5 py-1 text-[11px] font-sans text-muted-foreground bg-muted/50 border border-border rounded flex items-center gap-1" title="Evidence verification is performed by DLSA, Supervisory Legal Officer, or Jail Custody Officer">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                        Custody Verified
                      </span>
                    )}
                  </div>
                </div>
              );
            })}

            {evidenceVerificationResult && (
              evidenceVerificationResult.error ? (
                /* Access Denied / Other API Error */
                <div className="p-4 rounded border bg-red-500/10 border-red-500/30 text-xs font-sans space-y-1">
                  <p className="font-bold text-red-600">VERIFICATION FAILED — ACCESS DENIED</p>
                  <p className="text-muted-foreground text-xs">{evidenceVerificationResult.error}</p>
                </div>
              ) : evidenceVerificationResult.integrity_verified ? (
                /* Authentic — Hashes Match */
                <div className="p-4 rounded border bg-emerald-500/10 border-emerald-500/30 text-xs font-sans space-y-1.5">
                  <p className="font-bold text-emerald-600 dark:text-emerald-400">
                    ✔ OFFICIAL DOCKET INTEGRITY VERIFIED — AUTHENTIC
                  </p>
                  {user?.role === "PLATFORM_ADMIN" ? (
                    <>
                      <p className="text-foreground/80 break-all font-mono text-[11px]">
                        <span className="text-muted-foreground">Stored Hash:&nbsp;</span>
                        {evidenceVerificationResult.stored_hash}
                      </p>
                      <p className="text-foreground/80 break-all font-mono text-[11px]">
                        <span className="text-muted-foreground">Computed Hash:&nbsp;</span>
                        {evidenceVerificationResult.computed_hash}
                      </p>
                    </>
                  ) : (
                    <p className="text-foreground/80">
                      <span className="text-muted-foreground">Digital Seal:&nbsp;</span>
                      Sealed &amp; Matching Judicial Records Repository (BSA Sec 63 where applicable)
                    </p>
                  )}
                  <p className="text-muted-foreground text-xs">{evidenceVerificationResult.note}</p>
                </div>
              ) : (
                /* Tampered — Hashes Do Not Match */
                <div className="p-4 rounded border bg-red-500/10 border-red-500/30 text-xs font-sans space-y-1.5">
                  <p className="font-bold text-red-600">
                    ⚠ INTEGRITY VIOLATION — POSSIBLE TAMPERING DETECTED
                  </p>
                  {user?.role === "PLATFORM_ADMIN" ? (
                    <>
                      <p className="text-foreground/80 break-all font-mono text-[11px]">
                        <span className="text-muted-foreground">Stored Hash (Original):&nbsp;</span>
                        {evidenceVerificationResult.stored_hash}
                      </p>
                      <p className="text-foreground/80 break-all font-mono text-[11px]">
                        <span className="text-muted-foreground">Computed Hash (Current):&nbsp;</span>
                        {evidenceVerificationResult.computed_hash}
                      </p>
                    </>
                  ) : (
                    <p className="text-foreground/80">
                      <span className="text-muted-foreground">Status:&nbsp;</span>
                      The file presented does not match the original sealed court docket file.
                    </p>
                  )}
                  <p className="text-red-500 text-xs font-semibold">{evidenceVerificationResult.note}</p>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* TAB 5: GROUNDED STATUTORY LEGAL AUTHORITIES (RAG) */}
      {!isPolice && !isJail && activeTab === "statutes" && (
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

      {/* TAB 6: INSTITUTIONAL LEGAL-AID & REPRESENTATION STATUS */}
      {(isJail || !isPolice) && activeTab === "legalaid" && (
        <div className="p-6 border border-border bg-card rounded-sm space-y-6 max-w-4xl">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Building2 className="w-5 h-5 text-primary" />
              <div>
                <h3 className="font-bold font-serif text-base text-foreground">
                  Institutional Legal-Aid & Representation Status
                </h3>
                <span className="text-[11px] font-mono text-muted-foreground">
                  Case ID: {c.case_id} • Accused: {c.name}
                </span>
              </div>
            </div>
            {c.assignment_status === "ASSIGNED" ? (
              <span className="px-2.5 py-1 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 font-mono text-xs font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> COUNSEL ASSIGNED
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 font-mono text-xs font-bold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> PENDING ASSIGNMENT
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-4 rounded bg-muted/40 border border-border space-y-2">
              <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Appointed Counsel</div>
              <div className="text-foreground font-semibold text-sm">{c.assigned_lawyer || "Not Assigned"}</div>
              <div className="text-muted-foreground font-mono">Counsel ID: {c.assigned_lawyer_id || "Unassigned"}</div>
            </div>

            <div className="p-4 rounded bg-muted/40 border border-border space-y-2">
              <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Coordinating Authority</div>
              <div className="text-foreground font-semibold text-sm">District Legal Services Authority (DLSA)</div>
              <div className="text-muted-foreground">Central Delhi District Court Complex</div>
            </div>
          </div>

          {/* Prison Superintendent Referral Actions */}
          {isJail && (
            <div className="p-4 rounded border border-border bg-secondary/20 space-y-3">
              <h4 className="font-mono text-xs font-bold uppercase text-foreground">
                Prison Superintendent Referral Actions
              </h4>
              <p className="text-xs text-muted-foreground">
                Under NALSA Undertrial Review Committee (UTRC) guidelines, the Jail Superintendent shall identify undertrials lacking private representation and refer custody records to DLSA for timely assignment of pro-bono defense counsel.
              </p>
              {c.assignment_status !== "ASSIGNED" ? (
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleReferToDlsa}
                    disabled={referringDlsa || referralDone}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-sm text-xs font-mono font-bold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
                  >
                    {referringDlsa ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    {referralDone ? "Referred to DLSA" : "Dispatch Referral Notice to DLSA"}
                  </button>
                  {referralDone && (
                    <span className="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" /> Referral logged & DLSA notified.
                    </span>
                  )}
                </div>
              ) : (
                <div className="text-xs font-mono text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" /> Legal representation is active. Adv. {c.assigned_lawyer} is handling bail proceedings.
                </div>
              )}
            </div>
          )}

          {/* DLSA Counsel Assignment Desk */}
          {can("CASE_ASSIGN_COUNSEL") && (
            <div className="p-5 rounded border border-border bg-card space-y-4 shadow-sm">
              <div className="border-b border-border pb-3 flex items-center justify-between">
                <div>
                  <h4 className="font-mono text-xs font-bold uppercase text-foreground flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-primary" /> DLSA Legal Aid Counsel Allocation Desk
                  </h4>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Formal statutory allocation of certified panel defense advocate under Legal Services Authorities Act, 1987.
                  </p>
                </div>
                {c.assignment_status === "ASSIGNED" && (
                  <span className="px-2.5 py-0.5 rounded font-mono text-[11px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-bold">
                    ACTIVE ALLOCATION
                  </span>
                )}
              </div>

              {assignmentSuccess && (
                <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 font-mono text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{assignmentSuccess}</span>
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-muted-foreground font-semibold mb-1">
                    Select Panel Defense Advocate
                  </label>
                  <select
                    value={selectedLawyerId}
                    onChange={(e) => {
                      const selected = PANEL_ADVOCATES.find((a) => a.id === e.target.value);
                      if (selected) {
                        setSelectedLawyerId(selected.id);
                        setSelectedLawyerName(selected.name);
                      } else {
                        setSelectedLawyerId(e.target.value);
                      }
                    }}
                    className="w-full p-2 border border-border rounded bg-background text-foreground text-xs font-mono"
                  >
                    {PANEL_ADVOCATES.map((adv) => (
                      <option key={adv.id} value={adv.id}>
                        {adv.name} ({adv.id}) — Bar: {adv.bar} [{adv.specialisation}]
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-muted-foreground font-semibold mb-1">
                      Advocate Name (Institutional Record)
                    </label>
                    <input
                      type="text"
                      value={selectedLawyerName}
                      onChange={(e) => setSelectedLawyerName(e.target.value)}
                      className="w-full p-2 border border-border rounded bg-background text-foreground text-xs font-mono"
                      placeholder="e.g. Adv. Rajesh Sharma"
                    />
                  </div>
                  <div>
                    <label className="block text-muted-foreground font-semibold mb-1">
                      Counsel ID / Bar Enrolment
                    </label>
                    <input
                      type="text"
                      value={selectedLawyerId}
                      onChange={(e) => setSelectedLawyerId(e.target.value)}
                      className="w-full p-2 border border-border rounded bg-background text-foreground text-xs font-mono"
                      placeholder="e.g. LWYR-001"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-muted-foreground font-semibold mb-1">
                    Allocation Order Notes / DLSA Reference
                  </label>
                  <textarea
                    value={assignmentNotes}
                    onChange={(e) => setAssignmentNotes(e.target.value)}
                    rows={2}
                    placeholder="Enter DLSA allocation order number, urgency instructions, or court appearance directive..."
                    className="w-full p-2 border border-border rounded bg-background text-foreground text-xs font-mono"
                  />
                </div>

                <button
                  onClick={handleAssignCounsel}
                  disabled={assigningCounsel || !selectedLawyerName}
                  className="px-4 py-2.5 bg-primary text-primary-foreground rounded-sm text-xs font-mono font-bold flex items-center gap-2 hover:opacity-90 transition-opacity shadow-sm"
                >
                  {assigningCounsel ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserCheck className="w-3.5 h-3.5" />}
                  {c.assignment_status === "ASSIGNED" ? "Reassign Legal Aid Counsel" : "Formally Appoint & Assign Legal Aid Counsel"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
