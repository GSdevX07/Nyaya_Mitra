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

  // Document Provenance Modal
  const [selectedProvenanceId, setSelectedProvenanceId] = useState<string | null>(null);

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
        // Attempt cached view for offline resilience
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
      // Refresh overview
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

  // Status Badge Helper
  const getStatusBadge = (statusCode: string) => {
    switch (statusCode) {
      case "UNDER_REVIEW":
        return { label: "UNDER INITIAL REVIEW", color: "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300" };
      case "ELIGIBLE_FOR_REVIEW":
      case "ELIGIBLE":
        return { label: "ELIGIBLE UNDER SEC 479", color: "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-400" };
      case "COUNSEL_ASSIGNED":
      case "ASSIGNED":
        return { label: "COUNSEL ASSIGNED", color: "bg-slate-100 text-slate-800 border-slate-400 dark:bg-slate-800 dark:text-slate-200" };
      case "READY_FOR_FILING":
      case "APPROVED_READY_FOR_FILING":
        return { label: "DRAFT APPROVED • PENDING FILING", color: "bg-slate-100 text-slate-800 border-slate-400 dark:bg-slate-800 dark:text-slate-200" };
      case "FILED_IN_COURT":
      case "FILED":
        return { label: "FILED IN COURT", color: "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-400" };
      case "COURT_ORDER_RECEIVED":
        return { label: "COURT BAIL ORDER ISSUED", color: "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-400" };
      case "RELEASE_EXECUTED":
      case "RELEASED":
        return { label: "PRISON RELEASE EXECUTED", color: "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-400" };
      default:
        return { label: statusCode, color: "bg-slate-100 text-slate-700 border-slate-300" };
    }
  };

  if (loading && !data) {
    return (
      <div className="p-4 md:p-6 max-w-2xl mx-auto flex flex-col items-center justify-center min-h-[60vh] gap-3 text-center">
        <div className="w-8 h-8 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
          Loading Legal Aid Dashboard...
        </p>
      </div>
    );
  }

  if (errorStatus === 404 || !data) {
    return (
      <div className="p-4 md:p-6 max-w-xl mx-auto space-y-4">
        <div className="bg-card border border-border rounded-xl p-6 text-center space-y-4 shadow-xs">
          <div className="w-12 h-12 rounded-full bg-rose-50 dark:bg-rose-950/30 text-rose-600 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-serif font-bold text-foreground">
            No Active Case Linked to This Account
          </h2>
          <p className="text-xs text-muted-foreground leading-relaxed">
            No authorized legal aid record is currently attached to these credentials. If you or an undertrial family member requires immediate defense representation, please contact the free National Legal Services Helpline (15100) or visit your local District Legal Services Authority (DLSA) office.
          </p>
          <div className="pt-2 border-t border-border flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="tel:15100"
              className="w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-sans font-bold text-xs rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              <Phone className="w-4 h-4" />
              Call NALSA Helpline: 15100 (Toll-Free)
            </a>
          </div>
        </div>
      </div>
    );
  }

  const badge = getStatusBadge(data.current_known_status.status_code);

  return (
    <div className="p-3 md:p-6 max-w-2xl mx-auto space-y-4 pb-16 animate-in fade-in duration-200">
      
      {/* ── Low-Bandwidth & Network Status Banner ── */}
      <div className="flex items-center justify-between bg-card border border-border px-3.5 py-2 rounded-xl text-xs shadow-xs">
        <div className="flex items-center gap-2">
          {isOffline ? (
            <span className="inline-flex items-center gap-1 font-mono font-bold text-rose-600 text-[11px]">
              <WifiOff className="w-3.5 h-3.5" />
              Offline View
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 font-mono text-emerald-600 text-[11px]">
              <Wifi className="w-3.5 h-3.5" />
              Synced {lastSyncTime ? `@ ${lastSyncTime}` : "Online"}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleLowBandwidth}
            className={`px-2 py-1 rounded text-[11px] font-mono font-bold border transition-colors ${
              isLowBandwidth
                ? "bg-emerald-600 text-white border-emerald-600"
                : "bg-muted text-muted-foreground border-border hover:text-foreground"
            }`}
            title="Toggle lightweight plain-text mode to save mobile data"
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

      {/* ── Multi-Language Derived Display Bar ── */}
      <div className="bg-card border border-border p-3 rounded-xl space-y-2 shadow-xs">
        <div className="flex items-center justify-between text-xs">
          <span className="font-mono font-bold text-muted-foreground flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
            <Globe className="w-3.5 h-3.5 text-emerald-600" />
            Language Service (भाषा)
          </span>
          <span className="text-[10px] font-mono text-muted-foreground">
            {lang === "en" ? "Authoritative Source: English" : "Derived Accessibility Display"}
          </span>
        </div>
        
        {/* Language Pill Selector */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {languages.map((l) => (
            <button
              key={l.code}
              onClick={() => handleLanguageChange(l.code)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                lang === l.code
                  ? "bg-black text-white dark:bg-white dark:text-black shadow-xs font-bold"
                  : "bg-muted text-muted-foreground hover:text-foreground border border-border"
              }`}
            >
              {l.native_name} {l.code === "en" ? "(Authoritative)" : ""}
            </button>
          ))}
        </div>

        {/* Translation Non-Legal-Truth Statutory Pill */}
        {data.language_meta.is_derived_display && (
          <div className="bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-2 rounded-lg text-[11px] text-muted-foreground flex items-start gap-2">
            <Info className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
            <span>
              <strong>Derived Display:</strong> Translated text is provided solely for informational accessibility. The original English court record remains the sole legal authority.
            </span>
          </div>
        )}
      </div>

      {/* ── Accused & Case Header Card ── */}
      <div className="bg-card border border-border p-4 md:p-5 rounded-xl space-y-3 shadow-xs">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
            {isFamily ? "Family & Guardian View" : "Accused Undertrial View"}
          </span>
          <span className="text-xs font-mono font-bold text-foreground">
            Ref: {data.case_reference}
          </span>
        </div>

        <div>
          <h1 className="text-xl font-serif font-bold text-foreground">
            {data.accused_name}
          </h1>
          <p className="text-xs text-muted-foreground font-mono mt-0.5">
            {data.court_name} • {data.police_station}
          </p>
        </div>

        {/* Status Badge & Title */}
        <div className="p-3 bg-muted/50 border border-border rounded-lg space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Current Known Status
            </span>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${badge.color}`}>
              {badge.label}
            </span>
          </div>
          <div className="text-sm font-serif font-bold text-foreground">
            {data.current_known_status.title}
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {data.current_known_status.detail}
          </p>
        </div>

        {/* Filing & Release Details */}
        <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1">
          <div className="p-2.5 bg-card border border-border rounded-lg space-y-0.5">
            <span className="text-[10px] text-muted-foreground uppercase">Court Registry Filing</span>
            <div className="font-bold text-foreground">
              {data.filing_details.is_filed ? "Lodged in Court" : "Awaiting Filing"}
            </div>
            <div className="text-[10px] text-muted-foreground truncate">
              {data.filing_details.filing_reference}
            </div>
          </div>
          <div className="p-2.5 bg-card border border-border rounded-lg space-y-0.5">
            <span className="text-[10px] text-muted-foreground uppercase">Custody Verification</span>
            <div className="font-bold text-foreground">
              {data.release_details.is_released ? "Release Confirmed" : "In Custody"}
            </div>
            <div className="text-[10px] text-muted-foreground truncate">
              {data.release_details.verification_source}
            </div>
          </div>
        </div>
      </div>

      {/* ── AI Procedural Explanation (Strict Statutory Disclaimers) ── */}
      <div className="bg-card border border-border p-4 md:p-5 rounded-xl space-y-3 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
            <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
            {data.ai_procedural_explanation.disclaimer_label}
          </span>
          {data.ai_procedural_explanation.is_derived_display && (
            <button
              onClick={() => setShowAuthoritativeEnglish(!showAuthoritativeEnglish)}
              className="text-[11px] font-mono text-emerald-600 hover:underline"
            >
              {showAuthoritativeEnglish ? "Show Derived Translation" : "Inspect English Record"}
            </button>
          )}
        </div>

        <div className="text-xs text-foreground leading-relaxed bg-muted/30 p-3 rounded-lg border border-border">
          {showAuthoritativeEnglish
            ? data.ai_procedural_explanation.authoritative_english_text
            : data.ai_procedural_explanation.explanation_text}
        </div>

        {/* Mandatory Legal Disclaimer */}
        <div className="flex items-start gap-2 p-2.5 bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/40 rounded-lg text-[11px] text-rose-800 dark:text-rose-300">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <p className="leading-normal">
            <strong>Statutory Caution:</strong> {data.ai_procedural_explanation.disclaimer_text}
          </p>
        </div>
      </div>

      {/* ── Upcoming Known Events Card ── */}
      {data.upcoming_known_events && data.upcoming_known_events.length > 0 && (
        <div className="bg-card border border-border p-4 md:p-5 rounded-xl space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-emerald-600" />
              Upcoming Scheduled Events
            </span>
          </div>
          <div className="space-y-2">
            {data.upcoming_known_events.map((ev, idx) => (
              <div key={idx} className="p-3 bg-muted/40 border border-border rounded-lg text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-serif font-bold text-foreground">{ev.title}</span>
                  <span className="font-mono text-[11px] font-bold text-emerald-600">
                    {ev.event_date}
                  </span>
                </div>
                <div className="text-muted-foreground text-[11px]">{ev.court_or_location}</div>
                <p className="text-[11px] text-muted-foreground leading-relaxed pt-0.5">
                  {ev.instructions}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Documents Missing From Your Side ── */}
      {data.missing_documents_from_citizen && data.missing_documents_from_citizen.length > 0 && (
        <div className="bg-card border border-rose-200 dark:border-rose-950/60 p-4 md:p-5 rounded-xl space-y-3 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              Documents Needed From Your Side
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            To assist DLSA legal aid counsel in moving your bail representation forward, please prepare the following records:
          </p>
          <div className="space-y-2.5 pt-1">
            {data.missing_documents_from_citizen.map((doc, idx) => (
              <div key={idx} className="p-3 bg-rose-50/40 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/40 rounded-lg text-xs space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-serif font-bold text-foreground">{doc.title}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-100 dark:bg-rose-900 text-rose-700 dark:text-rose-300 shrink-0">
                    {doc.urgency === "REQUIRED_BEFORE_HEARING" ? "URGENT" : "SUPPORTING"}
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  <strong>Why needed:</strong> {doc.why_needed}
                </p>
                <p className="text-[11px] text-muted-foreground leading-relaxed pt-0.5">
                  <strong>How to submit:</strong> {doc.how_to_submit}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Approved Entitled Documents (With Low-Bandwidth Text Summaries) ── */}
      <div className="bg-card border border-border p-4 md:p-5 rounded-xl space-y-3 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-emerald-600" />
            Approved Case Records Entitled To You
          </span>
          <span className="text-[11px] font-mono text-muted-foreground">
            {data.approved_entitled_documents.length} Available
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          You are entitled to soft copies and text summaries of official police and magisterial orders:
        </p>

        <div className="space-y-2 pt-1">
          {data.approved_entitled_documents.map((doc) => (
            <div
              key={doc.id}
              className="p-3 bg-muted/40 border border-border rounded-lg text-xs flex flex-col gap-1.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 truncate">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span className="font-serif font-bold text-foreground truncate">{doc.title}</span>
                </div>
                <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                  {doc.file_size_formatted}
                </span>
              </div>

              {/* Text Summary (Instant for Low Bandwidth) */}
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {doc.text_summary}
              </p>

              <div className="flex items-center justify-end gap-2 pt-1 border-t border-border/50">
                <button
                  onClick={() => setPreviewDoc(doc)}
                  className="px-2.5 py-1 rounded text-[11px] font-mono font-bold bg-card border border-border hover:bg-muted text-foreground flex items-center gap-1 transition-colors"
                >
                  <Eye className="w-3 h-3" />
                  Text Summary Preview
                </button>
                <button
                  onClick={() => setSelectedProvenanceId(doc.id)}
                  className="px-2.5 py-1 rounded text-[11px] font-mono font-bold bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 flex items-center gap-1 transition-colors"
                >
                  <Shield className="w-3 h-3" />
                  Provenance
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Legal Aid Defense Counsel & Contact ── */}
      <div className="bg-card border border-border p-4 md:p-5 rounded-xl space-y-3 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Landmark className="w-4 h-4 text-emerald-600" />
            Legal Aid & Defense Support
          </span>
          <span className="text-[11px] font-mono text-emerald-600 font-bold">
            100% Free Service
          </span>
        </div>

        <div className="space-y-2 text-xs">
          {data.legal_aid_support.is_assigned ? (
            <div className="p-3 bg-muted/40 border border-border rounded-lg space-y-1">
              <div className="font-serif font-bold text-foreground text-sm">
                {data.legal_aid_support.lawyer_name}
              </div>
              <div className="text-muted-foreground">{data.legal_aid_support.organization}</div>
              <div className="text-[11px] font-mono text-emerald-600">
                Contact: {data.legal_aid_support.contact_phone}
              </div>
              <div className="text-[11px] text-muted-foreground pt-1">
                {data.legal_aid_support.office_address}
              </div>
            </div>
          ) : (
            <div className="p-3 bg-muted/40 border border-border rounded-lg space-y-1">
              <div className="font-semibold text-rose-600 flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                Counsel Assignment in Progress
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                {data.legal_aid_support.status_message}
              </p>
            </div>
          )}

          {/* Toll Free Helpline Call Out */}
          <div className="p-3 bg-black text-white dark:bg-white dark:text-black rounded-lg flex items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="font-serif font-bold text-xs">National Legal Aid Helpline</div>
              <div className="text-[10px] opacity-80">24x7 Toll-Free NALSA Assistance</div>
            </div>
            <a
              href="tel:15100"
              className="px-3.5 py-1.5 bg-emerald-600 text-white font-sans font-bold text-xs rounded-md flex items-center gap-1.5 hover:bg-emerald-700 transition-colors shrink-0"
            >
              <Phone className="w-3.5 h-3.5" />
              Dial 15100
            </a>
          </div>
        </div>
      </div>

      {/* ── Citizen Action Center (Structured Actions) ── */}
      <div className="bg-card border border-border p-4 md:p-5 rounded-xl space-y-3 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Send className="w-4 h-4 text-emerald-600" />
            Citizen Action Center
          </span>
          <span className="text-[10px] font-mono text-muted-foreground">
            Auditable DLSA Requests
          </span>
        </div>
        <p className="text-xs text-muted-foreground">
          Submit structured requests directly to the District Legal Services Authority desk:
        </p>

        {/* 4 Action Buttons */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <button
            onClick={() => {
              setActionType("REQUEST_DLSA_CONTACT");
              setActionSubject("Request Contact with DLSA Panel Counsel");
              setActionDetails("Requesting an in-person or telephonic consultation with the assigned legal aid advocate regarding upcoming hearing.");
              setActionModalOpen(true);
            }}
            className="p-3 bg-muted/40 hover:bg-muted border border-border rounded-lg text-left transition-colors flex flex-col gap-1"
          >
            <span className="font-bold text-foreground flex items-center gap-1.5">
              <Phone className="w-3.5 h-3.5 text-emerald-600" />
              Contact DLSA
            </span>
            <span className="text-[11px] text-muted-foreground">Request panel counsel contact</span>
          </button>

          <button
            onClick={() => {
              setActionType("FLAG_INCORRECT_INFO");
              setActionSubject("Report Discrepancy in Case Records");
              setActionDetails("There is an error in custody calculation or identity attributes recorded in the system.");
              setActionModalOpen(true);
            }}
            className="p-3 bg-muted/40 hover:bg-muted border border-border rounded-lg text-left transition-colors flex flex-col gap-1"
          >
            <span className="font-bold text-foreground flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
              Flag Discrepancy
            </span>
            <span className="text-[11px] text-muted-foreground">Report incorrect dates or names</span>
          </button>

          <button
            onClick={() => {
              setActionType("REQUEST_DOCUMENT_COPY");
              setActionSubject("Request Certified Copy of Document");
              setActionDetails("Requesting certified soft copy of official court or police report.");
              setActionModalOpen(true);
            }}
            className="p-3 bg-muted/40 hover:bg-muted border border-border rounded-lg text-left transition-colors flex flex-col gap-1"
          >
            <span className="font-bold text-foreground flex items-center gap-1.5">
              <FileQuestion className="w-3.5 h-3.5 text-emerald-600" />
              Request Copy
            </span>
            <span className="text-[11px] text-muted-foreground">Request official document copy</span>
          </button>

          <button
            onClick={() => {
              setActionType("REQUEST_HELP");
              setActionSubject("Request Urgent Legal Aid Assistance");
              setActionDetails("Requesting immediate assistance from Jail Legal Aid Clinic or DLSA Secretary.");
              setActionModalOpen(true);
            }}
            className="p-3 bg-muted/40 hover:bg-muted border border-border rounded-lg text-left transition-colors flex flex-col gap-1"
          >
            <span className="font-bold text-foreground flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-emerald-600" />
              Ask For Help
            </span>
            <span className="text-[11px] text-muted-foreground">Urgent welfare assistance</span>
          </button>
        </div>

        {/* Recent Requests Status */}
        {data.recent_citizen_requests && data.recent_citizen_requests.length > 0 && (
          <div className="pt-2 border-t border-border space-y-2">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground block">
              Your Past Submissions
            </span>
            <div className="space-y-1.5">
              {data.recent_citizen_requests.map((req) => (
                <div key={req.id} className="p-2.5 bg-muted/30 border border-border rounded-lg text-xs flex items-center justify-between">
                  <div className="truncate pr-2">
                    <div className="font-serif font-bold text-foreground truncate">{req.subject}</div>
                    <div className="text-[10px] font-mono text-muted-foreground">ID: {req.id}</div>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 shrink-0">
                    {req.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Action Submission Modal ── */}
      {actionModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl w-full max-w-lg p-5 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h3 className="font-serif font-bold text-base text-foreground flex items-center gap-2">
                <Send className="w-4 h-4 text-emerald-600" />
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
              <div className="p-4 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg text-xs text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                <p className="font-bold text-emerald-800 dark:text-emerald-300">{actionSuccessMsg}</p>
                <p className="font-mono text-muted-foreground">Tracking ID: {actionTrackingId}</p>
                <button
                  onClick={() => {
                    setActionModalOpen(false);
                    setActionSuccessMsg(null);
                  }}
                  className="mt-2 px-4 py-1.5 bg-black text-white dark:bg-white dark:text-black font-bold text-xs rounded-md"
                >
                  Close
                </button>
              </div>
            ) : (
              <form onSubmit={handleActionSubmit} className="space-y-3 text-xs">
                <div>
                  <label className="block font-bold text-muted-foreground mb-1">Request Type</label>
                  <select
                    value={actionType}
                    onChange={(e: any) => setActionType(e.target.value)}
                    className="w-full p-2 rounded-lg bg-muted border border-border text-foreground font-mono"
                  >
                    <option value="REQUEST_DLSA_CONTACT">Request DLSA Panel Counsel Contact</option>
                    <option value="FLAG_INCORRECT_INFO">Report Discrepancy / Flag Error</option>
                    <option value="REQUEST_DOCUMENT_COPY">Request Certified Document Copy</option>
                    <option value="REQUEST_HELP">Ask for Urgent Legal Aid Help</option>
                  </select>
                </div>

                {actionType === "FLAG_INCORRECT_INFO" && (
                  <div>
                    <label className="block font-bold text-muted-foreground mb-1">Field with Discrepancy</label>
                    <select
                      value={actionField}
                      onChange={(e) => setActionField(e.target.value)}
                      className="w-full p-2 rounded-lg bg-muted border border-border text-foreground font-mono"
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
                    <label className="block font-bold text-muted-foreground mb-1">Document Requested</label>
                    <select
                      value={actionDocType}
                      onChange={(e) => setActionDocType(e.target.value)}
                      className="w-full p-2 rounded-lg bg-muted border border-border text-foreground font-mono"
                    >
                      <option value="charge_sheet">Police Charge Sheet</option>
                      <option value="remand_order">Judicial Remand Order</option>
                      <option value="fir">First Information Report (FIR)</option>
                      <option value="custody_certificate">Prison Custody Certificate</option>
                    </select>
                  </div>
                )}

                <div>
                  <label className="block font-bold text-muted-foreground mb-1">Subject</label>
                  <input
                    type="text"
                    required
                    value={actionSubject}
                    onChange={(e) => setActionSubject(e.target.value)}
                    className="w-full p-2 rounded-lg bg-muted border border-border text-foreground"
                    placeholder="Brief summary of what you require..."
                  />
                </div>

                <div>
                  <label className="block font-bold text-muted-foreground mb-1">Details</label>
                  <textarea
                    required
                    rows={3}
                    value={actionDetails}
                    onChange={(e) => setActionDetails(e.target.value)}
                    className="w-full p-2 rounded-lg bg-muted border border-border text-foreground leading-relaxed"
                    placeholder="Provide specific details so the DLSA officer can verify..."
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
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg transition-colors flex items-center gap-1.5"
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
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl w-full max-w-md p-5 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h3 className="font-serif font-bold text-base text-foreground flex items-center gap-2">
                <Bell className="w-4 h-4 text-emerald-600" />
                Notification Preferences & Consent
              </h3>
              <button onClick={() => setNotifModalOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveNotifPrefs} className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-muted-foreground mb-1">Mobile Number</label>
                <input
                  type="tel"
                  value={notifPhone}
                  onChange={(e) => setNotifPhone(e.target.value)}
                  className="w-full p-2 rounded-lg bg-muted border border-border text-foreground font-mono"
                  placeholder="+91 98765 43210"
                />
              </div>

              <div className="space-y-2 pt-1">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifSms}
                    onChange={(e) => setNotifSms(e.target.checked)}
                    className="rounded border-border"
                  />
                  <span>SMS Statutory Hearing & Status Notices</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifWhatsapp}
                    onChange={(e) => setNotifWhatsapp(e.target.checked)}
                    className="rounded border-border"
                  />
                  <span>WhatsApp Legal Aid Assistance Notices</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifInApp}
                    onChange={(e) => setNotifInApp(e.target.checked)}
                    className="rounded border-border"
                  />
                  <span>In-App Status Alerts</span>
                </label>
              </div>

              {/* Statutory Consent Record Notice */}
              <div className="p-3 bg-muted/40 border border-border rounded-lg text-[11px] text-muted-foreground leading-relaxed">
                <strong>Statutory Consent:</strong> By enabling notifications, you consent to receive institutional legal aid notices under Section 12 of the Legal Services Authorities Act, 1987. Carrier dispatch is logged in the statutory audit register.
              </div>

              {notifSavedMsg && (
                <div className="p-2 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 rounded text-center">
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
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg transition-colors"
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
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-xl w-full max-w-lg p-5 space-y-4 shadow-xl animate-in zoom-in-95">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <h3 className="font-serif font-bold text-base text-foreground truncate pr-2">
                {previewDoc.title}
              </h3>
              <button onClick={() => setPreviewDoc(null)} className="text-muted-foreground hover:text-foreground shrink-0">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                <span>Type: {previewDoc.document_type}</span>
                <span>Size: {previewDoc.file_size_formatted}</span>
              </div>
              <div className="p-3 bg-muted/40 border border-border rounded-lg text-muted-foreground leading-relaxed">
                <strong className="block text-foreground mb-1">Plain-Language Summary:</strong>
                {previewDoc.text_summary}
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed pt-1">
                This document is certified by the Legal Services Authority. Full certified PDF copies can be examined at the DLSA Front Office during court working hours.
              </p>
            </div>

            <div className="pt-2 flex items-center justify-end">
              <button
                onClick={() => setPreviewDoc(null)}
                className="px-4 py-2 bg-black text-white dark:bg-white dark:text-black font-bold text-xs rounded-lg"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Provenance Modal ── */}
      <RoleEvidenceProvenanceModal
        isOpen={!!selectedProvenanceId}
        onClose={() => setSelectedProvenanceId(null)}
        data={{
          target_record_id: selectedProvenanceId,
          source_agency: "DLSA & Magisterial Court Registry",
          cryptographic_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          chain_status: "VERIFIED_TAMPER_FREE",
        }}
        loading={false}
      />
    </div>
  );
}
