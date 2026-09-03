import { useState, useEffect } from "react";
import { Search, FileText, Activity } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { fetchCases, type BackendCaseSummary } from "@/lib/api";

interface CommandPaletteProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function CommandPalette({ isOpen: externalIsOpen, onClose }: CommandPaletteProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cases, setCases] = useState<BackendCaseSummary[]>([]);
  const navigate = useNavigate();

  const isPaletteOpen = externalIsOpen !== undefined ? externalIsOpen : internalIsOpen;

  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      setInternalIsOpen(false);
    }
  };

  useEffect(() => {
    if (isPaletteOpen) {
      fetchCases()
        .then((data) => setCases(data || []))
        .catch(() => setCases([]));
    }
  }, [isPaletteOpen]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setInternalIsOpen((open) => !open);
      }
      if (e.key === "Escape") {
        handleClose();
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  if (!isPaletteOpen) return null;

  const handleSelect = (id: string) => {
    handleClose();
    navigate(`/case/${id}`);
  };

  const results = query
    ? cases.filter(
        (c) =>
          c.case.case_id.toLowerCase().includes(query.toLowerCase()) ||
          c.case.name.toLowerCase().includes(query.toLowerCase()) ||
          c.case.offense_sections.some((s) => s.toLowerCase().includes(query.toLowerCase()))
      )
    : [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-primary backdrop-blur-md animate-in fade-in duration-200"
      onClick={handleClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Universal Case Search Command Palette"
        className="w-full max-w-2xl bg-primary border border-border rounded shadow-2xl overflow-hidden shadow-primary/5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-4 border-b border-border bg-card shadow-sm">
          <Search className="w-5 h-5 text-accent" />
          <input
            autoFocus
            type="text"
            aria-label="Search cases by ID, name, or legal section"
            placeholder="Search cases by ID, name, section (e.g., UTP-0007, IPC 379)..."
            className="flex-1 bg-transparent text-primary focus:outline-none placeholder:text-muted-foreground text-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="text-[10px] text-muted-foreground border border-border px-2 py-0.5 rounded font-mono">
            ESC
          </div>
        </div>

        {query ? (
          <div className="p-2 max-h-[60vh] overflow-y-auto">
            <div className="px-3 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Matching Cases ({results.length})
            </div>
            {results.map((item) => (
              <button
                key={item.case.case_id}
                onClick={() => handleSelect(item.case.case_id)}
                className="w-full text-left flex items-center gap-3 px-3 py-3 rounded hover:bg-secondary/50 transition-colors group"
              >
                <div
                  className={`p-2 rounded bg-secondary/50 ${
                    item.urgency_score > 200
                      ? "text-destructive group-hover:bg-destructive/10"
                      : "text-accent group-hover:bg-accent/10"
                  }`}
                >
                  {item.urgency_score > 200 ? (
                    <Activity className="w-4 h-4" />
                  ) : (
                    <FileText className="w-4 h-4" />
                  )}
                </div>
                <div>
                  <div className="text-primary font-medium text-sm">
                    {item.case.case_id} — {item.case.name}
                  </div>
                  <div className="text-xs text-muted-foreground font-mono">
                    Offense: {item.case.offense_sections.join(", ")} | Days in Custody: {item.case.custody_days}
                  </div>
                </div>
              </button>
            ))}
            {results.length === 0 && (
              <div className="p-8 text-center text-sm text-muted-foreground">
                No matching undertrial records found for "{query}"
              </div>
            )}
          </div>
        ) : (
          <div className="p-4 space-y-4">
            <div>
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                Quick Search Commands
              </div>
              <div className="space-y-1.5">
                {[
                  { label: "Find cases eligible under BNSS 479", query: "UTP-0007" },
                  { label: "View medical priority undertrials", query: "UTP-0021" },
                  { label: "View missing document cases", query: "UTP-0015" },
                ].map((cmd) => (
                  <button
                    key={cmd.label}
                    onClick={() => setQuery(cmd.query)}
                    className="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-secondary/50 rounded transition-colors flex items-center gap-2"
                  >
                    <Search className="w-4 h-4 text-accent" /> {cmd.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
