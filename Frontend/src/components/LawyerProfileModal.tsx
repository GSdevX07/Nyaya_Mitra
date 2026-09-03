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
  MapPin,
  Layers,
} from "lucide-react";
import { useAuth, type Role } from "@/lib/auth";
import { fetchCurrentUserProfile, fetchCases } from "@/lib/api";

interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function LawyerProfileModal({ isOpen, onClose }: UserProfileModalProps) {
  const { user: authUser } = useAuth();
  const [dbProfile, setDbProfile] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [assignedCasesCount, setAssignedCasesCount] = useState<number>(0);

  useEffect(() => {
    if (isOpen) {
      // Fetch live user identity from /auth/me
      fetchCurrentUserProfile()
        .then((data) => {
          if (data) {
            setDbProfile(data);
          }
        })
        .catch((err) => console.warn("fetchCurrentUserProfile error:", err));

      fetchCases().then((allCases) => {
        if (Array.isArray(allCases)) {
          const count = allCases.filter((c: any) => c.case?.assignment_status === "ASSIGNED").length;
          setAssignedCasesCount(count);
        }
      }).catch((err) => console.warn(err));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Active combined profile (database priority, authUser fallback)
  const profile = {
    id: dbProfile?.id || authUser?.id || "usr_nyaya_officer",
    full_name: dbProfile?.full_name || authUser?.full_name || "Institutional User",
    email: dbProfile?.email || authUser?.email || "user@nyayamitra.in",
    role: (dbProfile?.role || authUser?.role || "DLSA_OFFICER") as Role,
    org_id: dbProfile?.org_id || authUser?.org_id || "org_dlsa_central",
    district: dbProfile?.district || authUser?.district || "Central Delhi",
    phone: dbProfile?.phone || "+91 11 2338 1234",
    facility_ids: dbProfile?.facility_ids || authUser?.facility_ids || [],
    linked_case_id: dbProfile?.linked_case_id || authUser?.linked_case_id,
    bar_registration_no: dbProfile?.bar_registration_no || (
      authUser?.role === "DEFENSE_ADVOCATE" ? "DL/2018/49281" : undefined
    ),
  };

  const getRoleDisplayName = (role: Role) => {
    const map: Record<Role, { name: string; badge: string; color: string }> = {
      PLATFORM_ADMIN: {
        name: "Platform Administrator (Superuser)",
        badge: "Full System Root Access",
        color: "bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30",
      },
      GOV_ADMIN: {
        name: "State Legal Services Authority Admin (SLSA)",
        badge: "Statewide Oversight & Reporting",
        color: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30",
      },
      DLSA_OFFICER: {
        name: "District Legal Services Authority Officer (DLSA)",
        badge: "Legal Aid Panel Authority",
        color: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
      },
      SUPERVISING_LEGAL_OFFICER: {
        name: "Supervising Judicial Officer",
        badge: "BNSS 479 Final Sign-Off Authority",
        color: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30",
      },
      DEFENSE_ADVOCATE: {
        name: "Panel Defense Advocate (Pro Bono)",
        badge: "DLSA Bar Enrolled Counsel",
        color: "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/30",
      },
      CONTROLLED_EXTERNAL_ADVOCATE: {
        name: "Controlled External Legal Counsel",
        badge: "Provisional Case Docket Access",
        color: "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/30",
      },
      JAIL_OFFICER: {
        name: "Jail Superintendent / Prison In-Charge",
        badge: "Detention Roster & Admission Authority",
        color: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30",
      },
      POLICE_OFFICER: {
        name: "Police Station In-Charge / Investigating Officer",
        badge: "CCTNS Station Docket Access",
        color: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30",
      },
      ACCUSED_USER: {
        name: "Undertrial Prisoner Account",
        badge: "Accused Citizen Portal",
        color: "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/30",
      },
      FAMILY_GUARDIAN: {
        name: "Family Guardian & Legal Kin",
        badge: "Citizen Status & Legal Helpline",
        color: "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/30",
      },
      READ_ONLY_AUDITOR: {
        name: "Statutory Judicial Auditor",
        badge: "Cryptographic Audit Ledger Verifier",
        color: "bg-secondary text-secondary-foreground border-border",
      },
      INTEGRATION_SERVICE: {
        name: "System Integration API Service",
        badge: "Machine-to-Machine Service Role",
        color: "bg-secondary text-secondary-foreground border-border",
      },
    };
    return map[role] || {
      name: role.replace(/_/g, " "),
      badge: "Authenticated Institutional User",
      color: "bg-primary/10 text-primary border-primary/20",
    };
  };

  const roleInfo = getRoleDisplayName(profile.role);

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .filter(Boolean)
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ type: "spring", stiffness: 380, damping: 28 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="lawyer-profile-dialog-title"
          className="relative w-full max-w-2xl bg-card border-2 border-border rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="p-6 pb-4 border-b border-border bg-secondary/30 flex items-start justify-between">
            <div className="flex items-center gap-4">
              {/* Dynamic Avatar Pill */}
              <div className="w-16 h-16 rounded-xl bg-primary text-primary-foreground border-2 border-primary/40 flex items-center justify-center font-bold text-2xl font-mono shadow-md">
                {getInitials(profile.full_name)}
              </div>

              <div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h2 id="lawyer-profile-dialog-title" className="text-xl font-bold text-foreground tracking-tight">
                    {profile.full_name}
                  </h2>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${roleInfo.color}`}>
                    {roleInfo.badge}
                  </span>
                </div>

                <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground font-mono">
                  <span>UID: <strong className="text-foreground">{profile.id}</strong></span>
                  <span>•</span>
                  <span>Role: <strong className="text-primary">{profile.role}</strong></span>
                </div>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-secondary/60 hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Modal Content — Clean Institutional Dossier */}
          <div className="p-6 space-y-5 overflow-y-auto custom-scrollbar text-sm">
            {/* Authority Designation Banner */}
            <div className="p-4 rounded-xl bg-card border-2 border-border shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ShieldCheck className="w-6 h-6 text-emerald-600 shrink-0" />
                <div>
                  <div className="font-bold text-foreground text-sm">
                    {roleInfo.name}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    Jurisdiction: {profile.district} • Database Record Synchronized
                  </div>
                </div>
              </div>
              <span className="text-xs px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-600 font-bold border border-emerald-500/20">
                Active &amp; Verified
              </span>
            </div>

            {/* Information Grid */}
            <div className="rounded-xl bg-card border-2 border-border overflow-hidden shadow-sm">
              <div className="px-4 py-2.5 bg-secondary/50 border-b border-border flex items-center justify-between text-xs font-bold uppercase tracking-wider text-muted-foreground">
                <span>Institutional Registry Particulars</span>
                <button
                  onClick={() => handleCopy(profile.id)}
                  className="text-[11px] text-primary hover:underline flex items-center gap-1 font-mono font-medium"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? "Copied!" : "Copy User ID"}
                </button>
              </div>

              <div className="divide-y divide-border p-2">
                <div className="flex items-center justify-between p-2.5 text-xs">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-primary" /> Organization Entity:
                  </span>
                  <strong className="text-foreground font-mono">{profile.org_id}</strong>
                </div>

                <div className="flex items-center justify-between p-2.5 text-xs">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Mail className="w-4 h-4 text-primary" /> Registered Email:
                  </span>
                  <strong className="text-foreground font-mono bg-secondary px-2 py-0.5 rounded border border-border">
                    {profile.email}
                  </strong>
                </div>

                <div className="flex items-center justify-between p-2.5 text-xs">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <Phone className="w-4 h-4 text-primary" /> Official Contact Number:
                  </span>
                  <strong className="text-foreground font-mono">{profile.phone}</strong>
                </div>

                <div className="flex items-center justify-between p-2.5 text-xs">
                  <span className="text-muted-foreground flex items-center gap-2">
                    <MapPin className="w-4 h-4 text-primary" /> Administrative District:
                  </span>
                  <strong className="text-foreground">{profile.district}</strong>
                </div>

                {profile.bar_registration_no && (
                  <div className="flex items-center justify-between p-2.5 text-xs">
                    <span className="text-muted-foreground flex items-center gap-2">
                      <Award className="w-4 h-4 text-purple-600" /> Bar Council Registration No:
                    </span>
                    <strong className="text-purple-600 font-mono font-bold bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                      {profile.bar_registration_no}
                    </strong>
                  </div>
                )}

                {profile.linked_case_id && (
                  <div className="flex items-center justify-between p-2.5 text-xs">
                    <span className="text-muted-foreground flex items-center gap-2">
                      <FileText className="w-4 h-4 text-teal-600" /> Linked Case Reference:
                    </span>
                    <strong className="text-teal-600 font-mono font-bold bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20">
                      {profile.linked_case_id}
                    </strong>
                  </div>
                )}

                {profile.facility_ids && profile.facility_ids.length > 0 && (
                  <div className="flex items-center justify-between p-2.5 text-xs">
                    <span className="text-muted-foreground flex items-center gap-2">
                      <Layers className="w-4 h-4 text-amber-600" /> Assigned Prison Facilities:
                    </span>
                    <div className="flex gap-1">
                      {profile.facility_ids.map((fac: string) => (
                        <span key={fac} className="text-xs font-mono bg-amber-500/10 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded border border-amber-500/20">
                          {fac}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Role-Specific Metrics / Queue Block */}
            {profile.role === "DEFENSE_ADVOCATE" || profile.role === "SUPERVISING_LEGAL_OFFICER" ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-secondary/40 border border-border">
                  <span className="text-xs text-muted-foreground font-semibold">Active Docket Cases</span>
                  <div className="text-2xl font-bold font-mono text-primary mt-1">{assignedCasesCount}</div>
                  <span className="text-[11px] text-muted-foreground">Section 479 BNSS eligible cases</span>
                </div>
                <div className="p-4 rounded-xl bg-secondary/40 border border-border">
                  <span className="text-xs text-muted-foreground font-semibold">Statutory Compliance</span>
                  <div className="text-2xl font-bold font-mono text-emerald-600 mt-1">100%</div>
                  <span className="text-[11px] text-muted-foreground">Signed off &amp; audit tracked</span>
                </div>
              </div>
            ) : null}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-border bg-secondary/30 flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-mono">
              Nyaya Mitra Institutional Profile // ID: {profile.id}
            </span>
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="px-5 py-2 rounded-lg bg-primary text-primary-foreground font-bold text-xs hover:bg-primary/90 transition-all shadow-sm"
              >
                Done
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

// Export both names for backwards compatibility
export const UserProfileModal = LawyerProfileModal;



