"""
app.workflow.state_machine - Authoritative State Machine & Transition Rules.
=============================================================================
Defines the canonical 16-state matter lifecycle, 4 explicit exception states,
and the immutable transition matrix with strict Nyaya Mitra role ownership.

MANDATORY ROLE OWNERSHIP:
- JAIL_OFFICER: Custody/intake updates, prison-origin records, legal-aid referral
- POLICE_OFFICER: Police-origin records and police workflow updates
- DLSA_OFFICER: Legal-aid intake review, counsel appointment, coordination
- DEFENSE_ADVOCATE: Assigned-case legal drafting, counsel sign-off, submission for supervisory review, court filing
- SUPERVISING_LEGAL_OFFICER: Supervisory review, institutional approval, high-impact approval, exception resolution
- GOV_ADMIN: State-level governance oversight only; no routine case transitions
- PLATFORM_ADMIN: Technical administration only; no legal approvals, counsel appointments, or judicial actions
- READ_ONLY_AUDITOR: Read-only audit/oversight; no mutations
- ACCUSED_USER: Own case/status read-only view
- FAMILY_GUARDIAN: Linked-case status read-only view
- CONTROLLED_EXTERNAL_ADVOCATE: Authorized shared records only
- INTEGRATION_SERVICE / SYSTEM: Automated deterministic engine/sync transitions

SUBMITTED vs APPROVED vs FILED:
- SUBMITTED: Defence Advocate has completed and signed off counsel work product and submitted it into institutional review.
- APPROVED: Supervising Legal Officer has reviewed and approved the exact filing artifact version.
- FILED: Authorized counsel/filing actor has actually lodged the approved filing through court registry/eCourts with filing reference.
Court independently decides judicial outcome; Nyaya Mitra records court orders, not judicial pronouncements.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set, Dict, Any, Optional
from enum import Enum

from app.models.schemas import MatterState
from app.auth.roles import Role


@dataclass(frozen=True)
class TransitionRule:
    """Authoritative specification of a single permitted state transition."""
    action: str
    from_states: List[MatterState]
    to_state: MatterState
    allowed_roles: Set[Role]
    description: str
    required_payload_keys: List[str] = field(default_factory=list)
    requires_artifact_approval: bool = False
    ai_permitted: bool = False
    is_exception_transition: bool = False
    audit_event_type: str = "MATTER_STATE_TRANSITION"


# ── Canonical Transition Engine Definitions ───────────────────────────────────

TRANSITION_RULES: List[TransitionRule] = [
    # 1. INTAKE -> VERIFICATION
    TransitionRule(
        action="START_VERIFICATION",
        from_states=[MatterState.INTAKE],
        to_state=MatterState.VERIFICATION,
        allowed_roles={Role.DLSA_OFFICER, Role.JAIL_OFFICER},
        description="Move newly received custody or police intake record into legal-aid verification.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 2. VERIFICATION -> REVIEW
    TransitionRule(
        action="SUBMIT_FOR_REVIEW",
        from_states=[MatterState.VERIFICATION],
        to_state=MatterState.REVIEW,
        allowed_roles={Role.DLSA_OFFICER},
        description="DLSA officer confirms identity and document completeness; submits for legal-aid review.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 3. REVIEW -> LEGAL_AID_REQUIRED
    TransitionRule(
        action="FLAG_LEGAL_AID_REQUIRED",
        from_states=[MatterState.REVIEW],
        to_state=MatterState.LEGAL_AID_REQUIRED,
        allowed_roles={Role.DLSA_OFFICER, Role.SUPERVISING_LEGAL_OFFICER},
        description="Institutional legal review identifies that undertrial requires legal aid defense counsel.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 4. LEGAL_AID_REQUIRED -> ASSIGNED
    TransitionRule(
        action="ASSIGN_COUNSEL",
        from_states=[MatterState.LEGAL_AID_REQUIRED],
        to_state=MatterState.ASSIGNED,
        allowed_roles={Role.DLSA_OFFICER},  # Strict: PLATFORM_ADMIN / GOV_ADMIN cannot appoint counsel
        description="DLSA formally assigns a panel defense advocate to the matter.",
        required_payload_keys=["assigned_advocate_id"],
        ai_permitted=False,
    ),

    # 5. ASSIGNED -> DOCUMENT_PENDING
    TransitionRule(
        action="REQUEST_DOCUMENTS",
        from_states=[MatterState.ASSIGNED],
        to_state=MatterState.DOCUMENT_PENDING,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.DLSA_OFFICER},
        description="Assigned advocate flags missing records (charge-sheet, remand sheet, custody certificate).",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 6. DOCUMENT_PENDING / ASSIGNED -> ANALYSIS_READY
    # Strict Stage 8 Boundary: Section 479 rules / AI analysis moves state to ANALYSIS_READY only!
    TransitionRule(
        action="COMPLETE_ANALYSIS",
        from_states=[MatterState.DOCUMENT_PENDING, MatterState.ASSIGNED],
        to_state=MatterState.ANALYSIS_READY,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.DLSA_OFFICER, Role.INTEGRATION_SERVICE},
        description="Documents verified; deterministic statutory rules engine evaluation completed.",
        required_payload_keys=[],
        ai_permitted=True,  # Automated rules engine / AI background job allowed
    ),

    # 7. ANALYSIS_READY -> HUMAN_REVIEW
    TransitionRule(
        action="SUBMIT_FOR_HUMAN_REVIEW",
        from_states=[MatterState.ANALYSIS_READY],
        to_state=MatterState.HUMAN_REVIEW,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER},
        description="Defense advocate takes up analysis results to prepare and review petition draft.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 8. HUMAN_REVIEW -> SUBMITTED (Defence Advocate counsel sign-off)
    TransitionRule(
        action="COUNSEL_SIGN_OFF",
        from_states=[MatterState.HUMAN_REVIEW],
        to_state=MatterState.SUBMITTED,
        allowed_roles={Role.DEFENSE_ADVOCATE},
        description="Defense Advocate completes legal draft, signs off work product, and submits for supervisory review.",
        required_payload_keys=["artifact_version_id"],
        ai_permitted=False,
    ),
    TransitionRule(
        action="SUBMIT_FOR_SUPERVISORY_REVIEW",
        from_states=[MatterState.HUMAN_REVIEW],
        to_state=MatterState.SUBMITTED,
        allowed_roles={Role.DEFENSE_ADVOCATE},
        description="Alias: Defense Advocate submits signed counsel work product for supervisory review.",
        required_payload_keys=["artifact_version_id"],
        ai_permitted=False,
    ),

    # 9. SUBMITTED -> APPROVED (Supervising Legal Officer review of exact artifact version)
    TransitionRule(
        action="SUPERVISORY_APPROVE",
        from_states=[MatterState.SUBMITTED, MatterState.HUMAN_REVIEW],
        to_state=MatterState.APPROVED,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER},
        description="Supervising Legal Officer verifies exact artifact version and issues institutional approval.",
        required_payload_keys=["artifact_version_id"],
        requires_artifact_approval=True,
        ai_permitted=False,  # AI CAN NEVER APPROVE!
    ),
    TransitionRule(
        action="APPROVE_MATTER",
        from_states=[MatterState.SUBMITTED, MatterState.HUMAN_REVIEW],
        to_state=MatterState.APPROVED,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER},
        description="Alias: Supervising Legal Officer formally approves the matter.",
        required_payload_keys=["artifact_version_id"],
        requires_artifact_approval=True,
        ai_permitted=False,
    ),

    # Supervisory Revisions (SUBMITTED / APPROVED -> back to HUMAN_REVIEW)
    TransitionRule(
        action="REQUEST_REVISIONS",
        from_states=[MatterState.SUBMITTED, MatterState.APPROVED],
        to_state=MatterState.HUMAN_REVIEW,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER},
        description="Supervising Legal Officer returns draft to assigned advocate with requested revisions.",
        required_payload_keys=["comment"],
        ai_permitted=False,
    ),

    # 10. APPROVED -> SUBMITTED (Registry Submission step if separate from filing confirmation)
    TransitionRule(
        action="SUBMIT_TO_REGISTRY",
        from_states=[MatterState.APPROVED],
        to_state=MatterState.SUBMITTED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.INTEGRATION_SERVICE},
        description="Lodge filing packet with the court registry pending institutional filing acknowledgement.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 11. APPROVED / SUBMITTED -> FILED (Lodged through authorized court registry / eCourts process)
    TransitionRule(
        action="RECORD_FILING",
        from_states=[MatterState.APPROVED, MatterState.SUBMITTED],
        to_state=MatterState.FILED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.INTEGRATION_SERVICE},  # Authorized filing actor or eCourts
        description="Authorized filing actor lodges approved petition in court with authentic filing/CNR reference.",
        required_payload_keys=["filing_reference"],
        requires_artifact_approval=True,  # Cannot file without prior supervisor approval!
        ai_permitted=False,  # AI CAN NEVER FILE!
    ),
    TransitionRule(
        action="LODGE_COURT_FILING",
        from_states=[MatterState.APPROVED, MatterState.SUBMITTED],
        to_state=MatterState.FILED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.INTEGRATION_SERVICE},
        description="Alias: Lodging approved petition with court registry and recording filing acknowledgement.",
        required_payload_keys=["filing_reference"],
        requires_artifact_approval=True,
        ai_permitted=False,
    ),

    # 12. FILED -> HEARING_SCHEDULED
    TransitionRule(
        action="SCHEDULE_HEARING",
        from_states=[MatterState.FILED],
        to_state=MatterState.HEARING_SCHEDULED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.DLSA_OFFICER, Role.INTEGRATION_SERVICE},
        description="Court registry lists matter for judicial hearing.",
        required_payload_keys=["hearing_date"],
        ai_permitted=False,
    ),

    # 13. HEARING_SCHEDULED -> ORDER_RECEIVED
    # Nyaya Mitra records court order; does not pronounce or simulate judicial discretion!
    TransitionRule(
        action="RECORD_COURT_ORDER",
        from_states=[MatterState.HEARING_SCHEDULED],
        to_state=MatterState.ORDER_RECEIVED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER, Role.INTEGRATION_SERVICE},
        description="Record judicial order pronounced by the competent court (bail granted/rejected).",
        required_payload_keys=["order_type", "order_date"],
        ai_permitted=False,
    ),

    # 14. ORDER_RECEIVED -> RELEASE_WORKFLOW
    TransitionRule(
        action="INITIATE_RELEASE",
        from_states=[MatterState.ORDER_RECEIVED],
        to_state=MatterState.RELEASE_WORKFLOW,
        allowed_roles={Role.JAIL_OFFICER, Role.DLSA_OFFICER, Role.DEFENSE_ADVOCATE},
        description="Court has granted bail/release; initiate prison release and surety verification formalities.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 15. RELEASE_WORKFLOW -> POST_RELEASE_FOLLOW_UP
    TransitionRule(
        action="CONFIRM_RELEASE",
        from_states=[MatterState.RELEASE_WORKFLOW],
        to_state=MatterState.POST_RELEASE_FOLLOW_UP,
        allowed_roles={Role.JAIL_OFFICER, Role.DLSA_OFFICER},
        description="Undertrial released from prison; preserve dossier for trial appearance follow-up.",
        required_payload_keys=["release_date"],
        ai_permitted=False,
    ),
    TransitionRule(
        action="START_POST_RELEASE_FOLLOW_UP",
        from_states=[MatterState.RELEASE_WORKFLOW],
        to_state=MatterState.POST_RELEASE_FOLLOW_UP,
        allowed_roles={Role.JAIL_OFFICER, Role.DLSA_OFFICER},
        description="Alias: Transition to post-release follow up and legal continuity preservation.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 16. POST_RELEASE_FOLLOW_UP -> CLOSED
    TransitionRule(
        action="CLOSE_MATTER",
        from_states=[MatterState.POST_RELEASE_FOLLOW_UP],
        to_state=MatterState.CLOSED,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER},
        description="All legal-aid, trial monitoring, and supervisory obligations formally concluded.",
        required_payload_keys=["closure_reason"],
        ai_permitted=False,
    ),

    # ── Exception State Transitions ───────────────────────────────────────────

    # Escalate to MANUAL_REVIEW_REQUIRED from any non-closed state
    TransitionRule(
        action="ESCALATE_MANUAL_REVIEW",
        from_states=[s for s in MatterState if s != MatterState.CLOSED and s != MatterState.MANUAL_REVIEW_REQUIRED],
        to_state=MatterState.MANUAL_REVIEW_REQUIRED,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER, Role.DEFENSE_ADVOCATE},
        description="Escalate ambiguous statutory questions, complex provisos, or health concerns to human supervisor.",
        required_payload_keys=["reason"],
        is_exception_transition=True,
    ),

    # Flag DATA_CONFLICT from any non-closed state
    TransitionRule(
        action="FLAG_DATA_CONFLICT",
        from_states=[s for s in MatterState if s != MatterState.CLOSED and s != MatterState.DATA_CONFLICT],
        to_state=MatterState.DATA_CONFLICT,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER, Role.POLICE_OFFICER, Role.JAIL_OFFICER, Role.INTEGRATION_SERVICE},
        description="Flag contradictory dates, FIR discrepancies, or identity mismatches across police/jail/court records.",
        required_payload_keys=["conflict_details"],
        is_exception_transition=True,
    ),

    # Block transition
    TransitionRule(
        action="BLOCK_TRANSITION",
        from_states=[s for s in MatterState if s != MatterState.CLOSED and s != MatterState.TRANSITION_BLOCKED],
        to_state=MatterState.TRANSITION_BLOCKED,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER},
        description="Supervising officer places a hard administrative block on matter progression.",
        required_payload_keys=["block_reason"],
        is_exception_transition=True,
    ),

    # Flag external sync failure
    TransitionRule(
        action="FLAG_EXTERNAL_SYNC_FAILURE",
        from_states=[s for s in MatterState if s != MatterState.CLOSED and s != MatterState.EXTERNAL_SYNC_FAILED],
        to_state=MatterState.EXTERNAL_SYNC_FAILED,
        allowed_roles={Role.INTEGRATION_SERVICE, Role.SUPERVISING_LEGAL_OFFICER},
        description="External eCourts or ICJS synchronization encountered an unresolvable error.",
        required_payload_keys=["error_details"],
        is_exception_transition=True,
    ),

    # Resolve Exception (Supervising Legal Officer only!)
    TransitionRule(
        action="RESOLVE_EXCEPTION",
        from_states=[
            MatterState.MANUAL_REVIEW_REQUIRED,
            MatterState.TRANSITION_BLOCKED,
            MatterState.DATA_CONFLICT,
            MatterState.EXTERNAL_SYNC_FAILED,
        ],
        to_state=MatterState.HUMAN_REVIEW,  # Default resolution returns to human review
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER},
        description="Supervising Legal Officer resolves exception condition and restores matter to active workflow.",
        required_payload_keys=["resolution_notes"],
        is_exception_transition=True,
    ),
]


class WorkflowStateMachine:
    """Authoritative state machine validator and engine for Nyaya Mitra."""

    @classmethod
    def find_rule(cls, current_state: MatterState, action: str) -> Optional[TransitionRule]:
        for rule in TRANSITION_RULES:
            if rule.action == action and current_state in rule.from_states:
                return rule
        return None

    @classmethod
    def get_available_transitions(
        cls,
        current_state: MatterState,
        actor_role: Optional[Role] = None,
    ) -> List[Dict[str, Any]]:
        available = []
        for rule in TRANSITION_RULES:
            if current_state in rule.from_states:
                is_role_allowed = True
                if actor_role is not None:
                    is_role_allowed = actor_role in rule.allowed_roles
                available.append({
                    "action": rule.action,
                    "target_state": rule.to_state.value,
                    "description": rule.description,
                    "allowed_roles": [r.value for r in rule.allowed_roles],
                    "user_has_permission": is_role_allowed,
                    "requires_artifact_approval": rule.requires_artifact_approval,
                    "ai_permitted": rule.ai_permitted,
                    "required_payload_keys": rule.required_payload_keys,
                    "is_exception": rule.is_exception_transition,
                })
        return available

    @classmethod
    def validate_transition(
        cls,
        current_state: MatterState,
        action: str,
        actor_role: Role,
        payload: Optional[Dict[str, Any]] = None,
        is_ai_agent: bool = False,
    ) -> TransitionRule:
        rule = cls.find_rule(current_state, action)
        if not rule:
            raise ValueError(
                f"Illegal transition: Action '{action}' is not valid from state '{current_state.value}'."
            )

        # AI Boundary Check
        if is_ai_agent and not rule.ai_permitted:
            raise PermissionError(
                f"AI Safety Violation: Automated agents cannot perform '{action}'. "
                f"Must be performed by an authorized human officer."
            )

        # Role Authorization Check
        if actor_role not in rule.allowed_roles:
            raise PermissionError(
                f"Permission Denied: Role '{actor_role.value}' is not authorized for action '{action}'. "
                f"Permitted roles: {[r.value for r in rule.allowed_roles]}."
            )

        # Mandatory Payload Keys Check
        if payload is None:
            payload = {}
        missing_keys = []
        for key in rule.required_payload_keys:
            # Special case for filing reference: accept 'filing_reference', 'cnr_number', or 'e_filing_acknowledgement'
            if key == "filing_reference":
                if not (payload.get("filing_reference") or payload.get("cnr_number") or payload.get("e_filing_acknowledgement")):
                    missing_keys.append("filing_reference (or cnr_number / e_filing_acknowledgement)")
            # Special case for assigned advocate: accept 'assigned_advocate_id' or 'assigned_advocate_name'
            elif key == "assigned_advocate_id":
                if not (payload.get("assigned_advocate_id") or payload.get("assigned_advocate_name") or payload.get("advocate_id")):
                    missing_keys.append("assigned_advocate_id (or assigned_advocate_name)")
            elif key == "reason":
                val = payload.get("reason") or payload.get("comment") or payload.get("notes") or payload.get("justification")
                if not val:
                    missing_keys.append("reason")
                else:
                    payload["reason"] = val
            elif key == "conflict_details":
                val = payload.get("conflict_details") or payload.get("details") or payload.get("conflict") or payload.get("comment")
                if not val:
                    missing_keys.append("conflict_details")
                else:
                    payload["conflict_details"] = val
            elif key == "block_reason":
                val = payload.get("block_reason") or payload.get("reason") or payload.get("comment") or payload.get("justification")
                if not val:
                    missing_keys.append("block_reason")
                else:
                    payload["block_reason"] = val
            elif key == "resolution_notes":
                val = payload.get("resolution_notes") or payload.get("notes") or payload.get("comment") or payload.get("resolution")
                if not val:
                    missing_keys.append("resolution_notes")
                else:
                    payload["resolution_notes"] = val
            elif key == "closure_reason":
                val = payload.get("closure_reason") or payload.get("reason") or payload.get("comment")
                if not val:
                    missing_keys.append("closure_reason")
                else:
                    payload["closure_reason"] = val
            elif key not in payload or payload[key] is None or payload[key] == "":
                missing_keys.append(key)

        if missing_keys:
            raise ValueError(
                f"Missing required transition prerequisites: {missing_keys} must be provided for action '{action}'."
            )

        return rule
