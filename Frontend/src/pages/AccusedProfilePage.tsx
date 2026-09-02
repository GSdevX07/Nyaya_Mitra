import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { fetchAccusedProfile, fetchAccusedTimeline } from '../lib/api';
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
  Scale
} from 'lucide-react';

interface AccusedProfile {
  id: string;
  full_name: string;
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
  const { token, user } = useAuth();
  const [profile, setProfile] = useState<AccusedProfile | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'cases' | 'timeline' | 'medical' | 'family' | 'identity'>('cases');
  const [timelineFilter, setTimelineFilter] = useState<'ALL' | 'FACTUAL_EVENT' | 'SYSTEM_INTERPRETATION'>('ALL');

  const accusedId = id || 'acc_utp_0001';

  useEffect(() => {
    const fetchProfileData = async () => {
      setLoading(true);
      try {
        // 1. Fetch Profile
        const profData = await fetchAccusedProfile(accusedId);
        setProfile(profData);

        // 2. Fetch Timeline
        const timeData = await fetchAccusedTimeline(accusedId);
        setTimeline(timeData);
      } catch (err) {
        console.error('Error fetching accused profile dossier:', err);
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchProfileData();
    }
  }, [accusedId, token]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-8 text-center bg-card rounded-xl border border-border">
        <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto mb-3" />
        <h2 className="text-xl font-bold">Accused Profile Not Found</h2>
        <p className="text-muted-foreground mt-1">No consolidated records located for identifier: {accusedId}</p>
        <Link to="/cases" className="mt-4 inline-flex items-center gap-2 text-primary hover:underline text-sm font-medium">
          <ArrowLeft className="h-4 w-4" /> Return to Cases Ledger
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
        <Link to="/cases" className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="h-4 w-4" /> Back to Case Master
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
                Ground-Truth Facts Only
              </button>
              <button
                onClick={() => setTimelineFilter('SYSTEM_INTERPRETATION')}
                className={`px-4 py-2 text-xs md:text-sm rounded-lg font-bold transition-all ${timelineFilter === 'SYSTEM_INTERPRETATION' ? 'bg-purple-600 text-white shadow' : 'bg-card text-foreground border border-border hover:bg-muted'}`}
              >
                System Interpretations Only
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
                Logged in as <strong>{user?.role}</strong>. Requires medical clearance role (DLSA, Supervising Officer, Jail Medical Staff).
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
          <h3 className="text-base font-bold text-foreground flex items-center gap-2.5">
            <Lock className="h-5 w-5 text-primary" /> Restricted Government Registry Identifiers
          </h3>
          <p className="text-sm text-muted-foreground">
            Quarantined identity references accessible strictly to authorized state authorities.
          </p>

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
    </div>
  );
};
export default AccusedProfilePage;
