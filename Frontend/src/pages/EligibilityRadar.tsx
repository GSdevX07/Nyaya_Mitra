import { motion } from "framer-motion";
import { Search, Filter, AlertCircle, Clock, FileText, ArrowLeft } from "lucide-react";
import { MOCK_CASES } from "@/data/mock";
import { Link } from "react-router-dom";

export function EligibilityRadar() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-10">
      
      {/* Header */}
      <div className="space-y-6">
        <Link to="/dashboard" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Command Center
        </Link>
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-4xl font-semibold tracking-tight text-white uppercase">Eligibility Radar</h1>
            <p className="text-xl text-muted-foreground">Proactive monitoring for upcoming statutory thresholds.</p>
          </div>
          
          <div className="flex gap-2">
            {["Today", "7 days", "30 days", "90 days"].map((filter, i) => (
              <button key={filter} className={`px-4 py-2 text-sm font-medium rounded border ${i === 2 ? "bg-white/10 text-white border-white/20" : "bg-transparent text-muted-foreground border-white/5 hover:bg-white/5"} transition-colors`}>
                {filter}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02]">
          <div className="text-3xl font-light text-white mb-2">NEXT 30 DAYS</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Active Monitoring Window</div>
        </div>
        <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02]">
          <div className="text-3xl font-light text-accent mb-2">12</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Approaching Threshold</div>
        </div>
        <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02]">
          <div className="text-3xl font-light text-amber-500 mb-2">34</div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Requiring Documentation</div>
        </div>
        <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02]">
          <div className="text-3xl font-light text-destructive mb-2">7</div>
          <div className="text-xs text-destructive/80 uppercase tracking-wider">Overdue Actions</div>
        </div>
      </div>

      {/* Radar Timeline (Mocked visually) */}
      <div className="p-8 rounded-xl border border-white/5 bg-black/20 space-y-8 relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03] mix-blend-overlay pointer-events-none" />
        
        <div className="flex items-center gap-4 border-b border-white/10 pb-4">
          <div className="flex items-center gap-2 text-white font-medium">
            <Clock className="w-4 h-4 text-accent" /> Timeline View
          </div>
          <div className="w-px h-4 bg-white/10" />
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input type="text" placeholder="Search cases..." className="w-full bg-white/5 border border-white/10 rounded pl-9 pr-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent" />
          </div>
          <button className="ml-auto flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors">
            <Filter className="w-4 h-4" /> Filters
          </button>
        </div>

        <div className="space-y-12">
          {/* Week 1 */}
          <div className="relative">
            <div className="absolute -left-4 top-0 bottom-0 w-px bg-white/10" />
            <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-accent ring-4 ring-black" />
            
            <h3 className="text-lg font-medium text-white mb-6 uppercase tracking-wider">This Week</h3>
            
            <div className="space-y-4 pl-4">
              {MOCK_CASES.filter(c => c.urgency === "URGENT").map(c => (
                <div key={c.id} className="p-5 rounded-lg border border-destructive/20 bg-destructive/5 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-white font-medium">{c.id}</span>
                      <span className="px-2 py-0.5 bg-destructive/20 text-destructive text-[10px] font-bold uppercase tracking-wider rounded border border-destructive/30">Overdue by 47 days</span>
                    </div>
                    <div className="text-sm text-muted-foreground">{c.prisonerName} • {c.offence}</div>
                  </div>
                  <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm font-medium rounded transition-colors">
                    Review
                  </button>
                </div>
              ))}
              {MOCK_CASES.filter(c => c.urgency === "MEDIUM").map(c => (
                <div key={c.id} className="p-5 rounded-lg border border-white/5 bg-white/5 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-white font-medium">{c.id}</span>
                      <span className="px-2 py-0.5 bg-amber-500/20 text-amber-500 text-[10px] font-bold uppercase tracking-wider rounded border border-amber-500/30">Docs Required</span>
                    </div>
                    <div className="text-sm text-muted-foreground">{c.prisonerName} • Threshold in 15 days</div>
                  </div>
                  <button className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white text-sm font-medium rounded transition-colors">
                    View Case
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Week 2 */}
          <div className="relative opacity-60">
            <div className="absolute -left-4 top-0 bottom-0 w-px bg-white/10" />
            <div className="absolute -left-[19px] top-1 w-2 h-2 rounded-full bg-white/20 ring-4 ring-black" />
            
            <h3 className="text-lg font-medium text-white mb-6 uppercase tracking-wider">Next Week</h3>
            
            <div className="space-y-4 pl-4">
              <div className="p-5 rounded-lg border border-white/5 bg-white/5 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-white font-medium">CASE-2026-004</span>
                  </div>
                  <div className="text-sm text-muted-foreground">Approaching threshold on Aug 18, 2026</div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
