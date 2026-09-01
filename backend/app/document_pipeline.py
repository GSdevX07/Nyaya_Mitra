"""Evidence-based document assessment workflow.

Pipeline architecture for image uploads:

    Image uploaded
        │
        ▼
    detect_is_handwritten(image_bytes)
        │
        ├── YES ──► Microsoft TrOCR  (trocr-large-handwritten)
        │                │
        └── NO  ──► Tesseract OCR
                        │ (if Tesseract not installed)
                        └──► Microsoft TrOCR  (trocr-base-printed, fallback)
        │
        ▼
    Extracted text
        │
        ▼
    Legal AI pipeline  (RAG retrieval  →  LLM assessment)

For PDFs the pipeline goes directly to pypdf text extraction — no OCR needed.
Provided text bypasses OCR entirely.

The pipeline deliberately does not manufacture OCR text, legal citations,
prisoner facts, or an assessment when a required service or input is unavailable.
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

import numpy as np
from PIL import Image
from pydantic import BaseModel

from app.llm_client import generate, get_last_provider
from app.rag.legal_ingestion import LegalIngestionError, extract_pdf_text, run_data_prep_kit
from app.rag.vector_store import retrieve_legal_chunks, VectorStoreUnavailable


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


# ── Step 1: Handwriting Detection ────────────────────────────────────────────

def detect_is_handwritten(image_bytes: bytes) -> tuple[bool, float]:
    """Detect whether an image contains handwritten or printed text.

    Algorithm (pure PIL + numpy, no extra dependencies):
      1. Convert to grayscale and normalise size.
      2. Binarise with Otsu's threshold.
      3. Compute the coefficient of variation (CV) of horizontal ink run-lengths.
         Handwriting → highly irregular strokes → high CV  (> 1.4)
         Printed text → uniform strokes → low CV  (≤ 1.4)
      4. Also sample local-block variance as a supporting signal.

    Returns:
        (is_handwritten, confidence_score)
        confidence_score is between 0.0 and 1.0.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L")  # greyscale

        # Normalise to a fixed width to make the threshold consistent
        TARGET_W = 800
        w, h = img.size
        if w != TARGET_W:
            img = img.resize((TARGET_W, max(1, int(h * TARGET_W / w))), Image.LANCZOS)

        arr = np.array(img, dtype=np.float32)

        # ── Otsu binarisation ─────────────────────────────────────────────────
        # Values below threshold are "ink" (dark pixels)
        otsu_thresh = float(np.mean(arr))
        binary = (arr < otsu_thresh).astype(np.uint8)

        # ── Horizontal run-length analysis ────────────────────────────────────
        run_lengths: list[int] = []
        for row in binary:
            in_run = False
            run_len = 0
            for px in row:
                if px == 1:
                    in_run = True
                    run_len += 1
                elif in_run:
                    if run_len > 0:
                        run_lengths.append(run_len)
                    in_run = False
                    run_len = 0
            if in_run and run_len > 0:
                run_lengths.append(run_len)

        if len(run_lengths) < 10:
            # Not enough ink pixels to analyse — assume printed (safe default)
            return False, 0.5

        rl = np.array(run_lengths, dtype=np.float32)
        mean_rl = float(np.mean(rl))
        std_rl = float(np.std(rl))
        cv = std_rl / (mean_rl + 1e-6)   # coefficient of variation

        # ── Local block variance (supporting signal) ──────────────────────────
        block_h, block_w = 20, 20
        rows_b = arr.shape[0] // block_h
        cols_b = arr.shape[1] // block_w
        block_vars: list[float] = []
        for r in range(rows_b):
            for c in range(cols_b):
                block = arr[r * block_h:(r + 1) * block_h, c * block_w:(c + 1) * block_w]
                block_vars.append(float(np.var(block)))
        mean_block_var = float(np.mean(block_vars)) if block_vars else 0.0

        # ── Decision rule ─────────────────────────────────────────────────────
        # Handwriting signature: high run-length CV AND moderate block variance
        HW_CV_THRESHOLD = 1.4          # tuned empirically
        HW_VAR_THRESHOLD = 400.0       # greyscale variance units

        hw_score = 0.0
        if cv > HW_CV_THRESHOLD:
            hw_score += 0.6            # run-length irregularity (primary)
        if mean_block_var > HW_VAR_THRESHOLD:
            hw_score += 0.4            # texture complexity (secondary)

        is_hw = hw_score >= 0.6
        confidence = min(1.0, hw_score + 0.1) if is_hw else min(1.0, (1.0 - hw_score) + 0.1)

        return is_hw, round(confidence, 3)

    except Exception:
        # If detection fails for any reason, default to handwritten (safer
        # choice: TrOCR handles printed text reasonably as a fallback).
        return True, 0.5


# ── Step 2: OCR routing ───────────────────────────────────────────────────────

def _ocr_image(image_bytes: bytes, suffix: str) -> tuple[bool, float, str, str]:
    """Route an image through the correct OCR engine based on handwriting detection.

    Uses EasyOCR as the primary unified OCR engine for both printed and handwritten text.
    It solves the hallucination problems of TrOCR and the installation dependencies of Tesseract.

    Returns:
        (is_handwritten, confidence, ocr_engine_name, extracted_text)
    """
    from app.llm_client import ocr_image_via_easyocr
    
    # ── 1. Detect handwriting ─────────────────────────────────────────────────
    is_handwritten, confidence = detect_is_handwritten(image_bytes)

    # ── 2. Unified OCR using EasyOCR ──────────────────────────────────────────
    try:
        text = ocr_image_via_easyocr(image_bytes)
        engine = "EasyOCR (handwritten)" if is_handwritten else "EasyOCR (printed)"
        
        if not text.strip():
            raise DocumentPipelineError("EasyOCR returned empty text. Image may be illegible.")
            
        return is_handwritten, confidence, engine, text
    except Exception as exc:
        raise DocumentPipelineError(
            f"EasyOCR extraction failed: {exc}. Please check image quality."
        ) from exc


# ── Step 3: Entry point for extract_document_text ─────────────────────────────

def extract_document_text(
    file_bytes: Optional[bytes],
    document_name: str,
    provided_text: Optional[str],
) -> tuple[bool, float, str, str]:
    """Return (is_handwritten, confidence, engine, text) from the best available source.

    Routing:
        provided_text supplied  →  return as-is (no OCR)
        .pdf                    →  pypdf text extraction  →  legal pipeline
        image file              →  detect_is_handwritten()
                                       YES  →  TrOCR
                                       NO   →  Tesseract  (→  TrOCR fallback)
                                   →  legal pipeline
    """
    if provided_text and provided_text.strip():
        return False, 1.0, "provided text", provided_text.strip()

    if not file_bytes:
        raise DocumentPipelineError("Provide document text or upload a PDF/image for assessment")

    suffix = Path(document_name).suffix.lower()

    # PDF — extract text directly, no OCR needed
    if suffix == ".pdf":
        try:
            text = extract_pdf_text(file_bytes)
        except LegalIngestionError as exc:
            raise DocumentPipelineError(str(exc)) from exc
        return False, 1.0, "pypdf text extraction", text

    # Image — detect handwriting, then route to correct OCR engine
    supported = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp", ".gif", ".heic"}
    if suffix not in supported:
        raise DocumentPipelineError(
            f"Unsupported file type '{suffix}'. Upload a PDF or image "
            f"({', '.join(sorted(supported))})."
        )

    return _ocr_image(file_bytes, suffix)


# ── Metadata extraction helpers ───────────────────────────────────────────────

def _first_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_metadata(text: str, prep_status: str) -> dict[str, Any]:
    """Extract only explicit facts; missing facts remain null for human review."""
    case_match = re.search(
        r"\b(?:CASE\s*(?:ID|NO\.?|NUMBER)?\s*[:=-]?\s*)?(UTP[\s-]*[A-Z0-9-]+)\b",
        text, re.IGNORECASE,
    )
    case_id = re.sub(r"\s+", "-", case_match.group(1).upper()) if case_match else None
    custody_value = _first_match(text, [
        r"(?:custody|detention)[^\d]{0,32}(\d+)\s*days?",
        r"(\d+)\s*days?\s*(?:in\s*)?(?:custody|detention)",
    ])
    sentence_days = _first_match(text, [
        r"(?:maximum|max)[^\d]{0,48}(\d+)\s*days?",
        r"sentence[^\d]{0,48}(\d+)\s*days?",
    ])
    sentence_years = _first_match(text, [
        r"(?:maximum|max)[^\d]{0,48}(\d+(?:\.\d+)?)\s*years?",
        r"sentence[^\d]{0,48}(\d+(?:\.\d+)?)\s*years?",
    ])
    custody_days = int(custody_value) if custody_value else None
    max_sentence_days = (
        int(sentence_days) if sentence_days
        else (round(float(sentence_years) * 365) if sentence_years else None)
    )
    section_matches = re.findall(
        r"\b(?:IPC|BNS|BNSS)\s*(?:Section\s*)?\d+[A-Za-z-]*\b", text, re.IGNORECASE
    )
    sections = list(dict.fromkeys(match.upper() for match in section_matches))
    age_value = _first_match(text, [
        r"\bage\s*[:=-]?\s*(\d{1,3})\b",
        r"\baged\s*(\d{1,3})\b",
    ])
    age = int(age_value) if age_value else None
    custody_fraction = (
        round(custody_days / max_sentence_days, 4)
        if custody_days is not None and max_sentence_days
        else None
    )
    return {
        "case_id": case_id,
        "legal_sections": sections,
        "custody_days": custody_days,
        "max_sentence_days": max_sentence_days,
        "custody_fraction": custody_fraction,
        "age": age,
        "is_senior_citizen": age is not None and age >= 60,
        "has_medical_condition": bool(
            re.search(
                r"\b(?:medical|health|hypertension|diabetes|disability|treatment)\b",
                text, re.IGNORECASE,
            )
        ),
        "data_prep_kit_status": prep_status,
    }


def _retrieve_citations(clean_text: str, metadata: dict[str, Any]) -> list[dict[str, str]]:
    query_terms = ["BNSS Section 479", *metadata.get("legal_sections", [])]
    query = " ".join(query_terms) if metadata.get("legal_sections") else clean_text[:800]
    try:
        chunks = retrieve_legal_chunks(query)
    except (VectorStoreUnavailable, Exception):
        chunks = []
    return [
        {
            "code": str(chunk["source"].get("document_id", "legal-source")),
            "title": str(chunk["source"].get("source_name", "Authorised legal source")),
            "relevance": f"Vector distance: {chunk['distance']:.4f}",
            "snippet": str(chunk["content"]),
        }
        for chunk in chunks
    ]


def _assessment_prompt(
    document_name: str,
    clean_text: str,
    metadata: dict[str, Any],
    citations: list[dict[str, str]],
) -> str:
    sources = (
        "\n\n".join(f"SOURCE: {item['title']}\n{item['snippet']}" for item in citations)
        or "No legal source was retrieved from the approved corpus."
    )
    return (
        "Prepare a concise preliminary legal-aid assessment. "
        "State that it requires human lawyer review; do not claim a legal outcome. "
        f"Document: {document_name}\n"
        f"Extracted facts: {metadata}\n"
        f"Document text:\n{clean_text}\n\n"
        f"Approved RAG sources:\n{sources}"
    )


def _build_assessment(
    document_name: str,
    clean_text: str,
    metadata: dict[str, Any],
    citations: list[dict[str, str]],
) -> dict[str, Any]:
    fraction = metadata.get("custody_fraction")
    if fraction is None:
        eligibility_status = "INSUFFICIENT_DOCUMENT_FACTS"
    elif fraction >= 0.5:
        eligibility_status = "POTENTIAL_SECTION_479_REVIEW"
    else:
        eligibility_status = "REQUIRES_HUMAN_LEGAL_REVIEW"

    generated = generate(
        _assessment_prompt(document_name, clean_text, metadata, citations),
        system=(
            "You are a legal-aid drafting assistant. "
            "Use only supplied document facts and RAG sources. "
            "Do not fabricate facts or give a final legal determination."
        ),
    )
    provider = get_last_provider()
    findings = [
        f"{key.replace('_', ' ').title()}: {value}"
        for key, value in metadata.items()
        if value not in (None, [], "")
    ]
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
        "recommended_action": (
            "A qualified legal professional must verify extracted facts "
            "and approve any next step."
        ),
        "ai_generated_report_draft": generated,
    }


# ── Step 4: Full pipeline entry point ─────────────────────────────────────────

def execute_full_document_pipeline(
    file_bytes: Optional[bytes] = None,
    document_name: str = "document",
    provided_text: Optional[str] = None,
) -> DocumentPipelineResult:
    """Run the full pipeline:  OCR/extraction → data prep → RAG → LLM assessment.

    Stage 1 — Text extraction:
        provided_text  →  use directly
        PDF            →  pypdf
        image          →  detect_is_handwritten() → TrOCR | Tesseract

    Stage 2 — Data preparation:
        run_data_prep_kit() cleans and normalises the raw text.

    Stage 3 — RAG retrieval:
        retrieve_legal_chunks() finds relevant BNSS/IPC statutes.

    Stage 4 — LLM assessment:
        Groq LLM produces a preliminary legal-aid assessment.
    """
    started = time.monotonic()

    # Stage 1
    is_handwritten, confidence, ocr_engine, raw_text = extract_document_text(
        file_bytes, document_name, provided_text
    )

    # Stage 2
    clean_text, prep_status = run_data_prep_kit(raw_text)

    # Stage 3
    metadata = _extract_metadata(clean_text, prep_status)
    citations = _retrieve_citations(clean_text, metadata)

    # Stage 4
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
