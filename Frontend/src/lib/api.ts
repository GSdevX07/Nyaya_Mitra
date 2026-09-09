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
  assigned_lawyer?: string;
  assigned_lawyer_id?: string;
  police_station_id?: string;
  status?: string;
  data_source_status: DataSourceStatus;
  legal_needs?: LegalNeedItem[];
  timeline?: TimelineEvent[];
  data_provenance?: Record<string, any>;
  appeal_details?: AppealMetadata;
  post_release_details?: PostReleaseDetails;
}

export type CaseRecord = CaseRecordData;

export interface RuleExplanationData {
  rule_id: string;
  rule_version: string;
  jurisdiction: string;
  legal_source: string;
  effective_date: string;
  input_facts_used: Record<string, any>;
  input_provenance?: Record<string, any>;
  calculation_performed: Record<string, any>;
  conditions_evaluated: Array<{
    condition_name: string;
    satisfied?: boolean | null;
    reason: string;
    facts_used?: Record<string, any>;
    statutory_reference?: string;
  }>;
  exclusions_provisos_evaluated: Array<{
    proviso_name: string;
    applies: boolean;
    statutory_text?: string;
    facts_used?: Record<string, any>;
  }>;
  missing_or_conflicting_inputs?: Array<{
    type: string;
    field: string;
    reason?: string;
    source_a?: string;
    source_b?: string;
    details?: string;
  }>;
  machine_status: "THRESHOLD_REACHED" | "THRESHOLD_NOT_REACHED" | "POTENTIALLY_APPLICABLE" | "INSUFFICIENT_DATA" | "EXCLUDED" | "MANUAL_REVIEW";
  explanation_text: string;
  manual_review_reason?: string;
  disclaimer: string;
}

export interface StatutoryEligibilityData {
  is_eligible: boolean;
  eligible?: boolean;
  statutory_threshold_fraction: string;
  threshold_fraction?: number;
  threshold_days: number;
  countable_custody_days: number;
  total_elapsed_calendar_days?: number;
  excluded_delay_days?: number;
  days_overdue: number;
  machine_status?: "THRESHOLD_REACHED" | "THRESHOLD_NOT_REACHED" | "POTENTIALLY_APPLICABLE" | "INSUFFICIENT_DATA" | "EXCLUDED" | "MANUAL_REVIEW";
  legal_rule_version?: string;
  rule_version?: string;
  reasons?: string[];
  statutory_conditions?: string[];
  requires_human_legal_review?: boolean;
  human_review_required?: boolean;
  review_warning?: string;
  explanation?: RuleExplanationData;
  execution_id?: string;
}

export interface BackendCaseSummary {
  case: CaseRecordData;
  days_overdue: number;
  urgency_score: number;
  eligibility?: StatutoryEligibilityData;
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

export interface PoliceCaseSummary {
  case_id: string;
  name: string;
  fir_number: string;
  police_station?: string;
  police_station_id?: string;
  district?: string;
  state?: string;
  offense_sections: string[];
  arrest_date: string;
  custody_days: number;
  jail_location: string;
  court_name: string;
  legal_code: string;
  remand_order_present: boolean;
  charge_sheet_present: boolean;
  charge_sheet_status: string;
  remand_status: string;
  status: string;
}

export interface PoliceActionItem {
  id: string;
  case_id: string;
  police_station_id: string;
  action_type: string;
  title: string;
  description?: string;
  requested_by?: string;
  status: "PENDING" | "ACKNOWLEDGED" | "COMPLETED";
  document_id?: string;
  notes?: string;
  created_at: string;
  completed_at?: string;
}

export async function fetchPoliceCases(): Promise<PoliceCaseSummary[]> {
  try {
    const res = await authFetch(`${API_BASE_URL}/police/cases`);
    if (!res.ok) throw new Error(`Failed to fetch police cases: status ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend police cases unavailable or unauthenticated:", err);
    return [];
  }
}

export async function fetchPoliceActions(): Promise<PoliceActionItem[]> {
  try {
    const res = await authFetch(`${API_BASE_URL}/police/actions`);
    if (!res.ok) throw new Error(`Failed to fetch police actions: status ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend police actions unavailable or unauthenticated:", err);
    return [];
  }
}

export async function acknowledgePoliceAction(actionId: string, notes?: string) {
  const res = await authFetch(`${API_BASE_URL}/police/actions/${actionId}/acknowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  });
  if (!res.ok) throw new Error(`Failed to acknowledge action: status ${res.status}`);
  return await res.json();
}

export async function completePoliceAction(actionId: string, documentId: string, notes?: string) {
  const res = await authFetch(`${API_BASE_URL}/police/actions/${actionId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, notes }),
  });
  if (!res.ok) throw new Error(`Failed to complete action: status ${res.status}`);
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

export async function submitCaseComment(caseId: string, comment: string, targetRole?: string): Promise<{ status: string; message: string }> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment, target_role: targetRole || "DEFENSE_ADVOCATE" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit comment");
  }
  return await res.json();
}

export async function signOffCase(caseId: string, draftText?: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/sign-off`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft_text: draftText }),
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      const detailMsg = typeof errJson.detail === "string" ? errJson.detail : (errJson.detail?.message || "Counsel sign-off failed");
      const errorObj = new Error(detailMsg) as any;
      errorObj.status = res.status;
      errorObj.detail = errJson.detail;
      throw errorObj;
    }
    return await res.json();
  } catch (err) {
    console.error("Error signing off case:", err);
    throw err;
  }
}

export async function saveCaseDraft(caseId: string, draftText: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/save-draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft_text: draftText }),
    });
    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}));
      const detailMsg = typeof errJson.detail === "string" ? errJson.detail : (errJson.detail?.message || "Failed to save draft changes");
      const errorObj = new Error(detailMsg) as any;
      errorObj.status = res.status;
      errorObj.detail = errJson.detail;
      throw errorObj;
    }
    return await res.json();
  } catch (err) {
    console.error("Error saving case draft:", err);
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
    if (!res.ok) {
      if (res.status === 403) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || "Access Restricted: You are not authorized to access this case dossier.");
      }
      throw new Error(`Failed to fetch case ${caseId}`);
    }
    return await res.json();
  } catch (err) {
    console.warn(`Backend API failed for case ${caseId}:`, err);
    throw err;
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

export async function fetchCaseDocuments(caseId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/cases/${caseId}/documents`);
    if (!res.ok) throw new Error("Failed to fetch case documents");
    return await res.json();
  } catch (err) {
    console.warn(`Backend API case documents unavailable for ${caseId}:`, err);
    return null;
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
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.message || `Action dispatch failed: HTTP ${res.status}`);
    }
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

export async function clearNotificationsApi(notificationId?: string) {
  try {
    const url = notificationId
      ? `${API_BASE_URL}/notifications?id=${encodeURIComponent(notificationId)}`
      : `${API_BASE_URL}/notifications`;
    const res = await authFetch(url, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to clear notifications");
    return await res.json();
  } catch (err) {
    console.warn("Backend API clear notifications error:", err);
    return { status: "cleared_locally", cleared_count: 0 };
  }
}

export async function acknowledgeNotificationApi(notificationId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/${encodeURIComponent(notificationId)}/acknowledge`, {
      method: "PATCH",
    });
    if (!res.ok) throw new Error("Failed to acknowledge notification");
    return await res.json();
  } catch (err) {
    console.warn("Acknowledge notification error:", err);
    return { status: "acknowledged_locally", id: notificationId };
  }
}

export async function dismissNotificationApi(notificationId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/${encodeURIComponent(notificationId)}/dismiss`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to dismiss notification");
    return await res.json();
  } catch (err) {
    console.warn("Dismiss notification error:", err);
    return { status: "dismissed_locally", id: notificationId };
  }
}

export async function markNotificationReadApi(notificationId: string) {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/${encodeURIComponent(notificationId)}/read`, {
      method: "PATCH",
    });
    if (!res.ok) throw new Error("Failed to mark notification read");
    return await res.json();
  } catch (err) {
    console.warn("Mark notification read error:", err);
    return { status: "read_locally", id: notificationId };
  }
}

export async function markAllNotificationsReadApi() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/mark-all-read`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to mark all notifications read");
    return await res.json();
  } catch (err) {
    console.warn("Mark all notifications read error:", err);
    return { status: "read_all_locally", marked_read_count: 0 };
  }
}

export async function fetchNotificationPreferences() {
  const cached = localStorage.getItem("nyaya_notification_preferences");
  let defaultPrefs = {
    preferred_language: "en",
    enabled_channels: ["IN_APP", "EMAIL"],
    quiet_hours_enabled: false,
    quiet_hours_start: "22:00",
    quiet_hours_end: "06:00",
  };
  if (cached) {
    try {
      defaultPrefs = { ...defaultPrefs, ...JSON.parse(cached) };
    } catch {}
  }
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/preferences`);
    if (res.ok) {
      const serverData = await res.json();
      localStorage.setItem("nyaya_notification_preferences", JSON.stringify(serverData));
      return serverData;
    }
  } catch (err) {
    console.warn("Fetch notification preferences network notice:", err);
  }
  return defaultPrefs;
}

export async function updateNotificationPreferences(prefs: {
  preferred_language?: string;
  enabled_channels?: string[];
  quiet_hours_enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  phone_number?: string;
  email?: string;
}) {
  // Always immediately persist in localStorage for instant responsive client behavior
  const cached = localStorage.getItem("nyaya_notification_preferences");
  let current = {};
  if (cached) {
    try { current = JSON.parse(cached); } catch {}
  }
  const merged = { ...current, ...prefs };
  localStorage.setItem("nyaya_notification_preferences", JSON.stringify(merged));

  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/preferences`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prefs),
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("nyaya_notification_preferences", JSON.stringify(data));
      return data;
    }
  } catch (err) {
    console.warn("Backend update preferences note (using local cache):", err);
  }
  return merged;
}


export async function fetchNotificationDLQ() {
  try {
    const res = await authFetch(`${API_BASE_URL}/api/notifications/dlq`);
    if (!res.ok) throw new Error("Failed to fetch DLQ entries");
    return await res.json();
  } catch (err) {
    console.warn("Fetch DLQ error:", err);
    return [];
  }
}

export async function retryNotificationDLQ(dlqId: string) {
  const res = await authFetch(`${API_BASE_URL}/api/notifications/dlq/${encodeURIComponent(dlqId)}/retry`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to retry DLQ entry");
  return await res.json();
}


export function subscribeToNotificationsStream(
  onNotification: (notif: any) => void,
  onError?: (err: any) => void,
): () => void {
  let isClosed = false;
  let abortController: AbortController | null = null;
  let retryTimeout: any = null;

  async function connect() {
    if (isClosed) return;
    const token = getAuthToken();

    abortController = new AbortController();

    try {
      const headers: Record<string, string> = {
        Accept: "text/event-stream",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const streamUrl = token
        ? `${API_BASE_URL}/notifications/stream?token=${encodeURIComponent(token)}`
        : `${API_BASE_URL}/notifications/stream`;

      const response = await fetch(streamUrl, {
        headers,
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`SSE stream connection failed with status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!isClosed) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data:")) {
            try {
              const data = JSON.parse(trimmed.slice(5).trim());
              onNotification(data);
            } catch (err) {
              console.warn("Error parsing real-time notification data:", err);
            }
          }
        }
      }

      if (!isClosed) {
        retryTimeout = setTimeout(connect, 2000);
      }
    } catch (err: any) {
      if (!isClosed && err.name !== "AbortError") {
        if (onError) onError(err);
        retryTimeout = setTimeout(connect, 2500);
      }
    }
  }

  connect();

  return () => {
    isClosed = true;
    if (abortController) abortController.abort();
    if (retryTimeout) clearTimeout(retryTimeout);
  };
}

export async function triggerTestNotificationApi(caseId: string = "UTP-0001", title: string = "Live Real-Time Notification Test"): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/notifications/test-broadcast`, {
    method: "POST",
    body: JSON.stringify({ case_id: caseId, title }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `Notification broadcast failed: HTTP ${res.status}`);
  }
  return await res.json();
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

export async function fetchCitizenTimeline(): Promise<any[]> {
  const res = await authFetch(`${API_BASE_URL}/citizen/timeline`);
  if (!res.ok) {
    if (res.status === 404) return [];
    throw new Error(`Failed to fetch citizen timeline: HTTP ${res.status}`);
  }
  return await res.json();
}

// ── Stage 11: Constrained Mobile-First Citizen Types & APIs ──────────────────

export interface CitizenLanguageItem {
  code: string;
  name: string;
  native_name: string;
  is_authoritative: boolean;
  legal_authority_note: string;
}

export interface CitizenUpcomingEvent {
  event_type: string;
  title: string;
  event_date: string;
  court_or_location: string;
  instructions: string;
}

export interface CitizenMissingDocument {
  document_type: string;
  title: string;
  why_needed: string;
  how_to_submit: string;
  urgency: "REQUIRED_BEFORE_HEARING" | "OPTIONAL_SUPPORTING";
}

export interface CitizenEntitledDocument {
  id: string;
  document_type: string;
  title: string;
  status: string;
  uploaded_at?: string;
  file_size_bytes: number;
  file_size_formatted: string;
  text_summary: string;
  is_approved_for_citizen: boolean;
}

export interface CitizenAiExplanationData {
  is_ai_generated: boolean;
  disclaimer_type: string;
  disclaimer_label: string;
  disclaimer_text: string;
  explanation_text: string;
  derived_language: string;
  is_derived_display: boolean;
  authoritative_english_text: string;
}

export interface CitizenOverviewData {
  portal_mode: "ACCUSED_USER" | "FAMILY_GUARDIAN";
  accused_id: string;
  accused_name: string;
  case_reference: string;
  court_name: string;
  police_station: string;
  current_known_status: {
    status_code: string;
    title: string;
    detail: string;
    authoritative_title: string;
    authoritative_detail: string;
    is_derived: boolean;
    disclaimer: string;
  };
  filing_details: {
    is_filed: boolean;
    filing_status: string;
    filing_reference: string;
    court_name?: string;
  };
  release_details: {
    is_released: boolean;
    release_status: string;
    verification_source: string;
  };
  upcoming_known_events: CitizenUpcomingEvent[];
  legal_aid_support: {
    is_assigned: boolean;
    lawyer_name?: string | null;
    organization: string;
    contact_phone?: string;
    panel_type?: string;
    status_message?: string;
    representation_cost: string;
    office_address: string;
  };
  missing_documents_from_citizen: CitizenMissingDocument[];
  approved_entitled_documents: CitizenEntitledDocument[];
  ai_procedural_explanation: CitizenAiExplanationData;
  language_meta: {
    current_language: string;
    supported_languages: CitizenLanguageItem[];
    is_derived_display: boolean;
    authoritative_language: string;
    disclaimer: string;
  };
  notification_preferences: {
    case_id: string;
    user_id: string;
    phone_number?: string;
    channel_sms_enabled: boolean;
    channel_whatsapp_enabled: boolean;
    channel_in_app_enabled: boolean;
    preferred_language: string;
    consent_status: string;
    consent_timestamp: string;
    consent_version: string;
    consent_text: string;
  };
  recent_citizen_requests: Array<{
    id: string;
    case_id: string;
    request_type: string;
    subject: string;
    details: string;
    status: string;
    response_notes?: string;
    created_at: string;
  }>;
  low_bandwidth_mode_supported: boolean;
  support_helpline: string;
  support_notice: string;
}

export async function fetchCitizenOverview(lang: string = "en"): Promise<CitizenOverviewData> {
  const res = await authFetch(`${API_BASE_URL}/citizen/overview?lang=${encodeURIComponent(lang)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch citizen overview: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchCitizenLanguages(): Promise<CitizenLanguageItem[]> {
  const res = await authFetch(`${API_BASE_URL}/citizen/languages`);
  if (!res.ok) return [];
  return await res.json();
}

export async function fetchCitizenEntitledDocuments(lang: string = "en"): Promise<CitizenEntitledDocument[]> {
  const res = await authFetch(`${API_BASE_URL}/citizen/documents?lang=${encodeURIComponent(lang)}`);
  if (!res.ok) return [];
  return await res.json();
}

export async function fetchCitizenDocumentSummary(docId: string, lang: string = "en"): Promise<{
  id: string;
  case_id: string;
  document_type: string;
  file_name: string;
  text_summary?: string;
  text_preview: string;
  file_size_formatted: string;
  status: string;
}> {
  const res = await authFetch(`${API_BASE_URL}/citizen/documents/${encodeURIComponent(docId)}/summary?lang=${encodeURIComponent(lang)}`);
  if (!res.ok) throw new Error("Failed to load document summary");
  return await res.json();
}

export async function submitCitizenActionRequest(payload: {
  request_type: string;
  subject: string;
  details: string;
  target_document_type?: string;
  discrepancy_field?: string;
}): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/citizen/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to submit citizen request: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchCitizenActionRequests(): Promise<any[]> {
  const res = await authFetch(`${API_BASE_URL}/citizen/requests`);
  if (!res.ok) return [];
  return await res.json();
}

export async function fetchCitizenNotificationPreferences(): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/citizen/notification-preferences`);
  if (!res.ok) throw new Error("Failed to load notification preferences");
  return await res.json();
}

export async function updateCitizenNotificationPreferences(payload: {
  phone_number?: string;
  channel_sms_enabled: boolean;
  channel_whatsapp_enabled: boolean;
  channel_in_app_enabled: boolean;
  preferred_language: string;
  consent_status: string;
  consent_text?: string;
}): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/citizen/notification-preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update notification preferences");
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

export async function fetchDuplicateCandidates(status = "PENDING_HUMAN_REVIEW") {
  const res = await authFetch(`${API_BASE_URL}/accused/duplicates/candidates?status=${encodeURIComponent(status)}`);
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

export async function fetchAuditEvents(options?: {
  limit?: number;
  offset?: number;
  dateFrom?: string;
  dateTo?: string;
  action?: string;
  actorRole?: string;
  severity?: string;
} | number) {
  try {
    const params = new URLSearchParams();
    if (typeof options === "number") {
      params.append("limit", String(options));
    } else if (options) {
      if (options.limit) params.append("limit", String(options.limit));
      if (options.offset) params.append("offset", String(options.offset));
      if (options.dateFrom) params.append("date_from", options.dateFrom);
      if (options.dateTo) params.append("date_to", options.dateTo);
      if (options.action && options.action !== "ALL") params.append("action", options.action);
      if (options.actorRole && options.actorRole !== "ALL") params.append("actor_role", options.actorRole);
      if (options.severity && options.severity !== "ALL") params.append("severity", options.severity);
    }

    const url = `${API_BASE_URL}/audit-events${params.toString() ? `?${params.toString()}` : ""}`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error(`Failed to fetch audit events: HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend audit events unavailable:", err);
    return { events: [], total_count: 0, returned_count: 0 };
  }
}

export async function exportAuditLedger(payload: {
  export_reason: string;
  format?: string;
  date_from?: string;
  date_to?: string;
  action_filter?: string;
  actor_role_filter?: string;
}) {
  const res = await authFetch(`${API_BASE_URL}/audit/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Export failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchAuditExceptions() {
  try {
    const res = await authFetch(`${API_BASE_URL}/audit/exceptions`);
    if (!res.ok) throw new Error(`Failed to fetch exceptions: HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Backend /audit/exceptions unavailable:", err);
    return { total_exceptions: 0, exceptions: [] };
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

// ── State Legal Services Authority (SLSA) & Government Oversight APIs ─────────

export interface GovOverviewMetrics {
  state: string;
  scope_type: string;
  total_monitored_undertrials: number;
  section_479_eligibility_signals: number;
  average_custody_days: number;
  dlsa_mapping_coverage_pct: number;
  sla_compliance_rate_pct: number;
  legal_aid_assignment_rate_pct: number;
  document_completeness_rate_pct: number;
  estimated_manual_review_hours_avoided: number;
  estimated_hours_note: string;
  mandatory_human_signoff_notice: string;
}

export interface GovDistrictItem {
  district: string;
  dlsa_name: string;
  total_cases: number;
  eligible_signals: number;
  assigned_counsel: number;
  pending_documents: number;
  overdue_cases: number;
  avg_custody_days: number;
  compliance_rate_pct: number;
}

export interface GovSlaData {
  overall_compliance_pct: number;
  sla_breakdown: {
    compliant_cases: number;
    at_risk_cases: number;
    breached_cases: number;
  };
  target_metrics: Array<{
    milestone: string;
    target: string;
    current_avg: string;
    status: string;
  }>;
}

export interface GovExceptionItem {
  id: string;
  case_id: string;
  district: string;
  severity: string;
  category: string;
  title: string;
  description: string;
  days_overdue?: number;
  missing_documents?: string[];
}

export async function fetchGovOverview(): Promise<GovOverviewMetrics> {
  const res = await authFetch(`${API_BASE_URL}/gov/overview`);
  if (!res.ok) throw new Error(`Failed to fetch gov overview: HTTP ${res.status}`);
  return await res.json();
}

export async function fetchGovDistricts(): Promise<GovDistrictItem[]> {
  const res = await authFetch(`${API_BASE_URL}/gov/districts`);
  if (!res.ok) throw new Error(`Failed to fetch gov districts: HTTP ${res.status}`);
  return await res.json();
}

export async function fetchGovSlaMetrics(): Promise<GovSlaData> {
  const res = await authFetch(`${API_BASE_URL}/gov/sla`);
  if (!res.ok) throw new Error(`Failed to fetch gov SLA metrics: HTTP ${res.status}`);
  return await res.json();
}

export async function fetchGovExceptions(): Promise<GovExceptionItem[]> {
  const res = await authFetch(`${API_BASE_URL}/gov/exceptions`);
  if (!res.ok) throw new Error(`Failed to fetch gov exceptions: HTTP ${res.status}`);
  return await res.json();
}

export interface PlatformHealthData {
  status: string;
  environment: {
    app_env: string;
    demo_mode: boolean;
    python_version: string;
    framework: string;
  };
  subsystems: {
    api: { status: string; protocol: string; rate_limiting: string };
    database: { status: string; mode: string; active_records: number; storage_path: string };
    auth: { status: string; algorithm: string; session_revocation: string; brute_force_protection: string };
    audit_ledger: { status: string; records_logged: number; chain_continuity: string; database_immutability_triggers: string };
    rag_corpus: { status: string; documents_indexed: number; vector_store: string };
  };
  connectors: Array<{
    id: string;
    name: string;
    status: string;
    type: string;
    latency_ms: number;
    health: string;
  }>;
  timestamp: string;
}

export interface PlatformProfileData {
  id: string;
  full_name: string;
  email: string;
  role: string;
  administrative_domain: string;
  access_scope: string;
  environment: string;
  demo_mode: boolean;
  token_security: {
    algorithm: string;
    session_revocation: string;
    brute_force_lockout: string;
  };
  capabilities: string[];
  organization: string;
  timestamp: string;
}

export async function fetchPlatformHealth(): Promise<PlatformHealthData> {
  const res = await authFetch(`${API_BASE_URL}/platform/health`);
  if (!res.ok) throw new Error(`Failed to fetch platform health: HTTP ${res.status}`);
  return await res.json();
}

export async function fetchPlatformProfile(): Promise<PlatformProfileData> {
  const res = await authFetch(`${API_BASE_URL}/platform/profile`);
  if (!res.ok) throw new Error(`Failed to fetch platform profile: HTTP ${res.status}`);
  return await res.json();
}

export async function triggerPlatformAction(actionType: string, target?: string, parameters?: Record<string, any>) {
  const res = await authFetch(`${API_BASE_URL}/platform/actions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action_type: actionType, target, parameters }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Action failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchEvidenceChain(docId: string): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/documents/${encodeURIComponent(docId)}/evidence-chain`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch evidence chain: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function correctDocumentField(
  docId: string,
  payload: {
    field_name: string;
    corrected_value: any;
    correction_reason: string;
    version_id?: string;
  }
) {
  const res = await authFetch(`${API_BASE_URL}/documents/${encodeURIComponent(docId)}/correct-field`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Field correction failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function reprocessDocument(
  docId: string,
  payload?: {
    reason?: string;
    custom_text_override?: string;
  }
) {
  const res = await authFetch(`${API_BASE_URL}/documents/${encodeURIComponent(docId)}/reprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Reprocessing failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function downloadSecureDocument(docId: string): Promise<Blob> {
  const res = await authFetch(`${API_BASE_URL}/documents/download/${encodeURIComponent(docId)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Download failed: HTTP ${res.status}`);
  }
  return await res.blob();
}

export async function verifyUploadedDocument(docId: string) {
  const res = await authFetch(`${API_BASE_URL}/documents/${encodeURIComponent(docId)}/verify`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Document verification failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function reviewUploadedDocument(docId: string) {
  const res = await authFetch(`${API_BASE_URL}/documents/${encodeURIComponent(docId)}/review`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Document review failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchLegalRules() {
  const res = await authFetch(`${API_BASE_URL}/rules`);
  if (!res.ok) {
    throw new Error(`Failed to fetch legal rules: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchRuleDetails(ruleId: string) {
  const res = await authFetch(`${API_BASE_URL}/rules/${encodeURIComponent(ruleId)}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch rule details: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function evaluateRuleAdhoc(ruleId: string, payload: Record<string, any>) {
  const res = await authFetch(`${API_BASE_URL}/rules/${encodeURIComponent(ruleId)}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Rule evaluation failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function transitionRuleLifecycle(ruleId: string, targetState: string, notes: string = "") {
  const res = await authFetch(`${API_BASE_URL}/rules/${encodeURIComponent(ruleId)}/lifecycle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_state: targetState, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Lifecycle transition failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function updateAccusedIdentity(
  accusedId: string,
  payload: {
    update_reason: string;
    full_name?: string;
    aliases?: string[];
    father_name?: string;
    gender?: string;
    age?: number;
    government_identifiers?: Record<string, any>;
  }
) {
  const res = await authFetch(`${API_BASE_URL}/accused/${encodeURIComponent(accusedId)}/identity`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update identity: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function exportCaseFile(caseId: string, reason?: string) {
  const url = `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/export${
    reason ? `?export_reason=${encodeURIComponent(reason)}` : ""
  }`;
  const res = await authFetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to export case file: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function assignCaseCounsel(
  caseId: string,
  lawyerId: string,
  lawyerName?: string,
  notes?: string
) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/assign-counsel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lawyer_id: lawyerId,
      lawyer_name: lawyerName,
      notes: notes,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Assign counsel failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function getEligibleCounsel(caseId: string) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/eligible-counsel`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Fetch eligible counsel failed: HTTP ${res.status}`);
  }
  return await res.json();
}

// ── Stage 9: Matter Lifecycle, Approvals & Handoff APIs ─────────────────────

export async function requestMatterTransition(
  caseId: string,
  transition: string,
  payload?: Record<string, any>,
  comment?: string,
  expectedVersion?: number
) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/transitions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      transition,
      payload,
      comment,
      expected_version: expectedVersion,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detailMsg = typeof err.detail === "string" ? err.detail : (err.detail?.message || `Transition '${transition}' failed: HTTP ${res.status}`);
    const errorObj = new Error(detailMsg) as any;
    errorObj.status = res.status;
    errorObj.detail = err.detail;
    throw errorObj;
  }
  return await res.json();
}

export async function fetchMatterState(caseId: string) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/state`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch matter state: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchAvailableTransitions(caseId: string) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/available-transitions`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch available transitions: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function submitMatterApproval(
  caseId: string,
  approvalData: {
    artifact_id: string;
    artifact_version_id: string;
    artifact_type?: string;
    decision: "APPROVED" | "REJECTED" | "CHANGES_REQUESTED";
    comment?: string;
    approval_level?: number;
  }
) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/approvals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(approvalData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Approval submission failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchMatterApprovals(caseId: string, artifactVersionId?: string) {
  const url = `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/approvals${
    artifactVersionId ? `?artifact_version_id=${encodeURIComponent(artifactVersionId)}` : ""
  }`;
  const res = await authFetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch approvals: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function createMatterArtifact(
  caseId: string,
  artifactData: {
    artifact_id: string;
    artifact_type: string;
    content_text: string;
    is_ai_generated?: boolean;
    ai_model_name?: string;
    version_tag?: string;
  }
) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/artifacts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(artifactData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Artifact creation failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchMatterArtifacts(caseId: string, artifactId?: string) {
  const url = `${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/artifacts${
    artifactId ? `?artifact_id=${encodeURIComponent(artifactId)}` : ""
  }`;
  const res = await authFetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch artifacts: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function executeMatterHandoff(
  caseId: string,
  handoffData: {
    to_user_id: string;
    to_role: string;
    reason: string;
    metadata?: Record<string, any>;
  }
) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/handoff`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(handoffData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Handoff failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchMatterHandoffSummary(caseId: string) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/handoff-summary`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch handoff summary: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchMatterTimeline(caseId: string) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/timeline`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch matter timeline: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function syncMatterExternal(
  caseId: string,
  syncData: {
    source_system: string;
    external_reference: string;
    received_data: Record<string, any>;
  }
) {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/external-sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(syncData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `External sync failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function generateBailDraft(caseId: string): Promise<{
  case_id: string;
  draft_text: string;
  version_id: string;
  version_number: number;
  provenance: string;
  message: string;
}> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/draft/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to generate bail draft: HTTP ${res.status}`);
  }
  return await res.json();
}

export interface DocumentContentPreview {
  id: string;
  case_id: string;
  document_type: string;
  file_name: string;
  extracted_text: string;
  summary: string;
  file_hash: string;
  uploaded_by: string;
  uploaded_at: string;
  document_status: string;
  ocr_engine?: string;
}

export async function fetchDocumentContent(docId: string): Promise<DocumentContentPreview> {
  const res = await authFetch(`${API_BASE_URL}/documents/${encodeURIComponent(docId)}/content`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch document content: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function downloadCaseDocument(docId: string, fileName: string = "document.txt"): Promise<void> {
  const res = await authFetch(`${API_BASE_URL}/documents/download/${encodeURIComponent(docId)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to download document: HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

// ── Operational Task Queue & Authority Operations APIs ──────────────────────

export interface TaskQueueItem {
  id: string;
  case_id: string;
  accused_name: string;
  task_type: string;
  title: string;
  description?: string;
  owner_role: string;
  owner_user_id?: string;
  owner_name?: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  due_date: string;
  source: string;
  reason: string;
  status: "NEW" | "PENDING_ACTION" | "WAITING_FOR_DOCUMENTS" | "UNDER_REVIEW" | "OVERDUE" | "ESCALATED" | "COMPLETED" | "EXCEPTION";
  escalation_path: string;
  facility?: string;
  district?: string;
  custody_duration_days: number;
  document_completeness_pct: number;
  has_data_conflict: boolean;
  legal_aid_need: boolean;
  assignment_status: string;
  matter_status: string;
  hearing_date?: string;
  is_consequential: boolean;
  metadata_json?: any;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  completed_by?: string;
}

export interface TaskFilterParams {
  owner_role?: string;
  case_id?: string;
  facility?: string;
  district?: string;
  priority?: string;
  custody_duration_min?: number;
  document_completeness_max?: number;
  legal_aid_need?: boolean;
  hearing_date_from?: string;
  hearing_date_to?: string;
  has_data_conflict?: boolean;
  assignment_status?: string;
  matter_status?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
}

export async function fetchTaskQueue(params: TaskFilterParams = {}): Promise<TaskQueueItem[]> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "") {
      query.append(key, String(val));
    }
  });
  const res = await authFetch(`${API_BASE_URL}/tasks/queue?${query.toString()}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch task queue: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function updateTaskApi(taskId: string, updates: Partial<TaskQueueItem>): Promise<TaskQueueItem> {
  const res = await authFetch(`${API_BASE_URL}/tasks/${encodeURIComponent(taskId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update task: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function executeBulkTaskActionApi(
  action: string,
  taskIds: string[],
  payload: any = {}
): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/tasks/bulk-action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, task_ids: taskIds, ...payload }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Bulk action failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export interface CustodyIntakePayload {
  name: string;
  facility_id: string;
  facility_name?: string;
  district: string;
  court_name?: string;
  arrest_date: string;
  admission_date?: string;
  offense_sections: string[];
  max_sentence_days?: number;
  refer_to_dlsa: boolean;
  notes?: string;
}

export async function intakeCustodyRecordApi(payload: CustodyIntakePayload): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/cases/intake-custody`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Custody intake failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export interface CustodyEventPayload {
  event_type: string;
  event_date: string;
  court_name?: string;
  notes: string;
  verified?: boolean;
}

export async function recordCustodyEventApi(caseId: string, payload: CustodyEventPayload): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/custody-events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to record custody event: HTTP ${res.status}`);
  }
  return await res.json();
}

export interface AccusedProfileUpdatePayload {
  father_name?: string;
  date_of_birth?: string;
  age?: number;
  gender?: string;
  permanent_address?: string;
  contact_number?: string;
  emergency_family_contact_name?: string;
  emergency_family_contact_phone?: string;
  emergency_family_contact_relation?: string;
}

export async function updateAccusedProfileApi(caseId: string, payload: AccusedProfileUpdatePayload): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/accused-profile`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update accused profile: HTTP ${res.status}`);
  }
  return await res.json();
}

export interface PrisonReleasePayload {
  release_date: string;
  gate_pass_number: string;
  surety_verification_ref?: string;
  superintendent_notes?: string;
}

export async function confirmPrisonReleaseApi(caseId: string, payload: PrisonReleasePayload): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/confirm-release`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to confirm prison release: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchEligibleCounselApi(caseId: string): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/eligible-counsel`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch eligible counsel: HTTP ${res.status}`);
  }
  return await res.json();
}

export interface AssignCounselPayload {
  lawyer_id: string;
  lawyer_name?: string;
  notes?: string;
}

export async function assignCounselToCaseApi(caseId: string, payload: AssignCounselPayload): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/assign-counsel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to assign counsel: HTTP ${res.status}`);
  }
  return await res.json();
}

export interface ExpediteCoordinationPayload {
  notes?: string;
  target_roles?: string[];
}

export async function expediteCoordinationApi(caseId: string, notes?: string, targetRoles?: string[]): Promise<any> {
  const res = await authFetch(`${API_BASE_URL}/cases/${encodeURIComponent(caseId)}/expedite-coordination`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      notes: notes || "Expediting missing charge sheet / custody certificate.",
      target_roles: targetRoles || ["JAIL_OFFICER", "POLICE_OFFICER"],
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to dispatch coordination notice: HTTP ${res.status}`);
  }
  return await res.json();
}

// ── Analytics, Reporting & Impact Intelligence APIs ──────────────────────────

export interface FacilityCustodyMetric {
  facility_id: string;
  facility_name: string;
  facility_type: string;
  state: string;
  district: string;
  capacity: number;
  current_occupancy: number;
  undertrials_count: number;
  occupancy_rate_pct: number;
  overcrowding_flag: boolean;
}

export interface LegalAidAttentionItem {
  case_id: string;
  accused_name: string;
  facility: string;
  status: string;
  days_in_intake: number;
  urgency_level: string;
  assigned_lawyer_id?: string | null;
  reason: string;
}

export interface LegalAidAttentionMetric {
  total_attention_required: number;
  unassigned_cases_count: number;
  intake_pending_count: number;
  legal_need_identified_count: number;
  panel_requests_pending: number;
  high_urgency_count: number;
  cases: LegalAidAttentionItem[];
}

export interface ApproachingThresholdItem {
  case_id: string;
  accused_name: string;
  facility: string;
  offense_sections: string;
  custody_days: number;
  prescribed_max_days: number;
  half_sentence_days: number;
  third_sentence_days: number;
  statutory_category: string;
  days_until_threshold: number;
  threshold_status: string;
  recommended_action: string;
}

export interface ApproachingThresholdMetric {
  total_flagged: number;
  threshold_reached_count: number;
  within_15_days_count: number;
  within_30_days_count: number;
  cases: ApproachingThresholdItem[];
}

export interface OverdueActionItem {
  task_id: string;
  case_id: string;
  title: string;
  action_type: string;
  assigned_role: string;
  assigned_user?: string | null;
  days_overdue: number;
  escalation_tier: number;
  sla_target_hours: number;
  status: string;
}

export interface OverdueActionMetric {
  total_overdue: number;
  critical_overdue_count: number;
  tier_2_escalated: number;
  tier_3_escalated: number;
  tasks: OverdueActionItem[];
}

export interface MissingDocumentItem {
  case_id: string;
  accused_name: string;
  facility: string;
  total_required: number;
  total_present: number;
  completeness_pct: number;
  missing_docs: string[];
  present_docs: string[];
  is_filing_blocked: boolean;
}

export interface MissingDocumentMetric {
  total_cases_evaluated: number;
  dockets_complete_count: number;
  dockets_incomplete_count: number;
  average_completeness_pct: number;
  most_frequent_missing: { document_type: string; missing_count: number }[];
  cases: MissingDocumentItem[];
}

export interface TurnaroundIntakeToAssignmentMetric {
  total_cases_measured: number;
  average_hours: number;
  median_hours: number;
  target_hours: number;
  within_sla_pct: number;
  trend_direction: string;
}

export interface TurnaroundAssignmentToReviewMetric {
  total_reviews_measured: number;
  average_hours: number;
  median_hours: number;
  target_hours: number;
  supervisory_approval_rate_pct: number;
  trend_direction: string;
}

export interface UnresolvedConflictItem {
  conflict_id: string;
  conflict_type: string;
  entity_id: string;
  description: string;
  source_system: string;
  confidence_score: number;
  requires_human_review: boolean;
  detected_at: string;
}

export interface UnresolvedConflictMetric {
  total_unresolved: number;
  identity_merge_candidates_count: number;
  cross_facility_duplicates_count: number;
  connector_divergence_count: number;
  conflicts: UnresolvedConflictItem[];
}

export interface UpcomingHearingItem {
  hearing_id: string;
  case_id: string;
  accused_name: string;
  court_name: string;
  hearing_date: string;
  days_away: number;
  hearing_type: string;
  assigned_advocate: string;
  purpose: string;
}

export interface UpcomingHearingMetric {
  next_7_days_count: number;
  next_14_days_count: number;
  next_30_days_count: number;
  by_court_breakdown: { court: string; count: number }[];
  by_purpose_breakdown: { purpose: string; count: number }[];
  hearings: UpcomingHearingItem[];
}

export interface ReleaseOutcomeMetric {
  total_releases_recorded: number;
  regular_bail_count: number;
  section_479_statutory_bail_count: number;
  default_bail_count: number;
  acquittal_discharge_count: number;
  post_release_support_active: number;
  surety_compliance_rate_pct: number;
  monthly_trend: { month: string; releases: number }[];
}

export interface NotificationDeliveryMetric {
  total_dispatched: number;
  in_app_delivered: number;
  email_delivered: number;
  sms_delivered: number;
  whatsapp_delivered: number;
  dlq_failures_count: number;
  delivery_success_rate_pct: number;
  acknowledgement_rate_pct: number;
  auto_escalated_count: number;
}

export interface ConnectorHealthSummaryItem {
  connector_id: string;
  display_name: string;
  connector_type: string;
  sync_status: string;
  last_sync: string | null;
  latency_ms: number;
  error_rate_pct: number;
  records_processed: number;
  records_rejected: number;
  is_simulated: boolean;
}

export interface IntegrationHealthMetric {
  total_connectors: number;
  healthy_connectors_count: number;
  degraded_connectors_count: number;
  overall_uptime_pct: number;
  connectors: ConnectorHealthSummaryItem[];
}

export interface AdvocateWorkloadItem {
  advocate_id: string;
  name: string;
  bar_registration_no: string;
  active_cases: number;
  district: string;
  panel_status: string;
}

export interface RoleTaskWorkloadItem {
  role: string;
  pending_tasks: number;
  overdue_tasks: number;
  completed_today: number;
}

export interface WorkloadByTeamMetric {
  active_panel_advocates_count: number;
  average_cases_per_advocate: number;
  top_advocates: AdvocateWorkloadItem[];
  role_distribution: RoleTaskWorkloadItem[];
}

export interface AllDashboardsResponse {
  user_role: string;
  jurisdiction: string;
  data_provenance: string;
  is_synthetic: boolean;
  methodology_disclaimer: string;
  generated_at: string;
  people_in_custody: FacilityCustodyMetric[];
  legal_aid_attention: LegalAidAttentionMetric;
  approaching_thresholds: ApproachingThresholdMetric;
  overdue_actions: OverdueActionMetric;
  missing_documents: MissingDocumentMetric;
  time_intake_to_assignment: TurnaroundIntakeToAssignmentMetric;
  time_assignment_to_review: TurnaroundAssignmentToReviewMetric;
  unresolved_conflicts: UnresolvedConflictMetric;
  upcoming_hearings: UpcomingHearingMetric;
  release_outcomes: ReleaseOutcomeMetric;
  notification_delivery: NotificationDeliveryMetric;
  integration_health: IntegrationHealthMetric;
  workload_by_team: WorkloadByTeamMetric;
}

export interface LeadershipReportResponse {
  title: string;
  jurisdiction: string;
  period: string;
  generated_at: string;
  data_provenance: string;
  is_synthetic: boolean;
  methodology_disclaimer: string;
  executive_summary: Record<string, any>;
  operational_trends: Record<string, any>[];
  backlog_analysis: Record<string, any>;
  turnaround_benchmarks: Record<string, any>;
  service_coverage: Record<string, any>;
}

export interface ImpactMetricItem {
  indicator: string;
  measured_value: string;
  baseline_value: string;
  improvement_delta: string;
  description: string;
  is_synthetic: boolean;
  methodology: string;
}

export interface ImpactDashboardResponse {
  title: string;
  generated_at: string;
  data_provenance: string;
  is_synthetic: boolean;
  methodology_disclaimer: string;
  fewer_missed_actions_pct: number;
  faster_assignment_reduction_pct: number;
  document_completeness_rate_pct: number;
  manual_search_hours_avoided: number;
  deadline_visibility_rate_pct: number;
  post_release_continuity_rate_pct: number;
  indicators: ImpactMetricItem[];
}

export interface ExportRequest {
  report_type: string;
  format: "CSV" | "JSON" | "PDF";
  jurisdiction?: string;
  date_from?: string | null;
  date_to?: string | null;
  purpose: string;
  include_pii?: boolean;
}

export interface ExportResponse {
  export_id: string;
  filename: string;
  format: string;
  record_count: number;
  content: string;
  checksum_sha256: string;
  exported_at: string;
  data_minimized: boolean;
  jurisdiction_scope: string;
}

export interface ExportAuditLogRecord {
  id: string;
  user_id: string;
  user_email: string;
  user_role: string;
  report_type: string;
  format: string;
  record_count: number;
  scope_filter: string;
  purpose: string;
  export_hash: string;
  exported_at: string;
}

export interface ScheduledReportRecord {
  id: string;
  title: string;
  report_type: string;
  frequency: string;
  recipients: string[];
  jurisdiction: string;
  data_minimization_level: string;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface ScheduledReportCreateRequest {
  title: string;
  report_type: string;
  frequency: "DAILY" | "WEEKLY" | "MONTHLY" | "QUARTERLY";
  recipients: string[];
  jurisdiction?: string;
  data_minimization_level?: string;
}

export interface ScheduledExecutionRecord {
  id: string;
  schedule_id: string;
  executed_at: string;
  status: string;
  summary_content: string;
  delivery_channel: string;
}

export async function fetchAnalyticsDashboards(): Promise<AllDashboardsResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/dashboards`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch analytics dashboards: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchLeadershipReport(): Promise<LeadershipReportResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/leadership-report`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch leadership report: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchImpactDashboard(): Promise<ImpactDashboardResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/impact`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch impact dashboard: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function exportAnalyticsData(payload: ExportRequest): Promise<ExportResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Export generation failed: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchExportAuditLogs(limit: number = 50): Promise<ExportAuditLogRecord[]> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/export/audit-logs?limit=${limit}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch export audit logs: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchScheduledReports(): Promise<ScheduledReportRecord[]> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/schedules`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch scheduled reports: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function createScheduledReport(payload: ScheduledReportCreateRequest): Promise<ScheduledReportRecord> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create scheduled report: HTTP ${res.status}`);
  }
  return await res.json();
}

export async function triggerScheduledReport(scheduleId: string): Promise<ScheduledExecutionRecord> {
  const res = await authFetch(`${API_BASE_URL}/api/analytics/schedules/${encodeURIComponent(scheduleId)}/trigger`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to trigger scheduled report: HTTP ${res.status}`);
  }
  return await res.json();
}

// ── Operations & Production Reliability Dashboard ────────────────────────────

export interface OperationsDashboardData {
  status: string;
  timestamp: string;
  database: {
    connected: boolean;
    engine: string;
  };
  queue: {
    QUEUED?: number;
    PROCESSING?: number;
    COMPLETED?: number;
    FAILED?: number;
    DEAD_LETTER?: number;
  };
  circuit_breakers: Record<string, {
    name: string;
    state: string;
    consecutive_failures: number;
    failure_threshold: number;
    recovery_timeout_sec: number;
  }>;
  telemetry: {
    http?: {
      total_requests: number;
      total_errors: number;
      error_rate: number;
      avg_latency_ms: number;
    };
    ai_usage?: {
      requests: number;
      tokens: number;
    };
    ocr?: {
      operations: number;
      failures: number;
    };
    connectors?: {
      syncs: number;
      failures: number;
    };
  };
}

export async function fetchOperationsDashboard(): Promise<OperationsDashboardData> {
  const res = await authFetch(`${API_BASE_URL}/api/operations/dashboard`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch operations dashboard: HTTP ${res.status}`);
  }
  return await res.json();
}

