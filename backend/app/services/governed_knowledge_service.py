"""
governed_knowledge_service.py — Governed Legal Knowledge Layer for Nyaya Mitra.

╔══════════════════════════════════════════════════════════════════════════════╗
║  GOVERNED LEGAL KNOWLEDGE ARCHITECTURE & SECURITY BOUNDARIES                 ║
║  1. Source Registry: Every document tracks issuing authority, jurisdiction,   ║
║     effective date, publication date, SHA-256 hash, and version.             ║
║  2. Strict Ingestion Default: All proposed sources strictly enter            ║
║     lifecycle_status = 'discovered'. Client status override is rejected.     ║
║  3. Enforced State Machine Graph:                                            ║
║     discovered -> reviewed -> approved -> active -> superseded -> retired    ║
║     Arbitrary or invalid jumps are rejected with 400 Bad Request.            ║
║  4. Separation of Powers: Platform Admin has NO unilateral statutory content ║
║     authority. Only SUPERVISING_LEGAL_OFFICER & GOV_ADMIN govern enactments.  ║
║  5. Text Immutability: Legal text of active/approved sources cannot be       ║
║     mutated in-place. Updates require supersession with new version/hash.    ║
║  6. Durable Escalations: Unsupported assertions persist a review task        ║
║     in legal_human_review_tasks and alert the supervising legal officer.     ║
║  7. Structured Audit & Telemetry: Retrieval operations and lifecycle changes ║
║     write immutable records to audit_events and legal_retrieval_logs.        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.database import (
    get_db_connection,
    audit_repo,
    create_legal_escalation,
    log_legal_retrieval,
)
from app.models.domain import AuditAction


class SourceLifecycleState(str, Enum):
    DISCOVERED = "discovered"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


# Canonical server-side transition state machine graph
LEGAL_LIFECYCLE_TRANSITIONS: Dict[str, List[str]] = {
    SourceLifecycleState.DISCOVERED.value: [SourceLifecycleState.REVIEWED.value],
    SourceLifecycleState.REVIEWED.value: [SourceLifecycleState.APPROVED.value, SourceLifecycleState.DISCOVERED.value],
    SourceLifecycleState.APPROVED.value: [SourceLifecycleState.ACTIVE.value, SourceLifecycleState.REVIEWED.value],
    SourceLifecycleState.ACTIVE.value: [SourceLifecycleState.SUPERSEDED.value],
    SourceLifecycleState.SUPERSEDED.value: [SourceLifecycleState.RETIRED.value],
    SourceLifecycleState.RETIRED.value: [],
}


class LegalDomain(str, Enum):
    CRIMINAL_PROCEDURE = "CRIMINAL_PROCEDURE"
    PENAL_LAW = "PENAL_LAW"
    JUDICIAL_PRECEDENT = "JUDICIAL_PRECEDENT"
    PRISON_RULES = "PRISON_RULES"
    CONSTITUTIONAL_LAW = "CONSTITUTIONAL_LAW"
    LEGAL_AID = "LEGAL_AID"


@dataclass
class LegalSourceRecord:
    id: str
    title: str
    short_name: str
    issuing_authority: str
    effective_date: str
    publication_date: Optional[str]
    jurisdiction: str
    source_url: Optional[str]
    document_hash: str
    version: str
    language: str
    legal_domain: str
    lifecycle_status: str
    superseded_by_id: Optional[str] = None
    raw_content: Optional[str] = None
    created_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    audit_notes: Optional[str] = None


@dataclass
class LegalChunkRecord:
    id: str
    source_id: str
    document_title: str
    section_number: Optional[str]
    section_title: Optional[str]
    original_text: str
    normalized_text: str
    chunk_index: int
    start_char: int
    end_char: int
    citation_key: str
    legal_domain: str
    jurisdiction: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    lifecycle_status: str = "active"
    score: float = 0.0


# ── 1. TEXT PREPROCESSING & INGESTION (VERBATIM PRESERVATION) ─────────────────

def normalize_legal_text(text: str) -> str:
    """Normalize whitespace and linebreaks without altering statutory vocabulary or grammar.
    
    Zero semantic rewriting or paraphrasing is performed on legal sources.
    """
    if not text:
        return ""
    # Standardize Windows/Unix newlines
    standardized = re.sub(r"\r\n?", "\n", text)
    # Collapse irregular internal spaces while preserving paragraph breaks
    paragraphs = standardized.split("\n\n")
    cleaned_paras = []
    for p in paragraphs:
        cleaned_para = " ".join(p.split()).strip()
        if cleaned_para:
            cleaned_paras.append(cleaned_para)
    return "\n\n".join(cleaned_paras)


def compute_document_hash(raw_text: str) -> str:
    """Compute SHA-256 fingerprint of the source document."""
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def chunk_legal_source(
    source_id: str,
    document_title: str,
    raw_text: str,
    legal_domain: str,
    jurisdiction: str,
    max_chunk_chars: int = 1500,
) -> List[LegalChunkRecord]:
    """Segment a legal document by sections and boundary tracking.
    
    Preserves exact start_char and end_char offsets against the original text.
    """
    normalized = normalize_legal_text(raw_text)
    chunks: List[LegalChunkRecord] = []

    # Section-aware split: look for "Section X", "Rule X", "Article X" patterns
    section_pattern = re.compile(
        r"(?:^|\n\n)(?P<header>(?:Section|Sec\.|Rule|Article)\s+(?P<sec_num>[0-9A-Za-z\(\)]+)[^\n]*)",
        re.IGNORECASE,
    )

    matches = list(section_pattern.finditer(normalized))
    if matches:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(normalized)
            sec_text = normalized[start:end].strip()
            sec_num = match.group("sec_num")
            header = match.group("header").strip()

            # Clean citation key e.g. "BNSS:479"
            prefix = "STATUTE"
            if "Bhartiya" in document_title or "Bharatiya" in document_title:
                if "Nagarik" in document_title:
                    prefix = "BNSS"
                elif "Nyaya" in document_title:
                    prefix = "BNS"
            elif "Penal Code" in document_title:
                prefix = "IPC"
            elif "Criminal Procedure" in document_title:
                prefix = "CRPC"
            elif "Prison" in document_title:
                prefix = "DPR"
            elif "Supreme Court" in document_title:
                prefix = "SC"

            clean_sec = re.sub(r"[^0-9A-Za-z]", "", sec_num)
            citation_key = f"{prefix}:{clean_sec}" if clean_sec else f"{prefix}:SEC"

            chunk = LegalChunkRecord(
                id=f"chk_{source_id}_{i+1:03d}",
                source_id=source_id,
                document_title=document_title,
                section_number=sec_num,
                section_title=header,
                original_text=sec_text,
                normalized_text=sec_text,
                chunk_index=i,
                start_char=start,
                end_char=end,
                citation_key=citation_key,
                legal_domain=legal_domain,
                jurisdiction=jurisdiction,
                metadata={
                    "authority": prefix,
                    "section": sec_num,
                    "length": len(sec_text),
                },
            )
            chunks.append(chunk)
    else:
        # Fallback paragraph chunker
        paragraphs = normalized.split("\n\n")
        curr_text = ""
        curr_start = 0
        chunk_idx = 0
        for para in paragraphs:
            if len(curr_text) + len(para) > max_chunk_chars and curr_text:
                chunks.append(
                    LegalChunkRecord(
                        id=f"chk_{source_id}_{chunk_idx+1:03d}",
                        source_id=source_id,
                        document_title=document_title,
                        section_number=None,
                        section_title=None,
                        original_text=curr_text.strip(),
                        normalized_text=curr_text.strip(),
                        chunk_index=chunk_idx,
                        start_char=curr_start,
                        end_char=curr_start + len(curr_text),
                        citation_key=f"{source_id}:{chunk_idx+1}",
                        legal_domain=legal_domain,
                        jurisdiction=jurisdiction,
                    )
                )
                chunk_idx += 1
                curr_start += len(curr_text) + 2
                curr_text = para + "\n\n"
            else:
                curr_text += para + "\n\n"

        if curr_text.strip():
            chunks.append(
                LegalChunkRecord(
                    id=f"chk_{source_id}_{chunk_idx+1:03d}",
                    source_id=source_id,
                    document_title=document_title,
                    section_number=None,
                    section_title=None,
                    original_text=curr_text.strip(),
                    normalized_text=curr_text.strip(),
                    chunk_index=chunk_idx,
                    start_char=curr_start,
                    end_char=curr_start + len(curr_text),
                    citation_key=f"{source_id}:{chunk_idx+1}",
                    legal_domain=legal_domain,
                    jurisdiction=jurisdiction,
                )
            )

    return chunks


# ── 2. DATABASE REPOSITORY OPERATIONS ─────────────────────────────────────────

def list_legal_sources(
    domain: Optional[str] = None,
    lifecycle_status: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    redact_sensitive: bool = False,
) -> List[Dict[str, Any]]:
    """List all legal sources matching query filters with optional consumer redaction."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM legal_sources WHERE 1=1"
    params: List[Any] = []

    if domain:
        query += " AND legal_domain = ?"
        params.append(domain)
    if lifecycle_status:
        query += " AND lifecycle_status = ?"
        params.append(lifecycle_status)
    if jurisdiction:
        query += " AND jurisdiction LIKE ?"
        params.append(f"%{jurisdiction}%")

    query += " ORDER BY CASE lifecycle_status WHEN 'active' THEN 1 WHEN 'approved' THEN 2 WHEN 'reviewed' THEN 3 WHEN 'discovered' THEN 4 WHEN 'superseded' THEN 5 ELSE 6 END, effective_date DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    sources = []
    for r in rows:
        d = dict(r)
        # Count chunks
        cursor.execute("SELECT COUNT(*) as cnt FROM legal_chunks WHERE source_id = ?", (d["id"],))
        chunk_row = cursor.fetchone()
        d["chunk_count"] = chunk_row["cnt"] if chunk_row else 0

        # Redact internal maintainer notes for external consumer roles (e.g. Defense Advocate)
        if redact_sensitive:
            d["audit_notes"] = None
            d["reviewed_by"] = None
            d["approved_by"] = None

        sources.append(d)

    conn.close()
    return sources


def get_legal_source_by_id(source_id: str, redact_sensitive: bool = False) -> Optional[Dict[str, Any]]:
    """Fetch complete source record and its parsed chunks with optional redaction."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM legal_sources WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    source_dict = dict(row)
    cursor.execute("SELECT * FROM legal_chunks WHERE source_id = ? ORDER BY chunk_index ASC", (source_id,))
    chunks = [dict(c) for c in cursor.fetchall()]
    source_dict["chunks"] = chunks
    conn.close()

    if redact_sensitive:
        source_dict["audit_notes"] = None
        source_dict["reviewed_by"] = None
        source_dict["approved_by"] = None

    return source_dict


def register_legal_source(
    title: str,
    short_name: str,
    issuing_authority: str,
    effective_date: str,
    jurisdiction: str,
    legal_domain: str,
    raw_content: str,
    source_url: Optional[str] = None,
    publication_date: Optional[str] = None,
    version: str = "1.0",
    language: str = "en",
    lifecycle_status: str = SourceLifecycleState.DISCOVERED.value,
    user_id: str = "system",
    user_role: str = "DLSA_OFFICER",
    audit_notes: Optional[str] = None,
    is_system_seed: bool = False,
) -> Dict[str, Any]:
    """Register and ingest a new legal source document with provenance tracking.
    
    PART D & F ENFORCEMENT:
    - Ingestion strictly starts at 'discovered'. Client-provided attempts to set 'active' or 'approved' are rejected/normalized.
    - Active or approved legal texts are strictly immutable. Substantive updates require supersession.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Part D: Strictly enforce initial state = discovered for non-system seed ingestions
    enforced_status = SourceLifecycleState.DISCOVERED.value if not is_system_seed else lifecycle_status

    doc_hash = compute_document_hash(raw_content)
    # Generate stable ID from authority & title slug
    slug = re.sub(r"[^a-z0-9]", "_", short_name.lower())[:24].strip("_")
    source_id = f"src_{slug}_{doc_hash[:8]}"

    # Part F: Check text immutability if source with same title/short_name or ID already exists
    cursor.execute(
        """
        SELECT id, lifecycle_status, document_hash FROM legal_sources
        WHERE (id = ? OR short_name = ? OR title = ?) AND lifecycle_status IN ('active', 'approved')
        """,
        (source_id, short_name, title),
    )
    existing = cursor.fetchone()
    if existing and existing["document_hash"] != doc_hash:
        conn.close()
        raise ValueError(
            f"Legal content of active or approved source '{existing['id']}' ({title}) is immutable. "
            f"Modifications must be published as a new version and governed via supersession."
        )


    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cursor.execute(
        """
        INSERT OR REPLACE INTO legal_sources (
            id, title, short_name, issuing_authority, effective_date, publication_date,
            jurisdiction, source_url, document_hash, version, language, legal_domain,
            lifecycle_status, raw_content, created_at, reviewed_by, approved_by, audit_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id,
            title,
            short_name,
            issuing_authority,
            effective_date,
            publication_date,
            jurisdiction,
            source_url,
            doc_hash,
            version,
            language,
            legal_domain,
            enforced_status,
            raw_content,
            now_iso,
            user_id if enforced_status in ("reviewed", "approved", "active") else None,
            user_id if enforced_status in ("approved", "active") else None,
            audit_notes or f"Initial ingestion by {user_id} ({user_role}) as '{enforced_status}'",
        ),
    )

    # Chunk and store chunks
    chunks = chunk_legal_source(
        source_id=source_id,
        document_title=title,
        raw_text=raw_content,
        legal_domain=legal_domain,
        jurisdiction=jurisdiction,
    )

    # Delete any existing chunks for this source_id
    cursor.execute("DELETE FROM legal_chunks WHERE source_id = ?", (source_id,))

    for chk in chunks:
        cursor.execute(
            """
            INSERT INTO legal_chunks (
                id, source_id, document_title, section_number, section_title,
                original_text, normalized_text, chunk_index, start_char, end_char,
                citation_key, legal_domain, jurisdiction, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chk.id,
                chk.source_id,
                chk.document_title,
                chk.section_number,
                chk.section_title,
                chk.original_text,
                chk.normalized_text,
                chk.chunk_index,
                chk.start_char,
                chk.end_char,
                chk.citation_key,
                chk.legal_domain,
                chk.jurisdiction,
                json.dumps(chk.metadata),
            ),
        )

    conn.commit()
    conn.close()

    # Part I: Record structured audit log
    try:
        audit_repo.record(
            actor_id=user_id,
            actor_role=user_role,
            action=AuditAction.CREATE,
            entity_type="LEGAL_SOURCE",
            entity_id=source_id,
            details={
                "title": title,
                "short_name": short_name,
                "document_hash": doc_hash,
                "lifecycle_status": enforced_status,
                "chunks_indexed": len(chunks),
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit event for legal source creation: {e}")

    return {
        "source_id": source_id,
        "title": title,
        "document_hash": doc_hash,
        "chunks_indexed": len(chunks),
        "lifecycle_status": enforced_status,
    }


def update_source_lifecycle(
    source_id: str,
    new_status: str,
    user_id: str,
    user_role: str = "SUPERVISING_LEGAL_OFFICER",
    notes: Optional[str] = None,
    superseded_by_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Transition a legal source through its governance lifecycle.
    
    PART E & N ENFORCEMENT:
    - Enforces strict server-side state machine transitions.
    - Validates caller role against the requested transition.
    - Strips unilateral statutory authority from PLATFORM_ADMIN.
    - Persists structured audit events.
    """
    valid_states = [s.value for s in SourceLifecycleState]
    if new_status not in valid_states:
        raise ValueError(f"Invalid lifecycle state: '{new_status}'. Expected one of {valid_states}")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM legal_sources WHERE id = ?", (source_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Legal source not found: {source_id}")

    old_status = row["lifecycle_status"]

    # Part N: Role clearance verification
    if user_role == "PLATFORM_ADMIN":
        conn.close()
        raise ValueError(
            f"Role 'PLATFORM_ADMIN' is restricted from legal governance transitions. "
            f"Statutory authority requires SUPERVISING_LEGAL_OFFICER or GOV_ADMIN sign-off."
        )

    if user_role not in ("SUPERVISING_LEGAL_OFFICER", "GOV_ADMIN"):
        conn.close()
        raise ValueError(f"Role '{user_role}' is not authorized to manage statutory lifecycle transitions.")

    # Part E: Validate State Machine Graph
    allowed_next_states = LEGAL_LIFECYCLE_TRANSITIONS.get(old_status, [])
    if new_status not in allowed_next_states:
        conn.close()
        raise ValueError(
            f"Invalid lifecycle transition: Cannot transition source from '{old_status}' to '{new_status}'. "
            f"Permitted transitions from '{old_status}': {allowed_next_states}"
        )


    if new_status in (SourceLifecycleState.REVIEWED.value, SourceLifecycleState.APPROVED.value):
        if user_role not in ("SUPERVISING_LEGAL_OFFICER", "GOV_ADMIN"):
            conn.close()
            raise ValueError(f"Role '{user_role}' is not authorized to review or approve legal sources.")

    if new_status == SourceLifecycleState.ACTIVE.value:
        if user_role not in ("GOV_ADMIN", "SUPERVISING_LEGAL_OFFICER"):
            conn.close()
            raise ValueError(f"Role '{user_role}' is not authorized to activate statutory sources.")

    if new_status == SourceLifecycleState.SUPERSEDED.value:
        if user_role not in ("GOV_ADMIN", "SUPERVISING_LEGAL_OFFICER"):
            conn.close()
            raise ValueError(f"Role '{user_role}' is not authorized to supersede legal sources.")
        if not superseded_by_id:
            conn.close()
            raise ValueError("Superseding an active legal source requires providing 'superseded_by_id'.")
        # Validate that the replacement source exists
        cursor.execute("SELECT id FROM legal_sources WHERE id = ?", (superseded_by_id,))
        if not cursor.fetchone():
            conn.close()
            raise ValueError(f"Replacement source 'superseded_by_id' '{superseded_by_id}' not found in registry.")

    if new_status == SourceLifecycleState.RETIRED.value:
        if user_role not in ("GOV_ADMIN", "SUPERVISING_LEGAL_OFFICER"):
            conn.close()
            raise ValueError(f"Role '{user_role}' is not authorized to retire legal sources.")

    audit_notes = (
        f"{row['audit_notes'] or ''}\n"
        f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] {old_status} -> {new_status} "
        f"by {user_id} ({user_role}): {notes or 'No notes provided.'}"
    )

    reviewed_by = user_id if new_status in ("reviewed", "approved", "active") else row["reviewed_by"]
    approved_by = user_id if new_status in ("approved", "active") else row["approved_by"]

    cursor.execute(
        """
        UPDATE legal_sources
        SET lifecycle_status = ?,
            superseded_by_id = COALESCE(?, superseded_by_id),
            reviewed_by = ?,
            approved_by = ?,
            audit_notes = ?
        WHERE id = ?
        """,
        (new_status, superseded_by_id, reviewed_by, approved_by, audit_notes.strip(), source_id),
    )

    conn.commit()
    conn.close()

    # Part I: Record structured audit event
    try:
        audit_repo.record(
            actor_id=user_id,
            actor_role=user_role,
            action=AuditAction.STATUS_TRANSITION,
            entity_type="LEGAL_SOURCE",
            entity_id=source_id,
            details={
                "previous_status": old_status,
                "new_status": new_status,
                "superseded_by_id": superseded_by_id,
                "notes": notes,
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to write audit event for legal lifecycle transition: {e}")

    return {
        "source_id": source_id,
        "old_status": old_status,
        "new_status": new_status,
        "updated_by": user_id,
        "superseded_by_id": superseded_by_id,
    }


# ── 3. CITATION-AWARE HYBRID RETRIEVAL & RERANKING ────────────────────────────

def hybrid_retrieve_legal_chunks(
    query: str,
    domain: Optional[str] = None,
    include_superseded: bool = False,
    limit: int = 5,
    actor_id: str = "system",
    actor_role: str = "unknown",
    organization_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Hybrid legal retrieval engine: citation extraction + lexical search + rule-based reranking.
    
    Part H: Logs comprehensive retrieval telemetry into legal_retrieval_logs.
    """
    if not query.strip():
        return []

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query active sources by default
    status_filter = "('active', 'approved')" if not include_superseded else "('active', 'approved', 'superseded', 'reviewed')"

    sql = f"""
        SELECT c.*, s.title as source_title, s.short_name, s.issuing_authority,
               s.effective_date, s.jurisdiction as source_jurisdiction, s.document_hash,
               s.lifecycle_status, s.version, s.source_url
        FROM legal_chunks c
        JOIN legal_sources s ON c.source_id = s.id
        WHERE s.lifecycle_status IN {status_filter}
    """
    params: List[Any] = []
    if domain:
        sql += " AND c.legal_domain = ?"
        params.append(domain)

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    query_lower = query.lower()
    section_matches = re.findall(r"\b(?:section|sec\.?|s\.)?\s*([0-9]{1,4}(?:\([0-9A-Za-z]+\))*)\b", query_lower)
    query_tokens = set(re.findall(r"\b[a-z0-9_]{3,}\b", query_lower))

    scored_chunks: List[Tuple[float, Dict[str, Any]]] = []

    for r in rows:
        chunk = dict(r)
        chunk_text_lower = (chunk["normalized_text"] or "").lower()
        chunk_title_lower = (chunk["source_title"] or "").lower()
        citation_key_lower = (chunk["citation_key"] or "").lower()
        sec_num_lower = str(chunk["section_number"] or "").lower()

        score = 0.0

        # A. Exact Citation & Section Matching (Dominant hit)
        for sec in section_matches:
            clean_sec = re.sub(r"[^0-9a-z]", "", sec)
            if clean_sec and clean_sec in re.sub(r"[^0-9a-z]", "", sec_num_lower):
                score += 50.0
            if clean_sec and clean_sec in re.sub(r"[^0-9a-z]", "", citation_key_lower):
                score += 40.0

        # Code keywords
        if "bnss" in query_lower and ("bnss" in citation_key_lower or "nagarik" in chunk_title_lower):
            score += 25.0
        elif "bns" in query_lower and ("bns" in citation_key_lower or "nyaya" in chunk_title_lower):
            score += 25.0
        elif "ipc" in query_lower and "ipc" in citation_key_lower:
            score += 15.0
        elif "crpc" in query_lower and "crpc" in citation_key_lower:
            score += 15.0

        # B. Lexical Term Overlap
        for token in query_tokens:
            if token in ("the", "and", "for", "with", "under", "case"):
                continue
            if token in chunk_text_lower:
                score += 3.0
            if token in chunk_title_lower:
                score += 5.0

        # C. Rule-Based Authority & Lifecycle Prioritization
        if chunk["lifecycle_status"] == "active":
            score += 15.0
        elif chunk["lifecycle_status"] == "superseded":
            score -= 10.0  # Penalty so superseded documents are not mistaken for active law

        if "supreme court" in (chunk["issuing_authority"] or "").lower():
            score += 8.0
        elif "parliament" in (chunk["issuing_authority"] or "").lower():
            score += 6.0

        if any(w in query_lower for w in ("undertrial", "bail", "479", "custody", "detention")):
            if "479" in sec_num_lower or "undertrial" in chunk_text_lower:
                score += 20.0

        if score > 0:
            chunk["relevance_score"] = round(score, 2)
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    results = [item[1] for item in scored_chunks[:limit]]

    # Part H: Log retrieval telemetry
    try:
        query_id = f"qry_{uuid.uuid4().hex[:10]}"
        log_legal_retrieval(
            query_id=query_id,
            actor_id=actor_id,
            actor_role=actor_role,
            organization_id=organization_id,
            query_text=query,
            source_ids=[r.get("source_id") for r in results],
            source_versions=[r.get("version") for r in results],
            matched_citations=[r.get("citation_key") for r in results],
            relevance_scores=[r.get("relevance_score") for r in results],
            selected_passages=[r.get("id") for r in results],
            used_superseded=any(r.get("lifecycle_status") == "superseded" for r in results),
            grounding_score=0.0,
            routed_to_review=False,
            status="SUCCESS",
        )
    except Exception as e:
        print(f"[WARN] Failed to record retrieval telemetry: {e}")

    return results


# ── 4. CITATION INTEGRITY & DURABLE HUMAN-REVIEW ESCALATION ───────────────────

def verify_legal_citation_integrity(
    draft_statement: str,
    retrieved_passages: Optional[List[Dict[str, Any]]] = None,
    actor_id: str = "anonymous",
    actor_role: str = "unknown",
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Verify that legal assertions are grounded in approved active sources.
    
    PART G & P ENFORCEMENT:
    - Verifies citations against active legal chunks.
    - If unverified, unsupported, or invented citations are detected:
      1. Flags status = LEGAL_KNOWLEDGE_INSUFFICIENT
      2. Sets routed_to_human_review = True
      3. Persists a durable task in legal_human_review_tasks (idempotent)
      4. Creates a high-priority notification for supervising legal officers
      5. Writes an immutable audit_events record
    """
    if not draft_statement.strip():
        return {
            "status": "EMPTY",
            "grounding_score": 0.0,
            "citations_found": [],
            "routed_to_human_review": True,
            "message": "Empty draft statement provided.",
        }

    citation_pattern = re.compile(
        r"(?:Section|Sec\.|Article)\s*(?P<sec>[0-9]{1,4}(?:\([0-9A-Za-z]+\))*)\s*(?:of\s*(?:the\s*)?)?(?P<statute>BNSS|BNS|IPC|CrPC|Bharatiya\s+[A-Za-z]+|Indian\s+Penal\s+Code)?",
        re.IGNORECASE,
    )

    found_citations = []
    for match in citation_pattern.finditer(draft_statement):
        sec = match.group("sec")
        statute = match.group("statute") or "Unspecified"
        found_citations.append({
            "raw_text": match.group(0),
            "section": sec,
            "statute": statute.upper().replace(" ", "_"),
        })

    if retrieved_passages is None:
        retrieved_passages = hybrid_retrieve_legal_chunks(
            query=draft_statement,
            limit=6,
            actor_id=actor_id,
            actor_role=actor_role,
        )

    # Active verified citation keys and exact section numbers present in retrieved passages
    active_keys = set()
    active_sections = set()
    for p in retrieved_passages:
        if p.get("lifecycle_status") == "active":
            if p.get("citation_key"):
                active_keys.add(p["citation_key"].upper())
            sec = p.get("section_number")
            if sec:
                clean_sec = re.sub(r"[^0-9a-z]", "", str(sec).lower()).replace("section", "").replace("sec", "").strip()
                if clean_sec:
                    active_sections.add(clean_sec)

    verified_citations = []
    unsupported_citations = []

    for cit in found_citations:
        clean_cit_sec = re.sub(r"[^0-9a-z]", "", cit["section"].lower()).replace("section", "").replace("sec", "").strip()
        matched = False
        if clean_cit_sec:
            for a_sec in active_sections:
                if clean_cit_sec == a_sec:
                    matched = True
                    break


        if matched:
            verified_citations.append(cit)
        else:
            unsupported_citations.append(cit)

    total_citations = len(found_citations)
    if total_citations == 0:
        substantive_terms = ["bail", "undertrial", "imprisonment", "detention", "surety", "custody"]
        has_legal_claim = any(term in draft_statement.lower() for term in substantive_terms)

        if has_legal_claim and not retrieved_passages:
            grounding_score = 0.0
            status = "LEGAL_KNOWLEDGE_INSUFFICIENT"
            routed_to_human_review = True
            msg = "Substantive legal relief asserted without statutory citations or supporting active passages. Escalating to human legal review."
        else:
            grounding_score = 85.0 if retrieved_passages else 50.0
            status = "VERIFIED" if retrieved_passages else "LEGAL_KNOWLEDGE_INSUFFICIENT"
            routed_to_human_review = not bool(retrieved_passages)
            msg = "General legal text analyzed against active statutory passages."
    else:
        # Part P: Multi-part assertion hardening: ANY unverified citation triggers failure
        grounding_score = round((len(verified_citations) / total_citations) * 100.0, 1)
        if len(unsupported_citations) == 0 and grounding_score >= 80.0:
            status = "VERIFIED"
            routed_to_human_review = False
            msg = f"All {len(verified_citations)} legal citations verified against active statutory authority."
        else:
            status = "LEGAL_KNOWLEDGE_INSUFFICIENT"
            routed_to_human_review = True
            unsupported_labels = [c["raw_text"] for c in unsupported_citations]
            msg = f"Statutory Guardrail Alert: {len(unsupported_citations)} ungrounded or invented citations detected: {unsupported_labels}. Routed to human legal review."

    # Part G: Create durable persistent human-review escalation task
    escalation_record = None
    if routed_to_human_review:
        try:
            escalation_record = create_legal_escalation(
                actor_id=actor_id,
                actor_role=actor_role,
                draft_statement=draft_statement,
                unsupported_citations=unsupported_citations,
                retrieved_context=[
                    {"citation_key": p.get("citation_key"), "source_title": p.get("source_title")}
                    for p in retrieved_passages[:3]
                ],
                grounding_score=grounding_score,
                escalation_reason=msg,
                case_id=case_id,
            )

            # Part I: Record structured audit log for escalation
            audit_repo.record(
                actor_id=actor_id,
                actor_role=actor_role,
                action=AuditAction.SECURITY_ALERT,
                entity_type="LEGAL_CITATION_ESCALATION",
                entity_id=escalation_record["id"] if escalation_record else "esc_unknown",
                details={
                    "grounding_score": grounding_score,
                    "unsupported_citations": [c.get("raw_text") for c in unsupported_citations],
                    "escalation_reason": msg,
                    "case_id": case_id,
                },
            )
        except Exception as e:
            print(f"[WARN] Failed to persist citation escalation: {e}")

    return {
        "status": status,
        "grounding_score": grounding_score,
        "verified_citations": verified_citations,
        "unsupported_citations": unsupported_citations,
        "routed_to_human_review": routed_to_human_review,
        "escalation_id": escalation_record.get("id") if escalation_record else None,
        "grounding_passages_count": len(retrieved_passages),
        "message": msg,
        "retrieved_sources": [
            {
                "citation_key": p.get("citation_key"),
                "source_title": p.get("source_title"),
                "section": p.get("section_number"),
                "document_hash": p.get("document_hash"),
                "relevance_score": p.get("relevance_score"),
            }
            for p in retrieved_passages[:3]
        ],
    }


# ── 5. RETRIEVAL EVALUATION BENCHMARK SUITE ───────────────────────────────────

def run_retrieval_evaluation_suite(
    actor_id: str = "system",
    actor_role: str = "SUPERVISING_LEGAL_OFFICER",
) -> Dict[str, Any]:
    """Execute evaluation queries across all 5 representative legal categories.
    
    Part Q: Measures Recall@1, Recall@3, MRR and records audit telemetry.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM legal_evaluation_benchmarks ORDER BY query_category ASC")
    benchmarks = [dict(b) for b in cursor.fetchall()]
    conn.close()

    if not benchmarks:
        return {"total_queries": 0, "recall_at_1": 0.0, "recall_at_3": 0.0, "mrr": 0.0, "results": []}

    results: List[Dict[str, Any]] = []
    hits_at_1 = 0
    hits_at_3 = 0
    reciprocal_ranks = []

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for bench in benchmarks:
        q = bench["query_text"]
        expected_sources = json.loads(bench["expected_source_ids_json"])
        expected_citations = json.loads(bench["expected_citation_keys_json"])

        retrieved = hybrid_retrieve_legal_chunks(q, limit=5, actor_id=actor_id, actor_role=actor_role)
        retrieved_keys = [r.get("citation_key") for r in retrieved]
        retrieved_sources = [r.get("source_id") for r in retrieved]

        # Calculate rank
        first_match_rank = None
        for rank, r in enumerate(retrieved, start=1):
            s_match = r.get("source_id") in expected_sources
            c_match = any(ec in (r.get("citation_key") or "") for ec in expected_citations)
            if s_match or c_match:
                first_match_rank = rank
                break

        if first_match_rank == 1:
            hits_at_1 += 1
            hits_at_3 += 1
            rr = 1.0
        elif first_match_rank and first_match_rank <= 3:
            hits_at_3 += 1
            rr = 1.0 / first_match_rank
        elif first_match_rank:
            rr = 1.0 / first_match_rank
        else:
            rr = 0.0

        reciprocal_ranks.append(rr)

        results.append({
            "id": bench["id"],
            "query_category": bench["query_category"],
            "query_text": q,
            "target_statute": bench.get("target_statute"),
            "expected_citations": expected_citations,
            "top_retrieved_key": retrieved_keys[0] if retrieved_keys else None,
            "rank": first_match_rank,
            "reciprocal_rank": round(rr, 2),
            "hit_at_3": bool(first_match_rank and first_match_rank <= 3),
        })

    # Batch update historical scores
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        for res in results:
            cursor.execute(
                "UPDATE legal_evaluation_benchmarks SET last_recall_score = ?, last_evaluated_at = ? WHERE id = ?",
                (res["reciprocal_rank"], now_iso, res["id"]),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[WARN] Failed to update benchmark scores: {e}")


    total = len(benchmarks)
    recall_at_1 = round((hits_at_1 / total) * 100.0, 1)
    recall_at_3 = round((hits_at_3 / total) * 100.0, 1)
    mrr = round(sum(reciprocal_ranks) / total, 3)

    # Part Q: Record audit log for benchmark execution
    try:
        audit_repo.record(
            actor_id=actor_id,
            actor_role=actor_role,
            action=AuditAction.DATA_EXPORT,
            entity_type="LEGAL_BENCHMARK_SUITE",
            entity_id=f"bench_run_{now_iso[:10]}",
            details={
                "recall_at_1": recall_at_1,
                "recall_at_3": recall_at_3,
                "mean_reciprocal_rank": mrr,
                "total_queries": total,
            },
        )
    except Exception as e:
        print(f"[WARN] Failed to audit benchmark execution: {e}")

    return {
        "total_queries": total,
        "recall_at_1": recall_at_1,
        "recall_at_3": recall_at_3,
        "mean_reciprocal_rank": mrr,
        "evaluation_timestamp": now_iso,
        "results": results,
    }
