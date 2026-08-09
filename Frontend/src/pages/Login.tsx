import { Link, useNavigate } from "react-router-dom";
import { Activity, ShieldCheck, Lock, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";

export function Login() {
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    navigate("/dashboard");
  };

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

      {/* Left side: Branding & Visuals (Dark Charcoal Panel) */}
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
            AI that finds the cases the system forgot.
          </h2>
          <p className="text-primary-foreground/80 font-sans text-sm leading-relaxed">
            An intelligent legal operations layer for undertrial case workflows and statutory eligibility verification.
          </p>
        </div>

        <div className="relative z-10 text-xs font-mono font-semibold text-primary-foreground/70 uppercase tracking-widest border-t border-primary-foreground/20 pt-4">
          SYS_STATE: ONLINE // ENV: PROD
        </div>
      </div>

      {/* Right side: Login Form (Newsprint Paper Panel) */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 relative bg-background">
        <div className="film-grain" />
        
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md space-y-6 relative z-10"
        >
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-serif font-black tracking-tight text-foreground">
              Authorized personnel only
            </h1>
            <p className="text-sm font-sans font-medium text-muted-foreground">
              Sign in with your Officer ID to access the Command Center.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5 bg-card border-2 border-border p-8 rounded-sm shadow-md">
            <div className="space-y-2">
              <label className="text-xs font-mono font-bold text-foreground uppercase tracking-wider block">
                Officer ID / Email
              </label>
              <input 
                type="text" 
                defaultValue="officer_104@nyayamitra.gov.in"
                className="w-full bg-input border-2 border-border text-foreground font-mono text-sm px-4 py-3 rounded-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors font-medium shadow-inner"
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-mono font-bold text-foreground uppercase tracking-wider block">
                  Password
                </label>
              </div>
              <input 
                type="password" 
                defaultValue="••••••••••••"
                className="w-full bg-input border-2 border-border text-foreground font-mono text-sm px-4 py-3 rounded-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors font-medium shadow-inner"
              />
            </div>

            <button 
              type="submit" 
              className="w-full bg-primary text-primary-foreground font-mono font-bold text-xs uppercase tracking-wider rounded-sm py-3.5 mt-6 hover:bg-accent hover:text-accent-foreground transition-all flex items-center justify-center gap-2 shadow-sm"
            >
              <Lock className="w-4 h-4" /> Sign In securely
            </button>
          </form>

          <div className="flex flex-col items-center gap-2.5 text-xs text-foreground font-mono font-bold uppercase tracking-wider pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" /> 
              SYSTEM ONLINE
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <ShieldCheck className="w-3.5 h-3.5 text-foreground" /> 
              EVIDENCE TRACEABILITY ENABLED
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Lock className="w-3.5 h-3.5 text-foreground" /> 
              HUMAN REVIEW REQUIRED
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
