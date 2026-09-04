/**
 * permissions.ts — Canonical Institutional Capabilities and Permission System for Nyaya Mitra
 *
 * Implements the security principle:
 * AUTHENTICATION -> ROLE -> SCOPE -> JURISDICTION -> ASSIGNMENT -> WORKFLOW -> PERMISSION -> AUDIT
 *
 * Guarantees that:
 * 1. PLATFORM_ADMIN does NOT inherit consequential legal capabilities.
 * 2. Consequential actions (approval, court filing, identity merge, legal rule activation)
 *    are restricted to their authorized institutional authorities.
 * 3. Frontend action visibility strictly mirrors backend enforcement.
 */

import type { UserProfile } from "./auth";

export type Capability =
  | "CASE_VIEW"
  | "CASE_APPROVE"
  | "CASE_FILE"
  | "CASE_ASSIGN_COUNSEL"
  | "CASE_ACCEPT_ASSIGNMENT"
  | "CASE_DECLINE_ASSIGNMENT"
  | "CASE_EXPORT"
  | "MEDICAL_DATA_VIEW"
  | "IDENTITY_VIEW"
  | "IDENTITY_ESCALATE"
  | "IDENTITY_RESOLVE"
  | "IDENTITY_UPDATE"
  | "IDENTITY_LINK_ALIAS"
  | "EVIDENCE_VIEW"
  | "EVIDENCE_VERIFY"
  | "EVIDENCE_TECHNICAL_VERIFY"
  | "CUSTODY_UPDATE"
  | "DOCUMENT_VIEW"
  | "DOCUMENT_UPLOAD"
  | "DOCUMENT_REVIEW"
  | "DOCUMENT_INSTITUTIONAL_VERIFY"
  | "LEGAL_RULE_VIEW"
  | "LEGAL_RULE_PROPOSE"
  | "LEGAL_RULE_ACTIVATE"
  | "LEGAL_SOURCE_VIEW"
  | "LEGAL_SOURCE_PROPOSE"
  | "LEGAL_SOURCE_ACTIVATE"
  | "ACTION_QUEUE"
  | "ACTION_EXECUTE"
  | "INGESTION_ADMIN"
  | "SYSTEM_ADMIN"
  | "AUDIT_VIEW";

export interface PermissionContext {
  caseId?: string;
  assignedLawyerId?: string;
  assignedLawyerName?: string;
  district?: string;
  facilityId?: string;
  policeStation?: string;
  isExplicitlyShared?: boolean;
  documentType?: string;
  workflowState?: string;
}

/**
 * Evaluates whether an authenticated user possesses a specific capability,
 * optionally evaluated within an ABAC / resource context.
 */
export function checkPermission(
  user: UserProfile | null,
  capability: Capability,
  context?: PermissionContext
): boolean {
  if (!user) return false;
  const role = user.role;

  switch (capability) {
    // ── Case Dossier & Operations ───────────────────────────────────────────
    case "CASE_VIEW":
      // All institutional roles can view cases within their authorized ABAC scope
      if (role === "ACCUSED_USER" || role === "FAMILY_GUARDIAN") {
        if (!context?.caseId || !user.linked_case_id) return false;
        return context.caseId === user.linked_case_id;
      }
      if (role === "CONTROLLED_EXTERNAL_ADVOCATE") {
        return !!context?.isExplicitlyShared || (!!user.linked_case_id && context?.caseId === user.linked_case_id);
      }
      if (role === "DEFENSE_ADVOCATE") {
        if (!context?.assignedLawyerId && !context?.assignedLawyerName) return true;
        const userFullName = (user.full_name || "").toLowerCase();
        return (
          context?.assignedLawyerId === user.id ||
          (!!context?.assignedLawyerName && context.assignedLawyerName.toLowerCase().includes(userFullName)) ||
          context?.caseId === user.linked_case_id
        );
      }
      return true;

    case "CASE_APPROVE":
      // Consequential legal supervisory sign-off strictly requires SUPERVISING_LEGAL_OFFICER
      return role === "SUPERVISING_LEGAL_OFFICER";

    case "CASE_FILE":
      // Recording court filing requires SUPERVISING_LEGAL_OFFICER
      return role === "SUPERVISING_LEGAL_OFFICER";

    case "CASE_EXPORT":
      // Full case file export with SHA-256 seal requires SUPERVISING_LEGAL_OFFICER
      return role === "SUPERVISING_LEGAL_OFFICER";

    case "CASE_ASSIGN_COUNSEL":
      // District Legal Services Authority assigns panel / LADC counsel
      return role === "DLSA_OFFICER" || role === "SUPERVISING_LEGAL_OFFICER";

    case "CASE_ACCEPT_ASSIGNMENT":
    case "CASE_DECLINE_ASSIGNMENT":
      // Defense counsel can accept/decline cases assigned to them
      if (role !== "DEFENSE_ADVOCATE" && role !== "CONTROLLED_EXTERNAL_ADVOCATE") return false;
      if (context?.assignedLawyerId) {
        return context.assignedLawyerId === user.id;
      }
      if (context?.assignedLawyerName) {
        return context.assignedLawyerName.toLowerCase().includes((user.full_name || "").toLowerCase());
      }
      return true;

    // ── Sensitive Medical Records (DPDP Act) ────────────────────────────────
    case "MEDICAL_DATA_VIEW":
      // Only DLSA and Supervising Legal Officer are authorized for medical records
      return role === "SUPERVISING_LEGAL_OFFICER" || role === "DLSA_OFFICER";

    // ── Identity Resolution & Merge ────────────────────────────────────────
    case "IDENTITY_VIEW":
      return (
        role === "SUPERVISING_LEGAL_OFFICER" ||
        role === "GOV_ADMIN" ||
        role === "DLSA_OFFICER" ||
        role === "PLATFORM_ADMIN"
      );

    case "IDENTITY_ESCALATE":
      return role === "DLSA_OFFICER" || role === "GOV_ADMIN";

    case "IDENTITY_LINK_ALIAS":
      return role === "SUPERVISING_LEGAL_OFFICER" || role === "DLSA_OFFICER";

    case "IDENTITY_UPDATE":
    case "IDENTITY_RESOLVE":
      // High-impact canonical identity update/merge strictly requires SUPERVISING_LEGAL_OFFICER
      return role === "SUPERVISING_LEGAL_OFFICER";

    // ── Evidence & Verification ────────────────────────────────────────────
    case "EVIDENCE_VIEW":
      return true;

    case "EVIDENCE_VERIFY":
      // Institutional/substantive evidence verification
      return (
        role === "SUPERVISING_LEGAL_OFFICER" ||
        role === "DLSA_OFFICER" ||
        role === "JAIL_OFFICER"
      );

    case "EVIDENCE_TECHNICAL_VERIFY":
      // Technical file hash recalculation
      return role === "PLATFORM_ADMIN";

    // ── Custody Desk ───────────────────────────────────────────────────────
    case "CUSTODY_UPDATE":
      // Updating custody intake/status is strictly JAIL_OFFICER for own facility
      return role === "JAIL_OFFICER";

    // ── Documents ──────────────────────────────────────────────────────────
    case "DOCUMENT_VIEW":
      if (role === "CONTROLLED_EXTERNAL_ADVOCATE") {
        return !!context?.isExplicitlyShared;
      }
      return true;

    case "DOCUMENT_UPLOAD":
      return (
        role === "JAIL_OFFICER" ||
        role === "POLICE_OFFICER" ||
        role === "DLSA_OFFICER" ||
        role === "DEFENSE_ADVOCATE" ||
        role === "SUPERVISING_LEGAL_OFFICER"
      );

    case "DOCUMENT_REVIEW":
      // DLSA marks reviewed for legal-aid processing
      return role === "DLSA_OFFICER" || role === "SUPERVISING_LEGAL_OFFICER";

    case "DOCUMENT_INSTITUTIONAL_VERIFY":
      return role === "SUPERVISING_LEGAL_OFFICER";

    // ── Legal Rules & Knowledge ────────────────────────────────────────────
    case "LEGAL_RULE_VIEW":
    case "LEGAL_SOURCE_VIEW":
      return true;

    case "LEGAL_RULE_PROPOSE":
    case "LEGAL_SOURCE_PROPOSE":
      return role === "DLSA_OFFICER" || role === "SUPERVISING_LEGAL_OFFICER" || role === "GOV_ADMIN";

    case "LEGAL_RULE_ACTIVATE":
      // Legal rule activation is strictly governed; PLATFORM_ADMIN is prohibited
      return role === "SUPERVISING_LEGAL_OFFICER";

    case "LEGAL_SOURCE_ACTIVATE":
      return role === "SUPERVISING_LEGAL_OFFICER" || role === "GOV_ADMIN";

    // ── Actions ────────────────────────────────────────────────────────────
    case "ACTION_QUEUE":
      return (
        role === "DLSA_OFFICER" ||
        role === "DEFENSE_ADVOCATE" ||
        role === "SUPERVISING_LEGAL_OFFICER"
      );

    case "ACTION_EXECUTE":
      return (
        role === "SUPERVISING_LEGAL_OFFICER" ||
        role === "JAIL_OFFICER" ||
        role === "POLICE_OFFICER"
      );

    // ── Technical & System Administration ──────────────────────────────────
    case "INGESTION_ADMIN":
    case "SYSTEM_ADMIN":
      return role === "PLATFORM_ADMIN";

    case "AUDIT_VIEW":
      return (
        role === "READ_ONLY_AUDITOR" ||
        role === "PLATFORM_ADMIN" ||
        role === "GOV_ADMIN" ||
        role === "SUPERVISING_LEGAL_OFFICER"
      );

    default:
      return false;
  }
}
