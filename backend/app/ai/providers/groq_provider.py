"""
groq_provider.py — Isolated Groq Model Provider with Model Fallback & CoT Stripping.
"""

from __future__ import annotations
import os
import re
import time
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load backend/.env
_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
load_dotenv()

from app.ai.capabilities import TrustTier
from app.ai.providers.base import BaseProvider, ProviderResult


class GroqProvider(BaseProvider):
    provider_name = "groq"
    trust_tier = TrustTier.CLOUD_GENAI

    @property
    def candidate_models(self) -> List[str]:
        configured_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        models = [configured_model]
        for m in ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]:
            if m not in models:
                models.append(m)
        return models

    def is_available(self) -> bool:
        key = os.getenv("GROQ_API_KEY", "")
        return bool(key and len(key.strip()) > 10)

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> ProviderResult:
        if not self.is_available():
            raise RuntimeError("Groq API key not configured.")

        api_key = os.getenv("GROQ_API_KEY")
        client = Groq(api_key=api_key)
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        timeout = float(os.getenv("GROQ_TIMEOUT_SECONDS", "15"))

        last_err: Optional[Exception] = None
        start_t = time.perf_counter()

        for model in self.candidate_models:
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                raw_content = completion.choices[0].message.content or ""
                latency = (time.perf_counter() - start_t) * 1000

                # Strict CoT Stripping: Discard any <think> tags or reasoning traces
                clean_content = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
                if not clean_content and raw_content:
                    clean_content = raw_content.strip()

                usage = getattr(completion, "usage", None)
                if usage:
                    in_toks = getattr(usage, "prompt_tokens", 0) or 0
                    out_toks = getattr(usage, "completion_tokens", 0) or 0
                else:
                    in_toks, out_toks = self.estimate_tokens(prompt, clean_content)

                return ProviderResult(
                    content=clean_content,
                    model_name=f"groq/{model}",
                    model_version=model,
                    provider_name=self.provider_name,
                    trust_tier=self.trust_tier,
                    input_tokens=in_toks,
                    output_tokens=out_toks,
                    latency_ms=round(latency, 2),
                )
            except Exception as exc:
                last_err = exc
                continue

        raise RuntimeError(f"Groq generation failed across models {self.candidate_models}: {last_err}")
