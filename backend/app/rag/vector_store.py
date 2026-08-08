"""
vector_store.py — Lightweight mock knowledge base for Nyaya Mitra RAG layer.

Design note (from Nyaya_Mitra_Master_Roadmap_v2.md §8, Step 1.5):
  In production this module would be backed by ChromaDB with real embeddings.
  For the hackathon build, it is a plain Python dict of public-domain statute
  text — the retrieval logic (retrieve_legal_text) is identical in both cases,
  so swapping the backend only requires changing how STATUTE_DB is populated,
  not how it is queried.

  All statute text is sourced from public-domain government legislation.
  No synthetic or fabricated law is used here — this is a core RAG ground rule.
"""

from __future__ import annotations


# ── Knowledge base ───────────────────────────────────────────────────────────
# Keys map 1-to-1 with the query keys used by the Retrieval Agent.
# Add more entries here as the statute corpus grows.

STATUTE_DB: dict[str, str] = {
    "BNSS_479": (
        "Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023: "
        "Where a person has, during the period of investigation, inquiry or trial "
        "under this Sanhita of an offence under any law (not being an offence for "
        "which the punishment of death or life imprisonment has been specified as "
        "one of the punishments under that law) undergone detention for a period "
        "extending up to one-half of the maximum period of imprisonment specified "
        "for that offence under that law, he shall be released by the Court on bail: "
        "Provided that where such person is a first-time offender... he shall be "
        "released on bond by the Court, if he has undergone detention for the period "
        "extending up to one-third of the maximum period of imprisonment."
    ),

    "PRECEDENT_DELAY": (
        "Supreme Court ruling: Prolonged incarceration during pendency of trial "
        "violates Article 21 of the Constitution."
    ),
}


# ── Retrieval function ───────────────────────────────────────────────────────

def retrieve_legal_text(query_keys: list[str]) -> str:
    """
    Retrieve and concatenate statute/precedent text for the given keys.

    In the current mock implementation this is a direct dictionary lookup.
    In production, replace this function body with a vector similarity search
    against ChromaDB — the return type and call signature stay identical.

    Args:
        query_keys: List of STATUTE_DB keys to retrieve, e.g.
                    ["BNSS_479", "PRECEDENT_DELAY"].

    Returns:
        A single string with each matching entry joined by double newlines.
        Keys that do not exist in STATUTE_DB are silently skipped (logged
        at WARNING level so missing entries are detectable without crashing).

    Example:
        >>> text = retrieve_legal_text(["BNSS_479"])
        >>> "Section 479" in text
        True
    """
    import logging
    logger = logging.getLogger(__name__)

    chunks: list[str] = []
    for key in query_keys:
        text = STATUTE_DB.get(key)
        if text:
            chunks.append(text)
        else:
            logger.warning("retrieve_legal_text: key '%s' not found in STATUTE_DB", key)

    return "\n\n".join(chunks)
