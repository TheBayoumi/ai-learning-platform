import pytest
from pydantic import SecretStr, ValidationError

from ai_learning_platform_api.persistence.database import DatabaseRuntime, normalize_database_url
from ai_learning_platform_api.settings import Settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        (
            "postgresql://user:pass@db.example/neondb?sslmode=require&channel_binding=require",
            "postgresql+psycopg://user:pass@db.example/neondb?sslmode=require&channel_binding=require",
        ),
        (
            "postgres://user:pass@db.example/neondb?sslmode=require",
            "postgresql+psycopg://user:pass@db.example/neondb?sslmode=require",
        ),
        (
            "postgresql+psycopg://user:pass@db.example/neondb?sslmode=require",
            "postgresql+psycopg://user:pass@db.example/neondb?sslmode=require",
        ),
    ],
)
def test_normalize_database_url_uses_psycopg3(database_url: str, expected: str) -> None:
    assert normalize_database_url(database_url) == expected


def test_database_runtime_uses_psycopg_for_standard_postgres_url() -> None:
    runtime = DatabaseRuntime.create("postgresql://user:pass@localhost/neondb?sslmode=require")

    assert runtime.engine.url.drivername == "postgresql+psycopg"
    assert runtime.engine.url.query["sslmode"] == "require"


def test_settings_canonicalize_standard_postgres_url_before_runtime() -> None:
    settings = Settings(
        persistence_mode="postgres",
        database_url=SecretStr(
            "postgresql://user:pass@db.example/neondb?sslmode=require&channel_binding=require"
        ),
    )

    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == (
        "postgresql+psycopg://user:pass@db.example/neondb?sslmode=require&channel_binding=require"
    )


def test_settings_reject_unsupported_database_driver() -> None:
    with pytest.raises(ValidationError, match="database_url must use the postgresql\\+psycopg driver"):
        Settings(
            persistence_mode="postgres",
            database_url=SecretStr("postgresql+asyncpg://user:pass@db.example/neondb"),
        )
