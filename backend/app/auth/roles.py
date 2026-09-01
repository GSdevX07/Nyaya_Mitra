"""
auth/roles.py — Canonical role definitions for Nyaya Mitra.

Roles are arranged from highest privilege to lowest.
Each role maps to a string value stored in the JWT `role` claim.
"""
from __future__ import annotations
from enum import Enum


class Role(str, Enum):
    # ── Platform-level ────────────────────────────────────────────────────────
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    """Full system access across all organizations and districts."""

    # ── Organization-level authority ──────────────────────────────────────────
    GOV_ADMIN = "GOV_ADMIN"
    """Authority administrator within a single organization."""

    READ_ONLY_AUDITOR = "READ_ONLY_AUDITOR"
    """Reads audit log and case metadata; cannot write anything."""

    # ── Facility staff ────────────────────────────────────────────────────────
    JAIL_OFFICER = "JAIL_OFFICER"
    """Creates and updates custody records for their assigned facility."""

    POLICE_OFFICER = "POLICE_OFFICER"
    """Creates FIRs, reads accused records for their police station."""

    # ── DLSA / legal services authority ──────────────────────────────────────
    DLSA_OFFICER = "DLSA_OFFICER"
    """Manages legal-aid assignments and reviews cases in their district."""

    SUPERVISING_LEGAL_OFFICER = "SUPERVISING_LEGAL_OFFICER"
    """Approves submissions and reviews advocate work within their org."""

    # ── Legal aid advocates ───────────────────────────────────────────────────
    DEFENSE_ADVOCATE = "DEFENSE_ADVOCATE"
    """Acts on cases explicitly assigned to them."""

    CONTROLLED_EXTERNAL_ADVOCATE = "CONTROLLED_EXTERNAL_ADVOCATE"
    """Read-only access to case records explicitly shared with them."""

    # ── Service accounts ──────────────────────────────────────────────────────
    INTEGRATION_SERVICE = "INTEGRATION_SERVICE"
    """Machine-to-machine; scoped to specific declared integration endpoints."""

    # ── Citizen-facing ────────────────────────────────────────────────────────
    ACCUSED_USER = "ACCUSED_USER"
    """Reads their own case summary and next steps only."""

    FAMILY_GUARDIAN = "FAMILY_GUARDIAN"
    """Limited read view of a linked accused person's case."""


# Convenience groups for policy checks
STAFF_ROLES: set[Role] = {
    Role.PLATFORM_ADMIN,
    Role.GOV_ADMIN,
    Role.JAIL_OFFICER,
    Role.POLICE_OFFICER,
    Role.DLSA_OFFICER,
    Role.SUPERVISING_LEGAL_OFFICER,
    Role.DEFENSE_ADVOCATE,
    Role.CONTROLLED_EXTERNAL_ADVOCATE,
    Role.READ_ONLY_AUDITOR,
}

PRIVILEGED_ROLES: set[Role] = {
    Role.PLATFORM_ADMIN,
    Role.GOV_ADMIN,
    Role.SUPERVISING_LEGAL_OFFICER,
}

CITIZEN_ROLES: set[Role] = {Role.ACCUSED_USER, Role.FAMILY_GUARDIAN}

ALL_ROLES: set[Role] = set(Role)
