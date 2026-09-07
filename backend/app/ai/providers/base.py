"""
base.py — Base Provider Interface for Governed AI Service Layer.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from pydantic import BaseModel, Field

from app.ai.capabilities import TrustTier


class ProviderResult(BaseModel):
    content: str
    model_name: str
    model_version: Optional[str] = None
    provider_name: str
    trust_tier: TrustTier
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


class BaseProvider(ABC):
    provider_name: str
    trust_tier: TrustTier

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and reachable."""
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> ProviderResult:
        """Generate response content using the provider."""
        pass

    def estimate_tokens(self, prompt: str, completion: str = "") -> Tuple[int, int]:
        """Heuristic fallback token estimator (4 characters ~= 1 token)."""
        input_toks = max(1, round(len(prompt) / 4))
        output_toks = max(1, round(len(completion) / 4)) if completion else 0
        return input_toks, output_toks
