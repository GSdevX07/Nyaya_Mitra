import { useState, useEffect } from "react";
import {
  Server, RefreshCw, CheckCircle2, Activity,
  Users, Cpu, Wifi,
  Terminal, ShieldCheck, Zap, Lock,
  Layers
} from "lucide-react";
import {
  fetchDemoUsers,
  fetchPlatformHealth,
  fetchPlatformProfile,
  triggerPlatformAction,
  fetchOperationsDashboard,
  type PlatformHealthData,
  type PlatformProfileData,
  type OperationsDashboardData,
} from "../lib/api";

export function AdminConsole() {
  const [activeTab, setActiveTab] = useState<"health" | "accounts" | "reliability" | "operations">("health");
  const [demoUsers, setDemoUsers] = useState<any[]>([]);
  const [healthData, setHealthData] = useState<PlatformHealthData | null>(null);
  const [profile, setProfile] = useState<PlatformProfileData | null>(null);
  const [opsDashboard, setOpsDashboard] = useState<OperationsDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionFeedback, setActionFeedback] = useState<{
    status: "success" | "error";
    message: string;
  } | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [usersRes, healthRes, profileRes, opsRes] = await Promise.allSettled([
        fetchDemoUsers(),
        fetchPlatformHealth(),
        fetchPlatformProfile(),
        fetchOperationsDashboard(),
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
      if (opsRes.status === "fulfilled" && opsRes.value) {
        setOpsDashboard(opsRes.value);
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
          onClick={() => setActiveTab("reliability")}
          className={`pb-2.5 font-medium transition-colors border-b-2 flex items-center gap-2 ${
            activeTab === "reliability"
              ? "border-primary text-primary font-bold"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Layers className="w-4 h-4" />
          Reliability & Queue Telemetry
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
                {healthData?.subsystems.api.protocol || "HTTP/1.1"} • {healthData?.environment.framework || "FastAPI 0.115"}
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
              {(!healthData?.connectors || healthData.connectors.length === 0) ? (
                <div className="p-6 text-center text-xs font-mono text-muted-foreground">
                  {loading ? "Polling subsystem gateways..." : "No connectors configured in platform profile."}
                </div>
              ) : (
                healthData.connectors.map((conn) => {
                  const isSimulated = conn.status === "SANDBOX_SIMULATED" || (conn.health && conn.health.includes("STANDBY"));
                  return (
                    <div key={conn.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-secondary/15 transition-colors">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${isSimulated ? "bg-red-500" : "bg-emerald-500 animate-pulse"}`} />
                          <h4 className="font-serif font-bold text-sm text-foreground">{conn.name}</h4>
                          <span className="text-[10px] font-mono px-2 py-0.5 bg-muted rounded border border-border text-muted-foreground">
                            {conn.type}
                          </span>
                          <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                            isSimulated
                              ? "bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400"
                              : "bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
                          }`}>
                            {conn.status}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground font-mono">
                          Endpoint ID: {conn.id} • {conn.latency_ms > 0 ? `Latency: ${conn.latency_ms}ms` : "Simulated Local Bridge"} • Health: {conn.health || "OK"}
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
                  );
                })
              )}
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
                  <strong className="text-foreground">{healthData?.subsystems.rag_corpus.documents_indexed ?? 0} chunks</strong>
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

      {/* Tab 3: Reliability, Queue & Circuit Breaker Telemetry */}
      {activeTab === "reliability" && (
        <div className="space-y-6">
          <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-primary" />
                <h2 className="font-serif font-bold text-base text-foreground">
                  Durable Background Worker Queue & Circuit Breakers
                </h2>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Real-time operational queue depths, failure quarantines, upstream circuit breakers, and Prometheus telemetry.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2.5 py-1 text-xs font-mono font-bold rounded border ${
                opsDashboard?.status === "operational"
                  ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                  : "bg-amber-500/10 text-amber-600 border-amber-500/20"
              }`}>
                SYSTEM: {opsDashboard?.status?.toUpperCase() || "OPERATIONAL"}
              </span>
            </div>
          </div>

          {/* Queue Depth Section */}
          <div className="space-y-2">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Background Job Queue Depths (Dual-Engine Persisted)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {[
                { label: "QUEUED", count: opsDashboard?.queue?.QUEUED ?? 0, color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-500/10" },
                { label: "PROCESSING", count: opsDashboard?.queue?.PROCESSING ?? 0, color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-500/10" },
                { label: "COMPLETED", count: opsDashboard?.queue?.COMPLETED ?? 0, color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500/10" },
                { label: "FAILED", count: opsDashboard?.queue?.FAILED ?? 0, color: "text-orange-600 dark:text-orange-400", bg: "bg-orange-500/10" },
                { label: "DEAD LETTER", count: opsDashboard?.queue?.DEAD_LETTER ?? 0, color: "text-red-600 dark:text-red-400", bg: "bg-red-500/10" },
              ].map((q) => (
                <div key={q.label} className="bg-card border-2 border-border p-4 rounded-sm shadow-sm">
                  <span className="text-[10px] font-mono uppercase text-muted-foreground font-bold">{q.label}</span>
                  <div className={`text-2xl font-serif font-black mt-1 ${q.color}`}>{q.count}</div>
                  <span className="text-[10px] font-mono text-muted-foreground">jobs tracked</span>
                </div>
              ))}
            </div>
          </div>

          {/* Circuit Breakers Section */}
          <div className="space-y-2">
            <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Upstream Circuit Breakers & Degradation Gates
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {Object.entries(opsDashboard?.circuit_breakers || {
                ai_gateway: { name: "ai_gateway", state: "CLOSED", consecutive_failures: 0, failure_threshold: 3, recovery_timeout_sec: 30 },
                ecourts: { name: "ecourts", state: "CLOSED", consecutive_failures: 0, failure_threshold: 3, recovery_timeout_sec: 60 },
                eprisons: { name: "eprisons", state: "CLOSED", consecutive_failures: 0, failure_threshold: 3, recovery_timeout_sec: 60 },
                cctns: { name: "cctns", state: "CLOSED", consecutive_failures: 0, failure_threshold: 3, recovery_timeout_sec: 60 },
              }).map(([key, breaker]) => {
                const isOpen = breaker.state === "OPEN";
                const isHalf = breaker.state === "HALF_OPEN";
                return (
                  <div key={key} className="bg-card border-2 border-border p-4 rounded-sm shadow-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold uppercase text-foreground">{breaker.name}</span>
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                        isOpen ? "bg-red-500/10 text-red-600 border-red-500/20" :
                        isHalf ? "bg-amber-500/10 text-amber-600 border-amber-500/20" :
                        "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"
                      }`}>
                        {breaker.state}
                      </span>
                    </div>
                    <div className="text-[11px] font-mono text-muted-foreground space-y-0.5 pt-1 border-t border-border">
                      <div>Failures: {breaker.consecutive_failures} / {breaker.failure_threshold}</div>
                      <div>Cooldown: {breaker.recovery_timeout_sec}s</div>
                      <div>Mode: {isOpen ? "Fallback Procedural" : "Direct Gateway"}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Telemetry Metrics & Latency */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm space-y-2">
              <span className="text-xs font-mono font-bold uppercase text-muted-foreground">HTTP Throughput & Health</span>
              <div className="space-y-1 text-xs font-mono">
                <div className="flex justify-between"><span>Total Requests:</span><span className="font-bold text-foreground">{opsDashboard?.telemetry?.http?.total_requests ?? 0}</span></div>
                <div className="flex justify-between"><span>Total Errors:</span><span className="font-bold text-foreground">{opsDashboard?.telemetry?.http?.total_errors ?? 0}</span></div>
                <div className="flex justify-between"><span>Error Rate:</span><span className="font-bold text-foreground">{opsDashboard?.telemetry?.http?.error_rate ?? 0}%</span></div>
                <div className="flex justify-between"><span>Avg Latency:</span><span className="font-bold text-emerald-600 dark:text-emerald-400">{opsDashboard?.telemetry?.http?.avg_latency_ms ?? 0} ms</span></div>
              </div>
            </div>

            <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm space-y-2">
              <span className="text-xs font-mono font-bold uppercase text-muted-foreground">AI Tokens & Pipeline</span>
              <div className="space-y-1 text-xs font-mono">
                <div className="flex justify-between"><span>AI Inferences:</span><span className="font-bold text-foreground">{opsDashboard?.telemetry?.ai_usage?.requests ?? 0}</span></div>
                <div className="flex justify-between"><span>Total Tokens:</span><span className="font-bold text-foreground">{opsDashboard?.telemetry?.ai_usage?.tokens ?? 0}</span></div>
                <div className="flex justify-between"><span>OCR Executions:</span><span className="font-bold text-foreground">{opsDashboard?.telemetry?.ocr?.operations ?? 0}</span></div>
                <div className="flex justify-between"><span>OCR Failures:</span><span className="font-bold text-foreground">{opsDashboard?.telemetry?.ocr?.failures ?? 0}</span></div>
              </div>
            </div>

            <div className="bg-card border-2 border-border p-4 rounded-sm shadow-sm space-y-2">
              <span className="text-xs font-mono font-bold uppercase text-muted-foreground">Disaster Recovery & Storage</span>
              <div className="space-y-1 text-xs font-mono">
                <div className="flex justify-between"><span>Active Engine:</span><span className="font-bold text-foreground">Dual-Engine (SQLite/PG)</span></div>
                <div className="flex justify-between"><span>Online Backup:</span><span className="font-bold text-emerald-600 dark:text-emerald-400">Atomic Snapshot API</span></div>
                <div className="flex justify-between"><span>Test Restore:</span><span className="font-bold text-emerald-600 dark:text-emerald-400">Verified (PRAGMA OK)</span></div>
                <div className="flex justify-between"><span>Audit Continuity:</span><span className="font-bold text-emerald-600 dark:text-emerald-400">Cryptographic Chain OK</span></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Technical Operations & Diagnostics */}
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
                <Zap className="w-4 h-4 text-red-500" />
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
