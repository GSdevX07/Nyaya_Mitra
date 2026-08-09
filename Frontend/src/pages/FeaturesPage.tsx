import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowLeft, BrainCircuit, Shield, Users, Scale, FileText, Languages, ArrowRight } from "lucide-react";

const featuresList = [
  {
    icon: BrainCircuit,
    title: "Proactive Case Discovery",
    desc: "AI agents continuously monitor custody durations against legal thresholds, flagging cases before they fall through administrative cracks.",
    highlight: "Zero Manual Overlooks"
  },
  {
    icon: Shield,
    title: "Evidence-Grounded Analysis (RAG)",
    desc: "Every conclusion is traceable to exact source documents, Indian legal sections (e.g. BNSS 479), and precedent summaries never hallucinated.",
    highlight: "Strict Citation Grounding"
  },
  {
    icon: Scale,
    title: "Deterministic Rule Engine",
    desc: "Legal threshold calculations are governed by pure Python mathematical logic. The LLM explains and drafts, but never decides custody eligibility.",
    highlight: "Ethical & Audit-Proof"
  },
  {
    icon: Users,
    title: "Human-In-The-Loop Approval Gate",
    desc: "No legal application is ever filed automatically. Legal officers review, edit, and sign off on all generated bail drafts before submission.",
    highlight: "Lawyer Control"
  },
  {
    icon: Languages,
    title: "Multilingual Beneficiary Communication",
    desc: "Translates legal jargon into plain language explanations in Indian regional languages (Hindi, Kannada, etc.) for undertrial families.",
    highlight: "Inclusive Legal Aid"
  },
  {
    icon: FileText,
    title: "Automated Records Audit",
    desc: "Diffs required case documentation against present files, automatically alerting registry officers to missing remand orders or hearing records.",
    highlight: "Automated Audit"
  }
];

export function FeaturesPage() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans relative overflow-hidden p-6 md:p-12">
      {/* Background Ambients */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-muted blur-[150px] rounded-sm pointer-events-none" />

      <div className="w-full space-y-12 relative z-10">
        
        {/* Navigation Bar */}
        <div className="flex items-center justify-between border-b border-border pb-6">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors bg-secondary/50 border border-border px-4 py-2 rounded-sm"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Home
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 text-sm text-accent hover:text-accent/80 transition-colors bg-accent/10 border border-accent/20 px-4 py-2 rounded-sm font-medium"
            >
              Command Center
            </Link>
          </div>
          <div className="text-xs text-muted-foreground font-mono uppercase tracking-widest hidden sm:block">
            NYAYA MITRA // PLATFORM FEATURES
          </div>
        </div>

        {/* Hero Header */}
        <div className="text-center space-y-4 max-w-3xl mx-auto pt-6">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-sm border border-border bg-muted text-foreground text-xs font-semibold tracking-widest uppercase">
            <Shield className="w-4 h-4" /> Trust & Transparency Architecture
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-primary">
            Platform Capabilities
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            Built from the ground up for judicial accuracy, ethical AI governance, and officer efficiency.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 pt-6">
          {featuresList.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="p-8 rounded border border-border bg-card shadow-sm hover:bg-card hover:border-emerald-500/40 transition-all group flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="w-12 h-12 rounded bg-accent/10 border border-accent/20 flex items-center justify-center text-accent group-hover:bg-accent/20 group-hover:text-foreground transition-colors">
                    <f.icon className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-bold text-foreground uppercase tracking-widest bg-muted border border-border px-2 py-0.5 rounded">
                    {f.highlight}
                  </span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-primary mb-2">{f.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom Call to Action */}
        <div className="p-8 rounded border border-border bg-gradient-to-r from-emerald-500/10 via-white/[0.02] to-transparent text-center space-y-6">
          <h2 className="text-2xl font-bold text-primary">Experience the platform in action</h2>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="px-8 py-3.5 bg-card text-black font-semibold rounded hover:bg-card transition-all inline-flex items-center gap-2 text-sm shadow-lg shadow-primary/3"
            >
              Go to Command Center <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/how-it-works"
              className="px-8 py-3.5 bg-secondary/50 border border-border text-primary font-medium rounded hover:bg-secondary transition-all text-sm"
            >
              Explore How It Works
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
