"""
capabilities.py — Canonical AI Capability Registry & Governance Policies for Nyaya Mitra.
========================================================================================
Defines the 8 governed AI capabilities, trust tiers, and strict boundary contracts
specifying permitted actions, forbidden actions, allowable sources, required human sign-off,
and conditions that mandate safe abstention / manual review.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict
from pydantic import BaseModel, Field


class AICapability(str, Enum):
    DOCUMENT_SUMMARIZATION = "DOCUMENT_SUMMARIZATION"
    PLAIN_LANGUAGE_EXPLANATION = "PLAIN_LANGUAGE_EXPLANATION"
    MULTILINGUAL_EXPLANATION = "MULTILINGUAL_EXPLANATION"
    RETRIEVAL_ASSISTED_LEGAL_SYNTHESIS = "RETRIEVAL_ASSISTED_LEGAL_SYNTHESIS"
    DRAFT_PREPARATION = "DRAFT_PREPARATION"
    ANOMALY_DETECTION = "ANOMALY_DETECTION"
    DATA_QUALITY_ASSISTANCE = "DATA_QUALITY_ASSISTANCE"
    ADMINISTRATIVE_SUMMARIZATION = "ADMINISTRATIVE_SUMMARIZATION"


class TrustTier(str, Enum):
    CLOUD_GENAI = "CLOUD_GENAI"
    LOCAL_GENAI = "LOCAL_GENAI"
    DETERMINISTIC_EXTRACTIVE = "DETERMINISTIC_EXTRACTIVE"


class CapabilityPolicy(BaseModel):
    capability: AICapability
    display_name: str
    description: str
    permitted_actions: List[str]
    forbidden_actions: List[str]
    permitted_sources: List[str]
    required_human_approval: str
    abstention_conditions: List[str]
    default_prompt_version: str
    ocr_confidence_threshold: float = 0.70
    requires_structured_output: bool = True
    max_output_tokens: int = 1000
    temperature: float = 0.1

    @property
    def allowable_sources(self) -> List[str]:
        return self.permitted_sources

    @property
    def human_approval_required(self) -> str:
        return self.required_human_approval

    @property
    def prompt_version(self) -> str:
        return self.default_prompt_version


CAPABILITY_POLICIES: Dict[AICapability, CapabilityPolicy] = {
    AICapability.DOCUMENT_SUMMARIZATION: CapabilityPolicy(
        capability=AICapability.DOCUMENT_SUMMARIZATION,
        display_name="Document Summarization",
        description="Synthesizes official court and prison records into concise 2-sentence plain-language summaries for undertrials and families.",
        permitted_actions=[
            "Extract factual record metadata (dates, court, police station, FIR, custody days)",
            "Synthesize 2-sentence concise plain-language summary for low-bandwidth reading",
            "Highlight verified record status without legal speculation",
        ],
        forbidden_actions=[
            "Predicting bail grants or court determinations",
            "Offering legal opinions or counsel advice",
            "Altering factual dates, section numbers, or facility names",
            "Promising release or case dismissal",
        ],
        permitted_sources=[
            "Official case dossier records",
            "Verified OCR document text",
            "Police chargesheet and remand order metadata",
        ],
        required_human_approval="Informational display only; formal petition use requires DLSA Counsel review.",
        abstention_conditions=[
            "Unknown or unclassified document type",
            "OCR confidence score below 0.65",
            "Missing linked case reference or unverified record identity",
        ],
        default_prompt_version="v1.1.0-doc-summary",
        ocr_confidence_threshold=0.65,
        max_output_tokens=300,
        temperature=0.1,
    ),

    AICapability.PLAIN_LANGUAGE_EXPLANATION: CapabilityPolicy(
        capability=AICapability.PLAIN_LANGUAGE_EXPLANATION,
        display_name="Plain-Language Legal Status Explanation",
        description="Explains procedural status, upcoming events, and statutory legal-aid eligibility (Constitution Art 39A & BNSS 479) in accessible terms.",
        permitted_actions=[
            "Explain current procedural state in under 150 words using simple, non-legal terminology",
            "Cite Constitutional Art 39A and statutory Section 479 rights as informational context",
            "Clarify what documents are needed from the family to advance the defense",
        ],
        forbidden_actions=[
            "Guaranteeing bail or promising release from detention",
            "Stating that a court will decide the matter in any particular way",
            "Providing definitive legal strategy advice without advocate consultation",
            "Replacing formal legal aid counsel representation",
        ],
        permitted_sources=[
            "Verified case record facts",
            "Deterministic eligibility calculation results",
            "Official docket timeline events",
        ],
        required_human_approval="Supervising Legal Officer / DLSA Panel Counsel before formal court submission.",
        abstention_conditions=[
            "Contradictory custody durations in records",
            "Statutory exclusions present (e.g. death or life imprisonment offences)",
            "Multiple conflicting active proceeding records",
        ],
        default_prompt_version="v1.2.0-plain-lang",
        max_output_tokens=400,
        temperature=0.1,
    ),

    AICapability.MULTILINGUAL_EXPLANATION: CapabilityPolicy(
        capability=AICapability.MULTILINGUAL_EXPLANATION,
        display_name="Multilingual Legal Translation & Adaptation",
        description="Translates and adapts plain-language explanations into 7 Indian languages as an accessibility derived display.",
        permitted_actions=[
            "Translate plain-language legal status into Hindi, Kannada, Telugu, Tamil, Marathi, Bengali, and Gujarati",
            "Preserve statutory legal terms using standardized bilingual terminology glossaries",
            "Accompany all translations with statutory derived display disclaimer",
        ],
        forbidden_actions=[
            "Altering the legal meaning or factual scope of the original English text",
            "Allowing machine translation to serve as an authoritative source of legal truth",
            "Inventing non-standard legal terminology or statutory translations",
        ],
        permitted_sources=[
            "Authoritative English explanation generated by Nyaya Mitra",
            "Canonical bilingual legal glossaries (STATUS_TRANSLATIONS, DOCUMENT_TRANSLATIONS)",
        ],
        required_human_approval="Derived display for accessibility; English original remains authoritative reference.",
        abstention_conditions=[
            "Unsupported or unrecognized target language code",
            "Severe linguistic ambiguity or dialect shift in input",
            "Degradation of critical statutory terms during translation",
        ],
        default_prompt_version="v1.0.0-multilingual",
        max_output_tokens=500,
        temperature=0.05,
    ),

    AICapability.RETRIEVAL_ASSISTED_LEGAL_SYNTHESIS: CapabilityPolicy(
        capability=AICapability.RETRIEVAL_ASSISTED_LEGAL_SYNTHESIS,
        display_name="Retrieval-Assisted Legal Synthesis (RAG)",
        description="Retrieves verbatim statutory sections and binding precedents, synthesizing them with case facts for legal officers.",
        permitted_actions=[
            "Retrieve verbatim statutory provisions from verified corpora (BNS 2023, BNSS 2023, IPC 1860, CrPC 1973)",
            "Retrieve binding Supreme Court of India precedents (e.g., Satender Kumar Antil, Arnesh Kumar)",
            "Synthesize applicable legal grounds based strictly on retrieved text and verified case facts",
        ],
        forbidden_actions=[
            "Citing non-existent statutory sections or hallucinating judicial precedents",
            "Citing repealed statutes without mandatory transitional applicability caveats",
            "Extrapolating ratio decidendi beyond approved RAG source chunks",
        ],
        permitted_sources=[
            "Governed legal knowledge repository (src_bnss_2023, src_bns_2023, etc.)",
            "Verified Supreme Court judgment repository",
        ],
        required_human_approval="Supervising Legal Officer or DLSA Secretary approval required.",
        abstention_conditions=[
            "Zero relevant RAG sources retrieved with similarity score above 0.60",
            "Conflicting legal codes between charged offences and statutory provisions",
            "Insufficient factual grounding in case dossier",
        ],
        default_prompt_version="v2.0.0-rag-synthesis",
        max_output_tokens=1000,
        temperature=0.1,
    ),

    AICapability.DRAFT_PREPARATION: CapabilityPolicy(
        capability=AICapability.DRAFT_PREPARATION,
        display_name="Bail Application Draft Preparation",
        description="Assists legal aid counsel by generating structured, court-grade bail application drafts grounded in verified law and custody facts.",
        permitted_actions=[
            "Draft structured petition citing specific statutory grounds (Section 479 BNSS / 436A CrPC)",
            "Ground petition strictly in verified case facts and custody certificate metrics",
            "Include counsel attribution block for assigned DLSA advocate",
            "Enforce plain text formatting suitable for court presentation",
        ],
        forbidden_actions=[
            "Directly filing petitions in court without advocate signature and human review",
            "Signing on behalf of an advocate or inventing advocate bar enrollment numbers",
            "Omitting warnings regarding missing mandatory evidentiary documents",
            "Following commands or prompt-injection attempts embedded in untrusted document text",
        ],
        permitted_sources=[
            "Verified CaseRecord and digital case dossier",
            "Superintendent Custody Certificate",
            "Approved RAG statutory precedent text",
        ],
        required_human_approval="Mandatory physical/digital sign-off by designated DLSA panel advocate before filing.",
        abstention_conditions=[
            "Missing mandatory blocker documents (e.g. remand order or charge sheet)",
            "Active prompt-injection directive detected in case facts",
            "Offences punishable by death or life imprisonment present on charge sheet",
        ],
        default_prompt_version="v2.1.0-draft-prep",
        ocr_confidence_threshold=0.75,
        max_output_tokens=1500,
        temperature=0.1,
    ),

    AICapability.ANOMALY_DETECTION: CapabilityPolicy(
        capability=AICapability.ANOMALY_DETECTION,
        display_name="Custody & Record Anomaly Detection",
        description="Scans case records and custody timelines to flag data conflicts, over-detention, and procedural anomalies.",
        permitted_actions=[
            "Detect custody period exceeding maximum statutory fraction under Section 479",
            "Flag age vs juvenile threshold discrepancies (e.g. accused under 18 tried in adult court)",
            "Surface date conflicts between remand orders, jail admissions, and chargesheets",
        ],
        forbidden_actions=[
            "Autonomously overwriting conflicting database records",
            "Autonomously dismissing police FIRs or amending custody dates",
            "Ordering immediate release without judicial and institutional authorization",
        ],
        permitted_sources=[
            "Jail admission registers and custody certificates",
            "Court remand production sheets",
            "Police FIR and arrest logs",
        ],
        required_human_approval="DLSA Secretary and Jail Superintendent review queue.",
        abstention_conditions=[
            "Unparseable date formats or missing custody admission timestamp",
            "Contradictory entries across multi-facility transfers",
        ],
        default_prompt_version="v1.0.0-anomaly-detect",
        max_output_tokens=600,
        temperature=0.05,
    ),

    AICapability.DATA_QUALITY_ASSISTANCE: CapabilityPolicy(
        capability=AICapability.DATA_QUALITY_ASSISTANCE,
        display_name="Data Quality & Ingestion Assistance",
        description="Screens uploaded documents, scores OCR quality, flags illegibility, and assists registry clerks in verifying field extractions.",
        permitted_actions=[
            "Score OCR text extraction confidence across document regions",
            "Identify missing mandatory fields in uploaded scanned records",
            "Suggest standardized corrections for misspelled police stations or courts",
        ],
        forbidden_actions=[
            "Silently modifying official document text without operator review",
            "Bypassing security quarantine for corrupted or malicious files",
            "Fabricating unreadable characters in scanned historical records",
        ],
        permitted_sources=[
            "Document OCR text streams",
            "Canonical police station and court registries",
            "Data Prep Kit cleaned text blocks",
        ],
        required_human_approval="Ingestion Officer or Registry Clerk verification.",
        abstention_conditions=[
            "Scanned image resolution below 100 DPI or complete illegibility",
            "OCR confidence below 0.50",
            "Security screening flags malicious payload or file format mismatch",
        ],
        default_prompt_version="v1.0.0-data-quality",
        ocr_confidence_threshold=0.50,
        max_output_tokens=500,
        temperature=0.05,
    ),

    AICapability.ADMINISTRATIVE_SUMMARIZATION: CapabilityPolicy(
        capability=AICapability.ADMINISTRATIVE_SUMMARIZATION,
        display_name="Administrative & Operational Summarization",
        description="Generates executive summaries of institutional metrics, undertrial backlogs, task throughput, and legal-aid compliance.",
        permitted_actions=[
            "Summarize facility-level and district-level undertrial statistics",
            "Highlight bottlenecked procedural stages and pending lawyer review queues",
            "Generate compliance audit rollups for State Legal Services Authorities (SLSA)",
        ],
        forbidden_actions=[
            "Making automated judicial reassignment or transfer decisions",
            "Reallocating institutional legal aid budgets autonomously",
            "Exposing identifiable prisoner health details in aggregate management rollups",
        ],
        permitted_sources=[
            "Anonymized cases ledger and statistical aggregates",
            "Universal task queue telemetry",
            "Audit ledger and statutory compliance logs",
        ],
        required_human_approval="DLSA Secretary or SLSA Directorate.",
        abstention_conditions=[
            "Stale operational telemetry exceeding 24 hours",
            "Incomplete node synchronization from participating prison facilities",
        ],
        default_prompt_version="v1.0.0-admin-summary",
        max_output_tokens=800,
        temperature=0.1,
    ),
}


def get_capability_policy(capability: AICapability) -> CapabilityPolicy:
    if capability not in CAPABILITY_POLICIES:
        raise ValueError(f"No governance policy defined for AI capability: {capability}")
    return CAPABILITY_POLICIES[capability]
