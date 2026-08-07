import asyncio
import json
import logging

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.logging import configure_logging
from ai_learning_platform_api.settings import Settings


async def get_health(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app(Settings(environment="test", log_level="INFO")))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_application_factory_creates_foundation_application() -> None:
    app = create_app(Settings(environment="test", log_level="INFO"))

    assert app.title == "AI Career Learning Platform API"


def test_postgres_mode_wires_durable_compatibility_routes() -> None:
    settings = Settings(
        environment="test",
        persistence_mode="postgres",
        database_url=SecretStr("postgresql+psycopg://db.example/platform"),
    )
    app = create_app(settings)
    paths = app.openapi().get("paths")
    assert isinstance(paths, dict)

    assert "/api/v1/plans" in paths
    assert "/api/v1/plans/resume" in paths
    assert "/api/v1/progress" in paths
    assert all(not path.startswith("/api/v1/persistent/") for path in paths)

    async def run_lifespan() -> None:
        async with app.router.lifespan_context(app):
            pass

    asyncio.run(run_lifespan())


def test_live_health_check_returns_typed_process_status() -> None:
    response = asyncio.run(get_health("/health/live"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "detail": "process is live"}


def test_ready_health_check_explains_its_configuration_only_scope() -> None:
    response = asyncio.run(get_health("/health/ready"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "detail": "configuration is valid; no external dependency checks are performed",
    }


def test_invalid_environment_fails_settings_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PLATFORM_ENVIRONMENT", "invalid")

    with pytest.raises(ValidationError, match="environment"):
        Settings()


def test_signed_state_mode_does_not_require_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PLATFORM_DATABASE_URL", raising=False)
    settings = Settings(environment="test", persistence_mode="signed_state")

    assert settings.persistence_mode == "signed_state"
    assert settings.database_url is None


def test_postgres_persistence_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PLATFORM_DATABASE_URL", raising=False)
    with pytest.raises(
        ValidationError,
        match="database_url must be configured for postgres persistence",
    ):
        Settings(environment="test", persistence_mode="postgres")


def test_postgres_persistence_rejects_non_psycopg_driver() -> None:
    with pytest.raises(
        ValidationError,
        match=r"database_url must use the postgresql\+psycopg driver",
    ):
        Settings(
            environment="test",
            persistence_mode="postgres",
            database_url=SecretStr("postgresql+asyncpg://db.example/platform"),
        )


def test_postgres_persistence_keeps_database_url_secret() -> None:
    raw_database_url = "postgresql+psycopg://db.example/platform?sslmode=require"

    settings = Settings(
        environment="test",
        persistence_mode="postgres",
        database_url=SecretStr(raw_database_url),
    )

    assert settings.database_url is not None
    assert settings.database_url.get_secret_value() == raw_database_url
    assert raw_database_url not in repr(settings)


def test_structured_logging_initialization_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    logging.getLogger("foundation-test").info("CANARY configured")

    payload = json.loads(capsys.readouterr().err)

    assert payload == {
        "schema_version": 1,
        "event": "process.log",
        "service": "api",
        "outcome": "status",
        "reason": "unstructured_suppressed",
        "severity": "info",
    }
