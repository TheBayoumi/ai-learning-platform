"""Validated process and product configuration boundary."""

from typing import Literal, Self

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_DEVELOPMENT_STATE_SECRET = "development-only-learner-state-secret-change-me"


class Settings(BaseSettings):
    """Validated runtime configuration with a fail-closed production secret."""

    model_config = SettingsConfigDict(env_prefix="AI_PLATFORM_", extra="ignore")

    environment: Environment = "development"
    log_level: LogLevel = "INFO"
    learner_state_secret: SecretStr = SecretStr(_DEVELOPMENT_STATE_SECRET)

    @model_validator(mode="after")
    def require_production_state_secret(self) -> Self:
        """Reject the development signing key in production."""
        secret = self.learner_state_secret.get_secret_value()
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("learner_state_secret must contain at least 32 UTF-8 bytes")
        if self.environment == "production" and secret == _DEVELOPMENT_STATE_SECRET:
            raise ValueError("production learner_state_secret must be configured")
        return self
