"""Evidence-based document assessment workflow.

The pipeline accepts actual supplied text or a document upload.  It deliberately
does not manufacture OCR text, legal citations, prisoner facts, or an assessment
when a required service or input is unavailable.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from app.llm_client import generate, get_last_provider
from app.rag.legal_ingestion import LegalIngestionError, extract_pdf_text, run_data_prep_kit
from app.rag.vector_store import retrieve_legal_chunks


class DocumentPipelineError(ValueError):
    """Raised when an assessment cannot be completed from real document data."""


class DocumentPipelineResult(BaseModel):
    document_name: str
    is_scanned_handwritten: bool
    detection_confidence: float
    ocr_engine_used: str
    raw_ocr_text: str
    extracted_text: str
    data_prep_kit_clean_text: str
    structured_metadata: dict[str, Any]
    rag_statute_citations: list[dict[str, str]]
    granite_assessment: dict[str, Any]
    llm_used: str
    processing_time_ms: float


def _ocr_image(content: bytes, suffix: str) -> tuple[str, str]:
    """Recognise an image using a deployment-configured OCR command or Tesseract.

    ``HANDWRITING_OCR_COMMAND`` may contain ``{input}`` and ``{output}``.  It is
    intentionally deployment configured so a prison/DLSA can use its approved
    handwriting model (for example TrOCR) without embedding model credentials or
    an unverified model invocation in application code.
    """
    configured_command = os.getenv("HANDWRITING_OCR_COMMAND")
    with tempfile.TemporaryDirectory(prefix="nyaya-ocr-") as directory:
        source_path = Path(directory) / f"source{suffix or '.img'}"
        output_path = Path(directory) / "recognized.txt"
        source_path.write_bytes(content)

        if configured_command:
            command = configured_command.format(input=source_path, output=output_path)
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=int(os.getenv("OCR_TIMEOUT_SECONDS", "120")))
            if result.returncode != 0:
                raise DocumentPipelineError(f"Configured handwriting OCR failed: {result.stderr.strip()}")
            text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else result.stdout.strip()
            if not text:
                raise DocumentPipelineError("Configured handwriting OCR returned no text")
            return text, "configured handwriting OCR"

        tesseract = shutil.which("tesseract")
        if not tesseract:
            raise DocumentPipelineError(
                "No handwriting OCR engine is configured. Set HANDWRITING_OCR_COMMAND or install Tesseract for image uploads."
            )
        result = subprocess.run([tesseract, str(source_path), "stdout"], capture_output=True, text=True, timeout=int(os.getenv("OCR_TIMEOUT_SECONDS", "120")))
        if result.returncode != 0 or not result.stdout.strip():
            raise DocumentPipelineError(f"Tesseract could not recognise this image: {result.stderr.strip()}")
        return result.stdout.strip(), "Tesseract OCR"


def extract_document_text(file_bytes: Optional[bytes], document_name: str, provided_text: Optional[str]) -> tuple[bool, float, str, str]:
    """Return text only from a supplied source and name the extraction engine used."""
    if provided_text and provided_text.strip():
        return False, 1.0, "provided text", provided_text.strip()
    if not file_bytes:
        raise DocumentPipelineError("Provide document text or upload a PDF/image for assessment")

    suffix = Path(document_name).suffix.lower()
    if suffix == ".pdf":
        try:
            text = extract_pdf_text(file_bytes)
        except LegalIngestionError as exc:
            raise DocumentPipelineError(str(exc)) from exc
        return False, 1.0, "pypdf text extraction", text
    if suffix not in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}:
        raise DocumentPipelineError("Only PDF and image documents are supported")
    text, engine = _ocr_image(file_bytes, suffix)
    return True, 1.0, engine, text


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_metadata(text: str, prep_status: str) -> dict[str, Any]:
    """Extract only explicit facts; missing facts remain null for human review."""
    case_match = re.search(r"\b(?:CASE\s*(?:ID|NO\.?|NUMBER)?\s*[:=-]?\s*)?(UTP[\s-]*[A-Z0-9-]+)\b", text, re.IGNORECASE)
    case_id = re.sub(r"\s+", "-", case_match.group(1).upper()) if case_match else None
    custody_value = _first_match(text, [r"(?:custody|detention)[^\d]{0,32}(\d+)\s*days?", r"(\d+)\s*days?\s*(?:in\s*)?(?:custody|detention)"])
    sentence_days = _first_match(text, [r"(?:maximum|max)[^\d]{0,48}(\d+)\s*days?", r"sentence[^\d]{0,48}(\d+)\s*days?"])
    sentence_years = _first_match(text, [r"(?:maximum|max)[^\d]{0,48}(\d+(?:\.\d+)?)\s*years?", r"sentence[^\d]{0,48}(\d+(?:\.\d+)?)\s*years?"])
    custody_days = int(custody_value) if custody_value else None
    max_sentence_days = int(sentence_days) if sentence_days else (round(float(sentence_years) * 365) if sentence_years else None)
    section_matches = re.findall(r"\b(?:IPC|BNS|BNSS)\s*(?:Section\s*)?\d+[A-Za-z-]*\b", text, re.IGNORECASE)
    sections = list(dict.fromkeys(match.upper() for match in section_matches))
    age_value = _first_match(text, [r"\bage\s*[:=-]?\s*(\d{1,3})\b", r"\baged\s*(\d{1,3})\b"])
    age = int(age_value) if age_value else None
    custody_fraction = round(custody_days / max_sentence_days, 4) if custody_days is not None and max_sentence_days else None
    return {
        "case_id": case_id,
        "legal_sections": sections,
        "custody_days": custody_days,
        "max_sentence_days": max_sentence_days,
        "custody_fraction": custody_fraction,
        "age": age,
        "is_senior_citizen": age is not None and age >= 60,
        "has_medical_condition": bool(re.search(r"\b(?:medical|health|hypertension|diabetes|disability|treatment)\b", text, re.IGNORECASE)),
        "data_prep_kit_status": prep_status,
    }


def _retrieve_citations(clean_text: str, metadata: dict[str, Any]) -> list[dict[str, str]]:
    query_terms = ["BNSS Section 479", *metadata.get("legal_sections", [])]
    query = " ".join(query_terms) if metadata.get("legal_sections") else clean_text[:800]
    chunks = retrieve_legal_chunks(query)
    return [
        {
            "code": str(chunk["source"].get("document_id", "legal-source")),
            "title": str(chunk["source"].get("source_name", "Authorised legal source")),
            "relevance": f"Vector distance: {chunk['distance']:.4f}",
            "snippet": str(chunk["content"]),
        }
        for chunk in chunks
    ]


def _assessment_prompt(document_name: str, clean_text: str, metadata: dict[str, Any], citations: list[dict[str, str]]) -> str:
    sources = "\n\n".join(f"SOURCE: {item['title']}\n{item['snippet']}" for item in citations) or "No legal source was retrieved from the approved corpus."
    return (
        "Prepare a concise preliminary legal-aid assessment. State that it requires human lawyer review; do not claim a legal outcome. "
        f"Document: {document_name}\nExtracted facts: {metadata}\nDocument text:\n{clean_text}\n\nApproved RAG sources:\n{sources}"
    )


def _build_assessment(document_name: str, clean_text: str, metadata: dict[str, Any], citations: list[dict[str, str]]) -> dict[str, Any]:
    fraction = metadata.get("custody_fraction")
    if fraction is None:
        eligibility_status = "INSUFFICIENT_DOCUMENT_FACTS"
    elif fraction >= 0.5:
        eligibility_status = "POTENTIAL_SECTION_479_REVIEW"
    else:
        eligibility_status = "REQUIRES_HUMAN_LEGAL_REVIEW"
    generated = generate(
        _assessment_prompt(document_name, clean_text, metadata, citations),
        system="You are a legal-aid drafting assistant. Use only supplied document facts and RAG sources. Do not fabricate facts or give a final legal determination.",
    )
    provider = get_last_provider()
    findings = [f"{key.replace('_', ' ').title()}: {value}" for key, value in metadata.items() if value not in (None, [], "")]
    return {
        "assessment_id": str(uuid.uuid4()),
        "model_name": provider,
        "case_id": metadata.get("case_id"),
        "eligibility_status": eligibility_status,
        "confidence_score": 0.0,
        "urgency_rating": "HUMAN_REVIEW_REQUIRED",
        "statutory_ground": "RAG corpus required for legal grounding",
        "legal_summary": generated,
        "key_findings": findings,
        "recommended_action": "A qualified legal professional must verify extracted facts and approve any next step.",
        "ai_generated_report_draft": generated,
    }


def execute_full_document_pipeline(file_bytes: Optional[bytes] = None, document_name: str = "document", provided_text: Optional[str] = None) -> DocumentPipelineResult:
    """Run OCR/extraction -> data preparation -> RAG -> model assessment from real input."""
    started = time.monotonic()
    is_handwritten, confidence, ocr_engine, raw_text = extract_document_text(file_bytes, document_name, provided_text)
    clean_text, prep_status = run_data_prep_kit(raw_text)
    metadata = _extract_metadata(clean_text, prep_status)
    citations = _retrieve_citations(clean_text, metadata)
    assessment = _build_assessment(document_name, clean_text, metadata, citations)
    return DocumentPipelineResult(
        document_name=document_name,
        is_scanned_handwritten=is_handwritten,
        detection_confidence=confidence,
        ocr_engine_used=ocr_engine,
        raw_ocr_text=raw_text,
        extracted_text=raw_text,
        data_prep_kit_clean_text=clean_text,
        structured_metadata=metadata,
        rag_statute_citations=citations,
        granite_assessment=assessment,
        llm_used=get_last_provider(),
        processing_time_ms=round((time.monotonic() - started) * 1000, 2),
    )
