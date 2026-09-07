"""
ollama_provider.py — Isolated On-Premise Ollama Local Provider.
"""

from __future__ import annotations
import os
import time
import requests

from app.ai.capabilities import TrustTier
from app.ai.providers.base import BaseProvider, ProviderResult


class OllamaProvider(BaseProvider):
    provider_name = "ollama"
    trust_tier = TrustTier.LOCAL_GENAI

    def is_available(self) -> bool:
        return bool(os.getenv("OLLAMA_MODEL"))

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> ProviderResult:
        model = os.getenv("OLLAMA_MODEL")
        if not model:
            raise RuntimeError("Ollama model not configured.")

        url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "45"))
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]

        start_t = time.perf_counter()
        res = requests.post(
            url,
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=timeout,
        )
        res.raise_for_status()
        payload = res.json()
        latency = (time.perf_counter() - start_t) * 1000

        content = payload.get("message", {}).get("content") or payload.get("response") or ""
        clean_text = content.strip()
        if not clean_text:
            raise RuntimeError("Ollama returned empty response.")

        in_toks, out_toks = self.estimate_tokens(prompt, clean_text)

        return ProviderResult(
            content=clean_text,
            model_name=f"ollama/{model}",
            model_version=model,
            provider_name=self.provider_name,
            trust_tier=self.trust_tier,
            input_tokens=in_toks,
            output_tokens=out_toks,
            latency_ms=round(latency, 2),
        )
