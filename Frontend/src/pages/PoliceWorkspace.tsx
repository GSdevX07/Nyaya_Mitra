import { useState, useEffect } from "react";
import {
  ShieldAlert, AlertTriangle, CheckCircle2,
  Search, Plus, ChevronRight, FileText, UserCheck, Scale
} from "lucide-react";
import { Link } from "react-router-dom";
import { fetchCases, type CaseRecord } from "../lib/api";

export function PoliceWorkspace() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);

  const loadPoliceCases = async () => {
    setLoading(true);
    try {
      const raw = await fetchCases();
      const extracted = (raw || []).map((item: any) => (item.case || item) as CaseRecord);
      setCases(extracted);
    } catch (err) {
      console.error("Failed to load police desk cases:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPoliceCases();
  }, []);

  const filteredCases = cases.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.case_id.toLowerCase().includes(q) ||
      (c.fir_number && c.fir_number.toLowerCase().includes(q)) ||
      (c.police_station && c.police_station.toLowerCase().includes(q)) ||
      (c.offense_sections && c.offense_sections.join(" ").toLowerCase().includes(q)) ||
      (c.offense_summary && c.offense_summary.toLowerCase().includes(q))
    );
  });

  const chargesheetPending = cases.filter(
    (c) => !(c.present_docs || []).includes("charge_sheet")
  );

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Police Reference & Investigation Desk // District Coordination
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Police Investigation & FIR Registry Desk
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Track FIR compliance, upload arrest memos and charge sheets, monitor statutory remand limits, and verify identity records across custody facilities.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Link
            to="/documents"
            className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90 transition-opacity"
          >
            <Plus className="w-4 h-4" /> Upload FIR / Memo
          </Link>
          <Link
            to="/cases"
            className="px-3 py-2 border border-border bg-secondary hover:bg-muted text-foreground font-mono text-xs font-semibold uppercase rounded-sm flex items-center gap-1.5"
          >
            <Scale className="w-4 h-4" /> FIR Registry
          </Link>
        </div>
      </div>

      {/* Overview Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Monitored FIR Cases</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{cases.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">Central Delhi Jurisdiction</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Charge Sheet Pending</div>
          <div className="text-2xl font-serif font-bold text-amber-600 mt-1">{chargesheetPending.length}</div>
          <div className="text-[10px] font-mono text-amber-600/80 mt-1">Required for Bail Adjudication</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Court Remand Verified</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
            {cases.filter((c) => (c.present_docs || []).includes("remand_order")).length}
          </div>
          <div className="text-[10px] font-mono text-emerald-600/80 mt-1">Cryptographically Sealed</div>
        </div>
      </div>

      {/* Search & Case Roster */}
      <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/30 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by accused name, FIR no, police station..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-xs bg-background border border-border rounded-sm font-sans focus:outline-none focus:ring-1 focus:ring-primary text-foreground"
            />
          </div>
          <span className="text-xs font-mono text-muted-foreground self-center">
            Showing {filteredCases.length} of {cases.length} records
          </span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs font-mono text-muted-foreground">
            Loading police reference docket...
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="p-8 text-center text-xs font-mono text-muted-foreground">
            No matching police records found for query "{searchQuery}".
          </div>
        ) : (
          <div className="divide-y divide-border">
            {filteredCases.map((c) => {
              const hasChargeSheet = (c.present_docs || []).includes("charge_sheet");
              const hasRemand = (c.present_docs || []).includes("remand_order");
              const accusedOpaqueId = `acc_${c.case_id.toLowerCase().replace("-", "_")}`;

              return (
                <div
                  key={c.case_id}
                  className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-sm font-serif text-foreground">{c.name}</span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-secondary border border-border text-foreground">
                        {c.case_id}
                      </span>
                      {c.fir_number && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                          FIR: {c.fir_number}
                        </span>
                      )}
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-secondary text-muted-foreground border border-border">
                        {c.legal_code || "BNS_2023"}
                      </span>
                    </div>

                    <div className="text-xs font-sans text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1">
                      <span>PS: <strong className="text-foreground">{c.police_station || "Central Police Station"}</strong></span>
                      <span>Offense: {c.offense_sections?.join(", ") || c.offense_summary || "Bailable statutory category"}</span>
                      <span>Custody: <strong className="text-foreground">{c.custody_days || 0} days</strong></span>
                      <span>Facility: {c.jail_location || "Central Prison"}</span>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] font-mono pt-1">
                      <span className={`flex items-center gap-1 ${hasRemand ? 'text-emerald-600' : 'text-red-500 font-bold'}`}>
                        {hasRemand ? <CheckCircle2 className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                        Remand Order {hasRemand ? "Uploaded" : "Missing"}
                      </span>
                      <span className={`flex items-center gap-1 ${hasChargeSheet ? 'text-emerald-600' : 'text-amber-600'}`}>
                        {hasChargeSheet ? <CheckCircle2 className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                        Charge Sheet {hasChargeSheet ? "Present" : "Pending"}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                    <Link
                      to={`/accused/${accusedOpaqueId}`}
                      className="px-3 py-1.5 bg-secondary hover:bg-muted border border-border text-foreground font-mono text-xs font-semibold rounded-sm flex items-center gap-1"
                      title="View Accused Dossier"
                    >
                      <UserCheck className="w-3.5 h-3.5" /> Profile
                    </Link>
                    <Link
                      to={`/case/${c.case_id}`}
                      className="px-3 py-1.5 bg-primary text-primary-foreground font-mono text-xs font-bold rounded-sm flex items-center gap-1 hover:opacity-90"
                    >
                      Case File <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
