"""
Document Summarizer Service
===========================
Generates dynamic, AI-powered text summaries of legal case documents
by sending document content and case facts to the configured LLM API (Groq),
with Python NLP extractive fallback. Eliminates hardcoded summary strings.
"""

import os
import re
import logging
import unicodedata
from typing import Optional, Dict, Any

from app.database import get_case, get_uploaded_document_by_id
from app.ai import get_ai_gateway, GatewayRequest, AICapability
from app.services.language_service import generate_derived_display

logger = logging.getLogger(__name__)

# In-memory cache to prevent redundant API calls during rapid navigation
_SUMMARY_CACHE: Dict[str, str] = {}


def clean_text(text: str) -> str:
    """Normalize text and replace non-standard unicode characters."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    return (
        text.replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u202f", " ")
        .replace("\xa0", " ")
        .strip()
    )


def generate_extractive_summary(case_id: str, doc_type: str, raw_text: str = "") -> str:
    """
    Python-based factual extractive summarizer.
    Builds a case-specific factual summary from actual database records when
    external LLM APIs are offline or rate-limited.
    """
    case = get_case(case_id)
    name = getattr(case, "name", "the undertrial inmate") if case else "the undertrial inmate"
    fir = getattr(case, "fir_number", "FIR on record") if case else "FIR on record"
    ps = getattr(case, "police_station", "Police Station") if case else "Police Station"
    court = getattr(case, "court_name", "Court of Competent Jurisdiction") if case else "Court of Competent Jurisdiction"
    sections = getattr(case, "offense_sections", "relevant statutory sections") if case else "relevant statutory sections"
    custody_days = getattr(case, "custody_days", 0) if case else 0
    jail = getattr(case, "jail_location", "Designated Prison Facility") if case else "Designated Prison Facility"
    next_hearing = getattr(case, "next_hearing_date", None) if case else None

    clean_type = doc_type.lower().replace(" ", "_")

    if raw_text and len(raw_text.strip()) > 40:
        # Extract first substantive sentences
        sentences = [s.strip() for s in re.split(r"[.\n]+", raw_text) if len(s.strip()) > 15]
        if len(sentences) >= 2:
            return f"{sentences[0]}. {sentences[1]}."
        elif sentences:
            return f"{sentences[0]}."

    if "fir" in clean_type:
        return f"First Information Report {fir} registered at {ps} concerning {name} alleging offenses under Section {sections}."
    elif "charge" in clean_type:
        return f"Formal police final report filed before {court} detailing evidence and witness list for offenses under {sections}."
    elif "custody" in clean_type or "nominal" in clean_type:
        return f"Superintendent Custody Certificate issued by {jail} verifying {custody_days} calendar days served in judicial detention by {name}."
    elif "remand" in clean_type:
        date_str = f" Next court production scheduled for {next_hearing}." if next_hearing else ""
        return f"Magisterial Remand Order from {court} authorizing lawful detention under judicial custody.{date_str}"
    elif "bail" in clean_type:
        return f"Defense bail application draft submitted on behalf of {name} praying for statutory release before {court}."
    elif "order" in clean_type:
        return f"Authoritative judicial disposition order issued by {court} in case reference {case_id}."
    else:
        clean_name = doc_type.replace("_", " ").title()
        return f"Official {clean_name} entered on record for {name} before {court}."


def summarize_document(
    case_id: str,
    doc_type: str,
    raw_text: str = "",
    doc_obj: Optional[Dict[str, Any]] = None,
    lang: str = "en",
) -> str:
    """
    Summarize a case document dynamically using the LLM API (Groq).
    Falls back to Python extractive synthesis if the API is offline.
    Supports multi-language derived display.
    """
    cache_key = f"{case_id}_{doc_type}_{lang}_{hash(raw_text[:200]) if raw_text else 'base'}"
    if cache_key in _SUMMARY_CACHE:
        return _SUMMARY_CACHE[cache_key]

    case = get_case(case_id)
    clean_type = doc_type.replace("_", " ").title()

    # Build factual context from document and case safely
    facts = []
    if case:
        if getattr(case, "name", None):
            facts.append(f"Accused: {case.name}")
        if getattr(case, "fir_number", None):
            facts.append(f"FIR: {case.fir_number}")
        if getattr(case, "police_station", None):
            facts.append(f"Police Station: {case.police_station}")
        if getattr(case, "court_name", None):
            facts.append(f"Court: {case.court_name}")
        if getattr(case, "offense_sections", None):
            sec = case.offense_sections
            sec_str = ", ".join(sec) if isinstance(sec, list) else str(sec)
            facts.append(f"Sections: {sec_str}")
        if getattr(case, "custody_days", None):
            facts.append(f"Days in Detention: {case.custody_days} days")
        jail = getattr(case, "jail_location", None)
        if jail:
            facts.append(f"Facility: {jail}")
        next_hearing = getattr(case, "next_hearing_date", None)
        if next_hearing:
            facts.append(f"Next Hearing: {next_hearing}")

    context_str = "\n".join(facts)
    if raw_text and len(raw_text.strip()) > 30:
        snippet = raw_text.strip()[:600]
        context_str += f"\nDocument Extract Snippet:\n{snippet}"

    prompt = (
        f"Summarize this official judicial document for an undertrial accused person in 2 clear, concise, plain-language sentences.\n"
        f"Document Type: {clean_type}\n"
        f"Case Facts & Context:\n{context_str}\n\n"
        f"Guidelines:\n"
        f"- Be strictly factual and concise (maximum 2 sentences).\n"
        f"- Use plain language suitable for undertrials and their families.\n"
        f"- Never guarantee release or predict court determinations.\n"
        f"- Output ONLY the 2-sentence summary without preamble or quotation marks."
    )

    summary_text = ""
    try:
        gateway = get_ai_gateway()
        req = GatewayRequest(
            capability=AICapability.DOCUMENT_SUMMARIZATION,
            prompt=prompt,
            case_id=case_id,
            document_id=doc_type,
            user_id="system",
            user_role="SYSTEM",
            context_data={
                "case_id": case_id,
                "document_type": doc_type,
                "raw_text": raw_text[:600] if raw_text else "",
            },
        )
        res = gateway.execute(req)
        if res.structured_data and hasattr(res.structured_data, "concise_summary") and res.structured_data.concise_summary:
            cleaned = res.structured_data.concise_summary.strip()
        elif res.content and "unavailable" not in res.content.lower() and len(res.content.strip()) > 20:
            cleaned = res.content.strip().replace('"', '').replace('**', '')
        else:
            cleaned = ""

        if cleaned:
            # Normalize smart quotes and dashes to prevent encoding issues
            cleaned = (
                cleaned.replace('\u2011', '-')
                .replace('\u2012', '-')
                .replace('\u2013', '-')
                .replace('\u2014', '-')
                .replace('\u2018', "'")
                .replace('\u2019', "'")
                .replace('\u201c', '"')
                .replace('\u201d', '"')
            )
            summary_text = cleaned
    except Exception as e:
        logger.warning(f"AI Gateway summarization failed: {e}. Falling back to extractive Python summary.")

    if not summary_text:
        summary_text = generate_extractive_summary(case_id, doc_type, raw_text)

    # Translate if non-English
    if lang != "en":
        derived = generate_derived_display(summary_text, target_lang=lang)
        final_summary = derived.get("derived_display_text", summary_text)
    else:
        final_summary = summary_text

    clean_summary = clean_text(final_summary)
    _SUMMARY_CACHE[cache_key] = clean_summary
    return clean_summary
