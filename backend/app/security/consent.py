"""
consent.py - Privacy Notice and Consent Management for Nyaya Mitra Accused and Family Workflows.

Provides plain-language multi-lingual privacy notices, affirmative consent tracking,
and consent withdrawal capabilities with tamper-evident audit logging.
"""

from __future__ import annotations
import sqlite3
import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.models.domain import generate_prefixed_id


PRIVACY_NOTICE_CONTENT: Dict[str, Dict[str, Any]] = {
    "en": {
        "title": "Nyaya Mitra Legal Aid & Remand Assistance Privacy Notice",
        "version": "2026.1",
        "effective_date": "2026-01-01",
        "purposes": [
            "Facilitating free legal aid representation under the Legal Services Authorities Act, 1987.",
            "Tracking statutory detention thresholds under Section 479 Bharatiya Nagarik Suraksha Sanhita (BNSS) / 436A CrPC.",
            "Coordinating bail documentation between prison superintendents, DLSA officers, and assigned legal counsel.",
            "Providing case status updates to authorized family members upon affirmative request.",
        ],
        "data_collected": [
            "Demographic identification: Name, age, gender, relative's name, residential district.",
            "Case reference metadata: Police station, FIR number, court docket number, penal sections invoked.",
            "Custody timeline: Incarceration start date, remand extension dates, transfer history.",
            "Special vulnerability tags: Medical conditions or physical infirmity relevant to humanitarian bail or prison medical care.",
        ],
        "access_boundaries": [
            "Assigned Legal Aid Advocates: Case dossier, draft petitions, and client interview notes.",
            "District Legal Services Authority (DLSA) Officers: Entitlement audits and legal counsel assignment.",
            "Jail Superintendents: Custody verification and release order processing.",
            "Judicial Auditors: Read-only anonymized procedural compliance review.",
        ],
        "citizen_rights": [
            "Right to know your assigned legal aid counsel and contact information.",
            "Right to request correction of inaccurate dates or misspelled identifiers.",
            "Right to withdraw optional notification consent without affecting your constitutional entitlement to legal aid.",
        ],
    },
    "hi": {
        "title": "न्याय मित्र विधिक सहायता एवं अभिरक्षा सहायता गोपनीयता सूचना",
        "version": "2026.1",
        "effective_date": "2026-01-01",
        "purposes": [
            "विधिक सेवा प्राधिकरण अधिनियम, 1987 के अंतर्गत नि:शुल्क विधिक सहायता का समन्वय।",
            "बीएनएसएस धारा 479 / दंड प्रक्रिया संहिता धारा 436A के अंतर्गत वैधानिक जमानत पात्रता की गणना।",
            "कारागार अधीक्षक, डीएलएसए विधिक अधिकारी तथा पैनल अधिवक्ता के मध्य समन्वय।",
        ],
        "data_collected": [
            "व्यक्तिगत विवरण: नाम, आयु, लिंग, पिता/अभिभावक का नाम, गृह जनपद।",
            "मुकदमा विवरण: थाना, प्राथमिकी (FIR) संख्या, न्यायालय वाद संख्या, धाराएं।",
            "निरोध अवधि: कारावास आरंभ तिथि, रिमांड आदेश, निरुद्धि अवधि।",
        ],
        "access_boundaries": [
            "नियुक्त पैनल अधिवक्ता, डीएलएसए अधिकारी, एवं कारागार अधीक्षक तक विधिक कार्य हेतु सीमित।",
        ],
        "citizen_rights": [
            "अपने नियुक्त अधिवक्ता की जानकारी प्राप्त करने का अधिकार।",
            "गलत दर्ज तथ्यों में सुधार का अनुरोध करने का अधिकार।",
        ],
    },
}


class ConsentRecord(BaseModel):
    id: str
    citizen_id: str
    consent_type: str
    granted: bool
    version: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    granted_at: str
    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None


def init_consent_table(conn: sqlite3.Connection) -> None:
    """Ensure privacy_consents table exists in the local database."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS privacy_consents (
            id TEXT PRIMARY KEY,
            citizen_id TEXT NOT NULL,
            consent_type TEXT NOT NULL,
            granted INTEGER NOT NULL DEFAULT 1,
            version TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            granted_at TEXT NOT NULL,
            revoked_at TEXT,
            revocation_reason TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_consent_citizen ON privacy_consents(citizen_id, consent_type)")
    conn.commit()


def get_privacy_notice(language: str = "en") -> Dict[str, Any]:
    """Retrieve multi-lingual legal privacy notice text."""
    lang = language.lower()
    if lang not in PRIVACY_NOTICE_CONTENT:
        lang = "en"
    return PRIVACY_NOTICE_CONTENT[lang]


def record_consent(
    conn: sqlite3.Connection,
    citizen_id: str,
    consent_type: str,
    version: str = "2026.1",
    ip_address: str = "127.0.0.1",
    user_agent: str = "",
) -> Dict[str, Any]:
    """Record affirmative privacy consent from an accused or family member."""
    init_consent_table(conn)
    consent_id = generate_prefixed_id("cst")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cur = conn.cursor()
    # Revoke any prior consent of same type first
    cur.execute(
        """
        UPDATE privacy_consents
        SET granted = 0, revoked_at = ?, revocation_reason = 'SUPERSEDED_BY_NEW_CONSENT'
        WHERE citizen_id = ? AND consent_type = ? AND granted = 1
        """,
        (now, citizen_id, consent_type),
    )

    cur.execute(
        """
        INSERT INTO privacy_consents (
            id, citizen_id, consent_type, granted, version, ip_address, user_agent, granted_at
        ) VALUES (?, ?, ?, 1, ?, ?, ?, ?)
        """,
        (consent_id, citizen_id, consent_type, version, ip_address, user_agent, now),
    )
    conn.commit()

    # Emit audit event
    try:
        from app.repositories.audit_repository import audit_consent_recorded
        audit_consent_recorded(
            citizen_id=citizen_id,
            consent_type=consent_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        pass

    return {
        "status": "RECORDED",
        "consent_id": consent_id,
        "citizen_id": citizen_id,
        "consent_type": consent_type,
        "version": version,
        "granted_at": now,
    }


def revoke_consent(
    conn: sqlite3.Connection,
    citizen_id: str,
    consent_type: str,
    reason: str = "USER_REQUEST",
    ip_address: str = "127.0.0.1",
    user_agent: str = "",
) -> Dict[str, Any]:
    """Revoke previously granted privacy consent."""
    init_consent_table(conn)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cur = conn.cursor()
    cur.execute(
        """
        UPDATE privacy_consents
        SET granted = 0, revoked_at = ?, revocation_reason = ?
        WHERE citizen_id = ? AND consent_type = ? AND granted = 1
        """,
        (now, reason, citizen_id, consent_type),
    )
    updated_rows = cur.rowcount
    conn.commit()

    try:
        from app.repositories.audit_repository import audit_consent_revoked
        audit_consent_revoked(
            citizen_id=citizen_id,
            consent_type=consent_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        pass

    return {
        "status": "REVOKED",
        "citizen_id": citizen_id,
        "consent_type": consent_type,
        "active_records_revoked": updated_rows,
        "revoked_at": now,
        "reason": reason,
    }


def get_consent_status(
    conn: sqlite3.Connection,
    citizen_id: str,
    consent_type: str = "DATA_PROCESSING",
) -> Dict[str, Any]:
    """Check current consent status for a citizen."""
    init_consent_table(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, granted, version, granted_at, revoked_at, revocation_reason
        FROM privacy_consents
        WHERE citizen_id = ? AND consent_type = ?
        ORDER BY granted_at DESC LIMIT 1
        """,
        (citizen_id, consent_type),
    )
    row = cur.fetchone()
    if not row:
        return {
            "citizen_id": citizen_id,
            "consent_type": consent_type,
            "has_consented": False,
            "consent_id": None,
        }

    return {
        "citizen_id": citizen_id,
        "consent_type": consent_type,
        "has_consented": bool(row[1]),
        "consent_id": row[0],
        "version": row[2],
        "granted_at": row[3],
        "revoked_at": row[4],
        "revocation_reason": row[5],
    }
