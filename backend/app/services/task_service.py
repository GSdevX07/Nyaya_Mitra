"""
app/services/task_service.py — Operational Task Queue & Authority Operations Service.
=====================================================================================
Manages the universal task queue engine, safe bulk actions, custody intake, custody events,
inmate profile completeness, and physical release confirmation.
Strictly enforces server-side role and jurisdictional boundaries.
"""

from __future__ import annotations
import sqlite3
import datetime
import logging
from typing import List, Dict, Any, Optional

from app.database import (
    get_db_connection,
    get_all_cases,
    get_case,
    append_case_timeline_event,
    add_notification,
    DB_PATH,
)
from app.models.schemas import TimelineEvent, MatterState, CaseRecord
from app.auth.roles import Role
from app.auth.dependencies import AuthUser
from app.models.tasks import (
    TaskPriority,
    TaskStatus,
    TaskQueueItem,
    CustodyIntakeRequest,
    CustodyEventRequest,
    AccusedProfileUpdateRequest,
    PrisonReleaseConfirmationRequest,
)

logger = logging.getLogger(__name__)


class TaskService:
    """Authoritative service for the operational task queue and authority operations."""

    @classmethod
    def sync_operational_tasks(cls, conn: Optional[sqlite3.Connection] = None) -> int:
        """
        Synchronizes operational tasks from active cases and state machine into task_queue.
        Generates actionable, role-scoped tasks for:
        - JAIL_OFFICER: Custody intake verification, missing records, release confirmation
        - DLSA_OFFICER: Legal aid need assessment, panel advocate assignment, pending documents
        - SUPERVISING_LEGAL_OFFICER: Supervisory draft review, exception resolution
        - DEFENSE_ADVOCATE: Petition preparation/sign-off, court filing, hearing monitoring
        """
        should_close = False
        if conn is None:
            conn = get_db_connection()
            should_close = True

        synced_count = 0
        try:
            cursor = conn.cursor()
            cases = get_all_cases()
            today = datetime.date.today()
            today_iso = today.isoformat()

            for case in cases:
                cid = case.case_id
                cname = case.name or "Under-Trial Accused"
                status = getattr(case, "status", "INTAKE") or "INTAKE"
                if hasattr(status, "value"):
                    status = status.value
                elif not isinstance(status, str):
                    status = str(status)

                custody_days = int(getattr(case, "custody_days", 0) or 0)
                max_days = int(getattr(case, "max_sentence_days_for_offense", 1095) or 1095)
                facility = getattr(case, "jail_location", None) or "Not Recorded"
                district = getattr(case, "district", None) or "Not Recorded"
                assigned_id = getattr(case, "assigned_lawyer_id", None)
                assigned_name = getattr(case, "assigned_lawyer", None)
                missing_docs = getattr(case, "missing_docs", []) or []
                present_docs = getattr(case, "present_docs", []) or []
                total_doc_count = len(missing_docs) + len(present_docs)
                completeness_pct = int((len(present_docs) / total_doc_count * 100)) if total_doc_count > 0 else 100
                has_conflict = 1 if status in ("DATA_CONFLICT", "MANUAL_REVIEW_REQUIRED") else 0
                hearing_date = getattr(case, "hearing_date", None)
                assignment_status = getattr(case, "assignment_status", "AVAILABLE") or "AVAILABLE"
                legal_aid_need = 1 if (assignment_status == "AVAILABLE" or not assigned_id or status in ("INTAKE", "VERIFICATION", "REVIEW", "LEGAL_AID_REQUIRED")) else 0

                # 1a. Jail Officer: Custody intake & nominal roll verification
                if status in ("INTAKE", "VERIFICATION", "DETECTED"):
                    due_date = (today + datetime.timedelta(days=2)).isoformat()
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-JAIL-VERIF", cid, cname, "CUSTODY_VERIFICATION",
                        f"Verify Custody & Nominal Roll: {cname}",
                        f"Custody admission record and verification of nominal roll for inmate {cname} ({cid}).",
                        "JAIL_OFFICER", None, "Jail Intake Officer", "HIGH" if custody_days > 60 else "MEDIUM",
                        due_date, "PRISON_INTAKE",
                        f"Inmate admitted to {facility}. Physical admission registers, biometric logs, and nominal roll must be verified under Model Prison Rules.",
                        "PENDING_ACTION", "Jail Superintendent -> Inspector General of Prisons",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 0
                    ))
                    synced_count += 1

                # 1b. Jail Officer: Capture Missing Inmate Profile Information (for active detainees)
                if status not in ("POST_RELEASE_FOLLOW_UP", "CLOSED"):
                    due_date = (today + datetime.timedelta(days=3)).isoformat()
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-JAIL-PROFILE", cid, cname, "CAPTURE_MISSING_PROFILE",
                        f"Capture Inmate Profile Records: {cname}",
                        f"Verify guardian contacts, identification marks, and permanent domicile for {cname}.",
                        "JAIL_OFFICER", None, "Jail Welfare Officer", "MEDIUM",
                        due_date, "PRISON_INTAKE_RECORDS",
                        f"Inmate profile in {facility} requires biometric cross-verification and emergency family contact updates under Prison Rules.",
                        "PENDING_ACTION", "Jail Superintendent -> DLSA Member Secretary",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 0
                    ))
                    synced_count += 1

                # 2. DLSA Officer: Legal aid assessment & Panel counsel assignment
                if legal_aid_need and status not in ("POST_RELEASE_FOLLOW_UP", "CLOSED"):
                    due_date = (today + datetime.timedelta(days=1)).isoformat()
                    is_crit = custody_days >= (max_days // 3)
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-DLSA-ASSIGN", cid, cname, "ASSIGN_DEFENSE_COUNSEL",
                        f"Assign Defense Counsel: {cname}",
                        f"Statutory legal aid defense counsel allocation for unrepresented undertrial {cname} ({cid}).",
                        "DLSA_OFFICER", None, "DLSA Legal Aid Officer", "CRITICAL" if is_crit else "HIGH",
                        due_date, "LEGAL_AID_INTAKE_QUEUE",
                        f"Undertrial has served {custody_days} days without assigned legal counsel. Mandated panel advocate assignment under NALSA Standard Operating Procedures.",
                        "NEW" if not assigned_id else "COMPLETED", "DLSA Legal Aid Desk -> DLSA Secretary",
                        facility, district, custody_days, completeness_pct, has_conflict, 1,
                        assignment_status, status, hearing_date, 0
                    ))
                    synced_count += 1

                # 3. DLSA / Advocate: Missing Document Collection
                if len(missing_docs) > 0 and status not in ("CLOSED", "POST_RELEASE_FOLLOW_UP"):
                    due_date = (today + datetime.timedelta(days=3)).isoformat()
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-DOCS-PENDING", cid, cname, "COLLECT_MISSING_DOCUMENTS",
                        f"Obtain Required Documents: {cname}",
                        f"Missing defense records ({', '.join(missing_docs[:2])}) blocking formal bail drafting for {cname}.",
                        "DLSA_OFFICER", None, "DLSA Document Desk", "HIGH",
                        due_date, "DOCUMENT_VERIFICATION_RADAR",
                        f"Mandatory evidentiary records missing: {', '.join(missing_docs)}. Required for Section 479 statutory evaluation.",
                        "WAITING_FOR_DOCUMENTS", "Jail Welfare Officer -> DLSA Secretary",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 0
                    ))
                    synced_count += 1

                # 4. Defense Advocate: Draft bail petition & Counsel Sign-Off
                preliminary_states = (
                    "INTAKE", "INTAKE_PENDING", "DETECTED", "VERIFICATION", "CUSTODY_VERIFIED",
                    "CUSTODY_PENDING", "REVIEW", "LEGAL_AID_REQUIRED", "LEGAL_NEED_IDENTIFIED",
                    "PRE_INTAKE", "DOCUMENTS_MISSING", "DRAFT_INTAKE"
                )
                if (
                    assigned_id
                    and assignment_status == "ASSIGNED"
                    and status in ("ASSIGNED", "DOCUMENT_PENDING", "ANALYSIS_READY", "HUMAN_REVIEW")
                    and status not in preliminary_states
                ):
                    due_date = (today + datetime.timedelta(days=2)).isoformat()
                    is_crit = custody_days >= (max_days // 2)
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-ADV-DRAFT", cid, cname, "PREPARE_AND_SIGN_OFF_DRAFT",
                        f"Draft & Sign-Off Bail Petition: {cname}",
                        f"Prepare formal Section 479 bail petition and execute Level-1 Counsel Sign-Off for {cname}.",
                        "DEFENSE_ADVOCATE", assigned_id, assigned_name or "Assigned Defense Counsel", "CRITICAL" if is_crit else "HIGH",
                        due_date, "BNSS_479_EVALUATION_ENGINE",
                        f"Section 479 statutory eligibility reached ({custody_days} days served). Advocate drafting and mandatory human counsel sign-off required.",
                        "PENDING_ACTION", "Assigned Advocate -> Supervising Legal Officer",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 0
                    ))
                    synced_count += 1

                # 5. Supervising Legal Officer: Supervisory Review & Institutional Approval
                if status == "SUBMITTED" and assignment_status == "ASSIGNED":
                    due_date = (today + datetime.timedelta(days=1)).isoformat()
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-SUP-REVIEW", cid, cname, "SUPERVISORY_DRAFT_REVIEW",
                        f"Supervisory Draft Review & Approval: {cname}",
                        f"Level-2 institutional verification of counsel sign-off and SHA-256 petition artifact for {cname}.",
                        "SUPERVISING_LEGAL_OFFICER", None, "Supervising Legal Officer", "CRITICAL",
                        due_date, "SUPERVISORY_OVERSIGHT_QUEUE",
                        f"Counsel draft submitted with Level-1 sign-off. Supervisory legal verification of Section 479 statutory entitlement required prior to court lodgment.",
                        "UNDER_REVIEW", "Supervising Legal Officer -> SLSA Member Secretary",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 1
                    ))
                    synced_count += 1

                # 6. Defense Advocate: Lodge Approved Petition in Court
                if assigned_id and assignment_status == "ASSIGNED" and status in ("APPROVED", "APPROVED_READY_FOR_FILING"):
                    due_date = (today + datetime.timedelta(days=1)).isoformat()
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-COURT-FILING", cid, cname, "FILE_APPLICATION_IN_COURT",
                        f"Lodge Approved Petition in Court: {cname}",
                        f"File approved petition in {getattr(case, 'court_name', 'Competent Court')} and record authentic eFiling/CNR reference.",
                        "DEFENSE_ADVOCATE", assigned_id, assigned_name or "Assigned Defense Counsel", "CRITICAL",
                        due_date, "INSTITUTIONAL_APPROVAL_GATEWAY",
                        f"Supervisory approval granted. Counsel is authorized to file in competent court registry and record formal filing acknowledgement.",
                        "PENDING_ACTION", "Assigned Advocate -> DLSA Secretary",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 1
                    ))
                    synced_count += 1

                # 7. Jail Officer: Confirm Prison Release
                if status in ("RELEASE_WORKFLOW", "ORDER_RECEIVED") and getattr(case, "bail_granted", False):
                    due_date = today_iso
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-PRISON-RELEASE", cid, cname, "CONFIRM_PRISON_RELEASE",
                        f"Confirm Prison Release & Discharge: {cname}",
                        f"Verify solvent surety / release order and confirm physical custody discharge of inmate {cname}.",
                        "JAIL_OFFICER", None, "Jail Superintendent", "CRITICAL",
                        due_date, "COURT_RELEASE_ORDER",
                        f"Competent court granted bail and surety bond verified. Formal prison release memo and gate pass confirmation required from Superintendent.",
                        "PENDING_ACTION", "Jail Superintendent -> Inspector General of Prisons",
                        facility, district, custody_days, completeness_pct, has_conflict, 0,
                        assignment_status, status, hearing_date, 1
                    ))
                    synced_count += 1

                # 8. Supervisory: Resolve Data Conflict / Proviso Exception
                if status in ("DATA_CONFLICT", "MANUAL_REVIEW_REQUIRED", "TRANSITION_BLOCKED"):
                    due_date = (today + datetime.timedelta(days=1)).isoformat()
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-EXCEPTION-RESOLVE", cid, cname, "RESOLVE_DATA_CONFLICT",
                        f"Resolve Institutional Conflict / Exception: {cname}",
                        f"Investigate and resolve data discrepancies across Police/Jail/Court registers for {cname}.",
                        "SUPERVISING_LEGAL_OFFICER", None, "Supervising Legal Officer", "CRITICAL",
                        due_date, "DATA_INTEGRITY_AUDITOR",
                        f"Record discrepancies or statutory provisos block matter progression. Human supervisory review and authoritative determination required.",
                        "EXCEPTION", "Supervising Legal Officer -> Principal District & Sessions Judge",
                        facility, district, custody_days, completeness_pct, 1, legal_aid_need,
                        assignment_status, status, hearing_date, 1
                    ))
                    synced_count += 1

                # 9. DLSA: Hearing Follow-up & Court Production
                if hearing_date and status in ("FILED", "HEARING_SCHEDULED", "ORDER_RECEIVED"):
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-HEARING-FOLLOWUP", cid, cname, "HEARING_FOLLOW_UP",
                        f"Track Court Production & Hearing: {cname}",
                        f"Track scheduled court hearing and inmate production for {cname} ({cid}).",
                        "DLSA_OFFICER", None, "DLSA Court Production Desk", "HIGH",
                        hearing_date, "COURT_REGISTRY_SCHEDULE",
                        f"Matter listed for hearing on {hearing_date}. DLSA coordination of prisoner production and defense representation required under High Court rules.",
                        "PENDING_ACTION", "DLSA Secretary -> Chief Judicial Magistrate",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 0
                    ))
                    synced_count += 1

                # 10. DLSA: Matter Completion Monitoring
                if status in ("POST_RELEASE_FOLLOW_UP", "CLOSED"):
                    due_date = (today + datetime.timedelta(days=7)).isoformat()
                    task_st = "COMPLETED" if status == "CLOSED" else "UNDER_REVIEW"
                    cursor.execute("""
                        INSERT OR REPLACE INTO task_queue (
                            id, case_id, accused_name, task_type, title, description,
                            owner_role, owner_user_id, owner_name, priority, due_date, source, reason,
                            status, escalation_path, facility, district, custody_duration_days,
                            document_completeness_pct, has_data_conflict, legal_aid_need,
                            assignment_status, matter_status, hearing_date, is_consequential, updated_at
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP
                        )
                    """, (
                        f"TASK-{cid}-COMPLETION-MONITOR", cid, cname, "MATTER_COMPLETION_MONITORING",
                        f"Monitor Post-Release & Matter Conclusion: {cname}",
                        f"Post-release tracking and formal matter file closure review for {cname}.",
                        "DLSA_OFFICER", None, "DLSA Case Monitoring Desk", "LOW",
                        due_date, "POST_RELEASE_REGISTER",
                        f"Accused released / matter transitioned to {status}. Verify trial monitoring records and formal closure checklist.",
                        task_st, "DLSA Secretary -> State Legal Services Authority",
                        facility, district, custody_days, completeness_pct, has_conflict, legal_aid_need,
                        assignment_status, status, hearing_date, 0
                    ))
                    synced_count += 1

            conn.commit()

            # Authoritative Cloud Sync to Supabase PostgreSQL
            try:
                from app.supabase_adapter import get_supabase_client, is_supabase_active
                if is_supabase_active():
                    cli = get_supabase_client()
                    if cli:
                        cur_supa = conn.cursor()
                        cur_supa.row_factory = sqlite3.Row
                        all_t = [dict(r) for r in cur_supa.execute("SELECT * FROM task_queue").fetchall()]
                        if all_t:
                            cli.table("task_queue").upsert(all_t).execute()
            except Exception as supa_err:
                logger.warning(f"Supabase task_queue sync note: {supa_err}")
        except Exception as e:
            logger.warning(f"Failed to sync operational tasks: {e}", exc_info=True)
        finally:
            if should_close:
                conn.close()

        return synced_count

    @classmethod
    def get_task_queue(
        cls,
        current_user: AuthUser,
        facility: Optional[str] = None,
        district: Optional[str] = None,
        priority: Optional[str] = None,
        custody_duration_min: Optional[int] = None,
        document_completeness_max: Optional[int] = None,
        legal_aid_need: Optional[bool] = None,
        hearing_date_from: Optional[str] = None,
        hearing_date_to: Optional[str] = None,
        has_data_conflict: Optional[bool] = None,
        assignment_status: Optional[str] = None,
        matter_status: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = "due_date",
        sort_order: Optional[str] = "asc",
    ) -> List[Dict[str, Any]]:
        """
        Retrieve role-scoped, filterable, sortable operational task queue items.
        Enforces server-side institutional boundaries:
        - JAIL_OFFICER: sees tasks scoped to their assigned facilities or owner_role=JAIL_OFFICER
        - DLSA_OFFICER: sees legal aid intake, document, and assignment tasks in their district
        - SUPERVISING_LEGAL_OFFICER: sees supervisory review, conflict, and oversight tasks
        - DEFENSE_ADVOCATE: strictly sees tasks for cases assigned to them
        - POLICE_OFFICER: station-scoped records only
        - PLATFORM_ADMIN / GOV_ADMIN: systemic oversight
        """
        cls.sync_operational_tasks()

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
            user_id = getattr(current_user, "id", "")
            user_full = (getattr(current_user, "full_name", "") or "").lower()
            user_facs = getattr(current_user, "facility_ids", []) or []
            user_dist = getattr(current_user, "district", None) or getattr(current_user, "extra_claims", {}).get("district")
            linked_case = getattr(current_user, "linked_case_id", None)

            query = "SELECT * FROM task_queue WHERE 1=1"
            params: List[Any] = []

            # ── Strict Role Boundary Scoping ──────────────────────────────────────
            if role == "JAIL_OFFICER":
                query += " AND owner_role = 'JAIL_OFFICER'"
                if user_facs:
                    placeholders = ", ".join("?" for _ in user_facs)
                    query += f" AND facility IN ({placeholders})"
                    params.extend(user_facs)

            elif role in ("DEFENSE_ADVOCATE", "CONTROLLED_EXTERNAL_ADVOCATE"):
                query += " AND owner_role = 'DEFENSE_ADVOCATE' AND assignment_status = 'ASSIGNED'"
                query += " AND matter_status NOT IN ('INTAKE', 'INTAKE_PENDING', 'DETECTED', 'VERIFICATION', 'CUSTODY_VERIFIED', 'CUSTODY_PENDING', 'REVIEW', 'LEGAL_AID_REQUIRED', 'LEGAL_NEED_IDENTIFIED', 'PRE_INTAKE', 'DOCUMENTS_MISSING', 'DRAFT_INTAKE')"
                if user_id == "demo_advocate":
                    query += " AND (owner_user_id IN ('demo_advocate', 'adv_001', 'adv_rajesh_sharma') OR case_id IN (SELECT case_id FROM cases WHERE assigned_lawyer_id IN ('demo_advocate', 'adv_001', 'adv_rajesh_sharma') UNION SELECT accused_id FROM court_cases WHERE assigned_lawyer_id IN ('demo_advocate', 'adv_001', 'adv_rajesh_sharma')))"
                elif user_id == "demo_ext_advocate":
                    query += " AND (owner_user_id IN ('demo_ext_advocate', 'adv_ext_001') OR case_id IN (SELECT case_id FROM cases WHERE assigned_lawyer_id IN ('demo_ext_advocate', 'adv_ext_001') UNION SELECT accused_id FROM court_cases WHERE assigned_lawyer_id IN ('demo_ext_advocate', 'adv_ext_001')))"
                else:
                    query += " AND (owner_user_id = ? OR case_id IN (SELECT case_id FROM cases WHERE assigned_lawyer_id = ? UNION SELECT accused_id FROM court_cases WHERE assigned_lawyer_id = ?))"
                    params.extend([user_id, user_id, user_id])

            elif role == "DLSA_OFFICER":
                query += " AND owner_role IN ('DLSA_OFFICER', 'SUPERVISING_LEGAL_OFFICER')"
                if user_dist:
                    query += " AND district = ?"
                    params.append(user_dist)

            elif role == "SUPERVISING_LEGAL_OFFICER":
                query += " AND owner_role IN ('SUPERVISING_LEGAL_OFFICER', 'DLSA_OFFICER')"
                query += " AND (task_type != 'SUPERVISORY_DRAFT_REVIEW' OR assignment_status = 'ASSIGNED')"
                if user_dist:
                    query += " AND district = ?"
                    params.append(user_dist)

            elif role == "POLICE_OFFICER":
                station = getattr(current_user, "police_station", None) or getattr(current_user, "extra_claims", {}).get("police_station", "")
                if station:
                    query += " AND facility = ?"
                    params.append(station)
                else:
                    query += " AND 1=0"

            elif role in ("ACCUSED_USER", "FAMILY_GUARDIAN"):
                if linked_case:
                    query += " AND case_id = ?"
                    params.append(linked_case)
                else:
                    query += " AND 1=0"

            # ── Dynamic Filter Criteria ───────────────────────────────────────────
            if facility:
                query += " AND facility LIKE ?"
                params.append(f"%{facility}%")

            if district:
                query += " AND district LIKE ?"
                params.append(f"%{district}%")

            if priority:
                query += " AND priority = ?"
                params.append(priority.upper())

            if custody_duration_min is not None:
                query += " AND custody_duration_days >= ?"
                params.append(custody_duration_min)

            if document_completeness_max is not None:
                query += " AND document_completeness_pct <= ?"
                params.append(document_completeness_max)

            if legal_aid_need is not None:
                query += " AND legal_aid_need = ?"
                params.append(1 if legal_aid_need else 0)

            if has_data_conflict is not None:
                query += " AND has_data_conflict = ?"
                params.append(1 if has_data_conflict else 0)

            if assignment_status:
                query += " AND assignment_status = ?"
                params.append(assignment_status.upper())

            if matter_status:
                query += " AND matter_status = ?"
                params.append(matter_status.upper())

            today_iso = datetime.date.today().isoformat()
            if status:
                if status.upper() == "OVERDUE":
                    query += " AND (status = 'OVERDUE' OR (status != 'COMPLETED' AND due_date < ?))"
                    params.append(today_iso)
                else:
                    query += " AND status = ?"
                    params.append(status.upper())

            if search:
                s_term = f"%{search.strip()}%"
                query += " AND (title LIKE ? OR reason LIKE ? OR accused_name LIKE ? OR case_id LIKE ?)"
                params.extend([s_term, s_term, s_term, s_term])

            # ── Sorting ───────────────────────────────────────────────────────────
            order_dir = "DESC" if (sort_order or "").lower() == "desc" else "ASC"
            valid_sort_fields = {
                "due_date": "due_date",
                "priority": "CASE priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 WHEN 'LOW' THEN 4 ELSE 5 END",
                "custody_duration_days": "custody_duration_days",
                "created_at": "created_at",
                "status": "status",
            }
            sort_expr = valid_sort_fields.get(sort_by or "due_date", "due_date")
            query += f" ORDER BY {sort_expr} {order_dir}"

            rows = cursor.execute(query, params).fetchall()
            items = []
            for r in rows:
                d = dict(r)
                if d.get("status") not in ("COMPLETED", "EXCEPTION") and d.get("due_date") and d["due_date"] < today_iso:
                    d["status"] = "OVERDUE"
                items.append(d)
            return items
        finally:
            conn.close()

    @classmethod
    def update_task(
        cls,
        task_id: str,
        updates: Dict[str, Any],
        current_user: AuthUser,
    ) -> Dict[str, Any]:
        """Update task status, priority, or owner for safe, non-consequential workflow adjustments."""
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            task_row = cursor.execute("SELECT * FROM task_queue WHERE id = ?", (task_id,)).fetchone()
            if not task_row:
                raise LookupError(f"Task '{task_id}' not found.")

            task = dict(task_row)

            # Prohibit mutating consequential tasks through generic task update
            if task.get("is_consequential") and updates.get("status") in ("COMPLETED", "APPROVED", "FILED", "RELEASED"):
                raise PermissionError(
                    "Consequential task cannot be completed through generic metadata update. "
                    "Must be executed via authoritative legal or custody transition gateway."
                )

            fields = []
            vals = []
            if "status" in updates and updates["status"]:
                fields.append("status = ?")
                vals.append(updates["status"])
                if updates["status"] == "COMPLETED":
                    fields.append("completed_at = CURRENT_TIMESTAMP")
                    fields.append("completed_by = ?")
                    vals.append(current_user.full_name or current_user.id)

            if "priority" in updates and updates["priority"]:
                fields.append("priority = ?")
                vals.append(updates["priority"])

            if "owner_user_id" in updates:
                fields.append("owner_user_id = ?")
                vals.append(updates["owner_user_id"])

            if "owner_name" in updates:
                fields.append("owner_name = ?")
                vals.append(updates["owner_name"])

            if "due_date" in updates and updates["due_date"]:
                fields.append("due_date = ?")
                vals.append(updates["due_date"])

            fields.append("updated_at = CURRENT_TIMESTAMP")
            vals.append(task_id)

            cursor.execute(f"UPDATE task_queue SET {', '.join(fields)} WHERE id = ?", vals)
            conn.commit()

            # Authoritative Cloud Sync to Supabase PostgreSQL
            try:
                from app.supabase_adapter import get_supabase_client, is_supabase_active
                if is_supabase_active():
                    cli = get_supabase_client()
                    if cli:
                        supa_updates = {k: v for k, v in updates.items() if k in ("status", "priority", "owner_user_id", "owner_name", "due_date")}
                        if updates.get("status") == "COMPLETED":
                            supa_updates["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            supa_updates["completed_by"] = current_user.full_name or current_user.id
                        supa_updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        cli.table("task_queue").update(supa_updates).eq("id", task_id).execute()
            except Exception as e:
                logger.warning(f"Supabase task update note: {e}")

            updated_row = cursor.execute("SELECT * FROM task_queue WHERE id = ?", (task_id,)).fetchone()
            return dict(updated_row)
        finally:
            conn.close()

    @classmethod
    def execute_bulk_action(
        cls,
        action: str,
        task_ids: List[str],
        payload: Dict[str, Any],
        current_user: AuthUser,
    ) -> Dict[str, Any]:
        """
        Execute safe, reversible bulk actions on multiple task queue items.
        STRICT GUARANTEE: Legally consequential actions (approvals, filings, releases, closures)
        are unconditionally REJECTED with HTTP 400.
        """
        consequential_actions = {
            "SUPERVISORY_APPROVE", "APPROVE", "APPROVE_DRAFT",
            "RECORD_FILING", "FILE_IN_COURT", "FILE",
            "CONFIRM_PRISON_RELEASE", "CONFIRM_RELEASE", "RELEASE",
            "CLOSE_MATTER", "CLOSE",
        }
        act_upper = (action or "").strip().upper()
        if act_upper in consequential_actions:
            raise ValueError(
                f"Consequential action '{action}' cannot be performed in bulk. "
                "Each legal petition approval, court filing, prison release, or matter closure "
                "requires individual case review, certified document verification, and cryptographic audit logging."
            )

        safe_actions = {"ASSIGN_OWNER", "MARK_REVIEWED", "UPDATE_METADATA", "ACKNOWLEDGE"}
        if act_upper not in safe_actions:
            raise ValueError(
                f"Unsupported bulk action '{action}'. Permitted safe bulk actions: {sorted(list(safe_actions))}."
            )

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            updated_ids = []
            skipped_ids = []

            for tid in task_ids:
                row = cursor.execute("SELECT * FROM task_queue WHERE id = ?", (tid,)).fetchone()
                if not row:
                    skipped_ids.append(tid)
                    continue

                t = dict(row)
                if act_upper == "ASSIGN_OWNER":
                    owner_uid = payload.get("owner_user_id")
                    owner_nm = payload.get("owner_name")
                    cursor.execute(
                        "UPDATE task_queue SET owner_user_id = ?, owner_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (owner_uid, owner_nm, tid),
                    )
                    updated_ids.append(tid)

                elif act_upper == "MARK_REVIEWED":
                    if t.get("is_consequential"):
                        skipped_ids.append(tid)
                        continue
                    cursor.execute(
                        "UPDATE task_queue SET status = 'UNDER_REVIEW', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (tid,),
                    )
                    updated_ids.append(tid)

                elif act_upper == "ACKNOWLEDGE":
                    new_status = "PENDING_ACTION" if t.get("status") == "NEW" else t.get("status")
                    cursor.execute(
                        "UPDATE task_queue SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_status, tid),
                    )
                    updated_ids.append(tid)

                elif act_upper == "UPDATE_METADATA":
                    prio = payload.get("priority")
                    if prio:
                        cursor.execute(
                            "UPDATE task_queue SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            (prio.upper(), tid),
                        )
                        updated_ids.append(tid)

            conn.commit()

            return {
                "action": act_upper,
                "total_requested": len(task_ids),
                "updated_count": len(updated_ids),
                "updated_task_ids": updated_ids,
                "skipped_count": len(skipped_ids),
                "skipped_task_ids": skipped_ids,
                "message": f"Successfully executed safe bulk action '{act_upper}' on {len(updated_ids)} items.",
            }
        finally:
            conn.close()

    @classmethod
    def intake_new_custody_record(
        cls,
        data: CustodyIntakeRequest,
        current_user: AuthUser,
    ) -> Dict[str, Any]:
        """
        Record a newly admitted undertrial prisoner into institutional custody.
        Strictly restricted to JAIL_OFFICER within their assigned facility.
        """
        if current_user.role != Role.JAIL_OFFICER:
            raise PermissionError("Forbidden: Only authorized Jail Officers can intake custody records.")

        user_facs = getattr(current_user, "facility_ids", []) or []
        if user_facs and data.facility_id not in user_facs and not any(f in data.facility_id for f in user_facs):
            raise PermissionError(
                f"Forbidden: Facility '{data.facility_id}' is outside your authorized correctional facilities: {user_facs}."
            )

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Generate unique synthetic case_id
            import time
            cid = f"UTP-J{int(time.time()) % 10000:04d}"
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            today_iso = datetime.date.today().isoformat()

            # Normalize facility ID
            raw_fac = (data.facility_id or "").lower()
            if "rohini" in raw_fac:
                fac_id = "fac_rohini_jail"
            elif "mandoli" in raw_fac:
                fac_id = "fac_mandoli_jail"
            elif "lucknow" in raw_fac:
                fac_id = "fac_lucknow_jail"
            elif "bengaluru" in raw_fac:
                fac_id = "fac_bengaluru_jail"
            elif "02" in raw_fac:
                fac_id = "fac_tihar_jail_02"
            elif (data.facility_id or "").startswith("fac_"):
                fac_id = data.facility_id
            else:
                fac_id = "fac_tihar_jail_04"

            # 1. Insert into accused_persons
            cursor.execute("""
                INSERT INTO accused_persons (
                    id, full_name, gender, permanent_address,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                cid, data.name, "Male", data.district or "Not Provided"
            ))

            # 2. Insert into custody_records
            cursor.execute("""
                INSERT INTO custody_records (
                    id, accused_id, facility_id, admission_date, prisoner_category, created_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                f"CUST-{cid}-01", cid, fac_id, data.admission_date or today_iso, "UNDERTRIAL"
            ))

            # 3. Insert into cases (shared canonical case model)
            case_dict = {
                "case_id": cid,
                "name": data.name,
                "accused_name": data.name,
                "offense_sections": data.offense_sections,
                "arrest_date": data.arrest_date,
                "admission_date": data.admission_date or today_iso,
                "custody_days": 1,
                "max_sentence_days_for_offense": data.max_sentence_days or 1095,
                "court_name": data.court_name or "Competent Remand Court",
                "district": data.district,
                "jail_location": data.facility_name or data.facility_id,
                "facility_id": data.facility_id,
                "assignment_status": "AVAILABLE",
                "assigned_lawyer": None,
                "assigned_lawyer_id": None,
                "status": "INTAKE",
                "current_status": "INTAKE",
                "legal_aid_status": "FLAGGED_BY_PRISON" if data.refer_to_dlsa else "PENDING_VERIFICATION",
                "missing_docs": ["Charge Sheet", "Remand Sheet"],
                "present_docs": ["Prison Admission Record"],
                "urgency_flags": {"age": 30, "health_flag": False, "repeat_offender": False, "score": 0, "reasons": []},
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            import json
            cursor.execute("""
                INSERT INTO cases (case_id, data, status, assignment_status, assigned_lawyer_id, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (cid, json.dumps(case_dict), "INTAKE", "AVAILABLE", None))

            cursor.execute("""
                INSERT OR REPLACE INTO court_cases (
                    id, accused_id, case_number, current_status, court_name, district, created_at, updated_at
                ) VALUES (?, ?, ?, 'INTAKE', ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (cid, cid, f"REMAND-2026-{cid}", data.court_name or "Competent Court", data.district))

            conn.commit()

            # Authoritative Cloud Sync to Supabase PostgreSQL
            try:
                from app.supabase_adapter import get_supabase_client, is_supabase_active
                if is_supabase_active():
                    cli = get_supabase_client()
                    if cli:
                        cli.table("accused_persons").upsert({
                            "id": cid,
                            "full_name": data.name,
                            "gender": "Male",
                            "permanent_address": data.district or "Not Provided",
                        }).execute()
                        cli.table("custody_records").upsert({
                            "id": f"CUST-{cid}-01",
                            "accused_id": cid,
                            "facility_id": fac_id,
                            "admission_date": data.admission_date or today_iso,
                            "prisoner_category": "UNDERTRIAL",
                        }).execute()
                        cli.table("cases").upsert({
                            "case_id": cid,
                            "data": case_dict,
                            "status": "INTAKE",
                            "assignment_status": "AVAILABLE",
                        }).execute()
                        cli.table("court_cases").upsert({
                            "id": cid,
                            "accused_id": cid,
                            "case_number": f"REMAND-2026-{cid}",
                            "current_status": "INTAKE",
                            "court_name": data.court_name or "Competent Court",
                            "district": data.district,
                        }).execute()
            except Exception as supa_err:
                logger.warning(f"Supabase intake sync note: {supa_err}")
        finally:
            conn.close()

        # Update in-memory registry for instant retrieval
        from app.database import _MEMORY_CASES
        try:
            _MEMORY_CASES[cid] = CaseRecord(**case_dict)
        except Exception as e:
            logger.warning(f"Failed to populate _MEMORY_CASES: {e}")

        # Log timeline event
        append_case_timeline_event(
            cid,
            TimelineEvent(
                id=f"TLE-{cid}-INTAKE-{int(time.time()) % 10000}",
                timestamp=now_iso,
                event_type="PRISON_CUSTODY",
                title="Custody Admission Recorded",
                description=f"Inmate admitted to {data.facility_name or data.facility_id}. Arrest date: {data.arrest_date}. Charges: {', '.join(data.offense_sections)}.",
                actor=current_user.full_name or current_user.id,
                actor_role=current_user.role.value,
                source="Correctional Facility Intake Desk",
                is_human_verified=True,
            ),
        )

        if data.refer_to_dlsa:
            add_notification(
                case_id=cid,
                title=f"Legal Aid Referral: {data.name} ({cid})",
                message=f"Jail Superintendent referred newly admitted inmate {data.name} for DLSA legal-aid counsel assignment.",
                notif_type="urgent",
                target_role="DLSA_OFFICER",
            )

        # Refresh tasks
        cls.sync_operational_tasks()

        return {
            "case_id": cid,
            "name": data.name,
            "facility_id": data.facility_id,
            "status": "INTAKE",
            "legal_aid_status": "FLAGGED_BY_PRISON" if data.refer_to_dlsa else "PENDING_VERIFICATION",
            "message": f"Custody record for {data.name} ({cid}) successfully recorded.",
        }

    @classmethod
    def record_custody_event(
        cls,
        case_id: str,
        data: CustodyEventRequest,
        current_user: AuthUser,
    ) -> Dict[str, Any]:
        """Log official prison custody event (remand extension, transfer, court production)."""
        if current_user.role != Role.JAIL_OFFICER:
            raise PermissionError("Forbidden: Only Jail Officers are authorized to record prison custody events.")

        case = get_case(case_id)
        if not case:
            raise LookupError(f"Case '{case_id}' not found.")

        user_facs = getattr(current_user, "facility_ids", []) or []
        case_fac = getattr(case, "jail_location", "") or getattr(case, "facility_id", "")
        if user_facs and case_fac and not any(f in case_fac for f in user_facs):
            raise PermissionError(f"Forbidden: Case '{case_id}' is outside your authorized facility.")

        import time
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        event_title = data.event_type.replace("_", " ").title()

        append_case_timeline_event(
            case_id,
            TimelineEvent(
                id=f"TLE-{case_id}-CE-{int(time.time()) % 10000}",
                timestamp=now_iso,
                event_type="PRISON_CUSTODY",
                title=f"Custody Event: {event_title}",
                description=f"Date: {data.event_date}. Court: {data.court_name or 'Designated Bench'}. Remarks: {data.notes}",
                actor=current_user.full_name or current_user.id,
                actor_role=current_user.role.value,
                source="Jail Custody Desk",
                is_human_verified=data.verified,
            ),
        )

        return {
            "case_id": case_id,
            "event_type": data.event_type,
            "event_date": data.event_date,
            "message": f"Custody event '{event_title}' recorded successfully for case {case_id}.",
        }

    @classmethod
    def update_accused_profile(
        cls,
        case_id: str,
        data: AccusedProfileUpdateRequest,
        current_user: AuthUser,
    ) -> Dict[str, Any]:
        """Capture missing accused/inmate profile information (guardian, DOB, address, contact)."""
        if current_user.role not in (Role.JAIL_OFFICER, Role.DLSA_OFFICER, Role.PLATFORM_ADMIN):
            raise PermissionError("Forbidden: You are not authorized to update accused profile records.")

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            acc_id_slug = f"acc_{case_id.lower().replace('-', '_')}"
            accused = cursor.execute("SELECT * FROM accused_persons WHERE id = ? OR id = ?", (case_id, acc_id_slug)).fetchone()
            if not accused:
                raise LookupError(f"Accused record '{case_id}' not found.")
            real_acc_id = accused["id"]

            fields = []
            vals = []
            if data.date_of_birth:
                fields.append("date_of_birth = ?")
                vals.append(data.date_of_birth)
            if data.age is not None:
                fields.append("age = ?")
                vals.append(data.age)
            if data.gender:
                fields.append("gender = ?")
                vals.append(data.gender)
            if data.permanent_address:
                fields.append("permanent_address = ?")
                vals.append(data.permanent_address)
            if data.emergency_family_contact_name:
                fields.append("relative_name = ?")
                vals.append(data.emergency_family_contact_name)
            if data.emergency_family_contact_relation:
                fields.append("relative_relation = ?")
                vals.append(data.emergency_family_contact_relation)
            if data.emergency_family_contact_phone:
                fields.append("relative_phone = ?")
                vals.append(data.emergency_family_contact_phone)
            elif data.contact_number:
                fields.append("relative_phone = ?")
                vals.append(data.contact_number)

            if fields:
                fields.append("updated_at = CURRENT_TIMESTAMP")
                vals.append(real_acc_id)
                cursor.execute(f"UPDATE accused_persons SET {', '.join(fields)} WHERE id = ?", vals)

            # Update family contact if provided
            if data.emergency_family_contact_name:
                cursor.execute("""
                    INSERT OR REPLACE INTO family_contacts (
                        id, accused_id, name, relation, phone, is_primary_contact, verified_by_dlsa
                    ) VALUES (?, ?, ?, ?, ?, 1, 1)
                """, (
                    f"FAM-{case_id}-01", real_acc_id, data.emergency_family_contact_name,
                    data.emergency_family_contact_relation or "Guardian",
                    data.emergency_family_contact_phone or "Not Provided"
                ))

            conn.commit()

            # Authoritative Cloud Sync to Supabase PostgreSQL
            try:
                from app.supabase_adapter import get_supabase_client, is_supabase_active
                if is_supabase_active():
                    cli = get_supabase_client()
                    if cli:
                        supa_acc_updates = {}
                        if data.date_of_birth: supa_acc_updates["date_of_birth"] = data.date_of_birth
                        if data.age is not None: supa_acc_updates["age"] = data.age
                        if data.gender: supa_acc_updates["gender"] = data.gender
                        if data.permanent_address: supa_acc_updates["permanent_address"] = data.permanent_address
                        if data.emergency_family_contact_name: supa_acc_updates["relative_name"] = data.emergency_family_contact_name
                        if data.emergency_family_contact_relation: supa_acc_updates["relative_relation"] = data.emergency_family_contact_relation
                        if data.emergency_family_contact_phone: supa_acc_updates["relative_phone"] = data.emergency_family_contact_phone
                        elif data.contact_number: supa_acc_updates["relative_phone"] = data.contact_number
                        if supa_acc_updates:
                            supa_acc_updates["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            cli.table("accused_persons").update(supa_acc_updates).or_(f"id.eq.{case_id},id.eq.{real_acc_id}").execute()
                        if data.emergency_family_contact_name:
                            cli.table("family_contacts").upsert({
                                "id": f"FAM-{case_id}-01",
                                "accused_id": real_acc_id,
                                "name": data.emergency_family_contact_name,
                                "relation": data.emergency_family_contact_relation or "Guardian",
                                "phone": data.emergency_family_contact_phone or "Not Provided",
                                "is_primary_contact": True,
                                "verified_by_dlsa": True,
                            }).execute()
            except Exception as supa_err:
                logger.warning(f"Supabase profile update sync note: {supa_err}")
        finally:
            conn.close()

        import time
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        append_case_timeline_event(
            case_id,
            TimelineEvent(
                id=f"TLE-{case_id}-PROF-{int(time.time()) % 10000}",
                timestamp=now_iso,
                event_type="PROFILE_UPDATE",
                title="Accused Inmate Profile Updated",
                description=f"Updated profile fields by {current_user.full_name or current_user.id} ({current_user.role.value}).",
                actor=current_user.full_name or current_user.id,
                actor_role=current_user.role.value,
                source="Institutional Intake Desk",
                is_human_verified=True,
            ),
        )

        return {
            "case_id": case_id,
            "message": "Accused inmate profile updated successfully.",
        }

    @classmethod
    def confirm_prison_release(
        cls,
        case_id: str,
        data: PrisonReleaseConfirmationRequest,
        current_user: AuthUser,
    ) -> Dict[str, Any]:
        """
        Confirm physical discharge of inmate from prison custody upon court bail grant.
        Strictly restricted to JAIL_OFFICER.
        Executes authoritative state transition to POST_RELEASE_FOLLOW_UP.
        """
        if current_user.role != Role.JAIL_OFFICER:
            raise PermissionError("Forbidden: Only Jail Officers are authorized to confirm prison release.")

        case = get_case(case_id)
        if not case:
            raise LookupError(f"Case '{case_id}' not found.")

        # Facility check
        user_facs = getattr(current_user, "facility_ids", []) or []
        case_fac = getattr(case, "jail_location", "") or getattr(case, "facility_id", "")
        if user_facs and case_fac and not any(f in case_fac for f in user_facs):
            raise PermissionError(f"Forbidden: Case '{case_id}' is outside your authorized facility.")

        from app.workflow.service import WorkflowService
        result = WorkflowService.execute_transition(
            case_id=case_id,
            action="CONFIRM_PRISON_RELEASE",
            actor=current_user,
            payload={
                "release_date": data.release_date,
                "gate_pass_number": data.gate_pass_number,
                "surety_ref": data.surety_verification_ref,
                "notes": data.superintendent_notes,
            },
            comment=f"Physical prison release confirmed under gate pass {data.gate_pass_number}.",
        )

        # Update custody_records release date
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE custody_records SET release_date = ? WHERE accused_id = ? OR id = ?",
                (data.release_date, case_id, f"cus_{case_id.lower().replace('-', '_')}"),
            )
            conn.commit()

            # Authoritative Cloud Sync to Supabase PostgreSQL
            try:
                from app.supabase_adapter import get_supabase_client, is_supabase_active
                if is_supabase_active():
                    cli = get_supabase_client()
                    if cli:
                        cli.table("custody_records").update({
                            "release_date": data.release_date
                        }).or_(f"accused_id.eq.{case_id},accused_id.eq.acc_{case_id.lower().replace('-', '_')}").execute()
            except Exception as supa_err:
                logger.warning(f"Supabase custody release sync note: {supa_err}")
        finally:
            conn.close()

        cls.sync_operational_tasks()

        return {
            "case_id": case_id,
            "gate_pass_number": data.gate_pass_number,
            "release_date": data.release_date,
            "canonical_state": result["canonical_state"],
            "message": f"Inmate physical discharge confirmed. Case '{case_id}' transitioned to post-release follow-up.",
        }
