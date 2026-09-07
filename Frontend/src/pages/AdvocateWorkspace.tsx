import { useState, useEffect } from "react";
import {
  Briefcase,
  Scale,
  CheckCircle2,
  ChevronRight,
  Loader2,
  BookOpen,
  ShieldCheck,
  FileText,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import { Link } from "react-router-dom";
import { fetchCases, type CaseRecord } from "../lib/api";
import { useAuth } from "../lib/auth";
import { UniversalTaskQueue } from "../components/UniversalTaskQueue";

export function AdvocateWorkspace() {
  const { user } = useAuth();
  const isExternal = user?.role === "CONTROLLED_EXTERNAL_ADVOCATE";

  const [activeTab, setActiveTab] = useState<"tasks" | "briefs">("tasks");
  const [assignedCases, setAssignedCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const loadAdvocateCases = async () => {
    setLoading(true);
    try {
      const raw = await fetchCases();
      const extracted = (raw || []).map((item: any) => (item.case || item) as CaseRecord);
      const userFullName = (user?.full_name || "").toLowerCase().trim();
      const userId = (user?.id || "").toLowerCase().trim();

      const preliminaryStates = [
        "INTAKE", "INTAKE_PENDING", "DETECTED", "VERIFICATION", "CUSTODY_VERIFIED",
        "CUSTODY_PENDING", "REVIEW", "LEGAL_AID_REQUIRED", "LEGAL_NEED_IDENTIFIED",
        "PRE_INTAKE", "DOCUMENTS_MISSING", "DRAFT_INTAKE"
      ];

      const strictlyAssigned = extracted.filter((c) => {
        // 1. Must be formally ASSIGNED
        if (c.assignment_status !== "ASSIGNED") return false;

        // 2. Prerequisite Check: Reject preliminary / unverified lifecycle states
        const cStatus = (c.status || "").toUpperCase();
        if (preliminaryStates.includes(cStatus)) return false;

        // 3. Strict Counsel Matching
        const lawyerId = (c.assigned_lawyer_id || "").toLowerCase().trim();
        const lawyerName = (c.assigned_lawyer || "").toLowerCase().trim();

        // Direct ID match
        if (lawyerId && userId && lawyerId === userId) return true;

        // Demo advocate aliases
        if (userId === "demo_advocate") {
          if (["demo_advocate", "adv_001", "adv_rajesh_sharma"].includes(lawyerId)) return true;
          if (lawyerName.includes("rajesh") && (!lawyerId || ["demo_advocate", "adv_001", "adv_rajesh_sharma"].includes(lawyerId))) return true;
        }

        if (userId === "demo_ext_advocate") {
          if (["demo_ext_advocate", "adv_ext_001"].includes(lawyerId)) return true;
          if ((lawyerName.includes("external") || lawyerName.includes("controlled")) && (!lawyerId || ["demo_ext_advocate", "adv_ext_001"].includes(lawyerId))) return true;
        }

        // Substantive Name match (ensure not assigned to a different explicit lawyer ID)
        if (userFullName && userFullName.length >= 4 && lawyerName) {
          if ((lawyerName.includes(userFullName) || userFullName.includes(lawyerName)) && (!lawyerId || lawyerId === userId)) {
            return true;
          }
        }

        return false;
      });
      setAssignedCases(strictlyAssigned);
    } catch (err) {
      console.error("Failed to load advocate cases:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdvocateCases();
  }, []);

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
        <p className="text-xs font-mono text-muted-foreground">
          {isExternal ? "Loading external advocate workspace..." : "Loading advocate briefing workspace..."}
        </p>
      </div>
    );
  }

  const approvedForFiling = assignedCases.filter((c) => c.status === "APPROVED" || c.status === "APPROVED_READY_FOR_FILING");
  const filedCases = assignedCases.filter((c) => c.status === "FILED" || c.status === "HEARING_SCHEDULED");

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Advocate Workspace Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Briefcase className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              {isExternal 
                ? "Restricted External Advocate // Authorized Matters Only" 
                : "Defense Legal Aid Counsel // Assigned Portfolio"}
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            {isExternal 
              ? "Restricted Advocate Workspace" 
              : "Defense Advocate Briefing & Operations Desk"}
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            {isExternal
              ? "Access explicitly assigned cases, review authorized legal documents, consult the Governed Legal Knowledge Base, and track scheduled hearings."
              : "Scrutinize assigned undertrial dossiers, verify Section 479 statutory calculations, execute mandatory Level-1 Counsel Sign-Off, and file approved petitions in court."}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isExternal ? (
            <Link
              to="/legal-sources"
              className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90"
            >
              <BookOpen className="w-4 h-4" /> Legal Knowledge
            </Link>
          ) : (
            <Link
              to="/radar"
              className="px-4 py-2 bg-primary text-primary-foreground font-mono text-xs font-bold uppercase rounded-sm flex items-center gap-1.5 hover:opacity-90"
            >
              <Scale className="w-4 h-4" /> Eligibility Radar
            </Link>
          )}
        </div>
      </div>

      {/* Procedural Workflow Indicator Banner */}
      <div className="p-4 bg-primary/5 border border-primary/20 rounded-sm text-xs font-mono space-y-2">
        <div className="flex items-center gap-2 font-bold text-foreground uppercase">
          <ShieldCheck className="w-4 h-4 text-primary shrink-0" />
          <span>Statutory Defense Workflow Pipeline</span>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
          <span className="px-2 py-0.5 bg-card border border-border rounded font-bold text-foreground">1. Advocate Drafts</span>
          <ArrowRight className="w-3 h-3 text-muted-foreground" />
          <span className="px-2 py-0.5 bg-card border border-border rounded font-bold text-foreground">2. Counsel Sign-Off (Level 1)</span>
          <ArrowRight className="w-3 h-3 text-muted-foreground" />
          <span className="px-2 py-0.5 bg-card border border-border rounded font-bold text-foreground">3. Supervisor Approves (Level 2)</span>
          <ArrowRight className="w-3 h-3 text-muted-foreground" />
          <span className="px-2 py-0.5 bg-primary/10 text-primary border border-primary/30 font-bold rounded">4. Advocate Files in Court</span>
        </div>
      </div>

      {/* Stats Ribbon */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Assigned Undertrial Matters</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">{assignedCases.length}</div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">
            {isExternal ? "Explicitly Authorized Briefs" : "DLSA Confirmed Panel Assignment"}
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Ready for Court Filing</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
            {approvedForFiling.length}
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Level-2 Supervisory Approval Granted
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Filed in Court Registry</div>
          <div className="text-2xl font-serif font-bold text-blue-600 mt-1">
            {filedCases.length}
          </div>
          <div className="text-[10px] font-mono text-blue-600 mt-1">Active Court Proceedings</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b-2 border-border pb-2">
        <button
          onClick={() => setActiveTab("tasks")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "tasks"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <Briefcase className="w-4 h-4" />
          My Assigned Tasks
        </button>

        <button
          onClick={() => setActiveTab("briefs")}
          className={`px-4 py-2 font-serif text-xs uppercase font-bold tracking-wider rounded-sm transition-colors flex items-center gap-2 ${
            activeTab === "briefs"
              ? "bg-primary text-primary-foreground shadow-xs"
              : "bg-secondary text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileText className="w-4 h-4" />
          My Assigned Briefs ({assignedCases.length})
        </button>
      </div>

      {/* TAB 1: Assigned Task Queue */}
      {activeTab === "tasks" && (
        <div className="space-y-4">
          <UniversalTaskQueue
            initialFilter={{ owner_role: "DEFENSE_ADVOCATE" }}
            title="Assigned Defense Actions Queue"
            subtitle="Prioritized matters requiring bail petition drafting, counsel human sign-off, or court registry filing."
            allowedTaskTypes={["PREPARE_AND_SIGN_OFF_DRAFT", "FILE_APPLICATION_IN_COURT"]}
          />
        </div>
      )}

      {/* TAB 2: Assigned Cases List */}
      {activeTab === "briefs" && (
        <div className="bg-card border-2 border-border rounded-sm overflow-hidden">
          <div className="p-4 border-b border-border bg-secondary/40 font-serif font-bold text-xs uppercase tracking-wider text-muted-foreground flex items-center justify-between">
            <span>My Active Undertrial Briefs ({assignedCases.length} matters)</span>
            <span className="text-[11px] font-mono font-normal">
              Counsel ID: {user?.id}
            </span>
          </div>

          {assignedCases.length === 0 ? (
            <div className="p-12 text-center space-y-2">
              <FileText className="w-8 h-8 text-muted-foreground/50 mx-auto" />
              <h3 className="font-serif font-bold text-foreground text-sm">No Active Undertrial Briefs</h3>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                You do not have any undertrial cases assigned at this time. Matters assigned to you by the District Legal Services Authority (DLSA) will appear here automatically.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {assignedCases.map((c) => {
                const isApprovedForFiling = c.status === "APPROVED" || c.status === "APPROVED_READY_FOR_FILING";
                const isFiled = c.status === "FILED" || c.status === "HEARING_SCHEDULED";
                const hasDirectivePending = (c.timeline || []).some(
                  (ev: any) =>
                    ev.event_type === "LEGAL_AID" &&
                    (ev.title?.includes("Review Feedback") || ev.title?.includes("Review Note"))
                );

                return (
                  <div
                    key={c.case_id}
                    className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-secondary/20 transition-colors"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-base text-foreground font-serif">{c.name}</span>
                        <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                          {c.case_id}
                        </span>
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-secondary border border-border">
                          {c.legal_code}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
                        <span>Offences: <strong className="text-foreground">{c.offense_sections?.join(", ")}</strong></span>
                        <span>•</span>
                        <span>Custody: <strong className="text-foreground">{c.custody_days} days</strong></span>
                        <span>•</span>
                        <span>Court: <strong className="text-foreground">{c.court_name}</strong></span>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                      {hasDirectivePending && (
                        <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> REVISION REQUESTED
                        </span>
                      )}

                      {isApprovedForFiling && (
                        <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-emerald-500/10 text-emerald-600 border border-emerald-500/20 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> SUPERVISOR APPROVED
                        </span>
                      )}

                      {isFiled && (
                        <span className="px-2.5 py-1 text-[11px] font-mono font-bold rounded bg-blue-500/10 text-blue-600 border border-blue-500/20">
                          FILED IN COURT
                        </span>
                      )}

                      {!isApprovedForFiling && !isFiled && (
                        <span className="px-2.5 py-1 text-[11px] font-mono text-muted-foreground rounded bg-secondary border border-border">
                          {c.status}
                        </span>
                      )}

                      <Link
                        to={`/case/${c.case_id}${c.status === "ANALYSIS_READY" || c.status === "HUMAN_REVIEW" || isApprovedForFiling ? "?tab=draft" : ""}`}
                        className={`px-3.5 py-1.5 font-serif font-bold text-xs rounded-sm flex items-center gap-1 hover:opacity-90 transition-opacity ${
                          isApprovedForFiling
                            ? "bg-emerald-600 text-white"
                            : "bg-primary text-primary-foreground"
                        }`}
                      >
                        {isApprovedForFiling ? "File Petition in Court" : "Review Dossier & Draft"}{" "}
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

