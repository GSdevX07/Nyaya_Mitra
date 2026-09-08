"""
app.notifications.rules — Configurable Rules for Canonical Nyaya Mitra Events.
"""
from __future__ import annotations

import hashlib
import datetime
from typing import Dict, Any, Tuple
from app.notifications.schemas import (
    NotificationEventType,
    NotificationPriority,
)

EVENT_RULE_REGISTRY: Dict[NotificationEventType, Dict[str, Any]] = {
    NotificationEventType.NEW_LEGAL_AID_NEED: {
        "title": "New Legal Aid Need Identified",
        "default_priority": NotificationPriority.STANDARD,
        "default_roles": "DLSA_OFFICER,SUPERVISING_LEGAL_OFFICER",
        "description": "An undertrial or citizen requires pro bono defense representation.",
        "template": "Legal aid assistance required for {name} ({case_id}). Needs assignment of defense counsel.",
    },
    NotificationEventType.APPROACHING_CUSTODY_THRESHOLD: {
        "title": "Approaching Statutory Custody Threshold",
        "default_priority": NotificationPriority.HIGH,
        "default_roles": "DEFENSE_ADVOCATE,JAIL_OFFICER,DLSA_OFFICER",
        "description": "Custody duration has approached statutory milestone (1/3 or 1/2 max sentence) under Section 479 BNSS.",
        "template": "Undertrial {name} ({case_id}) has served {custody_days} days. Eligible threshold of {threshold_days} days approaching.",
    },
    NotificationEventType.OVERDUE_ACTION: {
        "title": "SLA Escalation: Overdue Operational Action",
        "default_priority": NotificationPriority.HIGH,
        "default_roles": "DEFENSE_ADVOCATE,SUPERVISING_LEGAL_OFFICER",
        "description": "Task or statutory response SLA exceeded without action.",
        "template": "Urgent: Action '{action_title}' for case {case_id} is overdue by {overdue_hours} hours. Immediate resolution required.",
    },
    NotificationEventType.MISSING_DOCUMENT: {
        "title": "Critical Docket Document Missing",
        "default_priority": NotificationPriority.STANDARD,
        "default_roles": "JAIL_OFFICER,DEFENSE_ADVOCATE,DLSA_OFFICER",
        "description": "Remand order, chargesheet, or nominal roll missing for undertrial docket.",
        "template": "Mandatory document '{document_type}' is missing for case {case_id} ({name}). Docket cannot proceed without verification.",
    },
    NotificationEventType.HEARING_APPROACHING: {
        "title": "Court Hearing Date Approaching",
        "default_priority": NotificationPriority.STANDARD,
        "default_roles": "DEFENSE_ADVOCATE,ACCUSED_USER,FAMILY_GUARDIAN",
        "description": "Upcoming court session scheduled within 48-72 hours.",
        "template": "Hearing scheduled on {hearing_date} before {court_name} for case {case_id}. Review defense submissions.",
    },
    NotificationEventType.ORDER_RECEIVED: {
        "title": "Judicial Order Received",
        "default_priority": NotificationPriority.STANDARD,
        "default_roles": "DEFENSE_ADVOCATE,JAIL_OFFICER,ACCUSED_USER,SUPERVISING_LEGAL_OFFICER",
        "description": "Formal bail or remand order entered into docket.",
        "template": "Judicial order received for case {case_id} from {court_name}. Order outcome: {order_outcome}.",
    },
    NotificationEventType.RELEASE_RECORDED: {
        "title": "Physical Release Confirmed from Custody",
        "default_priority": NotificationPriority.HIGH,
        "default_roles": "JAIL_OFFICER,DEFENSE_ADVOCATE,DLSA_OFFICER,ACCUSED_USER",
        "description": "Undertrial discharged from detention facility on bail bond or PR bond.",
        "template": "Formal physical discharge confirmed for {name} ({case_id}) from {jail_location} pursuant to bail order.",
    },
    NotificationEventType.UNRESOLVED_IDENTITY_CONFLICT: {
        "title": "Unresolved Inmate Identity Conflict Flagged",
        "default_priority": NotificationPriority.HIGH,
        "default_roles": "JAIL_OFFICER,SUPERVISING_LEGAL_OFFICER,PLATFORM_ADMIN",
        "description": "Biometric or nominal roll collision detected across institutional records.",
        "template": "Discrepancy detected in identity/nominal roll records for inmate {name} ({case_id}). Fingerprint/Aadhaar match conflict requires clearance.",
    },
    NotificationEventType.INTEGRATION_FAILURE: {
        "title": "External System Integration Failure",
        "default_priority": NotificationPriority.HIGH,
        "default_roles": "PLATFORM_ADMIN,GOV_ADMIN",
        "description": "eCourts, ICJS, or ePrisons synchronizer connection failed or timed out.",
        "template": "Integration connection failed with {external_system}: endpoint {endpoint} returned error '{error_snippet}'.",
    },
    NotificationEventType.SECURITY_EVENT: {
        "title": "High Severity Security Event Detected",
        "default_priority": NotificationPriority.EMERGENCY,
        "default_roles": "PLATFORM_ADMIN,GOV_ADMIN,READ_ONLY_AUDITOR",
        "description": "Prompt injection, binary signature threat, or unauthorized break-glass access.",
        "template": "Security threat flagged: {threat_type} detected on entity {entity_id}. Triggered policy: {security_policy}.",
    },
}


def compute_idempotency_key(
    event_type: NotificationEventType,
    entity_id: str,
    recipient: str,
    fingerprint: str = "",
) -> str:
    """
    Computes deterministic SHA-256 idempotency key to prevent duplicate notifications
    when the same event is reprocessed within the same calendar day or batch run.
    """
    today_bucket = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    raw_str = f"{event_type.value}:{str(entity_id).strip()}:{str(recipient).strip()}:{fingerprint or today_bucket}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def format_event_content(
    event_type: NotificationEventType,
    payload: Dict[str, Any],
) -> Tuple[str, str, NotificationPriority, str]:
    """
    Resolves default title, formatted message, priority, and default target roles for an event.
    """
    rule = EVENT_RULE_REGISTRY.get(event_type, {
        "title": event_type.value.replace("_", " ").title(),
        "default_priority": NotificationPriority.STANDARD,
        "default_roles": "ALL",
        "template": "System event {event_type} occurred.",
    })

    title = payload.get("title") or rule["title"]
    priority = payload.get("priority") or rule["default_priority"]
    if isinstance(priority, str):
        priority = NotificationPriority(priority)

    default_roles = rule.get("default_roles", "ALL")

    # Interpolate template safely
    tpl = rule.get("template", "{message}")
    format_kwargs = {
        "event_type": event_type.value,
        "name": payload.get("accused_name") or payload.get("name", "Accused Person"),
        "case_id": payload.get("case_id", "General"),
        "custody_days": payload.get("custody_days", "N/A"),
        "threshold_days": payload.get("threshold_days", "N/A"),
        "action_title": payload.get("action_title", "Operational Task"),
        "overdue_hours": payload.get("overdue_hours", "24"),
        "document_type": payload.get("document_type", "Document"),
        "hearing_date": payload.get("hearing_date", "Upcoming"),
        "court_name": payload.get("court_name", "Court of Competent Jurisdiction"),
        "order_outcome": payload.get("order_outcome", "Recorded"),
        "jail_location": payload.get("jail_location", "Detention Facility"),
        "external_system": payload.get("external_system", "Integrated Portal"),
        "endpoint": payload.get("endpoint", "/sync"),
        "error_snippet": payload.get("error_snippet", "Connection Timeout"),
        "threat_type": payload.get("threat_type", "Security Policy Violation"),
        "entity_id": payload.get("entity_id", payload.get("case_id", "System")),
        "security_policy": payload.get("security_policy", "Default AI Guardrails"),
        "message": payload.get("message", rule.get("description", "")),
    }

    try:
        message = payload.get("message") or tpl.format(**format_kwargs)
    except Exception:
        message = payload.get("message") or rule.get("description", "System event notification.")

    return title, message, priority, default_roles
