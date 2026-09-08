"""
ingestion/pipeline.py — Auditable Data Ingestion, Deduplication & Conflict Reconciliation Engine.

Pipeline Stages:
  1. Intake & SHA-256 Payload Hashing
  2. Schema & Production Synthetic Gate
  3. Field Normalization (Dates, Legal Codes, Sections)
  4. Exact & Probabilistic Identity Matching
  5. Conflict Detection & Provenance Preservation (No Silent Overwrite)
     - Conflicting hearing dates
     - Altered CNR / case identifiers
     - Custody duration & arrest date discrepancies
     - Offense section modifications
  6. Canonical Commit & Security Audit Logging
  7. Human Conflict Reconciliation Gateway (Keep Canonical / Adopt Incoming / Manual Override)
"""

from __future__ import annotations
import difflib
import datetime
import json
import re
import sqlite3
import uuid
from typing import Dict, Any, List, Optional, Tuple

from app.ingestion.models import (
    IngestionBatch, RawSourceRecord, IdentityMatchCandidate, MatchConfidence,
    ResolutionStatus, FieldConflict, ConflictSeverity, ConflictStatus,
    DataClassification, ConnectorConfig
)
from app.ingestion.connectors.base import BaseConnector
from app.models.schemas import CaseRecord, PrisonerCategory, LegalCode, CaseState, UrgencyFlags
from app.database import get_all_cases, get_case, get_db_connection
from app.repositories.audit_repository import append_audit_event


# ── In-Memory Cache with DB Backing ───────────────────────────────────────────

_ACTIVE_BATCHES: Dict[str, IngestionBatch] = {}
_PENDING_CONFLICTS: Dict[str, FieldConflict] = {}
_PENDING_IDENTITY_MERGES: Dict[str, IdentityMatchCandidate] = {}


def _calculate_string_similarity(a: str, b: str) -> float:
    """Levenshtein-based ratio for person and relative names."""
    clean_a = "".join(ch for ch in (a or "").lower() if ch.isalnum())
    clean_b = "".join(ch for ch in (b or "").lower() if ch.isalnum())
    if not clean_a or not clean_b:
        return 0.0
    return difflib.SequenceMatcher(None, clean_a, clean_b).ratio()


def _save_conflict_to_db(conf: FieldConflict) -> None:
    """Persist a field conflict to the SQLite integration_conflicts table."""
    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO integration_conflicts (
                id, case_id, accused_id, accused_name, entity_type, field_name,
                canonical_value, canonical_source, canonical_timestamp,
                proposed_value, proposed_source, proposed_timestamp,
                severity, status, resolution_notes, resolved_by, resolved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conf.id, conf.case_id, conf.accused_id, conf.accused_name,
                conf.entity_type, conf.field_name,
                json.dumps(conf.canonical_value) if not isinstance(conf.canonical_value, (str, int, float, bool)) else str(conf.canonical_value),
                conf.canonical_source, conf.canonical_timestamp,
                json.dumps(conf.proposed_value) if not isinstance(conf.proposed_value, (str, int, float, bool)) else str(conf.proposed_value),
                conf.proposed_source, conf.proposed_timestamp,
                conf.severity.value, conf.status.value,
                conf.resolution_notes, conf.resolved_by, conf.resolved_at, conf.created_at,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as err:
        print(f"[WARN] Failed to save conflict to SQLite: {err}")


def _load_conflicts_from_db() -> Dict[str, FieldConflict]:
    """Load pending conflicts from SQLite integration_conflicts table."""
    conflicts_map: Dict[str, FieldConflict] = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM integration_conflicts WHERE status = 'PENDING_REVIEW'")
        rows = cursor.fetchall()
        for r in rows:
            d = dict(r)
            canon_val = d.get("canonical_value")
            prop_val = d.get("proposed_value")
            try:
                canon_val = json.loads(canon_val)
            except Exception:
                pass
            try:
                prop_val = json.loads(prop_val)
            except Exception:
                pass

            conf = FieldConflict(
                id=d["id"],
                case_id=d["case_id"],
                accused_id=d["accused_id"],
                accused_name=d.get("accused_name") or "Undertrial",
                entity_type=d.get("entity_type") or "CASE",
                field_name=d["field_name"],
                canonical_value=canon_val,
                canonical_source=d.get("canonical_source") or "CANONICAL",
                canonical_timestamp=d.get("canonical_timestamp") or "",
                proposed_value=prop_val,
                proposed_source=d.get("proposed_source") or "EXTERNAL_FEED",
                proposed_timestamp=d.get("proposed_timestamp") or "",
                severity=ConflictSeverity(d.get("severity") or "MEDIUM"),
                status=ConflictStatus(d.get("status") or "PENDING_REVIEW"),
                resolution_notes=d.get("resolution_notes"),
                resolved_by=d.get("resolved_by"),
                resolved_at=d.get("resolved_at"),
                created_at=d.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
            conflicts_map[conf.id] = conf
        conn.close()
    except Exception:
        pass
    return conflicts_map


# Preload pending conflicts from database
_PENDING_CONFLICTS.update(_load_conflicts_from_db())


class IngestionPipeline:
    def __init__(self):
        pass

    def match_existing_identity(
        self,
        incoming_record: Dict[str, Any],
        existing_cases: List[CaseRecord],
    ) -> Tuple[Optional[CaseRecord], MatchConfidence, float, List[str]]:
        """
        Evaluate deterministic and probabilistic match candidate for incoming record.
        """
        incoming_case_id = str(incoming_record.get("case_id") or "").strip().upper()
        incoming_name = (
            incoming_record.get("full_name") or
            incoming_record.get("name") or
            incoming_record.get("respondent_accused") or
            incoming_record.get("accused_name") or
            ""
        ).strip().lower()
        incoming_cnr = incoming_record.get("cnr_number", "").strip().upper()
        incoming_fir = incoming_record.get("fir_number", "").strip().upper()
        incoming_age = int(incoming_record.get("age") or 30)
        incoming_station = incoming_record.get("police_station", "").strip().lower()
        incoming_relative = incoming_record.get("relative_name", "").strip().lower()

        clean_inc_cnr = "".join(ch for ch in incoming_cnr if ch.isalnum())
        clean_inc_fir = "".join(ch for ch in incoming_fir if ch.isalnum())
        clean_inc_name = re.sub(r"\(.*?\)", "", incoming_name).strip()

        best_case = None
        best_confidence = MatchConfidence.NEW_ENTITY
        best_score = 0.0
        reasons = []

        for case in existing_cases:
            case_name = case.name.strip().lower()
            case_fir = (case.fir_number or "").strip().upper()
            case_cnr = (case.cnr_number or "").strip().upper()
            case_station = (case.police_station or "").strip().lower()
            case_relative = (case.relative_name or "").strip().lower()
            case_age = case.urgency_flags.age

            clean_case_cnr = "".join(ch for ch in case_cnr if ch.isalnum())
            clean_case_fir = "".join(ch for ch in case_fir if ch.isalnum())
            clean_case_name = re.sub(r"\(.*?\)", "", case_name).strip()

            # 0. Direct Case ID Match
            if incoming_case_id and case.case_id.upper() == incoming_case_id:
                return case, MatchConfidence.CERTAIN, 1.0, [f"Exact Case ID Match ({incoming_case_id})"]

            # 1. Exact deterministic match on Official Identifiers (CNR / FIR)
            if clean_inc_cnr and clean_case_cnr and clean_inc_cnr == clean_case_cnr:
                return case, MatchConfidence.CERTAIN, 1.0, [f"Exact CNR Docket Match ({incoming_cnr})"]

            if clean_inc_fir and clean_case_fir and clean_inc_fir == clean_case_fir:
                return case, MatchConfidence.CERTAIN, 0.98, [f"Exact FIR Match ({incoming_fir})"]

            # 2. Probabilistic Matching on composite attributes
            name_sim = _calculate_string_similarity(clean_inc_name, clean_case_name)
            if name_sim < 0.65:
                continue

            score = name_sim * 0.50
            match_points = [f"Name Similarity: {int(name_sim * 100)}%"]

            # Age window check (+/- 3 years)
            if abs(incoming_age - case_age) <= 3:
                score += 0.20
                match_points.append(f"Age Window Proximity ({incoming_age} vs {case_age})")

            # Police Station / Location
            if incoming_station and case_station and (incoming_station in case_station or case_station in incoming_station):
                score += 0.15
                match_points.append(f"Police Station Jurisdiction Match ({case.police_station})")

            # Relative / Father Name
            if incoming_relative and case_relative:
                rel_sim = _calculate_string_similarity(incoming_relative, case_relative)
                if rel_sim >= 0.70:
                    score += 0.15
                    match_points.append(f"Relative / Guardian Match ({case.relative_name})")

            if score > best_score:
                best_score = score
                best_case = case
                reasons = match_points
                best_case = case
                reasons = match_points

        # Classify Confidence Band
        if best_score >= 0.95:
            best_confidence = MatchConfidence.CERTAIN
        elif best_score >= 0.75:
            best_confidence = MatchConfidence.PROBABLE
        elif best_score >= 0.60:
            best_confidence = MatchConfidence.UNCERTAIN
        else:
            best_confidence = MatchConfidence.NEW_ENTITY

        return best_case, best_confidence, round(best_score, 2), reasons

    def detect_field_conflicts(
        self,
        existing_case: CaseRecord,
        incoming: Dict[str, Any],
        source_name: str,
    ) -> List[FieldConflict]:
        """
        Compare incoming observation with existing trusted canonical record.
        Flags material conflicts across:
          - Hearing dates (e-Courts vs local schedule)
          - Changed case identifiers / CNR dockets
          - Arrest dates (crucial for Section 479 calculation)
          - Custody days differences (> 15 days)
          - Offense sections
        Never silently overwrites canonical records.
        """
        conflicts = []
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # 1. Arrest Date discrepancy (Critical legal impact on Section 479 eligibility)
        if incoming.get("arrest_date") and existing_case.arrest_date:
            if incoming["arrest_date"] != existing_case.arrest_date:
                conf = FieldConflict(
                    case_id=existing_case.case_id,
                    accused_id=existing_case.case_id,
                    accused_name=existing_case.name,
                    entity_type="CASE",
                    field_name="arrest_date",
                    canonical_value=existing_case.arrest_date,
                    canonical_source=existing_case.data_source_status.value,
                    canonical_timestamp=existing_case.arrest_date,
                    proposed_value=incoming["arrest_date"],
                    proposed_source=source_name,
                    proposed_timestamp=now_str,
                    severity=ConflictSeverity.CRITICAL,
                    status=ConflictStatus.PENDING_REVIEW,
                )
                conflicts.append(conf)
                _PENDING_CONFLICTS[conf.id] = conf
                _save_conflict_to_db(conf)

        # 2. Custody Days mismatch
        if incoming.get("custody_days") is not None and existing_case.custody_days:
            diff = abs(int(incoming["custody_days"]) - existing_case.custody_days)
            if diff > 15:
                conf = FieldConflict(
                    case_id=existing_case.case_id,
                    accused_id=existing_case.case_id,
                    accused_name=existing_case.name,
                    entity_type="CUSTODY",
                    field_name="custody_days",
                    canonical_value=existing_case.custody_days,
                    canonical_source=existing_case.data_source_status.value,
                    canonical_timestamp=now_str,
                    proposed_value=int(incoming["custody_days"]),
                    proposed_source=source_name,
                    proposed_timestamp=now_str,
                    severity=ConflictSeverity.CRITICAL,
                    status=ConflictStatus.PENDING_REVIEW,
                )
                conflicts.append(conf)
                _PENDING_CONFLICTS[conf.id] = conf
                _save_conflict_to_db(conf)

        # 3. Conflicting Hearing Dates (e-Courts vs Police vs Jail)
        incoming_hearing = incoming.get("next_hearing_date") or incoming.get("hearing_date")
        if incoming_hearing:
            # Check if canonical case has existing scheduled hearings in SQLite
            canon_hearing = self._get_latest_hearing_date(existing_case.case_id)
            if canon_hearing and canon_hearing != incoming_hearing:
                conf = FieldConflict(
                    case_id=existing_case.case_id,
                    accused_id=existing_case.case_id,
                    accused_name=existing_case.name,
                    entity_type="HEARING",
                    field_name="hearing_date",
                    canonical_value=canon_hearing,
                    canonical_source="LOCAL_COURT_CALENDAR",
                    canonical_timestamp=now_str,
                    proposed_value=incoming_hearing,
                    proposed_source=source_name,
                    proposed_timestamp=now_str,
                    severity=ConflictSeverity.CRITICAL,
                    status=ConflictStatus.PENDING_REVIEW,
                )
                conflicts.append(conf)
                _PENDING_CONFLICTS[conf.id] = conf
                _save_conflict_to_db(conf)

        # 4. Changed Case Identifiers / CNR Mismatch
        incoming_cnr = incoming.get("cnr_number")
        if incoming_cnr and existing_case.cnr_number and incoming_cnr.strip().upper() != existing_case.cnr_number.strip().upper():
            conf = FieldConflict(
                case_id=existing_case.case_id,
                accused_id=existing_case.case_id,
                accused_name=existing_case.name,
                entity_type="CASE_IDENTIFIER",
                field_name="cnr_number",
                canonical_value=existing_case.cnr_number,
                canonical_source="CANONICAL_COURT_DOCKET",
                canonical_timestamp=now_str,
                proposed_value=incoming_cnr,
                proposed_source=source_name,
                proposed_timestamp=now_str,
                severity=ConflictSeverity.CRITICAL,
                status=ConflictStatus.PENDING_REVIEW,
            )
            conflicts.append(conf)
            _PENDING_CONFLICTS[conf.id] = conf
            _save_conflict_to_db(conf)

        # 5. Offense sections mismatch
        if incoming.get("offense_sections") and existing_case.offense_sections:
            inc_set = set(incoming["offense_sections"])
            canon_set = set(existing_case.offense_sections)
            if inc_set != canon_set:
                conf = FieldConflict(
                    case_id=existing_case.case_id,
                    accused_id=existing_case.case_id,
                    accused_name=existing_case.name,
                    entity_type="LEGAL_CHARGES",
                    field_name="offense_sections",
                    canonical_value=existing_case.offense_sections,
                    canonical_source=existing_case.data_source_status.value,
                    canonical_timestamp=now_str,
                    proposed_value=incoming["offense_sections"],
                    proposed_source=source_name,
                    proposed_timestamp=now_str,
                    severity=ConflictSeverity.MEDIUM,
                    status=ConflictStatus.PENDING_REVIEW,
                )
                conflicts.append(conf)
                _PENDING_CONFLICTS[conf.id] = conf
                _save_conflict_to_db(conf)

        return conflicts

    def _get_latest_hearing_date(self, case_id: str) -> Optional[str]:
        """Fetch the latest scheduled hearing date from SQLite hearings_schedule."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT hearing_date FROM hearings_schedule WHERE case_id = ? ORDER BY hearing_date DESC LIMIT 1",
                (case_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row and row["hearing_date"]:
                return row["hearing_date"]
        except Exception:
            pass
        return None

    def ingest_record_batch(
        self,
        connector: BaseConnector,
        records: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
    ) -> IngestionBatch:
        """
        Run the complete non-destructive ingestion pipeline for a batch of raw records.
        """
        source_name = connector.get_source_name()
        batch = IngestionBatch(
            id=batch_id or f"batch_{connector.config.id}_{datetime.datetime.now().strftime('%m%d%H%M%S')}",
            connector_id=connector.config.id,
            source_name=source_name,
            total_records=len(records),
        )

        existing_cases = get_all_cases()

        for raw_item in records:
            # 1. Validation & normalization
            val_res = connector.validate_and_normalize(raw_item)
            if not val_res.is_valid:
                batch.invalid_records += 1
                connector.config.validation_failures += 1
                connector.record_raw_ingestion(
                    batch_id=batch.id,
                    external_record_id=str(raw_item.get("cnr_number") or raw_item.get("fir_number") or raw_item.get("inmate_number") or "UNKNOWN"),
                    raw_payload=raw_item,
                    normalized_payload=None,
                    status="REJECTED",
                    error_message="; ".join(val_res.errors),
                )
                continue

            norm = val_res.normalized_data
            batch.valid_records += 1

            # Persist immutable raw record
            ext_rec_id = str(norm.get("cnr_number") or norm.get("fir_number") or norm.get("inmate_number") or "REC")
            connector.record_raw_ingestion(
                batch_id=batch.id,
                external_record_id=ext_rec_id,
                raw_payload=raw_item,
                normalized_payload=norm,
                source_version=val_res.source_version,
                source_timestamp=val_res.source_timestamp,
                status="INGESTED",
            )

            # 2. Identity Resolution & Deduplication
            matched_case, confidence, score, reasons = self.match_existing_identity(norm, existing_cases)

            if matched_case and confidence == MatchConfidence.CERTAIN:
                # Safe Auto-Link / Update with conflict detection (non-destructive)
                conflicts = self.detect_field_conflicts(matched_case, norm, source_name)
                if conflicts:
                    batch.conflicts_detected += len(conflicts)
                    connector.config.conflicts_count += len(conflicts)
                connector.config.duplicates_detected += 1

            elif matched_case and confidence in (MatchConfidence.PROBABLE, MatchConfidence.UNCERTAIN):
                # Ambiguous Identity Match -> Review Queue
                candidate = IdentityMatchCandidate(
                    incoming_raw_id=f"raw_{norm.get('full_name')}",
                    candidate_accused_id=matched_case.case_id,
                    candidate_name=matched_case.name,
                    incoming_name=norm.get("full_name", ""),
                    similarity_score=score,
                    confidence=confidence,
                    match_reasons=reasons,
                    status=ResolutionStatus.PENDING_REVIEW,
                )
                _PENDING_IDENTITY_MERGES[candidate.id] = candidate
                batch.conflicts_detected += 1
                connector.config.conflicts_count += 1

            else:
                # Create Brand-New Accused Case Record
                name_val = norm.get("full_name") or norm.get("name") or norm.get("respondent_accused") or norm.get("accused_name") or "Unknown Undertrial"
                new_case_id = f"UTP-{abs(hash(name_val + str(norm.get('arrest_date')))) % 9000 + 1000}"
                fir_val = norm.get("fir_number")
                cust_val = int(norm.get("custody_days") or 180)
                computed_present = list(norm.get("present_docs") or [])
                if not computed_present:
                    if fir_val or norm.get("police_station"):
                        computed_present.append("fir_copy")
                    if cust_val > 0 or norm.get("arrest_date"):
                        computed_present.append("remand_order")
                new_case = CaseRecord(
                    case_id=new_case_id,
                    name=name_val,
                    prisoner_category=PrisonerCategory.UNDERTRIAL,
                    legal_code=LegalCode(norm.get("legal_code", "BNS_2023")),
                    offense_sections=norm.get("offense_sections", ["BNS 303(2)"]),
                    cnr_number=norm.get("cnr_number") or f"DLCT01-{new_case_id}-2025",
                    fir_number=fir_val or f"FIR-2025-{new_case_id}",
                    police_station=norm.get("police_station") or "Kotwali PS",
                    court_name=norm.get("court_name") or "Chief Judicial Magistrate Court",
                    district=norm.get("district") or "Central Delhi",
                    state=norm.get("state") or "Delhi",
                    arrest_date=norm.get("arrest_date") or datetime.date.today().isoformat(),
                    custody_days=cust_val,
                    excluded_delay_days=0,
                    max_sentence_days_for_offense=int(norm.get("max_sentence_days_for_offense") or 730),
                    punishable_by_death_or_life=bool(norm.get("punishable_by_death_or_life", False)),
                    multiple_active_cases=bool(norm.get("multiple_active_cases", False)),
                    prior_bail_orders=[],
                    required_docs=norm.get("required_docs") or ["fir_copy", "remand_order", "charge_sheet"],
                    present_docs=computed_present,
                    urgency_flags=UrgencyFlags(
                        age=int(norm.get("age") or 30),
                        health_flag=bool(norm.get("health_flag", False)),
                        health_details=norm.get("health_details"),
                        repeat_offender=False,
                    ),
                    jail_location=norm.get("jail_location") or "District Central Jail",
                    preferred_language=norm.get("preferred_language") or "en",
                    relative_name=norm.get("relative_name"),
                    relative_phone=norm.get("relative_phone"),
                    assignment_status="AVAILABLE",
                    status=CaseState.LEGAL_AID_REQUIRED,
                )

                # Persist to SQLite
                self._persist_case(new_case)
                existing_cases.append(new_case)

        connector.config.records_received += batch.total_records
        connector.config.records_processed += batch.valid_records
        connector.config.records_rejected += batch.invalid_records
        connector.config.last_successful_sync = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Calculate next sync timestamp based on sync interval
        interval_mins = connector.config.sync_interval_minutes or 60
        next_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=interval_mins)
        connector.config.next_sync_at = next_dt.isoformat()

        _ACTIVE_BATCHES[batch.id] = batch
        self._update_connector_db(connector)

        # Append audit event
        append_audit_event({
            "action": "CREATE",
            "entity_type": "ingestion_batch",
            "entity_id": batch.id,
            "actor_id": connector.config.id,
            "actor_role": "INGESTION_CONNECTOR",
            "details": {
                "source": source_name,
                "total": batch.total_records,
                "valid": batch.valid_records,
                "conflicts": batch.conflicts_detected,
            },
        })

        return batch

    def _persist_case(self, case: CaseRecord) -> None:
        """Write newly discovered ingested case to database and synchronize document inventory."""
        try:
            conn = get_db_connection()
            conn.execute(
                """
                INSERT OR REPLACE INTO cases (
                    case_id, data, status, assignment_status, assigned_lawyer_id
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    case.case_id,
                    json.dumps(case.model_dump()),
                    case.status.value,
                    case.assignment_status,
                    case.assigned_lawyer_id,
                ),
            )
            from app.database import sync_case_documents_and_evidence
            sync_case_documents_and_evidence(conn, case.case_id)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[WARN] Failed to insert newly ingested case into SQLite: {e}")

    def _update_connector_db(self, connector: BaseConnector) -> None:
        """Persist connector telemetry in external_connectors table."""
        try:
            conn = get_db_connection()
            c = connector.config
            conn.execute(
                """
                INSERT OR REPLACE INTO external_connectors (
                    id, name, display_name, connector_type, organization_owner,
                    auth_method, is_simulated, sync_status, sync_interval_minutes,
                    last_successful_sync, next_sync_at, records_received, records_rejected,
                    validation_failures, duplicates_detected, conflicts_count, latency_ms,
                    error_rate_pct, credential_status, credential_expiry, masked_credential,
                    rate_limit_per_minute, configuration_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c.id, c.name, c.display_name, c.connector_type.value, c.organization_owner,
                    c.auth_method.value, 1 if c.is_simulated else 0, c.sync_status.value,
                    c.sync_interval_minutes, c.last_successful_sync, c.next_sync_at,
                    c.records_received, c.records_rejected, c.validation_failures,
                    c.duplicates_detected, c.conflicts_count, c.latency_ms, c.error_rate_pct,
                    c.credential_status.value, c.credential_expiry, c.masked_credential,
                    c.rate_limit_per_minute, json.dumps(c.model_dump()),
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


_pipeline_instance = IngestionPipeline()


def get_ingestion_pipeline() -> IngestionPipeline:
    return _pipeline_instance


def get_pending_conflicts() -> List[FieldConflict]:
    # Return in-memory or query DB
    in_mem = [c for c in _PENDING_CONFLICTS.values() if c.status == ConflictStatus.PENDING_REVIEW]
    if in_mem:
        return in_mem
    db_conflicts = _load_conflicts_from_db()
    _PENDING_CONFLICTS.update(db_conflicts)
    return list(db_conflicts.values())


def get_pending_identity_merges() -> List[IdentityMatchCandidate]:
    return [m for m in _PENDING_IDENTITY_MERGES.values() if m.status == ResolutionStatus.PENDING_REVIEW]


def resolve_field_conflict(
    conflict_id: str,
    resolution: ConflictStatus,
    officer_id: str,
    notes: str = "",
    override_value: Optional[Any] = None,
) -> Optional[FieldConflict]:
    """
    Human review sign-off on a field-level conflict.
    Applies non-destructive update to the canonical record if ACCEPTED_PROPOSED or OVERRIDDEN_MANUAL.
    """
    conf = _PENDING_CONFLICTS.get(conflict_id)
    if not conf:
        # Check SQLite DB
        db_conflicts = _load_conflicts_from_db()
        conf = db_conflicts.get(conflict_id)
        if not conf:
            return None
        _PENDING_CONFLICTS[conflict_id] = conf

    conf.status = resolution
    conf.resolved_by = officer_id
    conf.resolved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conf.resolution_notes = notes

    # Determine resolved value
    chosen_value = None
    if resolution == ConflictStatus.ACCEPTED_PROPOSED:
        chosen_value = conf.proposed_value
    elif resolution == ConflictStatus.OVERRIDDEN_MANUAL:
        chosen_value = override_value if override_value is not None else conf.proposed_value

    # Apply to canonical case if adopting incoming or manual override
    if chosen_value is not None:
        _apply_resolved_value_to_canonical(conf.case_id, conf.field_name, chosen_value)

    # Persist updated conflict status to SQLite
    _save_conflict_to_db(conf)

    append_audit_event({
        "action": "UPDATE",
        "entity_type": "field_conflict",
        "entity_id": conflict_id,
        "actor_id": officer_id,
        "actor_role": "SUPERVISING_LEGAL_OFFICER",
        "details": {
            "resolution": resolution.value,
            "field_name": conf.field_name,
            "case_id": conf.case_id,
            "chosen_value": str(chosen_value) if chosen_value is not None else "KEPT_CANONICAL",
            "notes": notes,
        },
    })

    return conf


def _apply_resolved_value_to_canonical(case_id: str, field_name: str, new_value: Any) -> None:
    """Non-destructively apply reviewed value to canonical case and linked tables."""
    try:
        from app.database import get_case, _MEMORY_CASES
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        case_data = {}
        if row and row["data"]:
            case_data = json.loads(row["data"])
        else:
            c_obj = get_case(case_id)
            if c_obj:
                case_data = c_obj.model_dump()

        case_data[field_name] = new_value
        cursor.execute(
            "UPDATE cases SET data = ? WHERE case_id = ?",
            (json.dumps(case_data), case_id),
        )
        conn.commit()

        # Update in-memory cache if present
        if case_id in _MEMORY_CASES:
            try:
                setattr(_MEMORY_CASES[case_id], field_name, new_value)
            except Exception:
                pass

        # Also update linked domain tables safely
        try:
            if field_name in ("hearing_date", "next_hearing_date"):
                hearing_id = f"H-{case_id}-{uuid.uuid4().hex[:6]}"
                cursor.execute(
                    """
                    INSERT INTO hearings_schedule (
                        id, case_id, court_name, hearing_date, hearing_type, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (hearing_id, case_id, "Chief Judicial Magistrate Court", str(new_value), "Reconciled Hearing", "Scheduled"),
                )
                conn.commit()
            elif field_name == "arrest_date":
                cursor.execute(
                    "UPDATE custody_records SET admission_date = ? WHERE accused_id = ?",
                    (str(new_value), case_id),
                )
                conn.commit()
            elif field_name == "custody_days":
                cursor.execute(
                    "UPDATE custody_records SET countable_custody_days = ? WHERE accused_id = ?",
                    (int(new_value), case_id),
                )
                conn.commit()
        except Exception:
            pass

        conn.close()

        # Dual-write to Supabase if active
        try:
            from app.supabase_adapter import is_supabase_active, get_supabase_client
            if is_supabase_active():
                sb = get_supabase_client()
                if sb:
                    sb.table("cases").upsert({"case_id": case_id, "data": json.dumps(case_data)}).execute()
        except Exception:
            pass
    except Exception as err:
        print(f"[WARN] Failed to apply reconciled value to canonical case {case_id}: {err}")
