"""
app.workflow.service - Workflow Engine & Authoritative State Transition Service.
================================================================================
Encapsulates all matter/case lifecycle transitions, immutable artifact versioning,
multi-level approval enforcement, case handoffs, and audit timeline generation.

All state transitions, approvals, artifacts, and handoffs are persisted in the
production SQLite database (zero in-memory ephemeral storage).
"""

from __future__ import annotations
import hashlib
import json
import uuid
import datetime
import logging
from typing import Dict, Any, Optional, List, Tuple

from app.models.schemas import MatterState, CaseState, TimelineEvent
from app.models.domain import AuditAction
from app.auth.roles import Role
from app.auth.user_store import AuthUser
from app.workflow.state_machine import WorkflowStateMachine, TransitionRule
from app.database import (
    get_db_connection,
    get_case_version,
    execute_case_transition_tx,
    store_matter_approval,
    get_matter_approvals,
    store_matter_artifact_version,
    get_matter_artifact_versions,
    get_active_matter_artifact,
    store_matter_handoff,
    get_matter_handoffs,
    get_matter_approval_policy,
    case_repo,
    audit_repo,
)

logger = logging.getLogger(__name__)


class ConcurrencyConflictError(Exception):
    """Raised when an optimistic concurrency check fails (HTTP 409)."""
    pass


class WorkflowService:
    """Production service facade for matter lifecycle, approvals, and handoffs."""

    @classmethod
    def get_case_state(cls, case_id: str) -> Tuple[MatterState, int, Dict[str, Any]]:
        """Retrieve current canonical state, version number, and case record."""
        case = case_repo.get_case_by_id(case_id)
        if not case:
            raise LookupError(f"Case with ID '{case_id}' not found.")
        
        # Determine canonical state
        raw_status = getattr(case, "status", None) or getattr(case, "current_status", "INTAKE")
        canonical_state = CaseState.to_canonical(raw_status)
        version_number = get_case_version(case_id)
        
        case_dict = case if isinstance(case, dict) else (case.__dict__ if hasattr(case, "__dict__") else {})
        return canonical_state, version_number, case_dict

    @classmethod
    def execute_transition(
        cls,
        case_id: str,
        action: str,
        actor: AuthUser,
        payload: Optional[Dict[str, Any]] = None,
        comment: Optional[str] = None,
        expected_version: Optional[int] = None,
        is_ai_agent: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a server-enforced, transactional state transition.
        Validates state machine rules, actor role permissions, mandatory evidence,
        artifact version approvals, and optimistic concurrency.
        """
        if payload is None:
            payload = {}

        current_state, current_version, case_data = cls.get_case_state(case_id)

        # 1. Optimistic Concurrency Check
        if expected_version is not None and expected_version != current_version:
            raise ConcurrencyConflictError(
                f"Conflict: Matter '{case_id}' version mismatch. Expected {expected_version}, but database version is {current_version}."
            )

        # 2. State Machine & Role Validation
        rule = WorkflowStateMachine.validate_transition(
            current_state=current_state,
            action=action,
            actor_role=actor.role,
            payload=payload,
            is_ai_agent=is_ai_agent,
        )

        target_state = rule.to_state

        # 3. Artifact & Approval Prerequisites
        artifact_version_id = payload.get("artifact_version_id")
        artifact_id = payload.get("artifact_id", "art_bail_draft")

        # Specific check: SUBMITTED (Counsel Sign-off by DEFENSE_ADVOCATE)
        if action in ("COUNSEL_SIGN_OFF", "SUBMIT_FOR_SUPERVISORY_REVIEW"):
            # Counsel signing off work product registers Level 1 approval on artifact version
            if artifact_version_id:
                store_matter_approval({
                    "approval_id": f"app_{uuid.uuid4().hex[:12]}",
                    "matter_id": case_id,
                    "actor_id": actor.id,
                    "actor_role": actor.role.value,
                    "organization_id": actor.org_id,
                    "created_at": datetime.datetime.utcnow().isoformat(),
                    "decided_at": datetime.datetime.utcnow().isoformat(),
                    "artifact_id": artifact_id,
                    "artifact_version_id": artifact_version_id,
                    "artifact_type": payload.get("artifact_type", "BAIL_APPLICATION"),
                    "decision": "APPROVED",
                    "comment": comment or "Counsel signed off work product and submitted for supervisory review.",
                    "approval_level": 1,
                    "required_level": 1,
                    "is_valid": 1,
                    "metadata": {"action": action, "sign_off_actor": actor.full_name},
                })

        # Specific check: APPROVE_MATTER / SUPERVISORY_APPROVE (by SUPERVISING_LEGAL_OFFICER)
        if action in ("APPROVE_MATTER", "SUPERVISORY_APPROVE"):
            if not artifact_version_id:
                # Look up active artifact version if not explicitly passed
                active_art = get_active_matter_artifact(case_id, payload.get("artifact_type", "BAIL_APPLICATION"))
                if active_art:
                    artifact_version_id = active_art["version_id"]
                    artifact_id = active_art["artifact_id"]
                else:
                    raise ValueError(
                        f"Approval Failed: No active legal artifact exists to approve for matter '{case_id}'."
                    )
            
            # Store Supervisory Approval (Level 2)
            store_matter_approval({
                "approval_id": f"app_{uuid.uuid4().hex[:12]}",
                "matter_id": case_id,
                "actor_id": actor.id,
                "actor_role": actor.role.value,
                "organization_id": actor.org_id,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "decided_at": datetime.datetime.utcnow().isoformat(),
                "artifact_id": artifact_id,
                "artifact_version_id": artifact_version_id,
                "artifact_type": payload.get("artifact_type", "BAIL_APPLICATION"),
                "decision": "APPROVED",
                "comment": comment or "Supervisory institutional approval granted.",
                "approval_level": 2,
                "required_level": 2,
                "is_valid": 1,
                "metadata": {"action": action, "approved_by": actor.full_name},
            })

        # Specific check: RECORD_FILING / LODGE_COURT_FILING
        if action in ("RECORD_FILING", "LODGE_COURT_FILING"):
            # Must verify that valid supervisory approval exists on the current active artifact version!
            approvals = get_matter_approvals(case_id, artifact_version_id)
            supervisory_approved = any(
                a.get("decision") == "APPROVED" and a.get("approval_level", 1) >= 2 and a.get("is_valid", 1) == 1
                for a in approvals
            )
            # If no version passed or checked, verify active artifact version has supervisory approval
            if not supervisory_approved:
                active_art = get_active_matter_artifact(case_id, "BAIL_APPLICATION")
                if active_art:
                    active_approvals = get_matter_approvals(case_id, active_art["version_id"])
                    supervisory_approved = any(
                        a.get("decision") == "APPROVED" and a.get("approval_level", 1) >= 2 and a.get("is_valid", 1) == 1
                        for a in active_approvals
                    )
            
            if not supervisory_approved:
                raise ValueError(
                    f"Filing Blocked: Matter '{case_id}' cannot be filed in court without an active, valid "
                    f"Supervisory Legal Officer approval on the exact filing artifact version."
                )

        # 4. Prepare updated case data
        updated_data: Dict[str, Any] = {}
        if action == "ASSIGN_COUNSEL":
            adv_id = payload.get("assigned_advocate_id") or payload.get("advocate_id")
            adv_name = payload.get("assigned_advocate_name") or payload.get("advocate_name", "Assigned Legal Aid Counsel")
            updated_data["assigned_advocate_id"] = adv_id
            updated_data["assigned_advocate_name"] = adv_name
        elif action in ("RECORD_FILING", "LODGE_COURT_FILING"):
            updated_data["filing_reference"] = payload.get("filing_reference") or payload.get("cnr_number")
            updated_data["filing_date"] = payload.get("filing_date", datetime.date.today().isoformat())
        elif action == "SCHEDULE_HEARING":
            updated_data["hearing_date"] = payload.get("hearing_date")
            updated_data["court_name"] = payload.get("court_name", case_data.get("court_name"))
        elif action == "RECORD_COURT_ORDER":
            updated_data["order_type"] = payload.get("order_type")
            updated_data["order_date"] = payload.get("order_date", datetime.date.today().isoformat())
            updated_data["order_summary"] = payload.get("order_summary")
        elif action in ("CONFIRM_RELEASE", "START_POST_RELEASE_FOLLOW_UP"):
            updated_data["release_date"] = payload.get("release_date", datetime.date.today().isoformat())

        # 5. Execute DB Transaction with Optimistic Locking
        success, new_version, err_msg = execute_case_transition_tx(
            case_id=case_id,
            new_status=target_state.value,
            expected_version=current_version,
            updated_data=updated_data,
        )

        if not success:
            raise ConcurrencyConflictError(
                f"Concurrent Modification Detected: Failed to commit transition '{action}' for matter '{case_id}'. {err_msg}"
            )

        # 6. Immutable Audit Trail Logging
        provenance = "AI" if is_ai_agent else ("SYSTEM" if actor.role == Role.INTEGRATION_SERVICE else "USER")
        audit_repo.record(
            actor_id=actor.id,
            actor_role=actor.role.value,
            action=AuditAction.STATUS_TRANSITION,
            entity_type="CASE",
            entity_id=case_id,
            details={
                "action": action,
                "previous_state": current_state.value,
                "new_state": target_state.value,
                "version_number": new_version,
                "comment": comment,
                "payload": payload,
                "provenance": provenance,
            },
            organization_id=actor.org_id,
        )

        # 7. Add Chronological Timeline Event
        cls._add_timeline_event(
            case_id=case_id,
            title=f"Workflow State: {target_state.value}",
            description=f"Action '{action}' executed by {actor.full_name} ({actor.role.value}). {comment or ''}".strip(),
            actor=actor.full_name,
            actor_role=actor.role.value,
            source="AI" if is_ai_agent else ("Integration Sync" if actor.role == Role.INTEGRATION_SERVICE else "User Action"),
            previous_state=current_state.value,
            new_state=target_state.value,
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            provenance_badge=provenance,
        )

        return {
            "case_id": case_id,
            "previous_state": current_state.value,
            "current_state": target_state.value,
            "action": action,
            "version_number": new_version,
            "transitioned_by": actor.full_name,
            "transitioned_role": actor.role.value,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "message": f"Successfully transitioned matter '{case_id}' to '{target_state.value}'.",
        }

    @classmethod
    def create_artifact_version(
        cls,
        case_id: str,
        artifact_id: str,
        artifact_type: str,
        content_text: str,
        actor: AuthUser,
        is_ai_generated: bool = False,
        ai_model_name: Optional[str] = None,
        version_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an immutable version N+1 for a matter artifact.
        Generates cryptographic SHA-256 content hash.
        Creating version N+1 leaves previous version approvals bound only to version N.
        """
        # Determine current version count for this artifact
        existing_versions = get_matter_artifact_versions(case_id, artifact_id)
        next_ver_num = len(existing_versions) + 1
        tag = version_tag or f"{artifact_id}_v{next_ver_num}"
        
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
        version_id = f"ver_{uuid.uuid4().hex[:12]}"
        provenance = "AI_ASSISTED" if is_ai_generated else "HUMAN_AUTHORED"

        record = {
            "version_id": version_id,
            "artifact_id": artifact_id,
            "matter_id": case_id,
            "artifact_type": artifact_type,
            "version_number": next_ver_num,
            "version_tag": tag,
            "content_hash": content_hash,
            "content_text": content_text,
            "is_ai_generated": 1 if is_ai_generated else 0,
            "ai_model_name": ai_model_name,
            "provenance_tag": provenance,
            "created_by": actor.id,
            "created_by_role": actor.role.value,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "is_active": 1,
        }

        success = store_matter_artifact_version(record)
        if not success:
            raise RuntimeError(f"Database error: Failed to store artifact version for matter '{case_id}'.")

        # Emit audit event
        audit_repo.record(
            actor_id=actor.id,
            actor_role=actor.role.value,
            action=AuditAction.DOCUMENT_UPLOAD,
            entity_type="ARTIFACT_VERSION",
            entity_id=version_id,
            details={
                "case_id": case_id,
                "artifact_id": artifact_id,
                "version_number": next_ver_num,
                "version_tag": tag,
                "content_hash": content_hash,
                "is_ai": is_ai_generated,
                "provenance": provenance,
            },
            organization_id=actor.org_id,
        )

        return record

    @classmethod
    def record_approval(
        cls,
        case_id: str,
        artifact_id: str,
        artifact_version_id: str,
        artifact_type: str,
        decision: str,
        comment: Optional[str],
        actor: AuthUser,
        approval_level: int = 1,
    ) -> Dict[str, Any]:
        """Record formal first-class approval on an exact artifact version."""
        if actor.role == Role.PLATFORM_ADMIN:
            raise PermissionError("Platform Admins cannot grant legal approvals.")
        if actor.role == Role.READ_ONLY_AUDITOR:
            raise PermissionError("Auditors cannot grant legal approvals.")

        approval_id = f"app_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow().isoformat()

        record = {
            "approval_id": approval_id,
            "matter_id": case_id,
            "actor_id": actor.id,
            "actor_role": actor.role.value,
            "organization_id": actor.org_id,
            "created_at": now,
            "decided_at": now,
            "artifact_id": artifact_id,
            "artifact_version_id": artifact_version_id,
            "artifact_type": artifact_type,
            "decision": decision,
            "comment": comment,
            "approval_level": approval_level,
            "required_level": approval_level,
            "is_valid": 1,
            "metadata": {"approved_by": actor.full_name},
        }

        success = store_matter_approval(record)
        if not success:
            raise RuntimeError(f"Database error: Failed to store approval for matter '{case_id}'.")

        # Emit audit event
        audit_repo.record(
            actor_id=actor.id,
            actor_role=actor.role.value,
            action=AuditAction.UPDATE,
            entity_type="APPROVAL",
            entity_id=approval_id,
            details={
                "case_id": case_id,
                "artifact_version_id": artifact_version_id,
                "decision": decision,
                "approval_level": approval_level,
                "comment": comment,
            },
            organization_id=actor.org_id,
        )

        # Add timeline event
        cls._add_timeline_event(
            case_id=case_id,
            title=f"Artifact {decision}: {artifact_type} (Level {approval_level})",
            description=f"Decision '{decision}' recorded by {actor.full_name} ({actor.role.value}). {comment or ''}".strip(),
            actor=actor.full_name,
            actor_role=actor.role.value,
            source="User Action",
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            decision=decision,
            comment=comment,
            provenance_badge="USER",
        )

        return record

    @classmethod
    def record_handoff(
        cls,
        case_id: str,
        to_user_id: str,
        to_role: str,
        reason: str,
        actor: AuthUser,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record immutable case reassignment and handoff packet.
        Preserves complete historical continuity without overwriting past work.
        """
        if actor.role in (Role.READ_ONLY_AUDITOR, Role.ACCUSED_USER, Role.FAMILY_GUARDIAN):
            raise PermissionError(f"Role '{actor.role.value}' is not authorized to reassign matters.")

        handoff_id = f"hdf_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow().isoformat()

        record = {
            "handoff_id": handoff_id,
            "matter_id": case_id,
            "from_user_id": actor.id,
            "to_user_id": to_user_id,
            "from_role": actor.role.value,
            "to_role": to_role,
            "reason": reason,
            "created_at": now,
            "initiated_by": actor.full_name,
            "acknowledged_at": None,
            "metadata": metadata or {},
        }

        success = store_matter_handoff(record)
        if not success:
            raise RuntimeError(f"Database error: Failed to record handoff for matter '{case_id}'.")

        # Update case assigned advocate or handler
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        c_row = cursor.fetchone()
        if c_row and c_row[0]:
            try:
                cd = json.loads(c_row[0]) if isinstance(c_row[0], str) else dict(c_row[0])
                cd["assigned_lawyer_id"] = to_user_id
                cursor.execute(
                    "UPDATE cases SET assigned_lawyer_id = ?, data = ? WHERE case_id = ?",
                    (to_user_id, json.dumps(cd), case_id),
                )
                conn.commit()
            except Exception:
                pass
        conn.close()

        # Emit audit event
        audit_repo.record(
            actor_id=actor.id,
            actor_role=actor.role.value,
            action=AuditAction.COUNSEL_ASSIGNED,
            entity_type="CASE_HANDOFF",
            entity_id=handoff_id,
            details={
                "case_id": case_id,
                "from_user_id": actor.id,
                "to_user_id": to_user_id,
                "from_role": actor.role.value,
                "to_role": to_role,
                "reason": reason,
            },
            organization_id=actor.org_id,
        )

        # Timeline event
        cls._add_timeline_event(
            case_id=case_id,
            title=f"Case Reassigned & Handed Off",
            description=f"Reassigned from {actor.full_name} ({actor.role.value}) to {to_user_id} ({to_role}). Reason: {reason}",
            actor=actor.full_name,
            actor_role=actor.role.value,
            source="User Action",
            comment=reason,
            provenance_badge="USER",
        )

        return record

    @classmethod
    def get_handoff_summary(cls, case_id: str) -> Dict[str, Any]:
        """
        Compile comprehensive handoff dossier for incoming counsel:
        - Completed milestones
        - Pending requirements
        - Handoff origin reason
        - Active artifacts and latest versions
        """
        state, version, case_dict = cls.get_case_state(case_id)
        handoffs = get_matter_handoffs(case_id)
        latest_handoff = handoffs[0] if handoffs else None

        # Determine completed vs pending states based on canonical order
        canonical_order = [
            MatterState.INTAKE,
            MatterState.VERIFICATION,
            MatterState.REVIEW,
            MatterState.LEGAL_AID_REQUIRED,
            MatterState.ASSIGNED,
            MatterState.DOCUMENT_PENDING,
            MatterState.ANALYSIS_READY,
            MatterState.HUMAN_REVIEW,
            MatterState.SUBMITTED,
            MatterState.APPROVED,
            MatterState.FILED,
            MatterState.HEARING_SCHEDULED,
            MatterState.ORDER_RECEIVED,
            MatterState.RELEASE_WORKFLOW,
            MatterState.POST_RELEASE_FOLLOW_UP,
            MatterState.CLOSED,
        ]

        current_idx = canonical_order.index(state) if state in canonical_order else -1
        completed_milestones = [s.value for i, s in enumerate(canonical_order) if i <= current_idx]
        pending_requirements = [s.value for i, s in enumerate(canonical_order) if i > current_idx]

        active_draft = get_active_matter_artifact(case_id, "BAIL_APPLICATION")
        approvals = get_matter_approvals(case_id)

        return {
            "case_id": case_id,
            "current_state": state.value,
            "version_number": version,
            "originating_reason": latest_handoff.get("reason") if latest_handoff else "Initial Assignment",
            "latest_handoff": latest_handoff,
            "handoff_count": len(handoffs),
            "completed_milestones": completed_milestones,
            "pending_requirements": pending_requirements,
            "active_artifact": active_draft,
            "approval_count": len(approvals),
            "latest_approval": approvals[0] if approvals else None,
        }

    @classmethod
    def get_matter_timeline(cls, case_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve unified chronological timeline with authoritative provenance badges:
        👤 USER, ⚙️ SYSTEM, 🤖 AI, 🔄 EXTERNAL_SYNC
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Load from audit_events
        cursor.execute(
            "SELECT * FROM audit_events WHERE entity_id = ? OR details_json LIKE ? ORDER BY timestamp DESC",
            (case_id, f"%{case_id}%"),
        )
        audit_rows = cursor.fetchall()
        audit_cols = [d[0] for d in cursor.description]
        
        # Load case timeline json
        cursor.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        case_row = cursor.fetchone()
        conn.close()

        timeline_events: List[Dict[str, Any]] = []

        # Parse case internal timeline
        if case_row and case_row[0]:
            try:
                case_obj = json.loads(case_row[0]) if isinstance(case_row[0], str) else dict(case_row[0])
                raw_list = case_obj.get("timeline", [])
                for item in raw_list:
                    badge = item.get("provenance_badge")
                    if not badge:
                        src = (item.get("source") or "").upper()
                        if "AI" in src:
                            badge = "AI"
                        elif "SYNC" in src or "EXTERNAL" in src:
                            badge = "EXTERNAL_SYNC"
                        elif "SYSTEM" in src or "AUTOMATED" in src:
                            badge = "SYSTEM"
                        else:
                            badge = "USER"
                    item["provenance_badge"] = badge
                    timeline_events.append(item)
            except Exception:
                pass

        # Synthesize from audit_rows if case timeline is sparse
        for r in audit_rows:
            ad = dict(zip(audit_cols, r))
            details = {}
            if ad.get("details_json"):
                try:
                    details = json.loads(ad["details_json"]) if isinstance(ad["details"], str) else ad["details"]
                except Exception:
                    pass
            
            event_id = f"aud_{ad.get('id')}"
            if not any(e.get("id") == event_id for e in timeline_events):
                prov = details.get("provenance", "USER")
                timeline_events.append({
                    "id": event_id,
                    "timestamp": ad.get("timestamp"),
                    "event_type": getattr(ad.get("action"), "value", str(ad.get("action", ""))),
                    "title": str(ad.get("action", "")).replace("_", " ").title(),
                    "description": details.get("comment") or f"Action {details.get('action', '')} executed by {ad.get('actor_id')}.",
                    "actor": ad.get("actor_id"),
                    "actor_role": ad.get("actor_role"),
                    "source": "Audit Ledger",
                    "provenance_badge": prov,
                    "previous_state": details.get("previous_state"),
                    "new_state": details.get("new_state"),
                })

        # Sort descending by timestamp
        timeline_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return timeline_events

    @classmethod
    def record_external_sync(
        cls,
        case_id: str,
        source_system: str,
        external_reference: str,
        received_data: Dict[str, Any],
        actor: AuthUser,
    ) -> Dict[str, Any]:
        """Record external court/ICJS sync data with EXTERNAL_SYNC provenance."""
        cls._add_timeline_event(
            case_id=case_id,
            title=f"External Sync: {source_system}",
            description=f"Received updates from {source_system} (Ref: {external_reference}).",
            actor=source_system,
            actor_role="EXTERNAL_AUTHORITY",
            source="External Integration",
            comment=json.dumps(received_data),
            provenance_badge="EXTERNAL_SYNC",
        )

        audit_repo.record(
            actor_id=actor.id,
            actor_role=actor.role.value,
            action=AuditAction.INTEGRATION_ACTION,
            entity_type="CASE",
            entity_id=case_id,
            details={
                "source_system": source_system,
                "external_reference": external_reference,
                "received_data": received_data,
                "provenance": "EXTERNAL_SYNC",
            },
            organization_id=actor.org_id,
        )

        return {
            "case_id": case_id,
            "source_system": source_system,
            "external_reference": external_reference,
            "sync_status": "PROCESSED",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    @classmethod
    def consume_stage8_rule_result(
        cls,
        case_id: str,
        rule_result: Any,
        actor: AuthUser,
    ) -> Dict[str, Any]:
        """
        STRICT STAGE 8 BOUNDARY ENFORCEMENT:
        Consumes Section 479 / Stage 8 deterministic rules engine output.
        - Updates machine eligibility signals.
        - Moves state strictly to ANALYSIS_READY.
        - NEVER directly transitions to APPROVED, SUBMITTED, or FILED.
        - Preserves rule version, execution ID, explanation, and human-review flags.
        """
        machine_status = getattr(rule_result, "machine_status", None) or "REQUIRES_HUMAN_LEGAL_REVIEW"
        if hasattr(machine_status, "value"):
            machine_status = machine_status.value

        # Enforce boundary: rule status cannot be an approval
        current_state, current_ver, _ = cls.get_case_state(case_id)

        # Transition to ANALYSIS_READY if currently in INTAKE, VERIFICATION, or DOCUMENT_PENDING
        new_state_result = None
        if current_state in (MatterState.INTAKE, MatterState.VERIFICATION, MatterState.REVIEW, MatterState.DOCUMENT_PENDING, MatterState.ASSIGNED):
            new_state_result = cls.execute_transition(
                case_id=case_id,
                action="COMPLETE_ANALYSIS",
                actor=actor,
                payload={"stage8_machine_status": machine_status},
                comment=f"Stage 8 BNSS 479 Evaluation executed. Result: {machine_status}.",
                is_ai_agent=True,
            )

        # Record analysis artifact version tagged as AI_ASSISTED
        explanation_json = json.dumps(getattr(rule_result, "explanation", {}))
        cls.create_artifact_version(
            case_id=case_id,
            artifact_id="art_statutory_analysis",
            artifact_type="LEGAL_ANALYSIS",
            content_text=f"Section 479 Statutory Evaluation Result: {machine_status}\nDetails: {explanation_json}",
            actor=actor,
            is_ai_generated=True,
            ai_model_name="BNSS_479_DETERMINISTIC_ENGINE_V1",
            version_tag=f"sec479_analysis_{uuid.uuid4().hex[:6]}",
        )

        return {
            "case_id": case_id,
            "machine_status": machine_status,
            "transition_result": new_state_result,
            "message": "Stage 8 rule execution ingested safely. Matter moved to ANALYSIS_READY for human legal review.",
        }

    @classmethod
    def _add_timeline_event(
        cls,
        case_id: str,
        title: str,
        description: str,
        actor: str,
        actor_role: str,
        source: str,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        artifact_id: Optional[str] = None,
        artifact_version_id: Optional[str] = None,
        decision: Optional[str] = None,
        comment: Optional[str] = None,
        provenance_badge: Optional[str] = None,
    ) -> None:
        """Helper to append structured TimelineEvent to the case timeline in SQLite."""
        event = {
            "id": f"tle_{uuid.uuid4().hex[:10]}",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "event_type": "WORKFLOW_TRANSITION" if new_state else "WORKFLOW_EVENT",
            "title": title,
            "description": description,
            "actor": actor,
            "actor_role": actor_role,
            "source": source,
            "is_human_verified": provenance_badge == "USER",
            "previous_state": previous_state,
            "new_state": new_state,
            "artifact_id": artifact_id,
            "artifact_version_id": artifact_version_id,
            "decision": decision,
            "comment": comment,
            "provenance_badge": provenance_badge or "SYSTEM",
        }

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        if row and row[0]:
            try:
                case_dict = json.loads(row[0]) if isinstance(row[0], str) else dict(row[0])
                timeline = case_dict.setdefault("timeline", [])
                timeline.append(event)
                cursor.execute(
                    "UPDATE cases SET data = ? WHERE case_id = ?",
                    (json.dumps(case_dict), case_id),
                )
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to append timeline event: {e}")
        conn.close()
