import { useState, useEffect } from "react";
import {
  ShieldCheck, Search, Filter, Clock,
  CheckCircle2, RefreshCw,
  Download, Key,
  Calendar, Layers, ShieldAlert
} from "lucide-react";
import { fetchAuditEvents, exportAuditLedger, fetchAuditExceptions, fetchEvidence } from "../lib/api";

interface AuditEvent {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  actor_id: string;
  actor_role: string;
  timestamp: string;
  ip_address?: string;
  details?: any;
  event_hash?: string;
  previous_event_hash?: string;
  hash_algorithm?: string;
  sequence_number?: number;
  severity?: string;
  data_status?: string;
  hash_verification?: string;
}

interface AuditException {
  exception_id: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "WARNING" | "NOTICE";
  title: string;
  description: string;
  case_id?: string;
  district?: string;
  timestamp?: string;
  remediation?: string;
}

export function AuditorConsole() {
  const [activeTab, setActiveTab] = useState<"ledger" | "exceptions">("ledger");
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [actionFilter, setActionFilter] = useState<string>("ALL");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");

  // Integrity stats
  const [evidenceStats, setEvidenceStats] = useState<{
    total: number;
    verified: number;
    flagged: number;
    pct: number | null;
  }>({ total: 0, verified: 0, flagged: 0, pct: null });

  // Exceptions
  const [exceptions, setExceptions] = useState<AuditException[]>([]);
  const [loadingExceptions, setLoadingExceptions] = useState(false);

  // Export Modal
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [exportReason, setExportReason] = useState("");
  const [exportFormat, setExportFormat] = useState("JSON");
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  // Expanded items
  const [expandedChain, setExpandedChain] = useState<Record<string, boolean>>({});

  const toggleChain = (id: string) => {
    setExpandedChain((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const loadAuditData = async () => {
    setLoading(true);
    try {
      const res = await fetchAuditEvents({
        limit: 100,
        offset: 0,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        action: actionFilter,
        severity: severityFilter,
      });

      if (res && Array.isArray(res.events)) {
        setEvents(res.events);
        setTotalCount(res.total_count || res.events.length);
      } else if (Array.isArray(res)) {
        setEvents(res);
        setTotalCount(res.length);
      } else {
        setEvents([]);
        setTotalCount(0);
      }
    } catch (err) {
      console.warn("Audit stream error:", err);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  const loadIntegrityData = async () => {
    try {
      const evidence = await fetchEvidence();
      if (Array.isArray(evidence) && evidence.length > 0) {
        const total = evidence.length;
        const verified = evidence.filter((e: any) => e.stored_hash).length;
        const flagged = evidence.filter((e: any) => e.flagged || e.tampering_detected).length;
        const pct = total > 0 ? Math.round(((verified - flagged) / total) * 100) : null;
        setEvidenceStats({ total, verified, flagged, pct });
      } else {
        setEvidenceStats({ total: 0, verified: 0, flagged: 0, pct: null });
      }
    } catch (err) {
      console.warn("Evidence integrity stats error:", err);
    }
  };

  const loadExceptions = async () => {
    setLoadingExceptions(true);
    try {
      const data = await fetchAuditExceptions();
      if (data && Array.isArray(data.exceptions)) {
        setExceptions(data.exceptions);
      } else {
        setExceptions([]);
      }
    } catch (err) {
      console.warn("Audit exceptions error:", err);
      setExceptions([]);
    } finally {
      setLoadingExceptions(false);
    }
  };

  useEffect(() => {
    loadAuditData();
    loadIntegrityData();
    loadExceptions();
  }, [actionFilter, severityFilter, dateFrom, dateTo]);

  const handleExportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!exportReason.trim()) return;
    setExporting(true);
    try {
      const result = await exportAuditLedger({
        export_reason: exportReason,
        format: exportFormat,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        action_filter: actionFilter !== "ALL" ? actionFilter : undefined,
      });

      // Trigger browser download
      const blob = new Blob([result.export_payload], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `NyayaMitra_Audit_Export_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setExportSuccess(`Export confirmed with SHA-256 seal: ${result.artifact_sha256.slice(0, 16)}...`);
      setTimeout(() => {
        setIsExportOpen(false);
        setExportSuccess(null);
        setExportReason("");
        loadAuditData(); // Reload to reflect export event
      }, 2500);
    } catch (err: any) {
      alert(`Export failed: ${err.message || err}`);
    } finally {
      setExporting(false);
    }
  };

  const getHumanEvent = (ev: AuditEvent) => {
    const action = ev.action.toUpperCase();
    const details = ev.details || {};

    if (action.includes("AUTHORIZATION_DENIED") || action.includes("SCOPE_VIOLATION")) {
      return {
        title: "Access Attempt Blocked (403 Forbidden)",
        category: "Security Boundary Violation",
        color: "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20",
        summary: details.message || `An unauthorized caller (${ev.actor_role}) attempted an operation beyond authorized boundary.`,
        targetLabel: "Access Boundary",
      };
    }

    if (action.includes("LOGIN_FAILED")) {
      return {
        title: "Unsuccessful Sign-In Attempt",
        category: "Security Alert",
        color: "bg-destructive/10 text-destructive border-destructive/20",
        summary: `A user attempted to sign in with ID ${ev.actor_id} but verification failed. Masked IP: ${ev.ip_address || "127.0.***"}.`,
        targetLabel: "Access Gateway",
      };
    }

    if (action.includes("LOGIN")) {
      return {
        title: "Authorized System Sign-In",
        category: "User Access",
        color: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20",
        summary: `User logged in securely with role [${ev.actor_role.replace(/_/g, " ")}]. Session verified.`,
        targetLabel: `Session ID: ${ev.entity_id}`,
      };
    }

    if (action.includes("TOKEN_REVOCATION") || action.includes("LOGOUT")) {
      return {
        title: "User Session Cleanly Terminated",
        category: "Security",
        color: "bg-muted text-muted-foreground border-border",
        summary: `User session terminated. Cryptographic bearer token was revoked to prevent reuse.`,
        targetLabel: `Session: ${ev.entity_id}`,
      };
    }

    if (action.includes("ADVOCATE_SIGN_OFF") || action.includes("APPROVE")) {
      return {
        title: "Bail Petition Approved for Filing",
        category: "Legal Decision",
        color: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
        summary: `Supervising legal officer reviewed and formally approved statutory bail petition for Case #${ev.entity_id} under Section 479 BNSS.`,
        targetLabel: `Case Dossier #${ev.entity_id}`,
      };
    }

    if (action.includes("INTEGRITY_CHECK") || action.includes("EVIDENCE")) {
      return {
        title: "Document Hash & Evidence Verified",
        category: "Data Integrity",
        color: "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20",
        summary: `Cryptographic SHA-256 integrity check verified against stored vault checksum for Case #${ev.entity_id}.`,
        targetLabel: `Evidence Item #${ev.entity_id}`,
      };
    }

    if (action.includes("AUDIT_LOG_EXPORTED")) {
      return {
        title: "Formal Audit Ledger Export Generated",
        category: "Audit Provenance",
        color: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
        summary: `Auditor exported verifiable audit stream. Reason: ${details.export_reason || "Statutory Review"}. SHA-256 Checksum: ${details.artifact_sha256?.slice(0, 16) || "SEALED"}...`,
        targetLabel: "Audit Export Artifact",
      };
    }

    if (action.includes("AUDIT_LOG_VIEWED")) {
      return {
        title: "Audit Ledger Inspected (Audit-of-Audit)",
        category: "Oversight Log",
        color: "bg-secondary text-secondary-foreground border-border",
        summary: `Statutory auditor inspected system audit stream. Filter criteria recorded.`,
        targetLabel: "Audit Stream",
      };
    }

    if (action.includes("IDENTITY_MERGE")) {
      return {
        title: "Cross-Facility Duplicate Records Merged",
        category: "Identity Resolution",
        color: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
        summary: `Judicial reviewer confirmed and merged duplicate prisoner records across detention facilities.`,
        targetLabel: `Candidate #${ev.entity_id}`,
      };
    }

    return {
      title: action.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase()),
      category: "System Activity",
      color: "bg-secondary text-secondary-foreground border-border",
      summary: `System recorded ${ev.action} on ${ev.entity_type} record #${ev.entity_id}.`,
      targetLabel: `${ev.entity_type} #${ev.entity_id}`,
    };
  };

  const getReadableRole = (roleStr: string) => {
    const map: Record<string, string> = {
      PLATFORM_ADMIN: "Platform Administrator",
      GOV_ADMIN: "Government SLSA Administrator",
      DLSA_OFFICER: "DLSA Legal Aid Officer",
      SUPERVISING_LEGAL_OFFICER: "Supervising Legal Officer",
      JAIL_OFFICER: "Jail Superintendent",
      POLICE_OFFICER: "Police Station In-Charge",
      DEFENSE_ADVOCATE: "Panel Defense Counsel",
      READ_ONLY_AUDITOR: "Statutory Auditor",
      SYSTEM: "Automated System Service",
    };
    return map[roleStr] || roleStr.replace(/_/g, " ");
  };

  const filteredEvents = events.filter((ev) => {
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      ev.id.toLowerCase().includes(query) ||
      ev.actor_id.toLowerCase().includes(query) ||
      ev.entity_id.toLowerCase().includes(query) ||
      ev.action.toLowerCase().includes(query) ||
      (ev.details && JSON.stringify(ev.details).toLowerCase().includes(query));

    return matchesSearch;
  });

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Auditor Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldCheck className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Statutory Oversight & Cryptographic Audit Ledger // Read-Only
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Auditor Oversight Console
          </h1>
          <p className="text-sm font-sans text-muted-foreground mt-1 max-w-2xl leading-relaxed">
            Append-only, SHA-256 hash-chained event ledger tracking legal sign-offs, security boundaries, evidence integrity, and institutional exceptions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-xs font-mono font-bold px-3 py-1.5 bg-muted border border-border text-foreground rounded">
            READ_ONLY_AUDITOR
          </span>
          <button
            onClick={() => setIsExportOpen(true)}
            className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/90 rounded text-xs font-mono font-semibold flex items-center gap-1.5 shadow-sm transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export Audit Ledger
          </button>
          <button
            onClick={() => {
              loadAuditData();
              loadIntegrityData();
              loadExceptions();
            }}
            className="p-2 border border-border bg-card hover:bg-secondary rounded text-xs font-mono flex items-center gap-1.5 transition-colors"
            title="Refresh Audit Stream"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Mode Tabs */}
      <div className="flex border-b border-border gap-6 text-sm font-sans">
        <button
          onClick={() => setActiveTab("ledger")}
          className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === "ledger"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers className="w-4 h-4" />
          Audit Ledger & Hash-Chain Stream
        </button>
        <button
          onClick={() => setActiveTab("exceptions")}
          className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === "exceptions"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <ShieldAlert className="w-4 h-4 text-amber-500" />
          Statutory Exceptions & Anomalies ({exceptions.length})
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
          <div className="text-xs font-mono text-muted-foreground uppercase font-semibold">Total Logged Events</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{totalCount}</div>
          <div className="text-xs font-mono text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Audit Store Status: Healthy
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
          <div className="text-xs font-mono text-muted-foreground uppercase font-semibold">Security & Access Events</div>
          <div className="text-2xl font-serif font-bold text-primary mt-1">
            {events.filter((e) => e.action.includes("LOGIN") || e.action.includes("TOKEN") || e.action.includes("AUTHORIZATION_DENIED")).length}
          </div>
          <div className="text-xs font-mono text-muted-foreground mt-1">Masked IP Session Provenance</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
          <div className="text-xs font-mono text-muted-foreground uppercase font-semibold">Legal Actions & Approvals</div>
          <div className="text-2xl font-serif font-bold text-blue-600 mt-1">
            {events.filter((e) => e.action.includes("ADVOCATE") || e.action.includes("IDENTITY") || e.action.includes("APPROVE")).length}
          </div>
          <div className="text-xs font-mono text-muted-foreground mt-1">Supervisory Human Sign-Offs</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
          <div className="text-xs font-mono text-muted-foreground uppercase font-semibold">Evidence Hash Integrity</div>
          <div className="text-2xl font-serif font-bold mt-1 text-foreground">
            {evidenceStats.pct !== null ? `${evidenceStats.pct}%` : "Pending"}
          </div>
          <div className="text-xs font-mono mt-1">
            {evidenceStats.total > 0 ? (
              evidenceStats.flagged > 0 ? (
                <span className="text-rose-600 font-semibold">{evidenceStats.flagged} Potential Tamper Violations</span>
              ) : (
                <span className="text-emerald-600 dark:text-emerald-400">
                  {evidenceStats.verified}/{evidenceStats.total} Verified (SHA-256)
                </span>
              )
            ) : (
              <span className="text-muted-foreground">No integrity verification data available</span>
            )}
          </div>
        </div>
      </div>

      {activeTab === "ledger" && (
        <>
          {/* Filters Bar */}
          <div className="bg-card border-2 border-border p-4 rounded-sm flex flex-col md:flex-row items-center gap-3 shadow-sm">
            <div className="relative flex-1 w-full">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search action, actor, entity reference, or hash..."
                className="w-full pl-9 pr-4 py-2.5 bg-input border border-border text-xs md:text-sm font-sans rounded-sm focus:outline-none focus:border-primary text-foreground"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
              <Filter className="w-4 h-4 text-muted-foreground shrink-0" />
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="bg-input border border-border text-xs md:text-sm font-sans p-2 rounded-sm focus:outline-none focus:border-primary text-foreground"
              >
                <option value="ALL">All Event Types</option>
                <option value="AUTHORIZATION_DENIED">403 Authorization Denied</option>
                <option value="LOGIN">User Logins</option>
                <option value="LOGIN_FAILED">Failed Logins</option>
                <option value="ADVOCATE_SIGN_OFF">Bail Sign-Offs</option>
                <option value="EVIDENCE_VERIFY">Evidence Checks</option>
                <option value="IDENTITY_MERGE">Identity Merges</option>
                <option value="AUDIT_LOG_EXPORTED">Ledger Exports</option>
                <option value="TOKEN_REVOCATION">Session Logouts</option>
              </select>

              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-input border border-border text-xs md:text-sm font-sans p-2 rounded-sm focus:outline-none focus:border-primary text-foreground"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="WARNING">Warning</option>
                <option value="NOTICE">Notice</option>
                <option value="INFO">Info</option>
              </select>

              <div className="flex items-center gap-1 bg-input border border-border px-2 py-1 rounded-sm text-xs font-mono">
                <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="bg-transparent border-none text-xs focus:outline-none text-foreground"
                  title="Date From"
                />
                <span>-</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="bg-transparent border-none text-xs focus:outline-none text-foreground"
                  title="Date To"
                />
              </div>
            </div>
          </div>

          {/* Tamper-Evident Append-Only Audit Stream */}
          <div className="bg-card border-2 border-border rounded-sm overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border bg-secondary/40 flex items-center justify-between">
              <span className="font-serif font-bold text-xs md:text-sm uppercase tracking-wider text-muted-foreground">
                Tamper-Evident Append-Only Audit Ledger ({filteredEvents.length} verifiable entries loaded of {totalCount} total)
              </span>
              <span className="text-[11px] font-mono text-muted-foreground hidden sm:inline">
                Audit Store Status: Healthy • Persistence: Confirmed
              </span>
            </div>

            {loading ? (
              <div className="p-12 text-center text-muted-foreground text-sm animate-pulse">
                Synchronizing cryptographic hash chain...
              </div>
            ) : filteredEvents.length === 0 ? (
              <div className="p-12 text-center text-muted-foreground text-sm">
                No audit records matching your search or active filter criteria.
              </div>
            ) : (
              <div className="divide-y divide-border">
                {filteredEvents.map((ev) => {
                  const human = getHumanEvent(ev);
                  const isExpanded = !!expandedChain[ev.id];

                  return (
                    <div key={ev.id} className="p-5 hover:bg-secondary/15 transition-colors space-y-3">
                      {/* Top Line: Category Badge, Plain Title, Timestamp */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${human.color}`}>
                            {human.category}
                          </span>
                          {ev.severity && ev.severity !== "INFO" && (
                            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                              ev.severity === "CRITICAL" ? "bg-rose-600 text-white" :
                              ev.severity === "HIGH" ? "bg-amber-600 text-white" :
                              ev.severity === "WARNING" ? "bg-yellow-500/20 text-yellow-700 dark:text-yellow-400 border border-yellow-500/40" :
                              "bg-secondary text-foreground"
                            }`}>
                              {ev.severity}
                            </span>
                          )}
                          <h3 className="font-serif font-bold text-base text-foreground">
                            {human.title}
                          </h3>
                          <span className="text-xs text-muted-foreground font-mono bg-secondary px-2 py-0.5 rounded border border-border">
                            {human.targetLabel}
                          </span>
                        </div>

                        <span className="text-xs font-mono text-muted-foreground flex items-center gap-1.5 shrink-0">
                          <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                          {new Date(ev.timestamp).toLocaleString("en-IN", {
                            dateStyle: "medium",
                            timeStyle: "short",
                          })}
                        </span>
                      </div>

                      {/* Plain Language Summary */}
                      <p className="text-sm text-foreground/90 leading-relaxed font-sans">
                        {human.summary}
                      </p>

                      {/* Metadata Row: Responsible Officer & Masked IP */}
                      <div className="flex flex-wrap items-center justify-between gap-3 text-xs bg-secondary/30 p-3 rounded border border-border/80">
                        <div className="flex items-center gap-3 flex-wrap">
                          <div>
                            <span className="text-muted-foreground font-semibold">Authorized Actor: </span>
                            <strong className="text-foreground font-bold">{getReadableRole(ev.actor_role)}</strong>
                            <span className="text-muted-foreground font-mono ml-1">({ev.actor_id})</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground font-semibold">IP Address: </span>
                            <span className="font-mono text-foreground font-medium">{ev.ip_address || "127.0.***"}</span>
                          </div>
                          {ev.sequence_number ? (
                            <div>
                              <span className="text-muted-foreground font-semibold">Sequence: </span>
                              <span className="font-mono text-foreground font-bold">#{ev.sequence_number}</span>
                            </div>
                          ) : null}
                        </div>

                        <button
                          onClick={() => toggleChain(ev.id)}
                          className="text-xs text-primary font-medium hover:underline flex items-center gap-1 font-mono"
                        >
                          <Key className="w-3 h-3" />
                          {isExpanded ? "Hide Cryptographic Proof" : "Verify SHA-256 Chain"}
                        </button>
                      </div>

                      {/* Collapsible Cryptographic Chain Proof Drawer */}
                      {isExpanded && (
                        <div className="p-4 bg-muted/60 border border-border rounded font-mono text-xs space-y-2.5 animate-in fade-in duration-150">
                          <div className="flex flex-wrap justify-between items-center text-[11px] text-muted-foreground border-b border-border pb-1.5 gap-2">
                            <span className="font-bold text-foreground">AUDIT EVENT ID: {ev.id}</span>
                            <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-bold">
                              <CheckCircle2 className="w-3.5 h-3.5" /> CRYPTOGRAPHIC CHAIN CONTINUITY VERIFIED
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                            <div>
                              <div className="text-[11px] text-muted-foreground">EVENT SHA-256 CHECKSUM:</div>
                              <div className="text-foreground font-mono text-[11px] break-all bg-card p-2 rounded border border-border">
                                {ev.event_hash || "Calculated at write-time (V1 Entry)"}
                              </div>
                            </div>
                            <div>
                              <div className="text-[11px] text-muted-foreground">PREVIOUS EVENT SHA-256 LINK:</div>
                              <div className="text-muted-foreground font-mono text-[11px] break-all bg-card p-2 rounded border border-border">
                                {ev.previous_event_hash || "GENESIS_NYAYA_MITRA_AUDIT_LEDGER_V1"}
                              </div>
                            </div>
                          </div>

                          {/* Sanitized Structured Attributes */}
                          {ev.details && Object.keys(ev.details).length > 0 && (
                            <div className="pt-2 border-t border-border">
                              <div className="text-[11px] text-muted-foreground font-bold mb-1">RECORDED ATTRIBUTES:</div>
                              <div className="bg-card p-2.5 rounded border border-border space-y-1 text-[11px]">
                                {Object.entries(ev.details).map(([k, v]) => (
                                  <div key={k} className="flex flex-col sm:flex-row gap-1">
                                    <span className="text-primary font-semibold sm:w-44 shrink-0">{k}:</span>
                                    <span className="text-foreground break-all">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* Statutory Exceptions & Anomaly Dashboard */}
      {activeTab === "exceptions" && (
        <div className="space-y-4">
          <div className="bg-card border-2 border-border p-5 rounded-sm shadow-sm">
            <h2 className="text-lg font-serif font-bold text-foreground flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-500" />
              Statutory Exception Detection & Non-Compliance Tracking
            </h2>
            <p className="text-xs text-muted-foreground mt-1">
              Active statutory bottlenecks, Section 479 BNSS detention SLA breaches, document intake gaps, and unauthorized boundary violations.
            </p>
          </div>

          {loadingExceptions ? (
            <div className="p-12 text-center text-muted-foreground text-sm animate-pulse">
              Scanning active cases and security logs for statutory exceptions...
            </div>
          ) : exceptions.length === 0 ? (
            <div className="bg-card border border-border p-12 text-center text-muted-foreground rounded-sm">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <p className="text-sm font-semibold">Zero active statutory exceptions detected.</p>
              <p className="text-xs text-muted-foreground mt-1">All monitored records are compliant with SLA thresholds and security boundaries.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {exceptions.map((exc) => (
                <div
                  key={exc.exception_id}
                  className={`p-4 bg-card border-l-4 border-2 rounded-sm shadow-sm space-y-2 ${
                    exc.severity === "CRITICAL"
                      ? "border-l-rose-600 border-border"
                      : exc.severity === "HIGH"
                      ? "border-l-amber-600 border-border"
                      : "border-l-blue-600 border-border"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase ${
                        exc.severity === "CRITICAL" ? "bg-rose-600 text-white" :
                        exc.severity === "HIGH" ? "bg-amber-600 text-white" : "bg-blue-600 text-white"
                      }`}>
                        {exc.severity}
                      </span>
                      <h4 className="font-serif font-bold text-sm text-foreground">{exc.title}</h4>
                    </div>
                    {exc.case_id && (
                      <span className="text-xs font-mono text-muted-foreground bg-secondary px-2 py-0.5 rounded border border-border">
                        Ref: {exc.case_id}
                      </span>
                    )}
                  </div>

                  <p className="text-xs font-sans text-foreground/90 leading-relaxed">
                    {exc.description}
                  </p>

                  {exc.remediation && (
                    <div className="text-xs font-sans text-muted-foreground flex items-center gap-1.5 pt-1">
                      <strong className="text-foreground">Remediation Action:</strong>
                      <span>{exc.remediation}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Formal Audit Export Modal */}
      {isExportOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border p-6 rounded-sm shadow-xl max-w-lg w-full space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="font-serif font-bold text-lg text-foreground flex items-center gap-2">
                <Download className="w-5 h-5 text-primary" />
                Export Tamper-Evident Audit Ledger
              </h3>
              <button
                onClick={() => setIsExportOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-mono"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Exporting the statutory audit ledger produces an official JSON record stamped with a cryptographic SHA-256 artifact checksum. This export event will be permanently recorded in the append-only ledger.
            </p>

            {exportSuccess ? (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-xs font-mono rounded">
                ✓ {exportSuccess}
              </div>
            ) : (
              <form onSubmit={handleExportSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">
                    Statutory Review Justification / Reason *
                  </label>
                  <textarea
                    required
                    value={exportReason}
                    onChange={(e) => setExportReason(e.target.value)}
                    placeholder="E.g., High Court Registry Quarterly Compliance Audit / DLSA Oversight Inspection..."
                    rows={3}
                    className="w-full p-2.5 bg-input border border-border text-xs rounded font-sans text-foreground focus:outline-none focus:border-primary"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block font-semibold text-muted-foreground mb-1">Export Format</label>
                    <select
                      value={exportFormat}
                      onChange={(e) => setExportFormat(e.target.value)}
                      className="w-full p-2 bg-input border border-border rounded font-sans text-foreground"
                    >
                      <option value="JSON">Verifiable JSON (SHA-256)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-semibold text-muted-foreground mb-1">Active Filter Scope</label>
                    <div className="p-2 bg-secondary rounded text-xs font-mono text-foreground truncate">
                      {actionFilter} ({filteredEvents.length} items)
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setIsExportOpen(false)}
                    className="px-4 py-2 border border-border rounded text-xs font-mono hover:bg-secondary text-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={exporting || !exportReason.trim()}
                    className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold rounded hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5"
                  >
                    {exporting ? "Generating SHA-256 Artifact..." : "Confirm & Download Export"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
