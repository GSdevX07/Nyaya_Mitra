"""
security/secrets.py — Production Secret Manager Integration & Credential Governance.
===================================================================================
Provides an abstraction layer for loading platform credentials:
- EnvironmentSecretManager: For local development and test automation.
- CloudVaultSecretManager: Enterprise pluggable interface for AWS Secrets Manager,
  Azure Key Vault, GCP Secret Manager, or HashiCorp Vault.
- Production Security Guard: Refuses boot in production mode if plaintext default
  secrets are detected.
"""

from __future__ import annotations
import os
import abc
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("nyaya_mitra.security.secrets")


class BaseSecretManager(abc.ABC):
    """Abstract interface for enterprise secret managers."""

    @abc.abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret by name."""
        pass

    def validate_production_readiness(self) -> tuple[bool, list[str]]:
        """Validate if all mandatory production secrets are provisioned."""
        required = ["JWT_SECRET", "DB_PASSWORD", "SUPABASE_SERVICE_ROLE_KEY"]
        missing = []
        for k in required:
            val = self.get_secret(k)
            if not val or "CHANGE_ME" in val or "your_" in val:
                missing.append(k)
        return (len(missing) == 0, missing)


SecretManager = BaseSecretManager



class EnvironmentSecretManager(BaseSecretManager):
    """Loads credentials from OS environment / local .env file."""

    def __init__(self):
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)


class CloudVaultSecretManager(BaseSecretManager):
    """
    Pluggable production secret manager supporting AWS Secrets Manager,
    Azure Key Vault, Google Secret Manager, or HashiCorp Vault.
    Falls back gracefully to secure environment variables if cloud client unavailable.
    """

    def __init__(self, provider: str = "environment"):
        self.provider = provider.lower()
        self._cached_secrets: Dict[str, str] = {}
        self._env_fallback = EnvironmentSecretManager()

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        if key in self._cached_secrets:
            return self._cached_secrets[key]

        val: Optional[str] = None

        if self.provider == "aws_secrets_manager":
            val = self._fetch_from_aws(key)
        elif self.provider == "azure_key_vault":
            val = self._fetch_from_azure(key)
        elif self.provider == "gcp_secret_manager":
            val = self._fetch_from_gcp(key)
        elif self.provider == "hashicorp_vault":
            val = self._fetch_from_vault(key)

        if not val:
            val = self._env_fallback.get_secret(key, default)

        if val is not None:
            self._cached_secrets[key] = val
        return val

    def _fetch_from_aws(self, key: str) -> Optional[str]:
        try:
            import boto3
            client = boto3.client("secretsmanager")
            res = client.get_secret_value(SecretId=f"nyaya-mitra/{key}")
            return res.get("SecretString")
        except Exception:
            return None

    def _fetch_from_azure(self, key: str) -> Optional[str]:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            vault_url = os.environ.get("AZURE_VAULT_URL", "")
            if not vault_url:
                return None
            client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
            return client.get_secret(key).value
        except Exception:
            return None

    def _fetch_from_gcp(self, key: str) -> Optional[str]:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.environ.get("GCP_PROJECT_ID", "")
            if not project_id:
                return None
            name = f"projects/{project_id}/secrets/{key}/versions/latest"
            res = client.access_secret_version(request={"name": name})
            return res.payload.data.decode("UTF-8")
        except Exception:
            return None

    def _fetch_from_vault(self, key: str) -> Optional[str]:
        try:
            import hvac
            vault_addr = os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
            vault_token = os.environ.get("VAULT_TOKEN", "")
            client = hvac.Client(url=vault_addr, token=vault_token)
            read_res = client.secrets.kv.read_secret_version(path=f"nyaya_mitra/{key}")
            return read_res["data"]["data"].get("value")
        except Exception:
            return None


# Global Secret Manager instance based on configuration
_vault_provider = os.environ.get("SECRET_MANAGER_PROVIDER", "environment").lower()
_secret_manager: BaseSecretManager = (
    CloudVaultSecretManager(provider=_vault_provider)
    if _vault_provider != "environment"
    else EnvironmentSecretManager()
)


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve secret from active manager."""
    return _secret_manager.get_secret(key, default)


def get_secret_manager() -> BaseSecretManager:
    """Return singleton secret manager instance."""
    return _secret_manager



def validate_production_secrets() -> None:
    """
    Fail-closed startup verification: Ensures system will not boot in production
    if using default or insecure credentials.
    """
    env = (os.environ.get("APP_ENV") or "development").lower()
    if env == "production":
        secret = get_secret("JWT_SECRET")
        if not secret or "CHANGE_ME" in secret or len(secret) < 32:
            raise RuntimeError(
                "PRODUCTION SECURITY ABORT: Application refused to boot with missing, "
                "insecure, or default JWT_SECRET. Configure an external secret manager or vault."
            )
        db_pwd = get_secret("DB_PASSWORD")
        if not db_pwd or db_pwd in ("your_db_password_here", "postgres", "password"):
            raise RuntimeError(
                "PRODUCTION SECURITY ABORT: Insecure or default DB_PASSWORD in production environment."
            )
