"""
app.analytics.scheduled_reports — Scheduled Reports Management and Execution Framework.

Supports:
1. Automated periodic report scheduling (DAILY, WEEKLY, MONTHLY, QUARTERLY).
2. Data minimization enforcement (AGGREGATE_ONLY summaries, secure portal links).
3. Execution tracking with audit logging in scheduled_report_executions.
4. Role-based scoping by organization and jurisdiction.
"""
from __future__ import annotations

import datetime
import json
import logging
import uuid
from typing import List, Optional

from fastapi import HTTPException, status

from app.auth.dependencies import AuthUser
from app.auth.roles import Role
from app.auth.user_store import get_user_by_email
from app.database import get_db_connection
from app.analytics.schemas import (
    ReportFrequency,
    ScheduledReportCreateRequest,
    ScheduledReportRecord,
    ScheduledExecutionRecord,
)
from app.analytics.service import AnalyticsService

logger = logging.getLogger("nyaya_mitra.analytics.scheduled_reports")

# Official approved domains for institutional reporting
OFFICIAL_APPROVED_DOMAINS = (
    "gov.in",
    "nic.in",
    "delhi.gov.in",
    "nyayamitra.in",
    "nyayamitra.org",
    "kslsa.kar.nic.in",
    "delhicourts.nic.in",
    "tiharprisons.delhi.gov.in",
)


def _calculate_next_run(frequency: ReportFrequency) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    if frequency == ReportFrequency.DAILY:
        next_date = now + datetime.timedelta(days=1)
    elif frequency == ReportFrequency.WEEKLY:
        next_date = now + datetime.timedelta(weeks=1)
    elif frequency == ReportFrequency.MONTHLY:
        next_date = now + datetime.timedelta(days=30)
    elif frequency == ReportFrequency.QUARTERLY:
        next_date = now + datetime.timedelta(days=90)
    else:
        next_date = now + datetime.timedelta(days=7)
    return next_date.isoformat()


class ScheduledReportManager:
    """Manager for scheduled reports lifecycle, recipient verification, and execution."""

    @classmethod
    def list_schedules(cls, user: AuthUser) -> List[ScheduledReportRecord]:
        conn = get_db_connection()
        cursor = conn.cursor()

        is_state_level = user.role in (Role.PLATFORM_ADMIN, Role.GOV_ADMIN, Role.READ_ONLY_AUDITOR)

        if is_state_level:
            cursor.execute(
                """
                SELECT id, title, report_type, frequency, recipients_json,
                       jurisdiction, data_minimization_level, is_active,
                       last_run_at, next_run_at, created_at
                FROM scheduled_reports
                ORDER BY created_at DESC
                """
            )
        else:
            jurisdiction = user.district or ""
            cursor.execute(
                """
                SELECT id, title, report_type, frequency, recipients_json,
                       jurisdiction, data_minimization_level, is_active,
                       last_run_at, next_run_at, created_at
                FROM scheduled_reports
                WHERE (jurisdiction = ? AND jurisdiction != 'ALL') OR created_by_user_id = ?
                ORDER BY created_at DESC
                """,
                (jurisdiction, user.id),
            )

        rows = cursor.fetchall()
        schedules = []
        for r in rows:
            try:
                recipients = json.loads(r[4]) if r[4] else []
            except Exception:
                recipients = []
            schedules.append(
                ScheduledReportRecord(
                    id=r[0],
                    title=r[1],
                    report_type=r[2],
                    frequency=r[3],
                    recipients=recipients,
                    jurisdiction=r[5] or "ALL",
                    data_minimization_level=r[6] or "AGGREGATE_ONLY",
                    is_active=bool(r[7]),
                    last_run_at=str(r[8]) if r[8] else None,
                    next_run_at=str(r[9]) if r[9] else None,
                    created_at=str(r[10]),
                )
            )
        return schedules

    @classmethod
    def _validate_recipients(cls, user: AuthUser, recipients: List[str]) -> List[str]:
        """
        Validate that every recipient email is an approved registered user
        or from an authorized official government/judicial domain.
        """
        validated = []
        for email in recipients:
            clean_email = email.strip().lower()
            if not clean_email or "@" not in clean_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid email address format: '{email}'.",
                )

            domain = clean_email.split("@")[-1]
            rec_user = get_user_by_email(clean_email)

            if rec_user:
                if not rec_user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Recipient '{email}' is an inactive user account.",
                    )
                # Ensure institutional clearance
                if rec_user.role not in (
                    Role.PLATFORM_ADMIN,
                    Role.GOV_ADMIN,
                    Role.DLSA_OFFICER,
                    Role.SUPERVISING_LEGAL_OFFICER,
                    Role.JAIL_OFFICER,
                    Role.READ_ONLY_AUDITOR,
                    Role.DEFENSE_ADVOCATE,
                    Role.CONTROLLED_EXTERNAL_ADVOCATE,
                ):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Recipient '{email}' is not authorized to receive institutional reports.",
                    )
            elif any(domain == app_dom or domain.endswith("." + app_dom) for app_dom in OFFICIAL_APPROVED_DOMAINS):
                # Authorized institutional domain
                pass
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Recipient '{email}' is not an approved registered user or authorized official domain.",
                )

            validated.append(clean_email)
        return validated

    @classmethod
    def create_schedule(cls, user: AuthUser, req: ScheduledReportCreateRequest) -> ScheduledReportRecord:
        # Validate clearance
        if user.role not in (
            Role.PLATFORM_ADMIN,
            Role.GOV_ADMIN,
            Role.DLSA_OFFICER,
            Role.SUPERVISING_LEGAL_OFFICER,
            Role.JAIL_OFFICER,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User role is not authorized to create scheduled reports.",
            )

        if not req.recipients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one recipient email must be specified.",
            )

        # Enforce approved recipient validation
        validated_recipients = cls._validate_recipients(user, req.recipients)

        schedule_id = f"sch_{uuid.uuid4().hex[:10]}"
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        next_run = _calculate_next_run(req.frequency)
        effective_jurisdiction = req.jurisdiction or user.district or "ALL"

        conn = get_db_connection()
        cursor = conn.cursor()
        user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
        cursor.execute(
            """
            INSERT INTO scheduled_reports (
                id, title, report_type, frequency, recipients_json,
                organization_id, jurisdiction, data_minimization_level,
                created_by_user_id, created_by_role,
                is_active, last_run_at, next_run_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, ?)
            """,
            (
                schedule_id,
                req.title.strip(),
                req.report_type.upper(),
                req.frequency.value,
                json.dumps(validated_recipients),
                getattr(user, "org_id", "") or "DEFAULT",
                effective_jurisdiction,
                req.data_minimization_level,
                user.id,
                user_role_str,
                next_run,
                now_str,
            ),
        )
        conn.commit()

        return ScheduledReportRecord(
            id=schedule_id,
            title=req.title.strip(),
            report_type=req.report_type.upper(),
            frequency=req.frequency.value,
            recipients=validated_recipients,
            jurisdiction=effective_jurisdiction,
            data_minimization_level=req.data_minimization_level,
            is_active=True,
            last_run_at=None,
            next_run_at=next_run,
            created_at=now_str,
        )

    @classmethod
    def trigger_schedule(cls, user: AuthUser, schedule_id: str) -> ScheduledExecutionRecord:
        """Manually execute a report schedule with strong ownership and jurisdiction enforcement."""
        if user.role in (
            Role.READ_ONLY_AUDITOR,
            Role.ACCUSED_USER,
            Role.FAMILY_GUARDIAN,
            Role.POLICE_OFFICER,
        ) or user.role not in (
            Role.PLATFORM_ADMIN,
            Role.GOV_ADMIN,
            Role.DLSA_OFFICER,
            Role.SUPERVISING_LEGAL_OFFICER,
            Role.JAIL_OFFICER,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Role not authorized to trigger scheduled report executions.",
            )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, title, report_type, frequency, recipients_json,
                   jurisdiction, data_minimization_level, created_by_user_id
            FROM scheduled_reports
            WHERE id = ?
            """,
            (schedule_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scheduled report {schedule_id} not found.",
            )

        title = row[1]
        report_type = row[2]
        frequency = row[3]
        jurisdiction = row[5] or "ALL"
        created_by_user_id = row[7]

        # Strong ownership & jurisdiction authorization check
        is_state_level = user.role in (Role.PLATFORM_ADMIN, Role.GOV_ADMIN)
        if not is_state_level:
            is_owner = bool(created_by_user_id and user.id == created_by_user_id)
            has_district_jurisdiction = bool(
                user.district and
                user.district.upper() != "ALL" and
                jurisdiction != "ALL" and
                user.district.strip().lower() == jurisdiction.strip().lower()
            )
            if not (is_owner or has_district_jurisdiction):
                logger.warning(
                    "User %s (district: %s) attempted unauthorized execution of schedule %s (jurisdiction: %s, creator: %s)",
                    user.id, user.district, schedule_id, jurisdiction, created_by_user_id
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have ownership or jurisdictional clearance to trigger this scheduled report.",
                )

        # Generate minimized aggregated summary
        exec_id = f"exec_{uuid.uuid4().hex[:10]}"
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Build minimized content summary
        summary_payload = cls._build_minimized_summary(user, report_type, jurisdiction)
        summary_text = json.dumps(summary_payload, indent=2)

        # Record execution
        cursor.execute(
            """
            INSERT INTO scheduled_report_executions (
                id, schedule_id, executed_at, status, summary_content, delivery_channel
            ) VALUES (?, ?, ?, 'SUCCESS', ?, 'SECURE_NOTIFICATION')
            """,
            (exec_id, schedule_id, now_str, summary_text),
        )

        # Update last run and next run
        freq_enum = ReportFrequency(frequency) if frequency in ReportFrequency._value2member_map_ else ReportFrequency.WEEKLY
        next_run = _calculate_next_run(freq_enum)
        cursor.execute(
            """
            UPDATE scheduled_reports
            SET last_run_at = ?, next_run_at = ?
            WHERE id = ?
            """,
            (now_str, next_run, schedule_id),
        )
        conn.commit()

        return ScheduledExecutionRecord(
            id=exec_id,
            schedule_id=schedule_id,
            executed_at=now_str,
            status="SUCCESS",
            summary_content=summary_text,
            delivery_channel="SECURE_NOTIFICATION",
        )

    @classmethod
    def _build_minimized_summary(cls, user: AuthUser, report_type: str, jurisdiction: str) -> dict:
        """Construct privacy-preserving summary without raw individual case files."""
        if report_type == "LEADERSHIP_REPORT":
            rep = AnalyticsService.get_leadership_report(user)
            return {
                "report": rep.title,
                "period": rep.period,
                "summary": rep.executive_summary,
                "benchmarks": rep.turnaround_benchmarks,
                "secure_link": "/reports?tab=leadership",
            }
        elif report_type == "IMPACT_METRICS":
            imp = AnalyticsService.get_impact_dashboard(user)
            return {
                "report": imp.title,
                "fewer_missed_actions_pct": imp.fewer_missed_actions_pct,
                "faster_assignment_reduction_pct": imp.faster_assignment_reduction_pct,
                "hours_saved": imp.manual_search_hours_avoided,
                "secure_link": "/reports?tab=impact",
            }
        else:
            dash = AnalyticsService.get_all_dashboards(user)
            return {
                "report": "Operational Overview Brief",
                "facilities_monitored": len(dash.people_in_custody),
                "urgent_legal_aid_count": dash.legal_aid_attention.total_attention_required,
                "approaching_thresholds_count": dash.approaching_thresholds.total_flagged,
                "overdue_actions_count": dash.overdue_actions.total_overdue,
                "missing_documents_cases": dash.missing_documents.dockets_incomplete_count,
                "system_uptime_pct": dash.integration_health.overall_uptime_pct,
                "secure_link": "/reports?tab=operational",
            }

