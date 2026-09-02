import React, { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { Activity, ShieldCheck, Lock, ArrowLeft, AlertCircle, Key } from "lucide-react";
import { motion } from "framer-motion";
import { useAuth, type Role } from "../lib/auth";

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, loginWithDemoRole, isLoading, user, logout } = useAuth();

  const [email, setEmail] = useState("dlsa@demo.nyayamitra.in");
  const [password, setPassword] = useState("Demo@12345");
  const [error, setError] = useState<string | null>(null);
  const [selectedDemoRole, setSelectedDemoRole] = useState<Role>("DLSA_OFFICER");

  const getRoleDefaultRoute = (role?: Role): string => {
    switch (role) {
      case "ACCUSED_USER":
        return "/my-case";
      case "FAMILY_GUARDIAN":
        return "/family/status";
      case "READ_ONLY_AUDITOR":
        return "/audit";
      case "PLATFORM_ADMIN":
        return "/admin";
      case "GOV_ADMIN":
        return "/gov";
      case "JAIL_OFFICER":
        return "/jail";
      case "DEFENSE_ADVOCATE":
      case "CONTROLLED_EXTERNAL_ADVOCATE":
        return "/advocate";
      case "POLICE_OFFICER":
        return "/police";
      case "DLSA_OFFICER":
      case "SUPERVISING_LEGAL_OFFICER":
      default:
        return "/dashboard";
    }
  };

  const handleManualLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const loggedInRole = await login(email, password);
      // Determine destination strictly according to authenticated role
      const fromPath = (location.state as any)?.from?.pathname;
      const target = fromPath && fromPath !== "/dashboard" && fromPath !== "/" 
        ? fromPath 
        : getRoleDefaultRoute(loggedInRole);
      navigate(target, { replace: true });
    } catch (err: any) {

      setError(err?.message || "Invalid credentials or authorization failure.");
    }
  };

  const handleDemoRoleSelect = async (role: Role) => {
    setError(null);
    setSelectedDemoRole(role);
    try {
      await loginWithDemoRole(role);
      const target = getRoleDefaultRoute(role);
      navigate(target, { replace: true });
    } catch (err: any) {
      setError(err?.message || "Demo role login failed.");
    }
  };

  const demoRoles: { role: Role; label: string; org: string }[] = [
    { role: "DLSA_OFFICER", label: "DLSA Legal Officer", org: "DLSA Central" },
    { role: "SUPERVISING_LEGAL_OFFICER", label: "Supervising Legal Officer", org: "DLSA Central" },
    { role: "DEFENSE_ADVOCATE", label: "Defense Legal-Aid Advocate", org: "Delhi Bar Panel" },
    { role: "JAIL_OFFICER", label: "Jail Superintendent / Intake", org: "Sub-Jail Central" },
    { role: "POLICE_OFFICER", label: "Station Police Officer", org: "Kotwali PS" },
    { role: "GOV_ADMIN", label: "Govt / SLSA Admin", org: "Delhi SLSA" },
    { role: "READ_ONLY_AUDITOR", label: "Statutory Oversight Auditor", org: "High Court Registry" },
    { role: "PLATFORM_ADMIN", label: "Platform Administrator", org: "Nyaya Mitra Ops" },
    { role: "ACCUSED_USER", label: "Accused Person (UTP-0001)", org: "Citizen Portal" },
    { role: "FAMILY_GUARDIAN", label: "Family Guardian", org: "Citizen Portal" },
  ];

  return (
    <div className="min-h-screen bg-background flex relative">
      {/* Top Navigation Back Button */}
      <div className="absolute top-6 left-6 z-30">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-primary-foreground bg-primary/90 border border-primary-foreground/30 px-4 py-2 rounded-sm shadow-md hover:bg-primary-foreground hover:text-primary transition-all"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Home
        </Link>
      </div>

      {/* Left side: Branding & Visuals */}
      <div className="hidden lg:flex flex-1 relative flex-col justify-between p-12 pt-24 border-r-2 border-border bg-primary text-primary-foreground overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay pointer-events-none" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white/5 blur-[100px] rounded-sm pointer-events-none" />

        <Link to="/" className="relative z-10 flex items-center gap-3 hover:opacity-90 transition-opacity w-fit cursor-pointer">
          <div className="w-8 h-8 rounded-sm bg-primary-foreground/10 border border-primary-foreground/30 flex items-center justify-center">
            <Activity className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-bold font-serif text-2xl tracking-tight text-primary-foreground uppercase">
            Nyaya Mitra
          </span>
        </Link>

        <div className="relative z-10 max-w-md space-y-4">
          <h2 className="text-3xl font-serif font-black tracking-tight text-primary-foreground leading-tight">
            Institutional Operations & Access Control Gateway
          </h2>
          <p className="text-primary-foreground/80 font-sans text-sm leading-relaxed">
            Strict RBAC & ABAC perimeter guarding Undertrial Prisoner dossiers, Section 479 eligibility assessments,
            evidentiary hashes, and formal court petitions.
          </p>
        </div>

        <div className="relative z-10 text-xs font-mono font-semibold text-primary-foreground/70 uppercase tracking-widest border-t border-primary-foreground/20 pt-4">
          SEC_PERIMETER: ENFORCED // STAGE_03: ACTIVE
        </div>
      </div>

      {/* Right side: Login Form & Role Switcher */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 relative bg-background overflow-y-auto max-h-screen">
        <div className="film-grain" />

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md space-y-6 relative z-10 my-auto py-8"
        >
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
              Secure Officer Access
            </h1>
            <p className="text-xs font-sans font-medium text-muted-foreground">
              Sign in with institutional credentials or select an authorized demo identity.
            </p>
          </div>

          {error && (
            <div className="bg-destructive/10 border border-destructive/30 p-3 rounded-sm flex items-start gap-2 text-destructive text-xs font-mono">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {user && (
            <div className="bg-muted/50 border border-border p-3 rounded-sm flex items-center justify-between text-xs font-mono">
              <div>
                <span className="text-muted-foreground">Signed in as: </span>
                <span className="font-bold text-foreground">[{user.role}]</span>
              </div>
              <button
                onClick={() => logout()}
                className="text-destructive font-bold hover:underline uppercase text-[11px]"
              >
                Sign Out
              </button>
            </div>
          )}

          <form onSubmit={handleManualLogin} className="space-y-4 bg-card border-2 border-border p-6 rounded-sm shadow-md">
            <div className="space-y-1.5">
              <label className="text-xs font-mono font-bold text-foreground uppercase tracking-wider block">
                Officer Email / Identity
              </label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-input border-2 border-border text-foreground font-mono text-xs px-3.5 py-2.5 rounded-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary font-medium"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono font-bold text-foreground uppercase tracking-wider block">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full bg-input border-2 border-border text-foreground font-mono text-xs px-3.5 py-2.5 rounded-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary font-medium"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary text-primary-foreground font-mono font-bold text-xs uppercase tracking-wider rounded-sm py-3 mt-2 hover:bg-accent hover:text-accent-foreground transition-all flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                <Lock className="w-3.5 h-3.5" />
              )}
              Authenticate Session
            </button>
          </form>

          {/* Quick Demo Identities Selector */}
          <div className="bg-card border-2 border-border/80 p-4 rounded-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-mono font-bold uppercase tracking-wider text-foreground">
                <Key className="w-3.5 h-3.5 text-primary" />
                <span>Demo Identities (Stage 03)</span>
              </div>
              <span className="text-[10px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded font-bold">
                DEMO_MODE
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
              {demoRoles.map(({ role, label, org }) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => handleDemoRoleSelect(role)}
                  disabled={isLoading}
                  className={`text-left p-2 rounded-sm border text-[11px] font-mono transition-all ${
                    selectedDemoRole === role
                      ? "border-primary bg-primary/10 text-foreground font-bold shadow-xs"
                      : "border-border/60 bg-muted/20 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                  }`}
                >
                  <div className="truncate font-semibold">{label}</div>
                  <div className="text-[9px] text-muted-foreground truncate">{org}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col items-center gap-2 text-xs text-foreground font-mono font-bold uppercase tracking-wider pt-2 border-t border-border">
            <div className="flex items-center gap-2 text-muted-foreground">
              <ShieldCheck className="w-3.5 h-3.5 text-foreground" />
              SERVER-SIDE RBAC & ABAC ENFORCED
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
