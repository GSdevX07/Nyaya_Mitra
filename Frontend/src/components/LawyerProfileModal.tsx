import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ShieldCheck, UserCheck, Phone, Mail, Award, FileText, CheckCircle2, Building2 } from "lucide-react";
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

  useEffect(() => {
    if (isOpen) {
      fetchLawyerProfile().then(data => {
        if (data) setProfile(data);
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/70 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative w-full max-w-xl bg-[#0F172A]/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* Top Banner Accent */}
          <div className="h-24 bg-gradient-to-r from-accent/30 via-accent/10 to-indigo-500/20 relative flex items-end px-6 pb-3">
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 rounded-xl bg-black/40 hover:bg-black/60 text-white/70 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Profile Header Avatar & Info */}
          <div className="px-6 relative -mt-10 pb-6 border-b border-white/5 flex items-end justify-between">
            <div className="flex items-end gap-4">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent to-indigo-600 border-4 border-[#0F172A] flex items-center justify-center shadow-xl font-bold text-white text-2xl font-mono">
                RS
              </div>
              <div className="mb-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-white">{profile.full_name}</h2>
                  <span className="p-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" title="Verified Lawyer">
                    <ShieldCheck className="w-4 h-4" />
                  </span>
                </div>
                <p className="text-xs text-accent font-mono">ID: {profile.id} • Bar: {profile.bar_association_id}</p>
              </div>
            </div>

            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20 flex items-center gap-1.5">
              <UserCheck className="w-3.5 h-3.5" />
              {profile.status}
            </span>
          </div>

          {/* Body Content */}
          <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">
            {/* Quick Stats Grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-accent/10 text-accent">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white font-mono">{profile.cases_taken}</div>
                  <div className="text-xs text-muted-foreground">Cases Assigned / Taken</div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                  <Award className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-white font-mono">100%</div>
                  <div className="text-xs text-muted-foreground">Bail Filing Verification Rate</div>
                </div>
              </div>
            </div>

            {/* Lawyer Profile Details List */}
            <div className="space-y-3 bg-white/[0.02] border border-white/10 rounded-xl p-4 text-sm">
              <h3 className="text-xs font-semibold text-accent uppercase tracking-wider mb-2">Advocate Credentials & Contact</h3>
              
              <div className="flex items-center justify-between text-xs py-1.5 border-b border-white/5">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-accent" /> Organization / Authority:
                </span>
                <span className="text-white font-medium">{profile.organization}</span>
              </div>

              <div className="flex items-center justify-between text-xs py-1.5 border-b border-white/5">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Award className="w-4 h-4 text-accent" /> Primary Specialization:
                </span>
                <span className="text-white font-medium">{profile.specialization}</span>
              </div>

              <div className="flex items-center justify-between text-xs py-1.5 border-b border-white/5">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Mail className="w-4 h-4 text-accent" /> Official Email:
                </span>
                <span className="text-white font-mono">{profile.email}</span>
              </div>

              <div className="flex items-center justify-between text-xs py-1.5">
                <span className="text-muted-foreground flex items-center gap-2">
                  <Phone className="w-4 h-4 text-accent" /> Mobile Contact:
                </span>
                <span className="text-white font-mono">{profile.phone}</span>
              </div>
            </div>

            {/* System Privileges Notice */}
            <div className="p-4 rounded-xl bg-accent/5 border border-accent/20 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-accent shrink-0 mt-0.5" />
              <div className="text-xs text-muted-foreground space-y-1">
                <span className="font-semibold text-white">Verified Legal Officer Access</span>
                <p>
                  You are logged in as an authorized advocate with pro bono case review, Section 479 BNSS eligibility audit, and statutory bail filing privileges.
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-white/10 bg-white/[0.01] flex justify-end">
            <button
              onClick={onClose}
              className="px-5 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold transition-colors"
            >
              Close Profile
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
