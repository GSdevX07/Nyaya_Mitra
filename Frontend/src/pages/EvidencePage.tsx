import { useState, useEffect } from "react";
import { AlertCircle, Scan, Lock, CheckCircle2, RefreshCw, ShieldCheck } from "lucide-react";
import { fetchEvidence, verifyEvidence } from "@/lib/api";
import { useAuth } from "@/lib/auth";

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
  stored_hash: string;
  computed_hash?: string;
  tampering_detected?: boolean;
}

export function EvidencePage() {
  const { hasRole } = useAuth();
  // DLSA officers, Supervisors, Platform Admins, Gov Admins, and Jail Officers can trigger cryptographic hash re-verification.
  const canVerify = hasRole("SUPERVISING_LEGAL_OFFICER", "DLSA_OFFICER", "PLATFORM_ADMIN", "GOV_ADMIN", "JAIL_OFFICER");

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
    try {
      const verifyResult = await verifyEvidence(id);
      // Wait a short moment to show scan animation
      await new Promise((r) => setTimeout(r, 600));
      
      setEvidenceList((prev) =>
        prev.map((item) =>
          item.id === id
            ? {
                ...item,
                verification_status: verifyResult.status,
                computed_hash: verifyResult.computed_hash,
                tampering_detected: verifyResult.tampering_detected,
                authenticity_score: verifyResult.tampering_detected ? 0 : 100,
              }
            : item
        )
      );
    } catch (err) {
      console.error(err);
    } finally {
      setVerifyingId(null);
    }
  };

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-sm text-xs font-semibold bg-accent/10 text-accent border border-accent/20">
              Hash & Record Integrity Verification
            </span>
            <span className="text-xs text-muted-foreground font-mono">Hash Integrity & Chain-of-Custody Status</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">Evidence & Record Integrity</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Cryptographic hash comparison of remand orders, arrest logs, and legal documentation integrity. Verifies file byte-level integrity, not judicial authentication.
          </p>
        </div>

        <button
          onClick={loadEvidence}
          className="px-4 py-2 bg-secondary/50 border border-border text-primary rounded text-sm font-medium hover:bg-secondary transition-colors flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Refresh Engine
        </button>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse">
          Running cryptographic hash verification scan...
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {evidenceList.map(item => (
            <div
              key={item.id}
              className="p-6 rounded bg-card shadow-sm border border-border hover:border-accent/40 transition-all backdrop-blur-md space-y-4"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-mono text-xs font-semibold text-accent">{item.id}</span>
                  <h3 className="text-base font-semibold text-primary mt-0.5">{item.title}</h3>
                  <div className="text-xs text-muted-foreground mt-1">Case Ref: {item.case_id}</div>
                </div>

                <span
                  className={`px-3 py-1 rounded-sm text-xs font-semibold border flex items-center gap-1.5 ${
                    item.authenticity_score > 85
                      ? "bg-muted text-foreground border-border"
                      : "bg-muted text-muted-foreground border-border"
                  }`}
                >
                  {item.authenticity_score > 85 ? (
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5" />
                  )}
                  {item.authenticity_score}% Hash Match
                </span>
              </div>

              <div className="p-3 rounded bg-card shadow-sm border border-border text-xs space-y-1.5">
                <div className="flex justify-between text-muted-foreground">
                  <span>Chain of Custody:</span>
                  <span className="text-primary font-medium">{item.chain_of_custody}</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Stored SHA-256:</span>
                  <span className="text-primary font-mono">{item.stored_hash?.substring(0, 16)}...</span>
                </div>
                {item.computed_hash && (
                  <div className="flex justify-between text-muted-foreground">
                    <span>Computed Hash:</span>
                    <span className={`font-mono font-medium ${item.tampering_detected ? 'text-destructive' : 'text-foreground'}`}>
                      {item.computed_hash.substring(0, 16)}...
                    </span>
                  </div>
                )}
                <div className="flex justify-between text-muted-foreground">
                  <span>Verification Status:</span>
                  <span className={`${item.tampering_detected ? 'text-destructive' : 'text-accent'} font-medium`}>{item.verification_status}</span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                {item.computed_hash ? (
                  item.tampering_detected ? (
                    <span className="text-xs text-destructive font-medium flex items-center gap-1">
                      <AlertCircle className="w-4 h-4" /> ✕ Integrity Violation (Mismatch)
                    </span>
                  ) : (
                    <span className="text-xs text-foreground font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" /> ✓ Integrity Verified (Match)
                    </span>
                  )
                ) : (
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Lock className="w-3.5 h-3.5 text-accent" /> Awaiting Verification
                  </span>
                )}

                {canVerify ? (
                  <button
                    onClick={() => handleVerify(item.id)}
                    disabled={verifyingId === item.id}
                    className="px-3.5 py-1.5 bg-accent text-accent-foreground font-semibold rounded text-xs hover:opacity-90 transition-opacity flex items-center gap-1.5"
                  >
                    <Scan className={`w-3.5 h-3.5 ${verifyingId === item.id ? "animate-spin" : ""}`} />
                    {verifyingId === item.id ? "Scanning..." : "Re-Verify Record"}
                  </button>
                ) : (
                  <span className="px-3 py-1.5 bg-muted text-muted-foreground text-xs font-mono font-bold rounded border border-border flex items-center gap-1.5" title="Evidence verification requires Supervisory Legal Officer or Advocate authorization">
                    <ShieldCheck className="w-3.5 h-3.5" /> View Only
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
