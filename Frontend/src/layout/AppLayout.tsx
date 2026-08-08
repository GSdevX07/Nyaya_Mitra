import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { Search, Bell, User, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { CommandPalette } from "@/components/CommandPalette";

const navItems = [
  { path: "/", label: "Home" },
  { path: "/dashboard", label: "Command Center" },
  { path: "/how-it-works", label: "How It Works" },
  { path: "/features", label: "Features" },
  { path: "/cases", label: "Cases" },
  { path: "/radar", label: "Eligibility Radar" },
  { path: "/documents", label: "Documents" },
  { path: "/evidence", label: "Evidence" },
  { path: "/actions", label: "Actions" },
  { path: "/hearings", label: "Hearings" },
  { path: "/reports", label: "Reports" },
];

export function AppLayout() {
  const location = useLocation();
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-accent selection:text-accent-foreground relative overflow-hidden">
      {/* Subtle background grain/noise texture overlay */}
      <div className="pointer-events-none fixed inset-0 z-50 opacity-[0.03] mix-blend-overlay bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
      
      {/* Global Top Navigation */}
      <header className="sticky top-0 z-40 w-full border-b border-white/5 bg-background/80 backdrop-blur-md">
        <div className="flex h-16 items-center px-6">
          <Link to="/" className="flex items-center gap-2 mr-8 group hover:opacity-90 transition-opacity">
            <div className="relative flex items-center justify-center w-8 h-8">
              <div className="absolute inset-0 bg-accent/20 rounded-full animate-ping opacity-75" />
              <Activity className="w-5 h-5 text-accent relative z-10" />
            </div>
            <span className="font-semibold text-lg tracking-tight text-white uppercase group-hover:text-accent transition-colors">Nyaya Mitra</span>
          </Link>
          
          <nav className="flex items-center gap-1 flex-1 overflow-x-auto no-scrollbar">
            {navItems.map((item) => {
              const isActive = location.pathname.startsWith(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative px-4 py-2 text-sm transition-colors rounded-md hover:bg-white/5 ${
                    isActive ? "text-white font-medium" : "text-muted-foreground"
                  }`}
                >
                  {item.label}
                  {isActive && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent rounded-t-full"
                      initial={false}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    />
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-4 ml-auto pl-4">
            <button className="text-muted-foreground hover:text-white transition-colors">
              <Search className="w-5 h-5" />
            </button>
            <button className="text-muted-foreground hover:text-white transition-colors relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-0 right-0 w-2 h-2 bg-destructive rounded-full" />
            </button>
            <div className="w-px h-5 bg-border mx-2" />
            <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors">
              <div className="w-7 h-7 rounded-full bg-secondary border border-border flex items-center justify-center">
                <User className="w-4 h-4" />
              </div>
              <span className="hidden md:inline">Officer 104</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto relative z-10">
        <Outlet />
      </main>

      {/* Global AI Intelligence Floating Circular Icon / Expanded Panel (Bottom Right) */}
      <div className="fixed bottom-6 right-6 z-40">
        <motion.div
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className="bg-background/90 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/50 overflow-hidden cursor-pointer flex flex-col"
          initial={false}
          animate={{
            width: isHovered ? 320 : 48,
            height: isHovered ? 160 : 48,
            borderRadius: isHovered ? 16 : 9999,
          }}
          transition={{ type: "spring", stiffness: 350, damping: 25 }}
        >
          <AnimatePresence mode="wait">
            {!isHovered ? (
              <motion.div
                key="collapsed"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="w-12 h-12 flex items-center justify-center relative"
              >
                <Activity className="w-5 h-5 text-accent animate-pulse" />
                <span className="absolute top-2 right-2 w-2 h-2 bg-accent rounded-full animate-ping opacity-75" />
              </motion.div>
            ) : (
              <motion.div
                key="expanded"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="p-4 w-80"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Activity className="w-4 h-4 text-accent animate-pulse" />
                  <span className="text-xs font-semibold text-accent uppercase tracking-wider">Nyaya Intelligence</span>
                </div>
                <ul className="space-y-2 text-xs text-muted-foreground">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-white/20 animate-pulse" />
                    Analyzing case #TN-2026-00482
                  </li>
                  <li className="flex items-center gap-2 text-emerald-500/80">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/50" />
                    Retrieved BNSS Section 479
                  </li>
                  <li className="flex items-center gap-2 text-amber-500/80">
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-500/50" />
                    Missing document detected
                  </li>
                </ul>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
      <CommandPalette />
    </div>
  );
}
