import { useState, useEffect } from "react";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import {
  AlertCircle, FileText, CheckCircle2, Activity,
  Scale, Loader2, User, MapPin, Languages,
  ShieldCheck, XCircle, ScrollText, Bot, Gavel
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

// ── Type definitions ──────────────────────────────────────────────────────────

interface UrgencyFlags {
  age: number;
  health_flag: boolean;
  repeat_offender: boolean;
}

interface CaseRecord {
  case_id: string;
  name: string;
  offense_sections: string[];
  arrest_date: string;
  custody_days: number;
  max_sentence_days_for_offense: number;
  required_docs: string[];
  present_docs: string[];
  urgency_flags: UrgencyFlags;
  jail_location: string;
  preferred_language: string;
  prior_bail_orders: string[];
}

interface QueueEntry {
  case: CaseRecord;
  days_overdue: number;
  urgency_score: number;
}

interface EligibilityResult {
  eligible: boolean;
  threshold_fraction: number;
  required_custody_days: number;
  custody_days_served: number;
  days_overdue: number;
  legal_basis: string;
}

interface CompletenessResult {
  is_complete: boolean;
  missing_docs: string[];
  message: string;
}

interface LogEntry {
  timestamp: string;
  agent: string;
  status: string;
  detail: string;
}

interface CaseDetail {
  case_id: string;
  eligibility: EligibilityResult;
  completeness: CompletenessResult;
  urgency_score: number;
  notification: { alert_level: string; dispatched_message: string };
  retrieval: { retrieved_statutes: string };
  draft: { drafted_document: string };
  explanation: { explanation: string; language: string };
  status_tracking: { current_status: string; last_updated: string };
  draft_ready: boolean;
  agent_activity_log: LogEntry[];
}

// ── Animation variants ────────────────────────────────────────────────────────

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 280, damping: 24 } },
};

const stagger: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.07 } },
};

// ── Status badge colours ──────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  RUNNING:  "bg-blue-500/15 text-blue-400 border-blue-500/30",
  DONE:     "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  SKIPPED:  "bg-white/5 text-muted-foreground border-white/10",
};

const COURT_STATUS_COLORS: Record<string, string> = {
  "Pending Review":     "text-amber-400",
  "Filed":              "text-blue-400",
  "Hearing Scheduled":  "text-purple-400",
  "Order Passed":       "text-emerald-400",
  "Released":           "text-emerald-500",
};

import { InkStamp } from "@/components/ui/InkStamp";

// ── Subcomponents ─────────────────────────────────────────────────────────────

function QueueCard({
  entry,
  isSelected,
  isLoading,
  onClick,
}: {
  entry: QueueEntry;
  isSelected: boolean;
  isLoading: boolean;
  onClick: () => void;
}) {
  const { case: c, days_overdue, urgency_score } = entry;
  const isHigh = urgency_score > 100;
  // Urgency thread opacity scaled by overdue days severity
  const threadOpacity = Math.min(1, 0.4 + (days_overdue / 300) * 0.6);

  return (
    <motion.div variants={fadeUp}>
      <Card
        onClick={onClick}
        className={`cursor-pointer transition-all duration-200 border relative overflow-hidden dog-ear-fold
          ${isSelected
            ? "border-amber-500/50 bg-[#141B26] shadow-lg shadow-black/40"
            : "border-white/10 bg-[#0F141C]/80 hover:border-white/20 hover:bg-[#141A24]"
          }`}
      >
        {/* Red urgency thread on left edge */}
        <div
          className="absolute left-0 top-0 bottom-0 w-[3px] bg-[#B4453A] transition-opacity"
          style={{ opacity: threadOpacity }}
        />

        <CardContent className="p-4 pl-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="text-xs font-mono text-muted-foreground font-semibold tracking-wide">
                  {c.case_id}
                </span>
                {isHigh && (
                  <InkStamp text="HIGH PRIORITY" variant="red" />
                )}
              </div>
              <p className="text-base font-serif font-semibold text-white tracking-tight truncate">
                {c.name}
              </p>
              <p className="text-xs text-muted-foreground font-mono mt-0.5">
                IPC {c.offense_sections.join(", ")}
              </p>
            </div>
            <div className="text-right shrink-0">
              <InkStamp
                text={`${days_overdue}D OVERDUE`}
                variant={days_overdue > 100 ? "red" : "ochre"}
                doubleRing={isHigh}
              />
              <div className="text-[10px] text-muted-foreground font-mono mt-1">
                Score: {urgency_score}
              </div>
            </div>
          </div>

          {/* flags row */}
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {c.urgency_flags.health_flag && (
              <InkStamp text="HEALTH FLAG" variant="red" />
            )}
            {c.urgency_flags.age > 60 && (
              <InkStamp text={`ELDERLY (${c.urgency_flags.age})`} variant="ochre" />
            )}
            {!c.urgency_flags.repeat_offender && (
              <InkStamp text="FIRST-TIME" variant="sage" />
            )}
          </div>
        </CardContent>

        {isSelected && isLoading && (
          <div className="absolute inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center">
            <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
          </div>
        )}
      </Card>
    </motion.div>
  );
}

function OverviewTab({ detail }: { detail: CaseDetail }) {
  const { eligibility: elig, completeness: comp, status_tracking: st, notification: notif } = detail;

  return (
    <div className="space-y-4">
      {/* Eligibility */}
      <Card className="border-white/8 bg-white/[0.02]">
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <Scale className="w-4 h-4 text-blue-400" /> Eligibility — Section 479 BNSS
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-2">
          <div className="flex items-center gap-2">
            {elig.eligible
              ? <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              : <XCircle className="w-5 h-5 text-red-400" />}
            <span className={`font-semibold ${elig.eligible ? "text-emerald-400" : "text-red-400"}`}>
              {elig.eligible ? "ELIGIBLE" : "NOT YET ELIGIBLE"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{elig.legal_basis}</p>
          <div className="grid grid-cols-3 gap-2 mt-2">
            {[
              { label: "Days Served", value: elig.custody_days_served },
              { label: "Required", value: elig.required_custody_days },
              { label: "Overdue", value: elig.days_overdue, highlight: elig.days_overdue > 0 },
            ].map(({ label, value, highlight }) => (
              <div key={label} className="p-2 rounded-lg bg-white/[0.03] text-center">
                <div className={`text-lg font-bold ${highlight ? "text-red-400" : "text-white"}`}>{value}</div>
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Completeness */}
      <Card className="border-white/8 bg-white/[0.02]">
        <CardHeader className="pb-2 pt-4 px-4">
          <CardTitle className="text-sm flex items-center gap-2">
            <FileText className="w-4 h-4 text-amber-400" /> Document Completeness
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {comp.is_complete ? (
            <div className="flex items-center gap-2 text-emerald-400 text-sm">
              <CheckCircle2 className="w-4 h-4" /> All required documents are present.
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-amber-400 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" /> Missing documents:
              </p>
              <ul className="space-y-1">
                {comp.missing_docs.map((doc) => (
                  <li key={doc} className="text-xs px-3 py-1.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300 font-mono">
                    {doc}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Status & Notification */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="border-white/8 bg-white/[0.02]">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1"><Gavel className="w-3 h-3" /> Court Status</div>
            <div className={`font-semibold text-sm ${COURT_STATUS_COLORS[st.current_status] ?? "text-white"}`}>
              {st.current_status}
            </div>
            <div className="text-[10px] text-muted-foreground mt-1">
              {new Date(st.last_updated).toLocaleTimeString()}
            </div>
          </CardContent>
        </Card>
        <Card className="border-white/8 bg-white/[0.02]">
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Alert Level</div>
            <Badge
              variant={notif.alert_level === "HIGH" ? "destructive" : "secondary"}
              className="text-xs"
            >
              {notif.alert_level}
            </Badge>
            <div className="text-[10px] text-muted-foreground mt-1">Urgency: {detail.urgency_score}</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DraftTab({ detail, onApprove, approving }: { detail: CaseDetail; onApprove: () => void; approving: boolean }) {
  return (
    <div className="space-y-4">
      {detail.draft_ready ? (
        <>
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/8">
            <pre className="whitespace-pre-wrap text-sm text-white/80 font-mono leading-relaxed">
              {detail.draft.drafted_document}
            </pre>
          </div>
          <button
            onClick={onApprove}
            disabled={approving}
            className="w-full py-3 px-6 rounded-xl bg-emerald-500/90 hover:bg-emerald-500 text-white font-semibold text-sm transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {approving
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Filing...</>
              : <><ShieldCheck className="w-4 h-4" /> Approve &amp; File</>
            }
          </button>
        </>
      ) : (
        <div className="p-8 text-center rounded-xl border border-white/8 bg-white/[0.02]">
          <XCircle className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">
            Draft not available. Case must be <span className="text-white">eligible</span> and{" "}
            <span className="text-white">documents complete</span> before a bail application can be drafted.
          </p>
        </div>
      )}
    </div>
  );
}

function ExplanationTab({ detail }: { detail: CaseDetail }) {
  const { explanation } = detail;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Languages className="w-3.5 h-3.5" />
        Language code: <span className="text-white font-mono">{explanation.language}</span>
      </div>
      <div className="p-5 rounded-xl bg-white/[0.02] border border-white/8">
        <p className="text-white/90 leading-relaxed text-sm whitespace-pre-wrap">
          {explanation.explanation}
        </p>
      </div>
      <p className="text-xs text-muted-foreground">
        This explanation is generated in the prisoner's preferred language and is suitable for reading aloud to family members.
      </p>
    </div>
  );
}

function AgentLogTab({ log }: { log: LogEntry[] }) {
  return (
    <div className="space-y-2">
      {log.map((entry, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.04 }}
          className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/5"
        >
          <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border font-mono uppercase tracking-wider ${STATUS_COLORS[entry.status] ?? "bg-white/5 text-white border-white/10"}`}>
            {entry.status}
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-white">{entry.agent}</span>
              <span className="text-[10px] text-muted-foreground font-mono shrink-0">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
            </div>
            {entry.detail && (
              <p className="text-xs text-muted-foreground mt-0.5 truncate">{entry.detail}</p>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export function CommandCenter() {
  const [cases, setCases] = useState<QueueEntry[]>([]);
  const [selectedCase, setSelectedCase] = useState<CaseDetail | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [queueLoading, setQueueLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [approveMsg, setApproveMsg] = useState<string | null>(null);

  // Fetch prioritized queue on mount
  useEffect(() => {
    setQueueLoading(true);
    fetch("http://127.0.0.1:8000/cases")
      .then((r) => r.json())
      .then((data) => setCases(data))
      .catch((e) => console.error("Failed to fetch queue:", e))
      .finally(() => setQueueLoading(false));
  }, []);

  // Fetch full case detail when a queue card is clicked
  const handleSelectCase = (caseId: string) => {
    setSelectedId(caseId);
    setSelectedCase(null);
    setApproveMsg(null);
    setIsLoading(true);
    fetch(`http://127.0.0.1:8000/cases/${caseId}`)
      .then((r) => r.json())
      .then((data) => setSelectedCase(data))
      .catch((e) => console.error("Failed to fetch case detail:", e))
      .finally(() => setIsLoading(false));
  };

  // Human-lawyer approval gate
  const handleApprove = async () => {
    if (!selectedId) return;
    setApproving(true);
    setApproveMsg(null);
    try {
      const r = await fetch(`http://127.0.0.1:8000/cases/${selectedId}/approve`, { method: "POST" });
      const data = await r.json();
      setApproveMsg(data.status ?? "Approved.");
    } catch {
      setApproveMsg("Error: Could not reach the server.");
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="p-4 md:p-6 w-full h-full">
      <motion.div initial="hidden" animate="show" variants={stagger} className="space-y-6">

        {/* Header */}
        <motion.div variants={fadeUp} className="space-y-1">
          <h1 className="text-3xl font-serif font-semibold tracking-tight text-white">Lawyer Command Centre</h1>
          <p className="text-muted-foreground text-sm font-sans">
            Prioritized undertrial queue — powered by the Nyaya Mitra agent pipeline.
          </p>
        </motion.div>

        {/* Two-column layout */}
        <motion.div variants={fadeUp} className="grid grid-cols-1 md:grid-cols-3 gap-6 min-h-[calc(100vh-12rem)]">

          {/* ── LEFT: Prioritized Queue ──────────────────────────────────── */}
          <div className="md:col-span-1 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5" /> Prioritized Queue
              </h2>
              {!queueLoading && (
                <span className="text-xs text-muted-foreground">{cases.length} cases</span>
              )}
            </div>

            {queueLoading ? (
              <div className="flex-1 flex items-center justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <motion.div variants={stagger} className="flex flex-col gap-2 overflow-y-auto pr-1">
                {cases.map((entry) => (
                  <QueueCard
                    key={entry.case.case_id}
                    entry={entry}
                    isSelected={selectedId === entry.case.case_id}
                    isLoading={isLoading && selectedId === entry.case.case_id}
                    onClick={() => handleSelectCase(entry.case.case_id)}
                  />
                ))}
              </motion.div>
            )}
          </div>

          {/* ── RIGHT: Case Detail View ──────────────────────────────────── */}
          <div className="md:col-span-2">
            <AnimatePresence mode="wait">
              {!selectedId && !isLoading ? (
                <motion.div
                  key="placeholder"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full flex flex-col items-center justify-center text-center p-12 rounded-xl border border-dashed border-white/10 bg-white/[0.01]"
                >
                  <Scale className="w-10 h-10 text-muted-foreground/40 mb-4" />
                  <p className="text-muted-foreground text-sm max-w-xs">
                    Select a case from the queue to view the full agent pipeline report.
                  </p>
                </motion.div>
              ) : isLoading ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="h-full flex flex-col items-center justify-center gap-4 rounded-xl border border-white/8 bg-white/[0.02]"
                >
                  <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
                  <p className="text-muted-foreground text-sm">Running agent pipeline…</p>
                  <div className="flex flex-col gap-1.5 text-xs text-muted-foreground/60">
                    {["EligibilityAgent", "CompletenessAgent", "PrioritizationAgent", "DraftingAgent", "ExplainerAgent"].map((a) => (
                      <span key={a} className="flex items-center gap-1.5">
                        <Bot className="w-3 h-3" /> {a}
                      </span>
                    ))}
                  </div>
                </motion.div>
              ) : selectedCase ? (
                <motion.div
                  key={selectedCase.case_id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col gap-4"
                >
                  {/* Case header */}
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-sm text-muted-foreground">{selectedCase.case_id}</span>
                        <Badge variant={selectedCase.draft_ready ? "default" : "secondary"} className="text-[10px]">
                          {selectedCase.draft_ready ? "Draft Ready" : "Draft Pending"}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1"><User className="w-3 h-3" /> {cases.find(c => c.case.case_id === selectedCase.case_id)?.case.offense_sections.join(", ")}</span>
                        <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {cases.find(c => c.case.case_id === selectedCase.case_id)?.case.jail_location}</span>
                      </div>
                    </div>
                  </div>

                  {/* Approve success message */}
                  <AnimatePresence>
                    {approveMsg && (
                      <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center gap-2"
                      >
                        <ShieldCheck className="w-4 h-4 shrink-0" /> {approveMsg}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Tabbed detail */}
                  <Tabs defaultValue="overview" className="w-full">
                    <TabsList className="w-full grid grid-cols-4 bg-white/[0.04] border border-white/8">
                      <TabsTrigger value="overview" className="text-xs gap-1.5">
                        <Scale className="w-3.5 h-3.5" /> Overview
                      </TabsTrigger>
                      <TabsTrigger value="draft" className="text-xs gap-1.5">
                        <ScrollText className="w-3.5 h-3.5" /> Draft
                      </TabsTrigger>
                      <TabsTrigger value="family" className="text-xs gap-1.5">
                        <Languages className="w-3.5 h-3.5" /> Family
                      </TabsTrigger>
                      <TabsTrigger value="log" className="text-xs gap-1.5">
                        <Bot className="w-3.5 h-3.5" /> Agent Log
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="overview" className="mt-4">
                      <OverviewTab detail={selectedCase} />
                    </TabsContent>
                    <TabsContent value="draft" className="mt-4">
                      <DraftTab detail={selectedCase} onApprove={handleApprove} approving={approving} />
                    </TabsContent>
                    <TabsContent value="family" className="mt-4">
                      <ExplanationTab detail={selectedCase} />
                    </TabsContent>
                    <TabsContent value="log" className="mt-4">
                      <AgentLogTab log={selectedCase.agent_activity_log} />
                    </TabsContent>
                  </Tabs>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

        </motion.div>
      </motion.div>
    </div>
  );
}
