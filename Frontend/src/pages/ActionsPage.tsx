import { useState, useEffect } from "react";
import { Play, Clock, ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";
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
}

export function ActionsPage() {
  const { hasRole, user } = useAuth();
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggeringId, setTriggeringId] = useState<string | null>(null);
  const [executedIds, setExecutedIds] = useState<Set<string>>(new Set());

  const isDlsa = user?.role === "DLSA_OFFICER";
  const isSupervisor = user?.role === "SUPERVISING_LEGAL_OFFICER";
  const isAdvocate = user?.role === "DEFENSE_ADVOCATE" || user?.role === "CONTROLLED_EXTERNAL_ADVOCATE";

  // DLSA officers may dispatch institutional and procedural notices only.
  const DLSA_PERMITTED_ACTION_TYPES = [
    "MISSING_DOCUMENT",
    "DOCUMENT_REQUEST",
    "LEGAL_AID",
    "DLSA",
    "SECTION_479",
    "REMAND",
    "PANEL",
    "FOLLOWUP",
    "INSTITUTIONAL",
    "ADVOCATE_ASSIGN",
    "NOTIFY",
  ];

  // Supervising Legal Officers execute supervisory escalation, compliance review,
  // approval queue, and institutional follow-up actions.
  // They may NOT execute direct judicial determinations, court filing, or police/jail custody tasks.
  const SUPERVISOR_PERMITTED_ACTION_TYPES = [
    "ESCALATION",
    "REVIEW",
    "COMPLIANCE",
    "CORRECTION",
    "APPROVAL",
    "SECTION_479",
    "LEGAL_AID",
    "MISSING_DOCUMENT",
    "DOCUMENT_REQUEST",
    "PANEL",
    "NOTIFY",
    "FOLLOWUP",
    "INSTITUTIONAL",
  ];

  // Defense advocates may dispatch counsel actions related to their assigned cases:
  // bail applications, document requests, legal briefs, and petition drafting.
  const ADVOCATE_PERMITTED_ACTION_TYPES = [
    "BAIL",
    "DOCS",
    "REVIEW",
    "CORRECTION",
    "LEGAL_NOTE",
    "PETITION",
  ];

  const canExecute = hasRole("DLSA_OFFICER", "SUPERVISING_LEGAL_OFFICER", "PLATFORM_ADMIN", "DEFENSE_ADVOCATE");

  // Allow dispatch for permitted action types per role
  const canDispatchAction = (act: ActionItem): boolean => {
    if (!canExecute) return false;
    if (isDlsa) {
      return DLSA_PERMITTED_ACTION_TYPES.some((allowed) =>
        act.action_type.toUpperCase().includes(allowed) ||
        act.description.toUpperCase().includes(allowed)
      );
    }
    if (isSupervisor) {
      return SUPERVISOR_PERMITTED_ACTION_TYPES.some((allowed) =>
        act.action_type.toUpperCase().includes(allowed) ||
        act.description.toUpperCase().includes(allowed)
      );
    }
    if (isAdvocate) {
      return ADVOCATE_PERMITTED_ACTION_TYPES.some((allowed) =>
        act.action_type.toUpperCase().includes(allowed) ||
        act.description.toUpperCase().includes(allowed)
      );
    }
    return true; // Platform Admins
  };

  const loadActions = async () => {
    setLoading(true);
    const data = await fetchActions();
    setActions(data);
    setLoading(false);
  };

  useEffect(() => {
    loadActions();
  }, []);

  const handleTrigger = async (id: string) => {
    if (!canExecute) return;
    setTriggeringId(id);
    try {
      await triggerAction(id);
      setExecutedIds(prev => new Set(prev).add(id));
    } catch (err) {
      console.error(err);
    } finally {
      setTriggeringId(null);
    }
  };

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300 max-w-7xl mx-auto">
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

      {/* Action Cards */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Fetching automated agent queue from backend...
        </div>
      ) : (
        <div className="space-y-4">
          {actions.map(act => (
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

                {canDispatchAction(act) ? (
                  <button
                    onClick={() => handleTrigger(act.id)}
                    disabled={triggeringId === act.id || executedIds.has(act.id)}
                    className={`px-4 py-2 font-semibold rounded text-xs flex items-center gap-2 shadow-md transition-all ${
                      executedIds.has(act.id)
                        ? "bg-secondary text-primary cursor-not-allowed opacity-80"
                        : "bg-primary text-primary-foreground hover:opacity-90 shadow-primary/20"
                    }`}
                  >
                    {executedIds.has(act.id) ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : triggeringId === act.id ? (
                      <Clock className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    {executedIds.has(act.id)
                      ? "Dispatched"
                      : triggeringId === act.id
                      ? "Dispatching..."
                      : "Dispatch Action"}
                  </button>
                ) : isAdvocate ? (
                  <span
                    className="px-3 py-1.5 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs font-mono font-bold rounded border border-amber-500/30 flex items-center gap-1.5"
                    title="This action requires institutional or supervisory authority"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" /> Institutional Action Only
                  </span>
                ) : isSupervisor ? (
                  <span
                    className="px-3 py-1.5 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs font-mono font-bold rounded border border-amber-500/30 flex items-center gap-1.5"
                    title="This action type requires Court or Originating Institutional authority"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" /> Judicial/Originating Auth Required
                  </span>
                ) : isDlsa ? (
                  <span
                    className="px-3 py-1.5 bg-amber-500/10 text-amber-700 dark:text-amber-400 text-xs font-mono font-bold rounded border border-amber-500/30 flex items-center gap-1.5"
                    title="This action type requires Supervisory Legal Officer or Court authorization"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" /> Supervisor Auth Required
                  </span>
                ) : (
                  <span className="px-3 py-1.5 bg-muted text-muted-foreground text-xs font-mono font-bold rounded border border-border flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" /> Read-Only View
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
