import { useState, useEffect } from "react";
import { Search, FileText, Activity } from "lucide-react";
import { useNavigate } from "react-router-dom";
interface CommandPaletteProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export function CommandPalette({ isOpen: externalIsOpen, onClose }: CommandPaletteProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [query, setQuery] = useState("");
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
    ? [].filter(
        (c) =>
          c.id.toLowerCase().includes(query.toLowerCase()) ||
          c.prisonerName.toLowerCase().includes(query.toLowerCase()) ||
          c.offence.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/70 backdrop-blur-md animate-in fade-in duration-200"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-2xl bg-black/90 border border-white/10 rounded-2xl shadow-2xl overflow-hidden shadow-black/80"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-4 border-b border-white/10 bg-white/[0.02]">
          <Search className="w-5 h-5 text-accent" />
          <input
            autoFocus
            type="text"
            placeholder="Search cases by ID, name, section (e.g., UTP-0007, IPC 379)..."
            className="flex-1 bg-transparent text-white focus:outline-none placeholder:text-muted-foreground text-sm"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="text-[10px] text-muted-foreground border border-white/10 px-2 py-0.5 rounded font-mono">
            ESC
          </div>
        </div>

        {query ? (
          <div className="p-2 max-h-[60vh] overflow-y-auto">
            <div className="px-3 py-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Matching Cases ({results.length})
            </div>
            {results.map((c) => (
              <button
                key={c.id}
                onClick={() => handleSelect(c.id)}
                className="w-full text-left flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 transition-colors group"
              >
                <div
                  className={`p-2 rounded bg-white/5 ${
                    c.urgency === "URGENT"
                      ? "text-destructive group-hover:bg-destructive/10"
                      : "text-accent group-hover:bg-accent/10"
                  }`}
                >
                  {c.urgency === "URGENT" ? (
                    <Activity className="w-4 h-4" />
                  ) : (
                    <FileText className="w-4 h-4" />
                  )}
                </div>
                <div>
                  <div className="text-white font-medium text-sm">
                    {c.id} — {c.prisonerName}
                  </div>
                  <div className="text-xs text-muted-foreground font-mono">
                    Offense: {c.offence} | Days in Custody: {c.custodyDurationDays}
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
                    className="w-full text-left px-3 py-2 text-sm text-white/80 hover:text-white hover:bg-white/5 rounded-xl transition-colors flex items-center gap-2"
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
