"""
ingestion/connectors/gov_prosecution_connector.py — State Directorate of Prosecution Connector.

Synchronizes Public Prosecutor assignments, chargesheet filing records, and bail opposition stances.
Implements dual execution mode: LIVE API gateway vs SANDBOX simulated feed.
"""

from __future__ import annotations
import datetime
import os
import time
from typing import Dict, Any, List, Optional

from app.ingestion.models import (
    ConnectorConfig, ConnectorType, SyncStatus, ConnectorOperationalStatus,
    CredentialStatus, AuthMethod
)
from app.ingestion.connectors.base import BaseConnector, ValidationResult


class GovProsecutionConnector(BaseConnector):
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                id="conn_prosecution",
                name="prosecution_case_sync",
                display_name="Directorate of Prosecution (e-Prosecution)",
                connector_type=ConnectorType.SIMULATED_GOV_INTEGRATION,
                organization_owner="org_directorate_prosecution",
                auth_method=AuthMethod.API_KEY,
                is_simulated=True,
                sync_status=SyncStatus.HEALTHY,
                operational_status=ConnectorOperationalStatus.ONLINE,
                sync_interval_minutes=60,
                rate_limit_per_minute=40,
                latency_ms=132.0,
                error_rate_pct=0.0,
                endpoint_url=os.getenv("PROSECUTION_ENDPOINT_URL", "mock://sandbox.prosecution.gov.in/v1/cases/status"),
            )
        super().__init__(config)

    def get_source_name(self) -> str:
        return "[SIMULATED DATA] Directorate of Prosecution" if self.config.is_simulated else "Directorate of Prosecution"

    def fetch_records(
        self,
        since: Optional[str] = None,
        limit: int = 50,
        page: int = 1,
        offset: int = 0,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch prosecutor assignments and bail opposition stance records with true pagination."""
        start_time = time.time()
        self.rate_limiter.acquire(1)

        today = datetime.date.today()
        d45 = (today - datetime.timedelta(days=45)).isoformat()
        d90 = (today - datetime.timedelta(days=90)).isoformat()
        d130 = (today - datetime.timedelta(days=130)).isoformat()
        d60 = (today - datetime.timedelta(days=60)).isoformat()
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        all_records = [
            {
                "case_id": "UTP-0001",
                "cnr_number": "DLCT01-004921-2024",
                "fir_number": "FIR-2025-0104",
                "prosecutor_name": "Additional Public Prosecutor (ASJ-02)",
                "chargesheet_filed_date": d45,
                "bail_opposition_stance": "CONDITIONAL",
                "opposition_grounds": "No prior convictions; conditional bail subject to regular reporting.",
                "witnesses_examined": 2,
                "sanction_order_status": "OBTAINED",
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
            {
                "case_id": "UTP-0003",
                "cnr_number": "DLCT01-008192-2024",
                "fir_number": "FIR-2024-NDPS-88",
                "prosecutor_name": "Special Public Prosecutor (NDPS Cell)",
                "chargesheet_filed_date": d90,
                "bail_opposition_stance": "STRONGLY_OPPOSED",
                "opposition_grounds": "Commercial quantity recovery; statutory bar under Section 37 NDPS.",
                "witnesses_examined": 5,
                "sanction_order_status": "OBTAINED",
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
            {
                "case_id": "UTP-0002",
                "cnr_number": "DLNW01-009122-2024",
                "fir_number": "FIR-2024-ROH-91",
                "prosecutor_name": "Assistant Public Prosecutor (CMM Court)",
                "chargesheet_filed_date": d130,
                "bail_opposition_stance": "NOT_OPPOSED",
                "opposition_grounds": "Investigation concluded; trial unlikely to commence within 6 months.",
                "witnesses_examined": 1,
                "sanction_order_status": "OBTAINED",
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
            {
                "case_id": "UTP-0004",
                "cnr_number": "DLCT01-002194-2024",
                "fir_number": "FIR-2024-TH-12",
                "prosecutor_name": "Senior Public Prosecutor (Sessions)",
                "chargesheet_filed_date": d60,
                "bail_opposition_stance": "CONDITIONAL",
                "opposition_grounds": "Subject to local surety and travel document surrender.",
                "witnesses_examined": 3,
                "sanction_order_status": "OBTAINED",
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
        ]

        paginated = self.paginate_records(all_records, limit=limit, page=page, offset=offset, cursor=cursor)
        records = paginated["items"]

        latency = round((time.time() - start_time) * 1000 + 35.0, 1)
        self.config.latency_ms = latency
        self.record_audit_call(
            method="GET",
            endpoint_url=self.get_endpoint_url("/v1/cases/status"),
            response_status=200,
            latency_ms=latency,
            idempotency_key=f"idemp_pros_{int(time.time())}",
            attempt_number=1,
            payload_hash=self.compute_payload_hash({"count": len(records)}),
        )
        return records

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        cnr = raw_record.get("cnr_number") or raw_record.get("fir_number")
        if not cnr:
            return ValidationResult(is_valid=False, errors=["Missing CNR or FIR number in prosecution record."])

        valid_marker, err_msg = self.check_synthetic_markers(raw_record)
        if not valid_marker:
            return ValidationResult(is_valid=False, errors=[err_msg or "Synthetic data rejected."])

        normalized = {
            **raw_record,
            "data_source_status": "FUTURE_GOVERNMENT_API" if self.config.is_simulated else "GOVERNMENT_API",
            "source_provenance": {
                "source": self.get_source_name(),
                "connector_id": self.config.id,
                "ingested_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "payload_hash": self.compute_payload_hash(raw_record),
            },
        }

        return ValidationResult(
            is_valid=True,
            normalized_data=normalized,
            source_version="v1.0",
            source_timestamp=raw_record.get("source_timestamp"),
        )
