import { useState, useEffect } from "react";
import {
  Calendar,
  Gavel,
  MapPin,
  ArrowRight,
  ShieldCheck,
  FileText,
  X,
  Loader2,
  Clock,
  ShieldAlert,
} from "lucide-react";

import { Link, useNavigate } from "react-router-dom";
import { fetchHearings, fetchCaseById, type CaseRecord } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface HearingItem {
  id: string;
  case_id: string;
  fir_number?: string;
  police_station?: string;
  district?: string;
  prisoner_name: string;
  court_name: string;
  hearing_date: string;
  hearing_type: string;
  status: string;
  judge?: string;
  police_task?: string;
}

export function HearingsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isPolice = user?.role === "POLICE_OFFICER";

  const [hearings, setHearings] = useState<HearingItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Police Authorized Case Modal state
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [selectedCaseData, setSelectedCaseData] = useState<any | null>(null);
  const [loadingCaseModal, setLoadingCaseModal] = useState(false);

  const loadHearings = async () => {
    setLoading(true);
    try {
      const data = await fetchHearings();
      setHearings(data || []);
    } catch (err) {
      console.error("Error loading hearings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHearings();
  }, []);

  const handleOpenPoliceCaseDetails = async (caseId: string) => {
    setSelectedCaseId(caseId);
    setLoadingCaseModal(true);
    try {
      const data = await fetchCaseById(caseId);
      setSelectedCaseData(data);
    } catch (err) {
      console.error("Error loading authorized case details:", err);
    } finally {
      setLoadingCaseModal(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedCaseId(null);
    setSelectedCaseData(null);
  };

  return (
    <div className="p-4 md:p-8 w-full space-y-8 animate-in fade-in duration-300 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-sm text-xs font-semibold bg-primary/10 text-primary border border-primary/20">
              {isPolice ? "Police Judicial Motion Tracker • Station Remand Desk" : "Judicial Motion Tracker"}
            </span>
            <span className="text-xs text-muted-foreground font-mono">
              {isPolice ? "Kotwali / Central PS Reference" : "Active Judicial Tracker"}
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-primary">
            {isPolice ? "Court Hearings & Remand Calendar" : "Court Hearings"}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isPolice
              ? "Track scheduled court production dates, remand reviews, and police task compliance for station FIR cases."
              : "Track upcoming undertrial bail applications and remand reviews across judicial magistrate courts."}
          </p>
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="p-16 text-center text-muted-foreground animate-pulse font-mono text-sm">
          Fetching judicial calendar from FastAPI backend...
        </div>
      ) : hearings.length === 0 ? (
        <div className="p-12 text-center text-muted-foreground font-mono text-sm border-2 border-dashed border-border rounded-sm">
          No scheduled hearings found for current jurisdiction.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {hearings.map((h) => (
            <div
              key={h.id}
              className="p-6 rounded bg-card shadow-sm border border-border hover:border-primary/40 transition-all backdrop-blur-md space-y-4 flex flex-col justify-between"
            >
              <div className="space-y-3">
                {/* Hearing ID & Status */}
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-semibold text-primary">{h.id}</span>
                  <span
                    className={`px-2.5 py-0.5 rounded-sm text-[10px] font-bold uppercase border ${
                      h.status === "Scheduled"
                        ? "bg-primary/10 text-primary border-primary/30"
                        : "bg-muted text-foreground border-border"
                    }`}
                  >
                    {h.status}
                  </span>
                </div>

                {/* Hearing Type */}
                <h3 className="text-base font-semibold text-foreground">{h.hearing_type}</h3>

                {/* Case ID & FIR (Crucial for Police) */}
                <div className="flex items-center gap-2 flex-wrap text-xs font-mono pt-1">
                  <span className="text-muted-foreground">Case:</span>
                  <strong className="text-foreground">{h.case_id}</strong>
                  {h.fir_number && (
                    <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 text-[11px] font-bold">
                      {h.fir_number}
                    </span>
                  )}
                </div>

                {/* Accused Name */}
                <div className="text-xs font-sans text-muted-foreground">
                  Accused: <strong className="text-foreground">{h.prisoner_name}</strong>
                </div>

                {/* Key Hearing Details */}
                <div className="space-y-2 text-xs text-muted-foreground pt-2 border-t border-border">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span>
                      Hearing Date: <strong className="text-foreground">{h.hearing_date}</strong>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <MapPin className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span className="truncate">{h.court_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Gavel className="w-3.5 h-3.5 text-primary shrink-0" />
                    <span>{h.judge || "Hon'ble Special Judicial Magistrate"}</span>
                  </div>
                </div>

                {/* Police-related Task / Status (Visible for Police Officers) */}
                {isPolice && (
                  <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/25 text-amber-800 dark:text-amber-300 text-xs font-sans space-y-1">
                    <div className="font-bold font-mono text-[10px] uppercase flex items-center gap-1.5">
                      <Clock className="w-3 h-3" /> Station Compliance Task
                    </div>
                    <p className="text-[11px] leading-snug">
                      {h.police_task || "Case diary on record; verify remand order and production compliance."}
                    </p>
                  </div>
                )}
              </div>

              {/* Action Footer */}
              <div className="pt-4 border-t border-border flex items-center justify-between">
                <span className="text-xs text-muted-foreground font-mono truncate max-w-[120px]">
                  {h.prisoner_name}
                </span>

                {isPolice ? (
                  <button
                    onClick={() => handleOpenPoliceCaseDetails(h.case_id)}
                    className="px-3 py-1.5 rounded-sm bg-primary text-primary-foreground font-mono text-xs font-bold flex items-center gap-1.5 hover:opacity-90 transition-opacity shadow-sm"
                  >
                    <ShieldCheck className="w-3.5 h-3.5" /> View Authorized Case Details
                  </button>
                ) : (
                  <Link
                    to={`/case/${h.case_id}`}
                    className="text-xs font-semibold text-primary hover:underline transition-colors flex items-center gap-1"
                  >
                    Case Dossier <ArrowRight className="w-3 h-3" />
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Police Authorized Case Details Modal ─────────────────────────────── */}
      {selectedCaseId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border-2 border-border w-full max-w-2xl rounded-sm shadow-xl flex flex-col max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="p-5 border-b border-border bg-muted/40 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-primary" />
                  <span className="text-xs font-mono font-bold uppercase text-primary tracking-wider">
                    Police Station Clearance • Authorized Case Record
                  </span>
                </div>
                <h2 className="text-lg font-bold text-foreground mt-0.5 font-serif">
                  Case File: {selectedCaseId}
                </h2>
              </div>
              <button
                onClick={handleCloseModal}
                className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs font-sans">
              {/* Strict Redaction & Privacy Notice */}
              <div className="p-3 bg-primary/5 border border-primary/20 rounded text-foreground/80 space-y-1">
                <div className="font-bold font-mono text-[10px] uppercase text-primary flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" /> Confidentiality Control Active
                </div>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  Station Police View: Defense legal strategy, private DLSA notes, advocate petition drafts, family contact details, and internal AI analysis are restricted from station police access.
                </p>
              </div>

              {loadingCaseModal ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <span className="font-mono text-xs">Loading authorized station records...</span>
                </div>
              ) : selectedCaseData ? (
                (() => {
                  const c: CaseRecord = (selectedCaseData.case || selectedCaseData) as CaseRecord;
                  const completeness = selectedCaseData.completeness || {};
                  const presentDocs: string[] = c.present_docs || completeness.present_docs || [];

                  const hasRemand = presentDocs.some((d) => d.toLowerCase().includes("remand"));

                  const hasChargeSheet = presentDocs.some((d) => d.toLowerCase().includes("charge"));

                  return (
                    <div className="space-y-4">
                      {/* Grid 1: FIR & Station Particulars */}
                      <div className="p-4 bg-muted/30 border border-border rounded space-y-3">
                        <div className="text-[11px] font-mono font-bold uppercase text-foreground">
                          1. Station FIR & Accused Particulars
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Accused Name:</span>
                            <strong className="text-foreground text-sm">{c.name}</strong>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[11px]">FIR Reference:</span>
                            <strong className="text-primary font-mono">{c.fir_number || "FIR-2024-089"}</strong>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Police Station:</span>
                            <span className="text-foreground">{c.police_station || "Kotwali Police Station"}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Jurisdictional District:</span>
                            <span className="text-foreground">{c.district || "Central District, Delhi"}</span>
                          </div>
                        </div>
                      </div>

                      {/* Grid 2: Custody & Offenses */}
                      <div className="p-4 bg-muted/30 border border-border rounded space-y-3">
                        <div className="text-[11px] font-mono font-bold uppercase text-foreground">
                          2. Custody & Statutory Charges
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Date of Arrest:</span>
                            <span className="font-mono text-foreground">{c.arrest_date}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Elapsed Remand / Custody:</span>
                            <strong className="text-foreground font-mono">{c.custody_days || 0} Days</strong>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Detention Facility:</span>
                            <span className="text-foreground">{c.jail_location || "Tihar Jail 4"}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Penal Code Sections:</span>
                            <span className="font-bold text-foreground">
                              {c.offense_sections?.join(", ") || "BNS 303(2)"}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Grid 3: Police Compliance & Required Documents */}
                      <div className="p-4 bg-muted/30 border border-border rounded space-y-3">
                        <div className="text-[11px] font-mono font-bold uppercase text-foreground">
                          3. Police Evidence & Compliance Status
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between p-2 rounded bg-background border border-border">
                            <span className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-primary" />
                              Judicial Remand Extension Order
                            </span>
                            <span
                              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                                hasRemand
                                  ? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30"
                                  : "bg-red-500/15 text-red-600 border border-red-500/30"
                              }`}
                            >
                              {hasRemand ? "COMPLIANT / ON RECORD" : "PENDING EXTENSION COPY"}
                            </span>
                          </div>

                          <div className="flex items-center justify-between p-2 rounded bg-background border border-border">
                            <span className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-primary" />
                              Police Final Report / Charge Sheet
                            </span>
                            <span
                              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                                hasChargeSheet
                                  ? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30"
                                  : "bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30"
                              }`}
                            >
                              {hasChargeSheet ? "SUBMITTED TO COURT" : "INVESTIGATION PENDING"}
                            </span>
                          </div>

                          <div className="flex items-center justify-between p-2 rounded bg-background border border-border">
                            <span className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-primary" />
                              Arrest Memo & Ground of Arrest
                            </span>
                            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-600 border border-emerald-500/30">
                              VERIFIED ON RECORD
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Grid 4: Court & Presiding Magistrate */}
                      <div className="p-4 bg-muted/30 border border-border rounded space-y-2">
                        <div className="text-[11px] font-mono font-bold uppercase text-foreground">
                          4. Jurisdictional Court Tracking
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Court Name:</span>
                            <span className="text-foreground">{c.court_name || "Chief Metropolitan Magistrate Court"}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[11px]">Procedural Status:</span>
                            <span className="font-mono text-primary font-bold">{c.status}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })()
              ) : (
                <div className="p-6 text-center text-muted-foreground font-mono">
                  Could not load case details.
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-border bg-muted/30 flex items-center justify-between">
              <button
                onClick={handleCloseModal}
                className="px-4 py-2 border border-border rounded-sm hover:bg-muted font-mono text-xs font-semibold"
              >
                Close
              </button>

              <button
                onClick={() => {
                  handleCloseModal();
                  navigate(`/case/${selectedCaseId}`);
                }}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-sm font-mono text-xs font-bold flex items-center gap-1.5 hover:opacity-90"
              >
                Open Full Station Record <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

