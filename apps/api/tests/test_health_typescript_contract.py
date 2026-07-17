import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

from ai_learning_platform_api.contracts import health_typescript
from ai_learning_platform_api.contracts.health_openapi import OpenAPIContractDriftError
from ai_learning_platform_api.contracts.health_typescript import (
    HealthValidatorDriftError,
    HealthValidatorGenerationError,
    check_validator,
    load_verified_openapi_document,
    main,
    render_health_typescript_from_document,
    render_health_typescript_validator,
    write_validator,
)

API_ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = API_ROOT / "openapi" / "health.openapi.json"
GENERATED_VALIDATOR = (
    API_ROOT.parent / "web" / "server" / "contracts" / "generated" / "health-response.ts"
)


def canonical_document() -> dict[str, Any]:
    parsed: object = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return cast(dict[str, Any], parsed)


def response_schema(document: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], document["components"]["schemas"]["HealthResponse"])


def test_renderer_derives_type_and_guard_without_network_behavior() -> None:
    source = render_health_typescript_from_document(canonical_document()).decode("utf-8")

    assert "export type HealthResponse" in source
    assert "readonly detail: string;" in source
    assert 'readonly status: "ok";' in source
    assert "export function isHealthResponse(value: unknown)" in source
    assert 'hasOwnProperty.call(candidate, "detail")' in source
    assert 'hasOwnProperty.call(candidate, "status")' in source
    assert "fetch" not in source
    assert "process.env" not in source


def test_render_is_repeatable_lf_only_and_matches_committed_output() -> None:
    first = render_health_typescript_validator(OPENAPI_PATH)
    second = render_health_typescript_validator(OPENAPI_PATH)

    assert first == second == GENERATED_VALIDATOR.read_bytes()
    assert first.endswith(b"\n")
    assert not first.endswith(b"\n\n")
    assert b"\r\n" not in first


def test_write_and_check_use_exact_bytes(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "health-response.ts"

    write_validator(OPENAPI_PATH, target)
    before_check = target.read_bytes()
    check_validator(OPENAPI_PATH, target)

    assert before_check == render_health_typescript_validator(OPENAPI_PATH)
    assert target.read_bytes() == before_check


def test_check_rejects_missing_output_without_creating_it(tmp_path: Path) -> None:
    target = tmp_path / "missing.ts"

    with pytest.raises(HealthValidatorDriftError, match="is missing"):
        check_validator(OPENAPI_PATH, target)

    assert not target.exists()


@pytest.mark.parametrize(
    "drifted_bytes",
    [b"export {};\n", b"export {};\r\n"],
    ids=["stale", "crlf"],
)
def test_check_rejects_drift_without_rewriting(tmp_path: Path, drifted_bytes: bytes) -> None:
    target = tmp_path / "drifted.ts"
    target.write_bytes(drifted_bytes)

    with pytest.raises(HealthValidatorDriftError, match="drift detected"):
        check_validator(OPENAPI_PATH, target)

    assert target.read_bytes() == drifted_bytes


def test_invalid_source_does_not_mutate_output(tmp_path: Path) -> None:
    source = tmp_path / "stale.openapi.json"
    source.write_bytes(b"{}\n")
    target = tmp_path / "health-response.ts"
    target.write_bytes(b"keep\n")

    with pytest.raises(OpenAPIContractDriftError):
        write_validator(source, target)

    assert target.read_bytes() == b"keep\n"


def test_verified_document_parse_failure_is_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "invalid.json"
    source.write_bytes(b"not-json\n")
    monkeypatch.setattr(health_typescript, "check_contract", lambda _path: None)

    with pytest.raises(HealthValidatorGenerationError, match="Unable to parse"):
        load_verified_openapi_document(source)


@pytest.mark.parametrize(
    "case",
    [
        "missing-openapi",
        "openapi-not-string",
        "openapi-version",
        "paths-not-object",
        "paths-non-string-key",
        "paths-mismatch",
        "divergent-reference",
        "external-reference",
        "extra-component",
        "explicit-additional-properties",
        "schema-not-object",
        "empty-properties",
        "unsupported-property-keyword",
        "required-not-list",
        "required-non-string",
        "duplicate-required",
        "required-missing-property",
        "unsupported-property-type",
        "non-string-const",
        "invalid-property-identifier",
    ],
)
def test_generator_fails_closed_for_unsupported_schema(case: str) -> None:
    document = deepcopy(canonical_document())
    schema = response_schema(document)

    if case == "missing-openapi":
        document.pop("openapi")
    elif case == "openapi-not-string":
        document["openapi"] = 1
    elif case == "openapi-version":
        document["openapi"] = "3.0.3"
    elif case == "paths-not-object":
        document["paths"] = []
    elif case == "paths-non-string-key":
        document["paths"][1] = {}
    elif case == "paths-mismatch":
        document["paths"].pop("/health/ready")
    elif case == "divergent-reference":
        document["paths"]["/health/ready"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"] = "#/components/schemas/OtherResponse"
    elif case == "external-reference":
        for path in ("/health/live", "/health/ready"):
            document["paths"][path]["get"]["responses"]["200"]["content"]["application/json"][
                "schema"
            ]["$ref"] = "https://example.invalid/health.json"
    elif case == "extra-component":
        document["components"]["schemas"]["OtherResponse"] = deepcopy(schema)
    elif case == "explicit-additional-properties":
        schema["additionalProperties"] = False
    elif case == "schema-not-object":
        schema["type"] = "array"
    elif case == "empty-properties":
        schema["properties"] = {}
    elif case == "unsupported-property-keyword":
        schema["properties"]["detail"]["minLength"] = 1
    elif case == "required-not-list":
        schema["required"] = "detail"
    elif case == "required-non-string":
        schema["required"].append(1)
    elif case == "duplicate-required":
        schema["required"].append("detail")
    elif case == "required-missing-property":
        schema["required"].append("missing")
    elif case == "unsupported-property-type":
        schema["properties"]["detail"]["type"] = "integer"
    elif case == "non-string-const":
        schema["properties"]["status"]["const"] = 1
    else:
        schema["properties"]["invalid-name"] = schema["properties"].pop("detail")
        schema["required"][schema["required"].index("detail")] = "invalid-name"

    with pytest.raises(HealthValidatorGenerationError):
        render_health_typescript_from_document(document)


def test_optional_supported_property_is_derived_as_optional() -> None:
    document = deepcopy(canonical_document())
    response_schema(document)["required"].remove("detail")

    source = render_health_typescript_from_document(document).decode("utf-8")

    assert "readonly detail?: string;" in source
    assert '!Object.prototype.hasOwnProperty.call(candidate, "detail")' in source


def test_cli_reports_usage_write_check_and_failures(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "health-response.ts"

    assert main([]) == 2
    assert "usage:" in capsys.readouterr().err

    assert main(["write", str(OPENAPI_PATH), str(target)]) == 0
    assert "Wrote generated" in capsys.readouterr().out

    assert main(["check", str(OPENAPI_PATH), str(target)]) == 0
    assert "is current" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["health_typescript", "check", str(OPENAPI_PATH), str(target)])
    assert main() == 0
    assert "is current" in capsys.readouterr().out

    target.write_bytes(b"stale\n")
    assert main(["check", str(OPENAPI_PATH), str(target)]) == 1
    assert "drift detected" in capsys.readouterr().err
