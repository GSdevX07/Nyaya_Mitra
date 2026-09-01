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
  Sparkles
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
}

export const IdentityResolutionPage: React.FC = () => {
  const { token, user } = useAuth();
  const [candidates, setCandidates] = useState<DuplicateCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCandidate, setSelectedCandidate] = useState<DuplicateCandidate | null>(null);
  const [resolutionAction, setResolutionAction] = useState<'MERGE_RECORDS' | 'REJECT_MATCH' | 'MARK_AS_ALIAS' | null>(null);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchCandidates();
  }, [token]);

  const fetchCandidates = async () => {
    setLoading(true);
    try {
      const data = await fetchDuplicateCandidates();
      setCandidates(data);
      if (data.length > 0) {
        setSelectedCandidate(data[0]);
      }
    } catch (err) {
      console.error('Error fetching duplicate candidates:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedCandidate || !resolutionAction) return;
    setSubmitting(true);
    try {
      const result = await resolveDuplicateCandidate({
        candidate_id: selectedCandidate.id,
        action: resolutionAction,
        resolution_notes: notes || `Resolved as ${resolutionAction} by ${user?.full_name || 'Legal Officer'}`,
      });

      setActionSuccessMessage(result.message);
      setResolutionAction(null);
      setNotes('');
      // Refresh list
      fetchCandidates();
    } catch (err) {
      console.error('Resolution submission failed:', err);
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
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Fingerprint className="h-7 w-7 text-primary" /> Identity-Resolution & De-duplication Review
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Human-in-the-loop review queue for probable duplicate accused person records detected across detention facilities.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-3 py-1 rounded-full font-semibold bg-amber-500/10 text-amber-600 border border-amber-500/20 flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5" /> {candidates.length} Cases Awaiting Human Decision
          </span>
        </div>
      </div>

      {actionSuccessMessage && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs text-emerald-600 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" /> {actionSuccessMessage}
          </span>
          <button onClick={() => setActionSuccessMessage(null)} className="text-emerald-700 font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {candidates.length === 0 ? (
        <div className="p-12 text-center bg-card border border-border rounded-xl">
          <ShieldCheck className="h-12 w-12 text-emerald-500 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-foreground">Zero Duplicate Anomalies Pending</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
            All ingested records across e-Prisons, CCTNS, and Court Dockets have been reconciled with unambiguous identity references.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Candidate List */}
          <div className="lg:col-span-1 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Candidate Queue ({candidates.length})
            </h3>
            {candidates.map((cand) => (
              <div
                key={cand.id}
                onClick={() => setSelectedCandidate(cand)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  selectedCandidate?.id === cand.id
                    ? 'bg-primary/5 border-primary shadow-sm'
                    : 'bg-card border-border hover:border-primary/40'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-primary">{cand.id}</span>
                  <span className="text-xs px-2 py-0.5 rounded font-bold bg-amber-500/10 text-amber-600">
                    {(cand.match_confidence * 100).toFixed(0)}% Match
                  </span>
                </div>

                <div className="mt-2 space-y-1">
                  <div className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <span>{cand.source_name}</span>
                    <ArrowRight className="h-3 w-3 text-muted-foreground" />
                    <span>{cand.candidate_name}</span>
                  </div>
                  <div className="text-[11px] text-muted-foreground truncate">
                    {cand.source_facility} vs {cand.candidate_facility}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Right Column: Detailed Side-by-Side Comparison */}
          {selectedCandidate && (
            <div className="lg:col-span-2 space-y-5">
              {/* Top Banner: Explanation */}
              <div className="bg-secondary/40 border border-border rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-primary">
                  <Sparkles className="h-4 w-4" /> Probabilistic Match Diagnostic
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {selectedCandidate.match_explanation}
                </p>
              </div>

              {/* Side-by-Side Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Source Record */}
                <div className="bg-card border border-border rounded-xl p-5 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-border">
                    <span className="text-xs font-bold text-foreground">Record A (Primary Docket)</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-secondary text-muted-foreground">
                      {selectedCandidate.source_accused_id}
                    </span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <span className="text-muted-foreground block text-[10px]">FULL NAME</span>
                      <strong className="text-foreground text-sm">{selectedCandidate.source_name}</strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">FATHER'S NAME</span>
                      <span className="text-foreground font-medium">{selectedCandidate.source_father_name}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">DATE OF BIRTH</span>
                      <span className="text-foreground font-medium">{selectedCandidate.source_dob}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">FACILITY DETENTION</span>
                      <span className="text-foreground font-medium">{selectedCandidate.source_facility}</span>
                    </div>
                  </div>
                </div>

                {/* Candidate Record */}
                <div className="bg-card border border-border rounded-xl p-5 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-border">
                    <span className="text-xs font-bold text-primary">Record B (Candidate Match)</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-secondary text-muted-foreground">
                      {selectedCandidate.candidate_accused_id}
                    </span>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div>
                      <span className="text-muted-foreground block text-[10px]">FULL NAME</span>
                      <strong className="text-foreground text-sm">{selectedCandidate.candidate_name}</strong>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">FATHER'S NAME</span>
                      <span className="text-foreground font-medium">{selectedCandidate.candidate_father_name}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">DATE OF BIRTH</span>
                      <span className="text-foreground font-medium">{selectedCandidate.candidate_dob}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground block text-[10px]">FACILITY DETENTION</span>
                      <span className="text-foreground font-medium">{selectedCandidate.candidate_facility}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Shared vs Conflicting Traits */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 space-y-2">
                  <h4 className="text-xs font-bold text-emerald-600 flex items-center gap-1.5">
                    <CheckCircle2 className="h-4 w-4" /> Corroborated Shared Traits
                  </h4>
                  <ul className="space-y-1.5">
                    {selectedCandidate.shared_traits.map((trait, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                        {trait}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 space-y-2">
                  <h4 className="text-xs font-bold text-amber-600 flex items-center gap-1.5">
                    <AlertTriangle className="h-4 w-4" /> Discrepancies & Conflict Flags
                  </h4>
                  <ul className="space-y-1.5">
                    {selectedCandidate.conflicting_traits.map((conflict, i) => (
                      <li key={i} className="text-xs text-muted-foreground flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                        {conflict}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Human Decision Control Box */}
              <div className="bg-card border border-border rounded-xl p-5 space-y-4 shadow-sm">
                <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <GitMerge className="h-4 w-4 text-primary" /> Judicial De-duplication Decision
                </h4>

                <div className="grid grid-cols-3 gap-3">
                  <button
                    onClick={() => setResolutionAction('MERGE_RECORDS')}
                    className={`p-3 rounded-lg border text-xs font-bold transition-all flex flex-col items-center gap-1.5 ${
                      resolutionAction === 'MERGE_RECORDS'
                        ? 'bg-emerald-600 text-white border-emerald-600'
                        : 'bg-secondary/40 border-border text-foreground hover:border-emerald-500'
                    }`}
                  >
                    <GitMerge className="h-4 w-4" /> Merge Under Canonical ID
                  </button>

                  <button
                    onClick={() => setResolutionAction('MARK_AS_ALIAS')}
                    className={`p-3 rounded-lg border text-xs font-bold transition-all flex flex-col items-center gap-1.5 ${
                      resolutionAction === 'MARK_AS_ALIAS'
                        ? 'bg-purple-600 text-white border-purple-600'
                        : 'bg-secondary/40 border-border text-foreground hover:border-purple-500'
                    }`}
                  >
                    <Layers className="h-4 w-4" /> Link As Alias Profile
                  </button>

                  <button
                    onClick={() => setResolutionAction('REJECT_MATCH')}
                    className={`p-3 rounded-lg border text-xs font-bold transition-all flex flex-col items-center gap-1.5 ${
                      resolutionAction === 'REJECT_MATCH'
                        ? 'bg-rose-600 text-white border-rose-600'
                        : 'bg-secondary/40 border-border text-foreground hover:border-rose-500'
                    }`}
                  >
                    <XCircle className="h-4 w-4" /> Mark As Distinct Persons
                  </button>
                </div>

                {resolutionAction && (
                  <div className="space-y-3 pt-3 border-t border-border">
                    <label className="text-xs font-medium text-foreground block">
                      Resolution Notes & Evidentiary Rationale:
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Enter legal rationale (e.g. verified father name, physical scar marks, and CCTNS biometric record)..."
                      className="w-full bg-background border border-border rounded-lg p-3 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary min-h-[80px]"
                    />
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setResolutionAction(null)}
                        className="px-4 py-2 rounded-lg border border-border text-xs font-medium hover:bg-secondary text-foreground"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleResolve}
                        disabled={submitting}
                        className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                      >
                        {submitting ? 'Applying Decision...' : 'Confirm Decision & Log Audit'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
export default IdentityResolutionPage;
