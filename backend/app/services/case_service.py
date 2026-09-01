"""
case_service.py - Domain Service Layer for Accused-Centric Legal Services Operations.
"""

from __future__ import annotations
import datetime
from typing import List, Optional, Dict, Any
from app.models.schemas import CaseRecord, CaseState, TimelineEvent
from app.models.domain import AuditAction
from app.repositories.case_repository import CaseRepository
from app.repositories.audit_repository import AuditRepository
from app.agents.eligibility_agent import evaluate_eligibility
from app.agents.completeness_agent import evaluate_completeness


class CaseService:
    def __init__(self, case_repo: CaseRepository, audit_repo: AuditRepository):
        self.case_repo = case_repo
        self.audit_repo = audit_repo

    def list_cases(self) -> List[CaseRecord]:
        return self.case_repo.get_all_cases()

    def get_case(self, case_id: str) -> Optional[CaseRecord]:
        return self.case_repo.get_case_by_id(case_id)

    def get_case_full_dossier(self, case_id: str) -> Optional[Dict[str, Any]]:
        from app.agents.orchestrator import process_case
        case = self.case_repo.get_case_by_id(case_id)
        if not case:
            return None
        return process_case(case)

    def approve_case_for_filing(self, case_id: str, lawyer_id: str = "Legal Officer 104") -> Dict[str, Any]:
        case = self.case_repo.get_case_by_id(case_id)
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        # Evaluate eligibility & completeness rules
        eligibility = evaluate_eligibility(case)
        completeness = evaluate_completeness(case)

        if not eligibility.get("is_eligible", False):
            raise ValueError(
                f"Cannot approve case {case_id}: Ineligible under Section 479 BNSS. "
                + "; ".join(eligibility.get("reasons", []))
            )

        if not completeness.get("is_complete", False):
            missing = ", ".join(completeness.get("missing_docs", []))
            raise ValueError(
                f"Cannot approve case {case_id}: Missing mandatory documents [{missing}]. All required documents must be on record."
            )

        # Transition status
        success = self.case_repo.update_case_status(
            case_id=case_id,
            new_status=CaseState.APPROVED_READY_FOR_FILING,
            actor_id=lawyer_id,
        )
        if not success:
            raise RuntimeError("Database update failed during approval.")

        # Record immutable audit event
        self.audit_repo.record(
            actor_id=lawyer_id,
            actor_role="LEGAL_AID_ADVOCATE",
            action=AuditAction.ADVOCATE_SIGN_OFF,
            entity_type="COURT_CASE",
            entity_id=case_id,
            details={
                "previous_status": case.status.value,
                "new_status": CaseState.APPROVED_READY_FOR_FILING.value,
                "statutory_threshold": eligibility.get("statutory_threshold_fraction"),
                "countable_custody_days": eligibility.get("countable_custody_days"),
            },
        )

        return {
            "status": "success",
            "message": f"Case {case_id} approved and marked ready for filing by {lawyer_id}.",
            "new_status": CaseState.APPROVED_READY_FOR_FILING.value,
            "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    def record_court_filing(self, case_id: str, filing_reference: Optional[str] = None, actor_id: str = "Legal Officer 104") -> Dict[str, Any]:
        case = self.case_repo.get_case_by_id(case_id)
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ref = filing_reference or f"PET-479-{case_id}-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M')}"

        success = self.case_repo.update_case_status(
            case_id=case_id,
            new_status=CaseState.FILED,
            actor_id=actor_id,
        )
        if not success:
            raise RuntimeError("Database update failed during filing recording.")

        # Append specific court filing event to timeline
        case = self.case_repo.get_case_by_id(case_id)
        if case:
            case.timeline.append(
                TimelineEvent(
                    id=f"TLE-{case_id}-FILING",
                    timestamp=now_iso,
                    event_type="FILING",
                    title="Bail Application Filed in Remand Court",
                    description=f"Section 479 petition officially lodged. Registry Filing Reference: {ref}",
                    actor=actor_id,
                    actor_role="Advocate on Record",
                    source="Court Registry E-Filing",
                    is_human_verified=True,
                )
            )
            self.case_repo.update_case_status(case_id, CaseState.FILED, actor_id)

        # Record immutable audit event
        self.audit_repo.record(
            actor_id=actor_id,
            actor_role="LEGAL_AID_ADVOCATE",
            action=AuditAction.COURT_FILING_RECORDED,
            entity_type="COURT_CASE",
            entity_id=case_id,
            details={"filing_reference": ref, "timestamp": now_iso},
        )

        return {
            "status": "success",
            "message": f"Case {case_id} marked as filed in court.",
            "filing_reference": ref,
            "new_status": CaseState.FILED.value,
            "timestamp": now_iso,
        }
