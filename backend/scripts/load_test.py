"""
Asynchronous and multi-threaded load testing harness for Nyaya Mitra API.
Measures latency quantiles (p50, p95, p99), requests per second (RPS), and error rates.

Usage:
  python scripts/load_test.py [--base-url http://127.0.0.1:8000] [--concurrency 25] [--requests 200]
"""

from __future__ import annotations
import sys
import time
import uuid
import json
import urllib.request
import urllib.error
import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple


def run_single_request(
    base_url: str,
    endpoint: str,
    method: str = "GET",
    payload: dict = None,
    headers: dict = None,
) -> Tuple[bool, int, float, str]:
    """Execute a single HTTP request and measure latency."""
    url = f"{base_url.rstrip('/')}{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8") if payload else None
    req_headers = headers or {}

    req = urllib.request.Request(url, data=data_bytes, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in req_headers.items():
        req.add_header(k, v)

    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            duration = time.perf_counter() - start
            return True, resp.status, duration, ""
    except urllib.error.HTTPError as e:
        duration = time.perf_counter() - start
        # Non-5xx may still be expected in certain idempotency or validation checks
        success = e.code < 500
        return success, e.code, duration, str(e.reason)
    except Exception as exc:
        duration = time.perf_counter() - start
        return False, 0, duration, str(exc)


def run_benchmark(
    base_url: str,
    total_requests: int = 100,
    concurrency: int = 10,
) -> Dict[str, Any]:
    """Execute concurrent requests across read and write operations."""
    print(f"Starting Load Benchmark against {base_url}")
    print(f"Parameters: {total_requests} total requests, {concurrency} concurrent workers.")

    endpoints_mix = [
        ("GET", "/health/live", None),
        ("GET", "/health/ready", None),
        ("GET", "/cases", None),
        ("GET", "/metrics", None),
        (
            "POST",
            "/jobs/submit",
            {
                "job_type": "AI_SYNTHESIS",
                "payload": {"case_id": "UTP-LOAD-TEST", "petition_type": "REGULAR_BAIL"},
            },
        ),
    ]

    latencies: List[float] = []
    success_count = 0
    failure_count = 0
    status_distribution: Dict[int, int] = {}

    bench_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(total_requests):
            method, endpoint, payload = endpoints_mix[i % len(endpoints_mix)]
            headers = {
                "X-Request-ID": f"LOAD-REQ-{i}-{uuid.uuid4().hex[:6]}",
                "Idempotency-Key": f"LOAD-KEY-{i // 2}",  # Test idempotency deduplication on repeat
            }
            f = executor.submit(run_single_request, base_url, endpoint, method, payload, headers)
            futures.append(f)

        for future in as_completed(futures):
            success, status_code, duration, error_msg = future.result()
            latencies.append(duration)
            status_distribution[status_code] = status_distribution.get(status_code, 0) + 1
            if success:
                success_count += 1
            else:
                failure_count += 1

    total_time = time.perf_counter() - bench_start
    rps = total_requests / total_time if total_time > 0 else 0.0

    # Calculate percentiles
    sorted_lats = sorted(latencies)
    p50 = statistics.median(sorted_lats) * 1000.0
    p90 = (sorted_lats[int(len(sorted_lats) * 0.90)] if sorted_lats else 0.0) * 1000.0
    p95 = (sorted_lats[int(len(sorted_lats) * 0.95)] if sorted_lats else 0.0) * 1000.0
    p99 = (sorted_lats[int(len(sorted_lats) * 0.99)] if sorted_lats else 0.0) * 1000.0
    mean_lat = (statistics.mean(sorted_lats) if sorted_lats else 0.0) * 1000.0

    results = {
        "total_requests": total_requests,
        "concurrency": concurrency,
        "total_time_seconds": round(total_time, 3),
        "requests_per_second": round(rps, 2),
        "successful_requests": success_count,
        "failed_requests": failure_count,
        "latency_ms": {
            "mean": round(mean_lat, 2),
            "p50": round(p50, 2),
            "p90": round(p90, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
        },
        "status_distribution": status_distribution,
    }

    print("\nBenchmark Results Summary:")
    print(f"  Total Requests:      {total_requests}")
    print(f"  Duration:            {round(total_time, 2)} s")
    print(f"  Throughput (RPS):    {round(rps, 1)} req/s")
    print(f"  Success Rate:        {round((success_count / total_requests) * 100, 1)}%")
    print(f"  Latency p50 (Med):   {round(p50, 1)} ms")
    print(f"  Latency p95:         {round(p95, 1)} ms")
    print(f"  Latency p99:         {round(p99, 1)} ms")
    print(f"  Status Codes:        {status_distribution}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Nyaya Mitra Load Testing Harness")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Target API root URL")
    parser.add_argument("--requests", type=int, default=100, help="Total requests to dispatch")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent worker threads")
    args = parser.parse_args()

    results = run_benchmark(
        base_url=args.base_url,
        total_requests=args.requests,
        concurrency=args.concurrency,
    )
    if results["failed_requests"] > (results["total_requests"] * 0.10):
        print("FAIL: Load test error rate exceeded 10% tolerance threshold.")
        sys.exit(1)


if __name__ == "__main__":
    main()
