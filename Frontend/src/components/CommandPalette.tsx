import { useState, useEffect } from "react";
import { Search, FileText, Activity } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { MOCK_CASES } from "@/data/mock";

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setIsOpen((open) => !open);
      }
      if (e.key === "Escape") {
        setIsOpen(false);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  if (!isOpen) return null;

  const handleSelect = (id: string) => {
    setIsOpen(false);
    navigate(`/case/${id}`);
  };

  const results = query ? MOCK_CASES.filter(c => 
    c.id.toLowerCase().includes(query.toLowerCase()) || 
    c.prisonerName.toLowerCase().includes(query.toLowerCase())
  ) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/60 backdrop-blur-sm" onClick={() => setIsOpen(false)}>
      <div 
        className="w-full max-w-2xl bg-black/90 border border-white/10 rounded-xl shadow-2xl overflow-hidden shadow-black/50"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-4 border-b border-white/10">
          <Search className="w-5 h-5 text-muted-foreground" />
          <input 
            autoFocus
            type="text" 
            placeholder="Search cases, commands, or type natural language..."
            className="flex-1 bg-transparent text-white focus:outline-none placeholder:text-muted-foreground"
            value={query}
            onChange={e => setQuery(e.target.value)}
          />
          <div className="text-[10px] text-muted-foreground border border-white/10 px-1.5 py-0.5 rounded font-mono">ESC</div>
        </div>

        {query && (
          <div className="p-2 max-h-[60vh] overflow-y-auto">
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Cases
            </div>
            {results.map(c => (
              <button
                key={c.id}
                onClick={() => handleSelect(c.id)}
                className="w-full text-left flex items-center gap-3 px-3 py-3 rounded-lg hover:bg-white/5 transition-colors group"
              >
                <div className={`p-2 rounded bg-white/5 ${c.urgency === 'URGENT' ? 'text-destructive group-hover:bg-destructive/10' : 'text-accent group-hover:bg-accent/10'}`}>
                  {c.urgency === 'URGENT' ? <Activity className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                </div>
                <div>
                  <div className="text-white font-medium">{c.id} - {c.prisonerName}</div>
                  <div className="text-xs text-muted-foreground">{c.offence}</div>
                </div>
              </button>
            ))}
            {results.length === 0 && (
              <div className="p-4 text-center text-sm text-muted-foreground">
                No results found for "{query}"
              </div>
            )}
          </div>
        )}
        
        {!query && (
          <div className="p-4 space-y-4">
            <div>
              <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                Suggested Commands
              </div>
              <div className="space-y-1">
                {["Find cases approaching eligibility", "Show overdue cases", "Find missing hearing orders"].map(cmd => (
                  <button key={cmd} className="w-full text-left px-3 py-2 text-sm text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors flex items-center gap-2">
                    <Search className="w-4 h-4 text-muted-foreground" /> {cmd}
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
