"""
auth/password.py — Password hashing and validation using native bcrypt.
"""
from __future__ import annotations
import re
import bcrypt


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of plain password."""
    # Ensure plain text is encoded and truncated to bcrypt's 72 byte limit safely if needed
    plain_bytes = plain.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored hashed password."""
    try:
        plain_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def validate_password_strength(plain: str) -> list[str]:
    """
    Validate password strength. Returns a list of failure reasons
    (empty list means the password is acceptable).
    """
    errors: list[str] = []
    if len(plain) < 10:
        errors.append("Password must be at least 10 characters.")
    if not re.search(r"[A-Z]", plain):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", plain):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", plain):
        errors.append("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", plain):
        errors.append("Password must contain at least one special character.")
    return errors
