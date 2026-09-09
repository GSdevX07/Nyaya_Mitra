import React, { useState } from "react";
import type { DraftDiffResult } from "../../lib/api";

interface DocumentDiffViewerProps {
  diffData?: DraftDiffResult | null;
  leftTitle?: string;
  rightTitle?: string;
  originalText?: string;
  currentText?: string;
}

export const DocumentDiffViewer: React.FC<DocumentDiffViewerProps> = ({
  diffData,
  leftTitle = "Machine Original / Previous Version",
  rightTitle = "Working Human Draft / Current Version",
  originalText,
  currentText,
}) => {
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");

  // Fallback simple line diff if diffData is not provided from API
  const lines = React.useMemo(() => {
    if (diffData && diffData.diff_lines) {
      return diffData.diff_lines;
    }
    if (!originalText && !currentText) {
      return [];
    }
    const origLines = (originalText || "").split("\n");
    const currLines = (currentText || "").split("\n");
    const computed: Array<{ type: "added" | "deleted" | "unchanged"; text: string }> = [];

    const maxLen = Math.max(origLines.length, currLines.length);
    for (let i = 0; i < maxLen; i++) {
      const o = origLines[i];
      const c = currLines[i];
      if (o === c) {
        computed.push({ type: "unchanged", text: o ?? "" });
      } else {
        if (o !== undefined) computed.push({ type: "deleted", text: o });
        if (c !== undefined) computed.push({ type: "added", text: c });
      }
    }
    return computed;
  }, [diffData, originalText, currentText]);

  const stats = React.useMemo(() => {
    if (diffData) {
      return {
        additions: diffData.additions,
        deletions: diffData.deletions,
        unchanged: diffData.unchanged,
      };
    }
    let additions = 0;
    let deletions = 0;
    let unchanged = 0;
    for (const l of lines) {
      if (l.type === "added") additions++;
      else if (l.type === "deleted") deletions++;
      else unchanged++;
    }
    return { additions, deletions, unchanged };
  }, [diffData, lines]);

  return (
    <div className="rounded-sm border-2 border-border bg-card shadow-sm overflow-hidden text-sm">
      {/* Newspaper Header Bar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-3 bg-muted/40 border-b border-border gap-3">
        <div className="flex items-center space-x-3">
          <span className="font-serif font-bold text-foreground uppercase tracking-wide text-xs">
            Revision Comparison
          </span>
          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className="inline-flex items-center px-2 py-0.5 rounded-sm bg-emerald-500/15 border border-emerald-600/40 text-emerald-800 font-bold">
              +{stats.additions} lines
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-sm bg-destructive/15 border border-destructive/40 text-destructive font-bold">
              -{stats.deletions} lines
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-sm bg-secondary border border-border text-foreground">
              {stats.unchanged} unchanged
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-2 font-mono">
          <div className="inline-flex rounded-sm shadow-sm bg-secondary p-0.5 border border-border">
            <button
              type="button"
              onClick={() => setViewMode("unified")}
              className={`px-3 py-1 text-xs font-bold uppercase rounded-sm transition-colors ${
                viewMode === "unified"
                  ? "bg-primary text-primary-foreground shadow"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Unified Diff
            </button>
            <button
              type="button"
              onClick={() => setViewMode("split")}
              className={`px-3 py-1 text-xs font-bold uppercase rounded-sm transition-colors ${
                viewMode === "split"
                  ? "bg-primary text-primary-foreground shadow"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Side-by-Side
            </button>
          </div>
        </div>
      </div>

      {/* Diff content view */}
      {viewMode === "unified" ? (
        <div className="overflow-x-auto max-h-[600px] divide-y divide-border/40 font-mono text-xs select-text bg-background">
          {lines.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground font-serif italic">
              No textual changes recorded between these versions.
            </div>
          ) : (
            lines.map((line, idx) => {
              const isAdd = line.type === "added";
              const isDel = line.type === "deleted";
              const bgClass = isAdd
                ? "bg-emerald-500/10 text-emerald-900 border-l-4 border-emerald-600 font-medium"
                : isDel
                ? "bg-destructive/10 text-destructive border-l-4 border-destructive line-through opacity-80"
                : "bg-card/60 text-foreground border-l-4 border-transparent";

              const prefix = isAdd ? "+ " : isDel ? "- " : "  ";

              return (
                <div key={idx} className={`flex px-3 py-1 font-mono hover:bg-muted/30 ${bgClass}`}>
                  <span className="w-10 select-none text-right pr-3 text-muted-foreground/60">{idx + 1}</span>
                  <span className="select-none font-bold mr-1">{prefix}</span>
                  <span className="whitespace-pre-wrap break-all flex-1">{line.text || " "}</span>
                </div>
              );
            })
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 divide-x divide-border max-h-[600px] overflow-y-auto font-mono text-xs bg-background">
          {/* Left panel */}
          <div className="overflow-x-auto p-4 bg-muted/20">
            <div className="sticky top-0 pb-2 mb-2 border-b border-border font-serif text-xs font-bold text-muted-foreground uppercase flex items-center justify-between">
              <span>{leftTitle}</span>
              <span className="font-mono text-[10px] text-muted-foreground">Original/Prior</span>
            </div>
            <pre className="whitespace-pre-wrap break-all text-foreground leading-relaxed font-mono">
              {originalText || (
                lines
                  .filter((l) => l.type !== "added")
                  .map((l) => l.text)
                  .join("\n") || "No baseline text available."
              )}
            </pre>
          </div>

          {/* Right panel */}
          <div className="overflow-x-auto p-4 bg-card">
            <div className="sticky top-0 pb-2 mb-2 border-b border-border font-serif text-xs font-bold text-foreground uppercase flex items-center justify-between">
              <span>{rightTitle}</span>
              <span className="font-mono text-[10px] text-primary">Working/Approved</span>
            </div>
            <pre className="whitespace-pre-wrap break-all text-foreground leading-relaxed font-mono">
              {currentText || (
                lines
                  .filter((l) => l.type !== "deleted")
                  .map((l) => l.text)
                  .join("\n") || "No working text available."
              )}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentDiffViewer;
