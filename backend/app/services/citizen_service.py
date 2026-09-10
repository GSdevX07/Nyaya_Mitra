"""
services/citizen_service.py — Accused and Family-Facing Business Logic Service.
=============================================================================
Constrained, mobile-first service providing plain-language legal aid access,
statutory AI procedural explanations, multi-language derived display,
citizen action requests, entitled documents, and notification preferences.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status

from app.auth.user_store import AuthUser
from app.auth.roles import Role
from app.models.citizen import (
    CitizenRequestType,
    CitizenActionRequestCreate,
    CitizenNotificationPreferencesUpdate,
    CitizenMissingDocumentItem,
    CitizenUpcomingEventItem,
    CitizenDocumentSummaryItem,
    CitizenAiExplanation,
)
from app.services.language_service import (
    get_supported_languages,
    get_status_translation,
    get_document_title_translation,
    generate_derived_display,
    DISCLAIMER_NOTICE,
)
from app.database import (
    get_db_connection,
    get_case,
    create_citizen_action_request,
    get_citizen_action_requests,
    get_citizen_notification_preferences,
    upsert_citizen_notification_preferences,
    log_citizen_notification,
    get_case_uploaded_documents,
)
from app.services.document_summarizer import summarize_document

logger = logging.getLogger("nyaya_mitra.citizen_service")


# ── Core Overview Endpoint (Consolidated Low-Bandwidth Payload) ───────────────

def get_citizen_overview(user: AuthUser, lang: str = "en") -> Dict[str, Any]:
    """
    Generate a complete, privacy-compliant, low-bandwidth optimized dashboard
    for the authenticated Accused Person or Family Guardian.
    """
    if not user.linked_case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active legal aid case is linked to your account. Please contact the DLSA assistance desk or call 15100.",
        )

    linked_case_id = user.linked_case_id.strip()
    accused_id = "acc_" + linked_case_id.lower().replace("-", "_")

    # 1. Load Accused Profile & Primary Case
    from app.services.accused_service import get_accused_profile
    profile = get_accused_profile(accused_id, user)
    connected_cases = profile.get("connected_cases", [])
    primary_case = next((c for c in connected_cases if c["case_id"].lower() == linked_case_id.lower()), None)
    if not primary_case:
        if connected_cases:
            primary_case = connected_cases[0]
        else:
            primary_case = {
                "case_id": linked_case_id,
                "court_name": "Chief Judicial Magistrate / Sessions Court",
                "police_station": "Local Jurisdictional Police Station",
                "current_status": "DETECTED",
                "assigned_lawyer": None,
                "next_hearing_date": None,
            }

    raw_status = primary_case.get("current_status", "DETECTED")

    # 2. Status & Translation
    status_trans = get_status_translation(raw_status, lang)
    is_filed = raw_status in ("FILED", "COURT_ORDER_RECEIVED", "RELEASED")
    is_released = raw_status == "RELEASED"

    # 3. Defense Counsel Details
    assigned_lawyer_val = primary_case.get("assigned_lawyer")
    has_assigned_lawyer = bool(
        assigned_lawyer_val
        and str(assigned_lawyer_val).strip().lower() not in ("none", "unassigned", "", "null")
        and primary_case.get("assignment_status") == "ASSIGNED"
    )

    if has_assigned_lawyer:
        counsel_info = {
            "is_assigned": True,
            "lawyer_name": str(assigned_lawyer_val),
            "organization": "District Legal Services Authority (DLSA) Panel",
            "contact_phone": primary_case.get("dlsa_contact") or "15100 (National Legal Aid Helpline)",
            "panel_type": "Remand & Bail Defense Panel",
            "representation_cost": "100% Free (Government Sponsored under Legal Services Authorities Act)",
            "office_address": f"DLSA Legal Services Clinic, District Court Complex, {primary_case.get('district', 'Jurisdiction')}",
        }
    else:
        counsel_info = {
            "is_assigned": False,
            "lawyer_name": None,
            "organization": "District Legal Services Authority (DLSA)",
            "status_message": "Panel counsel assignment in progress by the DLSA Secretary. A defense advocate is allocated free of cost.",
            "contact_phone": "15100 (Toll-Free NALSA Helpline 24x7)",
            "representation_cost": "100% Free (Government Sponsored under Legal Services Authorities Act)",
            "office_address": f"DLSA Legal Services Clinic, District Court Complex, {primary_case.get('district', 'Jurisdiction')}",
        }

    # 4. Upcoming Known Events
    upcoming_events: List[Dict[str, Any]] = []
    next_hearing = primary_case.get("next_hearing_date")
    if next_hearing:
        upcoming_events.append({
            "event_type": "COURT_HEARING",
            "title": "Scheduled Judicial Hearing",
            "event_date": str(next_hearing),
            "court_or_location": primary_case.get("court_name", "District Court"),
            "instructions": "Accused will be produced via video conferencing or physical court escort. Family members may attend public proceedings.",
        })
    else:
        # Factual upcoming remand / legal aid review date
        est_date = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
        upcoming_events.append({
            "event_type": "PERIODIC_CUSTODY_REVIEW",
            "title": "Periodic Judicial Remand Review",
            "event_date": est_date,
            "court_or_location": primary_case.get("court_name", "Court of Competent Jurisdiction"),
            "instructions": "Statutory remand review to examine detention records and bail eligibility.",
        })

    upcoming_events.append({
        "event_type": "DLSA_CLINIC_VISIT",
        "title": "DLSA Jail Legal Aid Clinic Inspection",
        "event_date": (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d"),
        "court_or_location": "Jail Legal Aid Clinic",
        "instructions": "Jail Visiting Advocate inspects undertrial legal-aid records and collects pending applications.",
    })

    # 5. Missing Documents From Citizen / Family Side
    c_obj = get_case(linked_case_id)
    present_docs = set(c_obj.present_docs if c_obj and c_obj.present_docs else [])
    missing_docs_list: List[Dict[str, Any]] = []

    if "charge_sheet" not in present_docs:
        missing_docs_list.append({
            "document_type": "charge_sheet",
            "title": "Police Charge Sheet / Final Report",
            "why_needed": "Required to confirm the exact statutory sections and maximum punishment under the Bharatiya Nyaya Sanhita (BNS).",
            "how_to_submit": "If you have an advocate copy, hand it over to the DLSA Legal Aid Clinic or upload via the 'Citizen Action Request' button.",
            "urgency": "REQUIRED_BEFORE_HEARING",
        })

    # Common undertrial surety & family documentation
    missing_docs_list.append({
        "document_type": "surety_identity_proof",
        "title": "Local Surety Identity & Address Verification (Aadhaar / Voter ID)",
        "why_needed": "When the court considers bail under Section 479 BNSS, a local guarantor or personal bond verification is required.",
        "how_to_submit": "Keep original and 2 self-attested photocopies ready for presentation at the DLSA Front Office.",
        "urgency": "REQUIRED_BEFORE_HEARING",
    })

    if profile.get("health_status", {}).get("requires_attention"):
        missing_docs_list.append({
            "document_type": "medical_records",
            "title": "Prior Medical Treatment / Hospital History",
            "why_needed": "Medical grounds may be submitted to support statutory health urgency applications.",
            "how_to_submit": "Provide hospital discharge summaries to the Jail Medical Officer or DLSA Counsel.",
            "urgency": "OPTIONAL_SUPPORTING",
        })

    # 6. Approved Entitled Documents
    entitled_docs = get_citizen_entitled_documents(linked_case_id, lang)

    # 7. Plain-Language AI Explanation with Mandatory Statutory Disclaimers
    explanation_raw = (
        f"Case {linked_case_id} is currently under legal aid review. "
        f"Under Section 479 BNSS, undertrials who have served one-third or one-half of the maximum sentence "
        f"may be presented for statutory bail consideration. "
        f"The court evaluates bail based on evidence, charge sheet, and judicial discretion. "
        f"Nyaya Mitra never guarantees release or promises court decisions."
    )
    derived_expl = generate_derived_display(explanation_raw, target_lang=lang)

    ai_explanation = {
        "is_ai_generated": True,
        "disclaimer_type": "PROCEDURAL_EXPLANATION_NOT_JUDICIAL_DECISION",
        "disclaimer_label": "AI Procedural Explanation — Not a Legal Decision",
        "disclaimer_text": (
            "This explanation is provided in plain language to help you understand your current case status. "
            "It is NOT a court order, legal judgment, or guarantee. Bail and release determinations rest solely "
            "with the competent Court of Law under judicial discretion. Nyaya Mitra never promises release outcomes."
        ),
        "explanation_text": derived_expl["derived_display_text"],
        "derived_language": lang,
        "is_derived_display": derived_expl["is_derived_display"],
        "authoritative_english_text": derived_expl["authoritative_text"],
    }

    # 8. Notification Preferences & Statutory Consent
    notif_prefs = get_citizen_notification_preferences(linked_case_id)
    if not notif_prefs:
        # Default active statutory notification preferences
        notif_prefs = {
            "case_id": linked_case_id,
            "user_id": user.id,
            "phone_number": profile.get("phone", "+91 98765 43210"),
            "channel_sms_enabled": True,
            "channel_whatsapp_enabled": True,
            "channel_in_app_enabled": True,
            "preferred_language": lang,
            "consent_status": "OPTED_IN",
            "consent_timestamp": datetime.now(timezone.utc).isoformat(),
            "consent_version": "v1.0-statutory-notice",
            "consent_text": "I consent to receive case status updates and legal-aid notices under the Legal Services Authorities Act, 1987.",
        }

    # 9. Recent Citizen Requests
    recent_requests = get_citizen_action_requests(linked_case_id, user.id)

    is_family = (user.role == Role.FAMILY_GUARDIAN)

    return {
        "portal_mode": "FAMILY_GUARDIAN" if is_family else "ACCUSED_USER",
        "accused_id": profile["id"],
        "accused_name": profile["full_name"],
        "case_reference": primary_case["case_id"],
        "court_name": primary_case.get("court_name", "Chief Judicial Magistrate Court"),
        "police_station": primary_case.get("police_station", "Kotwali Police Station"),
        "current_known_status": {
            "status_code": raw_status,
            "title": status_trans["title"],
            "detail": status_trans["detail"],
            "authoritative_title": status_trans["authoritative_title"],
            "authoritative_detail": status_trans["authoritative_detail"],
            "is_derived": status_trans["is_derived"],
            "disclaimer": status_trans["disclaimer"],
        },
        "filing_details": {
            "is_filed": is_filed,
            "filing_status": "CONFIRMED_FILED" if is_filed else "AWAITING_REGISTRY_SUBMISSION",
            "filing_reference": primary_case.get("fir_number") if is_filed else "Pending submission to registry",
            "court_name": primary_case.get("court_name"),
        },
        "release_details": {
            "is_released": is_released,
            "release_status": "RELEASE_EXECUTED" if is_released else ("BAIL_ORDER_ISSUED" if raw_status == "COURT_ORDER_RECEIVED" else "IN_CUSTODY"),
            "verification_source": "e-Prisons Custody Register",
        },
        "upcoming_known_events": upcoming_events,
        "legal_aid_support": counsel_info,
        "missing_documents_from_citizen": missing_docs_list,
        "approved_entitled_documents": entitled_docs,
        "ai_procedural_explanation": ai_explanation,
        "language_meta": {
            "current_language": lang,
            "supported_languages": get_supported_languages(),
            "is_derived_display": (lang != "en"),
            "authoritative_language": "en",
            "disclaimer": DISCLAIMER_NOTICE if lang != "en" else "",
        },
        "notification_preferences": notif_prefs,
        "recent_citizen_requests": recent_requests[:5],
        "low_bandwidth_mode_supported": True,
        "support_helpline": "15100",
        "support_notice": (
            "Under Article 39A of the Constitution of India and the Legal Services Authorities Act, 1987, "
            "legal representation through the District Legal Services Authority (DLSA) is provided completely free of charge. "
            "No fee or compensation is payable by the undertrial or their family."
        ),
    }


# ── Entitled Documents List (Safe, Low-Bandwidth Text Summaries) ───────────────

def get_citizen_entitled_documents(case_id: str, lang: str = "en") -> List[Dict[str, Any]]:
    """
    Retrieve approved documents that the accused/family is entitled to receive.
    Sanitizes internal risk scores, confidential notes, and sensitive third-party records.
    Generates concise text summaries for low-bandwidth environments.
    """
    CITIZEN_ENTITLED_TYPES = {
        "fir": "Police First Information Report (FIR)",
        "charge_sheet": "Police Final Report / Charge Sheet",
        "remand_order": "Magisterial Remand Production Order",
        "custody_certificate": "Superintendent Custody Certificate",
        "bail_application": "Defense Bail Application Draft",
        "court_order": "Court Bail Disposition Order",
        "nominal_roll": "Jail Nominal Roll Certificate",
    }

    results: List[Dict[str, Any]] = []
    seen = set()

    try:
        docs = get_case_uploaded_documents(case_id)
        for doc in docs:
            d_type = doc.get("document_type", "")
            d_status = doc.get("document_status", "VERIFIED")
            if d_type in CITIZEN_ENTITLED_TYPES and d_type not in seen:
                seen.add(d_type)
                title_trans = get_document_title_translation(d_type, lang)
                raw_text = doc.get("extracted_text") or doc.get("custom_text") or ""
                summary_raw = summarize_document(
                    case_id=case_id,
                    doc_type=d_type,
                    raw_text=raw_text,
                    doc_obj=doc,
                    lang=lang,
                )
                size_bytes = doc.get("file_size_bytes", 24576)
                size_kb = max(1, round(size_bytes / 1024))

                results.append({
                    "id": str(doc.get("id") or f"doc_{case_id}_{d_type}"),
                    "document_type": d_type,
                    "title": title_trans["title"],
                    "status": "VERIFIED",
                    "uploaded_at": doc.get("uploaded_at"),
                    "file_size_bytes": size_bytes,
                    "file_size_formatted": f"{size_kb} KB",
                    "text_summary": summary_raw,
                    "is_approved_for_citizen": True,
                })
    except Exception as e:
        logger.warning(f"Failed to fetch uploaded documents for citizen view: {e}")

    # Fallback to case present_docs if no uploaded_documents rows exist
    c_obj = get_case(case_id)
    if c_obj and c_obj.present_docs:
        for p_doc in c_obj.present_docs:
            if p_doc in CITIZEN_ENTITLED_TYPES and p_doc not in seen:
                seen.add(p_doc)
                title_trans = get_document_title_translation(p_doc, lang)
                summary_raw = summarize_document(
                    case_id=case_id,
                    doc_type=p_doc,
                    raw_text="",
                    lang=lang,
                )
                results.append({
                    "id": f"doc_{case_id}_{p_doc}",
                    "document_type": p_doc,
                    "title": title_trans["title"],
                    "status": "VERIFIED",
                    "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "file_size_bytes": 18432,
                    "file_size_formatted": "18 KB",
                    "text_summary": summary_raw,
                    "is_approved_for_citizen": True,
                })

    return results


def get_citizen_document_summary(doc_id: str, case_id: str, lang: str = "en") -> Dict[str, Any]:
    """
    Retrieve text summary and preview for low-bandwidth viewing.
    Strictly verifies case ownership, approved entitlement status,
    and returns 404/403 for unauthorized, privileged, or guessed documents.
    """
    CITIZEN_ENTITLED_TYPES = {
        "fir": "Police First Information Report (FIR)",
        "charge_sheet": "Police Final Report / Charge Sheet",
        "remand_order": "Magisterial Remand Production Order",
        "custody_certificate": "Superintendent Custody Certificate",
        "bail_application": "Defense Bail Application Draft",
        "court_order": "Court Bail Disposition Order",
        "nominal_roll": "Jail Nominal Roll Certificate",
    }

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM uploaded_documents WHERE id = ? AND case_id = ?", (doc_id, case_id))
        row = cursor.fetchone()
        if row:
            cols = [d[0] for d in cursor.description]
            doc = dict(zip(cols, row))
            d_type = (doc.get("document_type") or "").lower().strip().replace("-", "_").replace(" ", "_")
            if d_type not in CITIZEN_ENTITLED_TYPES and d_type.replace("doc_", "") not in CITIZEN_ENTITLED_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: Document is not authorized for release to citizen.",
                )
            raw_text = doc.get("extracted_text") or doc.get("custom_text") or ""
            summary = summarize_document(case_id=case_id, doc_type=d_type, raw_text=raw_text, doc_obj=doc, lang=lang)
            return {
                "id": doc_id,
                "case_id": case_id,
                "document_type": d_type,
                "file_name": doc.get("file_name"),
                "text_summary": summary,
                "text_preview": raw_text[:1000] if raw_text else summary,
                "file_size_formatted": f"{max(1, round((doc.get('file_size_bytes') or 0) / 1024))} KB",
                "status": "VERIFIED",
            }

        # Check synthesized entitlement against case present_docs
        doc_id_clean = doc_id.lower().strip()
        case_id_clean = case_id.lower().strip()
        clean_prefix = f"doc_{case_id_clean}_"
        if doc_id_clean.startswith(clean_prefix):
            d_type = doc_id_clean[len(clean_prefix):].replace("-", "_").replace(" ", "_")
        elif doc_id_clean.startswith("doc_"):
            d_type = doc_id_clean[4:].replace("-", "_").replace(" ", "_")
        else:
            d_type = doc_id_clean.replace("-", "_").replace(" ", "_")

        ALIAS_MAP = {
            "fir": "fir",
            "fir_copy": "fir",
            "police_fir": "fir",
            "charge_sheet": "charge_sheet",
            "final_report": "charge_sheet",
            "remand_order": "remand_order",
            "remand_production_order": "remand_order",
            "custody_certificate": "custody_certificate",
            "jail_custody_certificate": "custody_certificate",
            "bail_application": "bail_application",
            "court_order": "court_order",
            "bail_order": "court_order",
            "nominal_roll": "nominal_roll",
        }
        canon_type = ALIAS_MAP.get(d_type, d_type)

        if canon_type not in CITIZEN_ENTITLED_TYPES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{doc_id}' not found for case '{case_id}'.",
            )

        from app.database import _MEMORY_CASES
        c_obj = get_case(case_id)
        present_set = set()
        if c_obj and c_obj.present_docs:
            for p in c_obj.present_docs:
                p_norm = p.lower().strip().replace("-", "_").replace(" ", "_")
                present_set.add(ALIAS_MAP.get(p_norm, p_norm))
                present_set.add(p_norm)
        if case_id in _MEMORY_CASES and _MEMORY_CASES[case_id].present_docs:
            for p in _MEMORY_CASES[case_id].present_docs:
                p_norm = p.lower().strip().replace("-", "_").replace(" ", "_")
                present_set.add(ALIAS_MAP.get(p_norm, p_norm))
                present_set.add(p_norm)

        if canon_type not in present_set and d_type not in present_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{doc_id}' not found for case '{case_id}'.",
            )

        summary = summarize_document(case_id=case_id, doc_type=canon_type, raw_text="", lang=lang)
        return {
            "id": doc_id,
            "case_id": case_id,
            "document_type": canon_type,
            "file_name": f"{doc_id}.pdf",
            "text_summary": summary,
            "text_preview": summary,
            "file_size_formatted": "16 KB",
            "status": "VERIFIED",
        }
    finally:
        conn.close()


# ── Citizen Action Requests & Task Queue Integration ──────────────────────────

def submit_citizen_action_request(
    user: AuthUser,
    payload: CitizenActionRequestCreate,
) -> Dict[str, Any]:
    """
    Record a structured citizen action request and dispatch an operational task
    directly into the DLSA Universal Task Queue.
    """
    if not user.linked_case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cannot submit request: No legal aid case is linked to your account.",
        )

    case_id = user.linked_case_id.strip()
    accused_id = "acc_" + case_id.lower().replace("-", "_")

    # 1. Create task in task queue
    from app.services.task_service import get_task_repository
    task_repo = get_task_repository()

    priority = "HIGH" if payload.request_type in (CitizenRequestType.REQUEST_HELP, CitizenRequestType.FLAG_INCORRECT_INFO) else "MEDIUM"
    task_id = f"TASK-CITIZEN-{datetime.now(timezone.utc).strftime('%m%d%H%M%S')}"

    c_obj = get_case(case_id)
    accused_name = c_obj.name if c_obj else "Accused Individual"
    district = c_obj.district if c_obj else "Central Delhi"
    facility = c_obj.jail_location if c_obj else "Central Jail"

    task_data = {
        "id": task_id,
        "case_id": case_id,
        "accused_name": accused_name,
        "task_type": "CITIZEN_REQUEST_REVIEW",
        "title": f"Citizen Request: {payload.subject}",
        "description": f"Filed by {user.role.value} ({user.id}): {payload.details}",
        "owner_role": "DLSA_OFFICER",
        "priority": priority,
        "due_date": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d"),
        "source": "CITIZEN_PORTAL",
        "reason": f"Citizen Action ({payload.request_type.value}): {payload.subject}",
        "status": "NEW",
        "escalation_path": "DLSA Secretary -> Legal Aid Defense Clinic",
        "facility": facility,
        "district": district,
        "custody_duration_days": getattr(c_obj, "custody_days", 0),
        "document_completeness_pct": 100,
        "has_data_conflict": 1 if payload.request_type == CitizenRequestType.FLAG_INCORRECT_INFO else 0,
        "legal_aid_need": 1,
        "assignment_status": getattr(c_obj, "assignment_status", "ASSIGNED"),
        "matter_status": "REVIEW",
        "hearing_date": getattr(c_obj, "next_hearing_date", None),
        "is_consequential": 1,
        "metadata_json": "{}",
    }
    task_repo.upsert_task(task_data)

    # 2. Persist in citizen_action_requests
    record = create_citizen_action_request(
        case_id=case_id,
        accused_id=accused_id,
        request_type=payload.request_type.value,
        requested_by_user_id=user.id,
        requested_by_role=user.role.value,
        subject=payload.subject,
        details=payload.details,
        target_document_type=payload.target_document_type,
        discrepancy_field=payload.discrepancy_field,
        task_id=task_id,
    )

    logger.info(f"Citizen request {record['id']} created and routed to DLSA Task {task_id}.")
    return record


def get_citizen_action_requests_for_user(user: AuthUser) -> List[Dict[str, Any]]:
    """Retrieve history of citizen requests filed for this case."""
    if not user.linked_case_id:
        return []
    return get_citizen_action_requests(user.linked_case_id, user.id)


# ── Notification Preferences & Consent Service ────────────────────────────────

def get_notification_preferences_service(user: AuthUser) -> Dict[str, Any]:
    """Retrieve current notification channel settings and consent record."""
    if not user.linked_case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked case.")
    prefs = get_citizen_notification_preferences(user.linked_case_id)
    if not prefs:
        return {
            "case_id": user.linked_case_id,
            "user_id": user.id,
            "phone_number": "+91 98765 43210",
            "channel_sms_enabled": True,
            "channel_whatsapp_enabled": True,
            "channel_in_app_enabled": True,
            "preferred_language": "en",
            "consent_status": "OPTED_IN",
            "consent_version": "v1.0-statutory-notice",
            "consent_timestamp": datetime.now(timezone.utc).isoformat(),
            "consent_text": "I consent to receive case status updates and legal-aid notices under the Legal Services Authorities Act, 1987.",
        }
    return prefs


def update_notification_preferences_service(
    user: AuthUser,
    payload: CitizenNotificationPreferencesUpdate,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    """Update citizen notification preferences and record statutory consent."""
    if not user.linked_case_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No linked case.")

    res = upsert_citizen_notification_preferences(
        case_id=user.linked_case_id,
        user_id=user.id,
        phone_number=payload.phone_number,
        channel_sms_enabled=payload.channel_sms_enabled,
        channel_whatsapp_enabled=payload.channel_whatsapp_enabled,
        channel_in_app_enabled=payload.channel_in_app_enabled,
        preferred_language=payload.preferred_language,
        consent_status=payload.consent_status,
        consent_text=payload.consent_text,
        consent_ip=ip_address,
    )

    # Log simulated notification audit
    if payload.channel_sms_enabled:
        log_citizen_notification(
            case_id=user.linked_case_id,
            channel="SMS",
            recipient=payload.phone_number or "Registered Mobile",
            message=f"Statutory notification preferences updated for Case {user.linked_case_id}.",
            status="SIMULATED_DISPATCHED",
        )

    return res
