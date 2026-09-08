"""Legacy compatibility wrapper for Nyaya Mitra model calls.

ALL generative model invocations are strictly routed through the Governed AI Gateway
(app.ai.get_ai_gateway()). Direct SDK calls to Watsonx, Groq, Ollama, or unmonitored
endpoints have been retired to satisfy the Stage 12 single governed AI architecture.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Re-export OCR tools from dedicated service for backward compatibility
from app.services.ocr_service import (
    segment_text_lines,
    _segment_text_lines,
    ocr_image_via_easyocr,
)

# Suppress verbose oneDNN and TensorFlow informational messages
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore")

# Load backend/.env or cwd .env
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
load_dotenv()

_last_provider: str = "not-called"


def get_last_provider() -> str:
    """Return the provider or model that produced the last response."""
    try:
        from app.ai import get_ai_gateway

        gw = get_ai_gateway()
        if gw.last_provider_name and gw.last_provider_name != "not-called":
            return gw.last_model_name or gw.last_provider_name
    except Exception:
        pass
    return _last_provider


def generate(prompt: str, system: str = "", _override: Optional[str] = None) -> str:
    """Generate through the Governed AI Gateway.

    Enforces capability policies, rate limits, PII redaction, prompt injection defense,
    dynamic model pricing, and tamper-evident audit logging.
    Direct un-governed SDK calls are strictly prohibited.
    """
    global _last_provider
    if _override is not None:
        _last_provider = "test override"
        return _override

    try:
        from app.ai import get_ai_gateway, GatewayRequest, AICapability

        gateway = get_ai_gateway()
        req = GatewayRequest(
            capability=AICapability.PLAIN_LANGUAGE_EXPLANATION,
            prompt=prompt,
            system_instruction=system,
            user_id="legacy_llm_client",
            user_role="SYSTEM",
        )
        res = gateway.execute(req)
        _last_provider = res.model_name or res.provider_name
        if res.content:
            return res.content
    except Exception as exc:
        _last_provider = "governed-fallback"
        return os.getenv(
            "LLM_UNAVAILABLE_MESSAGE",
            "AI generation is unavailable. A qualified human reviewer must complete this step.",
        )

    _last_provider = "governed-fallback"
    return os.getenv(
        "LLM_UNAVAILABLE_MESSAGE",
        "AI generation is unavailable. A qualified human reviewer must complete this step.",
    )
