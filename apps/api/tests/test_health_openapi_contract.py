import sys
from pathlib import Path

import pytest

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.contracts import health_openapi
from ai_learning_platform_api.contracts.health_openapi import (
    HEALTH_PATHS,
    OpenAPIContractDriftError,
    build_health_openapi_document,
    check_contract,
    main,
    render_health_openapi_document,
    write_contract,
)
from ai_learning_platform_api.settings import Settings

API_ROOT = Path(__file__).resolve().parents[1]
COMMITTED_CONTRACT = API_ROOT / "openapi" / "health.openapi.json"


def test_generated_document_is_the_complete_health_only_runtime_contract() -> None:
    document = build_health_openapi_document()
    runtime_document = create_app(
        Settings(environment="test", log_level="CRITICAL"),
        include_product_routes=False,
    ).openapi()

    assert document == runtime_document
    assert set(document["paths"]) == HEALTH_PATHS
    assert document["paths"]["/health/live"]["get"]["operationId"] == "health_live"
    assert document["paths"]["/health/ready"]["get"]["operationId"] == "health_ready"
    assert document["paths"]["/health/live"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/HealthResponse"}


def test_render_is_repeatable_lf_only_and_has_one_final_newline() -> None:
    first = render_health_openapi_document()
    second = render_health_openapi_document()

    assert first == second
    assert first.endswith(b"\n")
    assert not first.endswith(b"\n\n")
    assert b"\r\n" not in first


def test_committed_contract_matches_current_generation() -> None:
    check_contract(COMMITTED_CONTRACT)


def test_write_and_check_use_exact_canonical_bytes(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "health.openapi.json"

    write_contract(target)
    before_check = target.read_bytes()
    check_contract(target)

    assert before_check == render_health_openapi_document()
    assert target.read_bytes() == before_check


def test_check_rejects_missing_artifact_without_creating_it(tmp_path: Path) -> None:
    target = tmp_path / "missing.json"

    with pytest.raises(OpenAPIContractDriftError, match="is missing"):
        check_contract(target)

    assert not target.exists()


@pytest.mark.parametrize(
    "drifted_bytes",
    [b"{}\n", render_health_openapi_document().replace(b"\n", b"\r\n")],
    ids=["stale", "crlf"],
)
def test_check_rejects_drift_without_rewriting(tmp_path: Path, drifted_bytes: bytes) -> None:
    target = tmp_path / "drifted.json"
    target.write_bytes(drifted_bytes)

    with pytest.raises(OpenAPIContractDriftError, match="drift detected"):
        check_contract(target)

    assert target.read_bytes() == drifted_bytes


def test_scope_guard_rejects_an_unapproved_route(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(Settings(environment="test", log_level="CRITICAL"))

    @app.get("/not-approved")
    async def not_approved() -> dict[str, str]:
        return {"status": "not-approved"}

    monkeypatch.setattr(health_openapi, "create_app", lambda _settings, **_kwargs: app)

    with pytest.raises(RuntimeError, match="scope changed"):
        build_health_openapi_document()


def test_scope_guard_rejects_a_document_without_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AppWithoutPaths:
        @staticmethod
        def openapi() -> dict[str, object]:
            return {}

    monkeypatch.setattr(
        health_openapi,
        "create_app",
        lambda _settings, **_kwargs: AppWithoutPaths(),
    )

    with pytest.raises(RuntimeError, match="no paths object"):
        build_health_openapi_document()


def test_cli_reports_usage_write_success_check_success_and_drift(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "health.openapi.json"

    assert main([]) == 2
    assert "usage:" in capsys.readouterr().err

    assert main(["write", str(target)]) == 0
    assert "Wrote canonical" in capsys.readouterr().out

    assert main(["check", str(target)]) == 0
    assert "is current" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["health_openapi", "check", str(target)])
    assert main() == 0
    assert "is current" in capsys.readouterr().out

    target.write_bytes(b"stale\n")
    assert main(["check", str(target)]) == 1
    assert "drift detected" in capsys.readouterr().err
