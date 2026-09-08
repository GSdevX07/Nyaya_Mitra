"""
pricing.py — Configurable Multi-Provider AI Token Pricing Registry.
===================================================================
Maintains transparent, auditable unit pricing for all AI providers and model tiers
in INR per 1,000 tokens. Eliminates hardcoded flat rates and supports real-world
billing calculations with effective date tracking.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ModelPricingRule:
    provider: str
    model_pattern: str  # Regex or wildcard matching model name
    input_cost_per_1k_inr: float
    output_cost_per_1k_inr: float
    effective_date: str = "2026-01-01"
    description: str = ""


# ── Canonical Pricing Table (Rates in Indian Rupees per 1,000 tokens) ───────────
PRICING_REGISTRY: List[ModelPricingRule] = [
    # Deterministic Extractive & Offline Guardrails (Zero compute cost)
    ModelPricingRule(
        provider="deterministic_fallback",
        model_pattern=r".*",
        input_cost_per_1k_inr=0.0,
        output_cost_per_1k_inr=0.0,
        description="Offline deterministic rules engine and safe guardrail fallback",
    ),
    # Local Self-Hosted Models (On-premise hardware, zero external API billing)
    ModelPricingRule(
        provider="ollama",
        model_pattern=r".*",
        input_cost_per_1k_inr=0.0,
        output_cost_per_1k_inr=0.0,
        description="Local on-premise Ollama instance",
    ),
    # Groq Cloud Production Models
    ModelPricingRule(
        provider="groq",
        model_pattern=r"(?i)llama-?3\.3-?70b",
        input_cost_per_1k_inr=0.049,
        output_cost_per_1k_inr=0.065,
        description="Groq LLaMA 3.3 70B Versatile",
    ),
    ModelPricingRule(
        provider="groq",
        model_pattern=r"(?i)llama-?3\.1-?8b",
        input_cost_per_1k_inr=0.008,
        output_cost_per_1k_inr=0.012,
        description="Groq LLaMA 3.1 8B Instant",
    ),
    ModelPricingRule(
        provider="groq",
        model_pattern=r"(?i)gpt-?oss-?120b",
        input_cost_per_1k_inr=0.040,
        output_cost_per_1k_inr=0.055,
        description="Groq GPT-OSS 120B Tier",
    ),
    ModelPricingRule(
        provider="groq",
        model_pattern=r"(?i)gpt-?oss-?20b",
        input_cost_per_1k_inr=0.010,
        output_cost_per_1k_inr=0.015,
        description="Groq GPT-OSS 20B Tier",
    ),
    ModelPricingRule(
        provider="groq",
        model_pattern=r"(?i)qwen",
        input_cost_per_1k_inr=0.015,
        output_cost_per_1k_inr=0.020,
        description="Groq Qwen 27B Tier",
    ),
    ModelPricingRule(
        provider="groq",
        model_pattern=r".*",
        input_cost_per_1k_inr=0.035,
        output_cost_per_1k_inr=0.045,
        description="Groq Default Tier",
    ),
    # IBM Watsonx AI Governance Models
    ModelPricingRule(
        provider="watsonx",
        model_pattern=r"(?i)granite-?3-?8b",
        input_cost_per_1k_inr=0.020,
        output_cost_per_1k_inr=0.030,
        description="IBM Granite 3 8B Instruct",
    ),
    ModelPricingRule(
        provider="watsonx",
        model_pattern=r".*",
        input_cost_per_1k_inr=0.025,
        output_cost_per_1k_inr=0.035,
        description="Watsonx Standard Governance Tier",
    ),
]

# Fallback default pricing if no rule matches
DEFAULT_PRICING_RULE = ModelPricingRule(
    provider="default",
    model_pattern=r".*",
    input_cost_per_1k_inr=0.025,
    output_cost_per_1k_inr=0.035,
    description="Universal Default Token Rate",
)


def get_model_pricing(provider: str, model_name: str = "") -> ModelPricingRule:
    """Resolve the specific pricing rule for a given provider and model identifier."""
    p_norm = (provider or "").lower().strip()
    m_norm = (model_name or "").strip()

    for rule in PRICING_REGISTRY:
        if rule.provider.lower() == p_norm:
            if re.search(rule.model_pattern, m_norm):
                return rule

    return DEFAULT_PRICING_RULE


def calculate_token_cost(
    provider: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """
    Calculate total execution cost in Indian Rupees (INR) from actual token telemetry.
    Returns value rounded to 5 decimal places.
    """
    pricing = get_model_pricing(provider, model_name)
    in_cost = (max(0, input_tokens) / 1000.0) * pricing.input_cost_per_1k_inr
    out_cost = (max(0, output_tokens) / 1000.0) * pricing.output_cost_per_1k_inr
    return round(in_cost + out_cost, 5)
