import React, { useState, useEffect } from "react";
import {
  Database, UploadCloud, RefreshCw, AlertTriangle, CheckCircle2,
  ShieldCheck, Users, Check, X
} from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

interface Connector {
  id: string;
  name: string;
  display_name: string;
  connector_type: string;
  organization_owner: string;
  auth_method: string;
  is_simulated: boolean;
  sync_status: string;
  last_successful_sync?: string;
  records_received: number;
  records_rejected: number;
  validation_failures: number;
  duplicates_detected: number;
  conflicts_count: number;
}

interface FieldConflict {
  id: string;
  case_id: string;
  accused_id: string;
  accused_name: string;
  field_name: string;
  canonical_value: any;
  canonical_source: string;
  canonical_timestamp: string;
  proposed_value: any;
  proposed_source: string;
  proposed_timestamp: string;
  severity: string;
  status: string;
}

interface IdentityMatchCandidate {
  id: string;
  incoming_raw_id: string;
  candidate_accused_id: string;
  candidate_name: string;
  incoming_name: string;
  similarity_score: number;
  confidence: string;
  match_reasons: string[];
  status: string;
}

interface IngestionDashboardData {
  connectors: Connector[];
  total_records_ingested: number;
  validation_failures_total: number;
  conflicts_awaiting_review: number;
  identity_merges_pending: number;
  active_feeds_count: number;
  stale_feeds_count: number;
  last_sync_timestamp: string;
  demo_mode_active: boolean;
}

export function IngestionDashboard() {
  const [telemetry, setTelemetry] = useState<IngestionDashboardData | null>(null);
  const [conflicts, setConflicts] = useState<FieldConflict[]>([]);
  const [merges, setMerges] = useState<IdentityMatchCandidate[]>([]);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"connectors" | "import" | "conflicts" | "identities">("connectors");
  const [csvText, setCsvText] = useState("");
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  const fetchTelemetry = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/ingestion/dashboard`);
      if (res.ok) {
        const data = await res.json();
        setTelemetry(data);
      }
      const cRes = await fetch(`${API_BASE_URL}/ingestion/conflicts`);
      if (cRes.ok) {
        setConflicts(await cRes.json());
      }
      const mRes = await fetch(`${API_BASE_URL}/ingestion/identity-merges`);
      if (mRes.ok) {
        setMerges(await mRes.json());
      }
    } catch (err) {
      console.warn("Ingestion telemetry fetch error:", err);
    }
  };

  useEffect(() => {
    fetchTelemetry();
  }, []);

  const handleSyncTrigger = async (connectorId: string) => {
    setSyncingId(connectorId);
    try {
      const res = await fetch(`${API_BASE_URL}/ingestion/connectors/${connectorId}/sync`, {
        method: "POST",
      });
      if (res.ok) {
        await fetchTelemetry();
      }
    } catch (err) {
      console.error("Sync error:", err);
    } finally {
      setSyncingId(null);
    }
  };

  const handleResolveConflict = async (conflictId: string, resolution: "ACCEPTED_PROPOSED" | "KEPT_CANONICAL") => {
    try {
      const res = await fetch(`${API_BASE_URL}/ingestion/conflicts/${conflictId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolution, notes: "Resolved in Ingestion Dashboard" }),
      });
      if (res.ok) {
        setConflicts(prev => prev.filter(c => c.id !== conflictId));
        await fetchTelemetry();
      }
    } catch (err) {
      console.error("Resolve conflict error:", err);
    }
  };

  const handleResolveIdentityMerge = async (mergeId: string, confirmMerge: boolean) => {
    try {
      const res = await fetch(`${API_BASE_URL}/ingestion/identity-merges/${mergeId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm_merge: confirmMerge, notes: "Identity reviewed by officer" }),
      });
      if (res.ok) {
        setMerges(prev => prev.filter(m => m.id !== mergeId));
        await fetchTelemetry();
      }
    } catch (err) {
      console.error("Resolve identity merge error:", err);
    }
  };

  const handleCsvImport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvText.trim()) return;

    setUploadStatus("Uploading and parsing batch...");
    try {
      const blob = new Blob([csvText], { type: "text/csv" });
      const file = new File([blob], "manual_import.csv", { type: "text/csv" });
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_BASE_URL}/ingestion/upload`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setUploadStatus(`Success! Ingested ${data.valid_records} of ${data.total_records} records. Conflicts: ${data.conflicts_detected}`);
        setCsvText("");
        await fetchTelemetry();
      } else {
        const err = await res.json();
        setUploadStatus(`Import error: ${err.detail || "Validation failed"}`);
      }
    } catch (err: any) {
      setUploadStatus(`Error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Institutional Data Layer // Stage 04
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Data Ingestion & Multi-Source Coordination
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Modular connectors for ePrisons, eCourts, CCTNS police webhooks, structured spreadsheets, and controlled manual intake with strict conflict preservation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchTelemetry()}
            className="flex items-center gap-1.5 px-3 py-2 bg-muted hover:bg-muted/80 text-foreground text-xs font-mono font-bold uppercase rounded-sm border border-border transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      {/* Overview Stat Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Total Ingested</div>
          <div className="text-2xl font-serif font-black text-foreground mt-1">
            {telemetry?.total_records_ingested ?? 0}
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Active Provenance
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Active Connectors</div>
          <div className="text-2xl font-serif font-black text-primary mt-1">
            {telemetry?.active_feeds_count ?? 0} / {telemetry?.connectors.length ?? 0}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">
            {telemetry?.demo_mode_active ? "DEMO_MODE ACTIVE" : "PRODUCTION"}
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Field Conflicts</div>
          <div className="text-2xl font-serif font-black text-amber-600 mt-1">
            {conflicts.length}
          </div>
          <div className="text-[10px] font-mono text-amber-600 mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Awaiting Human Review
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Identity Merges</div>
          <div className="text-2xl font-serif font-black text-blue-600 mt-1">
            {merges.length}
          </div>
          <div className="text-[10px] font-mono text-blue-600 mt-1 flex items-center gap-1">
            <Users className="w-3 h-3" /> Uncertain Matches
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b-2 border-border gap-2">
        <button
          onClick={() => setActiveTab("connectors")}
          className={`px-4 py-2.5 text-xs font-mono font-bold uppercase transition-all ${
            activeTab === "connectors"
              ? "border-b-2 border-primary text-primary -mb-[2px] bg-card"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Connectors ({telemetry?.connectors.length ?? 0})
        </button>
        <button
          onClick={() => setActiveTab("import")}
          className={`px-4 py-2.5 text-xs font-mono font-bold uppercase transition-all ${
            activeTab === "import"
              ? "border-b-2 border-primary text-primary -mb-[2px] bg-card"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Spreadsheet Import Hub
        </button>
        <button
          onClick={() => setActiveTab("conflicts")}
          className={`px-4 py-2.5 text-xs font-mono font-bold uppercase transition-all flex items-center gap-1.5 ${
            activeTab === "conflicts"
              ? "border-b-2 border-primary text-primary -mb-[2px] bg-card"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Conflict Resolution Queue
          {conflicts.length > 0 && (
            <span className="px-1.5 py-0.2 bg-amber-500/20 text-amber-600 text-[10px] rounded-full">
              {conflicts.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("identities")}
          className={`px-4 py-2.5 text-xs font-mono font-bold uppercase transition-all flex items-center gap-1.5 ${
            activeTab === "identities"
              ? "border-b-2 border-primary text-primary -mb-[2px] bg-card"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Identity Deduplication
          {merges.length > 0 && (
            <span className="px-1.5 py-0.2 bg-blue-500/20 text-blue-600 text-[10px] rounded-full">
              {merges.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab 1: Connectors Grid */}
      {activeTab === "connectors" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {telemetry?.connectors.map((c) => (
            <div key={c.id} className="bg-card border-2 border-border p-5 rounded-sm shadow-sm space-y-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                    c.sync_status === "HEALTHY" ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/30" : "bg-amber-500/10 text-amber-600"
                  }`}>
                    {c.sync_status}
                  </span>
                  {c.is_simulated && (
                    <span className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded font-bold">
                      SIMULATED
                    </span>
                  )}
                </div>

                <h3 className="font-serif font-black text-sm text-foreground uppercase mt-2">
                  {c.display_name}
                </h3>
                <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                  Type: <span className="text-foreground">{c.connector_type}</span>
                </div>
                <div className="text-[11px] font-mono text-muted-foreground">
                  Owner: <span className="text-foreground">{c.organization_owner}</span>
                </div>
              </div>

              <div className="border-t border-border pt-3 space-y-2">
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                  <div>
                    <span className="text-muted-foreground">Received: </span>
                    <span className="font-bold text-foreground">{c.records_received}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Duplicates: </span>
                    <span className="font-bold text-foreground">{c.duplicates_detected}</span>
                  </div>
                </div>

                {c.is_simulated && (
                  <button
                    onClick={() => handleSyncTrigger(c.id)}
                    disabled={syncingId === c.id}
                    className="w-full mt-2 py-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 text-xs font-mono font-bold uppercase rounded-sm flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                  >
                    {syncingId === c.id ? (
                      <div className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <RefreshCw className="w-3 h-3" />
                    )}
                    Trigger Live Sync
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 2: Spreadsheet Import Hub */}
      {activeTab === "import" && (
        <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm space-y-4 max-w-3xl">
          <div>
            <h2 className="text-lg font-serif font-black uppercase text-foreground">
              Direct CSV / Spreadsheet Bulk Importer
            </h2>
            <p className="text-xs font-sans text-muted-foreground mt-0.5">
              Paste or upload CSV rosters containing prisoner names, arrest dates, offenses, and court dockets.
            </p>
          </div>

          <form onSubmit={handleCsvImport} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-mono font-bold uppercase text-foreground block">
                CSV Payload Data
              </label>
              <textarea
                rows={6}
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                placeholder={"prisoner_name,age,gender,offense,arrest_date,custody_days,jail_location\nSanjay Gupta,35,Male,BNS 303(2),2024-08-10,380,Tihar Jail 4"}
                className="w-full bg-input border-2 border-border p-3 font-mono text-xs text-foreground rounded-sm focus:outline-none focus:border-primary"
              />
            </div>

            <button
              type="submit"
              className="px-5 py-2.5 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm hover:opacity-90 flex items-center gap-2"
            >
              <UploadCloud className="w-4 h-4" /> Ingest & Normalize Batch
            </button>
          </form>

          {uploadStatus && (
            <div className="p-3 bg-muted border border-border text-xs font-mono text-foreground rounded-sm">
              {uploadStatus}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Conflict Resolution Queue */}
      {activeTab === "conflicts" && (
        <div className="space-y-4">
          {conflicts.length === 0 ? (
            <div className="bg-card border-2 border-border p-8 rounded-sm text-center text-muted-foreground font-mono text-xs">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              No pending field conflicts. All incoming feeds reconciled with canonical records.
            </div>
          ) : (
            conflicts.map((conf) => (
              <div key={conf.id} className="bg-card border-2 border-amber-500/40 p-5 rounded-sm shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono bg-amber-500/20 text-amber-700 px-2 py-0.5 rounded font-bold uppercase">
                      {conf.severity} CONFLICT
                    </span>
                    <span className="font-mono text-xs font-bold text-foreground">
                      Case: [{conf.case_id}] — {conf.accused_name}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    Field: <span className="font-bold text-foreground uppercase">{conf.field_name}</span>
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono bg-muted/30 p-4 border border-border rounded-sm">
                  <div className="space-y-1">
                    <div className="text-[10px] text-muted-foreground uppercase font-bold">Trusted Canonical Value</div>
                    <div className="p-2.5 bg-background border border-border rounded font-bold text-foreground">
                      {JSON.stringify(conf.canonical_value)}
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      Source: {conf.canonical_source}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[10px] text-muted-foreground uppercase font-bold text-amber-600">Proposed Discrepancy</div>
                    <div className="p-2.5 bg-background border border-amber-500/30 rounded font-bold text-amber-700">
                      {JSON.stringify(conf.proposed_value)}
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      Source: {conf.proposed_source}
                    </div>
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    onClick={() => handleResolveConflict(conf.id, "KEPT_CANONICAL")}
                    className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground border border-border text-xs font-mono font-bold uppercase rounded-sm flex items-center gap-1.5"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" /> Keep Canonical
                  </button>
                  <button
                    onClick={() => handleResolveConflict(conf.id, "ACCEPTED_PROPOSED")}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-mono font-bold uppercase rounded-sm flex items-center gap-1.5"
                  >
                    <Check className="w-3.5 h-3.5" /> Accept Proposed Update
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab 4: Identity Deduplication Queue */}
      {activeTab === "identities" && (
        <div className="space-y-4">
          {merges.length === 0 ? (
            <div className="bg-card border-2 border-border p-8 rounded-sm text-center text-muted-foreground font-mono text-xs">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              No ambiguous identity candidates pending review.
            </div>
          ) : (
            merges.map((cand) => (
              <div key={cand.id} className="bg-card border-2 border-blue-500/40 p-5 rounded-sm shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono bg-blue-500/20 text-blue-700 px-2 py-0.5 rounded font-bold uppercase">
                      {cand.confidence} ({Math.round(cand.similarity_score * 100)}% match)
                    </span>
                    <span className="font-mono text-xs font-bold text-foreground">
                      Candidate Accused: [{cand.candidate_accused_id}]
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs font-mono bg-muted/30 p-3 rounded border border-border">
                  <div>
                    <span className="text-muted-foreground">Existing Subject: </span>
                    <span className="font-bold text-foreground">{cand.candidate_name}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Incoming Subject: </span>
                    <span className="font-bold text-foreground">{cand.incoming_name}</span>
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="text-[11px] font-mono font-bold text-muted-foreground uppercase">Match Reasons:</div>
                  <ul className="text-xs font-mono list-disc list-inside text-foreground/80 space-y-0.5">
                    {cand.match_reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    onClick={() => handleResolveIdentityMerge(cand.id, false)}
                    className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground border border-border text-xs font-mono font-bold uppercase rounded-sm flex items-center gap-1.5"
                  >
                    <X className="w-3.5 h-3.5" /> Keep As Separate Person
                  </button>
                  <button
                    onClick={() => handleResolveIdentityMerge(cand.id, true)}
                    className="px-4 py-2 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded-sm flex items-center gap-1.5"
                  >
                    <Check className="w-3.5 h-3.5" /> Confirm Merge Identity
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
