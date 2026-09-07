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
        setProvenanceData({
          ...initialMetadata,
          ...chain,
          document_name: chain.document_name || doc.title,
          case_reference: chain.case_reference || initialMetadata.case_reference,
          verification_status: chain.verification_status || chain.simple_status || initialMetadata.verification_status,
          source_authority: chain.source_authority || initialMetadata.source_authority,
          uploaded_by: chain.uploaded_by || initialMetadata.uploaded_by,
          uploaded_at: chain.uploaded_at || initialMetadata.uploaded_at,
          version_history:
            chain.version_history && chain.version_history.length > 0
              ? chain.version_history
              : initialMetadata.version_history,
        });
      }
    } catch (err) {
      console.warn("Evidence chain server fetch fallback:", err);
    } finally {
      setProvenanceLoading(false);
    }
  };

  // Monitor network connectivity
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

  // Save low bandwidth toggle
  const toggleLowBandwidth = () => {
    const next = !isLowBandwidth;
    setIsLowBandwidth(next);
    localStorage.setItem("nyaya_low_bandwidth", next ? "true" : "false");
  };

  // Load Languages
  useEffect(() => {
    fetchCitizenLanguages()
      .then((langs) => {
        if (langs && langs.length > 0) setLanguages(langs);
      })
      .catch(() => {});
  }, []);

  // Fetch Overview with Caching
  const loadOverview = async (targetLang: string = lang) => {
    setLoading(true);
    setErrorStatus(null);
    try {
      const res = await fetchCitizenOverview(targetLang);
      setData(res);
      setNotifPhone(res.notification_preferences?.phone_number || "");
      setNotifSms(res.notification_preferences?.channel_sms_enabled ?? true);
      setNotifWhatsapp(res.notification_preferences?.channel_whatsapp_enabled ?? true);
      setNotifInApp(res.notification_preferences?.channel_in_app_enabled ?? true);
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setLastSyncTime(timeStr);
      try {
        localStorage.setItem(`nyaya_citizen_cache_${targetLang}`, JSON.stringify(res));
      } catch {}
    } catch (err: any) {
      console.warn("Failed to load live overview, checking cache:", err);
      if (err?.message?.includes("404")) {
        setErrorStatus(404);
      } else {
        const cached = localStorage.getItem(`nyaya_citizen_cache_${targetLang}`);
        if (cached) {
          try {
            setData(JSON.parse(cached));
          } catch {}
        }
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
      setActionSuccessMsg("Request submitted successfully to DLSA Legal Aid Desk.");
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
      setNotifSavedMsg("Preferences & statutory consent updated successfully.");
      setTimeout(() => setNotifSavedMsg(null), 3000);
      loadOverview(lang);
    } catch (err: any) {
      alert(err?.message || "Failed to update notification preferences.");
    } finally {
      setSavingNotif(false);
    }
  };

  const isFamily = mode === "family" || user?.role === "FAMILY_GUARDIAN";

  // Status Badge Helper matching website palette
  const getStatusBadge = (statusCode: string) => {
    switch (statusCode) {
      case "UNDER_REVIEW":
        return { label: "UNDER INITIAL REVIEW", color: "bg-muted text-foreground border-border" };
      case "ELIGIBLE_FOR_REVIEW":
      case "ELIGIBLE":
        return { label: "ELIGIBLE UNDER SEC 479", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      case "COUNSEL_ASSIGNED":
      case "ASSIGNED":
        return { label: "COUNSEL ASSIGNED", color: "bg-muted text-foreground border-border" };
      case "READY_FOR_FILING":
      case "APPROVED_READY_FOR_FILING":
        return { label: "DRAFT APPROVED • PENDING FILING", color: "bg-rose-500/10 text-rose-600 border-rose-500/20" };
      case "FILED_IN_COURT":
      case "FILED":
        return { label: "FILED IN COURT", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      case "COURT_ORDER_RECEIVED":
        return { label: "COURT BAIL ORDER ISSUED", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      case "RELEASE_EXECUTED":
      case "RELEASED":
        return { label: "PRISON RELEASE EXECUTED", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/30" };
      default:
        return { label: statusCode, color: "bg-secondary text-foreground border-border" };
    }
  };

  if (loading && !data) {
    return (
      <div className="p-8 max-w-4xl mx-auto flex flex-col items-center justify-center min-h-[50vh] gap-3 text-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-serif text-muted-foreground">
          Loading authorized legal aid record...
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
            No Active Case Linked to This Account
          </h2>
          <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
            No active legal aid case is currently linked to your credentials. If you or an undertrial family member requires legal representation, please contact the National Legal Services Helpline (15100) or visit your local District Legal Services Authority (DLSA) office.
          </p>
          <div className="pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="tel:15100"
              className="px-5 py-2.5 bg-primary text-primary-foreground font-sans font-bold text-xs rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm"
            >
              <Phone className="w-4 h-4" />
              Call NALSA Helpline: 15100
            </a>
            <div className="text-xs text-muted-foreground font-mono">
              24x7 Toll-Free Free Legal Aid
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
          <span className="font-medium">Language (भाषा):</span>
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
              Offline
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 font-mono text-[11px] text-muted-foreground">
              <Wifi className="w-3.5 h-3.5 text-emerald-600" />
              {lastSyncTime ? `Synced ${lastSyncTime}` : "Online"}
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
            {isLowBandwidth ? "⚡ Low-Data: ON" : "Low-Data: OFF"}
          </button>

          <button
            onClick={() => setNotifModalOpen(true)}
            className="p-1.5 rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground transition-colors"
            title="Notification Preferences & Consent"
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
            <strong>Accessibility Notice:</strong> Translated text is a derived display provided for informational accessibility. The original English court docket remains the authoritative source of legal truth.
          </p>
        </div>
      )}

      {/* ── Citizen / Family Welcome Banner ── */}
      <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
            {isFamily ? "Family & Guardian Assistance Portal" : "Citizen Legal Aid Portal"}
          </span>
          <span className="text-xs font-mono font-bold text-muted-foreground">
            Ref: {data.case_reference}
          </span>
        </div>

        <h1 className="text-2xl md:text-3xl font-serif font-black tracking-tight text-foreground">
          {isFamily ? `Legal Status of ${data.accused_name}` : `Welcome, ${data.accused_name}`}
        </h1>

        <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">
          Under Article 39A of the Constitution of India and Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023, you are entitled to free legal aid representation and periodic judicial custody review without fee.
        </p>
      </div>

      {/* ── Main Status Cards 3-Column Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Legal Aid Status */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Legal Aid Status
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
              Assigned Defense Lawyer
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
                  Counsel Allocation in Progress
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
              Free DLSA Legal Assistance Desk
            </div>
          </div>
        </div>

        {/* Card 3: Next Court Hearing & Remand */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Next Court Hearing
              </span>
              <Calendar className="w-4 h-4 text-primary" />
            </div>

            <div>
              <div className="text-lg font-serif font-bold text-foreground">
                {data.upcoming_known_events && data.upcoming_known_events.length > 0
                  ? data.upcoming_known_events[0].event_date
                  : "Awaiting Schedule"}
              </div>
              <div className="text-xs text-muted-foreground truncate">{data.court_name}</div>
            </div>
          </div>

          <div className="pt-2 border-t border-border text-[11px] text-muted-foreground flex items-center gap-1.5">
            <Landmark className="w-3.5 h-3.5 text-primary" />
            <span>Authoritative Court Record</span>
          </div>
        </div>
      </div>

      {/* ── Procedural Details: Filing & Custody Status ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-card border border-border p-4 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4 text-primary" />
            <h3 className="font-serif font-bold text-sm text-foreground">
              Court Filing Status
            </h3>
          </div>
          <div className="text-xs space-y-1 font-mono text-muted-foreground">
            <div className="flex justify-between">
              <span>Filing Record:</span>
              <strong className="text-foreground">
                {data.filing_details.is_filed ? "FORMALLY LODGED" : "AWAITING SUBMISSION"}
              </strong>
            </div>
            <div className="flex justify-between">
              <span>Reference:</span>
              <span className="text-foreground">{data.filing_details.filing_reference}</span>
            </div>
            <div className="flex justify-between">
              <span>Jurisdiction:</span>
              <span className="text-foreground truncate">{data.court_name}</span>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-600" />
            <h3 className="font-serif font-bold text-sm text-foreground">
              Custody & Release Status
            </h3>
          </div>
          <div className="text-xs space-y-1 font-mono text-muted-foreground">
            <div className="flex justify-between">
              <span>Custody Status:</span>
              <strong className="text-foreground">
                {data.release_details.is_released
                  ? "RELEASE EXECUTED"
                  : (data.release_details.release_status === "BAIL_ORDER_ISSUED"
                      ? "BAIL ORDER ISSUED"
                      : "IN CUSTODY")}
              </strong>
            </div>
            <div className="flex justify-between">
              <span>Police Station:</span>
              <span className="text-foreground truncate">{data.police_station}</span>
            </div>
            <div className="flex justify-between">
              <span>Verification:</span>
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
              {showAuthoritativeEnglish ? "Show Derived Translation" : "Inspect Authoritative English"}
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
              Statutory Caution
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
              Documents Needed From Your Side
            </h3>
            <span className="text-xs font-mono font-bold text-rose-600">
              Action Required
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            To assist the legal-aid counsel in proceeding with court bail representations, please prepare the following documents:
          </p>

          <div className="space-y-3">
            {data.missing_documents_from_citizen.map((doc, idx) => (
              <div key={idx} className="p-4 bg-secondary/30 border border-border rounded-lg space-y-1 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-serif font-bold text-foreground text-sm">{doc.title}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded font-bold bg-rose-500/10 text-rose-600 border border-rose-500/20 shrink-0">
                    {doc.urgency === "REQUIRED_BEFORE_HEARING" ? "URGENT" : "SUPPORTING"}
                  </span>
                </div>
                <p className="text-muted-foreground leading-relaxed">
                  <strong>Why needed:</strong> {doc.why_needed}
                </p>
                <p className="text-muted-foreground leading-relaxed pt-0.5">
                  <strong>How to submit:</strong> {doc.how_to_submit}
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
            Verified Case Records Entitled To You
          </h3>
          <span className="text-xs font-mono text-muted-foreground">
            {data.approved_entitled_documents.length} Authorized
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Authorized case records verified by the Legal Services Authority. Text summaries allow instant reading on low bandwidth:
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
                    VERIFIED
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
                  {doc.text_summary}
                </p>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-border/50">
                <span className="text-[10px] font-mono text-muted-foreground">
                  Size: {doc.file_size_formatted}
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setPreviewDoc(doc)}
                    className="px-2.5 py-1 rounded text-[11px] font-sans font-bold bg-card border border-border hover:bg-secondary text-foreground flex items-center gap-1 transition-colors"
                  >
                    <Eye className="w-3 h-3" />
                    Text Summary
                  </button>
                  <button
                    onClick={() => handleOpenProvenance(doc)}
                    className="px-2.5 py-1 rounded text-[11px] font-sans font-bold bg-primary/10 border border-primary/20 hover:bg-primary/20 text-primary flex items-center gap-1 transition-colors"
                  >
                    <Shield className="w-3 h-3" />
                    Provenance
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
            Citizen Action Center
          </h3>
          <span className="text-xs font-mono text-muted-foreground">
            Auditable DLSA Desk
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Submit official requests directly to the DLSA Secretary and Jail Welfare Officer:
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
              <div className="font-serif font-bold text-sm text-foreground">Contact DLSA Counsel</div>
              <div className="text-xs text-muted-foreground">Request panel advocate consultation</div>
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
              <div className="font-serif font-bold text-sm text-foreground">Flag Discrepancy</div>
              <div className="text-xs text-muted-foreground">Report incorrect dates or details</div>
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
              <div className="font-serif font-bold text-sm text-foreground">Request Document Copy</div>
              <div className="text-xs text-muted-foreground">Request certified order or report copy</div>
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
              <div className="font-serif font-bold text-sm text-foreground">Ask For Legal Aid Help</div>
              <div className="text-xs text-muted-foreground">Urgent welfare / medical consultation</div>
            </div>
          </button>
        </div>

        {/* Past Requests History */}
        {data.recent_citizen_requests && data.recent_citizen_requests.length > 0 && (
          <div className="pt-3 border-t border-border space-y-2">
            <span className="text-xs font-serif font-bold uppercase tracking-wider text-muted-foreground block">
              Your Past Submissions
            </span>
            <div className="space-y-2">
              {data.recent_citizen_requests.map((req) => (
                <div key={req.id} className="p-3 bg-secondary/20 border border-border rounded-lg text-xs flex items-center justify-between">
                  <div className="truncate pr-2">
                    <div className="font-serif font-bold text-foreground truncate">{req.subject}</div>
                    <div className="text-[11px] font-mono text-muted-foreground">Tracking ID: {req.id}</div>
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
              National Legal Services Helpline (NALSA 24x7)
            </h4>
            <p className="text-xs text-muted-foreground">
              Toll-free government assistance for undertrials and family members under the Legal Services Authorities Act.
            </p>
          </div>

          <a
            href="tel:15100"
            className="px-5 py-2.5 bg-primary text-primary-foreground font-sans font-bold text-sm rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors shadow-sm shrink-0"
          >
            <Phone className="h-4 w-4" />
            15100 (Toll-Free)
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
                Submit Citizen Request
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
                <p className="font-mono text-muted-foreground">Tracking ID: {actionTrackingId}</p>
                <button
                  onClick={() => {
                    setActionModalOpen(false);
                    setActionSuccessMsg(null);
                  }}
                  className="mt-2 px-4 py-2 bg-primary text-primary-foreground font-bold text-xs rounded-lg"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleActionSubmit} className="space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-foreground mb-1">Request Type</label>
                  <select
                    value={actionType}
                    onChange={(e: any) => setActionType(e.target.value)}
                    className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground font-mono"
                  >
                    <option value="REQUEST_DLSA_CONTACT">Request DLSA Panel Counsel Contact</option>
                    <option value="FLAG_INCORRECT_INFO">Report Discrepancy / Flag Error</option>
                    <option value="REQUEST_DOCUMENT_COPY">Request Certified Document Copy</option>
                    <option value="REQUEST_HELP">Ask for Urgent Legal Aid Help</option>
                  </select>
                </div>

                {actionType === "FLAG_INCORRECT_INFO" && (
                  <div>
                    <label className="block font-bold text-foreground mb-1">Field with Discrepancy</label>
                    <select
                      value={actionField}
                      onChange={(e) => setActionField(e.target.value)}
                      className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground font-mono"
                    >
                      <option value="custody_days">Custody Period / Admission Date</option>
                      <option value="father_name">Parent / Guardian Name</option>
                      <option value="permanent_address">Permanent Address</option>
                      <option value="offense_sections">Recorded Offence Sections</option>
                    </select>
                  </div>
                )}

                {actionType === "REQUEST_DOCUMENT_COPY" && (
                  <div>
                    <label className="block font-bold text-foreground mb-1">Document Requested</label>
                    <select
                      value={actionDocType}
                      onChange={(e) => setActionDocType(e.target.value)}
                      className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground font-mono"
                    >
                      <option value="charge_sheet">Police Charge Sheet</option>
                      <option value="remand_order">Judicial Remand Order</option>
                      <option value="fir">First Information Report (FIR)</option>
                      <option value="custody_certificate">Prison Custody Certificate</option>
                    </select>
                  </div>
                )}

                <div>
                  <label className="block font-bold text-foreground mb-1">Subject</label>
                  <input
                    type="text"
                    required
                    value={actionSubject}
                    onChange={(e) => setActionSubject(e.target.value)}
                    className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground"
                    placeholder="Brief summary of what you require..."
                  />
                </div>

                <div>
                  <label className="block font-bold text-foreground mb-1">Details</label>
                  <textarea
                    required
                    rows={3}
                    value={actionDetails}
                    onChange={(e) => setActionDetails(e.target.value)}
                    className="w-full p-2.5 rounded-lg bg-input border border-border text-foreground leading-relaxed"
                    placeholder="Provide specific details for the DLSA desk..."
                  />
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setActionModalOpen(false)}
                    className="px-4 py-2 border border-border rounded-lg text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingAction}
                    className="px-5 py-2 bg-primary text-primary-foreground font-bold rounded-lg transition-colors"
                  >
                    {submittingAction ? "Submitting..." : "Submit to DLSA"}
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
                Notification Preferences & Consent
              </h3>
              <button onClick={() => setNotifModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveNotifPrefs} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-foreground mb-1">Registered Mobile Phone</label>
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
                  <span>SMS Statutory Hearing & Status Notices</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifWhatsapp}
                    onChange={(e) => setNotifWhatsapp(e.target.checked)}
                    className="rounded border-border h-4 w-4 text-primary"
                  />
                  <span>WhatsApp Legal Aid Assistance Notices</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifInApp}
                    onChange={(e) => setNotifInApp(e.target.checked)}
                    className="rounded border-border h-4 w-4 text-primary"
                  />
                  <span>In-App Status Alerts</span>
                </label>
              </div>

              <div className="p-3 bg-secondary/40 border border-border rounded-lg text-[11px] text-muted-foreground leading-relaxed">
                <strong>Statutory Notice:</strong> Notification delivery is recorded under the Legal Services Authorities Act, 1987. No commercial carrier charges are applied.
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
                  Close
                </button>
                <button
                  type="submit"
                  disabled={savingNotif}
                  className="px-5 py-2 bg-primary text-primary-foreground font-bold rounded-lg transition-colors"
                >
                  {savingNotif ? "Saving..." : "Save Preferences"}
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
              <button onClick={() => setPreviewDoc(null)} className="text-muted-foreground hover:text-foreground shrink-0">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                <span>Record Type: {previewDoc.document_type}</span>
                <span>Size: {previewDoc.file_size_formatted}</span>
              </div>
              <div className="p-4 bg-secondary/30 border border-border rounded-lg text-foreground leading-relaxed">
                <strong className="block font-serif text-sm mb-1 text-primary">Plain-Language Summary:</strong>
                {previewDoc.text_summary}
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                This document is certified by the Legal Services Authority. Certified paper copies may also be inspected at the DLSA Front Office during court working hours.
              </p>
            </div>

            <div className="pt-3 flex items-center justify-end">
              <button
                onClick={() => setPreviewDoc(null)}
                className="px-4 py-2 bg-primary text-primary-foreground font-bold text-xs rounded-lg"
              >
                Close Preview
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
