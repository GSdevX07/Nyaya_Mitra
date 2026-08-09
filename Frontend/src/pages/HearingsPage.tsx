import { useState, useEffect } from "react";
import { Calendar, Gavel, MapPin, UserCheck, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { fetchHearings } from "@/lib/api";

interface HearingItem {
  id: string;
  case_id: string;
  prisoner_name: string;
  court_name: string;
  hearing_date: string;
  hearing_type: string;
  status: string;
  judge: string;
}

export function HearingsPage() {
  const [hearings, setHearings] = useState<HearingItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadHearings = async () => {
    setLoading(true);
    const data = await fetchHearings();
    setHearings(data);
    setLoading(false);
  };

  useEffect(() => {
    loadHearings();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Judicial Motion Tracker
            </span>
            <span className="text-xs text-muted-foreground font-mono">Simulated Court Calendar</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Court Hearings (Demo Data)</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track upcoming undertrial bail applications and remand reviews across judicial magistrate courts.
          </p>
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Fetching judicial calendar from FastAPI backend...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {hearings.map(h => (
            <div
              key={h.id}
              className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 hover:border-accent/40 transition-all backdrop-blur-md space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-semibold text-accent">{h.id}</span>
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    {h.status}
                  </span>
                </div>

                <h3 className="text-base font-semibold text-white">{h.hearing_type}</h3>

                <div className="space-y-2 text-xs text-muted-foreground pt-2 border-t border-white/5">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-accent" />
                    <span>Hearing Date: <strong className="text-white">{h.hearing_date}</strong></span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-accent" />
                    <span className="truncate">{h.court_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Gavel className="w-3.5 h-3.5 text-accent" />
                    <span>{h.judge}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <UserCheck className="w-3.5 h-3.5 text-accent" />
                    <span>Case Ref: <strong className="text-accent">{h.case_id}</strong></span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                <span className="text-xs text-muted-foreground font-mono">{h.prisoner_name}</span>
                <Link
                  to={`/case/${h.case_id}`}
                  className="text-xs font-semibold text-white hover:text-accent transition-colors flex items-center gap-1"
                >
                  Case Dossier <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
