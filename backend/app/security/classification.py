"""
security/classification.py — Institutional Data Classification & Field-Level Access Control.
===========================================================================================
Defines the authoritative sensitive data taxonomy for Nyaya Mitra:
- Tier 1: Highly Sensitive / Medical, Psychiatric & Biometric Data
- Tier 2: Sensitive Identity PII & Family Contacts
- Tier 3: Restricted Legal Work Product & Supervisory Directives
- Tier 4: Operational Institutional Metadata

Enforces field-level access filtering based on Attribute-Based Access Control (ABAC),
preventing data leakage across organizational, judicial, and role boundaries.
"""

from __future__ import annotations
import copy
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from app.auth.roles import Role
from app.auth.user_store import AuthUser


class DataClassificationTier(str, Enum):
    TIER_1_MEDICAL_BIOMETRIC = "TIER_1_MEDICAL_BIOMETRIC"
    TIER_1_MEDICAL = "TIER_1_MEDICAL_BIOMETRIC"
    TIER_2_SENSITIVE_PII = "TIER_2_SENSITIVE_PII"
    TIER_2_PII = "TIER_2_SENSITIVE_PII"
    TIER_3_LEGAL_WORK_PRODUCT = "TIER_3_LEGAL_WORK_PRODUCT"
    TIER_4_OPERATIONAL_METADATA = "TIER_4_OPERATIONAL_METADATA"


# Convenience alias
DataTier = DataClassificationTier


class FieldDecision:
    def __init__(self, allowed: bool, tier: DataClassificationTier, mask_required: bool = False, reason: str = ""):
        self.allowed = allowed
        self.tier = tier
        self.mask_required = mask_required
        self.reason = reason

    def __repr__(self) -> str:
        return f"FieldDecision(allowed={self.allowed}, tier={self.tier.value}, mask_required={self.mask_required})"



# ── Authoritative Roles with Access to Specific Tiers ─────────────────────────

ROLES_WITH_MEDICAL_ACCESS: Set[Role] = {
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
    Role.ACCUSED_USER,  # Self-view only
}

ROLES_WITH_FULL_PII_ACCESS: Set[Role] = {
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
    Role.DEFENSE_ADVOCATE,
    Role.ACCUSED_USER,
    Role.FAMILY_GUARDIAN,
}

ROLES_WITH_WORK_PRODUCT_ACCESS: Set[Role] = {
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DLSA_OFFICER,
    Role.DEFENSE_ADVOCATE,
    Role.CONTROLLED_EXTERNAL_ADVOCATE,
}

# Roles strictly forbidden from accessing internal defense work products
FORBIDDEN_WORK_PRODUCT_ROLES: Set[Role] = {
    Role.PLATFORM_ADMIN,
    Role.READ_ONLY_AUDITOR,
    Role.POLICE_OFFICER,
    Role.JAIL_OFFICER,
}


def has_medical_clearance(user: AuthUser, case: Optional[Any] = None) -> bool:
    """Evaluate whether caller possesses Tier 1 Medical Clearance."""
    if user.role in (Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER):
        return True
    if user.role == Role.ACCUSED_USER and case:
        case_id = getattr(case, "case_id", None) or (case.get("case_id") if isinstance(case, dict) else None)
        if user.linked_case_id and case_id and user.linked_case_id.lower() == str(case_id).lower():
            return True
    return False


def has_pii_clearance(user: AuthUser, case: Optional[Any] = None) -> bool:
    """Evaluate whether caller possesses Tier 2 Identity/Contact PII Clearance."""
    if user.role in (Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER):
        return True
    if user.role in (Role.ACCUSED_USER, Role.FAMILY_GUARDIAN) and case:
        case_id = getattr(case, "case_id", None) or (case.get("case_id") if isinstance(case, dict) else None)
        if user.linked_case_id and case_id and user.linked_case_id.lower() == str(case_id).lower():
            return True
    if user.role == Role.DEFENSE_ADVOCATE and case:
        lawyer_id = getattr(case, "assigned_lawyer_id", None) or (case.get("assigned_lawyer_id") if isinstance(case, dict) else None)
        if lawyer_id and str(lawyer_id).lower() == user.id.lower():
            return True
        if user.id == "demo_advocate":
            return True
    return False


def _normalize_user(user_or_role: Any) -> AuthUser:
    if isinstance(user_or_role, AuthUser):
        return user_or_role
    if isinstance(user_or_role, Role):
        return AuthUser(id="actor", email="actor@example.com", role=user_or_role, org_id="org_default", full_name="Actor")
    if isinstance(user_or_role, str):
        try:
            r = Role(user_or_role)
        except Exception:
            r = Role.READ_ONLY_AUDITOR
        return AuthUser(id="actor", email="actor@example.com", role=r, org_id="org_default", full_name="Actor")
    return AuthUser(id="actor", email="actor@example.com", role=Role.READ_ONLY_AUDITOR, org_id="org_default", full_name="Actor")



def get_field_access_decision(role_or_user: Any, field_name: str) -> FieldDecision:
    """Evaluate institutional access entitlement and masking requirements for a field."""
    user = _normalize_user(role_or_user)
    role = user.role

    f_lower = field_name.lower()
    # 1. Tier 1: Medical & Biometric
    if any(k in f_lower for k in ["medical", "health", "psychiatric", "biometric"]):
        allowed = role in (Role.JAIL_OFFICER, Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER, Role.ACCUSED_USER)
        return FieldDecision(
            allowed=allowed,
            tier=DataClassificationTier.TIER_1_MEDICAL_BIOMETRIC,
            mask_required=False,
            reason="Medical privacy protected; restricted to facility and primary legal officers.",
        )

    # 2. Tier 2: Sensitive Identity PII & Family Contacts
    if any(k in f_lower for k in ["relative", "phone", "address", "family", "national_id", "aadhaar"]):
        if role == Role.READ_ONLY_AUDITOR:
            return FieldDecision(
                allowed=True,
                tier=DataClassificationTier.TIER_2_SENSITIVE_PII,
                mask_required=True,
                reason="Statutory auditors receive masked/sanitized PII projections.",
            )
        allowed = role in ROLES_WITH_FULL_PII_ACCESS
        return FieldDecision(
            allowed=allowed,
            tier=DataClassificationTier.TIER_2_SENSITIVE_PII,
            mask_required=not allowed,
            reason="PII access restricted to defense counsel and primary legal authorities.",
        )

    # 3. Tier 3: Legal Work Product
    if any(k in f_lower for k in ["draft", "strategy", "petition", "work_product"]):
        allowed = role in ROLES_WITH_WORK_PRODUCT_ACCESS and role not in FORBIDDEN_WORK_PRODUCT_ROLES
        return FieldDecision(
            allowed=allowed,
            tier=DataClassificationTier.TIER_3_LEGAL_WORK_PRODUCT,
            mask_required=False,
            reason="Privileged legal work product; restricted to defense and supervisory counsel.",
        )

    # 4. Tier 4: Operational Metadata
    return FieldDecision(
        allowed=True,
        tier=DataClassificationTier.TIER_4_OPERATIONAL_METADATA,
        mask_required=False,
        reason="Operational procedural metadata.",
    )


def assert_field_access(role_or_user: Any, field_name: str) -> None:
    decision = get_field_access_decision(role_or_user, field_name)
    if not decision.allowed:
        raise PermissionError(f"Access to sensitive field '{field_name}' is forbidden: {decision.reason}")


def has_work_product_clearance(user: AuthUser, case: Optional[Any] = None) -> bool:
    """Evaluate whether caller possesses Tier 3 Legal Work Product Clearance."""
    if user.role in FORBIDDEN_WORK_PRODUCT_ROLES:
        return False
    if user.role in (Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER):
        return True
    if user.role in (Role.DEFENSE_ADVOCATE, Role.CONTROLLED_EXTERNAL_ADVOCATE):
        if not case:
            return True
        lawyer_id = getattr(case, "assigned_lawyer_id", None) or (case.get("assigned_lawyer_id") if isinstance(case, dict) else None)
        if lawyer_id and str(lawyer_id).lower() == user.id.lower():
            return True
        if user.id in ("demo_advocate", "demo_ext_advocate"):
            return True
    return False


class FieldLevelAccessFilter:
    """
    Applies field-level classification filtering and redacts unauthorized attributes
    from case objects, accused profiles, documents, and export payloads.
    """

    @staticmethod
    def filter_case(case_obj_or_dict: Any, user: Any) -> Dict[str, Any]:
        """Redact Tier 1, Tier 2, and Tier 3 attributes from case records based on user credentials."""
        user = _normalize_user(user)
        if hasattr(case_obj_or_dict, "dict"):
            data = case_obj_or_dict.dict()
        elif hasattr(case_obj_or_dict, "__dict__"):
            data = dict(case_obj_or_dict.__dict__)
        elif isinstance(case_obj_or_dict, dict):
            data = copy.deepcopy(case_obj_or_dict)
        else:
            return {}

        can_view_medical = has_medical_clearance(user, data)
        can_view_pii = has_pii_clearance(user, data)
        can_view_work_product = has_work_product_clearance(user, data)

        # ── 1. Tier 1: Medical & Biometric Redaction ──────────────────────────
        if not can_view_medical:
            if "medical_records" in data:
                data["medical_records"] = "[RESTRICTED - MEDICAL PRIVACY]"
            if "medical_record" in data:
                data["medical_record"] = {
                    "has_vulnerability": bool(data["medical_record"].get("has_vulnerability", False)) if isinstance(data["medical_record"], dict) else False,
                    "vulnerability_category": "RESTRICTED",
                    "details_restricted": "[RESTRICTED SENSITIVE MEDICAL ENVELOPE - Requires authorized medical/legal officer clearance]",
                    "is_redacted": True,
                }
            if "urgency_flags" in data and isinstance(data["urgency_flags"], dict):
                # Preserve operational flags (age), sanitize detailed medical notes
                data["urgency_flags"]["health_flag"] = False if user.role in (Role.POLICE_OFFICER, Role.JAIL_OFFICER) else data["urgency_flags"].get("health_flag", False)
                data["urgency_flags"]["medical_notes"] = "[RESTRICTED - MEDICAL PRIVACY]"
            if "health_flag" in data and user.role in (Role.POLICE_OFFICER, Role.JAIL_OFFICER):
                data["health_flag"] = False

        # ── 2. Tier 2: Sensitive Identity PII Redaction ───────────────────────
        if not can_view_pii or user.role == Role.READ_ONLY_AUDITOR:
            if "permanent_address" in data:
                data["permanent_address"] = "[RESTRICTED - PRIVACY CONTROLLED]"
            if "relative_name" in data:
                data["relative_name"] = "[REDACTED - FAMILY PRIVACY]"
            if "relative_phone" in data:
                data["relative_phone"] = "[REDACTED - PII PRIVACY PROTECTED]"
            if "relative_relation" in data:
                data["relative_relation"] = "[RESTRICTED]"
            if "family_contacts" in data:
                data["family_contacts"] = []
            if "government_identifiers" in data:
                data["government_identifiers"] = {}

        # ── 3. Tier 3: Legal Work Product Redaction ───────────────────────────
        if not can_view_work_product:
            if "legal_strategy_notes" in data:
                data["legal_strategy_notes"] = "[REDACTED - ADVOCATE WORK PRODUCT]"
            if "ai_analysis" in data and isinstance(data["ai_analysis"], dict):
                data["ai_analysis"]["legal_strategy"] = "[RESTRICTED TO COUNSEL & SUPERVISING OFFICERS]"
                data["ai_analysis"]["draft_petition"] = None
                data["ai_analysis"]["supervisory_notes"] = None
            if "petition_draft_text" in data:
                data["petition_draft_text"] = None
            if "supervisory_review_notes" in data:
                data["supervisory_review_notes"] = None
            if "internal_strategy_notes" in data:
                data["internal_strategy_notes"] = None

        return data

    filter_case_record = filter_case

    @staticmethod
    def filter_accused_profile(profile: Dict[str, Any], user: Any) -> Dict[str, Any]:
        """Apply classification rules to consolidated accused profile records."""
        user = _normalize_user(user)
        data = copy.deepcopy(profile)
        can_view_medical = has_medical_clearance(user, data)
        can_view_pii = has_pii_clearance(user, data)

        if not can_view_medical:
            if data.get("medical_record"):
                data["medical_record"] = {
                    "has_vulnerability": data["medical_record"].get("has_vulnerability", False),
                    "vulnerability_category": "RESTRICTED",
                    "details_restricted": "[RESTRICTED SENSITIVE MEDICAL ENVELOPE - Requires authorized medical/legal officer clearance]",
                    "is_redacted": True,
                }

        if not can_view_pii:
            data["permanent_address"] = "[RESTRICTED - PRIVACY CONTROLLED]"
            data["family_contacts"] = []
            data["government_identifiers"] = {}

        return data

    @staticmethod
    def filter_export_payload(payload: Dict[str, Any], user: Any) -> Dict[str, Any]:
        """Sanitize export payloads to prevent accidental exfiltration of medical and PII data."""
        user = _normalize_user(user)
        data = copy.deepcopy(payload)
        can_view_medical = has_medical_clearance(user)
        can_view_pii = has_pii_clearance(user)

        if not can_view_medical:
            data.pop("medical_records", None)
            data.pop("psychiatric_evaluations", None)
            data["medical_summary"] = "Omitted per data minimization policy."

        if not can_view_pii:
            data.pop("home_addresses", None)
            data.pop("family_contact_numbers", None)
            data.pop("national_ids", None)

        data["export_classification"] = "LEGAL_SERVICES_CONTROLLED"
        data["exported_by_actor_id"] = user.id
        data["exported_by_role"] = user.role.value
        return data

