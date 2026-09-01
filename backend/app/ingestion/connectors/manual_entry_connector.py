"""
ingestion/connectors/manual_entry_connector.py — Controlled Manual Intake Gateway.

Validates official manual entries from Jail intake desks, Police Stations, or Legal Aid clinics.
"""

from __future__ import annotations
import datetime
from typing import Dict, Any, Optional
from app.ingestion.models import ConnectorConfig, ConnectorType, SyncStatus, AuthMethod, DataClassification
from app.ingestion.connectors.base import BaseConnector, ValidationResult


class ManualEntryConnector(BaseConnector):
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                id="conn_manual_entry",
                name="controlled_manual_gateway",
                display_name="Controlled Manual Entry Intake Desk",
                connector_type=ConnectorType.MANUAL_CONTROLLED_ENTRY,
                organization_owner="org_dlsa_central",
                auth_method=AuthMethod.SESSION_USER,
                is_simulated=False,
                sync_status=SyncStatus.HEALTHY,
            )
        super().__init__(config)

    def get_source_name(self) -> str:
        return "MANUAL_CONTROLLED_ENTRY"

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        errors = []

        is_allowed_synthetic, synth_err = self.check_synthetic_markers(raw_record)
        if not is_allowed_synthetic:
            return ValidationResult(is_valid=False, errors=[synth_err or "Synthetic rejected."])

        # Validate mandatory prisoner details
        full_name = str(raw_record.get("full_name") or "").strip()
        if len(full_name) < 2:
            errors.append("Accused full name must be at least 2 characters.")

        offense_sections = raw_record.get("offense_sections") or []
        if isinstance(offense_sections, str):
            offense_sections = [s.strip() for s in offense_sections.split(",") if s.strip()]
        if not offense_sections:
            errors.append("At least one legal offense section must be specified.")

        arrest_date = self.normalize_date(str(raw_record.get("arrest_date") or ""))
        legal_code = self.normalize_legal_code(str(raw_record.get("legal_code") or (offense_sections[0] if offense_sections else "")))

        try:
            custody_days = int(raw_record.get("custody_days") or 0)
            if custody_days < 0:
                errors.append("Custody days cannot be negative.")
        except ValueError:
            errors.append("Custody days must be an integer.")
            custody_days = 0

        try:
            age = int(raw_record.get("age") or 30)
            if age < 18 or age > 115:
                errors.append("Adult accused age must be between 18 and 115.")
        except ValueError:
            errors.append("Age must be an integer.")
            age = 30

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        normalized = {
            "full_name": full_name,
            "gender": raw_record.get("gender") or "Male",
            "age": age,
            "offense_sections": offense_sections,
            "legal_code": legal_code,
            "arrest_date": arrest_date,
            "custody_days": custody_days,
            "max_sentence_days_for_offense": int(raw_record.get("max_sentence_days_for_offense") or 730),
            "punishable_by_death_or_life": bool(raw_record.get("punishable_by_death_or_life", False)),
            "multiple_active_cases": bool(raw_record.get("multiple_active_cases", False)),
            "jail_location": raw_record.get("jail_location") or "District Central Jail",
            "court_name": raw_record.get("court_name") or "Chief Judicial Magistrate Court",
            "district": raw_record.get("district") or "Central Delhi",
            "state": raw_record.get("state") or "Delhi",
            "police_station": raw_record.get("police_station") or "Kotwali PS",
            "fir_number": raw_record.get("fir_number") or f"FIR-2025-{abs(hash(full_name)) % 900 + 100}",
            "cnr_number": raw_record.get("cnr_number") or "",
            "inmate_number": raw_record.get("inmate_number") or "",
            "relative_name": raw_record.get("relative_name") or "",
            "relative_phone": raw_record.get("relative_phone") or "",
            "permanent_address": raw_record.get("permanent_address") or "",
            "preferred_language": raw_record.get("preferred_language") or "en",
            "required_docs": raw_record.get("required_docs") or ["fir_copy", "remand_order", "charge_sheet"],
            "present_docs": raw_record.get("present_docs") or ["fir_copy"],
            "data_source_status": "MANUAL_INSTITUTIONAL_ENTRY",
            "source_provenance": {
                "source": "MANUAL_CONTROLLED_ENTRY",
                "entered_by": raw_record.get("officer_id", "INTAKE_OFFICER"),
                "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "payload_hash": self.compute_payload_hash(raw_record),
            },
        }

        return ValidationResult(is_valid=True, normalized_data=normalized)
