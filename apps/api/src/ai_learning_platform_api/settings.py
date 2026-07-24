"""Validated process and product configuration boundary."""

from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
PersistenceMode = Literal["signed_state", "postgres"]

_DEVELOPMENT_STATE_SECRET = "development-only-learner-state-secret-change-me"
_POSTGRESQL_URL_PREFIX = "postgresql+psycopg://"


class Settings(BaseSettings):
    """Validated runtime configuration with fail-closed production boundaries."""

    model_config = SettingsConfigDict(env_prefix="AI_PLATFORM_", extra="ignore")

    environment: Environment = "development"
    log_level: LogLevel = "INFO"
    learner_state_secret: SecretStr = SecretStr(_DEVELOPMENT_STATE_SECRET)
    persistence_mode: PersistenceMode = "signed_state"
    database_url: SecretStr | None = None

    @model_validator(mode="after")
    def require_runtime_secrets(self) -> Self:
        """Reject unsafe signing and PostgreSQL configuration."""
        secret = self.learner_state_secret.get_secret_value()
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("learner_state_secret must contain at least 32 UTF-8 bytes")
        if self.environment == "production" and secret == _DEVELOPMENT_STATE_SECRET:
            raise ValueError("production learner_state_secret must be configured")

        if self.persistence_mode == "postgres":
            if self.database_url is None:
                raise ValueError("database_url must be configured for postgres persistence")
            database_url = self.database_url.get_secret_value().strip()
            if not database_url:
                raise ValueError("database_url must be configured for postgres persistence")
            if not database_url.startswith(_POSTGRESQL_URL_PREFIX):
                raise ValueError("database_url must use the postgresql+psycopg driver")

        return self
