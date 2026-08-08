"""
llm_client.py — single choke-point for EVERY LLM call in Nyaya Mitra.

Rules:
  - No other file in the codebase should call an LLM SDK directly.
  - All calls go through generate(), which handles fallback transparently.
  - To switch the whole stack (e.g., watsonx → Groq), only this file changes.

Fallback chain
  1. _call_primary()      — cloud provider (IBM watsonx.ai by default)
  2. _call_local_fallback() — local Ollama model (Granite) when primary is unreachable

See Section 3 of Nyaya_Mitra_Master_Roadmap_v2.md for the full rationale.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception — keeps the public interface clean
# ---------------------------------------------------------------------------

class QuotaExceededError(Exception):
    """Raised when the primary LLM provider returns a quota / rate-limit error."""


# ---------------------------------------------------------------------------
# Private provider implementations (stub — fill these in per Section 3 / Phase 2)
# ---------------------------------------------------------------------------

def _call_primary(prompt: str, system: str = "") -> str:
    """
    Call the primary cloud LLM (IBM watsonx.ai, Path A default).

    TODO: Implement with the ibm-watsonx-ai SDK:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        credentials = Credentials(
            url=os.environ["WATSONX_URL"],
            api_key=os.environ["WATSONX_API_KEY"],
        )
        model = ModelInference(
            model_id="ibm/granite-13b-instruct-v2",
            credentials=credentials,
            project_id=os.environ["WATSONX_PROJECT_ID"],
        )
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = model.chat(messages=messages)
        return response["choices"][0]["message"]["content"]

    Raises:
        TimeoutError:        if the request times out (propagate as-is).
        QuotaExceededError:  if the provider returns HTTP 429 / quota exceeded.
        ConnectionError:     if the provider is unreachable.
    """
    # TODO: replace with real watsonx.ai call (see docstring above)
    raise NotImplementedError(
        "_call_primary is not yet implemented. "
        "Configure watsonx credentials and fill in the implementation."
    )


def _call_local_fallback(prompt: str, system: str = "") -> str:
    """
    Call the local Ollama Granite model (Path A fallback / Path B pivot point).

    TODO: Implement with the ollama Python SDK:
        import ollama
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = ollama.chat(
            model=os.environ.get("OLLAMA_MODEL", "granite4:8b"),
            messages=messages,
        )
        return response["message"]["content"]

    If pivoting to Path B entirely (Groq / Gemini), replace this function's
    body with the appropriate SDK call — the generate() function above needs
    no changes at all.

    Raises:
        RuntimeError: if Ollama is also unreachable (should be treated as a
                      hard failure — surface to the caller rather than silently
                      returning an empty string).
    """
    # TODO: replace with real Ollama call (see docstring above)
    raise NotImplementedError(
        "_call_local_fallback is not yet implemented. "
        "Ensure Ollama is running and the model is pulled: `ollama pull granite4:8b`"
    )


# ---------------------------------------------------------------------------
# Public interface — the ONLY function the rest of the codebase should import
# ---------------------------------------------------------------------------

def generate(prompt: str, system: str = "", _override: Optional[str] = None) -> str:
    """
    Generate an LLM response using the configured fallback chain.

    Args:
        prompt:    The user-turn content to send to the model.
        system:    An optional system-prompt string that sets the model's role
                   or constraints (e.g., the Drafting Agent's instruction block).
        _override: Internal escape hatch for unit tests — if set, return this
                   value immediately without calling any provider. Do NOT use
                   outside of tests.

    Returns:
        The model's text response as a plain string.

    Raises:
        RuntimeError: if every provider in the fallback chain fails. Callers
                      should catch this and surface a user-facing error rather
                      than crashing silently.

    Example:
        >>> from app.llm_client import generate
        >>> draft = generate(
        ...     prompt="Case facts: ...",
        ...     system="You are drafting a bail application for a legal-aid lawyer's review.",
        ... )
    """
    # Test / pre-computed output escape hatch (Phase 4 caching strategy)
    if _override is not None:
        logger.debug("generate(): returning override value (test / cache mode)")
        return _override

    # ── Primary provider (cloud) ──────────────────────────────────────────
    try:
        logger.debug("generate(): attempting primary cloud LLM")
        result = _call_primary(prompt, system)
        logger.info("generate(): primary call succeeded")
        return result

    except (TimeoutError, QuotaExceededError, ConnectionError) as exc:
        # Expected transient failures → fall through to local model
        logger.warning(
            "generate(): primary LLM unavailable (%s: %s) — "
            "falling back to local model",
            type(exc).__name__,
            exc,
        )

    except NotImplementedError:
        # Stub not yet wired up — fall through so the project still runs
        # during Phase 0/1 development before provider details are filled in
        logger.warning(
            "generate(): _call_primary is a stub — falling back to local model"
        )

    # ── Local fallback (Ollama / Granite) ─────────────────────────────────
    try:
        logger.debug("generate(): attempting local Ollama fallback")
        result = _call_local_fallback(prompt, system)
        logger.info("generate(): local fallback call succeeded")
        return result

    except NotImplementedError:
        # Both stubs unimplemented — give a helpful dev-mode placeholder
        logger.warning(
            "generate(): _call_local_fallback is also a stub — "
            "returning placeholder response for development"
        )
        return (
            "[DEV PLACEHOLDER] LLM providers not yet configured. "
            "Implement _call_primary() and _call_local_fallback() in llm_client.py."
        )

    except Exception as exc:  # noqa: BLE001
        # Local model failed for a non-stub reason — this is a hard failure
        logger.error(
            "generate(): local fallback also failed (%s: %s)",
            type(exc).__name__,
            exc,
        )
        raise RuntimeError(
            f"All LLM providers failed. Last error: {type(exc).__name__}: {exc}"
        ) from exc
