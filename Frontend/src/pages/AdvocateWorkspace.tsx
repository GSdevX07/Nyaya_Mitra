import { useState, useEffect } from "react";
import {
  Briefcase, Scale, CheckCircle2, ChevronRight
} from "lucide-react";
import { Link } from "react-router-dom";
import { fetchCases, type CaseRecord } from "../lib/api";

export function AdvocateWorkspace() {
  const [assignedCases, setAssignedCases] = useState<CaseRecord[]>([]);

  useEffect(() => {
    async function loadAdvocateCases() {
      try {
        const raw = await fetchCases();
        const extracted = (raw || []).map((item: any) => (item.case || item) as CaseRecord);
        const assigned = extracted.filter((c) => c.assignment_status === "ASSIGNED" || c.assigned_lawyer_id);
        setAssignedCases(assigned);
      } catch (err) {
        console.error("Failed to load advocate cases:", err);
      }
    }
    loadAdvocateCases();
  }, []);

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Advocate Workspace Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Briefcase className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Defense Legal Aid Counsel // Assigned Portfolio
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Defense Advocate Briefing Workspace
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Review assigned undertrial dossiers, verify Section 479 eligibility calculations, perform mandatory human legal sign-off, and prepare bail petitions for court filing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/radar"
            className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90"
          >
            <Scale className="w-4 h-4" /> Eligibility Radar
          </Link>
        </div>
      </div>

      {/* Stats Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Assigned Matters</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{assignedCases.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">DLSA Panel Assignment</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Petitions Ready for Filing</div>
          <div className="text-2xl font-serif font-bold text-blue-600 mt-1">
            {assignedCases.filter((c) => c.status === "APPROVED_READY_FOR_FILING").length}
          </div>
          <div className="text-[10px] font-mono text-blue-600 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Advocate Signed Off
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Filed in Court</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
            {assignedCases.filter((c) => c.status === "FILED").length}
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1">Active Court Proceedings</div>
        </div>
      </div>

      {/* Assigned Cases List */}
      <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/40 font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
          My Active Undertrial Briefs ({assignedCases.length} matters)
        </div>

        <div className="divide-y divide-border">
          {assignedCases.map((c) => (
            <div key={c.case_id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                    {c.case_id}
                  </span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-secondary border border-border">
                    {c.legal_code}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                  <span>Offences: <strong className="text-foreground">{c.offense_sections?.join(", ")}</strong></span>
                  <span>•</span>
                  <span>Custody: <strong className="text-foreground">{c.custody_days} days</strong></span>
                  <span>•</span>
                  <span>Court: <strong className="text-foreground">{c.court_name}</strong></span>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {c.status === "APPROVED_READY_FOR_FILING" && (
                  <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-blue-500/10 text-blue-600 border border-blue-500/20">
                    READY FOR FILING
                  </span>
                )}
                {c.status === "FILED" && (
                  <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                    FILED IN COURT
                  </span>
                )}

                <Link
                  to={`/case/${c.case_id}`}
                  className="px-3.5 py-1.5 bg-primary text-primary-foreground font-serif font-bold text-xs rounded-sm flex items-center gap-1 hover:opacity-90 transition-opacity"
                >
                  Review Dossier & Draft <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
