"""
auth/config.py — Auth configuration loaded from environment variables.
"""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

# Environment settings
APP_ENV: str = os.environ.get("APP_ENV", "development").lower()

# JWT settings
JWT_SECRET: str = os.environ.get("JWT_SECRET", "CHANGE_ME_in_production_min_32_chars_random")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TTL_MINUTES: int = int(os.environ.get("JWT_ACCESS_TTL_MINUTES", "60"))
JWT_REFRESH_TTL_DAYS: int = int(os.environ.get("JWT_REFRESH_TTL_DAYS", "7"))

# Demo mode — defaults to False in production; in non-production, follows DEMO_MODE env var (defaults to true)
if APP_ENV == "production":
    DEMO_MODE: bool = os.environ.get("DEMO_MODE", "false").lower() == "true"
else:
    DEMO_MODE: bool = os.environ.get("DEMO_MODE", "true").lower() == "true"


def validate_security_config() -> None:
    """
    Startup security assertion: Ensures production deployment fails immediately
    if JWT_SECRET uses an insecure fallback or DEMO_MODE is accidentally enabled.
    """
    env = os.environ.get("APP_ENV", "development").lower()
    if env == "production":
        secret = os.environ.get("JWT_SECRET", "")
        if not secret or secret == "CHANGE_ME_in_production_min_32_chars_random" or len(secret) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: Application refused to boot in production mode "
                "with default, missing, or insecure JWT_SECRET. Set a cryptographically random secret (>=32 chars)."
            )
        if os.environ.get("DEMO_MODE", "false").lower() == "true":
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: DEMO_MODE cannot be enabled in a production deployment."
            )


# Run startup validation check
validate_security_config()

# CORS — comma-separated list of allowed frontend origins
ALLOWED_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://localhost:4173"
    ).split(",")
    if o.strip()
]

# Brute-force thresholds
MAX_FAILED_ATTEMPTS_BEFORE_DELAY: int = 5
MAX_FAILED_ATTEMPTS_BEFORE_LOCKOUT: int = 10
LOCKOUT_DURATION_MINUTES: int = 15
