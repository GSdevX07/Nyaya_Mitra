"""
ingestion/connectors/spreadsheet_connector.py — Structured CSV/Excel Importer.

Parses tabular files (Jail Inmate Rolls, DLSA Camp Rosters) with dynamic column mapping.
"""

from __future__ import annotations
import csv
import io
import datetime
from typing import Dict, Any, List, Optional
from app.ingestion.models import ConnectorConfig, ConnectorType, SyncStatus, AuthMethod, DataClassification
from app.ingestion.connectors.base import BaseConnector, ValidationResult


DEFAULT_SPREADSHEET_MAPPING = {
    "prisoner_name": "full_name",
    "name": "full_name",
    "accused_name": "full_name",
    "inmate_id": "inmate_number",
    "cnr": "cnr_number",
    "cnr_number": "cnr_number",
    "fir": "fir_number",
    "fir_number": "fir_number",
    "police_station": "police_station",
    "court": "court_name",
    "court_name": "court_name",
    "offense": "offense_sections",
    "sections": "offense_sections",
    "section": "offense_sections",
    "arrest_date": "arrest_date",
    "admission_date": "arrest_date",
    "custody_days": "custody_days",
    "age": "age",
    "gender": "gender",
    "jail_location": "jail_location",
    "jail": "jail_location",
    "relative_name": "relative_name",
    "relative_phone": "relative_phone",
    "legal_code": "legal_code",
}


class SpreadsheetConnector(BaseConnector):
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                id="conn_spreadsheet_import",
                name="spreadsheet_bulk_importer",
                display_name="Secure Spreadsheet / CSV Importer",
                connector_type=ConnectorType.FILE_IMPORT_CSV,
                organization_owner="org_dlsa_central",
                auth_method=AuthMethod.SESSION_USER,
                is_simulated=False,
                sync_status=SyncStatus.HEALTHY,
                field_mapping=DEFAULT_SPREADSHEET_MAPPING,
            )
        super().__init__(config)

    def get_source_name(self) -> str:
        return "SPREADSHEET_IMPORT"

    def parse_csv_content(self, csv_text: str, custom_mapping: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Parse raw CSV string into normalized record dicts."""
        mapping = {**DEFAULT_SPREADSHEET_MAPPING, **(custom_mapping or {})}
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = []
        for row in reader:
            normalized_row = {}
            for col_header, val in row.items():
                if not col_header:
                    continue
                clean_header = col_header.strip().lower().replace(" ", "_")
                target_field = mapping.get(clean_header, clean_header)
                normalized_row[target_field] = (val or "").strip()
            if normalized_row:
                rows.append(normalized_row)
        return rows

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        errors = []
        
        # Synthetic check
        is_allowed_synthetic, synth_err = self.check_synthetic_markers(raw_record)
        if not is_allowed_synthetic:
            return ValidationResult(is_valid=False, errors=[synth_err or "Synthetic rejected."])

        # Mandatory fields
        full_name = raw_record.get("full_name") or raw_record.get("prisoner_name") or raw_record.get("name")
        if not full_name:
            errors.append("Missing mandatory field: full_name")

        offense_raw = raw_record.get("offense_sections") or raw_record.get("sections") or ["BNS 303(2)"]
        if isinstance(offense_raw, str):
            offense_sections = [s.strip() for s in offense_raw.split(",") if s.strip()]
        elif isinstance(offense_raw, list):
            offense_sections = offense_raw
        else:
            offense_sections = ["BNS 303(2)"]

        arrest_date = self.normalize_date(str(raw_record.get("arrest_date") or ""))
        legal_code = self.normalize_legal_code(str(raw_record.get("legal_code") or (offense_sections[0] if offense_sections else "")))

        try:
            custody_days = int(raw_record.get("custody_days") or 0)
        except ValueError:
            custody_days = 0

        try:
            age = int(raw_record.get("age") or 30)
        except ValueError:
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
            "jail_location": raw_record.get("jail_location") or "District Jail, Central",
            "court_name": raw_record.get("court_name") or "Metropolitan Magistrate Court",
            "district": raw_record.get("district") or "Central Delhi",
            "state": raw_record.get("state") or "Delhi",
            "police_station": raw_record.get("police_station") or "Kotwali PS",
            "fir_number": raw_record.get("fir_number") or f"FIR-2025-{abs(hash(full_name)) % 900 + 100}",
            "cnr_number": raw_record.get("cnr_number") or "",
            "inmate_number": raw_record.get("inmate_number") or "",
            "relative_name": raw_record.get("relative_name") or "",
            "relative_phone": raw_record.get("relative_phone") or "",
            "data_source_status": "MANUAL_INSTITUTIONAL_ENTRY" if not raw_record.get("is_demo") else "DEMO_SYNTHETIC",
            "source_provenance": {
                "source": "SPREADSHEET_IMPORT",
                "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "payload_hash": self.compute_payload_hash(raw_record),
            },
        }

        return ValidationResult(is_valid=True, normalized_data=normalized)
