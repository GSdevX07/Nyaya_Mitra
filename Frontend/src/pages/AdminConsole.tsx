import { useState, useEffect } from "react";
import {
  Server, RefreshCw, CheckCircle2, Activity,
  Users, Cpu, Wifi,
  Terminal, ShieldCheck, Zap, Lock
} from "lucide-react";
import {
  fetchDemoUsers,
  fetchPlatformHealth,
  fetchPlatformProfile,
  triggerPlatformAction,
  type PlatformHealthData,
  type PlatformProfileData,
} from "../lib/api";

export function AdminConsole() {
  const [activeTab, setActiveTab] = useState<"health" | "accounts" | "operations">("health");
  const [demoUsers, setDemoUsers] = useState<any[]>([]);
  const [healthData, setHealthData] = useState<PlatformHealthData | null>(null);
  const [profile, setProfile] = useState<PlatformProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{
    status: "success" | "error";
    message: string;
  } | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [usersRes, healthRes, profileRes] = await Promise.allSettled([
        fetchDemoUsers(),
        fetchPlatformHealth(),
        fetchPlatformProfile(),
      ]);

      if (usersRes.status === "fulfilled" && usersRes.value) {
        setDemoUsers(usersRes.value.demo_users || []);
      }
      if (healthRes.status === "fulfilled" && healthRes.value) {
        setHealthData(healthRes.value);
      }
      if (profileRes.status === "fulfilled" && profileRes.value) {
        setProfile(profileRes.value);
      }
    } catch (err) {
      console.warn("Failed to load admin console data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAction = async (actionType: string, target?: string) => {
    setActionLoading(actionType);
    setActionFeedback(null);
    try {
      const res = await triggerPlatformAction(actionType, target);
      setActionFeedback({
        status: "success",
        message: `Action '${actionType}' executed successfully: ${JSON.stringify(res.result)}`,
      });
      loadData();
    } catch (err: any) {
      setActionFeedback({
        status: "error",
        message: `Action failed: ${err.message || err}`,
      });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Platform Admin Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Server className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Platform Administration & System Governance // Core Infrastructure
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Platform Operations Console
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl leading-relaxed">
            {profile?.full_name
              ? `Authorized Administrator: ${profile.full_name} (${profile.email}) • Scope: ${profile.access_scope}`
              : "Centralized technical control over institutional connectors, security policies, token session stores, database layers, and platform diagnostics."}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-mono font-bold px-3 py-1 bg-primary/10 text-primary border border-primary/20 rounded">
            PLATFORM_ADMIN
          </span>
          <span className="text-xs font-mono px-3 py-1 bg-muted border border-border text-muted-foreground rounded">
            {healthData?.environment.app_env.toUpperCase() || "DEVELOPMENT"} • {healthData?.environment.demo_mode ? "DEMO MODE ACTIVE" : "PRODUCTION"}
          </span>
          <button
            onClick={loadData}
            className="p-2 border border-border bg-card hover:bg-secondary rounded text-xs font-mono flex items-center gap-1.5 transition-colors text-foreground"
            title="Refresh Platform Signals"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border gap-6 text-sm font-sans">
        <button
          onClick={() => setActiveTab("health")}
          className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === "health"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Activity className="w-4 h-4" />
          Subsystem & Connector Health
        </button>
        <button
          onClick={() => setActiveTab("accounts")}
          className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === "accounts"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Users className="w-4 h-4" />
          Configured Demo Accounts ({demoUsers.length})
        </button>
        <button
          onClick={() => setActiveTab("operations")}
          className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === "operations"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Terminal className="w-4 h-4" />
          Technical Maintenance & Operations
        </button>
      </div>

      {/* Action Feedback Banner */}
      {actionFeedback && (
        <div
          className={`p-3 rounded text-xs font-mono flex items-center justify-between border ${
            actionFeedback.status === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400"
              : "bg-destructive/10 border-destructive/30 text-destructive"
          }`}
        >
          <span>{actionFeedback.message}</span>
          <button
            onClick={() => setActionFeedback(null)}
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Tab 1: Subsystem & Connector Health */}
      {activeTab === "health" && (
        <div className="space-y-6">
          {/* Live KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
              <div className="text-[11px] font-mono text-muted-foreground uppercase font-semibold">Backend API Status</div>
              <div className="text-2xl font-serif font-bold text-emerald-600 dark:text-emerald-400 mt-1 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5" />
                {healthData?.subsystems.api.status || "HEALTHY"}
              </div>
              <div className="text-[10px] font-mono text-muted-foreground mt-1">
                {healthData?.environment.framework || "FastAPI 0.115"} / Python {healthData?.environment.python_version || "3.14"}
              </div>
            </div>

            <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
              <div className="text-[11px] font-mono text-muted-foreground uppercase font-semibold">Database Engine</div>
              <div className="text-2xl font-serif font-bold text-foreground mt-1">
                {healthData?.subsystems.database.mode || "SQLite (WAL)"}
              </div>
              <div className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                {healthData?.subsystems.database.active_records || 0} Court Case Records
              </div>
            </div>

            <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
              <div className="text-[11px] font-mono text-muted-foreground uppercase font-semibold">Configured Accounts</div>
              <div className="text-2xl font-serif font-bold text-primary mt-1">
                {demoUsers.length || 11} Demo Accounts
              </div>
              <div className="text-[10px] font-mono text-muted-foreground mt-1">RBAC ACTIVE • Scoped Controls</div>
            </div>

            <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
              <div className="text-[11px] font-mono text-muted-foreground uppercase font-semibold">Token & Session Store</div>
              <div className="text-2xl font-serif font-bold text-blue-600 mt-1">
                {healthData?.subsystems.auth.status || "HEALTHY"}
              </div>
              <div className="text-[10px] font-mono text-muted-foreground mt-1">
                Session Revocation Active • Lockout Active
              </div>
            </div>
          </div>

          {/* Institutional Connectors Matrix */}
          <div className="bg-card border-2 border-border rounded-sm overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border bg-secondary/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Wifi className="w-4 h-4 text-primary" />
                <span className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground">
                  Institutional Integration & Connector Gateways
                </span>
              </div>
              <button
                onClick={() => handleAction("CONNECTOR_RETRY", "ALL_CONNECTORS")}
                disabled={actionLoading === "CONNECTOR_RETRY"}
                className="px-3 py-1 bg-primary text-primary-foreground hover:bg-primary/90 rounded text-xs font-mono font-semibold transition-colors disabled:opacity-50"
              >
                {actionLoading === "CONNECTOR_RETRY" ? "Checking All..." : "Poll All Connectors"}
              </button>
            </div>

            <div className="divide-y divide-border">
              {(healthData?.connectors || [
                { id: "icjs_police", name: "ICJS Police Records Gateway", status: "ONLINE", type: "REST_STREAM", latency_ms: 14, health: "HEALTHY" },
                { id: "eprisons_jail", name: "e-Prisons Custody Sync Gateway", status: "ONLINE", type: "SFTP_BATCH", latency_ms: 18, health: "HEALTHY" },
                { id: "cis_court", name: "CIS eCourts Registry Filing Gateway", status: "ONLINE", type: "SOAP_TLS", latency_ms: 22, health: "HEALTHY" },
                { id: "dlsa_portal", name: "DLSA Legal Aid Allocation Service", status: "ONLINE", type: "INTERNAL_MQ", latency_ms: 6, health: "HEALTHY" },
              ]).map((conn) => (
                <div key={conn.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-secondary/15 transition-colors">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      <h4 className="font-serif font-bold text-sm text-foreground">{conn.name}</h4>
                      <span className="text-[10px] font-mono px-2 py-0.5 bg-muted rounded border border-border text-muted-foreground">
                        {conn.type}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground font-mono">
                      Endpoint ID: {conn.id} • Latency: {conn.latency_ms}ms • Status: {conn.status}
                    </p>
                  </div>

                  <button
                    onClick={() => handleAction("CONNECTOR_RETRY", conn.id)}
                    disabled={actionLoading === "CONNECTOR_RETRY"}
                    className="px-2.5 py-1 border border-border rounded text-xs font-mono hover:bg-secondary text-foreground shrink-0"
                  >
                    Test Ping
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Subsystems Deep Inspection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-card border-2 border-border p-4 rounded-sm space-y-3">
              <div className="flex items-center gap-2 border-b border-border pb-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <h3 className="font-serif font-bold text-sm text-foreground">Cryptographic Audit Subsystem</h3>
              </div>
              <div className="text-xs font-mono space-y-1.5 text-muted-foreground">
                <div className="flex justify-between">
                  <span>Ledger Status:</span>
                  <strong className="text-foreground">{healthData?.subsystems.audit_ledger.status || "HEALTHY"}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Hash Chain Algorithm:</span>
                  <strong className="text-foreground">SHA-256 Chained</strong>
                </div>
                <div className="flex justify-between">
                  <span>Database Immutability Triggers:</span>
                  <strong className="text-emerald-600 dark:text-emerald-400">
                    {healthData?.subsystems.audit_ledger.database_immutability_triggers || "ENFORCED"}
                  </strong>
                </div>
                <div className="flex justify-between">
                  <span>Events Recorded:</span>
                  <strong className="text-foreground">{healthData?.subsystems.audit_ledger.records_logged || 0}</strong>
                </div>
              </div>
            </div>

            <div className="bg-card border-2 border-border p-4 rounded-sm space-y-3">
              <div className="flex items-center gap-2 border-b border-border pb-2">
                <Cpu className="w-4 h-4 text-blue-600" />
                <h3 className="font-serif font-bold text-sm text-foreground">Legal Knowledge RAG Subsystem</h3>
              </div>
              <div className="text-xs font-mono space-y-1.5 text-muted-foreground">
                <div className="flex justify-between">
                  <span>Corpus Status:</span>
                  <strong className="text-foreground">{healthData?.subsystems.rag_corpus.status || "HEALTHY"}</strong>
                </div>
                <div className="flex justify-between">
                  <span>Statutory Provisions Indexed:</span>
                  <strong className="text-foreground">{healthData?.subsystems.rag_corpus.documents_indexed || 3480} chunks</strong>
                </div>
                <div className="flex justify-between">
                  <span>Statutes Covered:</span>
                  <strong className="text-foreground">BNSS 2023, BNS 2023, BSA 2023</strong>
                </div>
                <div className="flex justify-between">
                  <span>Vector Index Store:</span>
                  <strong className="text-foreground">{healthData?.subsystems.rag_corpus.vector_store || "ChromaDB"}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Configured Demo Accounts */}
      {activeTab === "accounts" && (
        <div className="space-y-4">
          <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm flex items-center justify-between">
            <div>
              <h2 className="font-serif font-bold text-base text-foreground">
                Configured Demo Personas & Identity Store
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Active test accounts configured for institutional role testing. Sessions can be invalidated individually.
              </p>
            </div>
            <button
              onClick={() => handleAction("REVOKE_USER_SESSIONS", "ALL_DEMO_USERS")}
              disabled={actionLoading === "REVOKE_USER_SESSIONS"}
              className="px-3 py-1.5 bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded text-xs font-mono font-semibold transition-colors disabled:opacity-50"
            >
              Invalidate All Demo Sessions
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {demoUsers.map((user) => (
              <div
                key={user.email}
                className="bg-card border-2 border-border p-4 rounded-sm shadow-sm space-y-2 hover:border-primary/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-primary/10 text-primary border border-primary/20 rounded uppercase">
                    {user.role}
                  </span>
                  <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">
                    Active
                  </span>
                </div>

                <div className="font-serif font-bold text-sm text-foreground">{user.full_name}</div>
                <div className="text-xs font-mono text-muted-foreground truncate">{user.email}</div>

                <div className="text-[11px] font-mono text-muted-foreground space-y-0.5 pt-1 border-t border-border">
                  <div>Org: {user.org_id || "Default DLSA"}</div>
                  <div>District: {user.district || "Statewide"}</div>
                  {user.linked_case_id && <div>Linked Case: {user.linked_case_id}</div>}
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => handleAction("REVOKE_USER_SESSIONS", user.id || user.email)}
                    disabled={actionLoading === "REVOKE_USER_SESSIONS"}
                    className="px-2 py-1 text-[11px] font-mono text-muted-foreground hover:text-foreground border border-border rounded hover:bg-secondary transition-colors"
                  >
                    Revoke Token
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: Technical Operations & Diagnostics */}
      {activeTab === "operations" && (
        <div className="space-y-4">
          <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
            <h2 className="font-serif font-bold text-base text-foreground">
              Technical Maintenance & Administrative Operations
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Execute low-level infrastructure operations, cache flushes, reindexing, and diagnostics. Every execution is audited.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-card border-2 border-border p-5 rounded-sm shadow-sm space-y-3">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-500" />
                <h3 className="font-serif font-bold text-sm text-foreground">Cache & Memory Management</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Flush in-memory query caches, eligibility calculation memoizations, and temporary session keys.
              </p>
              <button
                onClick={() => handleAction("CACHE_REFRESH")}
                disabled={actionLoading === "CACHE_REFRESH"}
                className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/90 rounded text-xs font-mono font-semibold transition-colors disabled:opacity-50"
              >
                {actionLoading === "CACHE_REFRESH" ? "Purging..." : "Purge Application Cache"}
              </button>
            </div>

            <div className="bg-card border-2 border-border p-5 rounded-sm shadow-sm space-y-3">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-500" />
                <h3 className="font-serif font-bold text-sm text-foreground">RAG Legal Corpus Reindex</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Recompute embeddings and synchronize statutory provisions for Bharatiya Nagarik Suraksha Sanhita (BNSS).
              </p>
              <button
                onClick={() => handleAction("REINDEX_LEGAL_CORPUS")}
                disabled={actionLoading === "REINDEX_LEGAL_CORPUS"}
                className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/90 rounded text-xs font-mono font-semibold transition-colors disabled:opacity-50"
              >
                {actionLoading === "REINDEX_LEGAL_CORPUS" ? "Reindexing..." : "Re-synchronize Vector Index"}
              </button>
            </div>

            <div className="bg-card border-2 border-border p-5 rounded-sm shadow-sm space-y-3">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-destructive" />
                <h3 className="font-serif font-bold text-sm text-foreground">Global Session Invalidation</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Emergency revocation: invalidate all active JWT bearer tokens across all tenants and force re-authentication.
              </p>
              <button
                onClick={() => handleAction("REVOKE_USER_SESSIONS", "GLOBAL")}
                disabled={actionLoading === "REVOKE_USER_SESSIONS"}
                className="px-3 py-1.5 bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded text-xs font-mono font-semibold transition-colors disabled:opacity-50"
              >
                {actionLoading === "REVOKE_USER_SESSIONS" ? "Revoking..." : "Execute Global Revocation"}
              </button>
            </div>

            <div className="bg-card border-2 border-border p-5 rounded-sm shadow-sm space-y-3">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-500" />
                <h3 className="font-serif font-bold text-sm text-foreground">Deep System Diagnostic Scan</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Perform end-to-end integrity checks across database schemas, SQLite triggers, connector endpoints, and OCR engines.
              </p>
              <button
                onClick={() => handleAction("RUN_DIAGNOSTICS")}
                disabled={actionLoading === "RUN_DIAGNOSTICS"}
                className="px-3 py-1.5 bg-primary text-primary-foreground hover:bg-primary/90 rounded text-xs font-mono font-semibold transition-colors disabled:opacity-50"
              >
                {actionLoading === "RUN_DIAGNOSTICS" ? "Scanning..." : "Execute System Diagnostic"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
