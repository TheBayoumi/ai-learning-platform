import asyncio
import json
import logging

import httpx
import pytest
from pydantic import ValidationError

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


def test_structured_logging_initialization_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    logging.getLogger("foundation-test").info("configured")

    payload = json.loads(capsys.readouterr().err)

    assert payload == {"level": "INFO", "logger": "foundation-test", "message": "configured"}
