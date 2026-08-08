/**
 * API Service for Nyaya Mitra Frontend
 * Connects directly to FastAPI backend running on http://localhost:8000
 */

const API_BASE_URL = "http://localhost:8000";

export interface BackendCaseSummary {
  case: {
    case_id: string;
    name: string;
    offense_sections: string[];
    arrest_date: string;
    custody_days: number;
    max_sentence_days_for_offense: number;
    prior_bail_orders: string[];
    required_docs: string[];
    present_docs: string[];
    urgency_flags: {
      age: number;
      health_flag: boolean;
      repeat_offender: boolean;
    };
    jail_location: string;
    preferred_language: string;
  };
  days_overdue: number;
  urgency_score: number;
}

export async function fetchCases(): Promise<BackendCaseSummary[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/cases`);
    if (!res.ok) throw new Error("Failed to fetch cases");
    return await res.json();
  } catch (err) {
    console.warn("Backend API unavailable, falling back to mock data:", err);
    return [];
  }
}

export async function fetchCaseById(caseId: string) {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}`);
    if (!res.ok) throw new Error(`Failed to fetch case ${caseId}`);
    return await res.json();
  } catch (err) {
    console.warn(`Backend API failed for case ${caseId}:`, err);
    return null;
  }
}

export async function approveCaseInBackend(caseId: string) {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/approve`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Approval failed");
    return await res.json();
  } catch (err) {
    console.error("Error approving case:", err);
    throw err;
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

export async function uploadDocument(caseId: string, documentType: string) {
  try {
    const res = await fetch(
      `${API_BASE_URL}/documents/upload?case_id=${encodeURIComponent(
        caseId
      )}&document_type=${encodeURIComponent(documentType)}`,
      { method: "POST" }
    );
    return await res.json();
  } catch (err) {
    console.error("Document upload error:", err);
    throw err;
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
