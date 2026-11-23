"""Configuración tipada (12-factor). Todo lo sensible viene de variables de entorno."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ONEHEAVY_", extra="ignore")

    env: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "1heavy API"
    public_app_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    log_json: bool = False

    # Base de datos
    database_url: str = "postgresql+asyncpg://oneheavy:oneheavy@localhost:5432/oneheavy"
    db_echo: bool = False
    db_auto_create: bool = True  # sólo local/test; en producción usar migraciones

    # Seguridad
    jwt_secret: SecretStr = SecretStr("change-me-in-env")
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 12
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )
    login_rate_limit: str = "5/minute"

    # Scheduler
    scheduler_enabled: bool = True
    scheduler_timezone: str = "America/Bogota"

    # Archivos
    storage_dir: str = "storage"
    max_upload_mb: int = 10

    # IA
    llm_provider: Literal["fake", "anthropic", "openai"] = "fake"
    anthropic_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("ONEHEAVY_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    )
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    tavily_api_key: SecretStr | None = None

    # WhatsApp (Evolution API — cada workspace conecta su número por QR)
    messaging_provider: Literal["console", "evolution"] = "console"
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: SecretStr | None = None

    # Mautic (marketing automation open source)
    mautic_enabled: bool = False
    mautic_base_url: str = "http://localhost:8081"
    mautic_username: str | None = None
    mautic_password: SecretStr | None = None
    mautic_webhook_secret: SecretStr | None = None

    # Meta Business (Graph API / Marketing API / Lead Ads)
    meta_enabled: bool = False
    meta_graph_version: str = "v21.0"
    meta_app_secret: SecretStr | None = None
    meta_verify_token: SecretStr | None = None
    meta_system_user_token: SecretStr | None = None

    # Pagos (Wompi)
    wompi_public_key: str | None = None
    wompi_integrity_secret: SecretStr | None = None
    wompi_events_secret: SecretStr | None = None

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.jwt_secret.get_secret_value() == "change-me-in-env":
        raise RuntimeError("ONEHEAVY_JWT_SECRET debe configurarse en producción")
    return settings
