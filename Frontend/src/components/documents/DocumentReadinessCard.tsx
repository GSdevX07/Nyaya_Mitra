import React from "react";
import type { ReadinessReport } from "../../lib/api";
import { ShieldAlert, ShieldCheck, AlertCircle } from "lucide-react";

interface DocumentReadinessCardProps {
  readiness: ReadinessReport | null;
  loading?: boolean;
  onRefresh?: () => void;
}

const renderIssueText = (item: any): string => {
  if (item === null || item === undefined) return "";
  if (typeof item === "string") return item;
  if (typeof item === "object") {
    return item.message || item.detail || item.field || JSON.stringify(item);
  }
  return String(item);
};

export const DocumentReadinessCard: React.FC<DocumentReadinessCardProps> = ({
  readiness,
  loading = false,
  onRefresh,
}) => {
  if (!readiness) {
    return (
      <div className="rounded-sm border-2 border-border bg-card p-4 text-center">
        <p className="text-xs font-serif text-muted-foreground italic">
          Pre-approval readiness audit has not yet been executed for this draft.
        </p>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="mt-3 px-3 py-1.5 text-xs font-mono font-bold uppercase rounded-sm bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? "Auditing..." : "Run Pre-Approval Audit"}
          </button>
        )}
      </div>
    );
  }

  const blockingCount = readiness.blocking_issues?.length || 0;
  const isReady = (readiness.can_approve ?? (readiness as any).is_ready) && blockingCount === 0;

  return (
    <div
      className={`rounded-sm border-2 shadow-sm p-4 transition-all ${
        isReady
          ? "border-emerald-600/70 bg-emerald-500/5"
          : "border-destructive/70 bg-destructive/5"
      }`}
    >
      {/* Header Banner */}
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-2.5">
          {isReady ? (
            <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
          )}
          <div>
            <h4
              className={`text-sm font-serif font-bold uppercase tracking-wide ${
                isReady ? "text-emerald-800" : "text-destructive"
              }`}
            >
              {isReady
                ? "Pre-Approval Readiness Cleared"
                : "Approval Blocked: Statutory & Factual Discrepancies"}
            </h4>
            <p className="text-xs text-muted-foreground mt-0.5 font-serif">
              {isReady
                ? "All statutory thresholds, documentary prerequisites, and mandatory petition clauses verified."
                : `${blockingCount} blocking discrepancy(ies) preventing advocate sign-off.`}
            </p>
          </div>
        </div>

        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="text-xs font-mono font-bold uppercase px-2.5 py-1 rounded-sm bg-secondary hover:bg-muted text-foreground border border-border disabled:opacity-50 transition-colors"
          >
            {loading ? "Checking..." : "Re-Audit"}
          </button>
        )}
      </div>

      {/* Blocking Issues */}
      {blockingCount > 0 && (
        <div className="mt-3.5 space-y-1.5">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-destructive block flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Blocking Issues ({blockingCount})</span>
          </span>
          <div className="space-y-1.5">
            {readiness.blocking_issues.map((issue, idx) => (
              <div
                key={idx}
                className="flex items-start text-xs bg-destructive/10 border border-destructive/30 rounded-sm px-2.5 py-2 text-destructive font-mono"
              >
                <span className="font-bold mr-1.5">&bull;</span>
                <span className="leading-snug">{renderIssueText(issue)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unsupported Factual Claims */}
      {readiness.unsupported_factual_claims &&
        readiness.unsupported_factual_claims.length > 0 && (
          <div className="mt-3 space-y-1">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-amber-800 block">
              Unsupported Factual Assertions ({readiness.unsupported_factual_claims.length})
            </span>
            <div className="space-y-1">
              {readiness.unsupported_factual_claims.map((claim, idx) => (
                <div
                  key={idx}
                  className="text-xs bg-amber-500/10 border border-amber-600/30 rounded-sm px-2.5 py-1.5 text-amber-900 font-mono"
                >
                  {renderIssueText(claim)}
                </div>
              ))}
            </div>
          </div>
        )}

      {/* Missing Template Fields */}
      {readiness.missing_fields && readiness.missing_fields.length > 0 && (
        <div className="mt-3 space-y-1">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground block">
            Missing Mandatory Fields
          </span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {readiness.missing_fields.map((field, idx) => (
              <span
                key={idx}
                className="inline-block px-2 py-0.5 rounded-sm bg-secondary border border-border text-foreground text-xs font-mono font-bold"
              >
                {renderIssueText(field)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Warnings & Advisories */}
      {readiness.warnings && readiness.warnings.length > 0 && (
        <div className="mt-3 space-y-1">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground block">
            Advisories ({readiness.warnings.length})
          </span>
          <ul className="list-disc list-inside text-xs text-muted-foreground space-y-0.5 font-serif">
            {readiness.warnings.map((warn, idx) => (
              <li key={idx}>{renderIssueText(warn)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Audit timestamp footer */}
      {readiness.checked_at && (
        <div className="mt-3 pt-2 border-t border-border text-[10px] font-mono text-muted-foreground uppercase flex justify-between items-center">
          <span>Gating Rule: Section 479 Strict Verification</span>
          <span>Checked: {new Date(readiness.checked_at).toLocaleTimeString()}</span>
        </div>
      )}
    </div>
  );
};

export default DocumentReadinessCard;
