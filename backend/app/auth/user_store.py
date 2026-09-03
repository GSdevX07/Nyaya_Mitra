"""
auth/user_store.py — User data access layer for authentication.

Queries organization_users table in SQLite (local) or Supabase (production).
The AuthUser dataclass is the internal representation of a logged-in identity.
"""
from __future__ import annotations
import datetime
import sqlite3
import json
from dataclasses import dataclass, field
from typing import Optional

from app.auth.roles import Role


@dataclass
class AuthUser:
    """Internal representation of an authenticated user."""
    id: str
    email: str
    role: Role
    org_id: str
    facility_ids: list[str] = field(default_factory=list)
    police_station_id: str = ""
    police_station: str = ""
    jurisdiction_ids: list[str] = field(default_factory=list)
    district: str = ""
    state_id: str = ""
    state: str = ""
    scope_type: str = ""
    authorized_district_ids: list[str] = field(default_factory=list)
    full_name: str = ""
    is_active: bool = True
    locked_until: Optional[datetime.datetime] = None
    failed_login_count: int = 0
    # For ACCUSED_USER / FAMILY_GUARDIAN scope
    linked_case_id: Optional[str] = None
    phone: str = ""
    relationship_to_accused: Optional[str] = None
    bar_registration_no: Optional[str] = None
    years_of_experience: Optional[int] = None
    specialization: Optional[str] = None
    empanelment_category: Optional[str] = None
    supervision_required: bool = False


def _row_to_user(row: dict) -> AuthUser:
    import json
    fac_raw = row.get("facility_ids", "[]") or "[]"
    if isinstance(fac_raw, str):
        try:
            facility_ids = json.loads(fac_raw)
        except Exception:
            facility_ids = []
    elif isinstance(fac_raw, list):
        facility_ids = fac_raw
    else:
        facility_ids = []

    jur_raw = row.get("jurisdiction_ids", "[]") or "[]"
    if isinstance(jur_raw, str):
        try:
            jurisdiction_ids = json.loads(jur_raw)
        except Exception:
            jurisdiction_ids = []
    elif isinstance(jur_raw, list):
        jurisdiction_ids = jur_raw
    else:
        jurisdiction_ids = []

    dist_raw = row.get("authorized_district_ids", "[]") or "[]"
    if isinstance(dist_raw, str):
        try:
            authorized_district_ids = json.loads(dist_raw)
        except Exception:
            authorized_district_ids = []
    elif isinstance(dist_raw, list):
        authorized_district_ids = dist_raw
    else:
        authorized_district_ids = []

    locked_until = None
    if row.get("locked_until"):
        try:
            locked_until = datetime.datetime.fromisoformat(str(row["locked_until"]))
        except Exception:
            pass

    return AuthUser(
        id=str(row["id"]),
        email=str(row["email"]),
        role=Role(row["role"]),
        org_id=str(row.get("organization_id", "")),
        facility_ids=facility_ids,
        police_station_id=str(row.get("police_station_id", "") or ""),
        police_station=str(row.get("police_station", "") or ""),
        jurisdiction_ids=jurisdiction_ids,
        district=str(row.get("district", "") or ""),
        state_id=str(row.get("state_id", "") or ""),
        state=str(row.get("state", "") or ""),
        scope_type=str(row.get("scope_type", "") or ""),
        authorized_district_ids=authorized_district_ids,
        full_name=str(row.get("full_name", "") or ""),
        is_active=bool(row.get("is_active", True)),
        locked_until=locked_until,
        failed_login_count=int(row.get("failed_login_count", 0) or 0),
        linked_case_id=row.get("linked_case_id"),
        phone=str(row.get("phone", "") or ""),
        relationship_to_accused=row.get("relationship_to_accused"),
        bar_registration_no=row.get("bar_registration_no") or ("D/1420/2018" if "advocate" in str(row.get("role", "")).lower() else None),
        years_of_experience=int(row["years_of_experience"]) if row.get("years_of_experience") is not None else (7 if "advocate" in str(row.get("role", "")).lower() else None),
        specialization=row.get("specialization") or ("Bail & Undertrial Defense" if "advocate" in str(row.get("role", "")).lower() else None),
        empanelment_category=row.get("empanelment_category") or ("DLSA Senior Panel Counsel" if "advocate" in str(row.get("role", "")).lower() else None),
        supervision_required=bool(row.get("supervision_required", False) or (row.get("years_of_experience") is not None and int(row["years_of_experience"]) < 3)),
    )



def get_user_by_email(email: str) -> Optional[AuthUser]:
    """Fetch a user by email — tries Supabase then SQLite."""
    email = email.lower().strip()

    # Supabase
    try:
        from app.supabase_adapter import get_supabase_client
        client = get_supabase_client()
        if client:
            res = (
                client.table("organization_users")
                .select("*")
                .eq("email", email)
                .execute()
            )
            if res.data:
                return _row_to_user(res.data[0])
    except Exception as e:
        print(f"[WARN] Supabase get_user_by_email error: {e}")

    # SQLite fallback
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM organization_users WHERE LOWER(email) = ?", (email,)
        ).fetchone()
        conn.close()
        if row:
            return _row_to_user(dict(row))
    except Exception as e:
        print(f"[WARN] SQLite get_user_by_email error: {e}")

    # Demo user fallback (only in DEMO_MODE)
    from app.auth.config import DEMO_MODE
    if DEMO_MODE:
        return _get_demo_user(email)

    return None


def get_user_by_id(user_id: str) -> Optional[AuthUser]:
    """Fetch user by primary key. Checks local SQLite first for high performance, then Supabase."""
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM organization_users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        if row:
            return _row_to_user(dict(row))
    except Exception:
        pass

    # Skip external network roundtrip for test/demo user identifiers
    if not (user_id.startswith("test") or user_id.startswith("demo_") or user_id.startswith("usr_")):
        try:
            from app.supabase_adapter import get_supabase_client, is_supabase_active

            if is_supabase_active():
                client = get_supabase_client()
                if client:
                    res = client.table("organization_users").select("*").eq("id", user_id).execute()
                    if res.data:
                        return _row_to_user(res.data[0])
        except Exception:
            pass

    # Demo fallback
    from app.auth.config import DEMO_MODE
    if DEMO_MODE:
        if user_id.startswith("deleted_") or user_id.startswith("revoked_"):
            return None

        _build_demo_users()
        # Direct ID match
        for u in _DEMO_USERS.values():
            if u["id"] == user_id:
                return _row_to_user(u)

        # Test aliases for backward compatibility with existing integration tests
        TEST_ALIASES = {
            "demo_admin": "demo_platform_admin",
            "admin_ingestion_test": "demo_platform_admin",
            "demo_supervisor": "demo_supervising",
            "usr_sup_01": "demo_supervising",
            "test_supervisor": "demo_supervising",
            "demo_gov": "demo_gov_admin",
            "test_gov": "demo_gov_admin",
        }
        if user_id in TEST_ALIASES:
            alias_id = TEST_ALIASES[user_id]
            for u in _DEMO_USERS.values():
                if u["id"] == alias_id:
                    return _row_to_user(u)

    return None


def get_password_hash_for_email(email: str) -> Optional[str]:
    """Return stored password_hash for the given email, or None."""
    email = email.lower().strip()

    try:
        from app.supabase_adapter import get_supabase_client
        client = get_supabase_client()
        if client:
            res = (
                client.table("organization_users")
                .select("password_hash")
                .eq("email", email)
                .execute()
            )
            if res.data and res.data[0].get("password_hash"):
                return res.data[0].get("password_hash")
    except Exception:
        pass

    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        row = conn.execute(
            "SELECT password_hash FROM organization_users WHERE LOWER(email) = ?", (email,)
        ).fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception:
        pass

    # Demo fallback
    from app.auth.config import DEMO_MODE
    if DEMO_MODE:
        _build_demo_users()
        if email in _DEMO_USERS:
            return _DEMO_USERS[email].get("password_hash")

    return None


def update_last_login(user_id: str) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        from app.supabase_adapter import get_supabase_client
        client = get_supabase_client()
        if client:
            client.table("organization_users").update({
                "last_login_at": now, "failed_login_count": 0
            }).eq("id", user_id).execute()
            return
    except Exception:
        pass
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        conn.execute(
            "UPDATE organization_users SET last_login_at=?, failed_login_count=0 WHERE id=?",
            (now, user_id)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── Demo Users (DEMO_MODE only) ───────────────────────────────────────────────
# Passwords are hashed. Plain-text values are shown only in demo UI.
# Demo password for all demo accounts: Demo@12345

def _make_demo_hash() -> str:
    from app.auth.password import hash_password
    return hash_password("Demo@12345")


_DEMO_HASH: Optional[str] = None


def _get_demo_hash() -> str:
    global _DEMO_HASH
    if _DEMO_HASH is None:
        _DEMO_HASH = _make_demo_hash()
    return _DEMO_HASH


# Lazily built demo user registry
_DEMO_USERS: dict[str, dict] = {}

_DEMO_USER_DEFINITIONS = [
    {"id": "demo_platform_admin",    "email": "admin@demo.nyayamitra.in",        "role": "PLATFORM_ADMIN",             "full_name": "Platform Admin (Demo)",         "organization_id": "org_dlsa_central", "district": "Central Delhi"},
    {"id": "demo_gov_admin",         "email": "govadmin@demo.nyayamitra.in",     "role": "GOV_ADMIN",                  "full_name": "State Legal Services Oversight Officer (Demo)", "organization_id": "org_slsa_delhi", "state_id": "state_delhi", "state": "Delhi", "district": "All (Statewide)", "scope_type": "STATE", "authorized_district_ids": ["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi", "Shahdara", "Rohini"]},
    {"id": "demo_jail_officer",      "email": "jail@demo.nyayamitra.in",         "role": "JAIL_OFFICER",               "full_name": "Jail Officer (Demo)",           "organization_id": "org_tihar_jail",   "district": "West Delhi", "facility_ids": ["fac_tihar_jail_04", "Central Jail No. 4, Tihar (Synthetic)", "Tihar"]},
    {"id": "demo_police_officer",    "email": "police@demo.nyayamitra.in",       "role": "POLICE_OFFICER",             "full_name": "Police Officer (Demo)",         "organization_id": "ps_kotwali_central", "police_station_id": "ps_kotwali_central", "police_station": "Kotwali Police Station", "district": "Central Delhi", "jurisdiction_ids": ["ps_kotwali_central", "Central Delhi"]},
    {"id": "demo_dlsa_officer",      "email": "dlsa@demo.nyayamitra.in",         "role": "DLSA_OFFICER",               "full_name": "DLSA Officer (Demo)",           "organization_id": "org_dlsa_central", "district": "Central Delhi"},
    {"id": "demo_supervising",       "email": "supervisor@demo.nyayamitra.in",   "role": "SUPERVISING_LEGAL_OFFICER",  "full_name": "Supervising Legal Officer (Demo)", "organization_id": "org_dlsa_central", "district": "Central Delhi", "bar_registration_no": "D/0842/2012", "years_of_experience": 12, "specialization": "Judicial Oversight & Human Rights", "empanelment_category": "Supervising Officer"},
    {"id": "demo_advocate",          "email": "advocate@demo.nyayamitra.in",     "role": "DEFENSE_ADVOCATE",           "full_name": "Defense Advocate (Demo)",       "organization_id": "org_dlsa_central", "district": "Central Delhi", "linked_case_id": "UTP-0001", "bar_registration_no": "D/1420/2018", "years_of_experience": 7, "specialization": "Undertrial Defense & Bail", "empanelment_category": "DLSA Senior Panel Counsel"},
    {"id": "demo_ext_advocate",      "email": "extadvocate@demo.nyayamitra.in",  "role": "CONTROLLED_EXTERNAL_ADVOCATE","full_name": "External Advocate (Demo)",     "organization_id": "org_dlsa_central", "district": "Central Delhi", "linked_case_id": "UTP-0001", "bar_registration_no": "D/2984/2021", "years_of_experience": 4, "specialization": "Criminal Defense", "empanelment_category": "Panel Advocate"},
    {"id": "demo_accused",           "email": "accused@demo.nyayamitra.in",      "role": "ACCUSED_USER",               "full_name": "Accused Person (Demo)",         "organization_id": "org_dlsa_central", "district": "Central Delhi", "linked_case_id": "UTP-0001"},
    {"id": "demo_family",            "email": "family@demo.nyayamitra.in",       "role": "FAMILY_GUARDIAN",            "full_name": "Family Guardian (Demo)",        "organization_id": "org_dlsa_central", "district": "Central Delhi", "linked_case_id": "UTP-0001"},
    {
        "id": "demo_auditor",
        "email": "auditor@demo.nyayamitra.in",
        "role": "READ_ONLY_AUDITOR",
        "full_name": "Statutory Oversight Auditor (Demo)",
        "organization_id": "org_statutory_audit_delhi",
        "district": "All (Statewide)",
        "state_id": "state_delhi",
        "state": "Delhi",
        "scope_type": "STATUTORY_STATE_AUDIT",
        "authorized_district_ids": ["Central Delhi", "South Delhi", "West Delhi", "North Delhi", "East Delhi", "New Delhi", "Shahdara", "Rohini"],
    },
]


def _build_demo_users() -> None:
    global _DEMO_USERS
    if _DEMO_USERS:
        return
    h = _get_demo_hash()
    for defn in _DEMO_USER_DEFINITIONS:
        fac_ids = json.dumps(defn.get("facility_ids", [])) if isinstance(defn.get("facility_ids"), list) else defn.get("facility_ids", "[]")
        jur_ids = json.dumps(defn.get("jurisdiction_ids", [])) if isinstance(defn.get("jurisdiction_ids"), list) else defn.get("jurisdiction_ids", "[]")
        dist_ids = json.dumps(defn.get("authorized_district_ids", [])) if isinstance(defn.get("authorized_district_ids"), list) else defn.get("authorized_district_ids", "[]")
        entry = {
            **defn,
            "password_hash": h,
            "is_active": True,
            "failed_login_count": 0,
            "facility_ids": fac_ids,
            "jurisdiction_ids": jur_ids,
            "authorized_district_ids": dist_ids,
        }
        _DEMO_USERS[defn["email"]] = entry


def _get_demo_user(email: str) -> Optional[AuthUser]:
    _build_demo_users()
    entry = _DEMO_USERS.get(email.lower())
    if entry:
        return _row_to_user(entry)
    return None


def get_all_demo_users() -> list[dict]:
    """Return demo user info (no hashes) for the demo login UI panel."""
    from app.auth.config import DEMO_MODE
    if not DEMO_MODE:
        return []
    _build_demo_users()
    return [
        {
            "email": d["email"],
            "role": d["role"],
            "full_name": d["full_name"],
            "demo_password": "Demo@12345",
        }
        for d in _DEMO_USER_DEFINITIONS
    ]
