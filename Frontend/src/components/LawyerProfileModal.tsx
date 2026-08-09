import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  ShieldCheck,
  Phone,
  Mail,
  Award,
  FileText,
  Building2,
  Copy,
  Check,
  Lock,
} from "lucide-react";
import { fetchLawyerProfile } from "@/lib/api";

interface LawyerProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LawyerProfileModal({ isOpen, onClose }: LawyerProfileModalProps) {
  const [profile, setProfile] = useState<any>({
    id: "Legal Officer 104",
    full_name: "Adv. Rajesh Sharma",
    bar_association_id: "DL/2018/49281",
    email: "rajesh.sharma@nyayamitra.org",
    phone: "+91 98112 34567",
    specialization: "Undertrial Defense & Section 479 BNSS",
    cases_taken: 4,
    status: "Active Pro Bono Counsel",
    organization: "Delhi Legal Services Authority (DLSA)",
  });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchLawyerProfile().then((data) => {
        if (data) setProfile(data);
      });
    }
  }, [isOpen]);

  const handleCopyId = () => {
    navigator.clipboard.writeText(profile.bar_association_id || profile.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-xl animate-in fade-in duration-200">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ type: "spring", stiffness: 380, damping: 28 }}
          className="relative w-full max-w-xl bg-[#0D121B] border border-white/10 rounded-2xl shadow-[0_25px_60px_-15px_rgba(0,0,0,0.9)] overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* Subtle Ambient Top Accent Glow */}
          <div className="absolute top-0 inset-x-0 h-32 bg-gradient-to-b from-amber-500/10 via-amber-500/5 to-transparent pointer-events-none" />

          {/* Modal Header */}
          <div className="p-6 pb-4 flex items-start justify-between relative z-10 border-b border-white/[0.06]">
            <div className="flex items-center gap-4">
              {/* Executive Avatar Pill */}
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500/20 via-yellow-500/10 to-amber-950/40 border border-amber-500/30 flex items-center justify-center font-bold text-amber-400 text-xl tracking-wider font-mono shadow-lg shadow-amber-500/5">
                  RS
                </div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-[#0D121B] flex items-center justify-center p-0.5">
                  <span className="w-3.5 h-3.5 rounded-full bg-emerald-500 flex items-center justify-center text-[8px] text-black font-bold">
                    ✓
                  </span>
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-xl font-bold text-white tracking-tight">
                    {profile.full_name}
                  </h2>
                  <span className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-medium flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    DLSA Verified
                  </span>
                </div>

                <div className="flex items-center gap-2 mt-1 text-xs text-white/50 font-mono">
                  <span>ID: {profile.id}</span>
                  <span>•</span>
                  <span>Bar Reg: {profile.bar_association_id}</span>
                </div>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body Content */}
          <div className="p-6 space-y-5 overflow-y-auto custom-scrollbar relative z-10">
            {/* Counsel Status Bar */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.07]">
              <div className="flex items-center gap-2.5">
                <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-xs font-semibold text-white/90">
                  {profile.status}
                </span>
              </div>
              <span className="text-[11px] font-mono text-amber-400/90 bg-amber-500/10 px-2.5 py-1 rounded-lg border border-amber-500/20">
                Pro Bono Panel Advocate
              </span>
            </div>

            {/* Quick Metrics Cards */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-xl bg-gradient-to-b from-white/[0.04] to-white/[0.01] border border-white/[0.07] flex flex-col justify-between">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-white/50 font-medium">Cases Assigned</span>
                  <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
                    <FileText className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white font-mono">{profile.cases_taken}</span>
                  <span className="text-[10px] text-emerald-400 font-medium">Active Queue</span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-gradient-to-b from-white/[0.04] to-white/[0.01] border border-white/[0.07] flex flex-col justify-between">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-white/50 font-medium">Verification Rate</span>
                  <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                    <Award className="w-4 h-4" />
                  </div>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white font-mono">100%</span>
                  <span className="text-[10px] text-emerald-400 font-medium">BNSS 479 Compliant</span>
                </div>
              </div>
            </div>

            {/* Credentials Detail Panel */}
            <div className="rounded-xl bg-white/[0.02] border border-white/[0.07] overflow-hidden">
              <div className="px-4 py-2.5 border-b border-white/[0.06] bg-white/[0.01] flex items-center justify-between">
                <span className="text-xs font-semibold text-white/80 uppercase tracking-wider">
                  Advocate Credentials &amp; Registry
                </span>
                <button
                  onClick={handleCopyId}
                  className="text-[11px] text-amber-400 hover:text-amber-300 flex items-center gap-1 font-mono transition-colors"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copied ? "Copied!" : "Copy Bar ID"}
                </button>
              </div>

              <div className="divide-y divide-white/[0.04] p-4 text-xs space-y-0">
                <div className="flex items-center justify-between py-2.5">
                  <span className="text-white/50 flex items-center gap-2">
                    <Building2 className="w-3.5 h-3.5 text-amber-400/80" /> Authority / Org:
                  </span>
                  <span className="text-white font-medium text-right">{profile.organization}</span>
                </div>

                <div className="flex items-center justify-between py-2.5">
                  <span className="text-white/50 flex items-center gap-2">
                    <Award className="w-3.5 h-3.5 text-amber-400/80" /> Specialization:
                  </span>
                  <span className="text-white font-medium text-right">{profile.specialization}</span>
                </div>

                <div className="flex items-center justify-between py-2.5">
                  <span className="text-white/50 flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-amber-400/80" /> Official Email:
                  </span>
                  <span className="text-white font-mono bg-white/5 px-2 py-0.5 rounded border border-white/10">{profile.email}</span>
                </div>

                <div className="flex items-center justify-between py-2.5">
                  <span className="text-white/50 flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-amber-400/80" /> Direct Contact:
                  </span>
                  <span className="text-white font-mono bg-white/5 px-2 py-0.5 rounded border border-white/10">{profile.phone}</span>
                </div>
              </div>
            </div>

            {/* Access & Privileges Banner */}
            <div className="p-3.5 rounded-xl bg-emerald-500/[0.04] border border-emerald-500/20 flex items-start gap-3">
              <div className="p-1 rounded bg-emerald-500/10 text-emerald-400 mt-0.5">
                <Lock className="w-3.5 h-3.5" />
              </div>
              <div className="text-xs text-white/70 space-y-0.5">
                <span className="font-semibold text-white">Authorized Judicial Officer Privileges</span>
                <p className="text-[11px] text-white/50 leading-relaxed">
                  Direct access to statutory Section 479 BNSS automated bail drafting, parent contact verification system, and DLSA priority filings.
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-white/[0.06] bg-white/[0.01] flex items-center justify-between">
            <span className="text-[11px] text-white/40 font-mono">
              System ID: NYAYA-DLSA-2026
            </span>
            <button
              onClick={onClose}
              className="px-5 py-2 rounded-xl bg-amber-500 text-black font-semibold text-xs hover:bg-amber-400 transition-all shadow-md shadow-amber-500/10"
            >
              Done
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

