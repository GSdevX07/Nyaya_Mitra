/**
 * API Service for Nyaya Mitra Frontend
 * Connects directly to FastAPI backend running on http://localhost:8000
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
    relative_name?: string;
    relative_relation?: string;
    relative_phone?: string;
    permanent_address?: string;
    assignment_status?: string;
    assigned_lawyer_id?: string;
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

export async function fetchAvailableCases(): Promise<BackendCaseSummary[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/available`);
    if (!res.ok) throw new Error("Failed to fetch available cases");
    return await res.json();
  } catch (err) {
    console.warn("Backend API available cases unavailable:", err);
    return [];
  }
}

export async function takeUpCase(caseId: string) {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/take`, {
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
    const res = await fetch(`${API_BASE_URL}/cases/${caseId}/decline`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Decline case failed");
    return await res.json();
  } catch (err) {
    console.error("Error declining case:", err);
    throw err;
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
      cases_taken: 4,
      status: "Active Pro Bono Counsel",
      organization: "Delhi Legal Services Authority (DLSA)",
    };
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

/**
 * Upload a real file (PDF / image) and / or custom text for a case document.
 * Sends multipart/form-data to POST /documents/upload.
 */
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

/** Backward-compat alias — no file, no text. */
export async function uploadDocument(caseId: string, documentType: string) {
  return uploadDocumentFile(caseId, documentType, undefined, undefined);
}

/** Fetch per-case upload history from Supabase. */
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

export async function fetchSampleDocuments() {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/sample-documents`);
    if (!res.ok) throw new Error("Failed to fetch sample documents");
    return await res.json();
  } catch (err) {
    console.warn("Backend API sample-documents unavailable:", err);
    return [];
  }
}

export async function assessDocument(documentName?: string, providedText?: string) {
  try {
    const res = await fetch(`${API_BASE_URL}/cases/assess-document`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_name: documentName || "scanned_handwritten_remand.pdf",
        provided_text: providedText || undefined,
      }),
    });
    if (!res.ok) throw new Error("Document assessment API error");
    return await res.json();
  } catch (err) {
    console.error("Error in assessDocument:", err);
    throw err;
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
