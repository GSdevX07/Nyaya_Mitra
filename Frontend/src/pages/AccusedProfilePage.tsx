import React, { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { fetchAccusedProfile, fetchAccusedTimeline, updateAccusedIdentity } from '../lib/api';
import { 
  ShieldAlert, 
  Clock, 
  HeartPulse, 
  Building2, 
  Phone, 
  ExternalLink, 
  Lock, 
  CheckCircle2, 
  AlertTriangle, 
  Calendar,
  Layers,
  ArrowLeft,
  Scale,
  Edit3,
  X,
  Loader2
} from 'lucide-react';

interface AccusedProfile {
  id: string;
  full_name: string;
  father_name?: string;
  alias_names: string[];
  gender: string;
  age: number;
  date_of_birth?: string;
  preferred_language: string;
  health_vulnerability: boolean;
  is_senior_citizen: boolean;
  repeat_offender: boolean;
  permanent_address: string;
  provenance: {
    source_system: string;
    source_record_id: string;
    confidence_score: number;
    verification_status: string;
    ingested_at?: string;
  };
  family_contacts: Array<{
    id?: string;
    name: string;
    relation: string;
    phone: string;
    alt_phone?: string;
    address?: string;
    preferred_language: string;
    preferred_channel: string;
    is_primary_contact: boolean;
    verified_by_dlsa: boolean;
  }>;
  medical_record?: {
    has_vulnerability: boolean;
    vulnerability_category?: string;
    details_restricted?: string;
    medical_officer_name?: string;
    examining_facility_id?: string;
    last_examination_date?: string;
    treatment_underway?: boolean;
    requires_hospital_referral?: boolean;
    is_redacted?: boolean;
  };
  government_identifiers?: Record<string, any>;
  connected_cases: Array<{
    case_id: string;
    court_name: string;
    fir_number: string;
    police_station: string;
    current_status: string;
    assigned_lawyer: string;
    days_in_custody: number;
    max_sentence_days: number;
    eligible_under_479: boolean;
    next_hearing_date: string;
  }>;
  total_cases_count: number;
}

interface TimelineItem {
  id: string;
  item_type: 'FACTUAL_EVENT' | 'SYSTEM_INTERPRETATION';
  category: string;
  title: string;
  description: string;
  event_date: string;
  source_name: string;
  source_record_id?: string;
  recorded_by: string;
  verification_status: 'CONFIRMED' | 'DISPUTED' | 'PENDING_REVIEW';
  confidence_score: number;
  is_disputed?: boolean;
  is_sensitive_medical?: boolean;
}

export const AccusedProfilePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { token, user, can } = useAuth();
  const [profile, setProfile] = useState<AccusedProfile | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'cases' | 'timeline' | 'medical' | 'family' | 'identity'>('cases');
  const [timelineFilter, setTimelineFilter] = useState<'ALL' | 'FACTUAL_EVENT' | 'SYSTEM_INTERPRETATION'>('ALL');

  // Identity Edit Modal State (Supervisor Only)
  const [isEditIdentityOpen, setIsEditIdentityOpen] = useState(false);
  const [editFullName, setEditFullName] = useState("");
  const [editAliases, setEditAliases] = useState("");
  const [editFatherName, setEditFatherName] = useState("");
  const [editGender, setEditGender] = useState("");
  const [editAge, setEditAge] = useState<number>(0);
  const [updateReason, setUpdateReason] = useState("");
  const [savingIdentity, setSavingIdentity] = useState(false);
  const [identityUpdateSuccess, setIdentityUpdateSuccess] = useState<string | null>(null);
  const [identityUpdateError, setIdentityUpdateError] = useState<string | null>(null);

  const [fetchError, setFetchError] = useState<{ status?: number; message?: string } | null>(null);

  const effectiveAccusedId = useMemo(() => {
    if (id) {
      if (!id.toLowerCase().startsWith("acc_") && id.toUpperCase().startsWith("UTP-")) {
        return `acc_${id.toLowerCase().replace("-", "_")}`;
      }
      return id;
    }
    if (user?.linked_case_id) {
      return `acc_${user.linked_case_id.toLowerCase().replace("-", "_")}`;
    }
    return "acc_utp_0001";
  }, [id, user?.linked_case_id]);

  useEffect(() => {
    const fetchProfileData = async () => {
      setLoading(true);
      setFetchError(null);
      try {
        // 1. Fetch Profile
        const profData = await fetchAccusedProfile(effectiveAccusedId);
        setProfile(profData);

        // 2. Fetch Timeline
        const timeData = await fetchAccusedTimeline(effectiveAccusedId);
        setTimeline(timeData);
      } catch (err: any) {
        console.error('Error fetching accused profile dossier:', err);
        const msg = err?.message || String(err);
        const is403 = msg.includes("403") || msg.includes("Forbidden") || msg.includes("authorized");
        setFetchError({
          status: is403 ? 403 : 404,
          message: is403
            ? "Access to this accused dossier is restricted by institutional scoping policies. Only assigned defense counsel, jurisdiction police stations, or custody facility officers may inspect this file."
            : `No consolidated records located for identifier: ${effectiveAccusedId}`,
        });
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchProfileData();
    }
  }, [effectiveAccusedId, token]);

  const handleOpenEditIdentity = () => {
    if (!profile) return;
    setEditFullName(profile.full_name || "");
    setEditAliases((profile.alias_names || []).join(", "));
    setEditFatherName(profile.father_name || profile.family_contacts?.find(fc => fc.relation?.toLowerCase().includes("father"))?.name || "");
    setEditGender(profile.gender || "Male");
    setEditAge(profile.age || 0);
    setUpdateReason("");
    setIdentityUpdateSuccess(null);
    setIdentityUpdateError(null);
    setIsEditIdentityOpen(true);
  };

  const handleSaveIdentity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!updateReason.trim() || updateReason.trim().length < 5) {
      setIdentityUpdateError("A substantive statutory update reason (minimum 5 characters) is required.");
      return;
    }
    setSavingIdentity(true);
    setIdentityUpdateError(null);
    try {
      await updateAccusedIdentity(effectiveAccusedId, {
        update_reason: updateReason.trim(),
        full_name: editFullName.trim() || undefined,
        aliases: editAliases.split(",").map(s => s.trim()).filter(Boolean),
        father_name: editFatherName.trim() || undefined,
        gender: editGender || undefined,
        age: editAge ? Number(editAge) : undefined,
      });
      setIdentityUpdateSuccess("Identity attributes updated successfully with supervisory audit seal.");
      const profData = await fetchAccusedProfile(effectiveAccusedId);
      setProfile(profData);
      setTimeout(() => {
        setIsEditIdentityOpen(false);
        setIdentityUpdateSuccess(null);
      }, 1200);
    } catch (err: any) {
      setIdentityUpdateError(err?.message || "Failed to update identity record.");
    } finally {
      setSavingIdentity(false);
    }
  };

  const backRoute =
    user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE"
      ? "/advocate"
      : user?.role === "POLICE_OFFICER"
      ? "/police"
      : user?.role === "JAIL_OFFICER"
      ? "/jail"
      : user?.role === "ACCUSED_USER"
      ? "/my-case"
      : user?.role === "FAMILY_GUARDIAN"
      ? "/family/status"
      : "/cases";

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!profile) {
    const isForbidden = fetchError?.status === 403;
    return (
      <div className="p-8 text-center bg-card rounded-xl border border-border max-w-2xl mx-auto my-12 shadow-sm">
        {isForbidden ? (
          <div className="w-12 h-12 rounded-full bg-amber-500/10 flex items-center justify-center mx-auto mb-3 border border-amber-500/20">
            <Lock className="h-6 w-6 text-amber-500" />
          </div>
        ) : (
          <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto mb-3" />
        )}
        <h2 className="text-xl font-bold font-serif text-foreground">
          {isForbidden ? "Institutional Access Restricted" : "Accused Profile Not Found"}
        </h2>
        <p className="text-muted-foreground mt-2 text-sm max-w-md mx-auto">
          {fetchError?.message || `No consolidated records located for identifier: ${effectiveAccusedId}`}
        </p>
        <Link to={backRoute} className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground text-xs font-bold font-mono uppercase rounded-sm hover:opacity-90 transition-opacity">
          <ArrowLeft className="h-4 w-4" /> Return to Assigned Workspace
        </Link>
      </div>
    );
  }

  const filteredTimeline = timeline.filter(item => {
    if (timelineFilter === 'ALL') return true;
    return item.item_type === timelineFilter;
  });

  return (
    <div className="space-y-8 pb-16 max-w-7xl mx-auto text-base">
      {/* Back Navigation & Breadcrumb — Enlarged */}
      <div className="flex items-center justify-between">
        <Link to={backRoute} className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" /> Back to Dashboard / Workspace
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs px-3 py-1.5 rounded-full font-mono font-bold bg-secondary border border-border text-foreground shadow-sm">
            OPAQUE REF: {profile.id}
          </span>
          <span className="text-xs px-3.5 py-1.5 rounded-full font-bold bg-emerald-500/10 text-emerald-600 border border-emerald-500/30 shadow-sm">
            {profile.provenance.verification_status}
          </span>
        </div>
      </div>

      {/* Hero Header Card — Zoomed In */}
      <div className="bg-card border-2 border-border rounded-2xl p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-5">
            <div className="h-20 w-20 rounded-2xl bg-primary/10 border-2 border-primary/20 flex items-center justify-center text-primary font-extrabold text-3xl shadow-sm shrink-0">
              {profile.full_name.charAt(0)}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-foreground">{profile.full_name}</h1>
                {profile.alias_names.length > 0 && (
                  <span className="text-sm text-muted-foreground font-normal">
                    (Aliases: {profile.alias_names.join(', ')})
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-y-2 gap-x-5 mt-2.5 text-sm text-muted-foreground">
                <span><strong>Gender:</strong> {profile.gender}</span>
                <span>•</span>
                <span><strong>Age:</strong> {profile.age} Yrs</span>
                <span>•</span>
                <span><strong>Language:</strong> {profile.preferred_language.toUpperCase()}</span>
                <span>•</span>
                <span><strong>Address:</strong> {profile.permanent_address}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 border-t md:border-t-0 pt-4 md:pt-0 border-border shrink-0">
            <div className="text-right">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">Connected Cases</span>
              <span className="text-2xl font-extrabold text-primary mt-0.5 block">{profile.total_cases_count} Multi-Facility Matters</span>
            </div>
          </div>
        </div>

        {/* Provenance Footer */}
        <div className="mt-6 pt-4 border-t border-border flex flex-wrap items-center justify-between gap-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-primary" />
            <span>Authoritative Source: <strong>{profile.provenance.source_system}</strong> (Ref: {profile.provenance.source_record_id})</span>
          </div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-emerald-500" />
            <span>Confidence Score: <strong>{(profile.provenance.confidence_score * 100).toFixed(0)}%</strong></span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs — Larger & Clearer */}
      <div className="flex items-center gap-2.5 border-b-2 border-border overflow-x-auto pb-2">
        <button
          onClick={() => setActiveTab('cases')}
          className={`px-5 py-3 text-sm font-bold rounded-xl flex items-center gap-2.5 transition-all whitespace-nowrap shadow-sm ${
            activeTab === 'cases' 
              ? 'bg-primary text-primary-foreground shadow-md' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Layers className="h-4 w-4" /> Connected Court Cases ({profile.total_cases_count})
        </button>

        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-5 py-3 text-sm font-bold rounded-xl flex items-center gap-2.5 transition-all whitespace-nowrap shadow-sm ${
            activeTab === 'timeline' 
              ? 'bg-primary text-primary-foreground shadow-md' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Clock className="h-4 w-4" /> Facts vs. Interpretations Timeline ({timeline.length})
        </button>

        <button
          onClick={() => setActiveTab('medical')}
          className={`px-5 py-3 text-sm font-bold rounded-xl flex items-center gap-2.5 transition-all whitespace-nowrap shadow-sm ${
            activeTab === 'medical' 
              ? 'bg-primary text-primary-foreground shadow-md' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <HeartPulse className="h-4 w-4" /> Restricted Health Dossier
          {profile.medical_record?.is_redacted && <Lock className="h-3.5 w-3.5 text-amber-500" />}
        </button>

        <button
          onClick={() => setActiveTab('family')}
          className={`px-5 py-3 text-sm font-bold rounded-xl flex items-center gap-2.5 transition-all whitespace-nowrap shadow-sm ${
            activeTab === 'family' 
              ? 'bg-primary text-primary-foreground shadow-md' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Phone className="h-4 w-4" /> Family & Communication ({profile.family_contacts.length})
        </button>

        <button
          onClick={() => setActiveTab('identity')}
          className={`px-5 py-3 text-sm font-bold rounded-xl flex items-center gap-2.5 transition-all whitespace-nowrap shadow-sm ${
            activeTab === 'identity' 
              ? 'bg-primary text-primary-foreground shadow-md' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Lock className="h-4 w-4" /> Restricted Identifiers
        </button>
      </div>


      {/* Tab 1: Connected Cases — Zoomed Cards */}
      {activeTab === 'cases' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {profile.connected_cases.map((c) => (
              <div key={c.case_id} className="bg-card border-2 border-border rounded-2xl p-6 shadow-sm hover:border-primary/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-mono font-bold text-primary px-2.5 py-1 rounded bg-primary/10 border border-primary/20">{c.case_id}</span>
                    <h3 className="text-lg font-bold text-foreground mt-2">{c.court_name}</h3>
                  </div>
                  <span className={`text-xs px-3 py-1.5 rounded-full font-bold shadow-sm ${
                    c.current_status === 'APPROVED_READY_FOR_FILING' ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/30' :
                    c.current_status === 'ELIGIBLE' ? 'bg-amber-500/10 text-amber-600 border border-amber-500/30' :
                    'bg-secondary text-muted-foreground border border-border'
                  }`}>
                    {c.current_status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 my-5 text-xs md:text-sm text-muted-foreground bg-secondary/50 p-4 rounded-xl border border-border/50">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">Police Station &amp; FIR</span>
                    <span className="font-semibold text-foreground mt-0.5 block">{c.police_station} ({c.fir_number})</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">Assigned Advocate</span>
                    <span className="font-semibold text-foreground mt-0.5 block">{c.assigned_lawyer}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">Detention Days</span>
                    <span className="font-semibold text-foreground mt-0.5 block">{c.days_in_custody} / {c.max_sentence_days} Max Days</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground block tracking-wider">Next Hearing</span>
                    <span className="font-semibold text-foreground mt-0.5 block">{c.next_hearing_date}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-border">
                  <div className="flex items-center gap-2 text-sm">
                    <Scale className="h-4 w-4 text-primary" />
                    <span>Section 479 Eligibility: <strong>{c.eligible_under_479 ? 'ELIGIBLE' : 'PENDING'}</strong></span>
                  </div>
                  <Link
                    to={`/case/${c.case_id}`}
                    className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:underline"
                  >
                    View Case File <ExternalLink className="h-4 w-4" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Facts vs Interpretations Timeline — Zoomed In */}
      {activeTab === 'timeline' && (
        <div className="space-y-6">
          {/* Filter Toolbar */}
          <div className="bg-secondary/50 border-2 border-border rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="text-sm font-bold text-foreground">Filter Event Category:</span>
              <button
                onClick={() => setTimelineFilter('ALL')}
                className={`px-4 py-2 text-xs md:text-sm rounded-lg font-bold transition-all ${timelineFilter === 'ALL' ? 'bg-primary text-primary-foreground shadow' : 'bg-card text-foreground border border-border hover:bg-muted'}`}
              >
                All Events ({timeline.length})
              </button>
              <button
                onClick={() => setTimelineFilter('FACTUAL_EVENT')}
                className={`px-4 py-2 text-xs md:text-sm rounded-lg font-bold transition-all ${timelineFilter === 'FACTUAL_EVENT' ? 'bg-emerald-600 text-white shadow' : 'bg-card text-foreground border border-border hover:bg-muted'}`}
              >
                Official Court Records Only
              </button>
              <button
                onClick={() => setTimelineFilter('SYSTEM_INTERPRETATION')}
                className={`px-4 py-2 text-xs md:text-sm rounded-lg font-bold transition-all ${timelineFilter === 'SYSTEM_INTERPRETATION' ? 'bg-purple-600 text-white shadow' : 'bg-card text-foreground border border-border hover:bg-muted'}`}
              >
                Legal Assessments &amp; Milestones
              </button>
            </div>
            <span className="text-xs text-muted-foreground font-medium">
              Strictly segregated for evidentiary provenance
            </span>
          </div>

          {/* Chronological Stream */}
          <div className="relative pl-8 border-l-2 border-border space-y-6 my-6">
            {filteredTimeline.map((item) => (
              <div key={item.id} className="relative group">
                {/* Timeline Dot Indicator */}
                <div className={`absolute -left-[41px] top-2 h-5 w-5 rounded-full border-2 bg-background flex items-center justify-center shadow-sm ${
                  item.item_type === 'FACTUAL_EVENT' 
                    ? 'border-emerald-500 text-emerald-500' 
                    : 'border-purple-500 text-purple-500'
                }`}>
                  <div className={`h-2 w-2 rounded-full ${item.item_type === 'FACTUAL_EVENT' ? 'bg-emerald-500' : 'bg-purple-500'}`} />
                </div>

                <div className="bg-card border-2 border-border rounded-2xl p-6 shadow-sm space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <span className={`text-xs px-3 py-1 rounded-md font-bold uppercase ${
                        item.item_type === 'FACTUAL_EVENT'
                          ? 'bg-emerald-500/15 text-emerald-600 border border-emerald-500/30'
                          : 'bg-purple-500/15 text-purple-600 border border-purple-500/30'
                      }`}>
                        {item.item_type === 'FACTUAL_EVENT' ? 'Factual Record' : 'System Interpretation'}
                      </span>
                      <span className="text-xs font-mono font-bold text-muted-foreground">{item.category}</span>
                    </div>

                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>{new Date(item.event_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                    </div>
                  </div>

                  <h4 className="text-base md:text-lg font-bold text-foreground">{item.title}</h4>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.description}</p>

                  <div className="pt-3 border-t border-border flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
                    <div>
                      <span>Source: <strong>{item.source_name}</strong></span>
                      {item.source_record_id && <span className="ml-2 font-mono">({item.source_record_id})</span>}
                    </div>
                    <div>
                      <span>Recorded By: <strong>{item.recorded_by}</strong></span>
                      <span className="ml-3 px-2 py-0.5 rounded bg-secondary font-bold text-foreground border border-border">
                        {item.verification_status}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Restricted Medical Dossier — Zoomed In */}
      {activeTab === 'medical' && (
        <div className="bg-card border-2 border-border rounded-2xl p-8 space-y-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-border pb-5">
            <div className="flex items-center gap-4">
              <div className="h-12 w-12 rounded-xl bg-rose-500/10 border-2 border-rose-500/20 flex items-center justify-center text-rose-500 shrink-0">
                <HeartPulse className="h-7 w-7" />
              </div>
              <div>
                <h3 className="text-xl font-extrabold text-foreground">Restricted Health &amp; Vulnerability Profile</h3>
                <p className="text-sm text-muted-foreground mt-0.5">Protected medical records under DPDP Act &amp; Institutional Medical Protocols</p>
              </div>
            </div>

            {profile.medical_record?.is_redacted ? (
              <span className="px-3.5 py-1.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-600 border border-amber-500/30 flex items-center gap-2 shadow-sm">
                <Lock className="h-4 w-4" /> REDACTED ENVELOPE
              </span>
            ) : (
              <span className="px-3.5 py-1.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 border border-emerald-500/30 flex items-center gap-2 shadow-sm">
                <CheckCircle2 className="h-4 w-4" /> AUTHORIZED CLEARANCE
              </span>
            )}
          </div>

          {profile.medical_record?.is_redacted ? (
            <div className="p-10 text-center bg-secondary/40 rounded-xl border-2 border-border space-y-3">
              <Lock className="h-12 w-12 text-muted-foreground mx-auto mb-2" />
              <h4 className="text-base font-bold text-foreground">Medical Details Are Quarantined</h4>
              <p className="text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
                {profile.medical_record.details_restricted}
              </p>
              <span className="inline-block text-xs text-muted-foreground pt-2">
                Logged in as <strong>{user?.role}</strong>. Requires statutory medical clearance authority (DLSA Officer or Supervising Legal Officer only under Section 479 BNSS / DPDP Act).
              </span>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-secondary/50 p-5 rounded-xl border-2 border-border">
                  <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground block">Health Vulnerability Status</span>
                  <span className={`text-base font-extrabold mt-1 block ${profile.medical_record?.has_vulnerability ? 'text-rose-500' : 'text-emerald-500'}`}>
                    {profile.medical_record?.has_vulnerability ? 'CRITICAL / ELEVATED RISK' : 'NORMAL INTAKE FIT'}
                  </span>
                </div>

                <div className="bg-secondary/50 p-5 rounded-xl border-2 border-border">
                  <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground block">Examining Medical Officer</span>
                  <span className="text-base font-bold text-foreground mt-1 block">
                    {profile.medical_record?.medical_officer_name || 'Chief Medical Officer'}
                  </span>
                </div>

                <div className="bg-secondary/50 p-5 rounded-xl border-2 border-border">
                  <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground block">Last Clinical Review Date</span>
                  <span className="text-base font-bold text-foreground mt-1 block">
                    {profile.medical_record?.last_examination_date || 'Intake Date'}
                  </span>
                </div>
              </div>

              <div className="bg-secondary/30 p-5 rounded-xl border-2 border-border">
                <span className="text-sm font-bold text-foreground block mb-2">Clinical Remarks &amp; Hospital Referral Directives:</span>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {profile.medical_record?.details_restricted}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Family & Communication Preferences — Zoomed In */}
      {activeTab === 'family' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {profile.family_contacts.map((c, idx) => (
              <div key={idx} className="bg-card border-2 border-border rounded-2xl p-6 space-y-4 shadow-sm">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3.5">
                    <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center text-primary font-extrabold text-lg shrink-0">
                      {c.name.charAt(0)}
                    </div>
                    <div>
                      <h4 className="text-base font-bold text-foreground">{c.name}</h4>
                      <span className="text-xs text-muted-foreground">{c.relation}</span>
                    </div>
                  </div>
                  {c.is_primary_contact && (
                    <span className="text-xs px-2.5 py-1 rounded-md font-bold bg-primary/10 text-primary border border-primary/20">
                      PRIMARY GUARDIAN
                    </span>
                  )}
                </div>

                <div className="space-y-2.5 text-sm text-muted-foreground pt-3 border-t-2 border-border">
                  <div className="flex items-center justify-between">
                    <span>Phone Number:</span>
                    <strong className="text-foreground font-mono">{c.phone}</strong>
                  </div>
                  {c.alt_phone && (
                    <div className="flex items-center justify-between">
                      <span>Alternate Phone:</span>
                      <strong className="text-foreground font-mono">{c.alt_phone}</strong>
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span>Preferred Language:</span>
                    <strong className="text-foreground">{c.preferred_language.toUpperCase()}</strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Notification Channel:</span>
                    <strong className="text-foreground">{c.preferred_channel}</strong>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 5: Restricted Identifiers — Zoomed In */}
      {activeTab === 'identity' && (
        <div className="bg-card border-2 border-border rounded-2xl p-8 space-y-5 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
            <div>
              <h3 className="text-base font-bold text-foreground flex items-center gap-2.5">
                <Lock className="h-5 w-5 text-primary" /> Restricted Government Registry Identifiers
              </h3>
              <p className="text-sm text-muted-foreground mt-0.5">
                Quarantined identity references accessible strictly to authorized state authorities.
              </p>
            </div>
            {can("IDENTITY_UPDATE") && (
              <button
                onClick={handleOpenEditIdentity}
                className="px-3.5 py-2 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity self-start sm:self-auto"
              >
                <Edit3 className="w-3.5 h-3.5" /> Edit Legal Identity
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-3">
            {profile.government_identifiers && Object.entries(profile.government_identifiers).map(([k, v]) => (
              <div key={k} className="p-4 bg-secondary/50 rounded-xl border-2 border-border">
                <span className="text-xs uppercase font-bold tracking-wider text-muted-foreground block font-mono">
                  {k.replace(/_/g, ' ')}
                </span>
                <span className="text-sm font-mono font-bold text-foreground mt-1 block">
                  {typeof v === 'string' ? v : JSON.stringify(v)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Identity Edit Modal — Authorized Supervising Legal Officer Only */}
      {isEditIdentityOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="bg-card border-2 border-border rounded-xl shadow-2xl max-w-lg w-full p-6 space-y-4 animate-in fade-in zoom-in duration-150 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-primary" />
                <h3 className="font-serif font-bold text-lg text-foreground">
                  Update Consolidated Legal Identity
                </h3>
              </div>
              <button
                onClick={() => setIsEditIdentityOpen(false)}
                className="p-1 text-muted-foreground hover:text-foreground rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-xs font-mono bg-blue-500/10 text-blue-700 dark:text-blue-300 p-3 rounded border border-blue-500/20">
              <strong>Supervisory Identity Revision:</strong> Changes will be committed to the canonical accused registry and logged in the immutable audit ledger with statutory actor credentials.
            </div>

            {identityUpdateSuccess && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-mono rounded flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>{identityUpdateSuccess}</span>
              </div>
            )}

            {identityUpdateError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs font-mono rounded flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{identityUpdateError}</span>
              </div>
            )}

            <form onSubmit={handleSaveIdentity} className="space-y-3.5 text-xs font-mono">
              <div>
                <label className="block text-muted-foreground font-semibold mb-1">
                  Full Legal Name
                </label>
                <input
                  type="text"
                  value={editFullName}
                  onChange={(e) => setEditFullName(e.target.value)}
                  className="w-full px-3 py-2 bg-secondary border border-border rounded text-foreground font-sans text-sm focus:outline-hidden focus:border-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-muted-foreground font-semibold mb-1">
                  Recognized Aliases (comma separated)
                </label>
                <input
                  type="text"
                  value={editAliases}
                  onChange={(e) => setEditAliases(e.target.value)}
                  placeholder="e.g. Suresh @ Langda, Suri"
                  className="w-full px-3 py-2 bg-secondary border border-border rounded text-foreground font-sans text-sm focus:outline-hidden focus:border-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-muted-foreground font-semibold mb-1">
                    Father's / Guardian's Name
                  </label>
                  <input
                    type="text"
                    value={editFatherName}
                    onChange={(e) => setEditFatherName(e.target.value)}
                    className="w-full px-3 py-2 bg-secondary border border-border rounded text-foreground font-sans text-sm focus:outline-hidden focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground font-semibold mb-1">
                    Gender
                  </label>
                  <select
                    value={editGender}
                    onChange={(e) => setEditGender(e.target.value)}
                    className="w-full px-3 py-2 bg-secondary border border-border rounded text-foreground font-sans text-sm focus:outline-hidden focus:border-primary"
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Transgender">Transgender</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground font-semibold mb-1">
                  Age (Years)
                </label>
                <input
                  type="number"
                  min="18"
                  max="120"
                  value={editAge || ""}
                  onChange={(e) => setEditAge(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 bg-secondary border border-border rounded text-foreground font-sans text-sm focus:outline-hidden focus:border-primary"
                />
              </div>

              <div>
                <label className="block text-rose-500 font-semibold mb-1">
                  * Statutory Modification Reason (Required, min 5 chars)
                </label>
                <textarea
                  value={updateReason}
                  onChange={(e) => setUpdateReason(e.target.value)}
                  rows={3}
                  placeholder="e.g. Identity correction pursuant to verified Aadhaar/Voter ID submission during DLSA camp..."
                  className="w-full px-3 py-2 bg-secondary border border-border rounded text-foreground font-sans text-xs focus:outline-hidden focus:border-primary"
                  required
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setIsEditIdentityOpen(false)}
                  className="px-4 py-2 bg-secondary text-foreground rounded text-xs font-mono font-semibold hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingIdentity}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded text-xs font-mono font-bold flex items-center gap-1.5 hover:opacity-90 disabled:opacity-50"
                >
                  {savingIdentity ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                  {savingIdentity ? "Saving Revisions..." : "Commit Identity Revisions"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
export default AccusedProfilePage;
