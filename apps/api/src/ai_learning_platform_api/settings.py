"""Validated process and product configuration boundary."""

from typing import Annotated, Literal, Self

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
PersistenceMode = Literal["signed_state", "postgres"]
TutorMode = Literal["disabled", "vercel_ai_gateway"]

_DEVELOPMENT_STATE_SECRET = "development-only-learner-state-secret-change-me"
_POSTGRESQL_URL_PREFIX = "postgresql+psycopg://"


class Settings(BaseSettings):
    """Validated runtime configuration with fail-closed production boundaries."""

    model_config = SettingsConfigDict(
        env_prefix="AI_PLATFORM_",
        extra="ignore",
        populate_by_name=True,
    )

    environment: Environment = "development"
    log_level: LogLevel = "INFO"
    learner_state_secret: SecretStr = SecretStr(_DEVELOPMENT_STATE_SECRET)
    persistence_mode: PersistenceMode = "signed_state"
    database_url: SecretStr | None = None
    tutor_mode: TutorMode = "disabled"
    tutor_model: Annotated[
        str,
        Field(min_length=3, max_length=160, pattern=r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$"),
    ] = "alibaba/qwen3.5-flash"
    tutor_timeout_seconds: Annotated[float, Field(ge=5.0, le=45.0)] = 25.0
    tutor_max_output_tokens: Annotated[int, Field(ge=128, le=1_000)] = 600
    tutor_max_concurrent_turns: Annotated[int, Field(ge=1, le=100)] = 8
    tutor_requests_per_window: Annotated[int, Field(ge=1, le=100)] = 6
    tutor_rate_window_seconds: Annotated[int, Field(ge=10, le=3_600)] = 60
    ai_gateway_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_PLATFORM_AI_GATEWAY_API_KEY",
            "AI_GATEWAY_API_KEY",
        ),
    )
    vercel_oidc_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AI_PLATFORM_VERCEL_OIDC_TOKEN",
            "VERCEL_OIDC_TOKEN",
        ),
    )

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

        if self.tutor_mode == "vercel_ai_gateway" and self.tutor_gateway_token() is None:
            raise ValueError(
                "a server-only AI Gateway credential is required when tutoring is enabled"
            )

        return self

    def tutor_gateway_token(self) -> str | None:
        """Return the first configured server-only gateway credential."""
        for candidate in (self.ai_gateway_api_key, self.vercel_oidc_token):
            if candidate is None:
                continue
            value = candidate.get_secret_value().strip()
            if value:
                return value
        return None
