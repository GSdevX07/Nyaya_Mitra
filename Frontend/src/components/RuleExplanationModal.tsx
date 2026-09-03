import {
  X,
  Scale,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Calculator,
} from "lucide-react";
import type { RuleExplanationData } from "@/lib/api";

interface RuleExplanationModalProps {
  isOpen: boolean;
  onClose: () => void;
  explanation?: RuleExplanationData;
  caseId?: string;
  accusedName?: string;
}

export function RuleExplanationModal({
  isOpen,
  onClose,
  explanation,
  caseId,
  accusedName,
}: RuleExplanationModalProps) {
  if (!isOpen || !explanation) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "THRESHOLD_REACHED":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-500 border border-emerald-500/30 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> Threshold Reached
          </span>
        );
      case "THRESHOLD_NOT_REACHED":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/30 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" /> Threshold Not Reached
          </span>
        );
      case "POTENTIALLY_APPLICABLE":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" /> Approaching / Records Required
          </span>
        );
      case "EXCLUDED":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-destructive/10 text-destructive border border-destructive/30 flex items-center gap-1.5">
            <XCircle className="w-3.5 h-3.5" /> Statutory Exclusion
          </span>
        );
      case "INSUFFICIENT_DATA":
        return (
          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1.5">
            <HelpCircle className="w-3.5 h-3.5" /> Missing Essential Data
          </span>
        );
      case "MANUAL_REVIEW":
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-purple-500/10 text-purple-400 border border-purple-500/30 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" /> Manual Review Required
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-card border border-border rounded-xl shadow-2xl p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between pb-4 border-b border-border">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <span className="p-2 rounded bg-primary/10 text-primary">
                <Scale className="w-5 h-5" />
              </span>
              <div>
                <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
                  Statutory Rule Calculation & Explanation
                </h2>
                <p className="text-xs text-muted-foreground font-mono">
                  {explanation.rule_id} • {explanation.rule_version}
                </p>
              </div>
            </div>
            {caseId && (
              <div className="text-sm text-muted-foreground pt-1">
                Case: <span className="font-semibold text-foreground font-mono">{caseId}</span>
                {accusedName && ` (${accusedName})`}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Machine Status & Explanation Banner */}
        <div className="p-4 rounded-lg bg-secondary/40 border border-border space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Deterministic Machine Status
            </span>
            {getStatusBadge(explanation.machine_status)}
          </div>
          <p className="text-sm font-medium text-foreground leading-relaxed">
            {explanation.explanation_text}
          </p>
          {explanation.manual_review_reason && (
            <div className="text-xs text-amber-400 bg-amber-500/10 p-2.5 rounded border border-amber-500/20 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                <strong>Reason for Human Review:</strong> {explanation.manual_review_reason}
              </span>
            </div>
          )}
        </div>

        {/* Conflicting or Missing Records Warning */}
        {explanation.missing_or_conflicting_inputs && explanation.missing_or_conflicting_inputs.length > 0 && (
          <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 space-y-2">
            <h4 className="text-xs font-bold text-destructive uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4" /> Data Quality & Reconciliation Notice
            </h4>
            <div className="space-y-1.5 text-xs text-foreground">
              {explanation.missing_or_conflicting_inputs.map((m, idx) => (
                <div key={idx} className="p-2 rounded bg-destructive/5 border border-destructive/20">
                  <span className="font-semibold text-destructive">{m.type}: </span>
                  {m.reason || m.details || m.field}
                  {m.source_a && m.source_b && (
                    <div className="text-[11px] text-muted-foreground mt-1">
                      Source A: {m.source_a} | Source B: {m.source_b}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Deterministic Calculation Card */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Calculator className="w-4 h-4 text-primary" /> Machine Calculation & Statutory Threshold
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 rounded bg-secondary/30 border border-border">
              <div className="text-[10px] text-muted-foreground uppercase">Statutory Fraction</div>
              <div className="text-base font-bold text-foreground font-mono">
                {explanation.calculation_performed?.fraction || "N/A"}
              </div>
            </div>
            <div className="p-3 rounded bg-secondary/30 border border-border">
              <div className="text-[10px] text-muted-foreground uppercase">Required Threshold</div>
              <div className="text-base font-bold text-primary font-mono">
                {explanation.calculation_performed?.threshold_days ?? "N/A"} days
              </div>
            </div>
            <div className="p-3 rounded bg-secondary/30 border border-border">
              <div className="text-[10px] text-muted-foreground uppercase">Countable Detention</div>
              <div className="text-base font-bold text-emerald-400 font-mono">
                {explanation.calculation_performed?.countable_custody_days ?? "N/A"} days
              </div>
            </div>
            <div className="p-3 rounded bg-secondary/30 border border-border">
              <div className="text-[10px] text-muted-foreground uppercase">Days Overdue</div>
              <div className="text-base font-bold text-foreground font-mono">
                {explanation.calculation_performed?.days_overdue ?? 0} days
              </div>
            </div>
          </div>
          {explanation.calculation_performed?.formula && (
            <div className="text-xs text-muted-foreground bg-secondary/20 p-2.5 rounded font-mono border border-border">
              Formula: {explanation.calculation_performed.formula} (using {explanation.calculation_performed.rounding_rule || "math.ceil"} statutory rounding)
            </div>
          )}
        </div>

        {/* Evaluated Conditions */}
        {explanation.conditions_evaluated && explanation.conditions_evaluated.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-primary" /> Statutory Conditions Evaluated
            </h3>
            <div className="space-y-2">
              {explanation.conditions_evaluated.map((c, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded bg-card border border-border flex items-start gap-3"
                >
                  <div className="mt-0.5">
                    {c.satisfied === true ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : c.satisfied === false ? (
                      <XCircle className="w-4 h-4 text-destructive" />
                    ) : (
                      <HelpCircle className="w-4 h-4 text-amber-500" />
                    )}
                  </div>
                  <div className="space-y-0.5 text-xs flex-1">
                    <div className="font-semibold text-foreground">{c.condition_name}</div>
                    <div className="text-muted-foreground">{c.reason}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Exclusions and Provisos */}
        {explanation.exclusions_provisos_evaluated && explanation.exclusions_provisos_evaluated.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-primary" /> Statutory Provisos & Exclusions
            </h3>
            <div className="space-y-2">
              {explanation.exclusions_provisos_evaluated.map((p, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded border text-xs ${
                    p.applies
                      ? "bg-destructive/10 border-destructive/30"
                      : "bg-secondary/20 border-border"
                  }`}
                >
                  <div className="font-semibold text-foreground flex items-center justify-between">
                    <span>{p.proviso_name}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                      p.applies ? "bg-destructive/20 text-destructive" : "bg-secondary text-muted-foreground"
                    }`}>
                      {p.applies ? "Applies (Exclusion)" : "Does Not Apply"}
                    </span>
                  </div>
                  {p.statutory_text && (
                    <p className="text-muted-foreground mt-1 italic font-serif text-[11px]">
                      "{p.statutory_text}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Institutional Non-Judicial Disclaimer */}
        <div className="p-3 rounded bg-muted/20 border border-border text-[11px] text-muted-foreground italic">
          {explanation.disclaimer}
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-secondary text-secondary-foreground text-xs font-medium rounded-lg hover:bg-secondary/80 transition-colors"
          >
            Close Explanation
          </button>
        </div>
      </div>
    </div>
  );
}
