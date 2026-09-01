"""
ingestion/connectors/simulated_ecourts.py — [SIMULATED] eCourts Services Docket Connector.

Simulates automated synchronization of CNR case statuses, next hearing listings,
and bail disposal orders from the eCourts CIS portal. Clearly marked as SIMULATED.
"""

from __future__ import annotations
import datetime
from typing import Dict, Any, List, Optional
from app.ingestion.models import ConnectorConfig, ConnectorType, SyncStatus, AuthMethod, DataClassification
from app.ingestion.connectors.base import BaseConnector, ValidationResult


class SimulatedECourtsConnector(BaseConnector):
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                id="conn_simulated_ecourts",
                name="ecourts_docket_sync",
                display_name="[SIMULATED] eCourts Judicial Services Portal",
                connector_type=ConnectorType.SIMULATED_GOV_INTEGRATION,
                organization_owner="org_high_court",
                auth_method=AuthMethod.API_KEY,
                is_simulated=True,
                sync_status=SyncStatus.HEALTHY,
                sync_interval_minutes=60,
            )
        super().__init__(config)

    def get_source_name(self) -> str:
        return "[SIMULATED] eCourts Connector"

    def fetch_simulated_feed(self) -> List[Dict[str, Any]]:
        """Simulate court registry updates for active dockets."""
        today = datetime.date.today()
        hearing_date = (today + datetime.timedelta(days=7)).isoformat()

        return [
            {
                "cnr_number": "DLCT01-004921-2024",
                "case_number": "BAIL APPLN 491/2024",
                "court_name": "Court of Additional Sessions Judge 02, Central",
                "judge_designation": "Hon'ble Justice P. K. Mathur",
                "next_hearing_date": hearing_date,
                "stage_of_case": "Remand & Bail Consideration",
                "petitioner": "State (NCT of Delhi)",
                "respondent_accused": "Suresh Patel",
                "fir_number": "FIR-2025-0104",
                "police_station": "Kotwali PS",
                "legal_code": "BNS_2023",
                "offense_sections": ["BNS 115(2)", "BNS 351(2)"],
                "is_simulated": True,
            }
        ]

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        cnr = raw_record.get("cnr_number")
        if not cnr:
            return ValidationResult(is_valid=False, errors=["Missing CNR number in eCourts docket update."])

        normalized = {
            **raw_record,
            "data_source_status": "FUTURE_GOVERNMENT_API",
            "source_provenance": {
                "source": "[SIMULATED] eCourts Connector",
                "connector_id": self.config.id,
                "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "payload_hash": self.compute_payload_hash(raw_record),
            },
        }

        return ValidationResult(is_valid=True, normalized_data=normalized)
