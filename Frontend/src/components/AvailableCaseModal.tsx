import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, 
  Phone, 
  MapPin, 
  User, 
  ShieldAlert, 
  FileText, 
  CheckCircle, 
  Clock, 
  ArrowDownCircle, 
  Building2, 
  Scale, 
  ThumbsDown, 
  Check 
} from "lucide-react";
import type { BackendCaseSummary } from "@/lib/api";

interface AvailableCaseModalProps {
  item: BackendCaseSummary | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (caseId: string) => void;
  onDecline: (caseId: string) => void;
}

export function AvailableCaseModal({
  item,
  isOpen,
  onClose,
  onApprove,
  onDecline,
}: AvailableCaseModalProps) {
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Reset scroll lock state when modal opens for a new case
  useEffect(() => {
    if (isOpen) {
      setHasScrolledToBottom(false);
      // Check if content is already short enough to not need scrolling
      setTimeout(() => {
        if (scrollRef.current) {
          const { scrollHeight, clientHeight } = scrollRef.current;
          if (scrollHeight <= clientHeight + 30) {
            setHasScrolledToBottom(true);
          }
        }
      }, 200);
    }
  }, [isOpen, item]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollTop + clientHeight >= scrollHeight - 35) {
      setHasScrolledToBottom(true);
    }
  };

  if (!isOpen || !item) return null;

  const c = item.case;
  const threshold = Math.floor(c.max_sentence_days_for_offense / 2);
  const isEligible = c.custody_days >= threshold;
  const relativeName = c.relative_name || "Ramesh Kumar";
  const relativeRelation = c.relative_relation || "Father / Guardian";
  const relativePhone = c.relative_phone || "+91 98765 11001";
  const permanentAddress = c.permanent_address || "Plot 42, Gandhi Nagar, Sector 4, Chennai, TN - 600001";

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative w-full max-w-3xl bg-[#0F172A] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="p-6 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/20">
                  {c.case_id}
                </span>
                <span className="text-xs text-muted-foreground uppercase tracking-wider">
                  Available Pro Bono Case
                </span>
              </div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                Undertrial Case Review
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Scrollable Modal Content */}
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="p-6 space-y-6 overflow-y-auto custom-scrollbar flex-1"
          >
            {/* Scroll Lock Notice Banner */}
            {!hasScrolledToBottom && (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-3 animate-pulse">
                <ArrowDownCircle className="w-5 h-5 shrink-0" />
                <div>
                  <span className="font-semibold block">Mandatory Review Required</span>
                  Please scroll down to the bottom and review all legal metrics, family contacts, and home address before taking up this case.
                </div>
              </div>
            )}

            {/* Prisoner Overview Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                <div className="text-xs text-muted-foreground mb-1">Prisoner Offenses</div>
                <div className="text-sm font-semibold text-white font-mono">{c.offense_sections.join(", ")}</div>
              </div>

              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                <div className="text-xs text-muted-foreground mb-1">Custody Duration</div>
                <div className="text-sm font-semibold text-white font-mono">{c.custody_days} Days Served</div>
                <div className="text-[10px] text-muted-foreground">50% Threshold: {threshold} days</div>
              </div>

              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                <div className="text-xs text-muted-foreground mb-1">Jail & Detention Location</div>
                <div className="text-sm font-semibold text-white flex items-center gap-1">
                  <Building2 className="w-3.5 h-3.5 text-accent shrink-0" />
                  {c.jail_location}
                </div>
              </div>
            </div>

            {/* BNSS Statutory Eligibility Banner */}
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
                  <Scale className="w-4 h-4" /> Section 479 BNSS Statutory Eligibility
                </span>
                {isEligible ? (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> High Priority Eligible
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Approaching Threshold
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                Under BNSS Section 479, an undertrial prisoner who has completed one-half (50%) of the maximum period of imprisonment for the charged offense is entitled to statutory release on bail.
              </p>
            </div>

            {/* ACCUSED PARENTS / RELATIVE CONTACT DETAILS (CRITICAL REQUIREMENT) */}
            <div className="p-5 rounded-2xl bg-accent/5 border border-accent/20 space-y-4">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-accent/10 text-accent">
                  <User className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                    Accused Family & Guardian Contact Details
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Required contact details of accused prisoner's parents / relatives for bail undertaking.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                {/* Relative Name & Relation */}
                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10 space-y-1">
                  <div className="text-[11px] text-muted-foreground uppercase font-mono">Parent / Relative Name & Relation</div>
                  <div className="text-sm font-semibold text-white flex items-center gap-2">
                    <span>{relativeName}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-accent/10 text-accent border border-accent/20">
                      {relativeRelation}
                    </span>
                  </div>
                </div>

                {/* Relative Phone Number */}
                <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10 space-y-1">
                  <div className="text-[11px] text-muted-foreground uppercase font-mono">Contact Mobile Phone Number</div>
                  <div className="text-sm font-semibold text-emerald-400 font-mono flex items-center gap-2">
                    <Phone className="w-4 h-4 text-emerald-400" />
                    <span>{relativePhone}</span>
                  </div>
                </div>
              </div>

              {/* Permanent Address */}
              <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10 space-y-1">
                <div className="text-[11px] text-muted-foreground uppercase font-mono flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-accent" /> Permanent Family Residential Address
                </div>
                <div className="text-sm font-medium text-white/90">
                  {permanentAddress}
                </div>
              </div>
            </div>

            {/* Document Inventory Section */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-accent uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-4 h-4" /> Required Document Verification
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {c.required_docs.map((doc) => {
                  const isPresent = c.present_docs.includes(doc);
                  return (
                    <div
                      key={doc}
                      className={`p-3 rounded-xl border flex items-center justify-between text-xs font-medium ${
                        isPresent
                          ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400"
                          : "bg-amber-500/5 border-amber-500/20 text-amber-400"
                      }`}
                    >
                      <span className="capitalize">{doc.replace(/_/g, " ")}</span>
                      <span className="flex items-center gap-1 font-mono text-[10px] uppercase font-bold">
                        {isPresent ? (
                          <>
                            <CheckCircle className="w-3.5 h-3.5" /> Present
                          </>
                        ) : (
                          <>
                            <ShieldAlert className="w-3.5 h-3.5" /> Missing
                          </>
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Additional Legal Flags */}
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 space-y-2">
              <div className="text-xs font-semibold text-muted-foreground">Urgency & Risk Attributes</div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="px-2.5 py-1 rounded bg-white/5 text-white/80 border border-white/10">
                  Age: {c.urgency_flags.age} Yrs
                </span>
                {c.urgency_flags.health_flag && (
                  <span className="px-2.5 py-1 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Medical Condition Flagged
                  </span>
                )}
                <span className="px-2.5 py-1 rounded bg-white/5 text-muted-foreground border border-white/10">
                  {c.urgency_flags.repeat_offender ? "Prior Conviction Record" : "First Time Offender"}
                </span>
                <span className="px-2.5 py-1 rounded bg-white/5 text-muted-foreground border border-white/10">
                  Language: {c.preferred_language.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-white/10 bg-white/[0.02] flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-xs text-muted-foreground">
              {hasScrolledToBottom ? (
                <span className="text-emerald-400 flex items-center gap-1 font-medium">
                  <Check className="w-4 h-4 text-emerald-400" /> Full details reviewed. You can now approve & take this case.
                </span>
              ) : (
                <span className="text-amber-400 flex items-center gap-1 font-medium">
                  <ArrowDownCircle className="w-4 h-4 text-amber-400" /> Scroll to the bottom of the modal to unlock Approve button.
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
              <button
                onClick={() => onDecline(c.case_id)}
                className="px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5 shrink-0"
              >
                <ThumbsDown className="w-4 h-4" /> Decline & Hide
              </button>

              <button
                disabled={!hasScrolledToBottom}
                onClick={() => onApprove(c.case_id)}
                className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-lg flex items-center gap-2 shrink-0 ${
                  hasScrolledToBottom
                    ? "bg-accent text-accent-foreground hover:bg-accent/90 shadow-accent/20 cursor-pointer"
                    : "bg-white/10 text-white/40 border border-white/10 cursor-not-allowed"
                }`}
              >
                <Check className="w-4 h-4" /> Approve & Take Case
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
