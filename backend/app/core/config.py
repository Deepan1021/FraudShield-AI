"""Environment-based configuration. No secrets are stored in source."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.core.errors import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_VALID_ENVS = ("development", "production", "test")
_VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines). Real environment variables always win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    log_level: str
    api_host: str
    api_port: int
    cors_origins: List[str]
    max_request_bytes: int
    reports_dir: Path
    backups_dir: Path
    data_dir: Path
    logs_dir: Path
    frontend_dist: Path
    serve_frontend: bool
    auto_seed_demo: bool

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def public_dict(self) -> dict:
        """Safe-to-display configuration (no secrets exist, but paths are shown relative to the project)."""
        def rel(p: Path) -> str:
            try:
                return str(p.resolve().relative_to(PROJECT_ROOT))
            except ValueError:
                return p.name
        return {
            "APP_ENV": self.app_env, "DATABASE_URL": self.database_url, "LOG_LEVEL": self.log_level,
            "API_HOST": self.api_host, "API_PORT": self.api_port, "CORS_ORIGINS": self.cors_origins,
            "MAX_REQUEST_BYTES": self.max_request_bytes, "REPORTS_DIR": rel(self.reports_dir),
            "BACKUPS_DIR": rel(self.backups_dir), "DATA_DIR": rel(self.data_dir), "SERVE_FRONTEND": self.serve_frontend,
        }


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def load_settings() -> Settings:
    _load_dotenv(PROJECT_ROOT / ".env")
    _load_dotenv(PROJECT_ROOT / "backend" / ".env")
    env = os.environ.get("APP_ENV", "development").strip().lower()
    if env not in _VALID_ENVS:
        raise ConfigurationError(f"APP_ENV must be one of {_VALID_ENVS}, got '{env}'.", field="APP_ENV")
    level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    if level not in _VALID_LOG_LEVELS:
        raise ConfigurationError(f"LOG_LEVEL must be one of {_VALID_LOG_LEVELS}, got '{level}'.", field="LOG_LEVEL")
    try:
        port = int(os.environ.get("API_PORT", "8000"))
        max_bytes = int(os.environ.get("MAX_REQUEST_BYTES", str(1_000_000)))
    except ValueError as exc:
        raise ConfigurationError(f"API_PORT and MAX_REQUEST_BYTES must be integers: {exc}") from exc
    if not (1 <= port <= 65535):
        raise ConfigurationError("API_PORT must be between 1 and 65535.", field="API_PORT")
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
    if "*" in origins:
        raise ConfigurationError("CORS_ORIGINS must list explicit origins; '*' is not allowed.", field="CORS_ORIGINS")

    def path_env(name: str, default: str) -> Path:
        p = Path(os.environ.get(name, default))
        return p if p.is_absolute() else PROJECT_ROOT / p

    return Settings(
        app_env=env,
        database_url=os.environ.get("DATABASE_URL", "sqlite:///database/fraudshield.db"),
        log_level=level, api_host=os.environ.get("API_HOST", "127.0.0.1"), api_port=port,
        cors_origins=origins, max_request_bytes=max_bytes,
        reports_dir=path_env("REPORTS_DIR", "reports"), backups_dir=path_env("BACKUPS_DIR", "backups"),
        data_dir=path_env("DATA_DIR", "data"), logs_dir=path_env("LOGS_DIR", "logs"),
        frontend_dist=path_env("FRONTEND_DIST", "frontend/dist"),
        serve_frontend=_bool("SERVE_FRONTEND", True), auto_seed_demo=_bool("AUTO_SEED_DEMO", False),
    )
