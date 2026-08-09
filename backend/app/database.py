"""
database.py — Lightweight SQLite persistence for Nyaya Mitra.

This module provides a persistent state machine for the hackathon demo.
It initializes a SQLite database, creates the necessary schema, and seeds
it with the initial 5 hero cases.
"""

import sqlite3
import json
import hashlib
import datetime
from contextlib import contextmanager
from typing import List

from app.models.schemas import CaseRecord, CaseState

DB_PATH = "nyaya_mitra.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    """Create tables and seed initial mock data if empty."""
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                data JSON NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                stored_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_read INTEGER DEFAULT 0
            )
        ''')
        
        # Check if we need to seed
        cursor = conn.execute("SELECT COUNT(*) as count FROM cases")
        if cursor.fetchone()["count"] == 0:
            _seed_db(conn)

def _seed_db(conn):
    """Seed the database with the 5 hero cases and their mock evidence."""
    from app.main import MOCK_DB  # Import here to avoid circular dependency
    for case in MOCK_DB:
        # Save the full pydantic model as JSON
        conn.execute(
            "INSERT INTO cases (case_id, data) VALUES (?, ?)",
            (case.case_id, case.model_dump_json())
        )
        # Create evidence records for all present docs
        for doc in case.present_docs:
            evidence_id = f"EVI-{case.case_id}-{doc}"
            file_name = f"{doc}.pdf"
            # Simulate the "original" file bytes and compute its hash
            mock_file_bytes = f"mock_file_content_for_{case.case_id}_{doc}".encode()
            stored_hash = hashlib.sha256(mock_file_bytes).hexdigest()
            
            # Intentionally tamper with UTP-0012's remand_order hash to show MISMATCH in UI
            if case.case_id == "UTP-0012" and doc == "remand_order":
                stored_hash = "deadbeef" + stored_hash[8:]
                
            conn.execute(
                "INSERT INTO evidence (evidence_id, case_id, document_type, file_name, stored_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (evidence_id, case.case_id, doc, file_name, stored_hash, datetime.datetime.now(datetime.timezone.utc).isoformat())
            )
            
        # Add a mock notification for UTP-0007 if present
        if case.case_id == "UTP-0007":
            conn.execute(
                "INSERT INTO notifications (id, case_id, title, message, type, timestamp, is_read) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"NOTIF-{case.case_id}-mock", case.case_id, "High Priority Bail Eligibility Flagged", f"{case.case_id} has exceeded the sentence threshold.", "urgent", datetime.datetime.now(datetime.timezone.utc).isoformat(), 0)
            )

def get_all_cases() -> List[CaseRecord]:
    """Retrieve all cases from the database."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT data FROM cases")
        rows = cursor.fetchall()
        return [CaseRecord.model_validate_json(row["data"]) for row in rows]

def get_case(case_id: str) -> CaseRecord | None:
    """Retrieve a single case by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if row:
            return CaseRecord.model_validate_json(row["data"])
    return None

def update_case_status(case_id: str, new_status: CaseState) -> bool:
    """Update the status of a case. Returns True if successful."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            return False
        case_data = json.loads(row["data"])
        case_data["status"] = new_status.value
        conn.execute(
            "UPDATE cases SET data = ? WHERE case_id = ?",
            (json.dumps(case_data), case_id)
        )
        return True

def update_case_documents(case_id: str, present_docs: list) -> bool:
    """
    Persist an updated present_docs list for a case.
    This is required after document upload so the change survives a page reload.
    Returns True if successful.
    """
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            return False
        case_data = json.loads(row["data"])
        case_data["present_docs"] = present_docs
        conn.execute(
            "UPDATE cases SET data = ? WHERE case_id = ?",
            (json.dumps(case_data), case_id)
        )
        return True

def add_evidence(case_id: str, document_type: str, stored_hash: str) -> str:
    """Insert a new evidence record and return the generated evidence_id."""
    evidence_id = f"EVI-{case_id}-{document_type}"
    file_name = f"{document_type}.pdf"
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db_connection() as conn:
        # Use REPLACE INTO in case they re-upload the same document type
        conn.execute(
            "REPLACE INTO evidence (evidence_id, case_id, document_type, file_name, stored_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (evidence_id, case_id, document_type, file_name, stored_hash, created_at)
        )
    return evidence_id

def get_all_evidence() -> List[dict]:
    """Retrieve all evidence records."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM evidence")
        return [dict(row) for row in cursor.fetchall()]

def get_evidence_item(evidence_id: str) -> dict | None:
    """Retrieve a single evidence record by ID."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM evidence WHERE evidence_id = ?", (evidence_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None

def add_notification(case_id: str, title: str, message: str, type: str) -> str:
    """Insert a new notification and return its generated ID."""
    notif_id = f"NOTIF-{case_id}-{datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (id, case_id, title, message, type, timestamp, is_read) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (notif_id, case_id, title, message, type, timestamp, 0)
        )
    return notif_id

def get_all_notifications() -> List[dict]:
    """Retrieve all notifications sorted by newest first."""
    with get_db_connection() as conn:
        cursor = conn.execute("SELECT * FROM notifications ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]
