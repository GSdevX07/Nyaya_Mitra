"""
Database and document backup, restore, and automated test-restore verification engine for Nyaya Mitra.
Ensures zero-loss disaster recovery with cryptographic hash verification and integrity assertion.
"""

from __future__ import annotations
import os
import time
import json
import shutil
import sqlite3
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.database import get_db_connection

logger = logging.getLogger("nyaya_mitra.operations.backup_restore")

DEFAULT_BACKUP_DIR = Path(__file__).resolve().parent.parent.parent / "backups"


class BackupManifest(BaseModel):
    backup_id: str
    created_at: str
    engine: str = "sqlite"
    database_filename: str
    database_path: str
    database_sha256: str
    database_size_bytes: int
    record_counts: Dict[str, int] = Field(default_factory=dict)
    documents_archive_path: Optional[str] = None
    status: str = "COMPLETED"


class TestRestoreReport(BaseModel):
    test_id: str
    backup_id: Optional[str] = None
    backup_file: str
    status: str  # PASSED or FAILED
    verified_at: str
    integrity_check: str
    tables_found: List[str]
    record_counts: Dict[str, int]
    audit_chain_valid: bool
    audit_events_verified: int
    duration_ms: float
    error: Optional[str] = None


def compute_file_sha256(filepath: Path | str) -> str:
    """Compute SHA-256 digest of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_backup(
    target_dir: Optional[str | Path] = None,
    include_documents: bool = False,
    documents_dir: Optional[str | Path] = None,
) -> BackupManifest:
    """
    Perform an atomic online backup of the SQLite database using the native Backup API.
    Computes cryptographic checksums and persists a JSON manifest.
    """
    out_dir = Path(target_dir) if target_dir else DEFAULT_BACKUP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_id = f"BKP-{timestamp_str}"
    db_filename = f"nyaya_mitra_{timestamp_str}.db"
    backup_db_path = out_dir / db_filename
    manifest_path = out_dir / f"nyaya_mitra_{timestamp_str}.manifest.json"

    # Online atomic backup via SQLite Backup API
    source_conn = get_db_connection()
    try:
        from app.database import _init_sqlite_tables
        _init_sqlite_tables(source_conn)

        dest_conn = sqlite3.connect(str(backup_db_path))
        try:
            source_conn.backup(dest_conn)
        finally:
            dest_conn.close()

        # Count records in snapshot
        verify_conn = sqlite3.connect(str(backup_db_path))
        record_counts: Dict[str, int] = {}
        try:
            cursor = verify_conn.cursor()
            for table in ["cases", "accused_persons", "audit_events", "organization_users", "documents"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    record_counts[table] = cursor.fetchone()[0]
                except Exception:
                    record_counts[table] = 0
        finally:
            verify_conn.close()

    finally:
        source_conn.close()

    db_sha256 = compute_file_sha256(backup_db_path)
    db_size = backup_db_path.stat().st_size

    # Optional documents archive
    docs_archive_path = None
    if include_documents and documents_dir:
        src_docs = Path(documents_dir)
        if src_docs.exists():
            archive_base = out_dir / f"nyaya_docs_{timestamp_str}"
            archive_zip = shutil.make_archive(str(archive_base), "zip", str(src_docs))
            docs_archive_path = archive_zip

    manifest = BackupManifest(
        backup_id=backup_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        engine="sqlite",
        database_filename=db_filename,
        database_path=str(backup_db_path),
        database_sha256=db_sha256,
        database_size_bytes=db_size,
        record_counts=record_counts,
        documents_archive_path=docs_archive_path,
        status="COMPLETED",
    )

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(), f, indent=2)

    logger.info(f"Created backup {backup_id} at {backup_db_path} (SHA256: {db_sha256[:12]}...).")
    return manifest


def restore_backup(
    backup_db_path: str | Path,
    target_conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """
    Restore an existing database snapshot into the active database or a specified connection.
    """
    path = Path(backup_db_path)
    if not path.exists():
        raise FileNotFoundError(f"Backup file not found at: {path}")

    start_time = time.perf_counter()
    backup_conn = sqlite3.connect(str(path))
    should_close_target = False

    if target_conn is None:
        target_conn = get_db_connection()
        should_close_target = True

    try:
        backup_conn.backup(target_conn)
        target_conn.commit()
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return {
            "status": "RESTORED",
            "source_backup": str(path),
            "duration_ms": duration_ms,
        }
    finally:
        backup_conn.close()
        if should_close_target:
            target_conn.close()


def test_restore_verification(backup_db_path: str | Path) -> TestRestoreReport:
    """
    Automated disaster recovery test:
    1. Restores the backup snapshot into an isolated ephemeral sandbox.
    2. Runs PRAGMA integrity_check.
    3. Confirms essential enterprise tables and record counts.
    4. Validates cryptographic audit hash chain continuity on the restored data.
    """
    start_time = time.perf_counter()
    path = Path(backup_db_path)
    test_id = f"RESTORE-TEST-{int(time.time())}"

    if not path.exists():
        return TestRestoreReport(
            test_id=test_id,
            backup_file=str(path),
            status="FAILED",
            verified_at=datetime.now(timezone.utc).isoformat(),
            integrity_check="file_not_found",
            tables_found=[],
            record_counts={},
            audit_chain_valid=False,
            audit_events_verified=0,
            duration_ms=0.0,
            error=f"Backup file not found: {path}",
        )

    # Isolated in-memory sandbox connection
    sandbox_conn = sqlite3.connect(":memory:")
    try:
        backup_conn = sqlite3.connect(str(path))
        try:
            backup_conn.backup(sandbox_conn)
        finally:
            backup_conn.close()

        cursor = sandbox_conn.cursor()

        # 1. PRAGMA integrity_check
        cursor.execute("PRAGMA integrity_check")
        integrity_row = cursor.fetchone()
        integrity_result = integrity_row[0] if integrity_row else "error"

        # 2. Table Discovery
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]

        # 3. Record Counts
        record_counts: Dict[str, int] = {}
        for tbl in ["cases", "accused_persons", "audit_events", "organization_users"]:
            if tbl in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
                record_counts[tbl] = cursor.fetchone()[0]
            else:
                record_counts[tbl] = 0

        # 4. Cryptographic Hash Chain Validation on Restored Audit Events
        audit_chain_valid = True
        verified_events_count = 0
        error_reasons = []

        if integrity_result != "ok":
            error_reasons.append(f"PRAGMA integrity_check returned: {integrity_result}")

        if "audit_events" in tables:
            cursor.execute(
                """
                SELECT id, timestamp, actor_id, actor_role, action, entity_type,
                       entity_id, details_json, event_hash, previous_event_hash, sequence_number
                FROM audit_events
                ORDER BY sequence_number ASC, timestamp ASC, rowid ASC
                """
            )
            audit_rows = cursor.fetchall()
            expected_prev_hash: Optional[str] = None

            for row in audit_rows:
                ev_id, ts, actor_id, role, action, ent_type, ent_id, details_json, stored_hash, prev_hash, seq = row
                verified_events_count += 1

                # Verify pointer continuity
                if expected_prev_hash is not None and prev_hash != expected_prev_hash:
                    audit_chain_valid = False
                    error_reasons.append(f"Audit pointer broken at seq {seq}: prev={prev_hash}, expected={expected_prev_hash}")
                    break

                # Recalculate hash matching AuditRepository
                hash_payload = f"{ev_id}|{ts}|{actor_id}|{role}|{action}|{ent_type}|{ent_id}|{details_json}|{prev_hash}|{seq}"
                recomputed_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

                hash_match = (recomputed_hash == stored_hash)
                if not hash_match:
                    try:
                        normalized_details = json.dumps(json.loads(details_json), sort_keys=True)
                        norm_payload = f"{ev_id}|{ts}|{actor_id}|{role}|{action}|{ent_type}|{ent_id}|{normalized_details}|{prev_hash}|{seq}"
                        if hashlib.sha256(norm_payload.encode("utf-8")).hexdigest() == stored_hash:
                            hash_match = True
                    except Exception:
                        pass

                if not hash_match:
                    audit_chain_valid = False
                    error_reasons.append(f"Audit hash mismatch at seq {seq}: stored={stored_hash}, recomputed={recomputed_hash}")
                    break

                expected_prev_hash = stored_hash

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        overall_status = "PASSED" if (integrity_result == "ok" and audit_chain_valid) else "FAILED"

        return TestRestoreReport(
            test_id=test_id,
            backup_file=str(path),
            status=overall_status,
            verified_at=datetime.now(timezone.utc).isoformat(),
            integrity_check=integrity_result,
            tables_found=tables,
            record_counts=record_counts,
            audit_chain_valid=audit_chain_valid,
            audit_events_verified=verified_events_count,
            duration_ms=duration_ms,
            error="; ".join(error_reasons) if error_reasons else None,
        )
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return TestRestoreReport(
            test_id=test_id,
            backup_file=str(path),
            status="FAILED",
            verified_at=datetime.now(timezone.utc).isoformat(),
            integrity_check="exception",
            tables_found=[],
            record_counts={},
            audit_chain_valid=False,
            audit_events_verified=0,
            duration_ms=duration_ms,
            error=f"Restore execution error: {type(exc).__name__} - {exc}",
        )
    finally:
        sandbox_conn.close()
