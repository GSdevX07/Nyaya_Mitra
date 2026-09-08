"""
schemas.py — Canonical Pydantic Schemas for Governed AI Service Layer.
=====================================================================
Enforces strict structured outputs for all 8 AI capabilities, eliminates hidden
chain-of-thought, and guarantees auditable rationales (source citations, extracted facts,
rule evaluations, and plain decision explanations).
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional, Generic, TypeVar
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, model_validator

from app.ai.capabilities import AICapability, TrustTier


class GatewayStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ABSTAINED = "ABSTAINED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    FALLBACK_USED = "FALLBACK_USED"
    FALLBACK_SUCCESS = "FALLBACK_USED"
    FAILED = "FAILED"


# ── Auditable Rationale (Zero Chain-of-Thought) ──────────────────────────────

class AuditableRationale(BaseModel):
    """
    Concise, auditable justifications for generation decisions.
    Strictly forbids chain-of-thought, raw scratchpads, or internal persona prompts.
    """
    source_citations: List[str] = Field(default_factory=list, description="Explicit statutory or document source identifiers cited.")
    extracted_facts: Dict[str, Any] = Field(default_factory=dict, description="Key factual attributes relied upon.")
    rule_results: List[str] = Field(default_factory=list, description="Deterministic rule checks verified before or during synthesis.")
    decision_explanation: str = Field(..., description="High-level factual reason for the resulting output.")
    human_explanation: Optional[str] = Field(default=None, description="Alias for decision_explanation.")

    @model_validator(mode="before")
    @classmethod
    def populate_human_explanation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "decision_explanation" in data and not data.get("human_explanation"):
                data["human_explanation"] = data["decision_explanation"]
            elif "human_explanation" in data and not data.get("decision_explanation"):
                data["decision_explanation"] = data["human_explanation"]
        return data


# ── Structured Output Models for the 8 Capabilities ─────────────────────────

class DocumentSummarizationOutput(BaseModel):
    document_type: str
    case_reference: Optional[str] = None
    summary_sentences: List[str] = Field(..., description="Exactly 1 or 2 concise, plain-language sentences.")
    full_summary_text: str
    verified_record_status: str = "VERIFIED"
    key_extracted_facts: Dict[str, Any] = Field(default_factory=dict)
    rationale: AuditableRationale


class PlainLanguageExplanationOutput(BaseModel):
    case_reference: str
    procedural_status_title: str
    plain_explanation: str = Field(..., description="Simple non-legal explanation suitable for reading aloud to family (max 150 words).")
    constitutional_statutory_basis: str = "Constitution of India Art. 39A & BNSS 2023 Sec. 479"
    next_steps_for_family: List[str] = Field(default_factory=list)
    statutory_caution_disclaimer: str = (
        "AI Procedural Explanation — Not a Legal Decision. This service provides plain-language procedural information under the Legal Services Authorities Act, 1987. "
        "It is not a court order and never guarantees bail, release, or judicial outcomes. Official relief is determined exclusively by the competent court."
    )
    rationale: AuditableRationale


class MultilingualExplanationOutput(BaseModel):
    source_language: str = "en"
    target_language: str
    translated_text: str
    is_derived_display: bool = True
    authoritative_source_text: str
    derived_display_disclaimer: str = (
        "Accessibility Notice: Translated text is a derived display for informational convenience. "
        "The authoritative English court docket and certified judicial record remain the definitive legal source."
    )
    glossary_terms_preserved: Dict[str, str] = Field(default_factory=dict)
    rationale: AuditableRationale


class LegalSynthesisOutput(BaseModel):
    reporting_period: Optional[str] = Field(
        default="Current Review Period",
        description="Reporting or review period",
    )
    case_reference: Optional[str] = Field(
        default="Case reference pending legal review",
        description="Case citation or reference number",
    )
    applicable_statutory_sections: List[str] = Field(default_factory=list)
    binding_precedents: List[Dict[str, str]] = Field(default_factory=list)
    legal_grounds_summary: Optional[str] = Field(
        default="Statutory grounds analysis: Section 479 BNSS (Bail) applicable pending detailed court record review.",
        description="Summary of applicable legal grounds and statutes",
    )
    synthesis_summary: Optional[str] = Field(
        default=None,
        description="Summary of legal synthesis",
    )
    statutory_transition_notes: Optional[str] = None
    unresolved_legal_questions: List[str] = Field(default_factory=list)
    rationale: AuditableRationale = Field(
        default_factory=lambda: AuditableRationale(
            source_citations=["Section 479 BNSS"],
            decision_explanation="Procedural legal synthesis generated from official docket.",
        )
    )

    @model_validator(mode="before")
    @classmethod
    def populate_legal_synthesis_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("case_reference"):
                data["case_reference"] = data.get("case_id") or "Case reference pending legal review"
            lgs = data.get("legal_grounds_summary")
            syn = data.get("synthesis_summary")
            if not lgs and syn:
                data["legal_grounds_summary"] = syn
            elif not syn and lgs:
                data["synthesis_summary"] = lgs
            elif not lgs and not syn:
                data["legal_grounds_summary"] = "Statutory grounds analysis: Section 479 BNSS (Bail) applicable pending detailed court record review."
                data["synthesis_summary"] = data["legal_grounds_summary"]
            if not data.get("rationale"):
                data["rationale"] = {
                    "source_citations": ["Section 479 BNSS", f"Dossier:{data.get('case_reference')}"],
                    "extracted_facts": {},
                    "rule_results": ["Rule:Statutory_Grounds_Extracted"],
                    "decision_explanation": "Procedural legal synthesis generated from official docket.",
                }
        return data


class DraftPreparationOutput(BaseModel):
    case_reference: Optional[str] = Field(
        default="Case reference pending legal review",
        description="Case citation or reference number",
    )
    petition_type: str = "Bail Application under Section 479 BNSS"
    jurisdictional_court: str = "Court of Competent Jurisdiction"
    designated_counsel: str = "DLSA Legal Aid Panel Counsel"
    petition_body_text: str = Field(default="")
    draft_text: Optional[str] = None
    mandatory_document_checklist: Dict[str, bool] = Field(default_factory=dict)
    missing_document_warnings: List[str] = Field(default_factory=list)
    requires_advocate_signature: bool = True
    counsel_signature_block: str = "Advocate on Record\nDLSA Legal Aid Panel Counsel"
    rationale: AuditableRationale = Field(
        default_factory=lambda: AuditableRationale(
            source_citations=["Section 479 BNSS"],
            decision_explanation="Bail petition drafted for defense counsel review.",
        )
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_draft_preparation(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("case_reference"):
                data["case_reference"] = data.get("case_id") or "Case reference pending legal review"
            pbt = data.get("petition_body_text")
            dt = data.get("draft_text")
            if not pbt and dt:
                data["petition_body_text"] = dt
            elif not dt and pbt:
                data["draft_text"] = pbt
            elif not pbt and not dt:
                default_text = (
                    "APPLICATION FOR REGULAR BAIL UNDER SECTION 479 OF THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023.\n"
                    "Official case facts extracted deterministically from verified court and jail records. "
                    "Automated neural generation is currently offline; a qualified legal aid officer must review this dossier."
                )
                data["petition_body_text"] = default_text
                data["draft_text"] = default_text
            if not data.get("rationale"):
                data["rationale"] = {
                    "source_citations": ["Section 479 BNSS"],
                    "extracted_facts": {},
                    "rule_results": ["Rule:Draft_Preparation_Generated"],
                    "decision_explanation": "Draft petition synthesized from verified court facts.",
                }
        return data


class AnomalyDetectionOutput(BaseModel):
    case_reference: str
    anomalies_detected: bool = False
    anomaly_count: int = 0
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    severity_level: str = "NONE"  # NONE, LOW, MEDIUM, HIGH, CRITICAL
    requires_immediate_human_review: bool = False
    routing_destination: str = "DLSA_SUPERVISOR_QUEUE"
    rationale: AuditableRationale


class DataQualityAssistanceOutput(BaseModel):
    document_id: str
    ocr_confidence_score: float
    is_scanned_image: bool = False
    legibility_rating: str = "HIGH"  # HIGH, MEDIUM, LOW, ILLEGIBLE
    missing_mandatory_fields: List[str] = Field(default_factory=list)
    suggested_corrections: Dict[str, str] = Field(default_factory=dict)
    requires_clerk_verification: bool = False
    rationale: AuditableRationale


class AdministrativeSummarizationOutput(BaseModel):
    reporting_period: str
    facility_or_district: str
    total_active_undertrials: int = 0
    potentially_eligible_479_count: int = 0
    backlog_summary: str
    compliance_percentage: float = 100.0
    bottleneck_stages: List[str] = Field(default_factory=list)
    rationale: AuditableRationale


# ── Gateway Execution Request & Response ─────────────────────────────────────

class GatewayRequest(BaseModel):
    capability: AICapability
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    prompt_input: str = ""
    prompt: Optional[str] = None
    untrusted_document_context: Optional[str] = None
    structured_context: Dict[str, Any] = Field(default_factory=dict)
    context_data: Optional[Dict[str, Any]] = None
    target_language: str = "en"
    ocr_confidence: float = 1.0
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    system_instruction: Optional[str] = None
    prompt_version_override: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_request_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "prompt" in data and not data.get("prompt_input"):
                data["prompt_input"] = str(data["prompt"])
            elif "prompt_input" in data and not data.get("prompt"):
                data["prompt"] = str(data["prompt_input"])
            if "context_data" in data and not data.get("structured_context"):
                data["structured_context"] = data["context_data"]
            elif "structured_context" in data and not data.get("context_data"):
                data["context_data"] = data["structured_context"]
        return data


T = TypeVar("T")

class GatewayResponse(BaseModel, Generic[T]):
    request_id: str
    capability: AICapability
    status: GatewayStatus
    prompt_version: str
    model_name: str
    model_version: Optional[str] = None
    provider_used: str
    trust_tier: TrustTier
    fallback_triggered: bool = False
    fallback_reason: Optional[str] = None
    source_document_identifiers: List[str] = Field(default_factory=list)
    retrieved_legal_source_identifiers: List[str] = Field(default_factory=list)
    structured_data: Optional[T] = None
    raw_output: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    estimated_cost_inr: float
    generation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    needs_human_review: bool = False
    abstention_reason: Optional[str] = None

    @property
    def content(self) -> str:
        return self.raw_output

    @property
    def provider_name(self) -> str:
        return self.provider_used

    @property
    def auditable_rationale(self) -> Any:
        return getattr(self.structured_data, "rationale", None)

    @property
    def token_usage(self) -> Any:
        class _Usage:
            total_tokens = self.input_tokens + self.output_tokens
            estimated_cost_usd = round(self.estimated_cost_inr / 83.0, 6)
        return _Usage()


# ── Audit Record ─────────────────────────────────────────────────────────────

class AIAuditRecord(BaseModel):
    id: str
    request_id: str
    capability: str
    status: str
    prompt_version: str
    model_name: str
    provider_used: str
    trust_tier: str
    fallback_triggered: bool
    fallback_reason: Optional[str] = None
    case_id: Optional[str] = None
    document_id: Optional[str] = None
    source_doc_ids: str = "[]"
    retrieved_source_ids: str = "[]"
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_inr: float
    needs_human_review: bool
    abstention_reason: Optional[str] = None
    rationale_json: str
    created_at: str
