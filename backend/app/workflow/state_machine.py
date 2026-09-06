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


# ── Action Alias Mapping (Normalizes legacy / deprecated action names) ──────────

ACTION_ALIASES: Dict[str, str] = {
    "SUBMIT_FOR_REVIEW": "SUBMIT_FOR_LEGAL_AID_REVIEW",
    "SUBMIT_FOR_LEGAL_AID": "SUBMIT_FOR_LEGAL_AID_REVIEW",
    "COMPLETE_ANALYSIS": "RUN_ANALYSIS",
    "EVALUATE_SECTION_479": "RUN_ANALYSIS",
    "APPROVE_MATTER": "SUPERVISORY_APPROVE",
    "APPROVE_DRAFT": "SUPERVISORY_APPROVE",
    "APPROVE": "SUPERVISORY_APPROVE",
    "LODGE_COURT_FILING": "RECORD_FILING",
    "FILE_IN_COURT": "RECORD_FILING",
    "FILE": "RECORD_FILING",
    "SUBMIT_FOR_HUMAN_REVIEW": "START_LEGAL_DRAFTING",
    "SUBMIT_FOR_SUPERVISORY_REVIEW": "COUNSEL_SIGN_OFF",
    "SIGN_OFF_DRAFT": "COUNSEL_SIGN_OFF",
    "SIGN_OFF": "COUNSEL_SIGN_OFF",
    "FLAG_MISSING_DOCS": "REQUEST_DOCUMENTS",
    "INITIATE_RELEASE": "COORDINATE_RELEASE",
    "CONFIRM_RELEASE": "CONFIRM_PRISON_RELEASE",
    "START_POST_RELEASE_FOLLOW_UP": "CONFIRM_PRISON_RELEASE",
}


# ── Canonical Transition Engine Definitions ───────────────────────────────────

TRANSITION_RULES: List[TransitionRule] = [
    # 1. INTAKE -> VERIFICATION
    TransitionRule(
        action="START_VERIFICATION",
        from_states=[MatterState.INTAKE],
        to_state=MatterState.VERIFICATION,
        allowed_roles={Role.DLSA_OFFICER, Role.JAIL_OFFICER},
        description="Custodian or DLSA intake desk starts legal-aid custody verification.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 2. VERIFICATION -> REVIEW
    TransitionRule(
        action="SUBMIT_FOR_LEGAL_AID_REVIEW",
        from_states=[MatterState.VERIFICATION],
        to_state=MatterState.REVIEW,
        allowed_roles={Role.JAIL_OFFICER, Role.DLSA_OFFICER},
        description="Custody verification complete; submitted to DLSA for legal-aid intake review.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 3. REVIEW -> LEGAL_AID_REQUIRED
    TransitionRule(
        action="FLAG_LEGAL_AID_REQUIRED",
        from_states=[MatterState.REVIEW],
        to_state=MatterState.LEGAL_AID_REQUIRED,
        allowed_roles={Role.DLSA_OFFICER, Role.SUPERVISING_LEGAL_OFFICER},
        description="Institutional legal review confirms undertrial requires legal-aid defense counsel.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 4. LEGAL_AID_REQUIRED -> ASSIGNED
    TransitionRule(
        action="ASSIGN_COUNSEL",
        from_states=[MatterState.LEGAL_AID_REQUIRED],
        to_state=MatterState.ASSIGNED,
        allowed_roles={Role.DLSA_OFFICER},  # Strict: DLSA appoints panel counsel; Supervisor / Admins cannot assign
        description="DLSA formally assigns an empanelled defense advocate to the matter under NALSA/SLSA mandate.",
        required_payload_keys=["assigned_advocate_id"],
        ai_permitted=False,
    ),

    # 5. ASSIGNED -> DOCUMENT_PENDING
    TransitionRule(
        action="REQUEST_DOCUMENTS",
        from_states=[MatterState.ASSIGNED],
        to_state=MatterState.DOCUMENT_PENDING,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.DLSA_OFFICER},
        description="Assigned advocate or DLSA flags missing records required for statutory defense.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 6. DOCUMENT_PENDING / ASSIGNED -> ANALYSIS_READY
    # Strict Stage 8 Boundary: Section 479 BNSS rules / AI analysis moves state to ANALYSIS_READY only!
    TransitionRule(
        action="RUN_ANALYSIS",
        from_states=[MatterState.DOCUMENT_PENDING, MatterState.ASSIGNED],
        to_state=MatterState.ANALYSIS_READY,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.DLSA_OFFICER, Role.INTEGRATION_SERVICE},
        description="Deterministic statutory rules engine evaluation completed under Section 479 BNSS.",
        required_payload_keys=[],
        ai_permitted=True,  # Automated rules engine / AI background job allowed
    ),
    TransitionRule(
        action="DOCUMENTS_COMPLETED",
        from_states=[MatterState.DOCUMENT_PENDING],
        to_state=MatterState.ANALYSIS_READY,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.DLSA_OFFICER, Role.INTEGRATION_SERVICE},
        description="Missing documents resolved; proceed to statutory analysis.",
        required_payload_keys=[],
        ai_permitted=True,
    ),

    # 7. ANALYSIS_READY -> HUMAN_REVIEW
    TransitionRule(
        action="START_LEGAL_DRAFTING",
        from_states=[MatterState.ANALYSIS_READY],
        to_state=MatterState.HUMAN_REVIEW,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.CONTROLLED_EXTERNAL_ADVOCATE},  # Assigned defense counsel takes up drafting
        description="Assigned defense counsel takes up statutory analysis to prepare and review formal bail petition.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 8. HUMAN_REVIEW -> SUBMITTED (Assigned Defense Advocate counsel sign-off)
    TransitionRule(
        action="COUNSEL_SIGN_OFF",
        from_states=[MatterState.HUMAN_REVIEW],  # Strict: Must go through HUMAN_REVIEW drafting; cannot skip from ANALYSIS_READY!
        to_state=MatterState.SUBMITTED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.CONTROLLED_EXTERNAL_ADVOCATE},
        description="Assigned Defense Advocate completes petition drafting, signs off work product (Level 1), and submits for supervisory review.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 9. SUBMITTED -> APPROVED (Supervising Legal Officer review of exact artifact version)
    TransitionRule(
        action="SUPERVISORY_APPROVE",
        from_states=[MatterState.SUBMITTED],  # Strict: Supervisor CANNOT approve from HUMAN_REVIEW without prior counsel sign-off!
        to_state=MatterState.APPROVED,
        allowed_roles={Role.SUPERVISING_LEGAL_OFFICER},
        description="Supervising Legal Officer verifies exact artifact version signed by counsel and issues institutional approval (Level 2).",
        required_payload_keys=[],
        requires_artifact_approval=True,
        ai_permitted=False,  # AI CAN NEVER APPROVE!
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

    # 10. APPROVED -> FILED (Lodged through authorized court registry / eCourts process)
    # Strict: Filing is permitted ONLY from APPROVED (never directly from SUBMITTED or INTAKE!)
    TransitionRule(
        action="RECORD_FILING",
        from_states=[MatterState.APPROVED],
        to_state=MatterState.FILED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.INTEGRATION_SERVICE},  # Assigned counsel or official eCourts sync
        description="Assigned defense advocate lodges approved petition in court with authentic filing/CNR reference.",
        required_payload_keys=["filing_reference"],
        requires_artifact_approval=True,  # Cannot file without prior supervisor approval!
        ai_permitted=False,  # AI CAN NEVER FILE!
    ),

    # 11. FILED -> HEARING_SCHEDULED
    TransitionRule(
        action="SCHEDULE_HEARING",
        from_states=[MatterState.FILED],
        to_state=MatterState.HEARING_SCHEDULED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.DLSA_OFFICER, Role.INTEGRATION_SERVICE},
        description="Court registry lists approved matter for judicial hearing with verified bench and provenance.",
        required_payload_keys=["hearing_date", "bench_name", "source_type"],
        ai_permitted=False,
    ),

    # 12. HEARING_SCHEDULED -> ORDER_RECEIVED
    # Nyaya Mitra records court order; does not pronounce or simulate judicial discretion!
    TransitionRule(
        action="RECORD_COURT_ORDER",
        from_states=[MatterState.HEARING_SCHEDULED],
        to_state=MatterState.ORDER_RECEIVED,
        allowed_roles={Role.DEFENSE_ADVOCATE, Role.SUPERVISING_LEGAL_OFFICER, Role.DLSA_OFFICER, Role.INTEGRATION_SERVICE},
        description="Record judicial order pronounced by the competent court with certified order reference.",
        required_payload_keys=["order_type", "order_date", "judge_name", "order_reference"],
        ai_permitted=False,
    ),

    # 13. ORDER_RECEIVED -> RELEASE_WORKFLOW (Legal coordination of release)
    TransitionRule(
        action="COORDINATE_RELEASE",
        from_states=[MatterState.ORDER_RECEIVED],
        to_state=MatterState.RELEASE_WORKFLOW,
        allowed_roles={Role.DLSA_OFFICER, Role.DEFENSE_ADVOCATE},
        description="Court has granted bail; DLSA and assigned advocate coordinate surety verification and bail bond compliance.",
        required_payload_keys=[],
        ai_permitted=False,
    ),

    # 14. RELEASE_WORKFLOW -> POST_RELEASE_FOLLOW_UP (Physical custody discharge by Prison)
    TransitionRule(
        action="CONFIRM_PRISON_RELEASE",
        from_states=[MatterState.RELEASE_WORKFLOW],
        to_state=MatterState.POST_RELEASE_FOLLOW_UP,
        allowed_roles={Role.JAIL_OFFICER},  # Strict: Only Jail Superintendent discharges inmate from custody!
        description="Prison Superintendent confirms physical discharge and custody release of inmate.",
        required_payload_keys=["release_date"],
        ai_permitted=False,
    ),

    # 15. POST_RELEASE_FOLLOW_UP -> CLOSED
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
    def normalize_action(cls, action: str) -> str:
        cleaned = (action or "").strip().upper()
        return ACTION_ALIASES.get(cleaned, cleaned)

    @classmethod
    def find_rule(cls, current_state: MatterState, action: str) -> Optional[TransitionRule]:
        norm_action = cls.normalize_action(action)
        for rule in TRANSITION_RULES:
            if rule.action == norm_action and current_state in rule.from_states:
                return rule
        return None

    @classmethod
    def get_available_transitions(
        cls,
        current_state: MatterState,
        actor_role: Optional[Role] = None,
        case_data: Optional[Dict[str, Any]] = None,
        actor: Optional[Any] = None,
        active_artifact: Optional[Dict[str, Any]] = None,
        has_supervisory_approval: bool = False,
    ) -> List[Dict[str, Any]]:
        available = []
        for rule in TRANSITION_RULES:
            if current_state in rule.from_states:
                is_role_allowed = True
                missing_prerequisites: List[str] = []
                is_blocked = False

                if actor_role is not None:
                    if actor_role not in rule.allowed_roles:
                        is_role_allowed = False
                        missing_prerequisites.append(f"Role '{actor_role.value}' is not permitted")

                # Case assignment check for defense advocates
                if actor_role in (Role.DEFENSE_ADVOCATE, Role.CONTROLLED_EXTERNAL_ADVOCATE) and case_data and actor:
                    user_full = (getattr(actor, "full_name", "") or "").lower()
                    actor_id = getattr(actor, "id", "")
                    linked_case = getattr(actor, "linked_case_id", None)
                    cid = case_data.get("case_id")
                    
                    is_assigned = (
                        (case_data.get("assigned_advocate_id") and case_data.get("assigned_advocate_id") == actor_id)
                        or (case_data.get("assigned_lawyer_id") and case_data.get("assigned_lawyer_id") == actor_id)
                        or (case_data.get("assigned_lawyer") and user_full and user_full in case_data.get("assigned_lawyer", "").lower())
                        or (linked_case and linked_case == cid)
                    )
                    # Non-assigned advocates cannot execute case transitions
                    if not is_assigned and rule.action != "ASSIGN_COUNSEL":
                        is_role_allowed = False
                        missing_prerequisites.append("Case is not assigned to you by DLSA")

                # Specific check: SUPERVISORY_APPROVE requires active artifact version
                if rule.action == "SUPERVISORY_APPROVE" and not active_artifact:
                    is_blocked = True
                    missing_prerequisites.append("Active draft artifact version required before supervisory approval")

                # Specific check: RECORD_FILING requires active supervisory approval
                if rule.action == "RECORD_FILING" and not has_supervisory_approval:
                    is_blocked = True
                    missing_prerequisites.append("Supervisory legal officer approval required before court filing")

                user_permitted = is_role_allowed and not is_blocked

                available.append({
                    "action": rule.action,
                    "current_state": current_state.value,
                    "target_state": rule.to_state.value,
                    "label": rule.action.replace("_", " "),
                    "description": rule.description,
                    "allowed_roles": [r.value for r in rule.allowed_roles],
                    "user_has_permission": user_permitted,
                    "missing_prerequisites": missing_prerequisites,
                    "requires_artifact_approval": rule.requires_artifact_approval,
                    "ai_permitted": rule.ai_permitted,
                    "required_payload_keys": rule.required_payload_keys,
                    "is_exception": rule.is_exception_transition,
                    "is_blocked": is_blocked,
                    "block_reason": "; ".join(missing_prerequisites) if is_blocked else "",
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
        norm_action = cls.normalize_action(action)
        rule = cls.find_rule(current_state, norm_action)
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
