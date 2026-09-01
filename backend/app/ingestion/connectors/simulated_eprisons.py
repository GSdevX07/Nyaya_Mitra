"""
ingestion/connectors/simulated_eprisons.py — [SIMULATED] ePrisons Jail Inmate Connector.

Simulates automated scheduled polling of prison admission dockets, custody certificates,
and facility occupancy tracking. Clearly marked as SIMULATED.
"""

from __future__ import annotations
import datetime
from typing import Dict, Any, List, Optional
from app.ingestion.models import ConnectorConfig, ConnectorType, SyncStatus, AuthMethod, DataClassification
from app.ingestion.connectors.base import BaseConnector, ValidationResult


class SimulatedEPrisonsConnector(BaseConnector):
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                id="conn_simulated_eprisons",
                name="eprisons_jail_sync",
                display_name="[SIMULATED] ePrisons National Prison Registry",
                connector_type=ConnectorType.SIMULATED_GOV_INTEGRATION,
                organization_owner="org_prison_dept",
                auth_method=AuthMethod.MUTUAL_TLS,
                is_simulated=True,
                sync_status=SyncStatus.HEALTHY,
                sync_interval_minutes=120,
            )
        super().__init__(config)

    def get_source_name(self) -> str:
        return "[SIMULATED] ePrisons Connector"

    def fetch_simulated_feed(self) -> List[Dict[str, Any]]:
        """Generate realistic simulated custody intake batches."""
        today = datetime.date.today()
        intake_date_1 = (today - datetime.timedelta(days=220)).isoformat()
        intake_date_2 = (today - datetime.timedelta(days=430)).isoformat()

        return [
            {
                "inmate_number": "EPR-DEL-2024-8841",
                "full_name": "Satish Verma",
                "gender": "Male",
                "age": 34,
                "offense_sections": ["BNS 303(2)", "BNS 317(2)"],
                "legal_code": "BNS_2023",
                "arrest_date": intake_date_1,
                "admission_date": intake_date_1,
                "custody_days": 220,
                "max_sentence_days_for_offense": 730,
                "jail_location": "Central Jail Tihar No. 4",
                "court_name": "Tis Hazari Metropolitan Court",
                "police_station": "Kashmere Gate PS",
                "fir_number": "FIR-2024-KG-419",
                "relative_name": "Sunita Verma",
                "relative_relation": "Wife",
                "relative_phone": "+91 98110 44211",
                "punishable_by_death_or_life": False,
                "multiple_active_cases": False,
                "is_simulated": True,
            },
            {
                "inmate_number": "EPR-DEL-2024-9102",
                "full_name": "Manohar Lal",
                "gender": "Male",
                "age": 62,
                "offense_sections": ["IPC 379", "IPC 411"],
                "legal_code": "IPC_1860",
                "arrest_date": intake_date_2,
                "admission_date": intake_date_2,
                "custody_days": 430,
                "max_sentence_days_for_offense": 1095,
                "jail_location": "Mandoli Sub-Jail No. 1",
                "court_name": "Karkardooma District Court",
                "police_station": "Seelampur PS",
                "fir_number": "FIR-2024-SP-102",
                "relative_name": "Rajesh Lal",
                "relative_relation": "Son",
                "relative_phone": "+91 98770 12390",
                "punishable_by_death_or_life": False,
                "multiple_active_cases": False,
                "is_simulated": True,
            },
        ]

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        full_name = raw_record.get("full_name")
        if not full_name:
            return ValidationResult(is_valid=False, errors=["Missing full_name in ePrisons record."])

        offense_sections = raw_record.get("offense_sections", ["BNS 303(2)"])
        legal_code = self.normalize_legal_code(raw_record.get("legal_code", "BNS_2023"))

        normalized = {
            **raw_record,
            "full_name": full_name,
            "legal_code": legal_code,
            "offense_sections": offense_sections,
            "data_source_status": "FUTURE_GOVERNMENT_API",
            "source_provenance": {
                "source": "[SIMULATED] ePrisons Connector",
                "connector_id": self.config.id,
                "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "payload_hash": self.compute_payload_hash(raw_record),
            },
        }

        return ValidationResult(is_valid=True, normalized_data=normalized)
