/**
 * API Service for Nyaya Mitra Frontend
 * Accused-Centric Legal-Services Operations & Coordination Platform
 * Connects to FastAPI backend on http://localhost:8000
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

export async function fetchCases(): Promise<BackendCaseSummary[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/cases`);
    if (!res.ok) throw new Error("Failed to fetch cases");
    return await res.json();
  } catch (err) {
    console.warn("Backend API unavailable, using fallback mock data:", err);
    return [];
  }
}

export async function fetchStakeholdersOverview(): Promise<StakeholdersOverview | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/stakeholders/overview`);
    if (!res.ok) throw new Error("Failed to fetch stakeholder overview");
    return await res.json();
  } catch (err) {
    console.warn("Backend stakeholder overview fallback:", err);
    return null;
  }
}

export async function takeUpCase(caseId: string, lawyerId: string = "Legal Officer 104") {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/take?lawyer_id=${encodeURIComponent(lawyerId)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Take up case failed");
    return await res.json();
  } catch (err) {
    console.error("Error taking up case:", err);
    throw err;
  }
}

export async function declineCase(caseId: string, lawyerId: string = "Legal Officer 104") {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/decline?lawyer_id=${encodeURIComponent(lawyerId)}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Decline case failed");
    return await res.json();
  } catch (err) {
    console.error("Error declining case:", err);
    throw err;
  }
}

export async function approveCaseInBackend(caseId: string, lawyerId: string = "Legal Officer 104") {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/approve?lawyer_id=${encodeURIComponent(lawyerId)}`, {
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
    const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/file${query}`, {
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
    const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}`);
    if (!res.ok) throw new Error(`Failed to fetch case ${caseId}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend API failed for case ${caseId}:`, err);
    return null;
  }
}

export async function fetchCaseTimeline(caseId: string) {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/timeline`);
    if (!res.ok) throw new Error(`Failed to fetch timeline for ${caseId}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend API timeline fallback:", err);
    return null;
  }
}

export async function fetchLawyerProfile() {
  try {
    const res = await fetch(`${API_BASE_URL}/lawyer/profile`);
    if (!res.ok) throw new Error("Failed to fetch lawyer profile");
    return await res.json();
  } catch (err) {
    console.warn("Backend API lawyer profile fallback:", err);
    return {
      id: "Legal Officer 104",
      full_name: "Adv. Rajesh Sharma",
      bar_association_id: "DL/2018/49281",
      email: "rajesh.sharma@nyayamitra.org",
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
    const res = await fetch(`${API_BASE_URL}/documents`);
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

  const res = await fetch(
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
    const res = await fetch(`${API_BASE_URL}/documents/uploaded/${encodeURIComponent(caseId)}`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function fetchEvidence() {
  try {
    const res = await fetch(`${API_BASE_URL}/evidence`);
    if (!res.ok) throw new Error("Failed to fetch evidence");
    return await res.json();
  } catch (err) {
    console.warn("Backend API evidence unavailable:", err);
    return [];
  }
}

export async function verifyEvidence(evidenceId: string) {
  try {
    const res = await fetch(
      `${API_BASE_URL}/evidence/verify?evidence_id=${encodeURIComponent(evidenceId)}`,
      { method: "POST" }
    );
    return await res.json();
  } catch (err) {
    console.error("Evidence verify error:", err);
    throw err;
  }
}

export async function fetchActions() {
  try {
    const res = await fetch(`${API_BASE_URL}/actions`);
    if (!res.ok) throw new Error("Failed to fetch actions");
    return await res.json();
  } catch (err) {
    console.warn("Backend API actions unavailable:", err);
    return [];
  }
}

export async function triggerAction(actionId: string) {
  try {
    const res = await fetch(
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
    const res = await fetch(`${API_BASE_URL}/hearings`);
    if (!res.ok) throw new Error("Failed to fetch hearings");
    return await res.json();
  } catch (err) {
    console.warn("Backend API hearings unavailable:", err);
    return [];
  }
}

export async function fetchReports() {
  try {
    const res = await fetch(`${API_BASE_URL}/reports`);
    if (!res.ok) throw new Error("Failed to fetch reports");
    return await res.json();
  } catch (err) {
    console.warn("Backend API reports unavailable:", err);
    return null;
  }
}

export async function fetchNotifications() {
  try {
    const res = await fetch(`${API_BASE_URL}/notifications`);
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
  const res = await fetch(`${API_BASE_URL}/documents/assess`, {
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

