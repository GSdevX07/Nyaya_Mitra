import { Link, useNavigate } from "react-router-dom";
import { Activity, ShieldCheck, Lock } from "lucide-react";
import { motion } from "framer-motion";

export function Login() {
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    navigate("/dashboard");
  };

  return (
    <div className="min-h-screen bg-[#0a0a0b] flex">
      {/* Left side: Branding & Visuals */}
      <div className="hidden lg:flex flex-1 relative flex-col justify-between p-12 border-r border-white/5 bg-black/40 overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay pointer-events-none" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent/10 blur-[100px] rounded-full pointer-events-none" />
        
        <div className="relative z-10 flex items-center gap-3">
          <Activity className="w-6 h-6 text-accent" />
          <span className="font-bold text-2xl tracking-tight text-white uppercase">Nyaya Mitra</span>
        </div>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-light text-white mb-4">AI that finds the cases the system forgot.</h2>
          <p className="text-muted-foreground leading-relaxed">
            An intelligent legal operations layer for undertrial case workflows.
          </p>
        </div>

        <div className="relative z-10 text-xs font-mono text-white/30 uppercase tracking-widest">
          SYS_STATE: ONLINE // ENV: PROD
        </div>
      </div>

      {/* Right side: Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 relative">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] mix-blend-overlay pointer-events-none" />
        
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md space-y-8 relative z-10"
        >
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-semibold tracking-tight text-white">Authorized personnel only</h1>
            <p className="text-sm text-muted-foreground">Sign in with your Officer ID to access the Command Center.</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4 bg-white/[0.02] border border-white/5 p-8 rounded-xl backdrop-blur-sm">
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Officer ID / Email</label>
              <input 
                type="text" 
                defaultValue="officer_104@nyayamitra.gov.in"
                className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-accent transition-colors"
              />
            </div>
            
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Password</label>
              </div>
              <input 
                type="password" 
                defaultValue="••••••••••••"
                className="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-accent transition-colors"
              />
            </div>

            <button type="submit" className="w-full bg-white text-black font-semibold rounded-lg py-3 mt-4 hover:bg-white/90 transition-colors flex items-center justify-center gap-2">
              <Lock className="w-4 h-4" /> Sign In securely
            </button>
          </form>

          <div className="flex flex-col items-center gap-3 text-xs text-muted-foreground font-medium uppercase tracking-widest pt-8">
            <div className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> SYSTEM ONLINE</div>
            <div className="flex items-center gap-2"><ShieldCheck className="w-3 h-3 text-accent" /> EVIDENCE TRACEABILITY ENABLED</div>
            <div className="flex items-center gap-2"><Lock className="w-3 h-3 text-amber-500" /> HUMAN REVIEW REQUIRED</div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
