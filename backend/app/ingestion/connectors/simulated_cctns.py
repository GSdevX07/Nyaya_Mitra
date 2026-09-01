"""
ingestion/connectors/simulated_cctns.py — [SIMULATED] CCTNS Police FIR Webhook Connector.

Simulates push-event webhooks from Police Crime and Criminal Tracking Network & Systems (CCTNS)
for newly registered FIRs, arrest memos, and remand dispatches. Clearly marked as SIMULATED.
"""

from __future__ import annotations
import datetime
from typing import Dict, Any, List, Optional
from app.ingestion.models import ConnectorConfig, ConnectorType, SyncStatus, AuthMethod, DataClassification
from app.ingestion.connectors.base import BaseConnector, ValidationResult


class SimulatedCCTNSConnector(BaseConnector):
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                id="conn_simulated_cctns",
                name="cctns_police_webhook",
                display_name="[SIMULATED] CCTNS National Police Network",
                connector_type=ConnectorType.API_PUSH_WEBHOOK,
                organization_owner="org_police_hq",
                auth_method=AuthMethod.BEARER_TOKEN,
                is_simulated=True,
                sync_status=SyncStatus.HEALTHY,
            )
        super().__init__(config)

    def get_source_name(self) -> str:
        return "[SIMULATED] CCTNS Police Connector"

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        errors = []
        fir_number = raw_record.get("fir_number")
        if not fir_number:
            errors.append("Missing mandatory fir_number in CCTNS push event.")

        full_name = raw_record.get("accused_name") or raw_record.get("full_name")
        if not full_name:
            errors.append("Missing accused name in CCTNS push event.")

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        arrest_date = self.normalize_date(str(raw_record.get("arrest_date") or ""))
        offense_sections = raw_record.get("offense_sections") or ["BNS 303(2)"]
        if isinstance(offense_sections, str):
            offense_sections = [s.strip() for s in offense_sections.split(",") if s.strip()]

        legal_code = self.normalize_legal_code(raw_record.get("legal_code") or offense_sections[0])

        normalized = {
            "full_name": full_name,
            "gender": raw_record.get("gender") or "Male",
            "age": int(raw_record.get("age") or 28),
            "fir_number": fir_number,
            "police_station": raw_record.get("police_station") or "Kotwali Police Station",
            "district": raw_record.get("district") or "Central Delhi",
            "state": raw_record.get("state") or "Delhi",
            "arrest_date": arrest_date,
            "offense_sections": offense_sections,
            "legal_code": legal_code,
            "io_officer_name": raw_record.get("io_officer_name") or "SI Arvind Singh",
            "data_source_status": "FUTURE_GOVERNMENT_API",
            "source_provenance": {
                "source": "[SIMULATED] CCTNS Police Connector",
                "connector_id": self.config.id,
                "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "payload_hash": self.compute_payload_hash(raw_record),
            },
        }

        return ValidationResult(is_valid=True, normalized_data=normalized)
