"""
database.py — Lightweight SQLite persistence for Nyaya Mitra.

This module provides a persistent state machine for the hackathon demo.
It initializes a SQLite database, creates the necessary schema, and seeds
it with the initial 5 hero cases.
"""

import sqlite3
import json
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
        
        # Check if we need to seed
        cursor = conn.execute("SELECT COUNT(*) as count FROM cases")
        if cursor.fetchone()["count"] == 0:
            _seed_db(conn)

def _seed_db(conn):
    """Seed the database with the 5 hero cases."""
    from app.main import MOCK_DB  # Import here to avoid circular dependency
    for case in MOCK_DB:
        # Save the full pydantic model as JSON
        conn.execute(
            "INSERT INTO cases (case_id, data) VALUES (?, ?)",
            (case.case_id, case.model_dump_json())
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
        # First read the case
        cursor = conn.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if not row:
            return False
            
        # Parse, update, and serialize
        case_data = json.loads(row["data"])
        case_data["status"] = new_status.value
        
        # Write back
        conn.execute(
            "UPDATE cases SET data = ? WHERE case_id = ?",
            (json.dumps(case_data), case_id)
        )
        return True
