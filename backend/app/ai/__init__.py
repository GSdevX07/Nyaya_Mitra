"""
backend/app/ai — Governed AI Service Layer Package.
"""

from app.ai.capabilities import AICapability, TrustTier, CapabilityPolicy, get_capability_policy
from app.ai.schemas import (
    GatewayStatus,
    GatewayRequest,
    GatewayResponse,
    AuditableRationale,
    DocumentSummarizationOutput,
    PlainLanguageExplanationOutput,
    MultilingualExplanationOutput,
    LegalSynthesisOutput,
    DraftPreparationOutput,
    AnomalyDetectionOutput,
    DataQualityAssistanceOutput,
    AdministrativeSummarizationOutput,
)
from app.ai.policies import redact_sensitive_pii, detect_prompt_injection, build_secure_document_boundary
from app.ai.gateway import AIGateway, get_ai_gateway
from app.ai.pricing import calculate_token_cost, get_model_pricing, ModelPricingRule

__all__ = [
    "AICapability",
    "TrustTier",
    "CapabilityPolicy",
    "get_capability_policy",
    "GatewayStatus",
    "GatewayRequest",
    "GatewayResponse",
    "AuditableRationale",
    "DocumentSummarizationOutput",
    "PlainLanguageExplanationOutput",
    "MultilingualExplanationOutput",
    "LegalSynthesisOutput",
    "DraftPreparationOutput",
    "AnomalyDetectionOutput",
    "DataQualityAssistanceOutput",
    "AdministrativeSummarizationOutput",
    "redact_sensitive_pii",
    "detect_prompt_injection",
    "build_secure_document_boundary",
    "AIGateway",
    "get_ai_gateway",
    "calculate_token_cost",
    "get_model_pricing",
    "ModelPricingRule",
]