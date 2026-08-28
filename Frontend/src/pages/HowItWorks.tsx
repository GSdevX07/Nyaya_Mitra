import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowLeft, FileCheck, Eye, Scale, Shield, Activity, Users, ArrowRight } from "lucide-react";

const pipelineSteps = [
  {
    step: "01",
    label: "CASE RECORDS INTAKE",
    icon: FileCheck,
    title: "Digitization & Ingestion",
    desc: "Ingests scanned prison registers, FIR copies, remand notes, and custody logs. Normalizes raw unstructured records into canonical JSON schemas with data source provenance.",
    badge: "Input Layer"
  },
  {
    step: "02",
    label: "DOC INTELLIGENCE",
    icon: Eye,
    title: "OCR & Key Fact Extraction",
    desc: "Extracts critical judicial metadata: arrest dates, sections charged, statutory terms, and prior bail orders using domain-specific vision-language models.",
    badge: "Extraction Engine"
  },
  {
    step: "03",
    label: "SECTION 479 RULE ENGINE",
    icon: Scale,
    title: "Versioned Statutory Math",
    desc: "Applies versioned deterministic Section 479 BNSS legal rules (evaluating 1/3 first-time proviso, 1/2 general threshold, countable vs excluded delay, capital offence and multiple proceedings exceptions) to produce an eligibility signal for human legal review.",
    badge: "Deterministic Rules"
  },
  {
    step: "04",
    label: "GROUNDED STATUTORY RAG",
    icon: Shield,
    title: "Statutory Law & Citations",
    desc: "Grounds analysis in verified criminal enactments (BNSS 2023, BNS 2023, IPC 1860) with exact statutory titles, section numbers, and effective-date context.",
    badge: "Statutory Retrieval"
  },
  {
    step: "05",
    label: "PETITION DRAFTING",
    icon: Activity,
    title: "Formal Petition Preparation",
    desc: "Drafts formal Section 479 bail applications formatted to Indian court standards, highlighting missing records, countable detention facts, and legal justification.",
    badge: "AI Agent"
  },
  {
    step: "06",
    label: "MANDATORY ADVOCATE GATEWAY",
    icon: Users,
    title: "Human Legal Sign-Off",
    desc: "Every AI petition requires explicit review, editing, and sign-off by a licensed panel advocate before procedural court filing. The system never executes autonomous court filings.",
    badge: "Human-in-the-Loop"
  }
];

export function HowItWorks() {
  return (
    <div className="min-h-screen bg-background text-foreground font-sans relative overflow-hidden p-6 md:p-12">
      {/* Background Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-accent/10 blur-[150px] rounded-sm pointer-events-none" />

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
            NYAYA MITRA // PIPELINE ARCHITECTURE
          </div>
        </div>

        {/* Hero Banner */}
        <div className="text-center space-y-4 max-w-3xl mx-auto pt-6">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-sm border border-accent/20 bg-accent/10 text-accent text-xs font-semibold tracking-widest uppercase">
            <Activity className="w-4 h-4 animate-pulse" /> End-to-End Operational Pipeline
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-primary">
            How Nyaya Mitra Works
          </h1>
          <p className="text-lg text-muted-foreground leading-relaxed">
            A transparent, multi-agent AI pipeline designed to ensure no undertrial prisoner is forgotten behind paperwork.
          </p>
        </div>

        {/* Grid of Steps */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 pt-6">
          {pipelineSteps.map((step, i) => (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="p-8 rounded border border-border bg-card shadow-sm hover:bg-card/80 hover:border-accent/40 transition-all group relative flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <div className="w-12 h-12 rounded bg-accent/10 border border-accent/20 flex items-center justify-center text-accent group-hover:bg-accent/20 transition-colors">
                    <step.icon className="w-6 h-6" />
                  </div>
                  <span className="text-2xl font-mono font-bold text-white/20 group-hover:text-accent transition-colors">
                    {step.step}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-accent uppercase tracking-widest bg-accent/10 border border-accent/20 px-2 py-0.5 rounded">
                    {step.badge}
                  </span>
                  <h3 className="text-xl font-bold text-primary mt-3 mb-2">{step.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom Call to Action */}
        <div className="p-8 rounded border border-border bg-gradient-to-r from-accent/10 via-white/[0.02] to-transparent text-center space-y-6">
          <h2 className="text-2xl font-bold text-primary">Ready to explore the live dashboard?</h2>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="px-8 py-3.5 bg-card text-black font-semibold rounded hover:bg-card transition-all inline-flex items-center gap-2 text-sm shadow-lg shadow-primary/3"
            >
              Open Command Center <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/"
              className="px-8 py-3.5 bg-secondary/50 border border-border text-primary font-medium rounded hover:bg-secondary transition-all text-sm"
            >
              Return to Landing Page
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
