"""
ingestion/connectors/base.py — Abstract Base Connector & Contract Validation.

Every external source connector (API, File, Manual, Simulated) implements this interface.
"""

from __future__ import annotations
import abc
import datetime
import hashlib
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from app.ingestion.models import (
    ConnectorConfig, ConnectorType, SyncStatus, AuthMethod, DataClassification, RawSourceRecord
)
from app.auth.config import DEMO_MODE


class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str] | None = None, normalized_data: Dict[str, Any] | None = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.normalized_data = normalized_data or {}


class BaseConnector(abc.ABC):
    def __init__(self, config: ConnectorConfig):
        self.config = config

    @abc.abstractmethod
    def get_source_name(self) -> str:
        """Return canonical source identifier."""
        pass

    def compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        """Deterministic SHA-256 hash of raw JSON payload to detect replay."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def check_synthetic_markers(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Detect synthetic demo tags.
        In production (DEMO_MODE=false), synthetic markers cause record rejection.
        """
        content_str = json.dumps(payload).lower()
        has_demo_tag = any(tag in content_str for tag in ["synthetic", "demo_synthetic", "test_accused", "mock_data", "sample_jail"])
        
        if has_demo_tag and not DEMO_MODE:
            return False, "Synthetic/demo data rejected in production mode."
        return True, None

    def normalize_legal_code(self, raw_code: str) -> str:
        """Normalize BNS 2023 vs IPC 1860."""
        raw_upper = (raw_code or "").strip().upper()
        if "BNS" in raw_upper or "BHARATIYA" in raw_upper:
            return "BNS_2023"
        elif "IPC" in raw_upper or "PENAL" in raw_upper:
            return "IPC_1860"
        return "SPECIAL_ACTS"

    def normalize_date(self, raw_date_str: str) -> str:
        """Normalize arbitrary date string to ISO YYYY-MM-DD."""
        if not raw_date_str:
            return datetime.date.today().isoformat()
        
        raw = raw_date_str.strip()
        # Direct YYYY-MM-DD check
        if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
            return raw[:10]
        # DD/MM/YYYY or DD-MM-YYYY
        match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
        if match:
            day, month, year = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
        
        return datetime.date.today().isoformat()

    @abc.abstractmethod
    def validate_and_normalize(self, raw_record: Dict[str, Any]) -> ValidationResult:
        """Validate required fields, apply field mappings, and normalize values."""
        pass
