"""
Structured JSON logging and secret/PII sanitization for Nyaya Mitra.
Ensures zero token/PII leakage while providing rich observability for ops/SRE teams.
"""

from __future__ import annotations
import re
import json
import logging
import datetime
from typing import Optional, Dict, Any

from app.telemetry.tracing import get_trace_context

# Sensitive data sanitization regex patterns
_SECRET_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]+", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"(api[_\-]?key|secret|password|auth_token)[\"']?\s*[:=]\s*[\"'][^\"']+[\"']", re.IGNORECASE), r'\1: "[REDACTED]"'),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+"), "[JWT_REDACTED]"),
    (re.compile(r"\b[2-9]{1}\d{3}\s?\d{4}\s?\d{4}\b"), "[AADHAAR_REDACTED]"),
    (re.compile(r"(\+91[\-\s]?)?[6-9]\d{9}"), "[PHONE_REDACTED]"),
]


def sanitize_sensitive_data(val: Any) -> Any:
    """Recursively scrub credentials, tokens, and PII from logged objects."""
    if isinstance(val, str):
        cleaned = val
        for pattern, replacement in _SECRET_PATTERNS:
            cleaned = pattern.sub(replacement, cleaned)
        # Prevent logging massive document dumps
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "...[TRUNCATED]"
        return cleaned
    elif isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            lower_k = str(k).lower()
            if any(s in lower_k for s in ("password", "token", "secret", "authorization", "bearer")):
                sanitized[k] = "[REDACTED]"
            elif any(p in lower_k for p in ("aadhaar", "phone", "mobile")):
                sanitized[k] = "[PII_REDACTED]"
            else:
                sanitized[k] = sanitize_sensitive_data(v)
        return sanitized
    elif isinstance(val, list):
        return [sanitize_sensitive_data(item) for item in val]
    return val


class StructuredJsonFormatter(logging.Formatter):
    """Format log records as clean, redacted JSON lines for ELK/CloudWatch/Promtail."""

    def format(self, record: logging.LogRecord) -> str:
        trace_ctx = get_trace_context()
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_sensitive_data(record.getMessage()),
            "request_id": getattr(record, "request_id", None) or trace_ctx.get("request_id"),
            "trace_id": getattr(record, "trace_id", None) or trace_ctx.get("trace_id"),
            "span_id": getattr(record, "span_id", None) or trace_ctx.get("span_id"),
            "organization_id": getattr(record, "organization_id", None),
            "actor_id": getattr(record, "actor_id", None),
            "route": getattr(record, "route", None),
            "operation": getattr(record, "operation", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "result": getattr(record, "result", None),
            "error_category": getattr(record, "error_category", None),
        }

        # Filter out None values to keep logs compact
        compact_entry = {k: v for k, v in log_entry.items() if v is not None}
        return json.dumps(compact_entry)


class StructuredLogger:
    """Wrapper around standard Logger with typed structured logging methods."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def log(
        self,
        level: int,
        message: str,
        operation: Optional[str] = None,
        route: Optional[str] = None,
        duration_ms: Optional[float] = None,
        result: Optional[str] = None,
        error_category: Optional[str] = None,
        actor_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        trace_ctx = get_trace_context()
        payload = {
            "operation": operation,
            "route": route,
            "duration_ms": duration_ms,
            "result": result,
            "error_category": error_category,
            "actor_id": actor_id,
            "organization_id": organization_id,
            "request_id": trace_ctx.get("request_id"),
            "trace_id": trace_ctx.get("trace_id"),
            "span_id": trace_ctx.get("span_id"),
        }
        if extra:
            payload.update(sanitize_sensitive_data(extra))

        self.logger.log(level, message, extra=payload)

    def info(self, message: str, **kwargs):
        self.log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log(logging.ERROR, message, **kwargs)


def get_structured_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
