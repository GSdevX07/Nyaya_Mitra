import { useState, useEffect } from "react";
import {
  Calendar, Phone, FileText, CheckCircle2,
  Clock, AlertCircle, Globe, Shield, Landmark,
  Send, CheckCheck
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { fetchCitizenCase, fetchCitizenTimeline, fetchEvidenceChain } from "../lib/api";
import { RoleEvidenceProvenanceModal } from "../components/RoleEvidenceProvenanceModal";

interface CitizenPortalProps {
  mode?: "accused" | "family";
}

interface CitizenViewData {
  portal_mode: string;
  accused_id: string;
  accused_name: string;
  case_reference: string;
  court_name: string;
  next_hearing_date: string | null;
  legal_status: {
    status_code: string;
    stage: string;
    title_en: string;
    title_hi: string;
    detail_en: string;
    detail_hi: string;
    filing_status: string;
    court_outcome_confirmed: boolean;
    badge_color: string;
  };
  filing_details: {
    status: string;
    is_filed: boolean;
    filing_reference: string;
    court_name: string;
  };
  release_details: {
    is_released: boolean;
    release_status: string;
  };
  assigned_legal_aid_lawyer: {
    is_assigned: boolean;
    name: string | null;
    organization: string;
    contact_phone?: string;
    helpline?: string;
    status_message?: string;
    dlsa_helpline?: string;
    dlsa_office_contact?: string;
  };
  available_documents: Array<{
    id?: string;
    title: string;
    document_type?: string;
    status: string;
    uploaded_at?: string;
  }>;
  communication_preferences?: {
    registered_relative: string;
    relation: string;
    preferred_language: string;
    supported_languages: string[];
    notification_channel: string;
  };
  support_notice: string;
}

export function CitizenPortal({ mode = "accused" }: CitizenPortalProps) {
  const { user, token } = useAuth();
  const [data, setData] = useState<CitizenViewData | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [lang, setLang] = useState<'en' | 'hi'>('en');

  // Document Status Modal State
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docProvenance, setDocProvenance] = useState<any>(null);
  const [docLoading, setDocLoading] = useState(false);

  const handleOpenDocStatus = async (docId?: string) => {
    const target = docId || (data?.case_reference ? `DOC-${data.case_reference}-remand_order` : "UTP-0001");
    setSelectedDocId(target);
    setDocLoading(true);
    try {
      const res = await fetchEvidenceChain(target);
      setDocProvenance(res);
    } catch (err) {
      console.error("Failed to load document status:", err);
    } finally {
      setDocLoading(false);
    }
  };

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setErrorStatus(null);
      try {
        const [caseRes, timelineRes] = await Promise.allSettled([
          fetchCitizenCase(),
          fetchCitizenTimeline(),
        ]);

        if (caseRes.status === "fulfilled" && caseRes.value) {
          setData(caseRes.value);
        } else if (caseRes.status === "rejected") {
          const err = caseRes.reason;
          if (err && err.message && err.message.includes("404")) {
            setErrorStatus(404);
          }
        }

        if (timelineRes.status === "fulfilled" && Array.isArray(timelineRes.value)) {
          setTimeline(timelineRes.value);
        }
      } catch (err: any) {
        console.error("Failed to load citizen case:", err);
      } finally {
        setLoading(false);
      }
    }
    if (token) {
      loadData();
    }
  }, [token, user]);

  const isFamily = mode === "family" || user?.role === "FAMILY_GUARDIAN";

  if (loading) {
    return (
      <div className="p-8 max-w-4xl mx-auto flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-sans text-muted-foreground">
          {lang === 'hi' ? "कानूनी सहायता स्थिति लोड हो रही है..." : "Loading your legal aid assistance status..."}
        </p>
      </div>
    );
  }

  if (errorStatus === 404 || !data) {
    return (
      <div className="p-8 max-w-2xl mx-auto space-y-6">
        <div className="bg-card border-2 border-border rounded-xl text-center p-8 space-y-4 shadow-sm">
          <AlertCircle className="w-12 h-12 text-amber-500 mx-auto" />
          <h2 className="text-xl font-serif font-bold text-foreground">
            {lang === 'hi' ? "कोई सक्रिय मामला लिंक नहीं मिला" : "No Active Case Linked to This Account"}
          </h2>
          <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
            {lang === 'hi'
              ? "आपके खाते से कोई सक्रिय कानूनी सहायता मामला संबद्ध नहीं है। यदि आप या आपका परिवार सदस्य हिरासत में है, तो कृपया निःशुल्क कानूनी सहायता हेल्पलाइन 15100 पर संपर्क करें या अपने जिला विधिक सेवा प्राधिकरण (DLSA) कार्यालय से संपर्क करें।"
              : "No active legal aid case is currently linked to your credentials. If you or an undertrial family member requires legal representation, please contact the National Legal Services Helpline (15100) or visit your local District Legal Services Authority (DLSA) office."}
          </p>

          <div className="pt-4 border-t border-border flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="tel:15100"
              className="px-4 py-2 bg-primary text-primary-foreground font-sans font-bold text-xs rounded-lg flex items-center gap-2 hover:bg-primary/90 transition-colors"
            >
              <Phone className="w-4 h-4" />
              {lang === 'hi' ? "हेल्पलाइन डायल करें: 15100" : "Call NALSA Helpline: 15100"}
            </a>
            <div className="text-xs text-muted-foreground">
              {lang === 'hi' ? "24x7 निःशुल्क सेवा" : "24x7 Toll-Free Free Legal Aid"}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Dynamic status badge mapping
  const getStatusBadge = () => {
    const code = data.legal_status.status_code;
    if (code === "UNDER_REVIEW") {
      return { text: lang === 'hi' ? "समीक्षाधीन" : "UNDER INITIAL REVIEW", color: "bg-blue-500/10 text-blue-600 border-blue-500/20" };
    }
    if (code === "ELIGIBLE_FOR_REVIEW") {
      return { text: lang === 'hi' ? "पात्रता चिह्नित" : "ELIGIBLE UNDER SEC 479", color: "bg-amber-500/10 text-amber-600 border-amber-500/20" };
    }
    if (code === "COUNSEL_ASSIGNED") {
      return { text: lang === 'hi' ? "अधिवक्ता नियुक्त" : "COUNSEL ASSIGNED", color: "bg-blue-500/10 text-blue-600 border-blue-500/20" };
    }
    if (code === "READY_FOR_FILING") {
      return { text: lang === 'hi' ? "दायर करने हेतु तैयार" : "DRAFT APPROVED • PENDING FILING", color: "bg-amber-500/10 text-amber-600 border-amber-500/20" };
    }
    if (code === "FILED_IN_COURT") {
      return { text: lang === 'hi' ? "अदालत में दायर" : "FILED IN COURT", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" };
    }
    if (code === "COURT_ORDER_RECEIVED") {
      return { text: lang === 'hi' ? "अदालत का आदेश प्राप्त" : "COURT BAIL ORDER ISSUED", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" };
    }
    if (code === "RELEASE_EXECUTED") {
      return { text: lang === 'hi' ? "रिहाई प्रक्रिया पूर्ण" : "PRISON RELEASE EXECUTED", color: "bg-purple-500/10 text-purple-600 border-purple-500/20" };
    }
    return { text: code, color: "bg-secondary text-foreground" };
  };

  const statusBadge = getStatusBadge();

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300">
      {/* Language & Accessibility Bar */}
      <div className="flex items-center justify-between bg-secondary/50 border border-border px-4 py-2 rounded-xl">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Globe className="h-4 w-4 text-primary" />
          <span>{lang === 'hi' ? "भाषा चुनें" : "Select Language"}:</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setLang('en')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
              lang === 'en' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            English
          </button>
          <button
            onClick={() => setLang('hi')}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
              lang === 'hi' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            हिन्दी (Hindi)
          </button>
        </div>
      </div>

      {/* Citizen Welcome Banner */}
      <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
            {isFamily 
              ? (lang === 'hi' ? "परिवार एवं संरक्षक सहायता पोर्टल" : "Family & Guardian Assistance Portal")
              : (lang === 'hi' ? "नागरिक कानूनी सहायता पोर्टल" : "Citizen Legal Aid Portal")}
          </span>
          <span className="text-xs font-mono font-bold text-muted-foreground">
            Ref: {data.case_reference}
          </span>
        </div>

        <h1 className="text-2xl font-serif font-black tracking-tight text-foreground">
          {isFamily
            ? (lang === 'hi' ? `${data.accused_name} की कानूनी स्थिति` : `Legal Status of ${data.accused_name}`)
            : (lang === 'hi' ? `नमस्ते, ${data.accused_name}` : `Welcome, ${data.accused_name}`)}
        </h1>

        <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">
          {lang === 'hi'
            ? "भारतीय संविधान के अनुच्छेद 39A एवं BNSS की धारा 479 के तहत आपको निःशुल्क सरकारी कानूनी सहायता एवं समयबद्ध जमानत समीक्षा का अधिकार प्राप्त है।"
            : "Under Article 39A of the Constitution of India and Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), you are entitled to free legal aid representation and custody review."}
        </p>
      </div>

      {/* Main Status Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Card 1: Current Legal Status */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {lang === 'hi' ? "वर्तमान कानूनी स्थिति" : "Legal Aid Status"}
              </span>
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            </div>

            <div>
              <div className="text-base font-serif font-bold text-foreground">
                {lang === 'hi' ? data.legal_status.title_hi : data.legal_status.title_en}
              </div>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {lang === 'hi' ? data.legal_status.detail_hi : data.legal_status.detail_en}
              </p>
            </div>
          </div>

          <div className="pt-2 border-t border-border">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-mono font-bold border ${statusBadge.color}`}>
              {statusBadge.text}
            </span>
          </div>
        </div>

        {/* Card 2: Appointed Lawyer */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
              {lang === 'hi' ? "नियुक्त कानूनी सहायता अधिवक्ता" : "Assigned Defense Lawyer"}
            </span>

            {data.assigned_legal_aid_lawyer.is_assigned ? (
              <div className="space-y-1">
                <div className="text-base font-serif font-bold text-foreground">
                  {data.assigned_legal_aid_lawyer.name}
                </div>
                <p className="text-xs text-muted-foreground">
                  {data.assigned_legal_aid_lawyer.organization}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <div className="text-sm font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                  <Clock className="w-4 h-4" />
                  {lang === 'hi' ? "आवंटन प्रक्रियाधीन" : "Counsel Allocation in Progress"}
                </div>
                <p className="text-xs text-muted-foreground">
                  {data.assigned_legal_aid_lawyer.status_message || "DLSA Legal Aid Panel"}
                </p>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-border space-y-1 text-xs">
            <div className="flex items-center gap-1.5 text-foreground font-mono">
              <Phone className="w-3.5 h-3.5 text-primary" />
              <span>{data.assigned_legal_aid_lawyer.contact_phone || data.assigned_legal_aid_lawyer.dlsa_office_contact || "15100"}</span>
            </div>
            <div className="text-[11px] text-muted-foreground">
              {lang === 'hi' ? "निःशुल्क कानूनी सहायता डेस्क" : "Free DLSA Legal Assistance Desk"}
            </div>
          </div>
        </div>

        {/* Card 3: Next Court Hearing */}
        <div className="bg-card border-2 border-border p-5 rounded-xl shadow-sm space-y-3 flex flex-col justify-between">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                {lang === 'hi' ? "अगली अदालती सुनवाई" : "Next Court Hearing"}
              </span>
              <Calendar className="w-4 h-4 text-primary" />
            </div>

            <div>
              <div className="text-lg font-serif font-bold text-foreground">
                {data.next_hearing_date || (lang === 'hi' ? "तारीख प्रतीक्षारत" : "Awaiting Schedule")}
              </div>
              <div className="text-xs text-muted-foreground">{data.court_name}</div>
            </div>
          </div>

          <div className="pt-2 border-t border-border text-[11px] text-muted-foreground flex items-center gap-1.5">
            <Landmark className="w-3.5 h-3.5 text-primary" />
            <span>{lang === 'hi' ? "अदालत में पेशी रिकॉर्ड" : "Authoritative Court Record"}</span>
          </div>
        </div>
      </div>

      {/* Procedural Details: Filing & Release Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-card border border-border p-4 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center gap-2">
            <Send className="w-4 h-4 text-primary" />
            <h3 className="font-serif font-bold text-sm text-foreground">
              {lang === 'hi' ? "अदालत में याचिका दायर करने की स्थिति" : "Court Filing Status"}
            </h3>
          </div>
          <div className="text-xs space-y-1 font-mono text-muted-foreground">
            <div className="flex justify-between">
              <span>{lang === 'hi' ? "दायर स्थिति:" : "Filing Record:"}</span>
              <strong className="text-foreground">
                {data.filing_details.is_filed ? (lang === 'hi' ? "दायर" : "FORMALLY LODGED") : (lang === 'hi' ? "प्रतीक्षारत" : "AWAITING SUBMISSION")}
              </strong>
            </div>
            <div className="flex justify-between">
              <span>{lang === 'hi' ? "संदर्भ:" : "Reference:"}</span>
              <span className="text-foreground">{data.filing_details.filing_reference}</span>
            </div>
            <div className="flex justify-between">
              <span>{lang === 'hi' ? "अदालत:" : "Jurisdiction:"}</span>
              <span className="text-foreground truncate">{data.filing_details.court_name}</span>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border p-4 rounded-xl space-y-2 shadow-sm">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-600" />
            <h3 className="font-serif font-bold text-sm text-foreground">
              {lang === 'hi' ? "हिरासत एवं रिहाई स्थिति" : "Custody & Release Status"}
            </h3>
          </div>
          <div className="text-xs space-y-1 font-mono text-muted-foreground">
            <div className="flex justify-between">
              <span>{lang === 'hi' ? "रिहाई सत्यापन:" : "Custody Status:"}</span>
              <strong className="text-foreground">
                {data.release_details.is_released
                  ? (lang === 'hi' ? "रिहाई पूर्ण" : "RELEASE EXECUTED")
                  : (data.release_details.release_status === "BAIL_ORDER_ISSUED"
                      ? (lang === 'hi' ? "आदेश जारी" : "BAIL ORDER ISSUED")
                      : (lang === 'hi' ? "हिरासत में" : "IN CUSTODY"))}
              </strong>
            </div>
            <div className="flex justify-between">
              <span>{lang === 'hi' ? "सत्यापन स्रोत:" : "Verification:"}</span>
              <span className="text-foreground">e-Prisons Custody Sync</span>
            </div>
          </div>
        </div>
      </div>

      {/* Available Documents Section */}
      <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-4">
        <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          {lang === 'hi' ? "सत्यापित आधिकारिक दस्तावेज" : "Verified Case Records Available to You"}
        </h3>
        <p className="text-xs text-muted-foreground">
          {lang === 'hi'
            ? "कानूनी सहायता प्राधिकरण द्वारा सत्यापित एवं संरक्षित आधिकारिक दस्तावेज।"
            : "Authorized public documents retrieved and verified by the Legal Services Authority."}
        </p>

        {data.available_documents && data.available_documents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.available_documents.map((doc, idx) => (
              <div
                key={idx}
                onClick={() => handleOpenDocStatus(doc.id)}
                className="p-3.5 bg-secondary/30 hover:bg-secondary/50 cursor-pointer border border-border rounded-lg flex items-center justify-between transition-colors shadow-xs"
                title="Click to view official document status"
              >
                <div className="flex items-center gap-2.5 truncate">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                  <span className="text-xs font-semibold text-foreground truncate">{doc.title}</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold bg-emerald-500/10 text-emerald-600 shrink-0">
                  {lang === 'hi' ? "सत्यापित" : "VERIFIED"}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 bg-secondary/20 border border-border rounded text-center text-xs text-muted-foreground">
            {lang === 'hi' ? "वर्तमान में कोई सत्यापित दस्तावेज उपलब्ध नहीं है।" : "No public documents currently verified for this case."}
          </div>
        )}
      </div>

      {/* Verified Milestone Timeline */}
      {timeline.length > 0 && (
        <div className="bg-card border-2 border-border p-6 rounded-xl shadow-sm space-y-4">
          <h3 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
            <CheckCheck className="w-5 h-5 text-primary" />
            {lang === 'hi' ? "प्रमाणित अदालती एवं कानूनी घटनाक्रम" : "Verified Legal Milestones Timeline"}
          </h3>
          <p className="text-xs text-muted-foreground">
            {lang === 'hi'
              ? "मामले से जुड़े आधिकारिक एवं सत्यापित घटनाक्रम (आंतरिक तकनीकी रिकॉर्ड छोड़कर)।"
              : "Plain-language record of official case events, excluding internal administrative logs."}
          </p>

          <div className="space-y-3 pt-2">
            {timeline.slice(0, 6).map((item, idx) => (
              <div key={idx} className="flex items-start gap-3 text-xs p-3 bg-secondary/20 rounded-lg border border-border">
                <div className="w-2 h-2 rounded-full bg-primary mt-1 shrink-0" />
                <div className="space-y-0.5 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-serif font-bold text-foreground">{item.title}</span>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {item.event_date ? new Date(item.event_date).toLocaleDateString() : ""}
                    </span>
                  </div>
                  <p className="text-muted-foreground text-[11px] leading-relaxed">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Direct Contact & Helpline Card */}
      <div className="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border-2 border-primary/20 p-6 rounded-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-base font-serif font-bold text-foreground flex items-center gap-2">
              <Phone className="h-5 w-5 text-primary" />
              {lang === 'hi' ? "निःशुल्क राष्ट्रीय कानूनी सहायता हेल्पलाइन" : "Free National Legal Aid Helpline"}
            </h4>
            <p className="text-xs text-muted-foreground">
              {lang === 'hi'
                ? "नालसा (NALSA) 24x7 हेल्पलाइन — किसी भी सहायता या प्रश्न के लिए तुरंत कॉल करें।"
                : "National Legal Services Authority (NALSA) 24x7 Helpline — Call for free guidance anytime."}
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

      {/* Citizen / Family Document Status Modal */}
      <RoleEvidenceProvenanceModal
        isOpen={!!selectedDocId}
        onClose={() => setSelectedDocId(null)}
        data={docProvenance}
        loading={docLoading}
      />
    </div>
  );
}
