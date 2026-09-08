import { useState, useEffect } from "react";
import { Play, Clock, ArrowRight, CheckCircle2, ShieldCheck, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchActions, triggerAction } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface ActionItem {
  id: string;
  case_id: string;
  action_type: string;
  priority: string;
  status: string;
  description: string;
  created_at: string;
  is_dispatched?: boolean;
  dispatched_at?: string | null;
  dispatched_by?: string | null;
  dispatched_role?: string | null;
}

export function ActionsPage() {
  const { user, can } = useAuth();
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggeringId, setTriggeringId] = useState<string | null>(null);
  const [executedIds, setExecutedIds] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<"ALL" | "HIGH" | "MEDIUM">("ALL");
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const isDlsa = user?.role === "DLSA_OFFICER";
  const isSupervisor = user?.role === "SUPERVISING_LEGAL_OFFICER";
  const isAdvocate = user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE";
  const isPolice = user?.role === "POLICE_OFFICER";
  const isJail = user?.role === "JAIL_OFFICER";
  const isAdmin = user?.role === "PLATFORM_ADMIN";
  const isGov = user?.role === "GOV_ADMIN";
  const isAuditor = user?.role === "READ_ONLY_AUDITOR";

  const canExecute = can("ACTION_QUEUE") || can("ACTION_EXECUTE");

  // Determine if current user can execute the action
  const canDispatchAction = (act: ActionItem): boolean => {
    if (!canExecute) return false;
    const upperId = (act.id || "").toUpperCase();
    const upperType = (act.action_type || "").toUpperCase();
    const upperDesc = (act.description || "").toUpperCase();

    const isBail = upperId.includes("-BAIL") || upperType.includes("BAIL") || upperType.includes("479") || upperType.includes("PETITION");
    const isDocs = upperId.includes("-DOCS") || upperType.includes("DOC") || upperDesc.includes("DOCUMENT") || upperType.includes("REQUISITION");
    const isReview = upperId.includes("-REVIEW") || upperType.includes("REVIEW");

    if (isDlsa) {
      // DLSA officers have authority over Document Requisitions, Section 479 Petitions, and Review Referrals
      return isBail || isDocs || isReview;
    }
    if (isSupervisor) {
      // Supervising legal officers have supervisory authority over Review, Bail Approval, and Directives
      return isBail || isDocs || isReview;
    }
    if (isAdvocate) {
      // Advocates can prepare bail petitions, request documents, and submit clarifications for assigned cases
      return isBail || isDocs || isReview;
    }
    return false;
  };

  const loadActions = async () => {
    setLoading(true);
    try {
      const data = await fetchActions();
      setActions(data || []);
    } catch (err: any) {
      console.error(err);
      setFeedbackMsg({ type: "error", text: "Failed to load dispatch queue: " + (err.message || err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActions();
  }, []);

  const handleTrigger = async (id: string) => {
    if (!canExecute) return;
    setTriggeringId(id);
    setFeedbackMsg(null);
    try {
      const res = await triggerAction(id);
      setExecutedIds(prev => new Set(prev).add(id));
      setActions(prev =>
        prev.map(act =>
          act.id === id ? { ...act, is_dispatched: true, status: "Dispatched" } : act
        )
      );
      setFeedbackMsg({
        type: "success",
        text: res?.message || `Action ${id} successfully dispatched and recorded in the audit trail.`,
      });
    } catch (err: any) {
      setFeedbackMsg({
        type: "error",
        text: `Action dispatch failed: ${err.message || err}`,
      });
    } finally {
      setTriggeringId(null);
    }
  };

  const getButtonText = (act: ActionItem) => {
    if (triggeringId === act.id) return "Processing...";
    const upperId = (act.id || "").toUpperCase();
    if (upperId.includes("-BAIL")) {
      if (isDlsa) return "Generate Section 479 Draft";
      if (isSupervisor) return "Authorize Petition Filing";
      if (isAdvocate) return "Submit Counsel Motion";
    }
    if (upperId.includes("-DOCS")) {
      if (isDlsa) return "Queue Notice / Request";
      if (isSupervisor) return "Issue Supervisory Directive";
      if (isAdvocate) return "Requisition Case Records";
    }
    if (upperId.includes("-REVIEW")) {
      if (isSupervisor) return "Conduct Supervisory Review";
      if (isDlsa) return "Refer for Legal Review";
      if (isAdvocate) return "Request Legal Clarification";
    }
    return isDlsa ? "Queue Notice / Request" : isAdvocate ? "Submit Counsel Action" : "Execute Institutional Action";
  };

  const filteredActions = actions.filter((act) => {
    const matchesSearch =
      !searchQuery.trim() ||
      act.case_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      act.action_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      act.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPriority =
      priorityFilter === "ALL" || act.priority.toUpperCase() === priorityFilter;
    return matchesSearch && matchesPriority;
  });

  return (
    <div className="p-4 md:p-8 w-full space-y-6 animate-in fade-in duration-300 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-sm text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              Legal Services Dispatch Queue
            </span>
            <span className="text-xs text-muted-foreground font-mono">Status Tracking & Procedural Actions</span>
          </div>
          <h1 className="text-3xl font-bold font-serif tracking-tight text-foreground">
            Legal Actions & Dispatch Desk
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Review and dispatch automated Section 479 draft reminders, DLSA requisitions, and missing document notices.
          </p>
        </div>
      </div>

      {feedbackMsg && (
        <div
          className={`p-4 rounded-xl text-xs flex items-center justify-between font-mono shadow-sm ${
            feedbackMsg.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400"
              : "bg-destructive/10 border border-destructive/30 text-destructive"
          }`}
        >
          <span className="flex items-center gap-2">
            {feedbackMsg.type === "success" ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : null}
            {feedbackMsg.text}
          </span>
          <button
            onClick={() => setFeedbackMsg(null)}
            className="text-muted-foreground hover:text-foreground text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {(["ALL", "HIGH", "MEDIUM"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-3 py-1.5 rounded text-xs font-mono font-bold uppercase transition-colors ${
                priorityFilter === p
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground border border-border"
              }`}
            >
              {p} Priority ({p === "ALL" ? actions.length : actions.filter(a => a.priority.toUpperCase() === p).length})
            </button>
          ))}
        </div>
        <input
          type="text"
          placeholder="Filter by case reference or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full sm:w-72 px-3.5 py-1.5 bg-card border border-border rounded text-xs text-foreground focus:outline-none focus:border-primary"
        />
      </div>

      {/* Action Cards */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse font-mono text-xs">
          Fetching automated agent queue from backend...
        </div>
      ) : filteredActions.length === 0 ? (
        <div className="p-16 text-center bg-card border border-border rounded-xl text-muted-foreground font-mono text-xs space-y-2">
          <p className="text-foreground font-bold text-sm">No Pending Actions Found</p>
          <p>All eligible case petitions and document requisitions are currently up to date.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredActions.map((act) => {
            const isAlreadyDispatched =
              act.is_dispatched ||
              executedIds.has(act.id) ||
              act.status === "Dispatched" ||
              act.status.includes("Draft Generated") ||
              act.status.includes("Supervisory Review");

            return (
              <div
                key={act.id}
                className="p-6 rounded bg-card shadow-sm border border-border hover:border-accent/40 transition-all backdrop-blur-md flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-semibold text-accent">{act.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent/10 text-accent border border-accent/20">
                      {act.priority} PRIORITY
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">Case: {act.case_id}</span>
                    {act.dispatched_by && (
                      <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                        Dispatched by {act.dispatched_by}
                      </span>
                    )}
                  </div>
                  <h3 className="text-base font-semibold text-primary">{act.action_type}</h3>
                  <p className="text-xs text-muted-foreground">{act.description}</p>
                </div>

                <div className="flex items-center gap-4 shrink-0 border-t md:border-t-0 border-border pt-4 md:pt-0">
                  <Link
                    to={`/case/${act.case_id}`}
                    className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
                  >
                    View Case <ArrowRight className="w-3 h-3" />
                  </Link>

                  {isAlreadyDispatched ? (
                    <div className="flex items-center gap-1.5 px-3.5 py-2 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      <span>{act.status}</span>
                    </div>
                  ) : canDispatchAction(act) ? (
                    <button
                      onClick={() => handleTrigger(act.id)}
                      disabled={triggeringId === act.id}
                      className="px-4 py-2 font-semibold rounded text-xs flex items-center gap-2 shadow-md transition-all bg-primary text-primary-foreground hover:opacity-90 shadow-primary/20"
                    >
                      {triggeringId === act.id ? (
                        <Clock className="w-4 h-4 animate-spin" />
                      ) : (
                        <Play className="w-4 h-4" />
                      )}
                      {getButtonText(act)}
                    </button>
                  ) : isPolice ? (
                    <Link
                      to="/police"
                      className="px-3.5 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 text-xs font-semibold rounded border border-blue-500/30 flex items-center gap-1.5 transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5" /> Fulfill at Police Desk
                    </Link>
                  ) : isJail ? (
                    <Link
                      to="/jail"
                      className="px-3.5 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-400 text-xs font-semibold rounded border border-amber-500/30 flex items-center gap-1.5 transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5" /> Fulfill at Custody Desk
                    </Link>
                  ) : isAdmin ? (
                    <span className="px-3 py-1.5 bg-secondary text-foreground text-xs font-mono font-medium rounded border border-border flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Technical System Oversight
                    </span>
                  ) : isGov ? (
                    <span className="px-3 py-1.5 bg-secondary text-foreground text-xs font-mono font-medium rounded border border-border flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> State Legal Authority Oversight
                    </span>
                  ) : isAuditor ? (
                    <span className="px-3 py-1.5 bg-muted text-muted-foreground text-xs font-mono font-bold rounded border border-border flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5" /> Auditor Read-Only Ledger
                    </span>
                  ) : (
                    <span className="px-3 py-1.5 bg-muted text-muted-foreground text-xs font-mono font-bold rounded border border-border flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5" /> Read-Only View
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
