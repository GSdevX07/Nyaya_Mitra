/**
 * API Service for Nyaya Mitra Frontend
 * Accused-Centric Legal-Services Operations & Coordination Platform
 * Connects to FastAPI backend on http://localhost:8000
 * Automatically attaches scoped JWT Bearer tokens to all requests.
 */

import { getAuthToken } from "./auth";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(input, { ...init, headers });
}

export type PrisonerCategory = "UNDERTRIAL" | "CONVICTED";
export type LegalCode = "BNS_2023" | "IPC_1860" | "SPECIAL_ACTS";
export type DataSourceStatus = "DEMO_SYNTHETIC" | "MANUAL_INSTITUTIONAL_ENTRY" | "DOCUMENT_INGESTION" | "FUTURE_GOVERNMENT_API";
export type StakeholderPerspective = "ALL" | "JAIL" | "DLSA" | "SLSA" | "ADVOCATE" | "ACCUSED";

export interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  actor: string;
  actor_role: string;
  source: string;
  is_human_verified: boolean;
}

export interface LegalNeedItem {
  need_type: string;
  title: string;
  description: string;
  urgency: string;
  blocking_bail_workflow: boolean;
  status: string;
}

export interface AppealMetadata {
  conviction_date: string;
  trial_court_name: string;
  sentence_awarded_days: number;
  appellate_forum: string;
  judgment_document_available: boolean;
  limitation_status: string;
  appeal_preparation_status: string;
}

export interface PostReleaseDetails {
  release_date: string;
  release_order_reference: string;
  surety_type: string;
  preservation_status: string;
  follow_up_notes?: string;
}

export interface CaseRecordData {
  case_id: string;
  name: string;
  prisoner_category: PrisonerCategory;
  legal_code: LegalCode;
  offense_sections: string[];
  offense_summary?: string;
  cnr_number?: string;
  fir_number?: string;
  police_station?: string;
  court_name?: string;
  district?: string;
  state?: string;
  dlsa_reference_number?: string;
  arrest_date: string;
  custody_days: number;
  excluded_delay_days: number;
  max_sentence_days_for_offense: number;
  punishable_by_death_or_life: boolean;
  multiple_active_cases: boolean;
  prior_bail_orders: string[];
  required_docs: string[];
  present_docs: string[];
  urgency_flags: {
    age: number;
    health_flag: boolean;
    health_details?: string;
    repeat_offender: boolean;
  };
  jail_location: string;
  preferred_language: string;
  relative_name?: string;
  relative_relation?: string;
  relative_phone?: string;
  permanent_address?: string;
  assignment_status?: string;
  assigned_lawyer_id?: string;
  status?: string;
  data_source_status: DataSourceStatus;
  legal_needs?: LegalNeedItem[];
  timeline?: TimelineEvent[];
  data_provenance?: Record<string, any>;
  appeal_details?: AppealMetadata;
  post_release_details?: PostReleaseDetails;
}

export type CaseRecord = CaseRecordData;

export interface BackendCaseSummary {
  case: CaseRecordData;
  days_overdue: number;
  urgency_score: number;
  eligibility?: {
    is_eligible: boolean;
    statutory_threshold_fraction: string;
    threshold_days: number;
    countable_custody_days: number;
    days_overdue: number;
    legal_rule_version: string;
    reasons: string[];
    statutory_conditions: string[];
    requires_human_legal_review: boolean;
    review_warning?: string;
  };
}

export interface StakeholdersOverview {
  jail_view: {
    title: string;
    total_inmates_monitored: number;
    undertrials_count: number;
    convicted_count: number;
    missing_records_count: number;
    legal_aid_requested_count: number;
    operational_note: string;
  };
  dlsa_view: {
    title: string;
    statutory_eligibility_signals: number;
    high_urgency_cases: number;
    unassigned_legal_aid_demand: number;
    document_bottlenecks: number;
    assigned_active_counsel: number;
  };
  slsa_view: {
    title: string;
    districts_reporting: number;
    total_undertrials_tracked: number;
    aggregate_eligible_milestones: number;
    institutional_resolution_rate: string;
    privacy_notice: string;
  };
  advocate_view: {
    title: string;
    active_briefs: number;
    ready_for_filing_petitions: number;
    hearings_this_month: number;
    evidence_vault_items: number;
  };
}

// ── API Operations ───────────────────────────────────────────────────────────

export interface JailInmateRecord {
  case: CaseRecord;
  inmate_id: string;
  name: string;
  jail_location: string;
  admission_date: string;
  custody_days: number;
  excluded_delay_days?: number;
  countable_days: number;
  required_docs: string[];
  present_docs: string[];
  missing_docs: string[];
  is_docs_complete: boolean;
  assignment_status: string;
  assigned_lawyer?: string;
  assigned_lawyer_id?: string;
  legal_code: string;
  offense_sections: string[];
  status: string;
  urgency_flags: any;
  potential_479_eligible: boolean;
}

export async function fetchJailInmates(): Promise<JailInmateRecord[]> {
  try {
    const res = await authFetch(`${API_BASE_URL}/jail/inmates`);
    if (!res.ok) throw new Error(`Failed to fetch jail inmates: status ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend jail inmates unavailable or unauthenticated:", err);
    return [];
  }
}

export async function referJailCaseToDlsa(caseId: string, notes?: string) {
  const res = await authFetch(`${API_BASE_URL}/jail/refer-legal-aid`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId, notes }),
  });
  if (!res.ok) throw new Error(`Referral failed: status ${res.status}`);
  return await res.json();
}

export async function fetchCases(): Promise<BackendCaseSummary[]> {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases`);
    if (!res.ok) throw new Error(`Failed to fetch cases: status ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend API unavailable or unauthenticated:", err);
    return [];
  }
}

export async function fetchStakeholdersOverview(): Promise<StakeholdersOverview | null> {
  try {
    const res = await authFetch(`${API_BASE_URL}/stakeholders/overview`);
    if (!res.ok) throw new Error("Failed to fetch stakeholder overview");
    return await res.json();
  } catch (err) {
    console.warn("Backend stakeholder overview fallback:", err);
    return null;
  }
}

export async function takeUpCase(caseId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/take`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Take up case failed");
    return await res.json();
  } catch (err) {
    console.error("Error taking up case:", err);
    throw err;
  }
}

export async function declineCase(caseId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/decline`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Decline case failed");
    return await res.json();
  } catch (err) {
    console.error("Error declining case:", err);
    throw err;
  }
}

export async function approveCaseInBackend(caseId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/approve`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Approval failed");
    return await res.json();
  } catch (err) {
    console.error("Error approving case:", err);
    throw err;
  }
}

export async function fileCaseInCourt(caseId: string, filingRef?: string) {
  try {
    const query = filingRef ? `?filing_reference=${encodeURIComponent(filingRef)}` : "";
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/file${query}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Filing failed");
    return await res.json();
  } catch (err) {
    console.error("Error filing case in court:", err);
    throw err;
  }
}

export async function fetchCaseById(caseId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}`);
    if (!res.ok) throw new Error(`Failed to fetch case ${caseId}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend API failed for case ${caseId}:`, err);
    return null;
  }
}

export async function fetchCaseTimeline(caseId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/timeline`);
    if (!res.ok) throw new Error(`Failed to fetch timeline for ${caseId}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend API timeline fallback:", err);
    return null;
  }
}

export async function fetchLawyerProfile() {
  try {
    const res = await authFetch(`${API_BASE_URL}/lawyer/profile`);
    if (!res.ok) throw new Error("Failed to fetch lawyer profile");
    return await res.json();
  } catch (err) {
    console.warn("Backend API lawyer profile fallback:", err);
    return {
      id: "Legal Officer",
      full_name: "Adv. Panel Counsel",
      bar_association_id: "DL/2018/49281",
      email: "counsel@nyayamitra.gov.in",
      phone: "+91 98112 34567",
      specialization: "Undertrial Defense & Section 479 BNSS",
      cases_taken: 3,
      status: "Active Pro Bono Counsel",
      organization: "District Legal Services Authority (DLSA)",
    };
  }
}

export async function fetchDocuments() {
  try {
    const res = await authFetch(`${API_BASE_URL}/documents`);
    if (!res.ok) throw new Error("Failed to fetch documents");
    return await res.json();
  } catch (err) {
    console.warn("Backend API documents unavailable:", err);
    return [];
  }
}

export async function uploadDocumentFile(
  caseId: string,
  documentType: string,
  file?: File,
  customText?: string
): Promise<{
  status: string;
  message: string;
  present_docs: string[];
  is_complete: boolean;
  is_handwritten: boolean;
  ocr_engine: string;
  extracted_text: string;
  file_name: string;
  file_size_bytes: number;
  file_hash: string;
}> {
  const formData = new FormData();
  if (file) formData.append("file", file);
  if (customText) formData.append("custom_text", customText);

  const res = await authFetch(
    `${API_BASE_URL}/documents/upload?case_id=${encodeURIComponent(caseId)}&document_type=${encodeURIComponent(documentType)}`,
    { method: "POST", body: formData }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function uploadDocument(caseId: string, documentType: string) {
  return uploadDocumentFile(caseId, documentType, undefined, undefined);
}

export async function getUploadedDocuments(caseId: string): Promise<
  Array<{
    id: string;
    case_id: string;
    document_type: string;
    file_name: string;
    extracted_text: string;
    custom_text: string;
    is_handwritten: boolean;
    ocr_engine: string;
    file_hash: string;
    file_size_bytes: number;
    mime_type: string;
    uploaded_at: string;
  }>
> {
  try {
    const res = await authFetch(`${API_BASE_URL}/documents/uploaded/${encodeURIComponent(caseId)}`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function fetchEvidence() {
  try {
    const res = await authFetch(`${API_BASE_URL}/evidence`);
    if (!res.ok) throw new Error("Failed to fetch evidence");
    return await res.json();
  } catch (err) {
    console.warn("Backend API evidence unavailable:", err);
    return [];
  }
}

export async function verifyEvidence(evidenceId: string) {
  const res = await authFetch(
    `${API_BASE_URL}/evidence/verify?evidence_id=${encodeURIComponent(evidenceId)}`,
    { method: "POST" }
  );
  const body = await res.json();
  if (!res.ok) {
    // Return a typed error shape so the caller can display it without crashing
    return {
      error: body?.detail ?? `HTTP ${res.status} — Verification request rejected.`,
      integrity_verified: false,
      stored_hash: null,
      computed_hash: null,
    };
  }
  return body;
}

export async function fetchActions() {
  try {
    const res = await authFetch(`${API_BASE_URL}/actions`);
    if (!res.ok) throw new Error("Failed to fetch actions");
    return await res.json();
  } catch (err) {
    console.warn("Backend API actions unavailable:", err);
    return [];
  }
}

export async function triggerAction(actionId: string) {
  try {
    const res = await authFetch(
      `${API_BASE_URL}/actions/trigger?action_id=${encodeURIComponent(actionId)}`,
      { method: "POST" }
    );
    return await res.json();
  } catch (err) {
    console.error("Trigger action error:", err);
    throw err;
  }
}

export async function fetchHearings() {
  try {
    const res = await authFetch(`${API_BASE_URL}/hearings`);
    if (!res.ok) throw new Error("Failed to fetch hearings");
    return await res.json();
  } catch (err) {
    console.warn("Backend API hearings unavailable:", err);
    return [];
  }
}

export async function fetchReports() {
  try {
    const res = await authFetch(`${API_BASE_URL}/reports`);
    if (!res.ok) throw new Error("Failed to fetch reports");
    return await res.json();
  } catch (err) {
    console.warn("Backend API reports unavailable:", err);
    return null;
  }
}

export async function fetchNotifications() {
  try {
    const res = await authFetch(`${API_BASE_URL}/notifications`);
    if (!res.ok) throw new Error("Failed to fetch notifications");
    return await res.json();
  } catch (err) {
    console.warn("Backend API notifications unavailable:", err);
    return [];
  }
}

export async function assessUploadedDocument(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await authFetch(`${API_BASE_URL}/documents/assess`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => null);
    throw new Error(error?.detail || "Document assessment API error");
  }
  return res.json();
}

export async function assessDocument(fileOrName?: any, textContent?: string) {
  if (fileOrName instanceof File) {
    return assessUploadedDocument(fileOrName);
  }
  const file = new File([textContent || "Sample judicial record"], fileOrName || "document.pdf", { type: "text/plain" });
  return assessUploadedDocument(file);
}

export async function fetchSampleDocuments() {
  return fetchDocuments();
}

export async function fetchCitizenCase() {
  const res = await authFetch(`${API_BASE_URL}/citizen/my-case`);
  if (!res.ok) {
    throw new Error(`Failed to fetch citizen case: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchAccusedProfile(accusedId: string) {
  const res = await authFetch(`${API_BASE_URL}/accused/${encodeURIComponent(accusedId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch accused profile: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchAccusedTimeline(accusedId: string) {
  const res = await authFetch(`${API_BASE_URL}/accused/${encodeURIComponent(accusedId)}/timeline`);
  if (!res.ok) {
    throw new Error(`Failed to fetch accused timeline: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchDuplicateCandidates() {
  const res = await authFetch(`${API_BASE_URL}/accused/duplicates/candidates`);
  if (!res.ok) {
    throw new Error(`Failed to fetch duplicate candidates: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function resolveDuplicateCandidate(payload: {
  candidate_id: string;
  action: string;
  resolution_notes?: string;
  target_canonical_id?: string;
}) {
  const res = await authFetch(`${API_BASE_URL}/accused/duplicates/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new Error(err?.detail || `Failed to resolve duplicate: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchDemoUsers() {
  const res = await authFetch(`${API_BASE_URL}/auth/demo-users`);
  if (!res.ok) {
    throw new Error(`Failed to fetch demo users: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchAuditEvents(limit: number = 50) {
  try {
    const res = await authFetch(`${API_BASE_URL}/audit-events?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to fetch audit events: HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend audit events unavailable:", err);
    return [];
  }
}

export async function fetchCurrentUserProfile() {
  try {
    const res = await authFetch(`${API_BASE_URL}/auth/me`);
    if (!res.ok) throw new Error(`Failed to fetch current user: HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend /auth/me unavailable:", err);
    return null;
  }
}

// ── Governed Legal Knowledge Layer API ────────────────────────────────────────

export async function fetchLegalSources(domain?: string, lifecycleStatus?: string, jurisdiction?: string) {
  try {
    const params = new URLSearchParams();
    if (domain) params.append("domain", domain);
    if (lifecycleStatus && lifecycleStatus !== "ALL") params.append("lifecycle_status", lifecycleStatus);
    if (jurisdiction) params.append("jurisdiction", jurisdiction);
    const url = `${API_BASE_URL}/api/legal-sources${params.toString() ? `?${params.toString()}` : ""}`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`Failed to fetch legal sources: HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Legal sources fetch fallback:", err);
    return [];
  }
}

export async function fetchLegalSourceDetail(sourceId: string) {
  const res = await authFetch(`${API_BASE_URL}/api/legal-sources/${sourceId}`);
  if (!res.ok) throw new Error(`Failed to fetch source details: HTTP ${res.status}`);
  return await res.json();
}

export async function createLegalSource(data: any) {
  const res = await authFetch(`${API_BASE_URL}/api/legal-sources`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to create legal source: HTTP ${res.status}`);
  return await res.json();
}

export async function updateLegalSourceLifecycle(sourceId: string, status: string, notes?: string, supersededById?: string) {
  const res = await authFetch(`${API_BASE_URL}/api/legal-sources/${sourceId}/lifecycle`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, notes, superseded_by_id: supersededById }),
  });
  if (!res.ok) throw new Error(`Failed to update lifecycle: HTTP ${res.status}`);
  return await res.json();
}

export async function retrieveLegalKnowledge(query: string, domain?: string, includeSuperseded: boolean = false, limit: number = 5) {
  const res = await authFetch(`${API_BASE_URL}/api/legal-knowledge/retrieve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, domain, include_superseded: includeSuperseded, limit }),
  });
  if (!res.ok) throw new Error(`Failed to retrieve legal knowledge: HTTP ${res.status}`);
  return await res.json();
}

export async function verifyCitationIntegrity(draftStatement: string) {
  const res = await authFetch(`${API_BASE_URL}/api/legal-knowledge/verify-citations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ draft_statement: draftStatement }),
  });
  if (!res.ok) throw new Error(`Failed to verify citation integrity: HTTP ${res.status}`);
  return await res.json();
}

export async function runLegalKnowledgeEvaluation() {
  const res = await authFetch(`${API_BASE_URL}/api/legal-knowledge/evaluate`);
  if (!res.ok) throw new Error(`Failed to run legal evaluation: HTTP ${res.status}`);
  return await res.json();
}

export async function fetchLegalEscalations(status: string = "PENDING_REVIEW") {
  const res = await authFetch(`${API_BASE_URL}/api/legal-knowledge/escalations?status=${encodeURIComponent(status)}`);
  if (!res.ok) throw new Error(`Failed to fetch legal escalations: HTTP ${res.status}`);
  return await res.json();
}

export async function resolveLegalEscalation(escalationId: string, notes: string, status: string = "RESOLVED") {
  const res = await authFetch(`${API_BASE_URL}/api/legal-knowledge/escalations/${escalationId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes, status }),
  });
  if (!res.ok) throw new Error(`Failed to resolve legal escalation: HTTP ${res.status}`);
  return await res.json();
}



