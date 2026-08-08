import { motion, useScroll, useTransform } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, BrainCircuit, Activity, Shield, Eye, Scale, FileCheck, Users, ChevronDown, ArrowUp } from "lucide-react";
import { useRef, useEffect, useState } from "react";

function useCounter(end: number, duration = 2000) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = 0;
    const increment = end / (duration / 16);
    const timer = setInterval(() => {
      start += increment;
      if (start >= end) { setCount(end); clearInterval(timer); }
      else { setCount(Math.floor(start)); }
    }, 16);
    return () => clearInterval(timer);
  }, [end, duration]);
  return count;
}

function Particle({ delay, x, y, size }: { delay: number; x: number; y: number; size: number }) {
  return (
    <motion.div
      className="absolute rounded-full bg-accent/30"
      style={{ width: size, height: size, left: `${x}%`, top: `${y}%` }}
      animate={{ y: [0, -30, 0], opacity: [0, 0.6, 0], scale: [0.5, 1, 0.5] }}
      transition={{ duration: 4 + Math.random() * 3, repeat: Infinity, delay, ease: "easeInOut" }}
    />
  );
}

const pipelineSteps = [
  { label: "CASE RECORDS", icon: FileCheck, desc: "Intake & digitization" },
  { label: "DOC INTELLIGENCE", icon: Eye, desc: "OCR & extraction" },
  { label: "ELIGIBILITY", icon: Scale, desc: "Statutory analysis" },
  { label: "EVIDENCE", icon: Shield, desc: "Chain of custody" },
  { label: "ACTION", icon: Activity, desc: "Automated drafting" },
  { label: "HUMAN REVIEW", icon: Users, desc: "Legal officer decision" },
];

const features = [
  { title: "Proactive Case Discovery", desc: "AI continuously monitors custody durations against statutory thresholds, flagging cases before they fall through the cracks.", icon: BrainCircuit },
  { title: "Evidence-Grounded Analysis", desc: "Every conclusion is traceable to source documents, legal provisions, and extracted data — never a black box.", icon: Shield },
  { title: "Human-In-The-Loop", desc: "AI prepares, humans decide. No bail application is ever filed without explicit officer review and approval.", icon: Users },
];

export function Landing() {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll();
  const heroOpacity = useTransform(scrollYProgress, [0, 0.3], [1, 0]);
  const heroScale = useTransform(scrollYProgress, [0, 0.3], [1, 0.95]);
  const casesMonitored = useCounter(1284);
  const eligibleFound = useCounter(127);
  const timeSaved = useCounter(340);
  const [showBackToTop, setShowBackToTop] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 300) {
        setShowBackToTop(true);
      } else {
        setShowBackToTop(false);
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const particles = Array.from({ length: 20 }, (_, i) => ({
    id: i, x: Math.random() * 100, y: Math.random() * 100,
    size: 2 + Math.random() * 4, delay: Math.random() * 5,
  }));

  return (
    <div className="min-h-screen bg-[#0a0a0b] text-foreground font-sans relative overflow-hidden">
      {/* Ambients */}
      <div className="absolute top-[-30%] left-[-15%] w-[60%] h-[60%] bg-accent/[0.07] blur-[150px] rounded-full pointer-events-none ambient-glow" />
      <div className="absolute bottom-[-30%] right-[-15%] w-[70%] h-[70%] bg-emerald-500/[0.05] blur-[180px] rounded-full pointer-events-none" />
      <div className="absolute top-[40%] right-[20%] w-[30%] h-[30%] bg-blue-500/[0.03] blur-[120px] rounded-full pointer-events-none" />

      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {particles.map(p => <Particle key={p.id} {...p} />)}
      </div>

      {/* Floating Back to Top / Home button */}
      {showBackToTop && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          onClick={scrollToTop}
          className="fixed bottom-6 left-6 z-50 bg-[#0a0a0b]/90 border border-white/10 hover:border-accent/40 text-white px-4 py-2.5 rounded-full shadow-2xl backdrop-blur-xl flex items-center gap-2 text-xs font-semibold uppercase tracking-wider group transition-all"
        >
          <ArrowUp className="w-4 h-4 text-accent group-hover:-translate-y-0.5 transition-transform" />
          <span>Back to Top</span>
        </motion.button>
      )}

      {/* Header - Sticky Top Bar */}
      <header className="sticky top-0 z-50 flex items-center justify-between px-8 lg:px-16 py-4 border-b border-white/5 bg-[#0a0a0b]/85 backdrop-blur-xl">
        <Link to="/" onClick={scrollToTop} className="flex items-center gap-3 cursor-pointer group hover:opacity-90 transition-opacity">
          <div className="relative flex items-center justify-center w-9 h-9">
            <motion.div className="absolute inset-0 bg-accent/20 rounded-full" animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }} transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }} />
            <Activity className="w-5 h-5 text-accent relative z-10" />
          </div>
          <span className="font-bold text-xl tracking-tight text-white uppercase group-hover:text-accent transition-colors">Nyaya Mitra</span>
        </Link>
        <div className="flex items-center gap-6">
          <button onClick={scrollToTop} className="text-sm text-muted-foreground hover:text-white transition-colors hidden md:inline">Home</button>
          <Link to="/how-it-works" className="text-sm text-muted-foreground hover:text-white transition-colors hidden md:inline">How it works</Link>
          <Link to="/features" className="text-sm text-muted-foreground hover:text-white transition-colors hidden md:inline">Features</Link>
          <Link to="/dashboard" className="text-sm text-muted-foreground hover:text-white transition-colors hidden md:inline font-medium">Command Center</Link>
          <Link to="/login" className="text-sm font-medium text-black bg-white hover:bg-white/90 px-5 py-2 rounded-lg transition-colors">Officer Login</Link>
        </div>
      </header>

      {/* Hero */}
      <motion.section ref={heroRef} style={{ opacity: heroOpacity, scale: heroScale }} className="relative z-20 flex flex-col items-center justify-center px-6 text-center pt-20 pb-32 min-h-[90vh]">
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }} className="max-w-5xl mx-auto space-y-8">
          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2, duration: 0.6 }} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-accent/20 bg-accent/[0.08] text-accent text-xs font-semibold tracking-widest uppercase">
            <BrainCircuit className="w-4 h-4" /> Agentic AI Legal Operations Platform
          </motion.div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tighter text-white leading-[0.95]">
            Turn legal eligibility{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-accent to-amber-600">into action.</span>
          </h1>

          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Nyaya Mitra uses AI to identify potential statutory eligibility, uncover missing records, ground every conclusion in evidence, and move cases toward human-reviewed legal action.
          </p>

          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.8 }} className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6">
            <Link to="/login" className="px-8 py-4 bg-white text-black font-semibold rounded-lg hover:bg-white/90 transition-all flex items-center gap-3 group w-full sm:w-auto justify-center shadow-lg shadow-white/5">
              Explore the Command Center <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <a href="#pipeline" className="px-8 py-4 bg-white/[0.03] border border-white/10 text-white font-medium rounded-lg hover:bg-white/[0.08] hover:border-white/20 transition-all flex items-center gap-2 w-full sm:w-auto justify-center">
              View System Architecture
            </a>
          </motion.div>
        </motion.div>

        <motion.div className="absolute bottom-8" animate={{ y: [0, 8, 0] }} transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}>
          <ChevronDown className="w-6 h-6 text-muted-foreground" />
        </motion.div>
      </motion.section>

      {/* Stats */}
      <section className="relative z-20 border-y border-white/5 bg-white/[0.01] backdrop-blur-sm">
        <div className="max-w-6xl mx-auto grid grid-cols-3 divide-x divide-white/5">
          <div className="p-8 md:p-12 text-center">
            <div className="text-4xl md:text-5xl font-light text-white tracking-tight">{casesMonitored.toLocaleString()}</div>
            <div className="text-xs text-muted-foreground uppercase tracking-widest mt-2">Cases Monitored</div>
          </div>
          <div className="p-8 md:p-12 text-center">
            <div className="text-4xl md:text-5xl font-light text-accent tracking-tight">{eligibleFound}</div>
            <div className="text-xs text-muted-foreground uppercase tracking-widest mt-2">Potentially Eligible</div>
          </div>
          <div className="p-8 md:p-12 text-center">
            <div className="text-4xl md:text-5xl font-light text-emerald-400 tracking-tight">{timeSaved}h</div>
            <div className="text-xs text-muted-foreground uppercase tracking-widest mt-2">Officer Hours Saved</div>
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section id="pipeline" className="relative z-20 py-32 px-6">
        <div className="max-w-6xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-20">
            <div className="text-xs text-accent uppercase tracking-[0.3em] font-semibold mb-4">How it works</div>
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-4">Intelligent Case Pipeline</h2>
            <p className="text-muted-foreground max-w-xl mx-auto">Every case flows through a structured intelligence pipeline — from raw records to human-reviewed legal action.</p>
          </motion.div>

          <div className="relative">
            <div className="hidden md:block absolute top-1/2 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-y-1/2" />
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
              {pipelineSteps.map((step, i) => (
                <motion.div key={step.label} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1, duration: 0.6 }} className="relative group">
                  <div className="p-6 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] hover:border-white/10 transition-all duration-300 text-center h-full flex flex-col items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center group-hover:bg-accent/20 transition-colors">
                      <step.icon className="w-6 h-6 text-accent" />
                    </div>
                    <div>
                      <div className="text-[10px] font-bold text-white uppercase tracking-wider mb-1">{step.label}</div>
                      <div className="text-xs text-muted-foreground">{step.desc}</div>
                    </div>
                    <div className="text-xs text-accent/50 font-mono">0{i + 1}</div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          <div className="flex justify-center mt-16">
            <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="text-sm font-medium text-muted-foreground border border-white/5 bg-white/[0.02] inline-flex items-center gap-2 px-6 py-3 rounded-full">
              <Shield className="w-4 h-4 text-accent" /> AI does the operational work. Humans make the legal decisions.
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-20 py-32 px-6 border-t border-white/5">
        <div className="max-w-6xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-20">
            <div className="text-xs text-accent uppercase tracking-[0.3em] font-semibold mb-4">Core Principles</div>
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white">Built for trust and transparency</h2>
          </motion.div>
          <div className="grid md:grid-cols-3 gap-8">
            {features.map((f, i) => (
              <motion.div key={f.title} initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.15, duration: 0.6 }} className="p-8 rounded-2xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/10 transition-all duration-300 group">
                <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center mb-6 group-hover:bg-accent/20 transition-colors">
                  <f.icon className="w-6 h-6 text-accent" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-3">{f.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-20 py-32 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-6">AI that finds the cases<br />the system forgot.</h2>
            <p className="text-muted-foreground mb-10 max-w-lg mx-auto">A living command center for cases that would otherwise disappear into paperwork.</p>
            <Link to="/login" className="inline-flex items-center gap-3 px-10 py-5 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-all group shadow-lg shadow-white/5 text-lg">
              Enter the Command Center <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-20 border-t border-white/5 px-8 py-10 bg-black/40">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-muted-foreground">
          <Link to="/" onClick={scrollToTop} className="flex items-center gap-2 text-white hover:text-accent transition-colors">
            <Activity className="w-4 h-4 text-accent" />
            <span className="uppercase tracking-wider font-bold text-sm">Nyaya Mitra</span>
          </Link>

          <div className="flex flex-wrap items-center gap-6 text-xs font-medium">
            <button onClick={scrollToTop} className="hover:text-white transition-colors">Home</button>
            <Link to="/how-it-works" className="hover:text-white transition-colors">How it works</Link>
            <Link to="/features" className="hover:text-white transition-colors">Features</Link>
            <Link to="/dashboard" className="hover:text-white transition-colors">Command Center</Link>
            <Link to="/login" className="hover:text-white transition-colors">Officer Login</Link>
          </div>

          <button onClick={scrollToTop} className="flex items-center gap-1.5 text-accent hover:underline uppercase tracking-wider font-semibold">
            <ArrowUp className="w-3.5 h-3.5" /> Back to top
          </button>
        </div>
      </footer>
    </div>
  );
}
