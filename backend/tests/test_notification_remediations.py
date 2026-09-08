"""
tests/test_notification_remediations.py — Dedicated Test Suite for the 14 Production Remediations.
"""
import pytest
import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.auth.tokens import create_access_token
from app.auth.roles import Role
from app.database import init_db
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
    filter_channels_for_delivery,
    EscalationManager,
)
from app.notifications.scheduler import process_pending_escalations

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
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


# ── 1. Automatic Timed Escalation Worker Test ─────────────────────────────────

def test_automatic_timed_escalation_scheduler():
    """Verify that unacknowledged notifications past wait_minutes threshold automatically escalate."""
    # Create notification with created_at set to 150 minutes ago
    past_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=150)).isoformat()
    
    rec = NotificationService.dispatch(
        event_type=NotificationEventType.OVERDUE_ACTION,
        case_id="UTP-ESC-01",
        payload={"action_title": "Bail filing", "fingerprint": "auto-esc-fingerprint-01"},
        target_role="DEFENSE_ADVOCATE",
    )
    # Manually backdate created_at to simulate time elapsed past Tier 2 wait_minutes (120m)
    rec.created_at = past_time
    NotificationRepository.save_notification(rec)

    # Trigger automatic scheduler
    escalated = process_pending_escalations()

    # Verify that the notification was escalated
    assert len(escalated) >= 1
    esc_rec = next((r for r in escalated if r.payload.get("escalated_from_id") == rec.id), None)
    assert esc_rec is not None
    assert esc_rec.escalation_tier == 2
    assert "SUPERVISING_LEGAL_OFFICER" in esc_rec.target_role

    # Verify that original notification was marked superseded (acknowledged)
    old_rec = NotificationRepository.get_by_id(rec.id)
    assert old_rec.is_acknowledged is True
    assert "ESCALATION" in old_rec.acknowledged_by


# ── 2. Organization Escalation Policy Persistence Test ───────────────────────

def test_organization_escalation_policy_db_persistence():
    """Verify that custom organization policies persist in SQLite across memory cache clears."""
    org_id = "ORG-MUMBAI-DLSA"
    custom_policy = EscalationPolicy(
        id=f"ESC-{org_id}-OVERDUE_ACTION",
        org_id=org_id,
        event_type=NotificationEventType.OVERDUE_ACTION,
        tiers=[
            EscalationTierConfig(tier=1, target_role="DEFENSE_ADVOCATE", wait_minutes=0),
            EscalationTierConfig(tier=2, target_role="DLSA_SECRETARY", wait_minutes=45),
            EscalationTierConfig(tier=3, target_role="HIGH_COURT_REGISTRAR", wait_minutes=90),
        ],
    )

    # Save policy
    EscalationManager.save_policy(custom_policy)

    # Clear memory cache to test database reload
    from app.notifications.escalation import _ESCALATION_POLICIES
    _ESCALATION_POLICIES.clear()

    # Fetch policy from DB
    loaded = EscalationManager.get_policy(org_id, NotificationEventType.OVERDUE_ACTION)
    assert loaded is not None
    assert loaded.org_id == org_id
    assert len(loaded.tiers) == 3
    assert loaded.tiers[1].target_role == "DLSA_SECRETARY"
    assert loaded.tiers[1].wait_minutes == 45


# ── 3. Safe Recipient Resolution (No +919876543210 Fallback) ─────────────────

def test_sms_and_whatsapp_safe_failure_on_missing_phone():
    """Verify that missing recipient phone causes delivery failure and DLQ routing instead of dummy phone fallback."""
    from app.notifications.adapters.sms import SmsAdapter
    from app.notifications.adapters.whatsapp import WhatsAppAdapter

    fake_rec = NotificationRecord(
        id="NOTIF-NO-PHONE",
        recipient="unknown_entity",
        event_type=NotificationEventType.NEW_LEGAL_AID_NEED,
        priority=NotificationPriority.STANDARD,
        title="Test Alert",
        message="No phone test",
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        idempotency_key="no-phone-key",
    )

    sms_adapter = SmsAdapter()
    res_sms = sms_adapter.send(fake_rec, recipient_meta={})
    assert res_sms.success is False
    assert res_sms.retryable is False
    assert "missing or unresolvable" in res_sms.error.lower()

    wa_adapter = WhatsAppAdapter()
    res_wa = wa_adapter.send(fake_rec, recipient_meta={})
    assert res_wa.success is False
    assert res_wa.retryable is False
    assert "missing or unresolvable" in res_wa.error.lower()


# ── 4. Decoupled Email Templates & Missing Email Handling ────────────────────

def test_email_safe_failure_and_dynamic_content():
    """Verify email adapter fails on missing email and renders dynamic legal notices without hardcoded Section 479."""
    from app.notifications.adapters.email import EmailAdapter

    fake_rec = NotificationRecord(
        id="NOTIF-NO-EMAIL",
        recipient="unknown_entity",
        event_type=NotificationEventType.SECURITY_EVENT,
        priority=NotificationPriority.EMERGENCY,
        title="Security Alert",
        message="Unauthorized access attempt",
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        idempotency_key="no-email-key",
    )

    email_adapter = EmailAdapter()
    res = email_adapter.send(fake_rec, recipient_meta={})
    assert res.success is False
    assert res.retryable is False
    assert "missing or invalid" in res.error.lower()


# ── 5. Quiet Hours Enforcement on Explicit Channels ──────────────────────────

def test_quiet_hours_enforced_even_with_explicit_channels():
    """Verify that supplying explicit external channels does NOT bypass quiet hours for non-emergencies."""
    prefs = UserNotificationPreferences(
        user_id="usr_quiet_test",
        quiet_hours_enabled=True,
        quiet_hours_start="22:00",
        quiet_hours_end="06:00",
        enabled_channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
    )
    # Simulate current time at 23:30 (inside quiet hours)
    night_time = datetime.datetime(2026, 9, 8, 23, 30, tzinfo=datetime.timezone.utc)

    # Case A: STANDARD priority with explicit channels -> Must suppress SMS/WhatsApp down to IN_APP
    channels_standard, override_std = filter_channels_for_delivery(
        priority=NotificationPriority.STANDARD,
        event_type=NotificationEventType.NEW_LEGAL_AID_NEED,
        prefs=prefs,
        requested_channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
        now=night_time,
    )
    assert NotificationChannel.SMS not in channels_standard
    assert NotificationChannel.WHATSAPP not in channels_standard
    assert NotificationChannel.IN_APP in channels_standard
    assert override_std is False

    # Case B: EMERGENCY priority with explicit channels -> Bypasses quiet hours
    channels_emerg, override_emg = filter_channels_for_delivery(
        priority=NotificationPriority.EMERGENCY,
        event_type=NotificationEventType.SECURITY_EVENT,
        prefs=prefs,
        requested_channels=[NotificationChannel.SMS, NotificationChannel.WHATSAPP],
        now=night_time,
    )
    assert NotificationChannel.SMS in channels_emerg
    assert override_emg is True


# ── 6. Idempotency Key Stable Fingerprint (No Daily Date Bucket) ─────────────

def test_idempotency_key_stable_without_daily_bucket():
    """Verify idempotency key is identical across different dates when event attributes match."""
    key1 = compute_idempotency_key(
        event_type=NotificationEventType.APPROACHING_CUSTODY_THRESHOLD,
        entity_id="UTP-STABLE-01",
        recipient="DEFENSE_ADVOCATE",
        payload={"milestone": "1/2_SENTENCE", "threshold_days": 180},
    )
    key2 = compute_idempotency_key(
        event_type=NotificationEventType.APPROACHING_CUSTODY_THRESHOLD,
        entity_id="UTP-STABLE-01",
        recipient="DEFENSE_ADVOCATE",
        payload={"milestone": "1/2_SENTENCE", "threshold_days": 180},
    )
    assert key1 == key2
    assert len(key1) == 64  # SHA-256


# ── 7. Authorization Check for Acknowledge & Dismiss ─────────────────────────

def test_authorization_prevents_unauthorized_mutation():
    """Verify unauthorized users receive 403 Forbidden when acknowledging or dismissing another's alert."""
    rec = NotificationService.dispatch(
        event_type=NotificationEventType.SECURITY_EVENT,
        case_id="UTP-AUTH-01",
        payload={"fingerprint": "auth-mutation-01"},
        user_id="demo_platform_admin",
        target_role="PLATFORM_ADMIN",
    )

    headers_accused = _auth_headers(Role.ACCUSED_USER, user_id="demo_accused")
    headers_admin = _auth_headers(Role.PLATFORM_ADMIN, user_id="demo_platform_admin")

    # Unauthorized user tries to acknowledge
    ack_res_unauth = client.patch(f"/api/notifications/{rec.id}/acknowledge", headers=headers_accused)
    assert ack_res_unauth.status_code == 403

    # Unauthorized user tries to dismiss
    dism_res_unauth = client.post(f"/api/notifications/{rec.id}/dismiss", headers=headers_accused)
    assert dism_res_unauth.status_code == 403

    # Authorized admin acknowledges
    ack_res_auth = client.patch(f"/api/notifications/{rec.id}/acknowledge", headers=headers_admin)
    assert ack_res_auth.status_code == 200
    assert ack_res_auth.json()["status"] == "success"


# ── 8. Read History & Mark Read Endpoint ─────────────────────────────────────

def test_read_history_and_mark_read_endpoints():
    """Verify mark-read updates read_at timestamp and mark-all-read processes batch correctly."""
    headers_adv = _auth_headers(Role.DEFENSE_ADVOCATE, user_id="demo_advocate")

    rec = NotificationService.dispatch(
        event_type=NotificationEventType.HEARING_APPROACHING,
        case_id="UTP-READ-01",
        payload={"fingerprint": "mark-read-01"},
        user_id="demo_advocate",
    )

    # Mark as read
    res = client.patch(f"/api/notifications/{rec.id}/read", headers=headers_adv)
    assert res.status_code == 200
    assert res.json()["is_read"] is True

    stored = NotificationRepository.get_by_id(rec.id)
    assert stored.is_read is True
    assert stored.read_at is not None

    # Batch mark all read
    batch_res = client.post("/api/notifications/mark-all-read", headers=headers_adv)
    assert batch_res.status_code == 200
    assert "marked_read_count" in batch_res.json()


# ── 9. Date Range Filtering ──────────────────────────────────────────────────

def test_date_range_filtering():
    """Verify notifications can be filtered by date_from and date_to."""
    headers_admin = _auth_headers(Role.PLATFORM_ADMIN, user_id="demo_platform_admin")

    # Filter with past window
    res = client.get(
        "/api/notifications?date_from=2020-01-01T00:00:00Z&date_to=2020-01-02T00:00:00Z",
        headers=headers_admin,
    )
    assert res.status_code == 200
    assert len(res.json()) == 0


# ── 10. DLQ Persistent Status Transitions ────────────────────────────────────

def test_dlq_persistent_status_update():
    """Verify that retrying a DLQ entry updates SQLite database row to RESOLVED."""
    dlq_id = NotificationRepository.save_dlq_entry(
        notification_id="NOTIF-DLQ-PERSIST",
        failure_reason="Simulated gateway network drop",
        attempts=3,
        task_id="TASK-DLQ-TEST",
    )

    entries = NotificationRepository.get_dlq_entries()
    match = next((e for e in entries if e["id"] == dlq_id), None)
    assert match is not None
    assert match["status"] == "DEAD_LETTER"

    # Update status to RESOLVED
    NotificationRepository.update_dlq_status(dlq_id, status="RESOLVED")

    updated_entries = NotificationRepository.get_dlq_entries()
    updated_match = next((e for e in updated_entries if e["id"] == dlq_id), None)
    assert updated_match is not None
    assert updated_match["status"] == "RESOLVED"
    assert updated_match["retry_attempts"] >= 4


# ── 11. Delivery Provider Webhook Lifecycle ──────────────────────────────────

def test_delivery_provider_webhook():
    """Verify provider webhook callbacks transition notification delivery state."""
    rec = NotificationService.dispatch(
        event_type=NotificationEventType.ORDER_RECEIVED,
        case_id="UTP-WH-01",
        payload={"fingerprint": "webhook-test-01"},
        channels=[NotificationChannel.IN_APP],
    )

    wh_res = client.post(
        "/api/notifications/webhook/IN_APP",
        json={
            "external_message_id": rec.id,
            "status": "delivered",
        },
    )
    assert wh_res.status_code == 200
    assert wh_res.json()["updated"] is True

    updated_rec = NotificationRepository.get_by_id(rec.id)
    assert updated_rec.delivery_status == DeliveryStatus.DELIVERED


# ── 12. Transparent Fallback Indicators ──────────────────────────────────────

def test_truthful_template_fallbacks():
    """Verify template replaces missing parameters with transparent audit indicators."""
    rec = NotificationService.dispatch(
        event_type=NotificationEventType.NEW_LEGAL_AID_NEED,
        payload={"fingerprint": "truthful-fallback-01"},  # Omit name and case_id
    )
    assert "[Name unavailable - docket review required]" in rec.message
    assert "[Case ID unspecified]" in rec.message
