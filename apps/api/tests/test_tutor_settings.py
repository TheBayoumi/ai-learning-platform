from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from ai_learning_platform_api.settings import Settings


def test_tutor_is_disabled_by_default_without_provider_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("VERCEL_OIDC_TOKEN", raising=False)
    settings = Settings(environment="test")

    assert settings.tutor_mode == "disabled"
    assert settings.tutor_gateway_token() is None
    assert settings.tutor_max_output_tokens == 600
    assert settings.tutor_max_concurrent_turns == 8
    assert settings.tutor_requests_per_window == 6
    assert settings.tutor_rate_window_seconds == 60


def test_enabled_tutor_requires_server_only_gateway_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PLATFORM_AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.delenv("AI_PLATFORM_VERCEL_OIDC_TOKEN", raising=False)
    monkeypatch.delenv("VERCEL_OIDC_TOKEN", raising=False)

    with pytest.raises(ValidationError, match="AI Gateway credential is required"):
        Settings(environment="test", tutor_mode="vercel_ai_gateway")


def test_enabled_tutor_accepts_and_redacts_explicit_gateway_key() -> None:
    raw_key = "gateway-secret-that-must-not-appear-in-repr"
    settings = Settings(
        environment="test",
        tutor_mode="vercel_ai_gateway",
        ai_gateway_api_key=SecretStr(raw_key),
    )

    assert settings.tutor_gateway_token() == raw_key
    assert raw_key not in repr(settings)


def test_enabled_tutor_accepts_vercel_oidc_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL_OIDC_TOKEN", "oidc-token")
    settings = Settings(environment="test", tutor_mode="vercel_ai_gateway")

    assert settings.tutor_gateway_token() == "oidc-token"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tutor_max_output_tokens", 1_001),
        ("tutor_max_concurrent_turns", 0),
        ("tutor_requests_per_window", 101),
        ("tutor_rate_window_seconds", 9),
        ("tutor_timeout_seconds", 46),
    ],
)
def test_tutor_resource_bounds_fail_configuration(
    field: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError, match=field):
        Settings.model_validate({"environment": "test", field: value})
