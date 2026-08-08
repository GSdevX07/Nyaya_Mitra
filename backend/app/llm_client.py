"""
llm_client.py — single choke-point for EVERY LLM call in Nyaya Mitra.

Provider chain
──────────────
  1. _call_primary()        → Groq cloud API (llama-3.3-70b-versatile)
                              Fast, free-tier generous, low latency.
                              Requires PRIMARY_API_KEY env var.

  2. _call_local_fallback() → Local Ollama (granite4:8b or llama3.2)
                              Works fully offline — demo-day insurance
                              against venue wifi failure.
                              Requires Ollama running on localhost:11434.

Rules:
  - No other file in the codebase should call an LLM API directly.
  - All calls go through generate(), which handles fallback transparently.
  - To swap the whole stack, only the two private functions change.

Environment:
  PRIMARY_API_KEY  — Groq API key (get free key at console.groq.com)
  OLLAMA_MODEL     — override the local model name (default: granite4:8b)
  OLLAMA_BASE_URL  — override Ollama host (default: http://localhost:11434)
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

# ── Configuration from environment ───────────────────────────────────────────

PRIMARY_API_KEY: str | None = os.getenv("PRIMARY_API_KEY")

# Groq endpoint + model
_GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL   = "llama-3.3-70b-versatile"

# Ollama local endpoint + model
_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "granite4:8b")

# Timeouts (seconds) — kept tight so demo never visibly hangs
_PRIMARY_TIMEOUT  = 8    # Groq is usually < 2 s; 8 s gives buffer on slow wifi
_FALLBACK_TIMEOUT = 30   # Local inference can be slower on weaker laptops


# ── Custom exception ──────────────────────────────────────────────────────────

class QuotaExceededError(Exception):
    """Raised when the primary provider returns HTTP 429 (rate limit)."""


# ── Private provider implementations ─────────────────────────────────────────

def _call_primary(prompt: str, system: str = "") -> str:
    """
    Call the Groq cloud API (OpenAI-compatible endpoint).

    Uses the chat/completions endpoint with llama-3.3-70b-versatile.
    Raises QuotaExceededError on HTTP 429, ConnectionError on network
    failure, and TimeoutError if the request exceeds _PRIMARY_TIMEOUT.
    """
    if not PRIMARY_API_KEY:
        raise ConnectionError(
            "PRIMARY_API_KEY env var is not set. "
            "Get a free key at https://console.groq.com and add it to .env"
        )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {PRIMARY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": _GROQ_MODEL,
        "messages": messages,
        "temperature": 0.3,      # Low temperature = consistent legal drafts
        "max_tokens": 1024,
    }

    try:
        response = requests.post(
            _GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=_PRIMARY_TIMEOUT,
        )
    except requests.exceptions.Timeout as exc:
        raise TimeoutError(f"Groq API timed out after {_PRIMARY_TIMEOUT}s") from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(f"Cannot reach Groq API: {exc}") from exc

    if response.status_code == 429:
        raise QuotaExceededError(
            f"Groq rate limit hit (HTTP 429): {response.text[:200]}"
        )
    if not response.ok:
        raise RuntimeError(
            f"Groq API returned HTTP {response.status_code}: {response.text[:300]}"
        )

    data = response.json()
    return data["choices"][0]["message"]["content"]


def _call_local_fallback(prompt: str, system: str = "") -> str:
    """
    Call the local Ollama model (offline demo-day insurance).

    Hits the Ollama /api/generate endpoint with stream=False.
    Model defaults to granite4:8b but is overridable via OLLAMA_MODEL env var.

    Ensure Ollama is running and the model is pulled before demo day:
        ollama pull granite4:8b
    """
    url = f"{_OLLAMA_BASE_URL}/api/generate"

    # Prepend system prompt inline since /api/generate is single-turn
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    payload = {
        "model": _OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=_FALLBACK_TIMEOUT,
        )
    except requests.exceptions.Timeout as exc:
        raise TimeoutError(
            f"Ollama timed out after {_FALLBACK_TIMEOUT}s — "
            "model may still be loading, try again"
        ) from exc
    except requests.exceptions.ConnectionError as exc:
        raise ConnectionError(
            f"Cannot reach Ollama at {_OLLAMA_BASE_URL}. "
            "Is Ollama running? Run: `ollama serve`"
        ) from exc

    if not response.ok:
        raise RuntimeError(
            f"Ollama returned HTTP {response.status_code}: {response.text[:300]}"
        )

    return response.json().get("response", "")


# ── Public interface ──────────────────────────────────────────────────────────

def generate(prompt: str, system: str = "", _override: str | None = None) -> str:
    """
    Generate an LLM response using the configured fallback chain.

    Args:
        prompt:    The user-turn content to send to the model.
        system:    Optional system prompt (role / constraints).
        _override: Test/cache escape hatch — if set, returns this value
                   immediately without calling any provider. Do NOT use
                   outside of tests or Phase 4 pre-computed cache.

    Returns:
        The model's text response as a plain string.

    Raises:
        RuntimeError: if both providers fail. Callers should catch this
                      and surface a user-facing error.

    Example:
        >>> from app.llm_client import generate
        >>> draft = generate(
        ...     prompt="Case facts: ...",
        ...     system="You are drafting a bail application.",
        ... )
    """
    # Test / pre-computed output escape hatch
    if _override is not None:
        logger.debug("generate(): returning override value (test/cache mode)")
        return _override

    # ── 1. Primary provider (Groq cloud) ─────────────────────────────────────
    try:
        logger.debug("generate(): calling primary provider (Groq / %s)", _GROQ_MODEL)
        result = _call_primary(prompt, system)
        logger.info("generate(): primary call succeeded")
        return result

    except (TimeoutError, QuotaExceededError, ConnectionError) as exc:
        logger.warning(
            "Primary LLM failed, switching to local fallback... [%s: %s]",
            type(exc).__name__, exc,
        )

    except Exception as exc:  # noqa: BLE001
        # Catch-all for unexpected provider errors (malformed response, etc.)
        logger.warning(
            "Primary LLM failed with unexpected error, switching to local fallback... "
            "[%s: %s]",
            type(exc).__name__, exc,
        )

    # ── 2. Local fallback (Ollama) ────────────────────────────────────────────
    try:
        logger.debug("generate(): calling local fallback (Ollama / %s)", _OLLAMA_MODEL)
        result = _call_local_fallback(prompt, system)
        logger.info("generate(): local fallback call succeeded")
        return result

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "generate(): local fallback also failed [%s: %s]",
            type(exc).__name__, exc,
        )
        raise RuntimeError(
            f"All LLM providers failed. Last error: {type(exc).__name__}: {exc}"
        ) from exc
