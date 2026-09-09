"""
Operational metrics registry and Prometheus telemetry exposition for Nyaya Mitra.
Tracks API latency, error rates, queue depth, job durations, OCR, RAG retrieval, AI tokens, and connectors.
"""

from __future__ import annotations
import time
import threading
from typing import Dict, Any, List, Optional
from collections import defaultdict


class MetricsCollector:
    """Thread-safe in-memory operational metrics collector."""

    def __init__(self):
        self._lock = threading.Lock()

        # Counters: (name, tuple(sorted labels)) -> count
        self._counters: Dict[str, Dict[tuple, float]] = defaultdict(lambda: defaultdict(float))
        # Histograms: (name, tuple(sorted labels)) -> list of recorded seconds
        self._histograms: Dict[str, Dict[tuple, List[float]]] = defaultdict(lambda: defaultdict(list))
        # Gauges: (name, tuple(sorted labels)) -> current value
        self._gauges: Dict[str, Dict[tuple, float]] = defaultdict(lambda: defaultdict(float))

        # Initial default gauge states
        self.set_gauge("nyaya_mitra_database_health", {}, 1.0)
        self.set_gauge("nyaya_mitra_circuit_breaker_state", {"service": "ai_gateway"}, 0.0)
        self.set_gauge("nyaya_mitra_circuit_breaker_state", {"service": "ecourts"}, 0.0)
        self.set_gauge("nyaya_mitra_circuit_breaker_state", {"service": "eprisons"}, 0.0)

    # ── Mutation Methods ─────────────────────────────────────────────────────────

    def inc_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        """Increment a counter by value."""
        label_tuple = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._counters[name][label_tuple] += value

    def set_gauge(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        """Set a gauge value."""
        label_tuple = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._gauges[name][label_tuple] = value

    def observe_histogram(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 0.0) -> None:
        """Record an observed latency/duration value."""
        label_tuple = tuple(sorted((labels or {}).items()))
        with self._lock:
            hist_list = self._histograms[name][label_tuple]
            hist_list.append(value)
            # Keep rolling window of last 1000 observations per label set
            if len(hist_list) > 1000:
                self._histograms[name][label_tuple] = hist_list[-1000:]

    # ── Domain-Specific Recording Helpers ───────────────────────────────────────

    def record_http_request(self, route: str, method: str, status_code: int, duration_seconds: float) -> None:
        labels = {"route": route, "method": method, "status": str(status_code)}
        self.inc_counter("nyaya_mitra_http_requests_total", labels)
        self.observe_histogram("nyaya_mitra_http_request_duration_seconds", {"route": route, "method": method}, duration_seconds)
        if status_code >= 400:
            category = "client_error" if status_code < 500 else "server_error"
            self.inc_counter("nyaya_mitra_http_errors_total", {"route": route, "error_category": category})

    def record_job_execution(self, job_type: str, status: str, duration_seconds: float) -> None:
        self.inc_counter("nyaya_mitra_jobs_total", {"job_type": job_type, "status": status})
        self.observe_histogram("nyaya_mitra_job_duration_seconds", {"job_type": job_type}, duration_seconds)

    def record_ocr_operation(self, status: str, duration_seconds: float) -> None:
        self.inc_counter("nyaya_mitra_ocr_operations_total", {"status": status})
        self.observe_histogram("nyaya_mitra_ocr_duration_seconds", {}, duration_seconds)
        if status != "success":
            self.inc_counter("nyaya_mitra_ocr_failures_total", {})

    def record_rag_retrieval(self, chunks_count: int, duration_seconds: float) -> None:
        self.inc_counter("nyaya_mitra_rag_retrieval_chunks_total", {}, value=float(chunks_count))
        self.observe_histogram("nyaya_mitra_rag_retrieval_duration_seconds", {}, duration_seconds)

    def record_ai_usage(self, provider: str, input_tokens: int, output_tokens: int, status: str = "success") -> None:
        self.inc_counter("nyaya_mitra_ai_requests_total", {"provider": provider, "status": status})
        self.inc_counter("nyaya_mitra_ai_tokens_total", {"provider": provider, "type": "input"}, value=float(input_tokens))
        self.inc_counter("nyaya_mitra_ai_tokens_total", {"provider": provider, "type": "output"}, value=float(output_tokens))

    def record_notification_delivery(self, channel: str, status: str) -> None:
        self.inc_counter("nyaya_mitra_notification_delivery_total", {"channel": channel, "status": status})

    def record_connector_call(self, connector: str, status: str) -> None:
        self.inc_counter("nyaya_mitra_connector_sync_total", {"connector": connector, "status": status})
        if status != "success":
            self.inc_counter("nyaya_mitra_connector_failures_total", {"connector": connector})

    def update_queue_depths(self, depths: Dict[str, int]) -> None:
        for status_name, count in depths.items():
            self.set_gauge("nyaya_mitra_job_queue_depth", {"status": status_name.lower()}, float(count))

    # ── Exposition Formats ──────────────────────────────────────────────────────

    def to_prometheus_format(self) -> str:
        """Render all metrics in Prometheus text format (version 0.0.4)."""
        lines: List[str] = []

        with self._lock:
            # Render Counters
            for name, series in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                for label_tuple, value in series.items():
                    label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                    lbl = f"{{{label_str}}}" if label_str else ""
                    lines.append(f"{name}{lbl} {value}")

            # Render Gauges
            for name, series in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                for label_tuple, value in series.items():
                    label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                    lbl = f"{{{label_str}}}" if label_str else ""
                    lines.append(f"{name}{lbl} {value}")

            # Render Histograms as summary count + sum
            for name, series in self._histograms.items():
                lines.append(f"# TYPE {name} summary")
                for label_tuple, values in series.items():
                    label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                    lbl_base = f"{label_str}" if label_str else ""
                    lbl_count = f"{{{lbl_base},quantile=\"count\"}}" if lbl_base else "{quantile=\"count\"}"
                    lbl_sum = f"{{{lbl_base},quantile=\"sum\"}}" if lbl_base else "{quantile=\"sum\"}"

                    count = len(values)
                    total_sum = sum(values) if count > 0 else 0.0
                    lines.append(f"{name}_count{lbl_count} {count}")
                    lines.append(f"{name}_sum{lbl_sum} {round(total_sum, 4)}")

        return "\n".join(lines) + "\n"

    def get_summary(self) -> Dict[str, Any]:
        """Summary dictionary for internal health and telemetry views."""
        with self._lock:
            total_requests = sum(self._counters.get("nyaya_mitra_http_requests_total", {}).values())
            total_errors = sum(self._counters.get("nyaya_mitra_http_errors_total", {}).values())
            error_rate = (total_errors / total_requests) if total_requests > 0 else 0.0

            # Compute avg latency
            all_durations: List[float] = []
            for vals in self._histograms.get("nyaya_mitra_http_request_duration_seconds", {}).values():
                all_durations.extend(vals)
            avg_latency_ms = (sum(all_durations) / len(all_durations) * 1000.0) if all_durations else 0.0

            # Queue depths
            queue_depths = {}
            for label_tuple, val in self._gauges.get("nyaya_mitra_job_queue_depth", {}).items():
                labels = dict(label_tuple)
                queue_depths[labels.get("status", "unknown")] = int(val)

            return {
                "http": {
                    "total_requests": int(total_requests),
                    "total_errors": int(total_errors),
                    "error_rate": round(error_rate, 4),
                    "avg_latency_ms": round(avg_latency_ms, 2),
                },
                "queue": queue_depths,
                "ai_usage": {
                    "requests": int(sum(self._counters.get("nyaya_mitra_ai_requests_total", {}).values())),
                    "tokens": int(sum(self._counters.get("nyaya_mitra_ai_tokens_total", {}).values())),
                },
                "ocr": {
                    "operations": int(sum(self._counters.get("nyaya_mitra_ocr_operations_total", {}).values())),
                    "failures": int(sum(self._counters.get("nyaya_mitra_ocr_failures_total", {}).values())),
                },
                "connectors": {
                    "syncs": int(sum(self._counters.get("nyaya_mitra_connector_sync_total", {}).values())),
                    "failures": int(sum(self._counters.get("nyaya_mitra_connector_failures_total", {}).values())),
                },
            }


_GLOBAL_METRICS: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Singleton getter for MetricsCollector."""
    global _GLOBAL_METRICS
    if _GLOBAL_METRICS is None:
        _GLOBAL_METRICS = MetricsCollector()
    return _GLOBAL_METRICS


def generate_prometheus_metrics() -> str:
    """Convenience exporter."""
    return get_metrics_collector().to_prometheus_format()
