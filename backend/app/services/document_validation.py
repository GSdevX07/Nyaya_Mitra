"""
document_validation.py - Pre-Approval Readiness & Gating Engine for Nyaya Mitra.
================================================================================
Enforces strict quality and grounding gates before legal documents can be approved:
1. Unsupported Factual Claims: compares assertions against exact case facts.
2. Uncited Legal Assertions: verifies cited statutory sections against retrieved sources.
3. Missing Required Fields: flags unresolved template tokens and mandatory blanks.
4. Template Mismatch: validates required formal structure and mandatory headings.
5. Document Prerequisites: verifies mandatory custody records and remand evidence.
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

STATUTORY_REF_PATTERN = re.compile(
    r"\b(?:Section|Sec\.?)\s+(\d+[A-Z]?)\b|"
    r"\b(?:Article|Art\.?)\s+(\d+[A-Z]?)\b|"
    r"\b(?:Rule)\s+(\d+)\b",
    re.IGNORECASE
)

MISSING_TOKEN_PATTERN = re.compile(r"\[MISSING:\s*([A-Z0-9_]+)\]|___+")


class DocumentReadinessChecker:
    """Evaluates readiness of a legal document draft for human sign-off."""

    @classmethod
    def validate_draft(
        cls,
        draft_dict: Dict[str, Any],
        case_data: Optional[Dict[str, Any]] = None,
        template: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute comprehensive validation suite.
        Returns report with can_approve boolean, blocking issues, warnings, and itemized checks.
        """
        content_text = draft_dict.get("content_text", "")
        exact_case_facts = draft_dict.get("exact_case_facts", {}) or (case_data or {})
        source_docs = draft_dict.get("source_documents", [])
        retrieved_sources = draft_dict.get("retrieved_legal_sources", [])

        blocking_issues: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        # 1. Missing Required Fields Check
        missing_field_findings = cls._check_missing_fields(content_text, exact_case_facts, template)
        if missing_field_findings["blocking"]:
            blocking_issues.extend(missing_field_findings["issues"])
        warnings.extend(missing_field_findings["warnings"])

        # 2. Unsupported Factual Claims Check
        factual_findings = cls._check_unsupported_facts(content_text, exact_case_facts)
        blocking_issues.extend(factual_findings["issues"])
        warnings.extend(factual_findings["warnings"])

        # 3. Uncited Legal Assertions Check
        legal_findings = cls._check_uncited_legal_assertions(
            content_text,
            retrieved_sources,
            template,
            exact_case_facts,
            draft_dict.get("source_citations"),
        )
        blocking_issues.extend(legal_findings["issues"])
        warnings.extend(legal_findings["warnings"])

        # 4. Template Structural Mismatch Check
        template_findings = cls._check_template_mismatch(content_text, template)
        if template_findings["blocking"]:
            blocking_issues.extend(template_findings["issues"])
        warnings.extend(template_findings["warnings"])

        # 5. Mandatory Documentary Evidence Check
        evidence_findings = cls._check_documentary_evidence(exact_case_facts, source_docs, template)
        if evidence_findings["blocking"]:
            blocking_issues.extend(evidence_findings["issues"])
        warnings.extend(evidence_findings["warnings"])

        can_approve = len(blocking_issues) == 0

        summary_status = "CLEARED" if can_approve else "BLOCKED"

        return {
            "can_approve": can_approve,
            "status": summary_status,
            "total_blocking_issues": len(blocking_issues),
            "total_warnings": len(warnings),
            "blocking_issues": blocking_issues,
            "warnings": warnings,
            "checks": {
                "missing_fields": {
                    "passed": len(missing_field_findings["issues"]) == 0,
                    "count": len(missing_field_findings["issues"]),
                },
                "factual_grounding": {
                    "passed": len(factual_findings["issues"]) == 0,
                    "count": len(factual_findings["issues"]),
                },
                "statutory_citations": {
                    "passed": len(legal_findings["issues"]) == 0,
                    "count": len(legal_findings["issues"]),
                },
                "template_conformance": {
                    "passed": len(template_findings["issues"]) == 0,
                    "count": len(template_findings["issues"]),
                },
                "documentary_evidence": {
                    "passed": len(evidence_findings["issues"]) == 0,
                    "count": len(evidence_findings["issues"]),
                },
            },
        }

    @classmethod
    def _check_missing_fields(
        cls,
        text: str,
        case_facts: Dict[str, Any],
        template: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Detect unresolved template tokens or missing mandatory case facts."""
        issues: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        # Find explicit missing tokens in text like [MISSING: FIR_NUMBER]
        matches = MISSING_TOKEN_PATTERN.findall(text)
        for token in matches:
            if token:
                issues.append({
                    "category": "MISSING_REQUIRED_FIELD",
                    "severity": "BLOCKING",
                    "field": token.lower(),
                    "message": f"Mandatory field '{token}' is unresolved in document text. Replace '[MISSING: {token}]' with verified fact.",
                })

        # Check template required_fields if template is attached
        if template and template.get("required_fields"):
            for field in template["required_fields"]:
                val = case_facts.get(field)
                if val is None and field == "accused_name":
                    val = case_facts.get("name")
                elif val is None and field == "fir_number":
                    val = case_facts.get("fir_no")
                elif val is None and field == "assigned_lawyer":
                    val = case_facts.get("assigned_advocate") or case_facts.get("lawyer_name")

                if val is None or (isinstance(val, str) and not val.strip()):
                    issues.append({
                        "category": "MISSING_CASE_FACT",
                        "severity": "BLOCKING",
                        "field": field,
                        "message": f"Required case attribute '{field}' is missing from the case record.",
                    })

        return {"blocking": len(issues) > 0, "issues": issues, "warnings": warnings}

    @classmethod
    def _check_unsupported_facts(
        cls,
        text: str,
        case_facts: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Detect potential factual hallucinations or discrepancies with case facts."""
        issues: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        accused_name = (case_facts.get("name") or case_facts.get("accused_name") or "").strip()
        clean_name = re.sub(r"\s*\(.*?\)", "", accused_name).strip()
        if clean_name and len(clean_name) > 3:
            # Check if clean name or first name appears in draft
            first_name = clean_name.split()[0].lower()
            if clean_name.lower() not in text.lower() and first_name not in text.lower():
                issues.append({
                    "category": "UNSUPPORTED_FACTUAL_CLAIM",
                    "severity": "BLOCKING",
                    "field": "accused_name",
                    "message": f"Accused name '{clean_name}' does not appear in the draft petition body.",
                })

        # Check custody days match
        custody_days = case_facts.get("custody_days")
        if custody_days is not None:
            # Check if text claims an exaggerated or contradictory custody duration
            # Look for patterns like "(\d+) days"
            found_day_mentions = re.findall(r"\b(\d{1,5})\s+days\b", text, re.IGNORECASE)
            day_ints = [int(m) for m in found_day_mentions if m.isdigit()]
            # If custody_days is not in any of the day mentions, generate warning
            if day_ints and custody_days not in day_ints:
                warnings.append({
                    "category": "FACTUAL_DISCREPANCY",
                    "severity": "WARNING",
                    "field": "custody_days",
                    "message": f"Case record indicates {custody_days} custody days, but draft mentions {day_ints}. Verify detention computation.",
                })

        # Check FIR number
        fir_num = case_facts.get("fir_number") or case_facts.get("fir_no")
        if fir_num and len(fir_num) > 2 and "not recorded" not in fir_num.lower():
            if fir_num.lower() not in text.lower():
                warnings.append({
                    "category": "FACTUAL_OMISSION",
                    "severity": "WARNING",
                    "field": "fir_number",
                    "message": f"FIR Number '{fir_num}' is recorded on file but not referenced in the draft.",
                })

        return {"issues": issues, "warnings": warnings}

    @classmethod
    def _check_uncited_legal_assertions(
        cls,
        text: str,
        retrieved_sources: List[Dict[str, Any]],
        template: Optional[Dict[str, Any]],
        case_facts: Optional[Dict[str, Any]] = None,
        source_citations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Detect legal citations in draft that have no grounding in retrieved authorities or case facts."""
        issues: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        # Extract all section numbers mentioned in text
        matches = STATUTORY_REF_PATTERN.findall(text)
        cited_sections = set()
        for m in matches:
            sec = m[0] or m[1] or m[2]
            if sec:
                cited_sections.add(sec)

        # Build corpus of retrieved authority texts
        source_texts = []
        for src in retrieved_sources:
            if isinstance(src, dict):
                source_texts.append(src.get("statute_text", ""))
                source_texts.append(src.get("query_text", ""))
                source_texts.append(src.get("citation_key", ""))
                source_texts.append(src.get("title", ""))
            elif isinstance(src, str):
                source_texts.append(src)
        corpus = " ".join(source_texts).lower()

        # Add statutory ground from template if available
        if template and template.get("statutory_ground"):
            corpus += " " + template["statutory_ground"].lower()

        # Add source citations if present
        if source_citations:
            for sc in source_citations:
                if isinstance(sc, dict):
                    corpus += " " + str(sc.get("section", "")).lower() + " " + str(sc.get("statute", "")).lower()

        # Add offense sections from case facts
        if case_facts and case_facts.get("offense_sections"):
            off_sec = case_facts["offense_sections"]
            if isinstance(off_sec, list):
                for sec_str in off_sec:
                    corpus += " " + str(sec_str).lower()
            else:
                corpus += " " + str(off_sec).lower()

        for sec in cited_sections:
            sec_clean = sec.strip()
            if sec_clean.lower() not in corpus:
                issues.append({
                    "category": "UNCITED_LEGAL_ASSERTION",
                    "severity": "BLOCKING",
                    "citation": f"Section/Article {sec}",
                    "message": f"Section/Article {sec} is cited in the draft but is not grounded in any retrieved legal source, template statutory ground, or charged case offense.",
                })

        return {"issues": issues, "warnings": warnings}

    @classmethod
    def _check_template_mismatch(
        cls,
        text: str,
        template: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Verify presence of essential formal petition sections."""
        issues: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        mandatory_markers = [
            ("PRAYER", "Prayer clause is missing. Every formal court petition must contain an explicit relief prayer."),
            ("MOST RESPECTFULLY SHOWETH", "Formal statement of grounds ('MOST RESPECTFULLY SHOWETH') is missing."),
        ]

        text_upper = text.upper()
        for marker, errMsg in mandatory_markers:
            if marker not in text_upper:
                issues.append({
                    "category": "TEMPLATE_STRUCTURE_MISMATCH",
                    "severity": "BLOCKING",
                    "element": marker,
                    "message": errMsg,
                })

        return {"blocking": len(issues) > 0, "issues": issues, "warnings": warnings}

    @classmethod
    def _check_documentary_evidence(
        cls,
        case_facts: Dict[str, Any],
        source_docs: List[Dict[str, Any]],
        template: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Verify presence of required underlying evidence records."""
        issues: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []

        present_doc_types = set()
        for d in case_facts.get("present_docs", []):
            present_doc_types.add(str(d).lower())
        for doc_obj in source_docs:
            if isinstance(doc_obj, dict) and doc_obj.get("document_type"):
                present_doc_types.add(str(doc_obj["document_type"]).lower())

        required_docs = (
            template.get("required_documents")
            if (template and template.get("required_documents"))
            else ["remand_order", "custody_certificate"]
        )

        for req in required_docs:
            req_clean = req.lower().replace(" ", "_")
            matches = any(req_clean in p or p in req_clean for p in present_doc_types)
            if not matches:
                # Mandatory judicial arrest / detention prerequisite: remand_order
                if req_clean == "remand_order":
                    issues.append({
                        "category": "MISSING_PREREQUISITE_EVIDENCE",
                        "severity": "BLOCKING",
                        "document_type": req,
                        "message": f"Mandatory evidence document '{req}' has not been uploaded or verified. Official court filing requires verified remand order.",
                    })
                else:
                    warnings.append({
                        "category": "RECOMMENDED_EVIDENCE_ABSENT",
                        "severity": "WARNING",
                        "document_type": req,
                        "message": f"Prerequisite document '{req}' is pending verification. Ensure physical certificate is obtained before hearing.",
                    })

        return {"blocking": len(issues) > 0, "issues": issues, "warnings": warnings}
