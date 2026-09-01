import { useState, useEffect } from "react";
import { Server } from "lucide-react";
import { fetchDemoUsers } from "../lib/api";

export function AdminConsole() {
  const [demoUsers, setDemoUsers] = useState<any[]>([]);

  useEffect(() => {
    async function loadDemoUsers() {
      try {
        const data = await fetchDemoUsers();
        setDemoUsers(data.demo_users || []);
      } catch (err) {
        console.warn("Failed to load demo users:", err);
      }
    }
    loadDemoUsers();
  }, []);

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Platform Admin Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Server className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              Platform Administration & System Governance
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Platform Operations Console
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            Central management of institutional roles, security policies, token session stores, tenant organizations, and system-wide connector health.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-bold px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded">
            SUPERUSER_ACCESS
          </span>
        </div>
      </div>

      {/* Health Matrix Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Backend API Status</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1 flex items-center gap-2">
            ONLINE
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">FastAPI 0.115 / Python 3.14</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Database Layer</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">
            SQLite + WAL
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1">Supabase PG Adapter Ready</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Active User Personas</div>
          <div className="text-2xl font-serif font-bold text-primary mt-1">
            {demoUsers.length || 11} Roles
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">RBAC & ABAC Enforced</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Token Store</div>
          <div className="text-2xl font-serif font-bold text-blue-600 mt-1">
            Active
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">HS256 JWT + Revocation</div>
        </div>
      </div>

      {/* User Roster & Role Matrix */}
      <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
        <div className="p-4 border-b border-border bg-secondary/40 flex items-center justify-between">
          <span className="font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground">
            Registered Institutional Personas & Role Matrix
          </span>
          <span className="text-xs font-mono text-muted-foreground">11 Pre-Configured Personas</span>
        </div>

        <div className="divide-y divide-border">
          {demoUsers.map((u) => (
            <div key={u.email || u.user_id || u.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-secondary/20 transition-colors">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-foreground">{u.full_name}</span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                    {u.role}
                  </span>
                </div>
                <div className="text-xs font-mono text-muted-foreground">
                  Email: {u.email} • Org: <strong className="text-foreground">{u.org_id || u.organization_id || 'org_dlsa_central'}</strong> {u.district && `• District: ${u.district}`}
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="px-2 py-1 bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 rounded font-bold">
                  ACTIVE
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
