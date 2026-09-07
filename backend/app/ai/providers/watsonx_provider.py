"""
watsonx_provider.py — Isolated IBM watsonx.ai Provider.
"""

from __future__ import annotations
import os
import time
import requests

from app.ai.capabilities import TrustTier
from app.ai.providers.base import BaseProvider, ProviderResult


class WatsonxProvider(BaseProvider):
    provider_name = "watsonx"
    trust_tier = TrustTier.CLOUD_GENAI

    def is_available(self) -> bool:
        return bool(
            os.getenv("WATSONX_API_KEY")
            and os.getenv("WATSONX_PROJECT_ID")
            and os.getenv("WATSONX_MODEL_ID")
            and os.getenv("WATSONX_URL")
        )

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> ProviderResult:
        if not self.is_available():
            raise RuntimeError("Watsonx credentials not configured.")

        api_key = os.getenv("WATSONX_API_KEY")
        project_id = os.getenv("WATSONX_PROJECT_ID")
        model_id = os.getenv("WATSONX_MODEL_ID")
        endpoint = os.getenv("WATSONX_URL", "").rstrip("/")
        timeout = float(os.getenv("WATSONX_TIMEOUT_SECONDS", "30"))

        start_t = time.perf_counter()
        tok_res = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": api_key},
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            timeout=timeout,
        )
        tok_res.raise_for_status()
        access_token = tok_res.json()["access_token"]

        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        res = requests.post(
            f"{endpoint}/ml/v1/text/chat",
            params={"version": os.getenv("WATSONX_API_VERSION", "2024-05-31")},
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "Accept": "application/json"},
            json={
                "model_id": model_id,
                "project_id": project_id,
                "messages": messages,
                "parameters": {"temperature": temperature, "max_tokens": max_tokens},
            },
            timeout=timeout,
        )
        res.raise_for_status()
        payload = res.json()
        latency = (time.perf_counter() - start_t) * 1000

        content = payload.get("choices", [{}])[0].get("message", {}).get("content")
        if isinstance(content, list):
            content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("watsonx response did not contain text")

        clean_text = content.strip()
        in_toks, out_toks = self.estimate_tokens(prompt, clean_text)

        return ProviderResult(
            content=clean_text,
            model_name=f"watsonx/{model_id}",
            model_version=model_id,
            provider_name=self.provider_name,
            trust_tier=self.trust_tier,
            input_tokens=in_toks,
            output_tokens=out_toks,
            latency_ms=round(latency, 2),
        )
