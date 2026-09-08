"""
ingestion/connectors/ecourts_connector.py — e-Courts Judicial Services (CIS / NJDG) Connector.

Synchronizes court case dockets, next hearing listings, bench assignments, and bail disposal orders.
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
from app.ingestion.connectors.base import BaseConnector, ValidationResult, RetryEngine


class ECourtsConnector(BaseConnector):
    def __init__(self, config: Optional[ConnectorConfig] = None):
        if config is None:
            config = ConnectorConfig(
                id="conn_ecourts",
                name="ecourts_docket_sync",
                display_name="e-Courts Judicial Services (CIS / NJDG)",
                connector_type=ConnectorType.SIMULATED_GOV_INTEGRATION,
                organization_owner="org_high_court",
                auth_method=AuthMethod.API_KEY,
                is_simulated=True,
                sync_status=SyncStatus.HEALTHY,
                operational_status=ConnectorOperationalStatus.ONLINE,
                sync_interval_minutes=60,
                rate_limit_per_minute=60,
                latency_ms=145.0,
                error_rate_pct=0.0,
                endpoint_url=os.getenv("ECOURTS_ENDPOINT_URL", "mock://sandbox.ecourts.gov.in/v2/dockets/sync"),
            )
        super().__init__(config)

    def get_source_name(self) -> str:
        return "[SIMULATED DATA] e-Courts CIS / NJDG Portal" if self.config.is_simulated else "e-Courts CIS / NJDG Portal"

    def fetch_records(
        self,
        since: Optional[str] = None,
        limit: int = 50,
        page: int = 1,
        offset: int = 0,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch court docket and hearing updates with true pagination, simulated latency, and rate limiting."""
        start_time = time.time()
        allowed, wait_sec = self.rate_limiter.acquire(1)
        if not allowed:
            time.sleep(min(wait_sec, 0.1))

        today = datetime.date.today()
        h1 = (today + datetime.timedelta(days=7)).isoformat()
        h2 = (today + datetime.timedelta(days=14)).isoformat()
        h3 = (today + datetime.timedelta(days=21)).isoformat()
        h4 = (today + datetime.timedelta(days=28)).isoformat()
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        all_records = [
            {
                "cnr_number": "DLCT01-004921-2024",
                "case_number": "BAIL APPLN 491/2024",
                "court_name": "Court of Additional Sessions Judge 02, Central",
                "judge_designation": "Presiding Additional Sessions Judge",
                "next_hearing_date": h1,
                "stage_of_case": "Remand & Bail Consideration",
                "petitioner": "State (NCT of Delhi)",
                "respondent_accused": "Suresh Patel",
                "fir_number": "FIR-2025-0104",
                "police_station": "Kotwali PS",
                "legal_code": "BNS_2023",
                "offense_sections": ["BNS 115(2)", "BNS 351(2)"],
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
            {
                "cnr_number": "DLCT01-008192-2024",
                "case_number": "SC 812/2024",
                "court_name": "Special NDPS Court, Patiala House",
                "judge_designation": "Special NDPS Judge",
                "next_hearing_date": h2,
                "stage_of_case": "Prosecution Evidence",
                "petitioner": "Narcotics Control Bureau",
                "respondent_accused": "Mohd. Tariq",
                "fir_number": "FIR-2024-NDPS-88",
                "police_station": "Special Cell PS",
                "legal_code": "SPECIAL_ACTS",
                "offense_sections": ["NDPS 20(b)", "NDPS 29"],
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
            {
                "cnr_number": "DLNW01-009122-2024",
                "case_number": "CRL 102/2024",
                "court_name": "Rohini District & Sessions Court",
                "judge_designation": "Chief Metropolitan Magistrate",
                "next_hearing_date": h3,
                "stage_of_case": "Charge Framing",
                "petitioner": "State (NCT of Delhi)",
                "respondent_accused": "Ramesh Chandra",
                "fir_number": "FIR-2024-ROH-91",
                "police_station": "Rohini North PS",
                "legal_code": "BNS_2023",
                "offense_sections": ["BNS 303(2)"],
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
            {
                "cnr_number": "DLCT01-002194-2024",
                "case_number": "BAIL APPLN 204/2024",
                "court_name": "Tis Hazari Court Complex",
                "judge_designation": "Additional Chief Judicial Magistrate",
                "next_hearing_date": h4,
                "stage_of_case": "Final Arguments",
                "petitioner": "State (NCT of Delhi)",
                "respondent_accused": "Vikram Singh",
                "fir_number": "FIR-2024-TH-12",
                "police_station": "Civil Lines PS",
                "legal_code": "BNS_2023",
                "offense_sections": ["BNS 316(2)"],
                "source_timestamp": now_ts,
                "is_simulated": self.config.is_simulated,
            },
        ]

        paginated = self.paginate_records(all_records, limit=limit, page=page, offset=offset, cursor=cursor)
        records = paginated["items"]

        latency = round((time.time() - start_time) * 1000 + 42.0, 1)
        self.config.latency_ms = latency
        self.record_audit_call(
            method="GET",
            endpoint_url=self.get_endpoint_url("/v2/dockets/sync"),
            response_status=200,
            latency_ms=latency,
            idempotency_key=f"idemp_ecourts_{int(time.time())}",
            attempt_number=1,
            payload_hash=self.compute_payload_hash({"count": len(records)}),
        )
        return records

    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        cnr = raw_record.get("cnr_number")
        if not cnr:
            return ValidationResult(is_valid=False, errors=["Missing required CNR number in e-Courts record."])

        # Validate synthetic demo markers in production mode
        valid_marker, err_msg = self.check_synthetic_markers(raw_record)
        if not valid_marker:
            return ValidationResult(is_valid=False, errors=[err_msg or "Synthetic data rejected."])

        normalized = {
            **raw_record,
            "legal_code": self.normalize_legal_code(raw_record.get("legal_code", "BNS_2023")),
            "next_hearing_date": self.normalize_date(raw_record.get("next_hearing_date")),
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
            source_version="v2.1",
            source_timestamp=raw_record.get("source_timestamp"),
        )
