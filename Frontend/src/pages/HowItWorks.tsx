import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowLeft, FileCheck, Eye, Scale, Shield, Activity, Users, ArrowRight } from "lucide-react";

const pipelineSteps = [
  {
    step: "01",
    label: "CASE RECORDS INTAKE",
    icon: FileCheck,
    title: "Digitization & Ingestion",
    desc: "Ingests scanned prison registers, FIR copies, remand notes, and custody logs. Normalizes raw unstructured data into machine-readable JSON schemas.",
    badge: "Input Layer"
  },
  {
    step: "02",
    label: "DOC INTELLIGENCE",
    icon: Eye,
    title: "OCR & Key Fact Extraction",
    desc: "Extracts critical judicial metadata: arrest dates, sections charged, sentence lengths, and prior bail orders using domain-specific vision-language models.",
    badge: "Extraction Engine"
  },
  {
    step: "03",
    label: "ELIGIBILITY RADAR",
    icon: Scale,
    title: "Statutory Threshold Math",
    desc: "Applies deterministic, zero-hallucination legal rules (e.g. BNSS Section 479 / IPC half-sentence custody thresholds) to compute exact days overdue.",
    badge: "Deterministic Math"
  },
  {
    step: "04",
    label: "EVIDENCE CHAIN",
    icon: Shield,
    title: "Statute RAG & Grounding",
    desc: "Queries ChromaDB vector stores for relevant Indian Penal Code provisions and judicial precedents, attaching strict citations to every claim.",
    badge: "Vector Retrieval"
  },
  {
    step: "05",
    label: "AUTOMATED DRAFTING",
    icon: Activity,
    title: "Bail Petition Generation",
    desc: "Drafts formal bail applications formatted to Indian court standards, highlighting missing records and exact legal justification.",
    badge: "LLM Agent"
  },
  {
    step: "06",
    label: "HUMAN REVIEW GATE",
    icon: Users,
    title: "Legal Officer Approval",
    desc: "Every AI output requires explicit human review and e-signature before filing. The system never submits applications autonomously.",
    badge: "Human-in-the-Loop"
  }
];

export function HowItWorks() {
  return (
    <div className="min-h-screen bg-[#0a0a0b] text-foreground font-sans relative overflow-hidden p-6 md:p-12">
      {/* Background Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-accent/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="w-full space-y-12 relative z-10">
        
        {/* Navigation Bar */}
        <div className="flex items-center justify-between border-b border-white/10 pb-6">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors bg-white/5 border border-white/10 px-4 py-2 rounded-lg"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Home
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 text-sm text-accent hover:text-accent/80 transition-colors bg-accent/10 border border-accent/20 px-4 py-2 rounded-lg font-medium"
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
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent/20 bg-accent/10 text-accent text-xs font-semibold tracking-widest uppercase">
            <Activity className="w-4 h-4 animate-pulse" /> End-to-End Operational Pipeline
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white">
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
              className="p-8 rounded-2xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] hover:border-accent/40 transition-all group relative flex flex-col justify-between"
            >
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent group-hover:bg-accent/20 transition-colors">
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
                  <h3 className="text-xl font-bold text-white mt-3 mb-2">{step.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom Call to Action */}
        <div className="p-8 rounded-2xl border border-white/10 bg-gradient-to-r from-accent/10 via-white/[0.02] to-transparent text-center space-y-6">
          <h2 className="text-2xl font-bold text-white">Ready to explore the live dashboard?</h2>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="px-8 py-3.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-all inline-flex items-center gap-2 text-sm shadow-lg shadow-white/5"
            >
              Open Command Center <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/"
              className="px-8 py-3.5 bg-white/5 border border-white/10 text-white font-medium rounded-xl hover:bg-white/10 transition-all text-sm"
            >
              Return to Landing Page
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
}
