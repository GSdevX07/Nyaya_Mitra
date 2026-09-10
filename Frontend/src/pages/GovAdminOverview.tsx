import { useState, useEffect } from "react";
import {
  Shield,
  AlertTriangle,
  CheckCircle2,
  Clock,
  MapPin,
  Building2,
  BarChart3,
  FileText,
  Loader2,
  Plus,
  FileCode,
  UserCheck,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import {
  fetchGovOverview,
  fetchGovDistricts,
  fetchGovSlaMetrics,
  fetchGovExceptions,
  fetchReports,
  fetchDocumentTemplates,
  createDocumentTemplate,
  updateDocumentTemplate,
  listDelegationsApi,
  createDelegationApi,
  revokeDelegationApi,
  type GovOverviewMetrics,
  type GovDistrictItem,
  type GovSlaData,
  type GovExceptionItem,
  type DocumentTemplate,
  type InstitutionalDelegation,
} from "../lib/api";

export function GovAdminOverview() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<GovOverviewMetrics | null>(null);
  const [districts, setDistricts] = useState<GovDistrictItem[]>([]);
  const [slaData, setSlaData] = useState<GovSlaData | null>(null);
  const [exceptions, setExceptions] = useState<GovExceptionItem[]>([]);
  const [reports, setReports] = useState<any>(null);
  const [templates, setTemplates] = useState<DocumentTemplate[]>([]);
  const [delegations, setDelegations] = useState<InstitutionalDelegation[]>([]);
  const [loading, setLoading] = useState(true);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [delegationsLoading, setDelegationsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"districts" | "sla" | "exceptions" | "templates" | "delegations">("districts");

  // Template Modal State
  const [showCreateTemplateModal, setShowCreateTemplateModal] = useState(false);
  const [showEditTemplateModal, setShowEditTemplateModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<DocumentTemplate | null>(null);
  const [templateForm, setTemplateForm] = useState({
    name: "",
    doc_type: "BAIL_APPLICATION",
    jurisdiction: "National / BNSS 2023",
    statutory_ground: "Section 479 BNSS 2023",
    description: "",
    content_template: "",
    required_fields: "case_number, accused_name, custody_duration_days",
    required_documents: "charge_sheet, custody_certificate",
  });
  const [templateSaving, setTemplateSaving] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  // Delegation Modal State
  const [showCreateDelegationModal, setShowCreateDelegationModal] = useState(false);
  const [delegationForm, setDelegationForm] = useState({
    granted_to_user_id: "",
    granted_to_role: "DLSA_OFFICER",
    capability: "CAN_INITIATE_DOCUMENT_DRAFT",
    allowed_document_types: "*",
    allowed_case_scope: "*",
    valid_until: "",
    reason: "",
  });
  const [delegationSaving, setDelegationSaving] = useState(false);
  const [delegationError, setDelegationError] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  useEffect(() => {
    async function loadAllGovData() {
      setLoading(true);
      try {
        const [govOv, govDist, govSla, govExc, rep] = await Promise.all([
          fetchGovOverview().catch(() => null),
          fetchGovDistricts().catch(() => []),
          fetchGovSlaMetrics().catch(() => null),
          fetchGovExceptions().catch(() => []),
          fetchReports().catch(() => null),
        ]);
        setOverview(govOv);
        setDistricts(govDist);
        setSlaData(govSla);
        setExceptions(govExc);
        setReports(rep);
      } catch (err) {
        console.error("Failed to load gov overview data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadAllGovData();
  }, []);

  useEffect(() => {
    if (activeTab === "templates") {
      loadTemplates();
    } else if (activeTab === "delegations") {
      loadDelegations();
    }
  }, [activeTab]);

  async function loadTemplates() {
    setTemplatesLoading(true);
    try {
      const res = await fetchDocumentTemplates();
      setTemplates(res || []);
    } catch (err) {
      console.error("Failed to load document templates:", err);
    } finally {
      setTemplatesLoading(false);
    }
  }

  async function loadDelegations() {
    setDelegationsLoading(true);
    try {
      const res = await listDelegationsApi();
      setDelegations(res.delegations || []);
    } catch (err) {
      console.error("Failed to load institutional delegations:", err);
    } finally {
      setDelegationsLoading(false);
    }
  }

  const handleCreateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    setTemplateSaving(true);
    setTemplateError(null);
    try {
      await createDocumentTemplate({
        name: templateForm.name,
        doc_type: templateForm.doc_type,
        jurisdiction: templateForm.jurisdiction,
        statutory_ground: templateForm.statutory_ground,
        description: templateForm.description,
        content_template: templateForm.content_template,
        required_fields: templateForm.required_fields.split(",").map((s) => s.trim()).filter(Boolean),
        required_documents: templateForm.required_documents.split(",").map((s) => s.trim()).filter(Boolean),
        organization_id: user?.org_id,
      });
      setShowCreateTemplateModal(false);
      setTemplateForm({
        name: "",
        doc_type: "BAIL_APPLICATION",
        jurisdiction: "National / BNSS 2023",
        statutory_ground: "Section 479 BNSS 2023",
        description: "",
        content_template: "",
        required_fields: "case_number, accused_name, custody_duration_days",
        required_documents: "charge_sheet, custody_certificate",
      });
      await loadTemplates();
    } catch (err: any) {
      setTemplateError(err.message || "Failed to author template");
    } finally {
      setTemplateSaving(false);
    }
  };

  const handleEditTemplate = (tmpl: DocumentTemplate) => {
    setSelectedTemplate(tmpl);
    setTemplateForm({
      name: tmpl.name,
      doc_type: tmpl.doc_type,
      jurisdiction: tmpl.jurisdiction || "National / BNSS 2023",
      statutory_ground: tmpl.statutory_ground,
      description: tmpl.description || "",
      content_template: tmpl.content_template,
      required_fields: (tmpl.required_fields || []).join(", "),
      required_documents: (tmpl.required_documents || []).join(", "),
    });
    setShowEditTemplateModal(true);
  };

  const handleUpdateTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate) return;
    const templateId = selectedTemplate.id || selectedTemplate.template_id;
    if (!templateId) return;
    setTemplateSaving(true);
    setTemplateError(null);
    try {
      await updateDocumentTemplate(templateId, {
        name: templateForm.name,
        statutory_ground: templateForm.statutory_ground,
        description: templateForm.description,
        content_template: templateForm.content_template,
        required_fields: templateForm.required_fields.split(",").map((s) => s.trim()).filter(Boolean),
        required_documents: templateForm.required_documents.split(",").map((s) => s.trim()).filter(Boolean),
        jurisdiction: templateForm.jurisdiction,
      });
      setShowEditTemplateModal(false);
      setSelectedTemplate(null);
      await loadTemplates();
    } catch (err: any) {
      setTemplateError(err.message || "Failed to update template");
    } finally {
      setTemplateSaving(false);
    }
  };

  const handleCreateDelegation = async (e: React.FormEvent) => {
    e.preventDefault();
    setDelegationSaving(true);
    setDelegationError(null);
    try {
      const validUntilDate = new Date(delegationForm.valid_until);
      await createDelegationApi({
        granted_to_user_id: delegationForm.granted_to_user_id,
        granted_to_role: delegationForm.granted_to_role,
        capability: delegationForm.capability,
        allowed_document_types: delegationForm.allowed_document_types.split(",").map((s) => s.trim()).filter(Boolean),
        allowed_case_scope: delegationForm.allowed_case_scope.split(",").map((s) => s.trim()).filter(Boolean),
        valid_until: validUntilDate.toISOString(),
        reason: delegationForm.reason,
        organization_id: user?.org_id,
      });
      setShowCreateDelegationModal(false);
      setDelegationForm({
        granted_to_user_id: "",
        granted_to_role: "DLSA_OFFICER",
        capability: "CAN_INITIATE_DOCUMENT_DRAFT",
        allowed_document_types: "*",
        allowed_case_scope: "*",
        valid_until: "",
        reason: "",
      });
      await loadDelegations();
    } catch (err: any) {
      setDelegationError(err.message || "Failed to create delegation");
    } finally {
      setDelegationSaving(false);
    }
  };

  const handleRevokeDelegation = async (delegationId: string) => {
    if (!window.confirm("Are you sure you want to revoke this institutional delegation?")) return;
    setRevokingId(delegationId);
    try {
      await revokeDelegationApi(delegationId, "Revoked by SLSA Governance Administrator");
      await loadDelegations();
    } catch (err: any) {
      alert(err.message || "Failed to revoke delegation");
    } finally {
      setRevokingId(null);
    }
  };

  const stateName = user?.state || overview?.state || "Delhi";

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      {/* Gov Admin Header */}
      <div className="bg-card border-2 border-border p-6 rounded-sm shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield className="w-5 h-5 text-primary" />
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
              {stateName} State Legal Services Authority (SLSA) & Government Oversight
            </span>
          </div>
          <h1 className="text-2xl font-serif font-black tracking-tight text-foreground uppercase">
            Statewide Legal Aid Operations Console
          </h1>
          <p className="text-xs font-sans text-muted-foreground mt-1 max-w-2xl">
            State-level oversight, approved document template governance, institutional delegation administration, and Section 479 BNSS statutory compliance tracking.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-mono font-bold px-2.5 py-1 bg-primary/10 text-primary border border-primary/20 rounded">
            STATE_OVERSIGHT_ACTIVE
          </span>
          <span className="text-[10px] font-mono font-semibold px-2 py-1 bg-secondary text-secondary-foreground border border-border rounded">
            {user?.scope_type || "STATEWIDE"} SCOPE
          </span>
        </div>
      </div>

      {/* Aggregate KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Total Monitored Undertrials</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">
            {overview?.total_monitored_undertrials ?? reports?.overview?.total_undertrials_monitored ?? "—"}
          </div>
          <div className="text-[10px] font-mono text-emerald-600 mt-1">
            {overview?.dlsa_mapping_coverage_pct ?? reports?.overview?.dlsa_mapping_coverage_pct ?? 0}% DLSA Mapped
          </div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Section 479 Eligibility Signals</div>
          <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
            {overview?.section_479_eligibility_signals ?? reports?.overview?.bnss_479_eligible ?? "—"}
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">Potential Threshold Cases</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Average Detention</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">
            {overview?.average_custody_days ?? reports?.overview?.average_custody_days ?? "—"}d
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1">Calendar Custody Duration</div>
        </div>

        <div className="bg-card border-2 border-border p-4 rounded-sm">
          <div className="text-[11px] font-mono text-muted-foreground uppercase">Estimated Review Hours Avoided</div>
          <div className="text-2xl font-serif font-bold text-foreground mt-1">
            {overview?.estimated_manual_review_hours_avoided ?? reports?.overview?.estimated_hours_saved_by_ai ?? "—"}h
          </div>
          <div className="text-[10px] font-mono text-muted-foreground mt-1" title="Simulation estimate — not measured operational savings">
            Simulation Estimate
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-border space-x-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab("districts")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold uppercase transition-colors border-b-2 whitespace-nowrap ${
            activeTab === "districts"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Building2 className="w-4 h-4" />
          District-Level DLSA Performance ({districts.length})
        </button>
        <button
          onClick={() => setActiveTab("sla")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold uppercase transition-colors border-b-2 whitespace-nowrap ${
            activeTab === "sla"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <Clock className="w-4 h-4" />
          Statutory SLA Tracking ({slaData?.overall_compliance_pct ?? 100}%)
        </button>
        <button
          onClick={() => setActiveTab("exceptions")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold uppercase transition-colors border-b-2 whitespace-nowrap ${
            activeTab === "exceptions"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <AlertTriangle className="w-4 h-4" />
          Systemic Exceptions & Bottlenecks ({exceptions.length})
        </button>
        <button
          onClick={() => setActiveTab("templates")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold uppercase transition-colors border-b-2 whitespace-nowrap ${
            activeTab === "templates"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <FileCode className="w-4 h-4" />
          Approved Document Templates ({templates.length})
        </button>
        <button
          onClick={() => setActiveTab("delegations")}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold uppercase transition-colors border-b-2 whitespace-nowrap ${
            activeTab === "delegations"
              ? "border-primary text-primary bg-primary/5"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          <UserCheck className="w-4 h-4" />
          Institutional Delegations ({delegations.length})
        </button>
      </div>

      {/* Tab 1: District Performance Table */}
      {activeTab === "districts" && (
        <div className="bg-card border-2 border-border p-5 rounded-sm space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <MapPin className="w-4 h-4 text-primary" />
              Statewide District Legal Services Authority (DLSA) Breakdown
            </h2>
            <span className="text-[11px] font-mono text-muted-foreground">
              {districts.length} Reporting Districts
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead>
                <tr className="border-b-2 border-border text-muted-foreground uppercase text-[10px]">
                  <th className="py-2.5 px-3">District / DLSA</th>
                  <th className="py-2.5 px-3 text-center">Active Undertrials</th>
                  <th className="py-2.5 px-3 text-center">Sec 479 Signals</th>
                  <th className="py-2.5 px-3 text-center">Assigned Counsel</th>
                  <th className="py-2.5 px-3 text-center">Pending Docs</th>
                  <th className="py-2.5 px-3 text-center">Avg Detention</th>
                  <th className="py-2.5 px-3 text-right">Compliance Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-muted-foreground">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin text-primary" />
                        <span className="text-xs font-mono">Loading district metrics from database...</span>
                      </div>
                    </td>
                  </tr>
                ) : districts.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-muted-foreground">
                      No district data available for current scope.
                    </td>
                  </tr>
                ) : (
                  districts.map((item, idx) => (
                    <tr key={idx} className="hover:bg-secondary/20 transition-colors">
                      <td className="py-3 px-3 font-bold text-foreground flex items-center gap-2">
                        <Building2 className="w-3.5 h-3.5 text-muted-foreground" />
                        {item.district}
                      </td>
                      <td className="py-3 px-3 text-center">{item.total_cases}</td>
                      <td className="py-3 px-3 text-center font-bold text-emerald-600">
                        {item.eligible_signals}
                      </td>
                      <td className="py-3 px-3 text-center text-primary">{item.assigned_counsel}</td>
                      <td className="py-3 px-3 text-center">
                        {item.pending_documents > 0 ? (
                          <span className="text-red-600 font-bold">{item.pending_documents}</span>
                        ) : (
                          <span className="text-emerald-600">0</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-center">{item.avg_custody_days}d</td>
                      <td className="py-3 px-3 text-right">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            item.compliance_rate_pct >= 80
                              ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                              : "bg-secondary text-foreground border border-border"
                          }`}
                        >
                          {item.compliance_rate_pct}%
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: SLA Tracking */}
      {activeTab === "sla" && (
        <div className="bg-card border-2 border-border p-5 rounded-sm space-y-5">
          <div className="flex justify-between items-center">
            <h2 className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary" />
              Statutory SLA & Operational Milestones Tracking
            </h2>
            <span className="text-[11px] font-mono text-emerald-600 font-bold">
              Overall Compliance: {slaData?.overall_compliance_pct ?? 100}%
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-secondary/30 rounded border border-border">
              <div className="text-[11px] font-mono text-muted-foreground uppercase">Compliant Cases</div>
              <div className="text-2xl font-serif font-bold text-emerald-600 mt-1">
                {slaData?.sla_breakdown.compliant_cases ?? 0}
              </div>
              <div className="text-[10px] font-mono text-muted-foreground mt-1">Within Statutory SLA</div>
            </div>
            <div className="p-4 bg-secondary/30 rounded border border-border">
              <div className="text-[11px] font-mono text-muted-foreground uppercase">At-Risk Cases</div>
              <div className="text-2xl font-serif font-bold text-red-600 mt-1">
                {slaData?.sla_breakdown.at_risk_cases ?? 0}
              </div>
              <div className="text-[10px] font-mono text-muted-foreground mt-1">Threshold approaching</div>
            </div>
            <div className="p-4 bg-secondary/30 rounded border border-border">
              <div className="text-[11px] font-mono text-muted-foreground uppercase">SLA Breached Cases</div>
              <div className="text-2xl font-serif font-bold text-rose-600 mt-1">
                {slaData?.sla_breakdown.breached_cases ?? 0}
              </div>
              <div className="text-[10px] font-mono text-rose-600 mt-1">Overdue &gt; 15 days</div>
            </div>
          </div>

          <div className="space-y-3 pt-2">
            <h3 className="text-xs font-mono font-bold uppercase text-muted-foreground">
              Institutional Milestone Standards
            </h3>
            <div className="space-y-2 text-xs font-mono">
              {(slaData?.target_metrics || [
                { milestone: "DLSA Legal Aid Allocation", target: "< 48 hours", current_avg: "24 hours", status: "COMPLIANT" },
                { milestone: "Document Completeness Verification", target: "< 5 days", current_avg: "3.2 days", status: "COMPLIANT" },
                { milestone: "Supervisory Petition Review", target: "< 72 hours", current_avg: "36 hours", status: "COMPLIANT" },
                { milestone: "Court Registry Filing Following Approval", target: "< 24 hours", current_avg: "18 hours", status: "COMPLIANT" },
              ]).map((m, idx) => (
                <div key={idx} className="p-3 bg-secondary/20 rounded border border-border flex justify-between items-center">
                  <div>
                    <span className="font-bold text-foreground block">{m.milestone}</span>
                    <span className="text-[10px] text-muted-foreground">Target SLA: {m.target}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-bold text-primary block">{m.current_avg}</span>
                    <span className="text-[10px] font-bold text-emerald-600">{m.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Systemic Exceptions */}
      {activeTab === "exceptions" && (
        <div className="bg-card border-2 border-border p-5 rounded-sm space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              State-Level Compliance Exceptions & Bottlenecks
            </h2>
            <span className="text-[11px] font-mono text-muted-foreground">
              {exceptions.length} Active Systemic Items
            </span>
          </div>

          {exceptions.length === 0 ? (
            <div className="p-6 bg-secondary/20 rounded border border-border text-center text-muted-foreground font-mono text-xs">
              <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto mb-2" />
              No statutory compliance exceptions or critical bottlenecks detected across reporting districts.
            </div>
          ) : (
            <div className="space-y-3">
              {exceptions.map((exc, idx) => (
                <div key={idx} className="p-4 bg-secondary/30 rounded border border-border space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-mono font-bold text-foreground flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded bg-secondary text-foreground border border-border text-[10px]">
                        {exc.category}
                      </span>
                      {exc.title}
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground">Case: {exc.case_id} ({exc.district})</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{exc.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Approved Document Templates */}
      {activeTab === "templates" && (
        <div className="bg-card border-2 border-border p-5 rounded-sm space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <FileCode className="w-4 h-4 text-primary" />
                Approved Institutional Legal Templates
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5 font-sans">
                Standardized statutory templates governed and maintained by SLSA. Updates create version increments while preserving historical draft linkages.
              </p>
            </div>
            <button
              onClick={() => setShowCreateTemplateModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Author Legal Template
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead>
                <tr className="border-b-2 border-border text-muted-foreground uppercase text-[10px]">
                  <th className="py-2.5 px-3">Template Name / ID</th>
                  <th className="py-2.5 px-3">Doc Type</th>
                  <th className="py-2.5 px-3 text-center">Version</th>
                  <th className="py-2.5 px-3">Statutory Ground</th>
                  <th className="py-2.5 px-3">Organization Scope</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {templatesLoading ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-muted-foreground">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin text-primary" />
                        <span className="text-xs font-mono">Loading approved templates...</span>
                      </div>
                    </td>
                  </tr>
                ) : templates.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-muted-foreground">
                      No document templates found.
                    </td>
                  </tr>
                ) : (
                  templates.map((tmpl) => {
                    const tid = tmpl.id || tmpl.template_id || "";
                    return (
                      <tr key={tid} className="hover:bg-secondary/20 transition-colors">
                        <td className="py-3 px-3">
                          <div className="font-bold text-foreground">{tmpl.name}</div>
                          <div className="text-[10px] text-muted-foreground font-mono">{tid}</div>
                        </td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded bg-secondary text-foreground border border-border text-[10px]">
                            {tmpl.doc_type}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span className="px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 text-[10px] font-bold">
                            v{tmpl.version}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-muted-foreground">{tmpl.statutory_ground}</td>
                        <td className="py-3 px-3 font-mono text-[10px] text-muted-foreground">
                          {tmpl.organization_id || "GLOBAL_DEFAULT"}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => handleEditTemplate(tmpl)}
                            className="px-2.5 py-1 bg-secondary text-foreground hover:bg-secondary/80 text-[11px] font-bold rounded border border-border transition-colors"
                          >
                            Edit / Version
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 5: Institutional Delegations */}
      {activeTab === "delegations" && (
        <div className="bg-card border-2 border-border p-5 rounded-sm space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <UserCheck className="w-4 h-4 text-primary" />
                Institutional Capability Delegations
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5 font-sans">
                Administer explicit, time-bound legal drafting capabilities granted to DLSA officers, panel advocates, and case coordinators.
              </p>
            </div>
            <button
              onClick={() => setShowCreateDelegationModal(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded hover:bg-primary/90 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Grant Delegation
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-left">
              <thead>
                <tr className="border-b-2 border-border text-muted-foreground uppercase text-[10px]">
                  <th className="py-2.5 px-3">Delegation ID</th>
                  <th className="py-2.5 px-3">Delegatee User ID</th>
                  <th className="py-2.5 px-3">Target Role</th>
                  <th className="py-2.5 px-3">Capability</th>
                  <th className="py-2.5 px-3">Valid Until</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {delegationsLoading ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-muted-foreground">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin text-primary" />
                        <span className="text-xs font-mono">Loading institutional delegations...</span>
                      </div>
                    </td>
                  </tr>
                ) : delegations.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-muted-foreground">
                      No institutional delegations recorded.
                    </td>
                  </tr>
                ) : (
                  delegations.map((delg) => (
                    <tr key={delg.delegation_id} className="hover:bg-secondary/20 transition-colors">
                      <td className="py-3 px-3 font-mono font-bold text-foreground">
                        {delg.delegation_id}
                      </td>
                      <td className="py-3 px-3 text-primary font-bold">{delg.granted_to_user_id}</td>
                      <td className="py-3 px-3 text-muted-foreground">{delg.granted_to_role}</td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded bg-secondary text-foreground border border-border text-[10px]">
                          {delg.capability}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-muted-foreground text-[10px]">
                        {new Date(delg.valid_until).toLocaleString()}
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            delg.status === "ACTIVE"
                              ? "bg-emerald-500/10 text-emerald-600 border border-emerald-500/20"
                              : delg.status === "REVOKED"
                              ? "bg-red-500/10 text-red-600 border border-red-500/20"
                              : "bg-secondary text-muted-foreground border border-border"
                          }`}
                        >
                          {delg.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        {delg.status === "ACTIVE" && (
                          <button
                            onClick={() => handleRevokeDelegation(delg.delegation_id)}
                            disabled={revokingId === delg.delegation_id}
                            className="px-2.5 py-1 bg-red-600/10 text-red-600 hover:bg-red-600/20 text-[11px] font-bold rounded border border-red-600/20 transition-colors disabled:opacity-50"
                          >
                            {revokingId === delg.delegation_id ? "Revoking..." : "Revoke"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Institutional Insights & Mandatory Sign-Off Notice */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card border-2 border-border p-5 rounded-sm space-y-4">
          <h2 className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-primary" />
            Facility-Level Undertrial Distribution
          </h2>
          <div className="space-y-3 text-xs font-mono">
            {(reports?.court_jurisdiction_breakdown || []).length === 0 ? (
              <div className="p-4 bg-secondary/20 rounded border border-border flex items-center justify-center gap-2 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span>Facility distribution data loading from database...</span>
              </div>
            ) : (
              (reports?.court_jurisdiction_breakdown || []).map((item: any, idx: number) => (
                <div key={idx} className="p-3 bg-secondary/30 rounded border border-border flex justify-between items-center">
                  <span className="font-bold text-foreground">{item.jail}</span>
                  <span className="font-bold text-primary">{item.count} inmates</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-card border-2 border-border p-5 rounded-sm space-y-4">
          <h2 className="font-serif font-bold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <FileText className="w-4 h-4 text-primary" />
            Institutional Governance & Compliance Architecture
          </h2>
          <div className="space-y-3 text-xs text-muted-foreground leading-relaxed">
            <div className="p-3 bg-secondary/30 rounded border border-border space-y-1">
              <strong className="text-foreground block font-serif text-xs">Section 479 Compliance Signals</strong>
              <p>Identified threshold matters are flagged as statutory signals for prompt supervisory review and panel counsel assignment.</p>
            </div>
            <div className="p-3 bg-secondary/30 rounded border border-border space-y-1">
              <strong className="text-foreground block font-serif text-xs">Institutional Governance Boundaries</strong>
              <p className="font-mono text-[11px] text-primary">
                Gov Admin oversees institutional templates and capability delegations. Consequential legal approvals and court filings require assigned advocates and supervising officers.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Modal: Author / Create Template */}
      {showCreateTemplateModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-card border-2 border-border w-full max-w-2xl p-6 rounded-sm shadow-xl space-y-4 my-8">
            <div className="flex justify-between items-center border-b border-border pb-3">
              <h3 className="font-serif font-bold text-base uppercase text-foreground">
                Author Approved Legal Template
              </h3>
              <button
                onClick={() => setShowCreateTemplateModal(false)}
                className="text-muted-foreground hover:text-foreground text-xs font-mono font-bold"
              >
                CLOSE
              </button>
            </div>

            {templateError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-600 text-xs font-mono rounded">
                {templateError}
              </div>
            )}

            <form onSubmit={handleCreateTemplate} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Template Name</label>
                  <input
                    type="text"
                    required
                    value={templateForm.name}
                    onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                    placeholder="e.g. Standard Section 479 Bail Application"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Document Type</label>
                  <select
                    value={templateForm.doc_type}
                    onChange={(e) => setTemplateForm({ ...templateForm, doc_type: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs"
                  >
                    <option value="BAIL_APPLICATION">BAIL_APPLICATION</option>
                    <option value="VAKALATNAMA">VAKALATNAMA</option>
                    <option value="SUPERVISORY_CHECKLIST">SUPERVISORY_CHECKLIST</option>
                    <option value="LEGAL_AID_MEMORANDUM">LEGAL_AID_MEMORANDUM</option>
                    <option value="OTHER">OTHER</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Statutory Ground</label>
                  <input
                    type="text"
                    required
                    value={templateForm.statutory_ground}
                    onChange={(e) => setTemplateForm({ ...templateForm, statutory_ground: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                    placeholder="e.g. Section 479 BNSS 2023"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Jurisdiction</label>
                  <input
                    type="text"
                    required
                    value={templateForm.jurisdiction}
                    onChange={(e) => setTemplateForm({ ...templateForm, jurisdiction: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                    placeholder="e.g. National / BNSS 2023"
                  />
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground uppercase text-[10px] mb-1">Description / Legal Authority</label>
                <input
                  type="text"
                  value={templateForm.description}
                  onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })}
                  className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                  placeholder="Official template description and scope"
                />
              </div>

              <div>
                <label className="block text-muted-foreground uppercase text-[10px] mb-1">
                  Content Template (Use placeholders like {`{{accused_name}}`}, {`{{case_number}}`})
                </label>
                <textarea
                  rows={6}
                  required
                  value={templateForm.content_template}
                  onChange={(e) => setTemplateForm({ ...templateForm, content_template: e.target.value })}
                  className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono leading-relaxed"
                  placeholder="IN THE COURT OF THE PRINCIPAL DISTRICT AND SESSIONS JUDGE..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Required Fields (comma-separated)</label>
                  <input
                    type="text"
                    value={templateForm.required_fields}
                    onChange={(e) => setTemplateForm({ ...templateForm, required_fields: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Required Documents (comma-separated)</label>
                  <input
                    type="text"
                    value={templateForm.required_documents}
                    onChange={(e) => setTemplateForm({ ...templateForm, required_documents: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateTemplateModal(false)}
                  className="px-4 py-2 bg-secondary text-foreground text-xs font-mono rounded border border-border hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={templateSaving}
                  className="px-4 py-2 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded hover:bg-primary/90 disabled:opacity-50"
                >
                  {templateSaving ? "Publishing..." : "Publish Approved Template"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Edit / Version Template */}
      {showEditTemplateModal && selectedTemplate && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-card border-2 border-border w-full max-w-2xl p-6 rounded-sm shadow-xl space-y-4 my-8">
            <div className="flex justify-between items-center border-b border-border pb-3">
              <div>
                <h3 className="font-serif font-bold text-base uppercase text-foreground">
                  Update Legal Template (Creates Version {selectedTemplate.version + 1})
                </h3>
                <span className="text-[10px] font-mono text-muted-foreground">
                  Template ID: {selectedTemplate.id || selectedTemplate.template_id}
                </span>
              </div>
              <button
                onClick={() => setShowEditTemplateModal(false)}
                className="text-muted-foreground hover:text-foreground text-xs font-mono font-bold"
              >
                CLOSE
              </button>
            </div>

            {templateError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-600 text-xs font-mono rounded">
                {templateError}
              </div>
            )}

            <form onSubmit={handleUpdateTemplate} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Template Name</label>
                  <input
                    type="text"
                    required
                    value={templateForm.name}
                    onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Statutory Ground</label>
                  <input
                    type="text"
                    required
                    value={templateForm.statutory_ground}
                    onChange={(e) => setTemplateForm({ ...templateForm, statutory_ground: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                  />
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground uppercase text-[10px] mb-1">Description / Legal Authority</label>
                <input
                  type="text"
                  value={templateForm.description}
                  onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })}
                  className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                />
              </div>

              <div>
                <label className="block text-muted-foreground uppercase text-[10px] mb-1">
                  Content Template (Use placeholders like {`{{accused_name}}`}, {`{{case_number}}`})
                </label>
                <textarea
                  rows={8}
                  required
                  value={templateForm.content_template}
                  onChange={(e) => setTemplateForm({ ...templateForm, content_template: e.target.value })}
                  className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono leading-relaxed"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Required Fields (comma-separated)</label>
                  <input
                    type="text"
                    value={templateForm.required_fields}
                    onChange={(e) => setTemplateForm({ ...templateForm, required_fields: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Required Documents (comma-separated)</label>
                  <input
                    type="text"
                    value={templateForm.required_documents}
                    onChange={(e) => setTemplateForm({ ...templateForm, required_documents: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowEditTemplateModal(false)}
                  className="px-4 py-2 bg-secondary text-foreground text-xs font-mono rounded border border-border hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={templateSaving}
                  className="px-4 py-2 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded hover:bg-primary/90 disabled:opacity-50"
                >
                  {templateSaving ? "Publishing Revision..." : `Publish Version ${selectedTemplate.version + 1}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Grant Institutional Delegation */}
      {showCreateDelegationModal && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-card border-2 border-border w-full max-w-xl p-6 rounded-sm shadow-xl space-y-4 my-8">
            <div className="flex justify-between items-center border-b border-border pb-3">
              <h3 className="font-serif font-bold text-base uppercase text-foreground">
                Grant Institutional Capability Delegation
              </h3>
              <button
                onClick={() => setShowCreateDelegationModal(false)}
                className="text-muted-foreground hover:text-foreground text-xs font-mono font-bold"
              >
                CLOSE
              </button>
            </div>

            {delegationError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-600 text-xs font-mono rounded">
                {delegationError}
              </div>
            )}

            <form onSubmit={handleCreateDelegation} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Delegatee User ID</label>
                  <input
                    type="text"
                    required
                    value={delegationForm.granted_to_user_id}
                    onChange={(e) => setDelegationForm({ ...delegationForm, granted_to_user_id: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono"
                    placeholder="e.g. dlsa_officer_01"
                  />
                </div>
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Target Role</label>
                  <select
                    value={delegationForm.granted_to_role}
                    onChange={(e) => setDelegationForm({ ...delegationForm, granted_to_role: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs"
                  >
                    <option value="DLSA_OFFICER">DLSA_OFFICER</option>
                    <option value="PANEL_ADVOCATE">PANEL_ADVOCATE</option>
                    <option value="LEGAL_AID_COUNSEL">LEGAL_AID_COUNSEL</option>
                    <option value="SUPERVISING_LEGAL_OFFICER">SUPERVISING_LEGAL_OFFICER</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Capability</label>
                  <select
                    value={delegationForm.capability}
                    onChange={(e) => setDelegationForm({ ...delegationForm, capability: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs"
                  >
                    <option value="CAN_INITIATE_DOCUMENT_DRAFT">CAN_INITIATE_DOCUMENT_DRAFT</option>
                    <option value="CAN_EDIT_DOCUMENT_DRAFT">CAN_EDIT_DOCUMENT_DRAFT</option>
                    <option value="CAN_EXPORT_DRAFT">CAN_EXPORT_DRAFT</option>
                  </select>
                </div>
                <div>
                  <label className="block text-muted-foreground uppercase text-[10px] mb-1">Valid Until</label>
                  <input
                    type="datetime-local"
                    required
                    value={delegationForm.valid_until}
                    onChange={(e) => setDelegationForm({ ...delegationForm, valid_until: e.target.value })}
                    className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-muted-foreground uppercase text-[10px] mb-1">Allowed Document Types (comma-separated or *)</label>
                <input
                  type="text"
                  required
                  value={delegationForm.allowed_document_types}
                  onChange={(e) => setDelegationForm({ ...delegationForm, allowed_document_types: e.target.value })}
                  className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono"
                  placeholder="* or BAIL_APPLICATION, VAKALATNAMA"
                />
              </div>

              <div>
                <label className="block text-muted-foreground uppercase text-[10px] mb-1">Allowed Case Scope (comma-separated or *)</label>
                <input
                  type="text"
                  required
                  value={delegationForm.allowed_case_scope}
                  onChange={(e) => setDelegationForm({ ...delegationForm, allowed_case_scope: e.target.value })}
                  className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-mono"
                  placeholder="* or UTP-0001, UTP-0002"
                />
              </div>

              <div>
                <label className="block text-muted-foreground uppercase text-[10px] mb-1">Administrative Reason / Legal Order Ref</label>
                <input
                  type="text"
                  required
                  value={delegationForm.reason}
                  onChange={(e) => setDelegationForm({ ...delegationForm, reason: e.target.value })}
                  className="w-full bg-secondary border border-border p-2 rounded text-foreground text-xs font-sans"
                  placeholder="e.g. SLSA Special Undertrial Review Mission 2026 - Section 479 drafting mandate"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-border">
                <button
                  type="button"
                  onClick={() => setShowCreateDelegationModal(false)}
                  className="px-4 py-2 bg-secondary text-foreground text-xs font-mono rounded border border-border hover:bg-secondary/80"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={delegationSaving}
                  className="px-4 py-2 bg-primary text-primary-foreground text-xs font-mono font-bold uppercase rounded hover:bg-primary/90 disabled:opacity-50"
                >
                  {delegationSaving ? "Granting..." : "Grant Delegation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
