import React, { useState, useEffect } from 'react';
import { useAuth } from '../lib/auth';
import { fetchDuplicateCandidates, resolveDuplicateCandidate } from '../lib/api';
import {
  GitMerge,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Fingerprint,
  Layers,
  Sparkles,
  Shield,
} from 'lucide-react';

interface DuplicateCandidate {
  id: string;
  source_accused_id: string;
  source_name: string;
  source_facility: string;
  source_father_name: string;
  source_dob: string;
  candidate_accused_id: string;
  candidate_name: string;
  candidate_facility: string;
  candidate_father_name: string;
  candidate_dob: string;
  match_confidence: number;
  shared_traits: string[];
  conflicting_traits: string[];
  match_explanation: string;
  review_status: string;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
  resolution_notes?: string;
}

export const IdentityResolutionPage: React.FC = () => {
  const { token, user } = useAuth();
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCandidate, setSelectedCandidate] = useState<DuplicateCandidate | null>(null);
  const [resolutionAction, setResolutionAction] = useState<'MERGE_RECORDS' | 'REJECT_MATCH' | 'MARK_AS_ALIAS' | null>(null);
  const [notes, setNotes] = useState('');
  const [confirmMerge, setConfirmMerge] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);
  const [actionErrorMessage, setActionErrorMessage] = useState<string | null>(null);
  const [viewTab, setViewTab] = useState<'PENDING' | 'ALL'>('PENDING');

  useEffect(() => {
    fetchCandidates(viewTab);
  }, [token, viewTab]);

  const fetchCandidates = async (tab: 'PENDING' | 'ALL' = viewTab) => {
    setLoading(true);
    setActionErrorMessage(null);
    try {
      const data = await fetchDuplicateCandidates(tab === 'PENDING' ? 'PENDING_HUMAN_REVIEW' : 'ALL');
      setCandidates(data);
      if (data.length > 0) {
        setSelectedCandidate(data[0]);
      } else {
        setSelectedCandidate(null);
      }
    } catch (err: any) {
      console.error('Error fetching duplicate candidates:', err);
      setActionErrorMessage(err?.message || 'Failed to fetch duplicate candidate records');
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedCandidate || !resolutionAction) return;
    setSubmitting(true);
    setActionErrorMessage(null);
    try {
      const candidateIdToResolve = selectedCandidate.id;
      const result = await resolveDuplicateCandidate({
        candidate_id: candidateIdToResolve,
        action: resolutionAction,
        resolution_notes: notes || `Resolved as ${resolutionAction} by ${user?.full_name || user?.role || 'Legal Officer'}`,
      });

      setActionSuccessMessage(result.message || `Candidate record ${candidateIdToResolve} resolved successfully.`);
      setResolutionAction(null);
      setNotes('');
      setConfirmMerge(false);

      // Optimistically update candidate list
      if (viewTab === 'PENDING') {
        setCandidates(prev => {
          const remaining = prev.filter(c => c.id !== candidateIdToResolve);
          if (remaining.length > 0) {
            setSelectedCandidate(remaining[0]);
          } else {
            setSelectedCandidate(null);
          }
          return remaining;
        });
      }
      // Re-fetch in background
      await fetchCandidates(viewTab);
    } catch (err: any) {
      console.error('Resolution submission failed:', err);
      setActionErrorMessage(err?.message || 'Resolution submission failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16 max-w-7xl mx-auto text-base">
      {/* Header — Enlarged & Zoomed In */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            <Fingerprint className="h-9 w-9 text-primary" /> Identity Resolution & De-duplication Review
          </h1>
          <p className="text-base text-muted-foreground mt-2 max-w-3xl leading-relaxed">
            Human-in-the-loop review queue for probable duplicate accused person records detected across detention facilities and court jurisdictions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-secondary p-1 rounded-xl border border-border">
            <button
              onClick={() => setViewTab('PENDING')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                viewTab === 'PENDING'
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Pending Decisions ({viewTab === 'PENDING' ? candidates.length : '...'})
            </button>
            <button
              onClick={() => setViewTab('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                viewTab === 'ALL'
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              All Records ({viewTab === 'ALL' ? candidates.length : '...'})
            </button>
          </div>
        </div>
      </div>

      {actionSuccessMessage && (
        <div className="p-5 bg-emerald-500/10 border-2 border-emerald-500/30 rounded-xl text-sm text-emerald-700 dark:text-emerald-300 font-semibold flex items-center justify-between shadow-sm">
          <span className="flex items-center gap-2.5">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" /> {actionSuccessMessage}
          </span>
          <button onClick={() => setActionSuccessMessage(null)} className="text-emerald-700 font-bold hover:underline text-sm">
            Dismiss
          </button>
        </div>
      )}

      {actionErrorMessage && (
        <div className="p-5 bg-destructive/10 border-2 border-destructive/30 rounded-xl text-sm text-destructive font-semibold flex items-center justify-between shadow-sm">
          <span className="flex items-center gap-2.5">
            <AlertTriangle className="h-5 w-5 text-destructive" /> {actionErrorMessage}
          </span>
          <button onClick={() => setActionErrorMessage(null)} className="text-destructive font-bold hover:underline text-sm">
            Dismiss
          </button>
        </div>
      )}

      {candidates.length === 0 ? (
        <div className="p-16 text-center bg-card border-2 border-border rounded-xl shadow-sm">
          <ShieldCheck className="h-16 w-16 text-emerald-500 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-foreground">Zero Duplicate Anomalies Pending</h3>
          <p className="text-sm text-muted-foreground mt-2 max-w-lg mx-auto leading-relaxed">
            All ingested records across e-Prisons, CCTNS, and Court Dockets have been reconciled with unambiguous identity references.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Candidate List (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
              <span>Candidate Queue</span>
              <span className="px-2 py-0.5 bg-secondary text-foreground rounded text-xs">{candidates.length} pending</span>
            </h3>
            <div className="space-y-3">
              {candidates.map((cand) => (
                <div
                  key={cand.id}
                  onClick={() => setSelectedCandidate(cand)}
                  className={`p-5 rounded-xl border-2 cursor-pointer transition-all shadow-sm ${
                    selectedCandidate?.id === cand.id
                      ? 'bg-primary/10 border-primary shadow-md ring-2 ring-primary/20'
                      : 'bg-card border-border hover:border-primary/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-primary bg-primary/10 px-2 py-1 rounded">{cand.id}</span>
                    <span className="text-xs px-2.5 py-1 rounded-full font-extrabold bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30">
                      {(cand.match_confidence * 100).toFixed(0)}% Match
                    </span>
                  </div>

                  <div className="mt-3 space-y-1.5">
                    <div className="text-base font-bold text-foreground flex items-center gap-2">
                      <span>{cand.source_name}</span>
                      <ArrowRight className="h-4 w-4 text-primary shrink-0" />
                      <span className="text-primary">{cand.candidate_name}</span>
                    </div>
                    <div className="text-xs text-muted-foreground font-medium">
                      {cand.source_facility} <span className="text-foreground/40">vs</span> {cand.candidate_facility}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Column: Detailed Side-by-Side Comparison (8 cols - Zoomed & Spacious) */}
          {selectedCandidate && (
            <div className="lg:col-span-8 space-y-6">
              {/* Top Banner: Explanation */}
              <div className="bg-primary/5 border-2 border-primary/20 rounded-xl p-5 space-y-2.5 shadow-sm">
                <div className="flex items-center gap-2 text-sm font-bold text-primary">
                  <Sparkles className="h-5 w-5" /> Probabilistic Match Diagnostic Engine
                </div>
                <p className="text-sm text-foreground/90 leading-relaxed">
                  {selectedCandidate.match_explanation}
                </p>
              </div>

              {/* Side-by-Side Comparison Cards — Enlarged */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Source Record */}
                <div className="bg-card border-2 border-border rounded-xl p-6 space-y-4 shadow-sm">
                  <div className="flex items-center justify-between pb-3 border-b border-border">
                    <span className="text-sm font-bold text-foreground uppercase tracking-wide">Record A (Primary Docket)</span>
                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-secondary text-foreground">
                      {selectedCandidate.source_accused_id}
                    </span>
                  </div>

                  <div className="space-y-3.5">
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">FULL NAME</span>
                      <strong className="text-foreground text-lg font-bold block mt-0.5">{selectedCandidate.source_name}</strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">FATHER'S NAME</span>
                      <span className="text-foreground font-semibold text-base block mt-0.5">{selectedCandidate.source_father_name || "Not Recorded"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">DATE OF BIRTH / AGE</span>
                      <span className="text-foreground font-semibold text-base block mt-0.5">{selectedCandidate.source_dob || "Estimated 24 Years"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">CUSTODY FACILITY</span>
                      <span className="text-foreground font-semibold text-base block mt-0.5">{selectedCandidate.source_facility}</span>
                    </div>
                  </div>
                </div>

                {/* Candidate Record */}
                <div className="bg-card border-2 border-primary/30 rounded-xl p-6 space-y-4 shadow-sm">
                  <div className="flex items-center justify-between pb-3 border-b border-border">
                    <span className="text-sm font-bold text-primary uppercase tracking-wide">Record B (Candidate Match)</span>
                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-primary/10 text-primary">
                      {selectedCandidate.candidate_accused_id}
                    </span>
                  </div>

                  <div className="space-y-3.5">
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">FULL NAME</span>
                      <strong className="text-primary text-lg font-bold block mt-0.5">{selectedCandidate.candidate_name}</strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">FATHER'S NAME</span>
                      <span className="text-foreground font-semibold text-base block mt-0.5">{selectedCandidate.candidate_father_name || "Not Recorded"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">DATE OF BIRTH / AGE</span>
                      <span className="text-foreground font-semibold text-base block mt-0.5">{selectedCandidate.candidate_dob || "Estimated 24 Years"}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-xs font-bold uppercase tracking-wider">CUSTODY FACILITY</span>
                      <span className="text-foreground font-semibold text-base block mt-0.5">{selectedCandidate.candidate_facility}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Shared vs Conflicting Traits — Large & Clear */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-emerald-500/10 border-2 border-emerald-500/30 rounded-xl p-5 space-y-3">
                  <h4 className="text-sm font-bold text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5" /> Corroborated Shared Traits
                  </h4>
                  <ul className="space-y-2">
                    {selectedCandidate.shared_traits.map((trait, i) => (
                      <li key={i} className="text-sm text-foreground/90 font-medium flex items-start gap-2.5">
                        <span className="h-2 w-2 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                        {trait}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-amber-500/10 border-2 border-amber-500/30 rounded-xl p-5 space-y-3">
                  <h4 className="text-sm font-bold text-amber-700 dark:text-amber-300 flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5" /> Discrepancies & Conflict Flags
                  </h4>
                  <ul className="space-y-2">
                    {selectedCandidate.conflicting_traits.map((conflict, i) => (
                      <li key={i} className="text-sm text-foreground/90 font-medium flex items-start gap-2.5">
                        <span className="h-2 w-2 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                        {conflict}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Human Decision Control Box */}
              {selectedCandidate.review_status && selectedCandidate.review_status !== 'PENDING_HUMAN_REVIEW' ? (
                <div className="bg-card border-2 border-border rounded-xl p-6 space-y-3 shadow-md">
                  <div className="flex items-center gap-2 text-emerald-600 font-bold text-sm">
                    <CheckCircle2 className="h-5 w-5" />
                    <span>Decision Recorded: {selectedCandidate.review_status.replace(/_/g, " ")}</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    This candidate record was reviewed and resolved by <span className="font-semibold text-foreground">{selectedCandidate.reviewed_by || "Legal Officer"}</span> on {selectedCandidate.reviewed_at ? new Date(selectedCandidate.reviewed_at).toLocaleString() : "record"}.
                  </p>
                  {selectedCandidate.resolution_notes && (
                    <div className="p-3 bg-secondary/60 rounded-lg text-xs font-mono text-muted-foreground">
                      <span className="font-bold text-foreground">Officer Notes: </span> {selectedCandidate.resolution_notes}
                    </div>
                  )}
                </div>
              ) : !(user?.role === "SUPERVISING_LEGAL_OFFICER" || user?.role === "DLSA_OFFICER") ? (
                <div className="bg-card border-2 border-border rounded-xl p-6 space-y-3 shadow-md">
                  <div className="flex items-center gap-2 text-foreground font-bold text-sm">
                    <Shield className="h-5 w-5 text-primary" />
                    <span>Judicial Authority Required for Identity Mutations</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Under BNSS Section 479 statutory governance and segregation of duties, resolving de-duplication candidates (Merge Under Canonical ID, Link as Alias Profile, or Mark as Distinct Persons) must be formally recorded by an authorized judicial officer (DLSA Officer or Supervising Legal Officer). As a <span className="font-semibold text-foreground">{user?.role?.replace(/_/g, " ")}</span>, you have supervisory inspection and audit visibility over this queue.
                  </p>
                </div>
              ) : (
                <div className="bg-card border-2 border-border rounded-xl p-6 space-y-5 shadow-md">
                  <div>
                    <h4 className="text-base font-bold text-foreground flex items-center gap-2">
                      <GitMerge className="h-5 w-5 text-primary" /> Judicial De-duplication Decision
                    </h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Select the statutory action to apply across state prison and court registries. This action is permanently logged into the immutable audit trail.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <button
                      onClick={() => setResolutionAction('MERGE_RECORDS')}
                      className={`p-4 rounded-xl border-2 text-sm font-bold transition-all flex flex-col items-center text-center gap-2 shadow-sm ${
                        resolutionAction === 'MERGE_RECORDS'
                          ? 'bg-emerald-600 text-white border-emerald-600 ring-2 ring-emerald-500/30'
                          : 'bg-secondary/40 border-border text-foreground hover:border-emerald-500 hover:bg-emerald-500/5'
                      }`}
                    >
                      <GitMerge className="h-6 w-6 text-emerald-500" />
                      <span>Merge Under Canonical ID</span>
                      <span className="text-[11px] font-normal opacity-80">Unify dockets across facilities</span>
                    </button>

                    <button
                      onClick={() => setResolutionAction('MARK_AS_ALIAS')}
                      className={`p-4 rounded-xl border-2 text-sm font-bold transition-all flex flex-col items-center text-center gap-2 shadow-sm ${
                        resolutionAction === 'MARK_AS_ALIAS'
                          ? 'bg-purple-600 text-white border-purple-600 ring-2 ring-purple-500/30'
                          : 'bg-secondary/40 border-border text-foreground hover:border-purple-500 hover:bg-purple-500/5'
                      }`}
                    >
                      <Layers className="h-6 w-6 text-purple-500" />
                      <span>Link As Alias Profile</span>
                      <span className="text-[11px] font-normal opacity-80">Preserve cross-alias reference</span>
                    </button>

                    <button
                      onClick={() => setResolutionAction('REJECT_MATCH')}
                      className={`p-4 rounded-xl border-2 text-sm font-bold transition-all flex flex-col items-center text-center gap-2 shadow-sm ${
                        resolutionAction === 'REJECT_MATCH'
                          ? 'bg-rose-600 text-white border-rose-600 ring-2 ring-rose-500/30'
                          : 'bg-secondary/40 border-border text-foreground hover:border-rose-500 hover:bg-rose-500/5'
                      }`}
                    >
                      <XCircle className="h-6 w-6 text-rose-500" />
                      <span>Mark As Distinct Persons</span>
                      <span className="text-[11px] font-normal opacity-80">Separate cases permanently</span>
                    </button>
                  </div>

                  {resolutionAction && (
                    <div className="space-y-4 pt-4 border-t border-border">
                      {resolutionAction === 'MERGE_RECORDS' && (
                        <div className="p-4 bg-amber-500/10 border-2 border-amber-500/30 rounded-xl space-y-2 text-xs font-mono text-amber-800 dark:text-amber-300">
                          <div className="font-bold flex items-center gap-2 text-sm uppercase">
                            <AlertTriangle className="h-4 w-4 text-amber-600" /> High-Impact Identity Mutation Warning
                          </div>
                          <p>
                            Merging under Canonical ID permanently unifies detention dockets, biometric aliases, and criminal histories across state facilities. This irreversible action will be stamped with your officer credentials ({user?.full_name || user?.role}) in the permanent audit ledger.
                          </p>
                        </div>
                      )}

                      <label className="text-sm font-bold text-foreground block">
                        Resolution Notes & Evidentiary Rationale: <span className="text-destructive">*</span>
                      </label>
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Enter specific legal rationale (e.g. verified father name, physical identification marks, and CCTNS biometric record)..."
                        className="w-full bg-background border-2 border-border rounded-xl p-4 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary min-h-[100px] leading-relaxed"
                      />

                      {resolutionAction === 'MERGE_RECORDS' && (
                        <label className="flex items-start gap-3 p-3 bg-secondary/50 border border-border rounded-lg text-xs font-semibold cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={confirmMerge}
                            onChange={(e) => setConfirmMerge(e.target.checked)}
                            className="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                          />
                          <span className="text-muted-foreground leading-normal">
                            I formally certify as {user?.role} that biometric traits, parentage records, and facility admission files have been verified to establish identical persona.
                          </span>
                        </label>
                      )}

                      <div className="flex items-center justify-end gap-3 pt-2">
                        <button
                          onClick={() => {
                            setResolutionAction(null);
                            setConfirmMerge(false);
                          }}
                          className="px-5 py-2.5 rounded-lg border border-border text-sm font-medium hover:bg-secondary text-foreground transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleResolve}
                          disabled={submitting || (resolutionAction === 'MERGE_RECORDS' && (!confirmMerge || notes.trim().length < 10)) || !notes.trim()}
                          className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2 shadow-sm transition-all"
                        >
                          {submitting ? 'Applying Decision...' : 'Confirm Decision & Record Audit'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default IdentityResolutionPage;

