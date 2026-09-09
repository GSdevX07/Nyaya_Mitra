"""
Distributed tracing context propagation for Nyaya Mitra.
Propagates X-Request-ID, X-Trace-ID, and X-Span-ID across web requests, workers, and integrations.
"""

from __future__ import annotations
import uuid
import contextvars
from typing import Optional, Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
_trace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)
_span_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("span_id", default=None)


def get_trace_context() -> Dict[str, Optional[str]]:
    """Return the active tracing identifiers for the current task/thread."""
    return {
        "request_id": _request_id_ctx.get(),
        "trace_id": _trace_id_ctx.get(),
        "span_id": _span_id_ctx.get(),
    }


def set_trace_context(
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """Explicitly set distributed trace context values."""
    if trace_id is not None:
        _trace_id_ctx.set(trace_id)
    if span_id is not None:
        _span_id_ctx.set(span_id)
    if request_id is not None:
        _request_id_ctx.set(request_id)


def new_trace_context(request_id: Optional[str] = None) -> Dict[str, str]:
    """Generate fresh trace and span IDs."""
    req_id = request_id or f"REQ-{uuid.uuid4().hex[:12]}"
    tr_id = f"TR-{uuid.uuid4().hex[:16]}"
    sp_id = f"SP-{uuid.uuid4().hex[:8]}"
    set_trace_context(trace_id=tr_id, span_id=sp_id, request_id=req_id)
    return {"request_id": req_id, "trace_id": tr_id, "span_id": sp_id}


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures or mints distributed trace headers,
    binds them to thread-local / async context, and annotates response headers.
    """

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or f"REQ-{uuid.uuid4().hex[:12]}"
        trace_id = request.headers.get("X-Trace-ID") or f"TR-{uuid.uuid4().hex[:16]}"
        parent_span_id = request.headers.get("X-Span-ID")
        span_id = f"SP-{uuid.uuid4().hex[:8]}"

        # Bind context variables
        req_token = _request_id_ctx.set(req_id)
        tr_token = _trace_id_ctx.set(trace_id)
        sp_token = _span_id_ctx.set(span_id)

        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Span-ID"] = span_id
            if parent_span_id:
                response.headers["X-Parent-Span-ID"] = parent_span_id
            return response
        finally:
            _request_id_ctx.reset(req_token)
            _trace_id_ctx.reset(tr_token)
            _span_id_ctx.reset(sp_token)
