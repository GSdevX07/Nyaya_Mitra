import { useState, useEffect } from "react";
import {
  Calendar, Phone, FileText, CheckCircle2,
  Clock, AlertCircle, Globe
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { fetchCitizenCase } from "../lib/api";

interface CitizenPortalProps {
  mode?: "accused" | "family";
}

interface CitizenViewData {
  accused_id: string;
  accused_name: string;
  case_reference: string;
  court_name: string;
  next_hearing_date: string;
  legal_status: {
    title_en: string;
    title_hi: string;
    detail_en: string;
    detail_hi: string;
    badge_color: string;
  };
  assigned_legal_aid_lawyer: {
    name: string;
    organization: string;
    phone: string;
    helpline: string;
  };
  available_documents: Array<{
    title: string;
    status: string;
  }>;
  communication_preferences?: {
    registered_relative: string;
    relation: string;
    preferred_language: string;
    notification_channel: string;
  };
  support_notice: string;
}

export function CitizenPortal({ mode = "accused" }: CitizenPortalProps) {
  const { user, token } = useAuth();
  const [data, setData] = useState<CitizenViewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState<'en' | 'hi'>('en');

  useEffect(() => {
    async function loadCitizenCase() {
      setLoading(true);
      try {
        const json = await fetchCitizenCase();
        setData(json);
      } catch (err) {
        console.error("Failed to load citizen case:", err);
      } finally {
        setLoading(false);
      }
    }
    if (token) {
      loadCitizenCase();
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

  if (!data) {
    return (
      <div className="p-8 max-w-2xl mx-auto bg-card border border-border rounded-xl text-center space-y-4 shadow-sm">
        <AlertCircle className="w-10 h-10 text-amber-500 mx-auto" />
        <h2 className="text-lg font-bold text-foreground">
          {lang === 'hi' ? "कोई सक्रिय मामला लिंक नहीं मिला" : "No Active Case Linked"}
        </h2>
        <p className="text-xs text-muted-foreground">
          {lang === 'hi'
            ? "यदि आप या आपका परिवार सदस्य हिरासत में है, तो कृपया निःशुल्क कानूनी सहायता हेल्पलाइन 15100 पर संपर्क करें।"
            : "We could not locate an active legal aid dossier. If you or your family member is in custody, contact the National Legal Aid Helpline at 15100."}
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-6 pb-12">
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
      <div className="bg-card border border-border p-6 rounded-xl shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20">
            {isFamily 
              ? (lang === 'hi' ? "परिवार एवं संरक्षक सहायता पोर्टल" : "Family & Guardian Assistance Portal")
              : (lang === 'hi' ? "नागरिक कानूनी सहायता पोर्टल" : "Citizen Legal Aid Portal")}
          </span>
          <span className="text-xs font-mono font-bold text-muted-foreground">
            Ref: {data.case_reference}
          </span>
        </div>

        <h1 className="text-2xl font-bold tracking-tight text-foreground">
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
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {lang === 'hi' ? "वर्तमान कानूनी स्थिति" : "Legal Aid Status"}
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          </div>

          <div>
            <div className="text-base font-bold text-foreground">
              {lang === 'hi' ? data.legal_status.title_hi : data.legal_status.title_en}
            </div>
            <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">
              {lang === 'hi' ? data.legal_status.detail_hi : data.legal_status.detail_en}
            </p>
          </div>

          <div className="pt-2 border-t border-border flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
            <CheckCircle2 className="w-4 h-4" />
            <span>{lang === 'hi' ? "समीक्षा प्रगति पर है" : "Active Review in Progress"}</span>
          </div>
        </div>

        {/* Card 2: Appointed Lawyer */}
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
            {lang === 'hi' ? "नियुक्त कानूनी सहायता अधिवक्ता" : "Assigned Defense Lawyer"}
          </span>

          <div className="space-y-1">
            <div className="text-base font-bold text-foreground">
              {data.assigned_legal_aid_lawyer.name}
            </div>
            <p className="text-xs text-muted-foreground">
              {data.assigned_legal_aid_lawyer.organization}
            </p>
          </div>

          <div className="pt-2 border-t border-border space-y-1.5 text-xs">
            <div className="flex items-center gap-2 text-foreground font-medium">
              <Phone className="w-3.5 h-3.5 text-primary" />
              <span>{data.assigned_legal_aid_lawyer.phone}</span>
            </div>
            <div className="text-[11px] text-muted-foreground">
              {lang === 'hi' ? "निःशुल्क कानूनी सहायता डेस्क" : "Free DLSA Assistance Desk"}
            </div>
          </div>
        </div>

        {/* Card 3: Next Court Date */}
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-3">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
            {lang === 'hi' ? "अगली अदालती सुनवाई" : "Next Court Hearing"}
          </span>

          <div className="flex items-center gap-3">
            <div className="p-3 bg-primary/10 rounded-lg text-primary">
              <Calendar className="w-6 h-6" />
            </div>
            <div>
              <div className="text-lg font-bold text-foreground">
                {data.next_hearing_date}
              </div>
              <div className="text-xs text-muted-foreground">{data.court_name}</div>
            </div>
          </div>

          <div className="pt-2 border-t border-border text-[11px] text-muted-foreground flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            <span>{lang === 'hi' ? "अदालत में पेशी निर्धारित" : "Scheduled Court Production"}</span>
          </div>
        </div>
      </div>

      {/* Available Documents Section */}
      <div className="bg-card border border-border p-6 rounded-xl shadow-sm space-y-4">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          {lang === 'hi' ? "सत्यापित आधिकारिक दस्तावेज" : "Verified Official Records"}
        </h3>
        <p className="text-xs text-muted-foreground">
          {lang === 'hi'
            ? "कानूनी सहायता प्राधिकरण द्वारा सत्यापित एवं संरक्षित दस्तावेज।"
            : "Authorized public documents retrieved and verified by the Legal Services Authority."}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {data.available_documents.map((doc, idx) => (
            <div key={idx} className="p-3.5 bg-secondary/40 border border-border rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span className="text-xs font-semibold text-foreground">{doc.title}</span>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-emerald-500/10 text-emerald-600">
                {lang === 'hi' ? "सत्यापित" : "VERIFIED"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Direct Contact & Helpline Card */}
      <div className="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-primary/20 p-6 rounded-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-base font-bold text-foreground flex items-center gap-2">
              <Phone className="h-5 w-5 text-primary" />
              {lang === 'hi' ? "निःशुल्क राष्ट्रीय कानूनी सहायता हेल्पलाइन" : "Free National Legal Aid Helpline"}
            </h4>
            <p className="text-xs text-muted-foreground">
              {lang === 'hi'
                ? "नालसा (NALSA) 24x7 हेल्पलाइन — किसी भी सहायता या प्रश्न के लिए तुरंत कॉल करें।"
                : "NALSA 24x7 Toll-Free Legal Helpline — Call anytime for guidance on undertrial rights."}
            </p>
          </div>

          <a
            href="tel:15100"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-bold text-sm shadow-md hover:bg-primary/90 transition-transform active:scale-95"
          >
            <Phone className="h-4 w-4" /> {lang === 'hi' ? "15100 पर कॉल करें" : "Call 15100 (Toll-Free)"}
          </a>
        </div>
      </div>
    </div>
  );
}
export default CitizenPortal;
