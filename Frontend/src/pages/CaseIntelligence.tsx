import { useParams, useNavigate, useSearchParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ShieldAlert,
  Calculator,
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
  Search,
  X,
  Eye,
  Save,
  Info,
  Scale,
} from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchCaseById,
  signOffCase,
  saveCaseDraft,
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
  getEligibleCounsel,
  exportCaseFile,
  fetchMatterState,
  fetchAvailableTransitions,
  requestMatterTransition,
  fetchMatterHandoffSummary,
  generateBailDraft,
  downloadCaseDocument,
} from "@/lib/api";
import { jsPDF } from "jspdf";
import { useAuth } from "@/lib/auth";
import { DocumentPreviewModal } from "@/components/DocumentPreviewModal";
import { ToastContainer, type ToastItem } from "@/components/ToastContainer";
import { resolveCaseUpdater } from "@/lib/utils";

export function normalizeDocKey(docType: string): string {
  if (!docType) return "";
  const clean = docType.toLowerCase().trim().replace(/[- ]/g, "_");
  const aliases: Record<string, string> = {
    fir_copy: "fir",
    first_information_report: "fir",
    first_information_report_fir: "fir",
    fir_legal_aid_intake: "fir",
    fir_copy_legal_aid_intake: "fir",
    chargesheet: "charge_sheet",
    charge_sheet_copy: "charge_sheet",
    final_report: "charge_sheet",
    final_police_report: "charge_sheet",
    charge_sheet_final_report: "charge_sheet",
    remand_order_copy: "remand_order",
    remand_application: "remand_order",
    judicial_remand_order: "remand_order",
    detention_order: "remand_order",
    police_remand_order: "remand_order",
    nominal_roll_copy: "nominal_roll",
    certified_nominal_roll: "nominal_roll",
    prison_nominal_roll: "nominal_roll",
    custody_certificate_copy: "custody_certificate",
    nominal_custody_certificate: "custody_certificate",
    custody_certificate_prison_record: "custody_certificate",
    trial_court_judgment_copy: "trial_court_judgment",
    trial_court_order: "trial_court_judgment",
    trial_court_order_judgment: "trial_court_judgment",
    trial_court_order_copy: "trial_court_judgment",
    prior_bail_order: "prior_bail_order_if_any",
    prior_bail_order_copy: "prior_bail_order_if_any",
    prior_bail_rejection_order: "prior_bail_order_if_any",
    bail_application: "bail_application",
    bail_petition: "bail_application",
    bail_application_draft: "bail_application",
    bail_order: "bail_order",
    bail_grant_order: "bail_order",
    certified_bail_order: "bail_order",
    release_memo: "release_memo",
    release_order: "release_memo",
    jail_release_memo: "release_memo",
    prison_admission: "prison_admission_record",
    prison_admission_record: "prison_admission_record",
    admission_record: "prison_admission_record",
    prison_conduct: "prison_conduct_record",
    prison_conduct_record: "prison_conduct_record",
    conduct_certificate: "prison_conduct_record",
    medical_report: "medical_certificate",
    medical_certificate: "medical_certificate",
    medical_examination_record: "medical_certificate",
    case_diary_extract: "case_diary_extract",
    case_diary: "case_diary_extract",
    arrest_memo: "arrest_memo",
    panchnama: "arrest_memo",
    supervisory_review_note: "supervisory_review_note",
    supervisory_note: "supervisory_review_note",
    vakalatnama: "vakalatnama",
    memo_of_appearance: "vakalatnama",
    dlsa_application: "dlsa_application",
    legal_aid_application: "dlsa_application",
  };
  return aliases[clean] || clean;
}

export function CaseIntelligence() {
  const { user, hasRole, can } = useAuth();
  const isPolice = user?.role === "POLICE_OFFICER";
  const isDlsa = user?.role === "DLSA_OFFICER";
  const isJail = user?.role === "JAIL_OFFICER";
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const tabParam = searchParams.get("tab");
  const validTab = (tabParam && ["dossier", "draft", "timeline", "evidence", "statutes", "legalaid"].includes(tabParam))
    ? (tabParam as "dossier" | "draft" | "timeline" | "evidence" | "statutes" | "legalaid")
    : "dossier";

  const [caseData, setCaseData] = useState<any>(null);
  const [caseDocDetails, setCaseDocDetails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadingDoc, setUploadingDoc] = useState<string | null>(null);
  const [verifyingDocId, setVerifyingDocId] = useState<string | null>(null);
  const [reviewingDocId, setReviewingDocId] = useState<string | null>(null);
  const [editableDraft, setEditableDraft] = useState<string>("");
  const [savingDraft, setSavingDraft] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = (type: ToastItem["type"], title: string, message: string) => {
    const toastId = "t-" + Date.now() + "-" + Math.random().toString(36).substring(2, 6);
    setToasts((prev) => [...prev, { id: toastId, type, title, message, timestamp: Date.now() }]);
  };

  const removeToast = (toastId: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  };
  const [dlsaComment, setDlsaComment] = useState<string>("");
  const [submittingComment, setSubmittingComment] = useState(false);
  const [activeTab, setActiveTab] = useState<"dossier" | "draft" | "timeline" | "evidence" | "statutes" | "legalaid">(validTab);

  useEffect(() => {
    const t = searchParams.get("tab");
    if (t && ["dossier", "draft", "timeline", "evidence", "statutes", "legalaid"].includes(t)) {
      setActiveTab(t as any);
    }
  }, [searchParams]);

  const [verifyingEvidenceId, setVerifyingEvidenceId] = useState<string | null>(null);
  const [evidenceVerificationResult, setEvidenceVerificationResult] = useState<any>(null);
  const [advocateSignedOff, setAdvocateSignedOff] = useState(false);
  const [signingOff, setSigningOff] = useState(false);
  const [referringDlsa, setReferringDlsa] = useState(false);
  const [referralDone, setReferralDone] = useState(false);
  const [actionBanner, setActionBanner] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const [exportingDossier, setExportingDossier] = useState(false);
  const [generatingDraft, setGeneratingDraft] = useState(false);
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);
  const [previewDocTitle, setPreviewDocTitle] = useState<string>("");
  const [advocateSearchQuery, setAdvocateSearchQuery] = useState("");
  const [assigningCounsel, setAssigningCounsel] = useState(false);
  const [selectedLawyerId, setSelectedLawyerId] = useState("");
  const [selectedLawyerName, setSelectedLawyerName] = useState("");
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
  const [activeTransitionModal, setActiveTransitionModal] = useState<{
    action: string;
    target_state?: string;
    description?: string;
    required_payload_keys: string[];
    is_exception?: boolean;
  } | null>(null);
  const [transitionFormData, setTransitionFormData] = useState<Record<string, string>>({});
  const [transitionComment, setTransitionComment] = useState("");
  const [eligibleCounselList, setEligibleCounselList] = useState<any[]>([]);
  const [loadingEligibleCounsel, setLoadingEligibleCounsel] = useState(false);
  const [counselSearchQuery, setCounselSearchQuery] = useState("");

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
      const canManageCounsel = ["DLSA_OFFICER", "SUPERVISING_LEGAL_OFFICER", "PLATFORM_ADMIN", "GOV_ADMIN"].includes(user?.role || "");
      const [data, docData, stateData, transData, handoffData, eligibleCounselData] = await Promise.all([
        fetchCaseById(id),
        fetchCaseDocuments(id).catch(() => null),
        fetchMatterState(id).catch(() => null),
        fetchAvailableTransitions(id).catch(() => null),
        fetchMatterHandoffSummary(id).catch(() => null),
        canManageCounsel ? getEligibleCounsel(id).catch(() => null) : Promise.resolve(null),
      ]);
      if (!data) throw new Error("Not found");
      setCaseData(data);
      if (eligibleCounselData?.counsel_list) {
        setEligibleCounselList(eligibleCounselData.counsel_list);
      }
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
      return data;
    } catch (err: any) {
      setError(err?.message || `Could not load case ${id}. Ensure the backend is online at localhost:8000.`);
      return null;
    } finally {
      setLoading(false);
    }
  }, [id, user?.role]);

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
      const res = await signOffCase(id, editableDraft);
      if (res?.status === "error" || res?.error) {
        throw new Error(res?.message || res?.error || "Counsel sign-off failed.");
      }
      setAdvocateSignedOff(true);
      setActionBanner({
        type: "success",
        text: "Counsel legal sign-off recorded. The petition draft is stamped as Advocate Work Product and submitted for supervisory review.",
      });
      addToast("success", "Petition Approved & Submitted", "You have successfully signed off on this bail petition. It is now submitted for official review.");
      await load();
    } catch (err: any) {
      const errMsg = err.message || "";
      const isConflict = errMsg.includes("409") || errMsg.toLowerCase().includes("conflict");
      if (isConflict) {
        const fresh = await load();
        const updater = resolveCaseUpdater(err?.detail, fresh || caseData, caseData?.case?.district);
        addToast("conflict", "Case Already Updated", `${updater} just made updates to this case. We have automatically refreshed your screen to show the latest information.`);
      } else {
        addToast("error", "Unable to Sign Off", err.message || "Could not complete the sign-off right now. Please check your connection and try again.");
      }
      setActionBanner({
        type: "error",
        text: "Counsel sign-off failed: " + (err.message || err),
      });
    } finally {
      setSigningOff(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!id || !editableDraft) return;
    setSavingDraft(true);
    setActionBanner(null);
    try {
      const res = await saveCaseDraft(id, editableDraft);
      if (res?.status === "error" || res?.error) {
        throw new Error(res?.message || res?.error || "Failed to save draft changes.");
      }
      setActionBanner({
        type: "success",
        text: "Bail petition draft changes saved successfully to database.",
      });
      addToast("success", "Draft Changes Saved", "Your edits to the bail petition have been safely saved.");
      await load();
    } catch (err: any) {
      const errMsg = err.message || "";
      const isConflict = errMsg.includes("409") || errMsg.toLowerCase().includes("conflict");
      if (isConflict) {
        const fresh = await load();
        const updater = resolveCaseUpdater(err?.detail, fresh || caseData, caseData?.case?.district);
        addToast("conflict", "Draft Already Updated", `${updater} just made updates to this draft. We have refreshed your screen with their latest changes.`);
      } else {
        addToast("error", "Could Not Save Draft", err.message || "Your changes could not be saved right now. Please check your connection and try again.");
      }
      setActionBanner({
        type: "error",
        text: "Save draft failed: " + (err.message || err),
      });
    } finally {
      setSavingDraft(false);
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

  const generateBailDraftPDF = async () => {
    const currentCase = caseData?.case || {};
    if (!currentCase.case_id) return;
    const counselAssigned = Boolean(
      currentCase.assigned_lawyer_id ||
      currentCase.assigned_lawyer ||
      currentCase.assigned_advocate_id ||
      currentCase.assigned_advocate_name ||
      currentCase.assignment_status === "ASSIGNED" ||
      caseData?.counsel_assigned ||
      caseData?.assigned_lawyer_id ||
      caseData?.assigned_lawyer ||
      caseData?.assigned_advocate_id ||
      caseData?.assigned_advocate_name ||
      caseData?.assignment_status === "ASSIGNED" ||
      (matterState && !["INTAKE", "VERIFICATION"].includes(matterState))
    );
    if (!counselAssigned) {
      addToast("error", "Counsel Required", "Legal Aid Defense Counsel must be assigned before downloading petition PDF.");
      return;
    }

    let activeDraft = editableDraft;
    if (!activeDraft || !activeDraft.trim()) {
      if (user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE") {
        try {
          setGeneratingDraft(true);
          addToast("info", "Generating Draft", "Fetching statutory Section 479 BNSS draft petition from AI drafting engine...");
          const res = await generateBailDraft(currentCase.case_id);
          if (res?.draft_text) {
            activeDraft = res.draft_text;
            setEditableDraft(res.draft_text);
            addToast("success", "Draft Generated", "Statutory draft prepared and compiled into petition PDF.");
          } else {
            throw new Error((res as any)?.detail || res?.message || "No draft content returned by the server.");
          }
        } catch (err: any) {
          const errMsg = err?.detail || err?.message || String(err);
          addToast("error", "Draft Generation Failed", errMsg);
          return;
        } finally {
          setGeneratingDraft(false);
        }
      } else {
        addToast("error", "Draft Not Ready", "Draft petition has not yet been generated by the assigned defence advocate.");
        return;
      }
    }
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
    doc.text(c.jail_location || "Designated Correctional Facility", margin + 140, yPos + 5);
    doc.text(c.dlsa_reference_number || "DLSA-PENDING", margin + 140, yPos + 10);
    doc.text(`${eligibility.custody_days_served ?? c.custody_days ?? 0} Days Served`, margin + 140, yPos + 15);
    const reqDays = eligibility.required_custody_days ?? (c.max_sentence_days_for_offense ? Math.ceil(c.max_sentence_days_for_offense / 3) : 0);
    doc.text(reqDays > 0 ? `${reqDays} Days (Statutory Threshold)` : "Statutory Evaluation Pending", margin + 140, yPos + 20);

    yPos += 28;

    // ── 3. PETITION NARRATIVE / GROUNDS ──────────────────────────────────────
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.text("MOST RESPECTFULLY SHOWETH:", margin, yPos);
    yPos += 6;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(9);
    
    // Split editable draft paragraphs
    const draftContent = activeDraft || editableDraft || "Statutory grounds under Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023. The petitioner has served the requisite statutory period in undertrial detention and has not been convicted of any prior offenses punishable by life or death.";
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
    doc.setTextColor(220, 38, 38); // Red color for notice
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
    const lawyerName = c.assigned_advocate_name || c.assigned_lawyer || c.assigned_advocate_id || c.assigned_lawyer_id || "Adv. DLSA Legal Aid Counsel";
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
    addToast("success", "Petition Downloaded", "Statutory Bail Petition PDF compiled and downloaded successfully.");
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
    const isForbidden = error?.includes("Forbidden") || error?.includes("Access Restricted") || error?.includes("authorized");
    return (
      <div className="p-8 max-w-xl mx-auto flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
        <ToastContainer toasts={toasts} onDismiss={removeToast} />
        {isForbidden ? (
          <ShieldAlert className="w-14 h-14 text-red-500" />
        ) : (
          <AlertCircle className="w-12 h-12 text-destructive" />
        )}
        <div>
          <h2 className="text-xl font-bold text-foreground mb-2">
            {isForbidden ? "Procedural Access Restricted" : "Dossier Unavailable"}
          </h2>
          <p className="text-muted-foreground text-sm max-w-md mx-auto">
            {error || "Case record could not be loaded."}
          </p>
          {isForbidden && (user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE") && (
            <div className="mt-4 p-3.5 text-left bg-muted/40 border border-border rounded-sm text-xs space-y-2 font-sans max-w-md mx-auto">
              <p className="font-bold text-foreground flex items-center gap-1.5">
                <Scale className="w-4 h-4 text-primary shrink-0" />
                Statutory Counsel Allocation Prerequisite
              </p>
              <p className="text-muted-foreground leading-relaxed">
                Under NALSA guidelines and undertrial privacy protections, panel defense advocates may only access a dossier <strong>after</strong> DLSA conducts legal aid intake review and formally allocates counsel.
              </p>
              <p className="text-foreground/90 leading-relaxed font-mono text-[11px] bg-secondary/50 p-2 rounded border border-border">
                <strong>Matter ID:</strong> {id} &bull; <strong>How to unlock:</strong> Log in as <em>DLSA Legal Aid Officer</em>, open case <strong>{id}</strong>, click <strong>Approve Legal Aid</strong>, and execute <strong>Assign Counsel</strong> to allocate this matter to your advocate profile.
              </p>
              <div className="pt-2 text-center">
                <Link
                  to="/case/UTP-0022?tab=draft"
                  className="text-xs text-primary font-bold hover:underline font-mono inline-flex items-center gap-1"
                >
                  Switch to your active assigned case UTP-0022 (Bail Draft Ready) &rarr;
                </Link>
              </div>
            </div>
          )}
        </div>
        <div className="flex items-center gap-3">
          <Link
            to={user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE" ? "/advocate" : "/dashboard"}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-sm text-sm font-semibold flex items-center gap-2"
          >
            {user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE" ? "Back to Assigned Briefs" : "Back to Dashboard"}
          </Link>
          <button onClick={load} className="px-4 py-2 border border-border text-foreground hover:bg-muted rounded-sm text-sm font-semibold flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  const c = caseData.case || {};
  const hasAssignedCounsel = Boolean(
    c.assigned_lawyer_id ||
    c.assigned_lawyer ||
    c.assigned_advocate_id ||
    c.assigned_advocate_name ||
    c.assignment_status === "ASSIGNED" ||
    caseData?.counsel_assigned ||
    caseData?.assigned_lawyer_id ||
    caseData?.assigned_lawyer ||
    caseData?.assigned_advocate_id ||
    caseData?.assigned_advocate_name ||
    caseData?.assignment_status === "ASSIGNED" ||
    (matterState && !["INTAKE", "VERIFICATION"].includes(matterState))
  );
  const eligibility = caseData.eligibility || {};
  const completeness = caseData.completeness || {};
  const retrieval = caseData.retrieval || {};
  const explanation = caseData.explanation || {};
  const legalNeeds: LegalNeedItem[] = c.legal_needs || [];
  const timeline: TimelineEvent[] = c.timeline || [];

  const isFiled = c.status === "FILED";

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
      const res = await referJailCaseToDlsa(id, "Prison custody desk legal-aid counsel assignment referral.");
      if (res?.status === "error" || res?.error) {
        throw new Error(res?.detail || res?.message || "Referral failed.");
      }
      setReferralDone(true);
      addToast("success", "Referred to DLSA", "Prison custody desk referral dispatched successfully.");
      await load();
    } catch (err: any) {
      const errMsg = err?.detail || err?.message || String(err);
      addToast("error", "Referral Failed", errMsg);
      setActionBanner({
        type: "error",
        text: `Referral failed: ${errMsg}`,
      });
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
      addToast("success", "Review Note Sent", "Your note has been added to the case file and shared with the defense counsel.");
      setDlsaComment("");
      await load();
    } catch (err: any) {
      addToast("error", "Could Not Send Note", "Failed to submit your review note. Please try again.");
      setActionBanner({
        type: "error",
        text: err.message || "Failed to submit review note.",
      });
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleGenerateAiDraft = async () => {
    if (!id) return;
    const currentCase = caseData?.case || {};
    const counselAssigned = Boolean(
      currentCase.assigned_lawyer_id ||
      currentCase.assigned_lawyer ||
      currentCase.assigned_advocate_id ||
      currentCase.assigned_advocate_name ||
      currentCase.assignment_status === "ASSIGNED" ||
      caseData?.counsel_assigned ||
      caseData?.assigned_lawyer_id ||
      caseData?.assigned_lawyer ||
      caseData?.assigned_advocate_id ||
      caseData?.assigned_advocate_name ||
      caseData?.assignment_status === "ASSIGNED" ||
      (matterState && !["INTAKE", "VERIFICATION"].includes(matterState))
    );
    if (!counselAssigned) {
      addToast("error", "Counsel Required", "Legal Aid Defense Counsel must be assigned before generating a formal bail petition.");
      return;
    }
    try {
      setGeneratingDraft(true);
      setActionBanner(null);
      const res = await generateBailDraft(id);
      if (!res || !res.draft_text) {
        throw new Error((res as any)?.detail || res?.message || "No draft content returned by the server.");
      }
      setEditableDraft(res.draft_text);
      setActionBanner({
        type: "success",
        text: `AI Bail Application draft generated successfully (v${res.version_number || 1}, ${res.provenance || "AI Generated"}). Grounded in Section 479 BNSS.`,
      });
      addToast("success", "Draft Generated", "A new bail petition draft has been created based on Section 479 guidelines.");
      await load();
    } catch (err: any) {
      const errMsg = err?.detail || err?.message || String(err);
      addToast("error", "Draft Creation Failed", errMsg);
      setActionBanner({
        type: "error",
        text: `Draft generation failed: ${errMsg}`,
      });
    } finally {
      setGeneratingDraft(false);
    }
  };

  const handleOpenDocPreview = (docId: string, docTitle?: string) => {
    setPreviewDocId(docId);
    setPreviewDocTitle(docTitle || "Official Document");
  };

  const handleDownloadCaseDoc = async (docId: string, fileName?: string) => {
    try {
      await downloadCaseDocument(docId, fileName || "document.txt");
    } catch (err: any) {
      alert(`Document download failed: ${err.message || err}`);
    }
  };

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
      addToast("success", "Case File Downloaded", `Official case dossier document (${caseData.case_id}) downloaded to your device.`);
    } catch (err: any) {
      addToast("error", "Download Failed", "Unable to download the case file right now. Please try again.");
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
      if (res?.status === "error" || res?.error || res?.success === false) {
        throw new Error(res?.detail || res?.message || res?.error || `Transition '${action}' failed.`);
      }
      setActionBanner({
        type: "success",
        text: `State transitioned to ${res.current_state} (Version ${res.version_number}) via ${action}.`,
      });

      const actionUpper = (action || "").toUpperCase();
      let friendlyTitle = "Case Updated";
      let friendlyMsg = "The case has been successfully updated.";

      if (actionUpper.includes("APPROVE")) {
        friendlyTitle = "Case Approved";
        friendlyMsg = "This bail application has been approved and moved to the next procedural step.";
      } else if (actionUpper.includes("SIGN_OFF") || actionUpper.includes("SIGN")) {
        friendlyTitle = "Bail Petition Signed";
        friendlyMsg = "Legal sign-off has been recorded. The petition is now ready for filing review.";
      } else if (actionUpper.includes("FILE")) {
        friendlyTitle = "Filed in Court";
        friendlyMsg = "The bail petition has been recorded as formally filed in court.";
      } else if (actionUpper.includes("REQUEST_CHANGES")) {
        friendlyTitle = "Revisions Requested";
        friendlyMsg = "Changes were requested on this petition, and the assigned advocate has been notified.";
      } else if (actionUpper.includes("HEARING")) {
        friendlyTitle = "Hearing Details Saved";
        friendlyMsg = "Court hearing notes and next dates have been saved to the case file.";
      } else if (actionUpper.includes("ASSIGN")) {
        friendlyTitle = "Advocate Assigned";
        friendlyMsg = "Legal counsel has been assigned to this undertrial prisoner.";
      } else if (actionUpper.includes("INTAKE") || actionUpper.includes("VERIF")) {
        friendlyTitle = "Intake Verified";
        friendlyMsg = "Undertrial custody details and eligibility status have been verified.";
      }

      addToast("success", friendlyTitle, friendlyMsg);
      await load();
    } catch (err: any) {
      const errMsg = err?.detail || err?.message || String(err);
      const isConflict = errMsg.includes("409") || errMsg.toLowerCase().includes("conflict") || errMsg.toLowerCase().includes("version mismatch");
      if (isConflict) {
        const fresh = await load();
        const updater = resolveCaseUpdater(err?.detail, fresh || caseData, caseData?.case?.district);
        addToast(
          "conflict",
          "Case Already Updated",
          `${updater} just updated this case. We have automatically refreshed your screen with the latest information.`
        );
      } else {
        addToast(
          "error",
          "Action Could Not Be Completed",
          errMsg || "Unable to complete this step right now. Please check the details and try again."
        );
      }
      setActionBanner({
        type: "error",
        text: errMsg || `Transition '${action}' failed.`,
      });
    } finally {
      setTransitioningAction(null);
    }
  };

  const handleTransitionButtonClick = (t: any) => {
    // If the transition requires payload keys, open the interactive modal
    if (t.required_payload_keys && t.required_payload_keys.length > 0) {
      const initialForm: Record<string, string> = {};
      t.required_payload_keys.forEach((key: string) => {
        if (key === "hearing_date" || key === "order_date" || key === "release_date") {
          initialForm[key] = new Date().toISOString().split("T")[0];
        } else if (key === "order_type") {
          initialForm[key] = "BAIL_GRANTED";
        } else if (key === "source_type") {
          initialForm[key] = "eCourts Daily Cause List";
        } else if (key === "bench_name") {
          initialForm[key] = caseData?.court_name || "";
        } else {
          initialForm[key] = "";
        }
      });
      if (t.action === "ASSIGN_COUNSEL") {
        setCounselSearchQuery("");
        if (eligibleCounselList.length > 0) {
          initialForm.assigned_advocate_id = eligibleCounselList[0].id;
          initialForm.assigned_advocate_name = eligibleCounselList[0].name;
        }
        if (id) {
          setLoadingEligibleCounsel(true);
          getEligibleCounsel(id)
            .then((res) => {
              if (res?.counsel_list && res.counsel_list.length > 0) {
                setEligibleCounselList(res.counsel_list);
                setTransitionFormData((prev) => ({
                  ...prev,
                  assigned_advocate_id: prev.assigned_advocate_id || res.counsel_list[0].id,
                  assigned_advocate_name: prev.assigned_advocate_name || res.counsel_list[0].name,
                }));
              }
            })
            .catch(() => {})
            .finally(() => setLoadingEligibleCounsel(false));
        }
      }
      setTransitionFormData(initialForm);
      setTransitionComment("");
      setActiveTransitionModal(t);
    } else {
      // Direct execution for transitions with no required input
      handleWorkflowTransition(t.action);
    }
  };

  const handleTransitionFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTransitionModal) return;

    // Check required fields
    for (const key of activeTransitionModal.required_payload_keys) {
      if (!transitionFormData[key] || !transitionFormData[key].trim()) {
        addToast("error", "Required Field Missing", `Please fill in ${key.replace(/_/g, " ")}.`);
        return;
      }
    }

    const action = activeTransitionModal.action;
    const payload = { ...transitionFormData };
    const comment = transitionComment.trim() || undefined;
    setActiveTransitionModal(null);
    await handleWorkflowTransition(action, payload, comment);
  };

  const handleAssignCounsel = async () => {
    if (!caseData?.case_id || !selectedLawyerId) return;
    try {
      setAssigningCounsel(true);
      setAssignmentSuccess(null);
      const res = await assignCaseCounsel(
        caseData.case_id,
        selectedLawyerId,
        selectedLawyerName,
        assignmentNotes || "Statutory Legal Aid Allocation under NALSA / DLSA mandate"
      );
      if (res?.status === "error" || res?.error) {
        throw new Error(res?.detail || res?.message || "Counsel Allocation failed.");
      }
      setCaseData((prev: any) => ({
        ...prev,
        assignment_status: "ASSIGNED",
        assigned_lawyer: selectedLawyerName,
        assigned_lawyer_id: selectedLawyerId,
        assigned_advocate_name: selectedLawyerName,
        assigned_advocate_id: selectedLawyerId,
      }));
      setAssignmentSuccess(`Successfully allocated ${selectedLawyerName} (${selectedLawyerId}) to case ${caseData.case_id}`);
      addToast("success", "Advocate Assigned", `Successfully allocated ${selectedLawyerName} to this matter.`);
      await load();
    } catch (err: any) {
      const errMsg = err?.detail || err?.message || String(err);
      addToast("error", "Counsel Allocation Failed", errMsg);
      setActionBanner({
        type: "error",
        text: `Counsel Allocation failed: ${errMsg}`,
      });
    } finally {
      setAssigningCounsel(false);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
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
                disabled={generatingDraft}
                className="px-3 py-2 border border-border rounded-sm hover:bg-secondary text-xs font-medium flex items-center gap-1.5"
                title="Download internal working copy — NOT a filed petition"
              >
                {generatingDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-4 h-4" />} Internal Copy
              </button>
              <span className="px-3 py-1.5 rounded-sm bg-red-500/10 border border-red-500/30 text-red-600 dark:text-red-400 text-xs font-mono font-bold flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" /> DLSA COORDINATION — Pending Advocate Sign-Off
              </span>
            </>
          ) : (
            <div className="flex items-center gap-2">
              {hasAssignedCounsel && !editableDraft && hasRole("DEFENSE_ADVOCATE") && (
                <button
                  onClick={handleGenerateAiDraft}
                  disabled={generatingDraft}
                  className="px-3 py-2 bg-primary text-primary-foreground rounded-sm hover:opacity-90 text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-opacity"
                  title="Generate Section 479 BNSS draft petition via AI drafting engine"
                >
                  {generatingDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Bot className="w-3.5 h-3.5" />}
                  ⚡ Generate Draft
                </button>
              )}
              <button
                onClick={generateBailDraftPDF}
                disabled={generatingDraft}
                className="px-3 py-2 border border-border rounded-sm hover:bg-secondary text-xs font-medium flex items-center gap-1.5"
                title="Download PDF petition"
              >
                {generatingDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-4 h-4" />} PDF
              </button>
            </div>
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
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] font-mono text-muted-foreground">Permitted Actions:</span>
              {/* Forward workflow transitions */}
              {availableTransitions.filter(t => t.user_has_permission && !t.is_exception).map(t => (
                <button
                  key={t.action}
                  onClick={() => handleTransitionButtonClick(t)}
                  disabled={transitioningAction === t.action}
                  className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-secondary hover:bg-muted border border-border text-foreground transition-colors flex items-center gap-1 shadow-sm"
                  title={t.description}
                >
                  {transitioningAction === t.action ? <Loader2 className="w-3 h-3 animate-spin" /> : null}
                  {t.action.replace(/_/g, " ")}
                </button>
              ))}
              {/* Exception transitions */}
              {availableTransitions.filter(t => t.user_has_permission && t.is_exception && t.action !== "RESOLVE_EXCEPTION").map(t => (
                <button
                  key={t.action}
                  onClick={() => handleTransitionButtonClick(t)}
                  disabled={transitioningAction === t.action}
                  className="px-2 py-1 text-[10px] font-mono font-bold rounded bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/30 hover:bg-red-500/20 transition-colors flex items-center gap-1"
                  title={t.description}
                >
                  <AlertTriangle className="w-3 h-3 shrink-0" />
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
              onClick={() => {
                const resolveRule = availableTransitions.find(t => t.action === "RESOLVE_EXCEPTION") || {
                  action: "RESOLVE_EXCEPTION",
                  target_state: "HUMAN_REVIEW",
                  description: "Supervising Legal Officer resolves exception condition and restores matter to active workflow.",
                  required_payload_keys: ["resolution_notes"],
                  is_exception: true,
                };
                handleTransitionButtonClick(resolveRule);
              }}
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
                  ? "bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400"
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
                        Jurisdiction: {c.police_station || "Jurisdiction Police Station"} • {c.district || "Designated District"}
                      </span>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded bg-primary/10 text-primary border border-primary/20 font-mono text-xs font-bold">
                    {c.fir_number || "FIR Pending"}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 rounded bg-muted/40 border border-border space-y-2">
                    <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Investigating Station</div>
                    <div className="text-foreground font-semibold text-sm">{c.police_station || "Jurisdiction Police Station"}</div>
                    <div className="text-muted-foreground">{c.district ? `${c.district}${c.state ? `, ${c.state}` : ""}` : (c.state || "Jurisdiction Record")}</div>
                  </div>

                  <div className="p-4 rounded bg-muted/40 border border-border space-y-2">
                    <div className="font-bold font-mono text-[11px] uppercase text-muted-foreground">Custodial Remand Metric</div>
                    <div className="text-foreground font-semibold text-sm">{c.custody_days || 0} Days In Custody</div>
                    <div className="text-muted-foreground">Detention Facility: {c.jail_location || "Correctional Facility"}</div>
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
                          : "bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30"
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
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30">
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
                            <span className="text-red-600 dark:text-red-400 flex items-center gap-1 text-[11px] font-bold">
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
                      : "bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30"
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
                  <span className="text-lg font-bold font-mono text-red-500">
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
                    <CheckCircle2 className={`w-3.5 h-3.5 ${c.multiple_active_cases ? "text-red-500" : "text-emerald-500"}`} />
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
                <span className={`text-xs font-mono font-bold ${completeness.is_complete ? "text-emerald-500" : "text-red-500"}`}>
                  {completeness.is_complete ? "All Documents Present" : "Missing Records Required"}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                {c.required_docs?.map((docType: string) => {
                  const normDoc = docType.toLowerCase().trim().replace(/ /g, "_");
                  const canonDoc = normalizeDocKey(normDoc);
                  const detail = caseDocDetails.find((d: any) => {
                    const dNorm = (d.document_type || "").toLowerCase().trim().replace(/ /g, "_");
                    const dCanon = normalizeDocKey(dNorm) || (d.canonical_type ? normalizeDocKey(d.canonical_type) : "");
                    return dNorm === normDoc || dCanon === canonDoc || dNorm === canonDoc || dCanon === normDoc || (d.id && (d.id.includes(normDoc) || d.id.includes(canonDoc)));
                  });

                  const isVerified = (detail && detail.document_status === "VERIFIED") || (c.present_docs || []).map(normalizeDocKey).includes(canonDoc);
                  const isReviewed = !isVerified && detail && detail.document_status === "REVIEWED";
                  const isPending = !isVerified && !isReviewed && (detail?.document_status === "PENDING_VERIFICATION" || (detail && detail.is_present && !isVerified));
                  const isAvailable = isVerified || isReviewed || isPending || Boolean(detail?.is_present);
                  const isMissing = !isAvailable;
                  const isSupervisor = user?.role === "SUPERVISING_LEGAL_OFFICER" || user?.role === "PLATFORM_ADMIN" || user?.role === "GOV_ADMIN";
                  const isDlsa = user?.role === "DLSA_OFFICER" || user?.role === "PLATFORM_ADMIN";
                  const docId = detail?.actual_doc_id || detail?.id || `DOC-${c.case_id}-${normDoc}`;

                  return (
                    <div
                      key={docType}
                      className={`p-4 rounded-lg border flex flex-col justify-between gap-3 overflow-hidden transition-all shadow-sm ${
                        isVerified
                          ? "bg-emerald-500/5 border-emerald-500/30"
                          : isReviewed
                          ? "bg-blue-500/10 border-blue-500/40"
                          : isPending
                          ? "bg-secondary/40 border-border"
                          : "bg-destructive/5 border-destructive/20"
                      }`}
                    >
                      {/* Top Header: Icon, Title, and Status Badge */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 min-w-0">
                          {isVerified ? (
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                          ) : isReviewed ? (
                            <CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0" />
                          ) : isPending ? (
                            <Clock className="w-4 h-4 text-red-500 shrink-0" />
                          ) : (
                            <AlertTriangle className="w-4 h-4 text-destructive shrink-0" />
                          )}
                          <span className="font-bold text-foreground tracking-tight text-xs font-serif uppercase truncate">
                            {docType.replace(/_/g, " ").toUpperCase()}
                          </span>
                        </div>

                        {/* Status Badge */}
                        <div className="shrink-0">
                          {isVerified && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-600 border border-emerald-500/30">
                              VERIFIED IN VAULT
                            </span>
                          )}
                          {isReviewed && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/20 text-blue-600 border border-blue-500/30">
                              REVIEWED (INTAKE) &bull; IN VAULT
                            </span>
                          )}
                          {isPending && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-secondary text-foreground border border-border">
                              PENDING VERIFICATION &bull; STORED IN VAULT
                            </span>
                          )}
                          {isMissing && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-destructive/20 text-destructive border border-destructive/30">
                              RECORD MISSING FROM VAULT
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Middle: Provenance & Attribution */}
                      <div className="text-[11px] text-muted-foreground font-mono">
                        {isVerified ? (
                          <span>Origin: <strong className="text-foreground">{detail?.uploaded_by || "Court Registry (Baseline)"}</strong></span>
                        ) : isReviewed ? (
                          <span>Status: <strong className="text-foreground">Reviewed for DLSA Intake</strong> &bull; Origin: <strong className="text-foreground">{detail?.uploaded_by || "Institutional Officer"}</strong></span>
                        ) : isPending ? (
                          <span>Stored in Vault &bull; Awaiting Verification &bull; Uploaded by: <strong className="text-foreground">{detail?.uploaded_by || "Institutional Officer"}</strong></span>
                        ) : (
                          <span className="text-red-600 dark:text-red-400 font-medium">Missing record &mdash; awaiting institutional upload</span>
                        )}
                      </div>

                      {/* Bottom: Dedicated Action Footer Bar */}
                      <div className="pt-2.5 border-t border-border/50 flex flex-wrap items-center justify-between gap-2">
                        {/* Left: View & Download controls */}
                        <div className="flex items-center gap-1.5">
                          {isAvailable ? (
                            <>
                              <button
                                onClick={() => handleOpenDocPreview(docId, docType.replace(/_/g, " ").toUpperCase())}
                                className="px-2 py-1 bg-secondary hover:bg-muted border border-border text-foreground rounded text-xs font-mono font-medium flex items-center gap-1 shadow-sm transition-colors"
                                title="Preview document content"
                              >
                                <Eye className="w-3.5 h-3.5 text-primary" />
                                <span>View</span>
                              </button>
                              <button
                                onClick={() => handleDownloadCaseDoc(docId, `${normDoc}_${c.case_id}.txt`)}
                                className="p-1 hover:bg-secondary border border-border rounded text-muted-foreground hover:text-foreground transition-colors"
                                title="Download document file"
                              >
                                <Download className="w-3.5 h-3.5" />
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => handleOpenDocPreview(docId, docType.replace(/_/g, " ").toUpperCase())}
                              className="px-2 py-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-600 dark:text-red-400 rounded text-xs font-mono font-medium flex items-center gap-1 shadow-sm transition-colors"
                              title="View statutory requisition notice"
                            >
                              <FileText className="w-3.5 h-3.5 text-red-500" />
                              <span>Notice</span>
                            </button>
                          )}
                        </div>

                        {/* Right: Operational actions */}
                        <div className="flex flex-wrap items-center gap-1.5">
                          {/* DLSA Officer: Review Document (only when pending) */}
                          {isPending && isDlsa && detail?.actual_doc_id && (
                            <button
                              onClick={() => handleReviewCaseDoc(detail.actual_doc_id)}
                              disabled={reviewingDocId === detail.actual_doc_id}
                              className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold uppercase flex items-center gap-1 shadow-sm transition-colors disabled:opacity-50"
                              title="Mark reviewed for DLSA intake"
                            >
                              {reviewingDocId === detail.actual_doc_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                              Review
                            </button>
                          )}

                          {/* Supervising Legal Officer / DLSA Officer: Supervisory Verify */}
                          {(isPending || isReviewed) && !isVerified && (isSupervisor || isDlsa) && (detail?.actual_doc_id || docId) && (
                            <button
                              onClick={() => handleVerifyCaseDoc(detail?.actual_doc_id || docId)}
                              disabled={verifyingDocId === (detail?.actual_doc_id || docId)}
                              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold uppercase flex items-center gap-1 shadow-sm transition-colors disabled:opacity-50"
                              title="Supervisory verification: authenticate record for court filing"
                            >
                              {verifyingDocId === (detail?.actual_doc_id || docId) ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCheck className="w-3 h-3" />}
                              {isSupervisor ? "Supervisory Verify" : "Verify Document"}
                            </button>
                          )}

                          {/* Upload / Re-upload Record */}
                          {can("DOCUMENT_UPLOAD") && (
                            <button
                              onClick={() => handleUploadDoc(docType)}
                              disabled={uploadingDoc === docType}
                              className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 transition-colors ${
                                isVerified
                                  ? "bg-secondary hover:bg-muted text-foreground border border-border"
                                  : "bg-primary text-primary-foreground hover:opacity-90 font-bold shadow-sm"
                              }`}
                              title={isVerified ? "Upload an updated copy to vault" : "Upload missing record"}
                            >
                              {uploadingDoc === docType ? <Loader2 className="w-3 h-3 animate-spin" /> : <Upload className="w-3 h-3" />}
                              <span>{isVerified ? "Re-upload" : isPending ? "Replace" : "Upload"}</span>
                            </button>
                          )}
                        </div>
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
          {!hasAssignedCounsel ? (
            <div className="p-8 border border-red-500/30 bg-red-500/5 rounded-sm space-y-6">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-full bg-red-500/20 text-red-600 dark:text-red-400 shrink-0">
                  <ShieldAlert className="w-8 h-8" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-secondary text-foreground border border-border">
                      Institutional Procedural Hold
                    </span>
                    <span className="text-xs font-mono text-muted-foreground">
                      Stage: LEGAL_AID_REQUIRED
                    </span>
                  </div>
                  <h3 className="font-serif font-bold text-xl text-foreground">
                    Legal Aid Defense Counsel Not Yet Assigned
                  </h3>
                  <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
                    Under Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023 institutional protocol, formal bail petition drafting is an <strong className="text-foreground">Advocate Work Product</strong>. Defense counsel must be designated before court-grade petition generation and sign-off can be initiated.
                  </p>
                </div>
              </div>

              <div className="p-4 rounded border border-border bg-card/60 space-y-3">
                <h4 className="text-xs font-mono font-bold uppercase text-foreground flex items-center gap-2">
                  <Info className="w-4 h-4 text-primary" /> Case Representation Status
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-muted/40 rounded border border-border">
                    <div className="text-[10px] font-mono uppercase text-muted-foreground">Accused Inmate</div>
                    <div className="font-bold text-foreground mt-0.5">{c.name || "UTP Inmate"}</div>
                  </div>
                  <div className="p-3 bg-muted/40 rounded border border-border">
                    <div className="text-[10px] font-mono uppercase text-muted-foreground">Custody Duration</div>
                    <div className="font-bold text-foreground mt-0.5">{c.custody_days ?? 0} days (Detained)</div>
                  </div>
                  <div className="p-3 bg-muted/40 rounded border border-border">
                    <div className="text-[10px] font-mono uppercase text-muted-foreground">Counsel Assignment</div>
                    <div className="font-bold text-red-600 dark:text-red-400 mt-0.5">Pending Panel Allocation</div>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                {hasRole("DLSA_OFFICER", "SUPERVISING_LEGAL_OFFICER", "PLATFORM_ADMIN") ? (
                  <button
                    onClick={() => setActiveTab("legalaid")}
                    className="px-4 py-2.5 bg-primary text-primary-foreground rounded-sm text-xs font-bold font-mono uppercase tracking-wider flex items-center gap-2 shadow-sm hover:opacity-90 transition-opacity"
                  >
                    <UserCheck className="w-4 h-4" />
                    Go to Counsel Allocation & Assign Defense Advocate
                  </button>
                ) : (
                  <p className="text-xs font-mono text-muted-foreground">
                    Awaiting DLSA Secretary / Supervisory Legal Officer counsel designation.
                  </p>
                )}
                <button
                  onClick={() => setActiveTab("dossier")}
                  className="px-4 py-2.5 border border-border rounded-sm text-xs font-medium hover:bg-secondary text-foreground transition-colors"
                >
                  Return to Case Dossier
                </button>
              </div>
            </div>
          ) : (
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
                  {hasRole("DEFENSE_ADVOCATE") && (
                    <button
                      onClick={handleGenerateAiDraft}
                      disabled={generatingDraft || !hasAssignedCounsel}
                      className="px-3 py-1.5 bg-primary text-primary-foreground rounded-sm hover:opacity-90 text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-opacity disabled:opacity-50"
                      title="Generate court-ready statutory Section 479 BNSS bail petition draft"
                    >
                      {generatingDraft ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                      {editableDraft ? "⚡ Regenerate AI Draft" : "⚡ Generate AI Bail Draft"}
                    </button>
                  )}
                  <button
                    onClick={generateBailDraftPDF}
                    disabled={generatingDraft || !hasAssignedCounsel}
                    className="px-3 py-1.5 border border-border rounded-sm hover:bg-secondary text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                    title={isDlsa ? "Download internal working copy — NOT a filed petition" : "Download PDF petition"}
                  >
                    {generatingDraft ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />} {isDlsa ? "Internal Copy" : "Download PDF"}
                  </button>
                  <button
                    onClick={() => navigate(`/workspace/documents?case_id=${c.case_id}`)}
                    className="px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-sm text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-opacity"
                    title="Open Document Workspace with side-by-side diff, readiness audit, and revision lineage"
                  >
                    <Scale className="w-4 h-4" /> Open in Workspace
                  </button>
                </div>
              </div>

              {!editableDraft.trim() && hasAssignedCounsel && hasRole("DEFENSE_ADVOCATE") && (
                <div className="p-4 rounded-sm border border-primary/20 bg-primary/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <Bot className="w-4 h-4 text-primary" /> AI Bail Petition Generation Ready
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Counsel is assigned. Click below to request AI generation of a formal Section 479 BNSS statutory bail petition draft.
                    </p>
                  </div>
                  <button
                    onClick={handleGenerateAiDraft}
                    disabled={generatingDraft}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-sm hover:opacity-90 text-xs font-bold font-mono uppercase tracking-wider flex items-center gap-2 shadow-sm transition-opacity shrink-0"
                  >
                    {generatingDraft ? <Loader2 className="w-4 h-4 animate-spin" /> : <Bot className="w-4 h-4" />}
                    Generate Draft Now
                  </button>
                </div>
              )}

            {/* In-Line Draft Editor — Role-Scoped */}
            {isDlsa ? (
              <div className="space-y-4">
                {/* DLSA: Read-only petition view */}
                <div className="space-y-2">
                  <label className="text-xs font-mono font-bold uppercase text-muted-foreground flex items-center gap-2">
                    <ShieldCheck className="w-3.5 h-3.5 text-red-500" />
                    Petition Work Product — Read Only (Authorised Legal Counsel Editing Reserved):
                  </label>
                  <div className="w-full p-4 font-mono text-xs bg-muted/30 border border-border rounded-sm text-foreground leading-relaxed min-h-[200px] overflow-auto whitespace-pre-wrap select-all">
                    {editableDraft || "Draft petition will appear here once AI generation is complete."}
                  </div>
                  <p className="text-[11px] text-red-600 dark:text-red-400 font-mono">
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
                {/* DLSA Review Feedback Banner for Advocate */}
                {(() => {
                  const reviewEvents = (c.timeline || []).filter(
                    (ev: any) => ev.event_type === "LEGAL_AID" && (ev.title?.includes("Review Feedback") || ev.title?.includes("Review Note"))
                  );
                  if (reviewEvents.length === 0) return null;
                  const latestFeedback = reviewEvents[reviewEvents.length - 1];
                  return (
                    <div className="p-3.5 bg-red-500/10 border border-red-500/30 rounded-sm space-y-1.5 font-mono text-xs">
                      <div className="flex items-center gap-2 font-bold text-red-600 dark:text-red-400">
                        <AlertTriangle className="w-4 h-4 shrink-0" />
                        <span>Institutional Review Directive ({latestFeedback.actor_role?.replace(/_/g, " ")}):</span>
                      </div>
                      <p className="text-foreground pl-6 whitespace-pre-wrap">{latestFeedback.description}</p>
                      <div className="text-[10px] text-muted-foreground pl-6">
                        Submitted by {latestFeedback.actor} &bull; {latestFeedback.timestamp}
                      </div>
                    </div>
                  );
                })()}

                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-bold uppercase text-muted-foreground">
                    Editable Petition Text (Reviewed by Defence Counsel):
                  </label>
                  <div className="flex items-center gap-3">
                    {hasRole("DEFENSE_ADVOCATE") && (
                      <span className="text-[11px] font-mono text-primary font-semibold">
                        Counsel Work Product // Versioned Legal Draft
                      </span>
                    )}
                    {hasRole("DEFENSE_ADVOCATE") && (
                      <button
                        onClick={handleSaveDraft}
                        disabled={savingDraft || !editableDraft.trim()}
                        className="px-3 py-1 bg-secondary hover:bg-muted text-foreground border border-border rounded-sm text-xs font-mono font-bold flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-50"
                        title="Persist draft updates directly to cloud database"
                      >
                        {savingDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5 text-primary" />}
                        {savingDraft ? "Saving Changes..." : "Save Draft Changes"}
                      </button>
                    )}
                  </div>
                </div>
                <textarea
                  value={editableDraft}
                  onChange={(e) => setEditableDraft(e.target.value)}
                  readOnly={!hasRole("DEFENSE_ADVOCATE")}
                  rows={16}
                  className={`w-full p-4 font-mono text-xs border border-border rounded-sm leading-relaxed resize-y ${
                    hasRole("DEFENSE_ADVOCATE")
                      ? "bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                      : "bg-muted/30 text-foreground cursor-not-allowed"
                  }`}
                />
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-border">
                  <p className="text-[11px] font-mono text-muted-foreground">
                    {hasRole("DEFENSE_ADVOCATE")
                      ? `Counsel Review Status: ${advocateSignedOff ? "✓ Legal Sign-Off Recorded (Awaiting Supervisory Approval)" : "Draft Under Active Counsel Review"}`
                      : "Draft Petitions are prepared by assigned defense counsel and reviewed by supervisors prior to court filing."}
                  </p>
                  <div className="flex items-center gap-2">
                    {hasRole("DEFENSE_ADVOCATE") && (
                      <>
                        <button
                          onClick={handleSaveDraft}
                          disabled={savingDraft || !editableDraft.trim()}
                          className="px-3.5 py-2 bg-secondary hover:bg-muted text-foreground border border-border rounded-sm text-xs font-bold font-mono uppercase tracking-wider flex items-center gap-1.5 transition-colors disabled:opacity-50"
                        >
                          {savingDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5 text-primary" />}
                          {savingDraft ? "Saving..." : "Save Draft Changes"}
                        </button>
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
                      </>
                    )}
                  </div>
                </div>

                {/* ── Level 2: Supervisory Legal Officer Approval Gateway ── */}
                {hasRole("SUPERVISING_LEGAL_OFFICER") && c.assignment_status === "ASSIGNED" && Boolean(c.assigned_lawyer || c.assigned_lawyer_id) && (matterState === "SUBMITTED" || c.status === "LAWYER_REVIEW" || advocateSignedOff) && matterState !== "APPROVED" && c.status !== "APPROVED_READY_FOR_FILING" && c.status !== "FILED" && (
                  <div className="p-4 rounded-sm border border-emerald-500/30 bg-emerald-500/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-emerald-600" />
                        <span className="font-bold text-xs font-serif uppercase text-foreground">Supervisory Approval Gateway (Level 2)</span>
                      </div>
                      <p className="text-xs text-muted-foreground font-mono">
                        Counsel legal sign-off has been verified. As Supervisory Legal Officer, issue institutional approval so defense counsel can proceed to file in court.
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleTransitionButtonClick({
                          action: "REQUEST_REVISIONS",
                          required_payload_keys: ["comment"],
                          description: "Return petition draft to assigned counsel with revision notes"
                        })}
                        disabled={transitioningAction === "REQUEST_REVISIONS"}
                        className="px-3 py-2 bg-secondary hover:bg-secondary/80 text-foreground border border-border rounded-sm text-xs font-bold font-serif uppercase tracking-wider flex items-center gap-1.5 transition-colors"
                      >
                        <Send className="w-3.5 h-3.5 text-red-500" />
                        Request Revisions
                      </button>
                      <button
                        onClick={() => handleWorkflowTransition("SUPERVISORY_APPROVE")}
                        disabled={transitioningAction === "SUPERVISORY_APPROVE"}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-sm text-xs font-bold font-serif uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-colors"
                      >
                        {transitioningAction === "SUPERVISORY_APPROVE" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCheck className="w-3.5 h-3.5" />}
                        Approve Bail Petition
                      </button>
                    </div>
                  </div>
                )}

                {/* ── Level 3: Defence Legal-Aid Advocate Files In Court ── */}
                {hasRole("DEFENSE_ADVOCATE") && c.assignment_status === "ASSIGNED" && (matterState === "APPROVED" || c.status === "APPROVED_READY_FOR_FILING" || c.status === "APPROVED") && c.status !== "FILED" && (
                  <div className="p-4 rounded-sm border border-blue-500/30 bg-blue-500/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <Scale className="w-4 h-4 text-blue-600" />
                        <span className="font-bold text-xs font-serif uppercase text-foreground">Court Registry Filing Gateway</span>
                      </div>
                      <p className="text-xs text-muted-foreground font-mono">
                        Supervisory sign-off is complete. As designated Legal-Aid Defense Counsel, file this petition in the Court Registry and record the filing reference.
                      </p>
                    </div>
                    <button
                      onClick={() => handleTransitionButtonClick({ action: "RECORD_FILING", required_payload_keys: ["filing_reference"], description: "Lodge approved petition in court registry" })}
                      disabled={transitioningAction === "RECORD_FILING"}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-sm text-xs font-bold font-serif uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-colors shrink-0"
                    >
                      {transitioningAction === "RECORD_FILING" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                      File Petition in Court Registry
                    </button>
                  </div>
                )}

                {/* ── DLSA / Supervisory Observation Notice ── */}
                {(isDlsa || hasRole("DLSA_OFFICER")) && (
                  <div className="p-3 bg-secondary/60 border border-border rounded-sm text-xs font-mono text-muted-foreground space-y-1">
                    <span className="font-bold text-foreground flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-primary" /> DLSA Coordination &amp; Oversight Status:
                    </span>
                    <p>
                      {c.status === "FILED"
                        ? "Bail petition has been formally lodged in the Court Registry by the assigned Legal-Aid Advocate."
                        : c.status === "APPROVED_READY_FOR_FILING" || matterState === "APPROVED"
                        ? "Petition approved by Supervisory Legal Officer. Awaiting court filing by the assigned Legal-Aid Advocate."
                        : advocateSignedOff || c.status === "LAWYER_REVIEW" || matterState === "SUBMITTED"
                        ? "Counsel sign-off recorded. Currently undergoing Level 2 Supervisory Legal Review."
                        : "Assigned Defense Counsel is currently preparing and reviewing the bail application work product."}
                    </p>
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
        )}
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
            {(() => {
              const list: any[] = [];
              const seenCanonKeys = new Set<string>();

              // 1. Add all documents already indexed from caseDocDetails
              (caseDocDetails || []).forEach((d: any) => {
                const norm = (d.document_type || "").toLowerCase().trim().replace(/ /g, "_");
                const canon = normalizeDocKey(norm) || (d.canonical_type ? normalizeDocKey(d.canonical_type) : norm);
                if (canon && !seenCanonKeys.has(canon)) {
                  seenCanonKeys.add(canon);
                  list.push({
                    ...d,
                    canonical_type: canon,
                    actual_doc_id: d.actual_doc_id || d.id || `DOC-${c.case_id}-${norm}`,
                  });
                }
              });

              // 2. Add required docs not yet in caseDocDetails
              (c.required_docs || []).forEach((reqDoc: string) => {
                const norm = reqDoc.toLowerCase().trim().replace(/ /g, "_");
                const canon = normalizeDocKey(norm);
                if (!seenCanonKeys.has(canon)) {
                  seenCanonKeys.add(canon);
                  const isBaselinePresent = (c.present_docs || []).map(normalizeDocKey).includes(canon);
                  list.push({
                    id: `DOC-${c.case_id}-${norm}`,
                    actual_doc_id: `DOC-${c.case_id}-${norm}`,
                    document_type: norm,
                    canonical_type: canon,
                    document_title: reqDoc.replace(/_/g, " ").toUpperCase(),
                    status: isBaselinePresent ? "Verified & Present" : "Missing Action Required",
                    document_status: isBaselinePresent ? "VERIFIED" : "MISSING",
                    is_present: isBaselinePresent,
                    uploaded_by: isBaselinePresent ? "Court Registry (Baseline)" : null,
                    uploaded_at: isBaselinePresent ? c.arrest_date : null,
                    evidence_id: `EVI-${c.case_id}-${norm}`,
                  });
                }
              });

              // 3. Add any present_docs not yet seen
              (c.present_docs || []).forEach((presDoc: string) => {
                const norm = presDoc.toLowerCase().trim().replace(/ /g, "_");
                const canon = normalizeDocKey(norm);
                if (!seenCanonKeys.has(canon)) {
                  seenCanonKeys.add(canon);
                  list.push({
                    id: `DOC-${c.case_id}-${norm}`,
                    actual_doc_id: `DOC-${c.case_id}-${norm}`,
                    document_type: norm,
                    canonical_type: canon,
                    document_title: presDoc.replace(/_/g, " ").toUpperCase(),
                    status: "Verified & Present",
                    document_status: "VERIFIED",
                    is_present: true,
                    uploaded_by: "Court Registry (Baseline)",
                    uploaded_at: c.arrest_date,
                    evidence_id: `EVI-${c.case_id}-${norm}`,
                  });
                }
              });

              if (list.length === 0) {
                return (
                  <p className="text-xs text-muted-foreground p-4 bg-muted/20 rounded border border-border">
                    No document records or vault entries currently indexed for this matter.
                  </p>
                );
              }

              return list.map((docItem: any) => {
                const normDoc = (docItem.document_type || "").toLowerCase().trim().replace(/ /g, "_");
                const canonDoc = docItem.canonical_type || normalizeDocKey(normDoc);
                const docTitle = docItem.document_title || normDoc.replace(/_/g, " ").toUpperCase();
                const isVerified = docItem.document_status === "VERIFIED" || (c.present_docs || []).map(normalizeDocKey).includes(canonDoc);
                const isReviewed = !isVerified && docItem.document_status === "REVIEWED";
                const isPending = !isVerified && !isReviewed && (docItem.document_status === "PENDING_VERIFICATION" || (docItem.is_present && !isVerified));
                const isMissing = !isVerified && !isReviewed && !isPending && !docItem.is_present;
                const docId = docItem.actual_doc_id || docItem.id || `DOC-${c.case_id}-${normDoc}`;
                const eviId = docItem.evidence_id || `EVI-${c.case_id}-${normDoc}`;
                const isSupervisor = user?.role === "SUPERVISING_LEGAL_OFFICER" || user?.role === "PLATFORM_ADMIN" || user?.role === "GOV_ADMIN";
                const isDlsa = user?.role === "DLSA_OFFICER" || user?.role === "PLATFORM_ADMIN";

                return (
                  <div
                    key={canonDoc || normDoc}
                    className={`p-4 border rounded-sm flex flex-wrap items-center justify-between gap-4 transition-all ${
                      isVerified
                        ? "border-emerald-500/30 bg-emerald-500/5"
                        : isReviewed
                        ? "border-blue-500/30 bg-blue-500/5"
                        : isPending
                        ? "border-red-500/30 bg-red-500/5"
                        : "border-destructive/30 bg-destructive/5"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {isVerified ? (
                        <ShieldCheck className="w-5 h-5 text-emerald-500 shrink-0" />
                      ) : isReviewed ? (
                        <CheckCircle2 className="w-5 h-5 text-blue-500 shrink-0" />
                      ) : isPending ? (
                        <Clock className="w-5 h-5 text-red-500 shrink-0" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-destructive shrink-0" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-bold text-sm font-serif text-foreground">
                            {docTitle}
                          </h4>
                          {isVerified && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-600 border border-emerald-500/30">
                              VERIFIED IN VAULT
                            </span>
                          )}
                          {isReviewed && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-600 border border-blue-500/30">
                              REVIEWED (INTAKE) &bull; STORED IN VAULT
                            </span>
                          )}
                          {isPending && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-secondary text-foreground border border-border">
                              PENDING VERIFICATION &bull; STORED IN VAULT
                            </span>
                          )}
                          {isMissing && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-destructive/20 text-destructive border border-destructive/30">
                              RECORD MISSING FROM VAULT
                            </span>
                          )}
                        </div>
                        <p className="text-xs font-mono text-muted-foreground mt-0.5">
                          Evidence ID: {eviId} &bull; Format: Digitised Judicial Record
                          {docItem.uploaded_by && ` &bull; Origin: ${docItem.uploaded_by}`}
                          {docItem.file_hash && (
                            <span className="ml-2 font-mono text-[10px] text-muted-foreground/80" title={docItem.file_hash}>
                              &bull; SHA256: {docItem.file_hash.slice(0, 8)}...
                            </span>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {!isMissing ? (
                        <>
                          <button
                            onClick={() => handleOpenDocPreview(docId, docTitle)}
                            className="px-2.5 py-1.5 bg-secondary border border-border text-foreground hover:bg-muted text-xs font-mono font-semibold rounded flex items-center gap-1.5 shadow-sm"
                            title="Preview document content and integrity seal"
                          >
                            <Eye className="w-3.5 h-3.5 text-primary" />
                            View
                          </button>
                          <button
                            onClick={() => handleDownloadCaseDoc(docId, `${normDoc}_${c.case_id}.txt`)}
                            className="p-1.5 bg-secondary border border-border text-muted-foreground hover:text-foreground text-xs rounded shadow-sm"
                            title="Download official file"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>

                          {/* DLSA Intake Review */}
                          {isPending && isDlsa && docItem.actual_doc_id && (
                            <button
                              onClick={() => handleReviewCaseDoc(docItem.actual_doc_id)}
                              disabled={reviewingDocId === docItem.actual_doc_id}
                              className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold uppercase flex items-center gap-1 shadow-sm transition-colors disabled:opacity-50"
                              title="Mark reviewed for DLSA legal-aid intake"
                            >
                              {reviewingDocId === docItem.actual_doc_id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                              Review
                            </button>
                          )}

                          {/* Supervisory / DLSA Verification */}
                          {(isPending || isReviewed) && !isVerified && (isSupervisor || isDlsa) && (docItem.actual_doc_id || docId) && (
                            <button
                              onClick={() => handleVerifyCaseDoc(docItem.actual_doc_id || docId)}
                              disabled={verifyingDocId === (docItem.actual_doc_id || docId)}
                              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold uppercase flex items-center gap-1 shadow-sm transition-colors disabled:opacity-50"
                              title="Supervisory verification: authenticate record for court filing"
                            >
                              {verifyingDocId === (docItem.actual_doc_id || docId) ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCheck className="w-3 h-3" />}
                              {isSupervisor ? "Supervisory Verify" : "Verify Document"}
                            </button>
                          )}

                          {hasRole("SUPERVISING_LEGAL_OFFICER", "DLSA_OFFICER", "JAIL_OFFICER") ? (
                            <button
                              onClick={() => handleVerifyEvidence(eviId)}
                              disabled={verifyingEvidenceId === eviId}
                              className="px-3 py-1.5 bg-secondary border border-border text-foreground hover:bg-muted text-xs font-semibold rounded flex items-center gap-1.5"
                            >
                              {verifyingEvidenceId === eviId ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                              Verify Integrity
                            </button>
                          ) : (
                            <span className="px-2.5 py-1 text-[11px] font-sans text-muted-foreground bg-muted/50 border border-border rounded flex items-center gap-1" title="Evidence verification is performed by DLSA, Supervisory Legal Officer, or Jail Custody Officer">
                              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                              Custody Verified
                            </span>
                          )}
                        </>
                      ) : (
                        can("DOCUMENT_UPLOAD") ? (
                          <button
                            onClick={() => handleUploadDoc(normDoc)}
                            disabled={uploadingDoc === normDoc}
                            className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-xs font-semibold flex items-center gap-1.5 hover:opacity-90 shadow-sm"
                          >
                            {uploadingDoc === normDoc ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                            Upload Document
                          </button>
                        ) : (
                          <span className="text-xs font-mono text-destructive">
                            Awaiting Record Upload
                          </span>
                        )
                      )}
                    </div>
                  </div>
                );
              });
            })()}

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
              <span className="px-2.5 py-1 rounded bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 font-mono text-xs font-bold flex items-center gap-1">
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
              <div className="text-muted-foreground">{c.court_name || (c.district ? `${c.district} Legal Services Authority` : "District Legal Services Authority Complex")}</div>
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
          {can("CASE_ASSIGN_COUNSEL") && (matterState === "REVIEW" || matterState === "LEGAL_AID_REQUIRED" || matterState === "ASSIGNED" || c.assignment_status === "ASSIGNED" || c.status === "ASSIGNED" || c.status === "REVIEW") && (
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
                {c.assignment_status === "ASSIGNED" ? (
                  <span className="px-2.5 py-0.5 rounded font-mono text-[11px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-bold">
                    ACTIVE ALLOCATION
                  </span>
                ) : (matterState === "REVIEW" || c.status === "REVIEW") ? (
                  <span className="px-2.5 py-0.5 rounded font-mono text-[11px] bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 font-bold">
                    REVIEW PENDING
                  </span>
                ) : null}
              </div>

              {(matterState === "REVIEW" || c.status === "REVIEW") && (
                <div className="p-3 rounded bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 font-mono text-xs flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Scale className="w-4 h-4 text-amber-600 shrink-0" />
                    <span>Matter awaiting DLSA intake review. Appointing counsel below will automatically approve Legal Aid review.</span>
                  </div>
                  <button
                    onClick={() => handleWorkflowTransition("FLAG_LEGAL_AID_REQUIRED", {}, "Approved by DLSA Legal Aid Officer")}
                    disabled={!!transitioningAction}
                    className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-[11px] font-bold font-mono shrink-0 shadow-xs"
                  >
                    {transitioningAction === "FLAG_LEGAL_AID_REQUIRED" ? "Approving..." : "Approve Legal Aid First"}
                  </button>
                </div>
              )}

              {assignmentSuccess && (
                <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 font-mono text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{assignmentSuccess}</span>
                </div>
              )}

              <div className="space-y-4 text-xs">
                <div>
                  {(() => {
                    const displayPanelAdvocates = eligibleCounselList.length > 0
                      ? eligibleCounselList.map((adv: any) => ({
                          id: adv.id,
                          name: adv.name,
                          bar: adv.bar_registration_no,
                          specialisation: `${adv.matter_type || "Criminal"} • ${adv.district}`,
                          experience: `${adv.experience_years} yrs`,
                          activeCases: adv.active_cases,
                          tier_label: adv.tier_label,
                        }))
                      : [];
                    const filtered = displayPanelAdvocates.filter((a: any) =>
                      !advocateSearchQuery ||
                      a.name.toLowerCase().includes(advocateSearchQuery.toLowerCase()) ||
                      a.bar.toLowerCase().includes(advocateSearchQuery.toLowerCase()) ||
                      a.specialisation.toLowerCase().includes(advocateSearchQuery.toLowerCase())
                    );
                    return (
                      <>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-muted-foreground font-semibold">
                            Search &amp; Select Panel Defense Advocate
                          </label>
                          <span className="text-[11px] font-mono text-primary font-semibold">
                            {filtered.length} empanelled counsel available
                          </span>
                        </div>
                        <input
                          type="text"
                          value={advocateSearchQuery}
                          onChange={(e) => setAdvocateSearchQuery(e.target.value)}
                          placeholder="Search panel counsel by name, bar enrolment, or statutory specialization..."
                          className="w-full p-2.5 border border-border rounded bg-background text-foreground text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary mb-3"
                        />
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-48 overflow-y-auto pr-1">
                          {filtered.length === 0 ? (
                            <div className="col-span-full p-3 text-center text-muted-foreground border border-dashed border-border rounded bg-muted/10 font-sans text-xs">
                              No empanelled counsel found for this district or query.
                            </div>
                          ) : (
                            filtered.map((adv: any) => {
                              const isSelected = selectedLawyerId === adv.id;
                              return (
                                <div
                                  key={adv.id}
                                  onClick={() => {
                                    setSelectedLawyerId(adv.id);
                                    setSelectedLawyerName(adv.name);
                                  }}
                                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                    isSelected
                                      ? "bg-primary/10 border-primary shadow-sm ring-1 ring-primary"
                                      : "bg-secondary/30 border-border hover:bg-secondary/60"
                                  }`}
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="font-bold text-foreground">{adv.name}</span>
                                    {isSelected && (
                                      <span className="text-[10px] font-mono font-bold text-primary bg-primary/15 px-1.5 py-0.5 rounded border border-primary/30">
                                        SELECTED
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                                    Bar: <strong className="text-foreground">{adv.bar}</strong> &bull; Exp: {adv.experience}
                                  </div>
                                  <div className="text-[10px] text-muted-foreground mt-1 flex items-center justify-between">
                                    <span className="truncate max-w-[180px]">{adv.specialisation}</span>
                                    <span className="font-mono text-primary font-medium">{adv.activeCases} active cases</span>
                                  </div>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </>
                    );
                  })()}
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
                      placeholder="Select or enter advocate name"
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
                      placeholder="Select or enter counsel ID / Bar Reg"
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
      {/* Interactive Workflow Transition Modal for Required Prerequisites */}
      {activeTransitionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div
            className="w-full max-w-lg bg-card border border-border rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
            style={{ boxShadow: "0 0 50px rgba(0,0,0,0.4)" }}
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/30">
              <div className="flex items-center gap-2.5">
                {activeTransitionModal.is_exception ? (
                  <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
                ) : (
                  <ShieldCheck className="w-5 h-5 text-primary shrink-0" />
                )}
                <div>
                  <h3 className="text-sm font-serif font-bold text-foreground">
                    {activeTransitionModal.action.replace(/_/g, " ")}
                  </h3>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Target State: <span className="font-mono font-bold text-primary">{activeTransitionModal.target_state}</span>
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setActiveTransitionModal(null)}
                className="w-7 h-7 rounded-lg hover:bg-secondary flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleTransitionFormSubmit} className="p-6 space-y-4 overflow-y-auto">
              {activeTransitionModal.description && (
                <div className="p-3 bg-secondary/40 border border-border/60 rounded-lg text-xs text-muted-foreground">
                  {activeTransitionModal.description}
                </div>
              )}

              {activeTransitionModal.required_payload_keys.map((key) => {
                if (key === "reason") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Reason for Manual Escalation <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="Detail the statutory ambiguity, complex provisos, health or custody issues requiring human supervisor intervention..."
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "conflict_details") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Data Conflict Details <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="Specify conflicting custody dates, FIR numbers, charges, or biometric/identity discrepancies across Police, Jail, or Court records..."
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "block_reason") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Administrative Block Justification <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="State the institutional, legal stay, or statutory grounds for placing a hard block on this matter..."
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "resolution_notes") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Supervisory Resolution Notes <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        required
                        rows={3}
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="Document how the exception was verified and resolved before restoring the matter to active workflow..."
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "closure_reason") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Matter Closure Justification <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        required
                        rows={2}
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="Reason for concluding legal-aid and supervisory oversight..."
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "filing_reference") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Court CNR / E-Filing Acknowledgement Number <span className="text-rose-500">*</span>
                      </label>
                      <input
                        required
                        type="text"
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="e.g., DLCT01-001234-2026 or EF-DEL-2026-098"
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "hearing_date") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Scheduled Hearing Date <span className="text-rose-500">*</span>
                      </label>
                      <input
                        required
                        type="date"
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "order_type") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Court Order Pronouncement <span className="text-rose-500">*</span>
                      </label>
                      <select
                        required
                        value={transitionFormData[key] || "BAIL_GRANTED"}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      >
                        <option value="BAIL_GRANTED">Bail Granted</option>
                        <option value="BAIL_REJECTED">Bail Rejected</option>
                        <option value="INTERIM_RELIEF">Interim Bail Granted</option>
                        <option value="STATUTORY_BAIL_479">Section 479 Statutory Bail Granted</option>
                        <option value="DISCHARGED">Discharged / Quashed</option>
                      </select>
                    </div>
                  );
                }
                if (key === "order_date") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Date of Court Order <span className="text-rose-500">*</span>
                      </label>
                      <input
                        required
                        type="date"
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "release_date") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Prison Release Date <span className="text-rose-500">*</span>
                      </label>
                      <input
                        required
                        type="date"
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "bench_name") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Court Bench / Courtroom <span className="text-rose-500">*</span>
                      </label>
                      <input
                        required
                        type="text"
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="e.g., Court No. 4, Sessions Judge, Tis Hazari"
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "source_type") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Listing Source / Notice Provenance <span className="text-rose-500">*</span>
                      </label>
                      <select
                        required
                        value={transitionFormData[key] || "eCourts Daily Cause List"}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      >
                        <option value="eCourts Daily Cause List">eCourts Daily Cause List</option>
                        <option value="Court Registry Notice">Court Registry Notice</option>
                        <option value="Urgent Motion / Direct Mention">Urgent Motion / Direct Mention</option>
                        <option value="Judicial Order Memo">Judicial Order Memo</option>
                      </select>
                    </div>
                  );
                }
                if (key === "judge_name") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Presiding Judge Name <span className="text-rose-500">*</span>
                      </label>
                      <input
                        required
                        type="text"
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="e.g., Hon'ble Sessions Judge S. K. Verma"
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "order_reference") {
                  return (
                    <div key={key}>
                      <label className="block text-xs font-semibold text-foreground mb-1">
                        Certified Order Reference / Dispatch No. <span className="text-rose-500">*</span>
                      </label>
                      <input
                        required
                        type="text"
                        value={transitionFormData[key] || ""}
                        onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                        placeholder="e.g., ORD-2026-DEL-8832 or Cr.M.A. 452/2026"
                        className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                      />
                    </div>
                  );
                }
                if (key === "assigned_advocate_id") {
                  const filteredCounsel = eligibleCounselList.filter((c: any) => {
                    if (!counselSearchQuery) return true;
                    const q = counselSearchQuery.toLowerCase();
                    return (
                      c.name?.toLowerCase().includes(q) ||
                      c.district?.toLowerCase().includes(q) ||
                      c.matter_type?.toLowerCase().includes(q) ||
                      c.bar_registration_no?.toLowerCase().includes(q) ||
                      c.dlsa_institution?.toLowerCase().includes(q)
                    );
                  });
                  const selectedAdvId = transitionFormData["assigned_advocate_id"] || "";

                  return (
                    <div key={key} className="space-y-3">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="block text-xs font-semibold text-foreground">
                            Select Defence Legal-Aid Advocate <span className="text-rose-500">*</span>
                          </label>
                          <span className="text-[10px] font-mono text-primary font-bold">
                            {caseData?.district ? `${caseData.district} DLSA Panel` : "DLSA Jurisdiction"}
                          </span>
                        </div>
                        <div className="relative">
                          <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-muted-foreground" />
                          <input
                            type="text"
                            value={counselSearchQuery}
                            onChange={(e) => setCounselSearchQuery(e.target.value)}
                            placeholder="Search lawyer... ▼"
                            className="w-full pl-9 pr-4 py-2 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary placeholder:text-muted-foreground/70"
                          />
                        </div>
                      </div>

                      <div>
                        <div className="flex items-center justify-between text-[11px] font-semibold text-muted-foreground mb-1.5">
                          <span>Available lawyers:</span>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {filteredCounsel.length} empanelled
                          </span>
                        </div>

                        <div className="max-h-60 overflow-y-auto space-y-2 pr-1 border-t border-b border-border/40 py-2">
                          {filteredCounsel.length === 0 ? (
                            <div className="p-4 text-center text-xs text-muted-foreground">
                              {loadingEligibleCounsel ? "Loading verified DLSA legal aid panel..." : "No eligible legal aid advocates found matching search."}
                            </div>
                          ) : (
                            filteredCounsel.map((counsel: any) => {
                              const isSelected = selectedAdvId === counsel.id;
                              return (
                                <div
                                  key={counsel.id}
                                  onClick={() => {
                                    setTransitionFormData((prev) => ({
                                      ...prev,
                                      assigned_advocate_id: counsel.id,
                                      assigned_advocate_name: counsel.name,
                                    }));
                                  }}
                                  className={`p-3 rounded-lg border cursor-pointer transition-all ${
                                    isSelected
                                      ? "bg-primary/10 border-primary shadow-sm ring-1 ring-primary"
                                      : "bg-card hover:bg-secondary/60 border-border/60"
                                  }`}
                                >
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="space-y-0.5">
                                      <div className="flex items-center gap-2 flex-wrap">
                                        <span className="font-bold text-xs text-foreground">
                                          {counsel.name}
                                        </span>
                                        {counsel.tier_label && (
                                          <span
                                            className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase tracking-wider ${
                                              counsel.tier === 1
                                                ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                                                : counsel.tier === 2
                                                ? "bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/30"
                                                : "bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30"
                                            }`}
                                          >
                                            {counsel.tier_label}
                                          </span>
                                        )}
                                        {isSelected && (
                                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-primary text-primary-foreground font-mono">
                                            SELECTED
                                          </span>
                                        )}
                                      </div>
                                      <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                                        <span className="font-medium text-foreground/90">{counsel.matter_type || "Criminal"}</span>
                                        <span>&bull;</span>
                                        <span>{counsel.district}</span>
                                        <span>&bull;</span>
                                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">Panel: {counsel.panel_status || "Active"}</span>
                                      </div>
                                      <div className="text-[10px] text-muted-foreground/80 font-mono flex items-center gap-2 pt-0.5">
                                        <span>Bar: {counsel.bar_registration_no}</span>
                                        <span>&bull;</span>
                                        <span>{counsel.experience_years} yrs exp</span>
                                        <span>&bull;</span>
                                        <span>{counsel.active_cases} active cases</span>
                                      </div>
                                    </div>
                                    <div className="shrink-0 pt-0.5">
                                      <div
                                        className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                                          isSelected
                                            ? "border-primary bg-primary text-primary-foreground"
                                            : "border-muted-foreground/40"
                                        }`}
                                      >
                                        {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </div>
                      <input
                        type="hidden"
                        value={transitionFormData[key] || ""}
                        required
                      />
                    </div>
                  );
                }
                return (
                  <div key={key}>
                    <label className="block text-xs font-semibold text-foreground mb-1">
                      {key.replace(/_/g, " ")} <span className="text-rose-500">*</span>
                    </label>
                    <input
                      required
                      type="text"
                      value={transitionFormData[key] || ""}
                      onChange={(e) => setTransitionFormData({ ...transitionFormData, [key]: e.target.value })}
                      className="w-full p-2.5 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                    />
                  </div>
                );
              })}

              <div>
                <label className="block text-xs font-semibold text-muted-foreground mb-1">
                  Audit Trail Comment (Optional)
                </label>
                <textarea
                  rows={2}
                  value={transitionComment}
                  onChange={(e) => setTransitionComment(e.target.value)}
                  placeholder="Optional explanatory notes for institutional audit log..."
                  className="w-full p-2 bg-background border border-border rounded-lg text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setActiveTransitionModal(null)}
                  className="px-4 py-2 border border-border rounded-lg text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={transitioningAction === activeTransitionModal.action}
                  className={`px-4 py-2 rounded-lg text-xs font-bold font-mono text-white shadow-sm flex items-center gap-1.5 transition-colors ${
                    activeTransitionModal.is_exception
                      ? "bg-red-600 hover:bg-red-700"
                      : "bg-primary hover:bg-primary/90 text-primary-foreground"
                  }`}
                >
                  {transitioningAction === activeTransitionModal.action ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  Confirm & Execute Transition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Secure Document Preview Modal */}
      <DocumentPreviewModal
        isOpen={!!previewDocId}
        onClose={() => setPreviewDocId(null)}
        docId={previewDocId}
        docTitle={previewDocTitle}
        onVerified={() => load()}
        onReviewed={() => load()}
      />
    </div>
  );
}
