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
    <div className="space-y-6 pb-12">
      {/* Back Navigation & Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link to="/cases" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to Case Master
        </Link>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded-full font-mono bg-secondary border border-border text-foreground">
            OPAQUE REF: {profile.id}
          </span>
          <span className="text-xs px-2.5 py-1 rounded-full font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
            {profile.provenance.verification_status}
          </span>
        </div>
      </div>

      {/* Hero Header Card */}
      <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="h-16 w-16 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold text-2xl">
              {profile.full_name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-foreground">{profile.full_name}</h1>
                {profile.alias_names.length > 0 && (
                  <span className="text-xs text-muted-foreground font-normal">
                    (Aliases: {profile.alias_names.join(', ')})
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-y-1 gap-x-4 mt-1.5 text-xs text-muted-foreground">
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

          <div className="flex flex-wrap items-center gap-2 border-t md:border-t-0 pt-3 md:pt-0 border-border">
            <div className="text-right">
              <span className="text-xs text-muted-foreground block">Connected Cases</span>
              <span className="text-lg font-bold text-primary">{profile.total_cases_count} Multi-Facility Matters</span>
            </div>
          </div>
        </div>

        {/* Provenance Footer */}
        <div className="mt-4 pt-3 border-t border-border/60 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Building2 className="h-3.5 w-3.5 text-primary" />
            <span>Authoritative Source: <strong>{profile.provenance.source_system}</strong> (Ref: {profile.provenance.source_record_id})</span>
          </div>
          <div className="flex items-center gap-1.5">
            <ShieldAlert className="h-3.5 w-3.5 text-emerald-500" />
            <span>Confidence Score: <strong>{(profile.provenance.confidence_score * 100).toFixed(0)}%</strong></span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-border overflow-x-auto pb-1">
        <button
          onClick={() => setActiveTab('cases')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'cases' 
              ? 'bg-primary text-primary-foreground shadow-sm' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Layers className="h-4 w-4" /> Connected Court Cases ({profile.total_cases_count})
        </button>

        <button
          onClick={() => setActiveTab('timeline')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'timeline' 
              ? 'bg-primary text-primary-foreground shadow-sm' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Clock className="h-4 w-4" /> Facts vs. Interpretations Timeline ({timeline.length})
        </button>

        <button
          onClick={() => setActiveTab('medical')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'medical' 
              ? 'bg-primary text-primary-foreground shadow-sm' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <HeartPulse className="h-4 w-4" /> Restricted Health Dossier
          {profile.medical_record?.is_redacted && <Lock className="h-3.5 w-3.5 text-amber-500" />}
        </button>

        <button
          onClick={() => setActiveTab('family')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'family' 
              ? 'bg-primary text-primary-foreground shadow-sm' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Phone className="h-4 w-4" /> Family & Communication ({profile.family_contacts.length})
        </button>

        <button
          onClick={() => setActiveTab('identity')}
          className={`px-4 py-2 text-sm font-medium rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap ${
            activeTab === 'identity' 
              ? 'bg-primary text-primary-foreground shadow-sm' 
              : 'text-muted-foreground hover:text-foreground hover:bg-secondary'
          }`}
        >
          <Lock className="h-4 w-4" /> Restricted Identifiers
        </button>
      </div>

      {/* Tab 1: Connected Cases */}
      {activeTab === 'cases' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profile.connected_cases.map((c) => (
              <div key={c.case_id} className="bg-card border border-border rounded-xl p-5 shadow-sm hover:border-primary/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-mono font-bold text-primary">{c.case_id}</span>
                    <h3 className="text-base font-semibold text-foreground mt-0.5">{c.court_name}</h3>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-semibold ${
                    c.current_status === 'APPROVED_READY_FOR_FILING' ? 'bg-emerald-500/10 text-emerald-600' :
                    c.current_status === 'ELIGIBLE' ? 'bg-amber-500/10 text-amber-600' :
                    'bg-secondary text-muted-foreground'
                  }`}>
                    {c.current_status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 my-4 text-xs text-muted-foreground bg-secondary/40 p-3 rounded-lg">
                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block">Police Station & FIR</span>
                    <span className="font-medium text-foreground">{c.police_station} ({c.fir_number})</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block">Assigned Advocate</span>
                    <span className="font-medium text-foreground">{c.assigned_lawyer}</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block">Detention Days</span>
                    <span className="font-medium text-foreground">{c.days_in_custody} / {c.max_sentence_days} Max Days</span>
                  </div>
                  <div>
                    <span className="text-[10px] uppercase text-muted-foreground block">Next Hearing</span>
                    <span className="font-medium text-foreground">{c.next_hearing_date}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-border">
                  <div className="flex items-center gap-1.5 text-xs">
                    <Scale className="h-3.5 w-3.5 text-primary" />
                    <span>Section 479 Eligibility: <strong>{c.eligible_under_479 ? 'ELIGIBLE' : 'PENDING'}</strong></span>
                  </div>
                  <Link
                    to={`/cases`}
                    className="inline-flex items-center gap-1 text-xs text-primary font-medium hover:underline"
                  >
                    View Case File <ExternalLink className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Facts vs Interpretations Timeline */}
      {activeTab === 'timeline' && (
        <div className="space-y-4">
          {/* Filter Toolbar */}
          <div className="bg-secondary/40 border border-border rounded-lg p-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-muted-foreground">Filter Event Category:</span>
              <button
                onClick={() => setTimelineFilter('ALL')}
                className={`px-3 py-1 text-xs rounded-md font-medium ${timelineFilter === 'ALL' ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground border border-border'}`}
              >
                All Events ({timeline.length})
              </button>
              <button
                onClick={() => setTimelineFilter('FACTUAL_EVENT')}
                className={`px-3 py-1 text-xs rounded-md font-medium ${timelineFilter === 'FACTUAL_EVENT' ? 'bg-emerald-600 text-white' : 'bg-card text-foreground border border-border'}`}
              >
                Ground-Truth Facts Only
              </button>
              <button
                onClick={() => setTimelineFilter('SYSTEM_INTERPRETATION')}
                className={`px-3 py-1 text-xs rounded-md font-medium ${timelineFilter === 'SYSTEM_INTERPRETATION' ? 'bg-purple-600 text-white' : 'bg-card text-foreground border border-border'}`}
              >
                System Interpretations Only
              </button>
            </div>
            <span className="text-xs text-muted-foreground">
              Strictly segregated for evidentiary provenance
            </span>
          </div>

          {/* Chronological Stream */}
          <div className="relative pl-6 border-l-2 border-border space-y-6 my-4">
            {filteredTimeline.map((item) => (
              <div key={item.id} className="relative group">
                {/* Timeline Dot Indicator */}
                <div className={`absolute -left-[31px] top-1.5 h-4 w-4 rounded-full border-2 bg-background flex items-center justify-center ${
                  item.item_type === 'FACTUAL_EVENT' 
                    ? 'border-emerald-500 text-emerald-500' 
                    : 'border-purple-500 text-purple-500'
                }`}>
                  <div className={`h-1.5 w-1.5 rounded-full ${item.item_type === 'FACTUAL_EVENT' ? 'bg-emerald-500' : 'bg-purple-500'}`} />
                </div>

                <div className="bg-card border border-border rounded-xl p-4 shadow-sm space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                        item.item_type === 'FACTUAL_EVENT'
                          ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
                          : 'bg-purple-500/10 text-purple-600 border border-purple-500/20'
                      }`}>
                        {item.item_type === 'FACTUAL_EVENT' ? 'Factual Record' : 'System Interpretation'}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground">{item.category}</span>
                    </div>

                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Calendar className="h-3.5 w-3.5" />
                      <span>{new Date(item.event_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                    </div>
                  </div>

                  <h4 className="text-sm font-bold text-foreground">{item.title}</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">{item.description}</p>

                  <div className="pt-2 border-t border-border flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
                    <div>
                      <span>Source: <strong>{item.source_name}</strong></span>
                      {item.source_record_id && <span className="ml-2 font-mono">({item.source_record_id})</span>}
                    </div>
                    <div>
                      <span>Recorded By: <strong>{item.recorded_by}</strong></span>
                      <span className="ml-3 px-1.5 py-0.5 rounded bg-secondary font-semibold text-foreground">
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

      {/* Tab 3: Restricted Medical Dossier */}
      {activeTab === 'medical' && (
        <div className="bg-card border border-border rounded-xl p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500">
                <HeartPulse className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground">Restricted Health & Vulnerability Profile</h3>
                <p className="text-xs text-muted-foreground">Protected medical records under DPDP Act & Institutional Medical Protocols</p>
              </div>
            </div>

            {profile.medical_record?.is_redacted ? (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 border border-amber-500/20 flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5" /> REDACTED ENVELOPE
              </span>
            ) : (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> AUTHORIZED CLEARANCE
              </span>
            )}
          </div>

          {profile.medical_record?.is_redacted ? (
            <div className="p-8 text-center bg-secondary/30 rounded-lg border border-border space-y-2">
              <Lock className="h-10 w-10 text-muted-foreground mx-auto mb-2" />
              <h4 className="text-sm font-semibold text-foreground">Medical Details Are Quarantined</h4>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                {profile.medical_record.details_restricted}
              </p>
              <span className="inline-block text-[11px] text-muted-foreground pt-2">
                Logged in as <strong>{user?.role}</strong>. Requires medical clearance role (DLSA, Supervising Officer, Jail Medical Staff).
              </span>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-secondary/40 p-3.5 rounded-lg border border-border">
                  <span className="text-[10px] uppercase text-muted-foreground block">Health Vulnerability Status</span>
                  <span className={`text-sm font-bold ${profile.medical_record?.has_vulnerability ? 'text-rose-500' : 'text-emerald-500'}`}>
                    {profile.medical_record?.has_vulnerability ? 'CRITICAL / ELEVATED RISK' : 'NORMAL INTAKE FIT'}
                  </span>
                </div>

                <div className="bg-secondary/40 p-3.5 rounded-lg border border-border">
                  <span className="text-[10px] uppercase text-muted-foreground block">Examining Medical Officer</span>
                  <span className="text-sm font-semibold text-foreground">
                    {profile.medical_record?.medical_officer_name || 'Chief Medical Officer'}
                  </span>
                </div>

                <div className="bg-secondary/40 p-3.5 rounded-lg border border-border">
                  <span className="text-[10px] uppercase text-muted-foreground block">Last Clinical Review Date</span>
                  <span className="text-sm font-semibold text-foreground">
                    {profile.medical_record?.last_examination_date || 'Intake Date'}
                  </span>
                </div>
              </div>

              <div className="bg-secondary/20 p-4 rounded-lg border border-border">
                <span className="text-xs font-bold text-foreground block mb-1">Clinical Remarks & Hospital Referral Directives:</span>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {profile.medical_record?.details_restricted}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Family & Communication Preferences */}
      {activeTab === 'family' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profile.family_contacts.map((c, idx) => (
              <div key={idx} className="bg-card border border-border rounded-xl p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                      {c.name.charAt(0)}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-foreground">{c.name}</h4>
                      <span className="text-xs text-muted-foreground">{c.relation}</span>
                    </div>
                  </div>
                  {c.is_primary_contact && (
                    <span className="text-[10px] px-2 py-0.5 rounded font-semibold bg-primary/10 text-primary border border-primary/20">
                      PRIMARY GUARDIAN
                    </span>
                  )}
                </div>

                <div className="space-y-2 text-xs text-muted-foreground pt-2 border-t border-border">
                  <div className="flex items-center justify-between">
                    <span>Phone Number:</span>
                    <strong className="text-foreground">{c.phone}</strong>
                  </div>
                  {c.alt_phone && (
                    <div className="flex items-center justify-between">
                      <span>Alternate Phone:</span>
                      <strong className="text-foreground">{c.alt_phone}</strong>
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

      {/* Tab 5: Restricted Identifiers */}
      {activeTab === 'identity' && (
        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Lock className="h-4 w-4 text-primary" /> Restricted Government Registry Identifiers
          </h3>
          <p className="text-xs text-muted-foreground">
            Quarantined identity references accessible strictly to authorized state authorities.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            {profile.government_identifiers && Object.entries(profile.government_identifiers).map(([k, v]) => (
              <div key={k} className="p-3 bg-secondary/40 rounded-lg border border-border">
                <span className="text-[10px] uppercase text-muted-foreground block font-mono">
                  {k.replace(/_/g, ' ')}
                </span>
                <span className="text-xs font-mono font-semibold text-foreground">
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
