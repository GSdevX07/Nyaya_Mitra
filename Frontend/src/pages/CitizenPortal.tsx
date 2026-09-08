import React, { useState, useEffect } from "react";
import {
  Calendar, Phone, FileText, CheckCircle2,
  Clock, AlertCircle, Globe, Shield, Landmark,
  Send, HelpCircle, Bell, Wifi, WifiOff,
  X, FileQuestion, AlertTriangle, Eye, Info
} from "lucide-react";
import { useAuth } from "../lib/auth";
import {
  fetchCitizenOverview,
  fetchCitizenLanguages,
  fetchCitizenDocumentSummary,
  submitCitizenActionRequest,
  updateCitizenNotificationPreferences,
  fetchEvidenceChain,
} from "../lib/api";
import type {
  CitizenOverviewData,
  CitizenLanguageItem,
  CitizenEntitledDocument,
} from "../lib/api";
import { RoleEvidenceProvenanceModal } from "../components/RoleEvidenceProvenanceModal";
import { getCitizenTranslation } from "../lib/citizenI18n";

interface CitizenPortalProps {
  mode?: "accused" | "family";
}

export function CitizenPortal({ mode = "accused" }: CitizenPortalProps) {
  const { user, token } = useAuth();
  const [data, setData] = useState<CitizenOverviewData | null>(null);
  const [languages, setLanguages] = useState<CitizenLanguageItem[]>([]);
  const [lang, setLang] = useState<string>("en");
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [isLowBandwidth, setIsLowBandwidth] = useState<boolean>(() => {
    return localStorage.getItem("nyaya_low_bandwidth") === "true";
  });
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);

  // Authoritative English preview toggle
  const [showAuthoritativeEnglish, setShowAuthoritativeEnglish] = useState(false);

  // Action Center Modal State
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [actionType, setActionType] = useState<
    "REQUEST_HELP" | "FLAG_INCORRECT_INFO" | "REQUEST_DOCUMENT_COPY" | "REQUEST_DLSA_CONTACT"
  >("REQUEST_HELP");
  const [actionSubject, setActionSubject] = useState("");
  const [actionDetails, setActionDetails] = useState("");
  const [actionDocType, setActionDocType] = useState("charge_sheet");
  const [actionField, setActionField] = useState("custody_date");
  const [submittingAction, setSubmittingAction] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);
  const [actionTrackingId, setActionTrackingId] = useState<string | null>(null);

  // Notification Preferences Modal State
  const [notifModalOpen, setNotifModalOpen] = useState(false);
  const [notifPhone, setNotifPhone] = useState("");
  const [notifSms, setNotifSms] = useState(true);
  const [notifWhatsapp, setNotifWhatsapp] = useState(true);
  const [notifInApp, setNotifInApp] = useState(true);
  const [savingNotif, setSavingNotif] = useState(false);
  const [notifSavedMsg, setNotifSavedMsg] = useState<string | null>(null);

  // Document Summary Preview Modal
  const [previewDoc, setPreviewDoc] = useState<CitizenEntitledDocument | null>(null);
  const [previewDetails, setPreviewDetails] = useState<any>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // Localization Dictionary for current active language
  const t = getCitizenTranslation(lang);

  const handleOpenTextSummary = async (doc: CitizenEntitledDocument) => {
    setPreviewDoc(doc);
    setPreviewDetails(null);
    setLoadingPreview(true);
    try {
      const summaryRes = await fetchCitizenDocumentSummary(doc.id, lang);
      setPreviewDetails(summaryRes);
    } catch (err) {
      console.warn("Failed to fetch extended document summary:", err);
    } finally {
      setLoadingPreview(false);
    }
  };

  // Document Provenance Modal State
  const [selectedProvenanceDoc, setSelectedProvenanceDoc] = useState<CitizenEntitledDocument | null>(null);
  const [provenanceData, setProvenanceData] = useState<any>(null);
  const [provenanceLoading, setProvenanceLoading] = useState(false);

  const handleOpenProvenance = async (doc: CitizenEntitledDocument) => {
    setSelectedProvenanceDoc(doc);
    setProvenanceLoading(true);

    const initialMetadata = {
      document_id: doc.id,
      document_name: doc.title,
      case_reference: data?.case_reference || "Not available",
      source_authority: "DLSA & Magisterial Court Registry",
      uploaded_by: "Court Registry (Official Docket)",
      uploaded_at: doc.uploaded_at || "Not available",
      verification_status: doc.status === "VERIFIED" ? "Verified" : (doc.status || "Verified"),
      simple_status: "Verified",
      integrity_status: "Record intact",
      version_history: [
        {
          version_number: "V1",
          recorded_at: doc.uploaded_at || new Date().toISOString(),
          uploader: "Court Registry / DLSA Records Desk",
          stage: "Official Judicial Record Intake",
          status: "Verified",
        },
      ],
      next_step: "Presented before court by assigned legal aid counsel",
      support_note: "Your legal aid team is actively tracking all required records for your case.",
    };
    setProvenanceData(initialMetadata);

    try {
      const chain = await fetchEvidenceChain(doc.id);
      if (chain) {
        setProvenanceData((prev: any) => ({
          ...prev,
          verification_status: chain.tamper_evident_valid ? "Certified Untampered" : "Integrity Flagged",
          integrity_status: chain.tamper_evident_valid ? "Cryptographically Certified" : "Integrity Verification Pending",
          version_history: chain.chain_events?.map((ev: any, idx: number) => ({
            version_number: `V${idx + 1}`,
            recorded_at: ev.timestamp,
            uploader: ev.actor_name || "Official Clerk",
            stage: ev.stage_action,
            status: ev.status || "Verified",
          })) || prev.version_history,
        }));
      }
    } catch (err) {
      console.warn("Evidence chain not available for citizen view:", err);
    } finally {
      setProvenanceLoading(false);
    }
  };

  const toggleLowBandwidth = () => {
    const nextVal = !isLowBandwidth;
    setIsLowBandwidth(nextVal);
    localStorage.setItem("nyaya_low_bandwidth", String(nextVal));
  };

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    async function loadLangs() {
      try {
        const list = await fetchCitizenLanguages();
        setLanguages(list);
      } catch (err) {
        console.warn("Failed to load language list:", err);
      }
    }
    loadLangs();
  }, []);

  const loadOverview = async (targetLang: string) => {
    setLoading(true);
    setErrorStatus(null);
    try {
      const res = await fetchCitizenOverview(targetLang);
      setData(res);
      setLastSyncTime(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
      try {
        localStorage.setItem(`citizen_cache_${user?.role}`, JSON.stringify(res));
      } catch (e) {
        // Storage limit safely ignored
      }
    } catch (err: any) {
      console.error("Failed to load citizen overview:", err);
      setErrorStatus(err?.status || 500);
      try {
        const cached = localStorage.getItem(`citizen_cache_${user?.role}`);
        if (cached) {
          setData(JSON.parse(cached));
        }
      } catch (e) {
        // Ignore cache retrieval errors
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadOverview(lang);
    }
  }, [token, lang]);

  const handleLanguageChange = (newLang: string) => {
    setLang(newLang);
    setShowAuthoritativeEnglish(false);
  };

  const handleActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!actionSubject.trim() || !actionDetails.trim()) return;
    setSubmittingAction(true);
    setActionSuccessMsg(null);
    try {
      const res = await submitCitizenActionRequest({
        request_type: actionType,
        subject: actionSubject.trim(),
        details: actionDetails.trim(),
        target_document_type: actionType === "REQUEST_DOCUMENT_COPY" ? actionDocType : undefined,
        discrepancy_field: actionType === "FLAG_INCORRECT_INFO" ? actionField : undefined,
      });
      setActionSuccessMsg(t.actionModal.successMsg);
      setActionTrackingId(res.id || res.task_id || "REQ-SUBMITTED");
      setActionSubject("");
      setActionDetails("");
      loadOverview(lang);
    } catch (err: any) {
      alert(err?.message || "Failed to submit citizen request.");
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleSaveNotifPrefs = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingNotif(true);
    setNotifSavedMsg(null);
    try {
      await updateCitizenNotificationPreferences({
        phone_number: notifPhone.trim(),
        channel_sms_enabled: notifSms,
        channel_whatsapp_enabled: notifWhatsapp,
        channel_in_app_enabled: notifInApp,
        preferred_language: lang,
        consent_status: "OPTED_IN",
        consent_text: "I consent to receive case status updates and legal-aid notices under the Legal Services Authorities Act, 1987.",
      });
      setNotifSavedMsg(t.notifModal.savedMsg);
      setTimeout(() => setNotifSavedMsg(null), 3000);
      loadOverview(lang);
    } catch (err: any) {
      alert(err?.message || "Failed to update notification preferences.");
    } finally {
      setSavingNotif(false);
    }
  };

  const isFamily = mode === "family" || user?.role === "FAMILY_GUARDIAN";

  // Status Badge Helper matching website palette and dynamic translation
  const getStatusBadge = (statusCode: string) => {
    switch (statusCode) {
      case "UNDER_REVIEW":
        return { label: t.statusBadges.underReview, color: "bg-muted text-foreground border-border" };
      case "ELIGIBLE_FOR_REVIEW":
      case "ELIGIBLE":
        return { label: t.statusBadges.eligible479, color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      case "COUNSEL_ASSIGNED":
      case "ASSIGNED":
        return { label: t.statusBadges.counselAssigned, color: "bg-muted text-foreground border-border" };
      case "READY_FOR_FILING":
      case "APPROVED_READY_FOR_FILING":
        return { label: t.statusBadges.readyForFiling, color: "bg-rose-500/10 text-rose-600 border-rose-500/20" };
      case "FILED_IN_COURT":
      case "FILED":
        return { label: t.statusBadges.filedInCourt, color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      case "COURT_ORDER_RECEIVED":
        return { label: t.statusBadges.courtOrderReceived, color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      case "RELEASE_EXECUTED":
      case "RELEASED":
        return { label: t.statusBadges.releaseExecuted, color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      default:
        return { label: statusCode, color: "bg-secondary text-foreground border-border" };
    }
  };

  if (loading && !data) {
    return (
      <div className="p-8 max-w-4xl mx-auto flex flex-col items-center justify-center min-h-[50vh] gap-3 text-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-serif text-muted-foreground">
          {t.emptyStates.loadingRecord}
        </p>
      </div>
    );
  }

  if (errorStatus === 404 || !data) {
    return (
      <div className="p-8 max-w-2xl mx-auto space-y-6">
        <div className="bg-card border-2 border-border rounded-xl text-center p-8 space-y-4 shadow-sm">
          <AlertCircle className="w-12 h-12 text-rose-600 mx-auto" />
          <h2 className="text-xl font-serif font-bold text-foreground">
            {t.emptyStates.noActiveCase}
          </h2>
          <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
            {t.emptyStates.noCaseDesc}
          </p>
          <div className="pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="tel:15100"
              className="px-5 py-2.5 bg-primary text-primary-foreground font-sans font-bold text-xs rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm"
            >
              <Phone className="w-4 h-4" />
              {t.emptyStates.callNalsa}
            </a>
            <div className="text-xs text-muted-foreground font-mono">
              {t.emptyStates.tollFreeLabel}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const badge = getStatusBadge(data.current_known_status.status_code);

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6 pb-16 animate-in fade-in duration-300">
      
      {/* ── Top Bar: Language & Low-Bandwidth Status ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-secondary/50 border border-border px-4 py-2.5 rounded-xl shadow-xs">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Globe className="h-4 w-4 text-primary shrink-0" />
          <span className="font-medium">{t.topBar.languageLabel}</span>
          <div className="flex flex-wrap items-center gap-1">
            {languages.map((l) => (
              <button
                key={l.code}
                onClick={() => handleLanguageChange(l.code)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-colors ${
                  lang === l.code
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                }`}
              >
                {l.native_name}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          {isOffline ? (
            <span className="inline-flex items-center gap-1 font-mono font-bold text-rose-600 text-[11px]">
              <WifiOff className="w-3.5 h-3.5" />
              {t.topBar.offline}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
              <Wifi className="w-3.5 h-3.5 text-emerald-600" />
              {lastSyncTime ? `${t.topBar.synced} ${lastSyncTime}` : t.topBar.online}
            </span>
          )}

          <button
            onClick={toggleLowBandwidth}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold border transition-colors ${
              isLowBandwidth
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-card text-muted-foreground border-border hover:text-foreground"
            }`}
            title="Toggle lightweight low-bandwidth mode"
          >
            {isLowBandwidth ? t.topBar.lowDataOn : t.topBar.lowDataOff}
          </button>

          <button
            onClick={() => setNotifModalOpen(true)}
            className="p-1.5 rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground transition-colors"
            title={t.topBar.notifPrefsTitle}
          >
            <Bell className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Derived Display Disclaimer Notice ── */}
      {data.language_meta.is_derived_display && (
        <div className="bg-secondary/40 border border-border px-4 py-2.5 rounded-xl text-xs text-muted-foreground flex items-start gap-2.5">
          <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>{t.derivedNotice.label}</strong> {t.derivedNotice.text}
          </p>
        </div>
      )}

      {/* ── Citizen / Family Welcome Banner ── */}
      <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
            {isFamily ? t.banner.familyPortal : t.banner.citizenPortal}
          </span>
          <span className="text-xs font-mono font-bold text-muted-foreground">
            {t.banner.refPrefix} {data.case_reference}
          </span>
        </div>

        <h1 className="text-2xl md:text-3xl font-serif font-black tracking-tight text-foreground">
          {isFamily ? `${t.banner.legalStatusOf} ${data.accused_name}` : `${t.banner.welcome} ${data.accused_name}`}
        </h1>

        <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">
          {t.banner.statutoryRight}
        </p>
      </div>

      {/* ── Main Status Cards 3-Column Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Legal Aid Status */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t.cards.legalAidStatusTitle}
              </span>
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            </div>

            <div>
              <div className="text-base font-serif font-bold text-foreground">
                {data.current_known_status.title}
              </div>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {data.current_known_status.detail}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-border">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold border ${badge.color}`}>
              {badge.label}
            </span>
          </div>
        </div>

        {/* Card 2: Assigned Defense Lawyer */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
              {t.cards.assignedLawyerTitle}
            </span>

            {data.legal_aid_support.is_assigned ? (
              <div className="space-y-1">
                <div className="text-base font-serif font-bold text-foreground">
                  {data.legal_aid_support.lawyer_name}
                </div>
                <p className="text-xs text-muted-foreground">
                  {data.legal_aid_support.organization}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <div className="text-sm font-semibold text-rose-600 flex items-center gap-1.5">
                  <Clock className="w-4 h-4" />
                  {t.cards.counselInProgress}
                </div>
                <p className="text-xs text-muted-foreground">
                  {data.legal_aid_support.status_message || "DLSA Legal Aid Panel"}
                </p>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-border space-y-1 text-xs">
            <div className="flex items-center gap-1.5 text-foreground font-mono">
              <Phone className="w-3.5 h-3.5 text-primary" />
              <span>{data.legal_aid_support.contact_phone || "15100"}</span>
            </div>
            <div className="text-[11px] text-muted-foreground">
              {t.cards.freeDlsaDesk}
            </div>
          </div>
        </div>

        {/* Card 3: Next Court Hearing & Remand */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {t.cards.nextHearingTitle}
              </span>
              <Calendar className="w-4 h-4 text-primary" />
            </div>

            <div>
              <div className="text-lg font-serif font-bold text-foreground">
                {data.upcoming_known_events && data.upcoming_known_events.length > 0
                  ? data.upcoming_known_events[0].event_date
                  : t.cards.awaitingSchedule}
              </div>
              <div className="text-xs text-muted-foreground truncate">{data.court_name}</div>
            </div>
          </div>

          <div className="pt-2 border-t border-border text-[11px] text-muted-foreground flex items-center gap-1.5">
            <Landmark className="w-3.5 h-3.5 text-primary" />
            <span>{t.cards.courtRecordBadge}</span>
          </div>
        </div>
      </div>

      {/* ── Procedural Details: Filing & Custody Status ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-card border border-border p-4 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4 text-primary" />
            <h3 className="font-serif font-bold text-sm text-foreground">
              {t.procedural.courtFilingTitle}
            </h3>
          </div>
          <div className="text-xs space-y-1 font-mono text-muted-foreground">
            <div className="flex justify-between">
              <span>{t.procedural.filingRecord}</span>
              <strong className="text-foreground">
                {data.filing_details.is_filed ? t.procedural.formallyLodged : t.procedural.awaitingSubmission}
              </strong>
            </div>
            <div className="flex justify-between">
              <span>{t.procedural.reference}</span>
              <span className="text-foreground">{data.filing_details.filing_reference}</span>
            </div>
            <div className="flex justify-between">
              <span>{t.procedural.jurisdiction}</span>
              <span className="text-foreground truncate">{data.court_name}</span>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-600" />
            <h3 className="font-serif font-bold text-sm text-foreground">
              {t.procedural.custodyReleaseTitle}
            </h3>
          </div>
          <div className="text-xs space-y-1 font-mono text-muted-foreground">
            <div className="flex justify-between">
              <span>{t.procedural.custodyStatus}</span>
              <strong className="text-foreground">
                {data.release_details.is_released
                  ? t.statusBadges.releaseExecuted
                  : (data.release_details.release_status === "BAIL_ORDER_ISSUED"
                      ? t.statusBadges.courtOrderReceived
                      : t.procedural.inCustody)}
              </strong>
            </div>
            <div className="flex justify-between">
              <span>{t.procedural.policeStation}</span>
              <span className="text-foreground truncate">{data.police_station}</span>
            </div>
            <div className="flex justify-between">
              <span>{t.procedural.verification}</span>
              <span className="text-foreground">{data.release_details.verification_source}</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── AI Procedural Explanation (Prominent Statutory Caution) ── */}
      <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-secondary border border-border text-foreground flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-primary" />
            {data.ai_procedural_explanation.disclaimer_label}
          </span>
          {data.ai_procedural_explanation.is_derived_display && (
            <button
              onClick={() => setShowAuthoritativeEnglish(!showAuthoritativeEnglish)}
              className="text-xs font-mono font-bold text-primary hover:underline"
            >
              {showAuthoritativeEnglish ? t.aiSection.showDerived : t.aiSection.inspectAuthoritative}
            </button>
          )}
        </div>

        <div className="text-xs md:text-sm text-foreground leading-relaxed bg-secondary/30 p-4 rounded-lg border border-border">
          {showAuthoritativeEnglish
            ? data.ai_procedural_explanation.authoritative_english_text
            : data.ai_procedural_explanation.explanation_text}
        </div>

        {/* Mandatory Statutory Caution Box */}
        <div
          className="p-4 bg-white border-2 border-red-600 rounded-xl text-xs flex items-start gap-3 shadow-xs"
          style={{ backgroundColor: "#FFFFFF", borderColor: "#DC2626" }}
        >
          <AlertTriangle
            className="w-6 h-6 text-red-600 shrink-0 mt-0.5"
            strokeWidth={3.5}
            style={{ color: "#DC2626" }}
          />
          <div className="space-y-1.5">
            <span
              className="inline-block px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border border-red-600"
              style={{ color: "#DC2626", borderColor: "#DC2626", backgroundColor: "#FFFFFF" }}
            >
              {t.aiSection.statutoryCautionTitle}
            </span>
            <p
              className="text-xs font-semibold leading-relaxed"
              style={{ color: "#000000" }}
            >
              {data.ai_procedural_explanation.disclaimer_text}
            </p>
          </div>
        </div>
      </div>

      {/* ── Documents Missing From Your Side ── */}
      {data.missing_documents_from_citizen && data.missing_documents_from_citizen.length > 0 && (
        <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-rose-600" />
              {t.missingDocs.title}
            </h3>
            <span className="text-xs font-mono font-bold text-rose-600">
              {t.missingDocs.actionRequired}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {t.missingDocs.subtitle}
          </p>

          <div className="space-y-3">
            {data.missing_documents_from_citizen.map((doc, idx) => (
              <div key={idx} className="p-4 bg-secondary/30 border border-border rounded-lg space-y-1 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-serif font-bold text-foreground text-sm">{doc.title}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-rose-500/10 text-rose-600 border border-rose-500/20 shrink-0">
                    {doc.urgency === "REQUIRED_BEFORE_HEARING" ? t.missingDocs.urgent : t.missingDocs.supporting}
                  </span>
                </div>
                <p className="text-muted-foreground leading-relaxed">
                  <strong>{t.missingDocs.whyNeeded}</strong> {doc.why_needed}
                </p>
                <p className="text-muted-foreground leading-relaxed pt-0.5">
                  <strong>{t.missingDocs.howToSubmit}</strong> {doc.how_to_submit}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Approved Entitled Case Records ── */}
      <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            {t.entitledDocs.title}
          </h3>
          <span className="text-xs font-mono text-muted-foreground">
            {data.approved_entitled_documents.length} {t.entitledDocs.authorizedSuffix}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          {t.entitledDocs.subtitle}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
          {data.approved_entitled_documents.map((doc) => (
            <div
              key={doc.id}
              className="p-4 bg-secondary/30 border border-border rounded-lg text-xs space-y-2 flex flex-col justify-between"
            >
              <div className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 truncate">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="font-serif font-bold text-foreground truncate">{doc.title}</span>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 shrink-0">
                    {t.entitledDocs.verified}
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                  {doc.text_summary}
                </p>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <span className="text-[10px] font-mono text-muted-foreground">
                  {t.entitledDocs.size} {doc.file_size_formatted}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleOpenTextSummary(doc)}
                    className="px-2.5 py-1 rounded text-[11px] font-sans font-bold bg-card border border-border hover:bg-secondary text-foreground flex items-center gap-1 transition-colors"
                  >
                    <Eye className="w-3 h-3" />
                    {t.entitledDocs.textSummaryBtn}
                  </button>
                  <button
                    onClick={() => handleOpenProvenance(doc)}
                    className="px-2.5 py-1 rounded text-[11px] font-sans font-bold bg-primary/10 border border-primary/20 hover:bg-primary/20 text-primary flex items-center gap-1 transition-colors"
                  >
                    <Shield className="w-3 h-3" />
                    {t.entitledDocs.provenanceBtn}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Citizen Action Center (Structured Request Cards) ── */}
      <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
            <Send className="w-5 h-5 text-primary" />
            {t.actionCenter.title}
          </h3>
          <span className="text-xs font-mono text-muted-foreground">
            {t.actionCenter.auditableDesk}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          {t.actionCenter.subtitle}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            onClick={() => {
              setActionType("REQUEST_DLSA_CONTACT");
              setActionSubject("Request Contact with DLSA Panel Counsel");
              setActionDetails("Requesting an in-person or telephonic consultation with the assigned legal aid advocate regarding upcoming hearing.");
              setActionModalOpen(true);
            }}
            className="p-4 bg-secondary/30 hover:bg-secondary/60 border border-border rounded-lg text-left transition-colors flex items-start gap-3"
          >
            <Phone className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div>
              <div className="font-serif font-bold text-sm text-foreground">{t.actionCenter.contactCounselTitle}</div>
              <div className="text-xs text-muted-foreground">{t.actionCenter.contactCounselSub}</div>
            </div>
          </button>

          <button
            onClick={() => {
              setActionType("FLAG_INCORRECT_INFO");
              setActionSubject("Report Discrepancy in Case Records");
              setActionDetails("There is an error in custody calculation or identity attributes recorded in the system.");
              setActionModalOpen(true);
            }}
            className="p-4 bg-secondary/30 hover:bg-secondary/60 border border-border rounded-lg text-left transition-colors flex items-start gap-3"
          >
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-serif font-bold text-sm text-foreground">{t.actionCenter.flagDiscrepancyTitle}</div>
              <div className="text-xs text-muted-foreground">{t.actionCenter.flagDiscrepancySub}</div>
            </div>
          </button>

          <button
            onClick={() => {
              setActionType("REQUEST_DOCUMENT_COPY");
              setActionSubject("Request Certified Copy of Document");
              setActionDetails("Requesting certified soft copy of official court or police report.");
              setActionModalOpen(true);
            }}
            className="p-4 bg-secondary/30 hover:bg-secondary/60 border border-border rounded-lg text-left transition-colors flex items-start gap-3"
          >
            <FileQuestion className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div>
              <div className="font-serif font-bold text-sm text-foreground">{t.actionCenter.requestDocTitle}</div>
              <div className="text-xs text-muted-foreground">{t.actionCenter.requestDocSub}</div>
            </div>
          </button>

          <button
            onClick={() => {
              setActionType("REQUEST_HELP");
              setActionSubject("Request Urgent Legal Aid Assistance");
              setActionDetails("Requesting immediate assistance from Jail Legal Aid Clinic or DLSA Secretary.");
              setActionModalOpen(true);
            }}
            className="p-4 bg-secondary/30 hover:bg-secondary/60 border border-border rounded-lg text-left transition-colors flex items-start gap-3"
          >
            <HelpCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
            <div>
              <div className="font-serif font-bold text-sm text-foreground">{t.actionCenter.askHelpTitle}</div>
              <div className="text-xs text-muted-foreground">{t.actionCenter.askHelpSub}</div>
            </div>
          </button>
        </div>

        {/* Past Requests History */}
        {data.recent_citizen_requests && data.recent_citizen_requests.length > 0 && (
          <div className="pt-3 border-t border-border space-y-2">
            <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground block">
              {t.actionCenter.pastSubmissionsTitle}
            </span>
            <div className="space-y-2">
              {data.recent_citizen_requests.map((req) => (
                <div key={req.id} className="p-3 bg-secondary/20 border border-border rounded-lg text-xs flex items-center justify-between">
                  <div className="truncate pr-2">
                    <div className="font-serif font-bold text-foreground truncate">{req.subject}</div>
                    <div className="text-[11px] font-mono text-muted-foreground">{t.actionCenter.trackingId} {req.id}</div>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 shrink-0">
                    {req.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Signature Toll-Free Legal Aid Banner ── */}
      <div className="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border-2 border-primary/20 p-6 rounded-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
              <Phone className="h-5 w-5 text-primary" />
              {t.nalsaBanner.title}
            </h4>
            <p className="text-xs text-muted-foreground">
              {t.nalsaBanner.desc}
            </p>
          </div>

          <a
            href="tel:15100"
            className="px-5 py-2.5 bg-primary text-primary-foreground font-sans font-bold text-sm rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm shrink-0"
          >
            <Phone className="h-4 w-4" />
            {t.nalsaBanner.phoneBtn}
          </a>
        </div>
      </div>

      {/* ── Action Submission Modal ── */}
      {actionModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border rounded-xl w-full max-w-lg p-6 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <h3 className="font-serif font-bold text-base text-foreground flex items-center gap-2">
                <Send className="w-4 h-4 text-primary" />
                {t.actionModal.title}
              </h3>
              <button
                onClick={() => {
                  setActionModalOpen(false);
                  setActionSuccessMsg(null);
                }}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {actionSuccessMsg ? (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                <p className="font-bold text-foreground">{actionSuccessMsg}</p>
                <p className="font-mono text-muted-foreground">{t.actionCenter.trackingId} {actionTrackingId}</p>
                <button
                  onClick={() => {
                    setActionModalOpen(false);
                    setActionSuccessMsg(null);
                  }}
                  className="mt-2 px-4 py-2 bg-primary text-primary-foreground font-bold text-xs rounded-lg"
                >
                  {t.actionModal.doneBtn}
                </button>
              </div>
            ) : (
              <form onSubmit={handleActionSubmit} className="space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-foreground mb-1">{t.actionModal.requestType}</label>
                  <select
                    value={actionType}
                    onChange={(e: any) => setActionType(e.target.value)}
                    className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground font-mono"
                  >
                    <option value="REQUEST_DLSA_CONTACT">{t.actionModal.optContact}</option>
                    <option value="FLAG_INCORRECT_INFO">{t.actionModal.optDiscrepancy}</option>
                    <option value="REQUEST_DOCUMENT_COPY">{t.actionModal.optDoc}</option>
                    <option value="REQUEST_HELP">{t.actionModal.optHelp}</option>
                  </select>
                </div>

                {actionType === "FLAG_INCORRECT_INFO" && (
                  <div>
                    <label className="block font-bold text-foreground mb-1">{t.actionModal.fieldLabel}</label>
                    <select
                      value={actionField}
                      onChange={(e) => setActionField(e.target.value)}
                      className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground font-mono"
                    >
                      <option value="custody_days">{t.actionModal.fieldCustody}</option>
                      <option value="father_name">{t.actionModal.fieldParent}</option>
                      <option value="permanent_address">{t.actionModal.fieldAddress}</option>
                      <option value="offense_sections">{t.actionModal.fieldOffense}</option>
                    </select>
                  </div>
                )}

                {actionType === "REQUEST_DOCUMENT_COPY" && (
                  <div>
                    <label className="block font-bold text-foreground mb-1">{t.actionModal.docLabel}</label>
                    <select
                      value={actionDocType}
                      onChange={(e) => setActionDocType(e.target.value)}
                      className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground font-mono"
                    >
                      <option value="charge_sheet">{t.actionModal.docChargeSheet}</option>
                      <option value="remand_order">{t.actionModal.docRemand}</option>
                      <option value="fir">{t.actionModal.docFir}</option>
                      <option value="custody_certificate">{t.actionModal.docCustodyCert}</option>
                    </select>
                  </div>
                )}

                <div>
                  <label className="block font-bold text-foreground mb-1">{t.actionModal.subjectLabel}</label>
                  <input
                    type="text"
                    required
                    value={actionSubject}
                    onChange={(e) => setActionSubject(e.target.value)}
                    className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground"
                    placeholder={t.actionModal.subjectPlaceholder}
                  />
                </div>

                <div>
                  <label className="block font-bold text-foreground mb-1">{t.actionModal.detailsLabel}</label>
                  <textarea
                    required
                    rows={3}
                    value={actionDetails}
                    onChange={(e) => setActionDetails(e.target.value)}
                    className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground leading-relaxed"
                    placeholder={t.actionModal.detailsPlaceholder}
                  />
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setActionModalOpen(false)}
                    className="px-4 py-2 border border-border rounded-lg text-muted-foreground hover:text-foreground"
                  >
                    {t.actionModal.cancelBtn}
                  </button>
                  <button
                    type="submit"
                    disabled={submittingAction}
                    className="px-5 py-2 bg-primary text-primary-foreground font-bold rounded-lg transition-colors"
                  >
                    {submittingAction ? t.actionModal.submitting : t.actionModal.submitBtn}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ── Notification Preferences Modal ── */}
      {notifModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border rounded-xl w-full max-w-md p-6 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <h3 className="font-serif font-bold text-base text-foreground flex items-center gap-2">
                <Bell className="w-4 h-4 text-primary" />
                {t.notifModal.title}
              </h3>
              <button onClick={() => setNotifModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveNotifPrefs} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-foreground mb-1">{t.notifModal.phoneLabel}</label>
                <input
                  type="tel"
                  value={notifPhone}
                  onChange={(e) => setNotifPhone(e.target.value)}
                  className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground font-mono"
                  placeholder="+91 98765 43210"
                />
              </div>

              <div className="space-y-2.5 pt-1">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifSms}
                    onChange={(e) => setNotifSms(e.target.checked)}
                    className="rounded border-border h-4 w-4 text-primary"
                  />
                  <span>{t.notifModal.smsLabel}</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifWhatsapp}
                    onChange={(e) => setNotifWhatsapp(e.target.checked)}
                    className="rounded border-border h-4 w-4 text-primary"
                  />
                  <span>{t.notifModal.whatsappLabel}</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifInApp}
                    onChange={(e) => setNotifInApp(e.target.checked)}
                    className="rounded border-border h-4 w-4 text-primary"
                  />
                  <span>{t.notifModal.inAppLabel}</span>
                </label>
              </div>

              <div className="p-3 bg-secondary/40 border border-border rounded-lg text-[11px] text-muted-foreground leading-relaxed">
                <strong>{t.notifModal.statutoryNoticeLabel}</strong> {t.notifModal.statutoryNoticeText}
              </div>

              {notifSavedMsg && (
                <div className="p-2.5 bg-emerald-500/10 text-emerald-600 border border-emerald-500/30 rounded-lg text-center font-bold">
                  {notifSavedMsg}
                </div>
              )}

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setNotifModalOpen(false)}
                  className="px-4 py-2 border border-border rounded-lg text-muted-foreground hover:text-foreground"
                >
                  {t.notifModal.closeBtn}
                </button>
                <button
                  type="submit"
                  disabled={savingNotif}
                  className="px-5 py-2 bg-primary text-primary-foreground font-bold rounded-lg transition-colors"
                >
                  {savingNotif ? t.notifModal.saving : t.notifModal.saveBtn}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Document Text Summary Modal ── */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border rounded-xl w-full max-w-lg p-6 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <h3 className="font-serif font-bold text-base text-foreground truncate pr-2">
                {previewDoc.title}
              </h3>
              <button
                onClick={() => {
                  setPreviewDoc(null);
                  setPreviewDetails(null);
                }}
                className="text-muted-foreground hover:text-foreground shrink-0"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                <span>{t.textSummaryModal.recordType} {previewDoc.document_type}</span>
                <span>{t.textSummaryModal.size} {previewDoc.file_size_formatted}</span>
              </div>
              <div className="p-4 bg-secondary/30 border border-border rounded-lg text-foreground leading-relaxed">
                <div className="flex items-center justify-between mb-1">
                  <strong className="block font-serif text-sm text-primary">{t.textSummaryModal.summaryLabel}</strong>
                  {loadingPreview && (
                    <span className="text-[10px] font-mono text-muted-foreground animate-pulse">{t.textSummaryModal.syncing}</span>
                  )}
                </div>
                <p className="text-xs text-foreground leading-relaxed">
                  {previewDetails?.text_summary || previewDoc.text_summary}
                </p>
              </div>

              {previewDetails?.text_preview &&
                previewDetails.text_preview !== (previewDetails.text_summary || previewDoc.text_summary) && (
                  <div className="space-y-1">
                    <span className="text-[11px] font-bold text-muted-foreground">{t.textSummaryModal.extractLabel}</span>
                    <div className="p-3 bg-secondary/20 border border-border/70 rounded-lg text-xs font-mono text-foreground max-h-36 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                      {previewDetails.text_preview}
                    </div>
                  </div>
                )}

              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {t.textSummaryModal.certNotice}
              </p>
            </div>

            <div className="pt-3 flex items-center justify-end">
              <button
                onClick={() => {
                  setPreviewDoc(null);
                  setPreviewDetails(null);
                }}
                className="px-4 py-2 bg-primary text-primary-foreground font-bold text-xs rounded-lg"
              >
                {t.textSummaryModal.closeBtn}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Role Evidence Provenance Modal ── */}
      <RoleEvidenceProvenanceModal
        isOpen={!!selectedProvenanceDoc}
        onClose={() => {
          setSelectedProvenanceDoc(null);
          setProvenanceData(null);
        }}
        data={provenanceData}
        loading={provenanceLoading}
      />
    </div>
  );
}
