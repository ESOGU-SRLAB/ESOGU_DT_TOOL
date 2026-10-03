"""Environment-backed application settings.

This module is deliberately dependency-light so legacy modules can import it
without changing the application's existing Pydantic version constraints.
"""

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


load_dotenv()


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _as_list(name: str, default: str = "") -> List[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    log_level: str
    app_reload: bool
    initialize_prompts_on_startup: bool
    mongo_uri: str
    database_name: str
    model_api_base_url: str
    model_identifier: str
    model_api_key: Optional[str]
    cors_origins: List[str]
    api_auth_enabled: bool
    app_api_key: Optional[str]
    artifact_dir: Path
    execution_service_url: Optional[str]
    execution_service_token: Optional[str]
    execution_timeout_seconds: int
    execution_adapter: str
    ssh_execution_host: Optional[str]
    ssh_execution_remote_dir: str
    ssh_execution_image: str
    ssh_execution_identity_file: Optional[Path]
    ssh_execution_password: Optional[str]
    ssh_execution_connect_timeout_seconds: int
    monitoring_enabled: bool
    monitoring_event_retention_days: int

    @classmethod
    def from_env(cls) -> "Settings":
        auth_enabled = _as_bool("API_AUTH_ENABLED", False)
        api_key = os.getenv("APP_API_KEY") or None
        if auth_enabled and not api_key:
            raise ValueError("APP_API_KEY is required when API_AUTH_ENABLED=true")

        origins = _as_list(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,"
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:5175,http://127.0.0.1:5175",
        )
        if "*" in origins and auth_enabled:
            raise ValueError(
                "Wildcard CORS is not allowed while API authentication is enabled"
            )

        return cls(
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            app_port=_as_int("APP_PORT", 8100),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            app_reload=_as_bool("APP_RELOAD", False),
            initialize_prompts_on_startup=_as_bool("INITIALIZE_PROMPTS_ON_STARTUP", True),
            mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
            database_name=os.getenv("DATABASE_NAME", "stlc_database"),
            model_api_base_url=os.getenv("MODEL_API_BASE_URL", "http://localhost:1234"),
            model_identifier=os.getenv("MODEL_IDENTIFIER", "llama-3.2-3b-instruct"),
            model_api_key=os.getenv("MODEL_API_KEY") or None,
            cors_origins=origins,
            api_auth_enabled=auth_enabled,
            app_api_key=api_key,
            artifact_dir=Path(os.getenv("ARTIFACT_DIR", "artifacts")),
            execution_service_url=os.getenv("EXECUTION_SERVICE_URL") or None,
            execution_service_token=os.getenv("EXECUTION_SERVICE_TOKEN") or None,
            execution_timeout_seconds=_as_int("EXECUTION_TIMEOUT_SECONDS", 1900),
            execution_adapter=os.getenv("EXECUTION_ADAPTER", "http").strip().lower(),
            ssh_execution_host=os.getenv("SSH_EXECUTION_HOST") or None,
            ssh_execution_remote_dir=os.getenv("SSH_EXECUTION_REMOTE_DIR", "~/stlc_runs"),
            ssh_execution_image=os.getenv("SSH_EXECUTION_IMAGE", "ros2-exec-harness:0.3.2"),
            ssh_execution_identity_file=(
                Path(os.environ["SSH_EXECUTION_IDENTITY_FILE"])
                if os.getenv("SSH_EXECUTION_IDENTITY_FILE")
                else None
            ),
            ssh_execution_password=os.getenv("SSH_EXECUTION_PASSWORD") or None,
            ssh_execution_connect_timeout_seconds=_as_int(
                "SSH_EXECUTION_CONNECT_TIMEOUT_SECONDS", 10
            ),
            monitoring_enabled=_as_bool("MONITORING_ENABLED", True),
            monitoring_event_retention_days=_as_int("MONITORING_EVENT_RETENTION_DAYS", 30),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def reset_settings_cache() -> None:
    """Test/support hook for reloading environment-backed settings."""
    get_settings.cache_clear()
