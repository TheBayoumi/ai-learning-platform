"""Validated process configuration boundary."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Settings that do not name a vendor, URL, credential, or product domain."""

    model_config = SettingsConfigDict(env_prefix="AI_PLATFORM_", extra="ignore")

    environment: Environment = "development"
    log_level: LogLevel = "INFO"
