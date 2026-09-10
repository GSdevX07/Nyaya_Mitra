"""
document_templates.py - Versioned Legal Document Templates Engine for Nyaya Mitra.
===================================================================================
Manages organization-aware, versioned document templates authorized for legal aid
assistance. Enforces role-based maintenance (PLATFORM_ADMIN, GOV_ADMIN, SUPERVISING_LEGAL_OFFICER).
"""

from __future__ import annotations
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from app.auth.roles import Role
from app.database import (
    store_document_template,
    get_document_templates,
    get_document_template_by_id,
)

logger = logging.getLogger(__name__)

# Roles authorized to create or edit organization templates
TEMPLATE_MAINTAINER_ROLES = {
    Role.GOV_ADMIN,
    Role.SUPERVISING_LEGAL_OFFICER,
}

PLACEHOLDER_REGEX = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")


def can_maintain_templates(role: Role) -> bool:
    """Check if the user's authenticated role is permitted to author or modify templates."""
    return role in TEMPLATE_MAINTAINER_ROLES


def extract_template_placeholders(template_str: str) -> List[str]:
    """Extract all placeholder variable names found in a template string."""
    return sorted(list(set(PLACEHOLDER_REGEX.findall(template_str))))


def render_template(template_str: str, context: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Render a document template using key-value fact substitution.
    Returns: (rendered_text, missing_fields)
    Missing fields are marked with [MISSING: field_name] in the text.
    """
    missing_fields: List[str] = []
    
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        val = context.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing_fields.append(key)
            return f"[MISSING: {key.upper()}]"
        if isinstance(val, list):
            return ", ".join(str(item) for item in val)
        return str(val)

    rendered = PLACEHOLDER_REGEX.sub(replacer, template_str)
    return rendered, missing_fields


# ── Canonical Default Templates ──────────────────────────────────────────────

DEFAULT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "tmpl_bnss_479_bail_v1",
        "organization_id": "GLOBAL_DEFAULT",
        "name": "Formal Bail Application under Section 479 BNSS, 2023",
        "doc_type": "BAIL_APPLICATION",
        "version": 1,
        "jurisdiction": "National / Bharatiya Nagarik Suraksha Sanhita, 2023",
        "statutory_ground": "Section 479 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (Read with Article 21 of the Constitution of India)",
        "description": "Standard institutional petition format for undertrial prisoners satisfying statutory detention thresholds under BNSS Section 479.",
        "required_fields": [
            "court_name",
            "district",
            "fir_number",
            "police_station",
            "offense_sections",
            "accused_name",
            "custody_days",
            "max_sentence_days_for_offense",
            "statutory_threshold_fraction",
            "threshold_days",
            "assigned_lawyer",
        ],
        "required_documents": [
            "remand_order",
            "charge_sheet",
            "custody_certificate",
        ],
        "content_template": """IN THE COURT OF {{court_name}}
AT {{district}}

BAIL APPLICATION NO. ______ OF {{filing_year}}
IN THE MATTER OF:
CASE / FIR NO: {{fir_number}}
POLICE STATION: {{police_station}}
UNDER SECTION(S): {{offense_sections}}

IN THE MATTER OF:
{{accused_name}}
...APPLICANT / ACCUSED

VERSUS

STATE (GOVT. OF NCT OF DELHI / STATE PROSECUTION)
...RESPONDENT / PROSECUTION

APPLICATION UNDER SECTION 479 OF THE BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS), 2023
(READ WITH ARTICLE 21 OF THE CONSTITUTION OF INDIA) FOR GRANT OF STATUTORY MANDATORY BAIL

MOST RESPECTFULLY SHOWETH:

1. That the Applicant / Accused above named has been in continuous judicial incarceration since {{arrest_date}}, having undergone {{custody_days}} days of actual detention in {{jail_location}}.

2. That the maximum prescribed term of imprisonment for the alleged offense(s) ({{offense_sections}}) is {{max_sentence_days_for_offense}} days. The Applicant has completed {{custody_days}} days, exceeding the statutory threshold of {{threshold_days}} days (representing {{statutory_threshold_fraction}} of the maximum imprisonment term).

3. STATUTORY MANDATE UNDER SECTION 479 BNSS, 2023:
   Section 479(1) of the Bharatiya Nagarik Suraksha Sanhita, 2023 establishes a non-derogable right to bail for undertrial prisoners who have completed the requisite statutory detention:
   "Where a person has, during the period of investigation, inquiry or trial under this Sanhita of an offence under any law undergone detention for a period extending up to one-half (or one-third in the case of a first-time offender) of the maximum period of imprisonment specified for that offence, he shall be released by the Court on bail."
   The Applicant satisfies all conditions:
   (a) The offenses charged do not carry capital punishment or imprisonment for life.
   (b) Delay in trial is not attributable to the Applicant.
   (c) The Applicant has deep societal ties, is indigent, and does not pose any flight risk.

4. That verified custodial and court records (including Remand Orders and Custody Certificate) substantiate that the detention period is continuous and lawful. Solvent local sureties are prepared to furnish bond.

PRAYER:
In view of the statutory mandate, it is most respectfully prayed that this Hon'ble Court may be pleased to:
(a) Admit the Applicant / Accused ({{accused_name}}) to statutory bail under Section 479 BNSS on reasonable and non-oppressive terms;
(b) Pass such further order(s) as this Hon'ble Court deems fit and proper in the interest of justice.

FILED BY:
ADV. {{assigned_lawyer}}
COUNSEL FOR THE APPLICANT / LEGAL AID DEFENSE COUNSEL
DATE: {{current_date}}
PLACE: {{district}}
""",
    },
    {
        "id": "tmpl_remand_objection_v1",
        "organization_id": "GLOBAL_DEFAULT",
        "name": "Objection to Police Custody Remand Application",
        "doc_type": "REMAND_OBJECTION",
        "version": 1,
        "jurisdiction": "District & Sessions Courts / Magistracy",
        "statutory_ground": "Section 187 of the Bharatiya Nagarik Suraksha Sanhita, 2023",
        "description": "Formal defense objection against police custody remand extension where custodial interrogation is unnecessary.",
        "required_fields": [
            "court_name",
            "district",
            "fir_number",
            "police_station",
            "offense_sections",
            "accused_name",
            "arrest_date",
            "assigned_lawyer",
        ],
        "required_documents": [
            "remand_order",
        ],
        "content_template": """IN THE COURT OF THE LEARNED JUDICIAL MAGISTRATE
AT {{district}}

IN RE:
FIR NO: {{fir_number}}
POLICE STATION: {{police_station}}
UNDER SECTION(S): {{offense_sections}}

STATE
...PROSECUTION

VERSUS

{{accused_name}}
...ACCUSED / OBJECTOR

OBJECTIONS ON BEHALF OF THE ACCUSED TO POLICE APPLICATION FOR EXTENSION OF CUSTODIAL REMAND UNDER SECTION 187 BNSS, 2023

MOST RESPECTFULLY SHOWETH:

1. That the Accused was taken into custody on {{arrest_date}} and has cooperated fully with the investigating agency throughout the statutory period.

2. That the Investigating Agency has failed to establish any specific recovery or genuine discovery ground justifying continued police custody. Mechanical remand infringes the personal liberty guaranteed under Article 21.

3. That all alleged recoveries have already been completed or are matter of documented record. No fresh custodial interrogation is warranted.

PRAYER:
It is therefore respectfully prayed that the application for police custody remand be rejected and the Accused be remanded to judicial custody, with leave to apply for regular bail.

FILED BY:
ADV. {{assigned_lawyer}}
COUNSEL FOR THE ACCUSED
DATE: {{current_date}}
""",
    },
    {
        "id": "tmpl_custody_cert_affidavit_v1",
        "organization_id": "GLOBAL_DEFAULT",
        "name": "Undertrial Verification Affidavit & Custody Grounding",
        "doc_type": "AFFIDAVIT",
        "version": 1,
        "jurisdiction": "Competent Court / Jail Authority",
        "statutory_ground": "Verification Affidavit under High Court Rules & BNSS Section 479",
        "description": "Affidavit verifying undertrial custody duration, nominal roll verification, and solvency of proposed local sureties.",
        "required_fields": [
            "court_name",
            "district",
            "accused_name",
            "case_id",
            "jail_location",
            "custody_days",
            "parent_or_guardian_name",
        ],
        "required_documents": [
            "custody_certificate",
        ],
        "content_template": """IN THE COURT OF {{court_name}}
AT {{district}}

IN THE MATTER OF:
STATE VERSUS {{accused_name}}
CASE ID: {{case_id}}
JAIL ADMISSION: {{jail_location}}

AFFIDAVIT OF UNDERTAKING AND CUSTODIAL DURATION VERIFICATION

I, {{accused_name}} (or on behalf, through relative {{parent_or_guardian_name}}), do hereby solemnly affirm and state on oath as under:

1. That I am the Applicant / Accused in the aforementioned case and am fully conversant with the facts and circumstances thereof.

2. That the official Custody Certificate issued by the Superintendent of {{jail_location}} confirms that I have undergone {{custody_days}} days of actual judicial custody without adverse prison infractions.

3. That I have not been convicted of any prior offense and am entitled to the benefit of Section 479 BNSS as a first-time undertrial.

4. That I undertake to appear on each and every date of hearing and shall not tamper with evidence or influence witnesses.

DEPONENT

VERIFICATION:
Verified at {{district}} on this {{current_date}} that the contents of the above affidavit are true and correct to the best of my knowledge and official record.

DEPONENT
""",
    },
]


def seed_default_templates() -> int:
    """Seed default templates into database if not already present."""
    seeded = 0
    for tmpl in DEFAULT_TEMPLATES:
        existing = get_document_template_by_id(tmpl["id"])
        if not existing:
            success = store_document_template(tmpl)
            if success:
                seeded += 1
    logger.info(f"Document templates engine: seeded {seeded} default templates.")
    return seeded
