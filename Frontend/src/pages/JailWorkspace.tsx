import { useState, useEffect } from "react";
import {
  Building2, AlertTriangle, CheckCircle2,
  Search, Plus, ChevronRight
} from "lucide-react";
import { Link } from "react-router-dom";
import { fetchCases, type CaseRecord } from "../lib/api";

export function JailWorkspace() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  const loadJailCases = async () => {
    try {
      const raw = await fetchCases();
      const extracted = (raw || []).map((item: any) => (item.case || item) as CaseRecord);
      setCases(extracted);
    } catch (err) {
      console.error("Failed to load jail cases:", err);
    }
  };

  useEffect(() => {
    loadJailCases();
  }, []);

  const filteredCases = cases.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.case_id.toLowerCase().includes(q) ||
      c.jail_location?.toLowerCase().includes(q) ||
      c.fir_number?.toLowerCase().includes(q)
    );
  });

  const docMissingCases = cases.filter(
    (c) => (c.required_docs?.length || 0) > (c.present_docs?.length || 0)
  );

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Prison Department & Custody Desk // Jail Operations
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Jail Inmate Custody & Legal Records Desk
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Track undertrial custody days, document completeness, remand orders, and ensure timely legal aid identification for all admitted prisoners.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/documents"
            className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" /> Upload Intake Record
          </Link>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Facility Inmates Tracked</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{cases.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">Central Prison Complex</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Missing Legal Documents</div>
          <div className="text-2xl font-serif font-bold text-amber-600 mt-1">{docMissingCases.length}</div>
          <div className="text-[10px] font-mono text-amber-600 mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Remand / FIR copies needed
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">DLSA Counsel Assigned</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
            {cases.filter((c) => c.assignment_status === "ASSIGNED").length} / {cases.length}
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1">Full Legal Aid Coverage</div>
        </div>
      </div>

      {/* Custody List */}
      <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <span className="font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
            Current Undertrial Custody Roll ({filteredCases.length} records)
          </span>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search inmate name or ID..."
              className="w-full pl-9 pr-3 py-1.5 bg-input border border-border text-xs font-mono rounded-sm focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        <div className="divide-y divide-border">
          {filteredCases.map((c) => {
            const hasMissingDocs = (c.required_docs?.length || 0) > (c.present_docs?.length || 0);
            return (
              <div key={c.case_id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                      {c.case_id}
                    </span>
                    <span className="text-xs font-mono text-muted-foreground">
                      {c.jail_location}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                    <span>Arrest Date: <strong className="text-foreground">{c.arrest_date}</strong></span>
                    <span>•</span>
                    <span>Calendar Custody: <strong className="text-foreground">{c.custody_days}d</strong></span>
                    <span>•</span>
                    <span>Countable Days: <strong className="text-primary font-bold">{c.custody_days - (c.excluded_delay_days || 0)}d</strong></span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {hasMissingDocs ? (
                    <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-amber-500/10 text-amber-600 border border-amber-500/20 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> Missing Docs
                    </span>
                  ) : (
                    <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Docs Complete
                    </span>
                  )}

                  <Link
                    to={`/case/${c.case_id}`}
                    className="px-3 py-1.5 bg-primary text-primary-foreground rounded-sm text-xs font-serif font-semibold flex items-center gap-1"
                  >
                    View Dossier <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
