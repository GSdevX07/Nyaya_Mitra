"""
tests/test_notification_escalation_system.py — Comprehensive Test Suite for Notification & Escalation Engine.
"""
import pytest
import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import init_db, get_db_connection
from app.notifications import (
    NotificationEventType,
    NotificationChannel,
    NotificationPriority,
    DeliveryStatus,
    NotificationRecord,
    UserNotificationPreferences,
    EscalationPolicy,
    EscalationTierConfig,
    NotificationService,
    NotificationRepository,
    compute_idempotency_key,
    is_in_quiet_hours,
    can_bypass_quiet_hours,
    filter_channels_for_delivery,
    EscalationManager,
)
from app.notifications.adapters.base import ChannelAdapterRegistry

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_notification_db():
    init_db()
    yield


def _auth_headers(role: Role, user_id: str = "test_user", linked_case_id: str = None) -> dict:
    claims = {"linked_case_id": linked_case_id} if linked_case_id else None
    token = create_access_token(
        subject=user_id,
        role=role.value,
        org_id="org_central",
        extra_claims=claims,
    )
    return {"Authorization": f"Bearer {token}"}


# ── 1. Test All 10 Canonical Event Types ─────────────────────────────────────

def test_all_ten_canonical_event_types():
    """Verify that all 10 statutory event types generate valid notification records."""
    assert len(NotificationEventType) == 10

    test_matrix = [
        (NotificationEventType.NEW_LEGAL_AID_NEED, "UTP-1001", NotificationPriority.STANDARD),
        (NotificationEventType.APPROACHING_CUSTODY_THRESHOLD, "UTP-1002", NotificationPriority.HIGH),
        (NotificationEventType.OVERDUE_ACTION, "UTP-1003", NotificationPriority.HIGH),
        (NotificationEventType.MISSING_DOCUMENT, "UTP-1004", NotificationPriority.STANDARD),
        (NotificationEventType.HEARING_APPROACHING, "UTP-1005", NotificationPriority.STANDARD),
        (NotificationEventType.ORDER_RECEIVED, "UTP-1006", NotificationPriority.STANDARD),
        (NotificationEventType.RELEASE_RECORDED, "UTP-1007", NotificationPriority.HIGH),
        (NotificationEventType.UNRESOLVED_IDENTITY_CONFLICT, "UTP-1008", NotificationPriority.HIGH),
        (NotificationEventType.INTEGRATION_FAILURE, "SYS-SYNC", NotificationPriority.HIGH),
        (NotificationEventType.SECURITY_EVENT, "AUDIT-THREAT", NotificationPriority.EMERGENCY),
    ]

    for ev_type, case_or_ref, expected_prio in test_matrix:
        rec = NotificationService.dispatch(
            event_type=ev_type,
            case_id=case_or_ref,
            payload={"case_id": case_or_ref, "name": "Under-Trial Inmate", "fingerprint": f"test-{ev_type.value}"},
        )
        assert rec is not None
        assert rec.id.startswith("NOTIF-")
        assert rec.event_type == ev_type
        assert rec.priority == expected_prio
        assert rec.delivery_status == DeliveryStatus.DELIVERED
        assert len(rec.title) > 0
        assert len(rec.message) > 0


# ── 2. Test Deterministic Deduplication ──────────────────────────────────────

def test_idempotency_deduplication_prevents_duplicate_notifications():
    """Verify that reprocessing the same event returns the existing record without duplicating."""
    fingerprint = "reprocess-batch-token-123"
    payload = {"case_id": "UTP-DEDUP-01", "name": "Mohan Lal", "fingerprint": fingerprint}

    # First dispatch
    rec1 = NotificationService.dispatch(
        event_type=NotificationEventType.APPROACHING_CUSTODY_THRESHOLD,
        case_id="UTP-DEDUP-01",
        payload=payload,
        recipient="DEFENSE_ADVOCATE",
    )
    assert rec1 is not None

    # Immediate second dispatch with identical event, entity, and fingerprint
    rec2 = NotificationService.dispatch(
        event_type=NotificationEventType.APPROACHING_CUSTODY_THRESHOLD,
        case_id="UTP-DEDUP-01",
        payload=payload,
        recipient="DEFENSE_ADVOCATE",
    )

    # Must return identical record ID and suppress duplicate
    assert rec2.id == rec1.id
    assert rec2.idempotency_key == rec1.idempotency_key


# ── 3. Test Pluggable Multi-Channel Adapters ────────────────────────────────

def test_pluggable_channel_adapters():
    """Verify all 4 delivery adapters (In-App, SMS, Email, WhatsApp) execute cleanly."""
    channels = [
        NotificationChannel.IN_APP,
        NotificationChannel.SMS,
        NotificationChannel.EMAIL,
        NotificationChannel.WHATSAPP,
    ]

    for ch in channels:
        adapter = ChannelAdapterRegistry.get(ch)
        assert adapter is not None
        assert adapter.channel == ch

        rec = NotificationService.dispatch(
            event_type=NotificationEventType.ORDER_RECEIVED,
            case_id="UTP-CH-01",
            payload={
                "case_id": "UTP-CH-01",
                "phone": "+919811223344",
                "email": "counsel@nyayamitra.gov.in",
                "fingerprint": f"channel-{ch.value}",
            },
            channels=[ch],
        )
        assert rec.delivery_status == DeliveryStatus.DELIVERED
        assert len(rec.retry_history) >= 1
        assert rec.retry_history[-1].success is True


# ── 4. Test Quiet Hours and Emergency Overrides ──────────────────────────────

def test_quiet_hours_suppression_and_emergency_override():
    """Verify standard alerts are silenced during quiet hours while emergencies bypass."""
    # User with quiet hours enabled from 22:00 to 06:00
    prefs = UserNotificationPreferences(
        user_id="usr_quiet_test",
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="06:00",
        enabled_channels=[NotificationChannel.IN_APP, NotificationChannel.SMS, NotificationChannel.EMAIL],
    )
    NotificationRepository.save_user_preferences(prefs)

    # Midnight time: 02:30 UTC
    midnight_time = datetime.datetime(2026, 9, 8, 2, 30, tzinfo=datetime.timezone.utc)
    assert is_in_quiet_hours(midnight_time, prefs) is True

    # Afternoon time: 14:30 UTC
    day_time = datetime.datetime(2026, 9, 8, 14, 30, tzinfo=datetime.timezone.utc)
    assert is_in_quiet_hours(day_time, prefs) is False

    # 1. Standard event during quiet hours -> Suppresses disruptive channels (SMS/WhatsApp)
    allowed_standard, is_override_std = filter_channels_for_delivery(
        priority=NotificationPriority.STANDARD,
        event_type=NotificationEventType.HEARING_APPROACHING,
        prefs=prefs,
        now=midnight_time,
    )
    assert is_override_std is False
    assert allowed_standard == [NotificationChannel.IN_APP]

    # 2. Emergency event during quiet hours -> Bypasses quiet hours and retains SMS
    allowed_emerg, is_override_emerg = filter_channels_for_delivery(
        priority=NotificationPriority.EMERGENCY,
        event_type=NotificationEventType.SECURITY_EVENT,
        prefs=prefs,
        now=midnight_time,
    )
    assert is_override_emerg is True
    assert NotificationChannel.SMS in allowed_emerg

    # 3. Statutory approaching custody threshold -> Bypasses quiet hours
    assert can_bypass_quiet_hours(NotificationPriority.HIGH, NotificationEventType.APPROACHING_CUSTODY_THRESHOLD) is True


# ── 5. Test Multi-Tier Escalation Chains ─────────────────────────────────────

def test_multi_tier_escalation_progression():
    """Verify overdue action escalates through Tier 1 -> Tier 2 -> Tier 3."""
    # Tier 1 Initial dispatch
    tier1_rec = NotificationService.dispatch(
        event_type=NotificationEventType.OVERDUE_ACTION,
        case_id="UTP-ESC-01",
        payload={"action_title": "File Section 479 Bail Application", "fingerprint": "esc-t1"},
        target_role="DEFENSE_ADVOCATE",
        escalation_tier=1,
    )
    assert tier1_rec.escalation_tier == 1
    assert "DEFENSE_ADVOCATE" in tier1_rec.target_role

    # Escalate to Tier 2 (Supervising Legal Officer)
    tier2_rec = NotificationService.escalate(tier1_rec.id)
    assert tier2_rec is not None
    assert tier2_rec.escalation_tier == 2
    assert "SUPERVISING_LEGAL_OFFICER" in tier2_rec.target_role
    assert "Escalation Tier 2" in tier2_rec.title

    # Escalate to Tier 3 (DLSA Officer)
    tier3_rec = NotificationService.escalate(tier2_rec.id)
    assert tier3_rec is not None
    assert tier3_rec.escalation_tier == 3
    assert "DLSA_OFFICER" in tier3_rec.target_role
    assert "Escalation Tier 3" in tier3_rec.title

    # Attempting to escalate beyond Tier 3 should return None
    tier4_rec = NotificationService.escalate(tier3_rec.id)
    assert tier4_rec is None


# ── 6. Test Delivery Failure & Dead-Letter Queue (DLQ) Operational Task ─────

def test_delivery_failure_routes_to_dlq_and_triggers_task():
    """Verify that exhausted delivery retries route to DLQ and automatically create an operational task."""
    # Inject forced failure into adapter execution
    fail_payload = {
        "case_id": "UTP-FAIL-01",
        "name": "Failed Delivery Inmate",
        "phone": "+919876543211",
        "fingerprint": "fail-test-dlq",
        "force_failure": True,
    }

    rec = NotificationService.dispatch(
        event_type=NotificationEventType.SECURITY_EVENT,
        case_id="UTP-FAIL-01",
        payload=fail_payload,
        channels=[NotificationChannel.SMS],
        max_retries=2,
        recipient_meta={"force_failure": True, "phone": "+919876543211"},
    )

    # Must transition to DEAD_LETTER
    assert rec.delivery_status == DeliveryStatus.DEAD_LETTER
    assert len(rec.retry_history) == 2
    assert all(r.success is False for r in rec.retry_history)

    # Verify DLQ entry exists
    dlq_entries = NotificationRepository.get_dlq_entries()
    matching_dlq = next((d for d in dlq_entries if d["notification_id"] == rec.id), None)
    assert matching_dlq is not None
    assert matching_dlq["status"] == "DEAD_LETTER"
    assert matching_dlq["task_id"] is not None
    assert "TASK-DLQ-" in matching_dlq["task_id"]

    # Test manual DLQ retry
    retry_ok = NotificationService.retry_dlq(matching_dlq["id"])
    assert retry_ok is True


# ── 7. Test Acknowledgement & Soft-Dismissal (Audit Preserving) ──────────────

def test_acknowledgement_and_soft_dismissal_preserves_audit():
    """Verify that acknowledging and dismissing notifications updates status without deleting records."""
    rec = NotificationService.dispatch(
        event_type=NotificationEventType.MISSING_DOCUMENT,
        case_id="UTP-AUDIT-01",
        payload={"document_type": "remand_order", "fingerprint": "audit-ack-dism"},
        target_role="DLSA_OFFICER",
    )

    # Acknowledge
    ack_res = NotificationService.acknowledge(rec.id, user_id="usr_dlsa_01")
    assert ack_res is True

    stored = NotificationRepository.get_by_id(rec.id)
    assert stored.is_acknowledged is True
    assert stored.acknowledged_by == "usr_dlsa_01"
    assert stored.acknowledged_at is not None

    # Soft-dismiss
    dism_res = NotificationService.dismiss(rec.id, user_id="usr_dlsa_01")
    assert dism_res is True

    # Record still exists in database! Never hard-deleted!
    stored_after_dism = NotificationRepository.get_by_id(rec.id)
    assert stored_after_dism is not None
    assert stored_after_dism.is_dismissed is True
    assert stored_after_dism.dismissed_at is not None


# ── 8. Test Notification REST Endpoints ─────────────────────────────────────

def test_api_notification_endpoints():
    """Verify REST endpoints for listing, filtering, preferences, and DLQ."""
    headers_admin = _auth_headers(Role.PLATFORM_ADMIN, user_id="demo_platform_admin")
    headers_adv = _auth_headers(Role.DEFENSE_ADVOCATE, user_id="demo_advocate")

    # 1. Dispatch through API
    dispatch_res = client.post(
        "/api/notifications/dispatch",
        json={
            "event_type": "NEW_LEGAL_AID_NEED",
            "case_id": "UTP-API-01",
            "priority": "HIGH",
            "target_role": "DEFENSE_ADVOCATE",
            "payload": {"name": "Sita Ram", "fingerprint": "api-dispatch-01"},
        },
        headers=headers_admin,
    )
    assert dispatch_res.status_code == 200
    notif_data = dispatch_res.json()
    notif_id = notif_data["id"]

    # 2. Filter endpoint
    list_res = client.get(
        "/api/notifications?priority=HIGH",
        headers=headers_adv,
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(i["id"] == notif_id for i in items)

    # 3. Acknowledge endpoint
    ack_res = client.patch(f"/api/notifications/{notif_id}/acknowledge", headers=headers_adv)
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "success"

    # 4. Soft-dismiss endpoint
    dism_res = client.post(f"/api/notifications/{notif_id}/dismiss", headers=headers_adv)
    assert dism_res.status_code == 200
    assert "Audit record preserved" in dism_res.json()["message"]

    # 5. Preferences GET & PUT
    pref_put = client.put(
        "/api/notifications/preferences",
        json={
            "preferred_language": "hi",
            "quiet_hours_enabled": True,
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "05:00",
            "phone_number": "+919876543210",
        },
        headers=headers_adv,
    )
    assert pref_put.status_code == 200
    assert pref_put.json()["preferred_language"] == "hi"
    assert pref_put.json()["quiet_hours_enabled"] is True

    pref_get = client.get("/api/notifications/preferences", headers=headers_adv)
    assert pref_get.status_code == 200
    assert pref_get.json()["preferred_language"] == "hi"

    # 6. DLQ endpoint
    dlq_res = client.get("/api/notifications/dlq", headers=headers_admin)
    assert dlq_res.status_code == 200
    assert isinstance(dlq_res.json(), list)
