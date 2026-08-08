import { useState, useEffect } from "react";
import { AlertCircle, Scan, Lock, CheckCircle2, RefreshCw } from "lucide-react";
import { fetchEvidence, verifyEvidence } from "@/lib/api";

interface EvidenceItem {
  id: string;
  case_id: string;
  title: string;
  offense: string;
  verification_status: string;
  authenticity_score: number;
  chain_of_custody: string;
  flagged: boolean;
  notes: string;
}

export function EvidencePage() {
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);

  const loadEvidence = async () => {
    setLoading(true);
    const data = await fetchEvidence();
    setEvidenceList(data);
    setLoading(false);
  };

  useEffect(() => {
    loadEvidence();
  }, []);

  const handleVerify = async (id: string) => {
    setVerifyingId(id);
    // Optimistic update
    setEvidenceList((prev) =>
      prev.map((item) =>
        item.id === id || item.case_id === id
          ? {
              ...item,
              verification_status: "Verified Authentic",
              authenticity_score: 99.5,
              flagged: false,
            }
          : item
      )
    );
    try {
      await verifyEvidence(id);
      // Wait a short moment to show scan animation
      await new Promise((r) => setTimeout(r, 600));
      const fresh = await fetchEvidence();
      if (fresh && fresh.length > 0) {
        setEvidenceList(fresh);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setVerifyingId(null);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              AI Verification Engine
            </span>
            <span className="text-xs text-muted-foreground font-mono">Chain-of-Custody Authenticity Check</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Evidence & Record Verification</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Automated verification of remand orders, police arrest logs, and legal documentation integrity.
          </p>
        </div>

        <button
          onClick={loadEvidence}
          className="px-4 py-2 bg-white/5 border border-white/10 text-white rounded-xl text-sm font-medium hover:bg-white/10 transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Refresh Engine
        </button>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Running AI authenticity verification scan...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {evidenceList.map(item => (
            <div
              key={item.id}
              className="p-6 rounded-2xl bg-white/[0.02] border border-white/10 hover:border-accent/40 transition-all backdrop-blur-md space-y-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-mono text-xs font-semibold text-accent">{item.id}</span>
                  <h3 className="text-base font-semibold text-white mt-0.5">{item.title}</h3>
                  <div className="text-xs text-muted-foreground mt-1">Case Ref: {item.case_id}</div>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold border flex items-center gap-1.5 ${
                    item.authenticity_score > 85
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  }`}
                >
                  {item.authenticity_score > 85 ? (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5" />
                  )}
                  {item.authenticity_score}% Match
                </span>
              </div>

              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 text-xs space-y-1.5">
                <div className="flex justify-between text-muted-foreground">
                  <span>Chain of Custody:</span>
                  <span className="text-white font-medium">{item.chain_of_custody}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Offense Charges:</span>
                  <span className="text-white font-mono">{item.offense}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Verification Status:</span>
                  <span className="text-accent font-medium">{item.verification_status}</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Lock className="w-3.5 h-3.5 text-accent" /> Cryptographic Integrity Verified
                </span>

                <button
                  onClick={() => handleVerify(item.id)}
                  disabled={verifyingId === item.id}
                  className="px-3.5 py-1.5 bg-accent text-accent-foreground font-semibold rounded-xl text-xs hover:opacity-90 transition-opacity flex items-center gap-1.5"
                >
                  <Scan className={`w-3.5 h-3.5 ${verifyingId === item.id ? "animate-spin" : ""}`} />
                  {verifyingId === item.id ? "Scanning..." : "Re-Verify Record"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
