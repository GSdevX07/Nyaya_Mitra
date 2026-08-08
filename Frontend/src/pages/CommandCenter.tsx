import { motion } from "framer-motion";
import { MOCK_CASES, DASHBOARD_METRICS } from "@/data/mock";
import { ArrowRight, AlertCircle, FileText, CheckCircle2, AlertTriangle, Scale, Clock, Activity } from "lucide-react";
import { Link } from "react-router-dom";

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export function CommandCenter() {
  const urgentCase = MOCK_CASES.find(c => c.urgency === "URGENT") || MOCK_CASES[0];

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <motion.div initial="hidden" animate="show" variants={container} className="space-y-10">
        
        {/* Header */}
        <motion.div variants={item} className="space-y-2">
          <h1 className="text-4xl font-semibold tracking-tight text-white">Good morning, Officer.</h1>
          <p className="text-xl text-muted-foreground">Here is what requires attention today.</p>
        </motion.div>

        {/* Primary Metrics */}
        <motion.div variants={item} className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: "Cases monitored", value: DASHBOARD_METRICS.monitored, color: "text-white" },
            { label: "Potentially eligible", value: DASHBOARD_METRICS.potentiallyEligible, color: "text-accent" },
            { label: "Missing documents", value: DASHBOARD_METRICS.missingDocuments, color: "text-amber-500" },
            { label: "Awaiting legal review", value: DASHBOARD_METRICS.awaitingReview, color: "text-white" },
            { label: "Urgent actions", value: DASHBOARD_METRICS.urgentActions, color: "text-destructive" },
          ].map((metric, i) => (
            <div key={i} className="p-5 rounded-xl border border-white/5 bg-white/[0.02] backdrop-blur-sm relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className={`text-4xl font-light tracking-tight mb-2 ${metric.color}`}>
                {metric.value.toLocaleString()}
              </div>
              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {metric.label}
              </div>
            </div>
          ))}
        </motion.div>

        {/* Layout Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Case Flow / Priority Queue */}
          <motion.div variants={item} className="lg:col-span-2 space-y-8">
            
            {/* Action Required */}
            <section className="space-y-4">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="w-5 h-5" />
                <h2 className="text-lg font-medium tracking-tight uppercase">Action Required</h2>
              </div>
              
              <Link to={`/case/${urgentCase.id}`} className="block">
                <div className="p-6 rounded-xl border border-destructive/20 bg-destructive/5 hover:bg-destructive/10 transition-colors relative overflow-hidden group cursor-pointer">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-destructive" />
                  
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="text-xl font-medium text-white">CASE #{urgentCase.id}</h3>
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-destructive/20 text-destructive border border-destructive/30">
                          {urgentCase.urgency}
                        </span>
                      </div>
                      <p className="text-muted-foreground">{urgentCase.prisonerName} • Potential Section 479 eligibility</p>
                    </div>
                    <div className="text-right">
                      <div className="text-destructive font-bold text-lg">47 DAYS</div>
                      <div className="text-xs text-destructive/80 uppercase tracking-wider font-medium">Over Threshold</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm mt-6 pt-4 border-t border-white/5">
                    <div>
                      <span className="text-muted-foreground block mb-1 text-xs uppercase tracking-wider">Missing Records</span>
                      <ul className="space-y-1">
                        {urgentCase.documents.filter(d => d.status === "missing").map(d => (
                          <li key={d.id} className="flex items-center gap-2 text-amber-500/90">
                            <AlertTriangle className="w-3.5 h-3.5" /> {d.name}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="flex justify-end items-end">
                      <div className="flex items-center gap-2 text-white font-medium group-hover:text-accent transition-colors">
                        Review Case <ArrowRight className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </div>
              </Link>
            </section>

            {/* Case Flow Simple Visualization */}
            <section className="space-y-4">
               <h2 className="text-lg font-medium tracking-tight uppercase text-muted-foreground">Case Flow</h2>
               <div className="p-8 rounded-xl border border-white/5 bg-white/[0.02] overflow-x-auto">
                 <div className="flex items-center justify-between min-w-[600px]">
                   {["DISCOVERED", "VERIFIED", "DOCUMENTS", "ELIGIBILITY", "REVIEW", "FILED"].map((stage, i, arr) => (
                     <div key={stage} className="flex items-center">
                       <div className="flex flex-col items-center gap-3">
                         <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${i === 3 ? "border-accent bg-accent/10 text-accent" : i < 3 ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-500" : "border-white/10 bg-white/5 text-muted-foreground"}`}>
                           {i < 3 ? <CheckCircle2 className="w-5 h-5" /> : i === 3 ? <Activity className="w-5 h-5 animate-pulse" /> : <Clock className="w-5 h-5" />}
                         </div>
                         <span className={`text-xs font-medium tracking-wider ${i === 3 ? "text-accent" : "text-muted-foreground"}`}>{stage}</span>
                       </div>
                       {i < arr.length - 1 && (
                         <div className={`w-16 h-px mx-2 ${i < 3 ? "bg-emerald-500/30" : "bg-white/10"}`} />
                       )}
                     </div>
                   ))}
                 </div>
               </div>
            </section>

          </motion.div>

          {/* Sidebar Metrics */}
          <motion.div variants={item} className="space-y-8">
            
            {/* Case Readiness */}
            <section className="space-y-4">
              <h2 className="text-lg font-medium tracking-tight uppercase text-muted-foreground">Case Readiness</h2>
              <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02] flex flex-col items-center justify-center relative">
                {/* Radial Chart Placeholder */}
                <div className="relative w-48 h-48 flex items-center justify-center mb-6">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="45" className="stroke-white/10" strokeWidth="4" fill="none" />
                    <circle cx="50" cy="50" r="45" className="stroke-accent" strokeWidth="4" fill="none" strokeDasharray="283" strokeDashoffset={283 * (1 - 0.82)} strokeLinecap="round" />
                    
                    <circle cx="50" cy="50" r="35" className="stroke-white/10" strokeWidth="4" fill="none" />
                    <circle cx="50" cy="50" r="35" className="stroke-emerald-500" strokeWidth="4" fill="none" strokeDasharray="220" strokeDashoffset={220 * (1 - 0.72)} strokeLinecap="round" />
                    
                    <circle cx="50" cy="50" r="25" className="stroke-white/10" strokeWidth="4" fill="none" />
                    <circle cx="50" cy="50" r="25" className="stroke-blue-500" strokeWidth="4" fill="none" strokeDasharray="157" strokeDashoffset={157 * (1 - 0.94)} strokeLinecap="round" />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl font-light text-white">82%</span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-widest">Ready</span>
                  </div>
                </div>

                <div className="w-full space-y-3 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground flex items-center gap-2"><Scale className="w-4 h-4 text-accent" /> Eligibility</span>
                    <span className="text-white font-medium">100%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground flex items-center gap-2"><FileText className="w-4 h-4 text-emerald-500" /> Documentation</span>
                    <span className="text-white font-medium">72%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-blue-500" /> Evidence</span>
                    <span className="text-white font-medium">94%</span>
                  </div>
                  <div className="flex justify-between items-center pt-3 border-t border-white/5">
                    <span className="text-muted-foreground">Legal Review</span>
                    <span className="text-amber-500 font-medium">Pending</span>
                  </div>
                </div>

                <div className="mt-6 w-full text-center py-2 bg-accent/10 text-accent text-xs font-semibold tracking-widest uppercase rounded">
                  Nearly Ready For Human Review
                </div>
              </div>
            </section>

          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}
