"""
retrieval_agent.py - Grounded Statutory Legal RAG for Nyaya Mitra.

╔══════════════════════════════════════════════════════════════════════════╗
║  STATUTORY RAG SCOPE & VERIFICATION PRINCIPLES                           ║
║  1. CURRENT PROTOTYPE: Grounded in verified statutory texts               ║
║     (BNSS 2023, BNS 2023, IPC 1860, CrPC 1973).                         ║
║  2. FUTURE EXPANSION: Judicial precedent / Case Law retrieval.           ║
║  3. Every retrieved passage retains full statutory provenance:          ║
║     - Statute Title                                                      ║
║     - Section Number                                                     ║
║     - Legal Code Context (BNS_2023 vs IPC_1860)                          ║
║     - Effective Date Context                                             ║
║     - Relevance Reasoning                                                ║
║  4. If statutory ambiguity or multiple active proceedings are flagged,  ║
║     an explicit 'HUMAN_LEGAL_REVIEW_REQUIRED' flag is attached.          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from typing import Dict, Any, List

from app.models.schemas import CaseRecord, LegalCode
from app.rag.vector_store import retrieve_legal_text


_STATUTORY_CORPUS: Dict[str, Dict[str, Any]] = {
    "BNSS_479": {
        "statute": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
        "section": "Section 479",
        "legal_code": "BNSS_2023",
        "effective_date": "2024-07-01",
        "title": "Maximum period for which an undertrial prisoner can be detained",
        "text": (
            "Section 479(1): Where a person has, during the period of investigation, inquiry or trial under this Sanhita "
            "of an offence under any law (not being an offence for which the punishment of death or life imprisonment "
            "has been specified as one of the punishments under that law) undergone detention for a period extending to "
            "one-half of the maximum period of imprisonment specified for that offence under that law, he shall be released "
            "by the Court on bail on his personal bond with or without sureties:\n"
            "Provided that where such person is a first-time offender (who has never been previously convicted of any offence), "
            "he shall be released on bond by the Court, if he has undergone detention for the period extending to "
            "one-third of the maximum period of imprisonment specified for such offence under that law:\n"
            "Provided further that where proceedings are delayed due to actions attributable to the accused, such period "
            "shall be excluded from the computation of the detention period."
        ),
        "relevance_rationale": "Primary statutory authority for maximum undertrial detention and bail eligibility.",
    },
    "BNS_115": {
        "statute": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
        "section": "Section 115(2)",
        "legal_code": "BNS_2023",
        "effective_date": "2024-07-01",
        "title": "Voluntarily causing hurt",
        "text": (
            "Section 115(2): Whoever voluntarily causes hurt shall be punished with imprisonment of either description "
            "for a term which may extend to one year, or with fine which may extend to ten thousand rupees, or with both."
        ),
        "relevance_rationale": "Offence specification determining maximum prescribed sentence (1 year / 365 days).",
    },
    "BNS_303": {
        "statute": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
        "section": "Section 303(2)",
        "legal_code": "BNS_2023",
        "effective_date": "2024-07-01",
        "title": "Theft",
        "text": (
            "Section 303(2): Whoever commits theft shall be punished with imprisonment of either description for a term "
            "which may extend to three years, or with fine, or with both."
        ),
        "relevance_rationale": "Offence specification determining maximum prescribed sentence (3 years / 730-1095 days).",
    },
    "BNS_105": {
        "statute": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
        "section": "Section 105",
        "legal_code": "BNS_2023",
        "effective_date": "2024-07-01",
        "title": "Culpable homicide not amounting to murder",
        "text": (
            "Section 105: Whoever commits culpable homicide not amounting to murder shall be punished with imprisonment for "
            "life, or imprisonment of either description for a term which may extend to ten years, and shall also be liable to fine."
        ),
        "relevance_rationale": "Conviction offence governing sentence term and appellate legal-aid forum.",
    },
    "IPC_392": {
        "statute": "Indian Penal Code, 1860 (IPC) — Historical / Transitional Offence",
        "section": "Section 392",
        "legal_code": "IPC_1860",
        "effective_date": "1860-10-06 (Transitional savings under BNSS Sec 531)",
        "title": "Punishment for robbery",
        "text": (
            "Section 392: Whoever commits robbery shall be punished with rigorous imprisonment for a term which may extend "
            "to ten years, and shall also be liable to fine; and, if the robbery be committed on the highway between sunset "
            "and sunrise, the imprisonment may be extended to fourteen years."
        ),
        "relevance_rationale": "Historical IPC statutory offence charged prior to BNS commencement.",
    },
    "IPC_420": {
        "statute": "Indian Penal Code, 1860 (IPC) — Historical / Transitional Offence",
        "section": "Section 420",
        "legal_code": "IPC_1860",
        "effective_date": "1860-10-06 (Transitional savings under BNSS Sec 531)",
        "title": "Cheating and dishonestly inducing delivery of property",
        "text": (
            "Section 420: Whoever cheats and thereby dishonestly induces the person deceived to deliver any property... "
            "shall be punished with imprisonment of either description for a term which may extend to seven years, "
            "and shall also be liable to fine."
        ),
        "relevance_rationale": "Historical IPC fraud offence with custody milestone preserved post-release.",
    },
    "CONSTITUTION_21": {
        "statute": "Constitution of India",
        "section": "Article 21 (Constitutional Precedent)",
        "legal_code": "CONSTITUTION_INDIA",
        "effective_date": "1950-01-26",
        "title": "Protection of life and personal liberty",
        "text": (
            "Article 21: No person shall be deprived of his life or personal liberty except according to procedure "
            "established by law.\n"
            "Precedent: Prolonged undertrial incarceration where delay is not attributable to the accused violates "
            "fundamental rights guaranteed under Article 21 (Hussainara Khatoon; Satender Kumar Antil v. CBI)."
        ),
        "relevance_rationale": "Constitutional foundation supporting statutory bail under Section 479 BNSS.",
    },
}


def execute_retrieval(case: CaseRecord, is_eligible: bool) -> Dict[str, Any]:
    """
    Retrieve verified statutory texts and citations grounded in the case's
    applicable legal code and charged sections.
    """
    citations: List[Dict[str, Any]] = []

    # 1. Base BNSS Section 479 & Constitutional Grounding
    citations.append(_STATUTORY_CORPUS["BNSS_479"])
    citations.append(_STATUTORY_CORPUS["CONSTITUTION_21"])

    # 2. Add Offence-Specific Statutory Passages
    for section in case.offense_sections:
        clean = section.upper().replace(" ", "_").replace("(", "").replace(")", "")
        for corpus_key, item in _STATUTORY_CORPUS.items():
            if corpus_key in clean or clean in corpus_key:
                if item not in citations:
                    citations.append(item)

    # 3. Concatenate Text for LLM Drafting
    full_text_blocks = []
    for c in citations:
        block = (
            f"[{c['statute']} — {c['section']}]\n"
            f"Title: {c['title']}\n"
            f"Legal Code: {c['legal_code']} (Effective: {c['effective_date']})\n"
            f"Statutory Text:\n{c['text']}\n"
            f"Relevance: {c['relevance_rationale']}\n"
        )
        full_text_blocks.append(block)

    concatenated_statutes = "\n" + ("=" * 50) + "\n\n".join(full_text_blocks)

    return {
        "case_id": case.case_id,
        "is_eligible": is_eligible,
        "rag_scope": "STATUTORY_LEGAL_TEXT (Case law / Judicial Precedents earmarked for future expansion)",
        "citations": citations,
        "retrieved_statutes": concatenated_statutes if is_eligible else "",
        "uncertainty_flag": "HUMAN_LEGAL_REVIEW_REQUIRED" if case.multiple_active_cases or case.punishable_by_death_or_life else None,
    }
