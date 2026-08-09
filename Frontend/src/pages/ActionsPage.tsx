import { useState, useEffect } from "react";
import { Play, Clock, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchActions, triggerAction } from "@/lib/api";

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
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggeringId, setTriggeringId] = useState<string | null>(null);

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
    setTriggeringId(id);
    try {
      await triggerAction(id);
      await loadActions();
    } catch (err) {
      console.error(err);
    } finally {
      setTriggeringId(null);
    }
  };

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Agentic Automation Queue
            </span>
            <span className="text-xs text-muted-foreground font-mono">Status Tracking & Legal Dispatch</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Automated Legal Actions</h1>
          <p className="text-sm text-muted-foreground mt-1">
            One-click execution queue for auto-drafted BNSS 479 petitions, DLSA reminders, and missing document notices.
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
              className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 hover:border-accent/40 transition-all backdrop-blur-md flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-semibold text-accent">{act.id}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-accent/10 text-accent border border-accent/20">
                    {act.priority} PRIORITY
                  </span>
                  <span className="text-xs text-muted-foreground font-mono">Case: {act.case_id}</span>
                </div>
                <h3 className="text-base font-semibold text-white">{act.action_type}</h3>
                <p className="text-xs text-muted-foreground">{act.description}</p>
              </div>

              <div className="flex items-center gap-4 shrink-0 border-t md:border-t-0 border-white/5 pt-4 md:pt-0">
                <Link
                  to={`/case/${act.case_id}`}
                  className="text-xs font-medium text-muted-foreground hover:text-white transition-colors flex items-center gap-1"
                >
                  View Case <ArrowRight className="w-3 h-3" />
                </Link>

                <button
                  onClick={() => handleTrigger(act.id)}
                  disabled={triggeringId === act.id}
                  className="px-4 py-2 bg-accent text-accent-foreground font-semibold rounded-xl text-xs hover:opacity-90 transition-opacity flex items-center gap-2 shadow-md shadow-accent/20"
                >
                  {triggeringId === act.id ? (
                    <Clock className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  {triggeringId === act.id ? "Executing..." : "Execute Action"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
