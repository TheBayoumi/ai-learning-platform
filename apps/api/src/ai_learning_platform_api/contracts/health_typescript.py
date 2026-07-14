"""Generate a TypeScript health validator from the canonical OpenAPI artifact."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import cast

from ai_learning_platform_api.contracts.health_openapi import (
    HEALTH_PATHS,
    OpenAPIContractDriftError,
    check_contract,
)

OPENAPI_VERSION = "3.1.0"
LOCAL_COMPONENT_REF = re.compile(r"^#/components/schemas/([A-Za-z_$][A-Za-z0-9_$]*)$")
TYPESCRIPT_IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
OBJECT_SCHEMA_KEYS = frozenset({"type", "properties", "required", "title", "description"})
PROPERTY_SCHEMA_KEYS = frozenset({"type", "const", "title", "description"})
USAGE = (
    "usage: python -m ai_learning_platform_api.contracts.health_typescript "
    "{write|check} <openapi-path> <typescript-path>"
)
WRITE_COMMAND = (
    "uv run --locked python -m ai_learning_platform_api.contracts.health_typescript "
    "write openapi/health.openapi.json "
    "../web/server/contracts/generated/health-response.ts"
)
_MISSING = object()


class HealthValidatorGenerationError(RuntimeError):
    """The OpenAPI document cannot be represented by the bounded generator."""


class HealthValidatorDriftError(RuntimeError):
    """The tracked TypeScript validator differs from current generation."""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One supported component property derived from JSON Schema."""

    name: str
    required: bool
    typescript_type: str
    predicate: str


def _expect_object(value: object, location: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise HealthValidatorGenerationError(f"{location} must be an object with string keys")
    return cast(dict[str, object], value)


def _required(parent: Mapping[str, object], key: str, location: str) -> object:
    if key not in parent:
        raise HealthValidatorGenerationError(f"{location}.{key} is required")
    return parent[key]


def _required_object(parent: Mapping[str, object], key: str, location: str) -> dict[str, object]:
    return _expect_object(_required(parent, key, location), f"{location}.{key}")


def _expect_string(value: object, location: str) -> str:
    if not isinstance(value, str):
        raise HealthValidatorGenerationError(f"{location} must be a string")
    return value


def _expect_string_list(value: object, location: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise HealthValidatorGenerationError(f"{location} must be an array of strings")
    return cast(list[str], value)


def _reject_unknown_keys(
    value: Mapping[str, object], allowed: frozenset[str], location: str
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise HealthValidatorGenerationError(
            f"{location} contains unsupported keys: {', '.join(unknown)}"
        )


def load_verified_openapi_document(path: Path) -> dict[str, object]:
    """Load JSON only after proving the artifact still matches FastAPI."""
    check_contract(path)
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, JSONDecodeError) as error:
        raise HealthValidatorGenerationError(
            f"Unable to parse verified OpenAPI at {path}"
        ) from error
    return _expect_object(parsed, "OpenAPI document")


def _resolve_health_component(
    document: Mapping[str, object],
) -> tuple[str, dict[str, object]]:
    version = _expect_string(_required(document, "openapi", "document"), "document.openapi")
    if version != OPENAPI_VERSION:
        raise HealthValidatorGenerationError(
            f"document.openapi must be {OPENAPI_VERSION}, found {version}"
        )

    paths = _required_object(document, "paths", "document")
    if frozenset(paths) != HEALTH_PATHS:
        raise HealthValidatorGenerationError(
            f"document.paths must be exactly {sorted(HEALTH_PATHS)}"
        )

    references: set[str] = set()
    for path in sorted(HEALTH_PATHS):
        path_item = _required_object(paths, path, "document.paths")
        operation = _required_object(path_item, "get", f"document.paths.{path}")
        responses = _required_object(operation, "responses", f"document.paths.{path}.get")
        response = _required_object(responses, "200", f"document.paths.{path}.get.responses")
        content = _required_object(response, "content", f"document.paths.{path}.get.responses.200")
        media_type = _required_object(
            content,
            "application/json",
            f"document.paths.{path}.get.responses.200.content",
        )
        response_schema = _required_object(
            media_type,
            "schema",
            f"document.paths.{path}.get.responses.200.content.application/json",
        )
        _reject_unknown_keys(
            response_schema,
            frozenset({"$ref"}),
            f"document.paths.{path}.get.responses.200.content.application/json.schema",
        )
        references.add(
            _expect_string(
                _required(response_schema, "$ref", "response schema"),
                "response schema.$ref",
            )
        )

    if len(references) != 1:
        raise HealthValidatorGenerationError(
            "Health operations must share one response component reference"
        )
    reference = next(iter(references))
    match = LOCAL_COMPONENT_REF.fullmatch(reference)
    if match is None:
        raise HealthValidatorGenerationError(
            "Health response must use one local #/components/schemas reference"
        )
    component_name = match.group(1)

    components = _required_object(document, "components", "document")
    schemas = _required_object(components, "schemas", "document.components")
    if set(schemas) != {component_name}:
        raise HealthValidatorGenerationError(
            f"components.schemas must contain only the referenced {component_name} component"
        )
    schema = _required_object(schemas, component_name, "document.components.schemas")
    return component_name, schema


def _derive_fields(schema: Mapping[str, object]) -> list[FieldSpec]:
    _reject_unknown_keys(schema, OBJECT_SCHEMA_KEYS, "response component")
    schema_type = _expect_string(
        _required(schema, "type", "response component"), "response component.type"
    )
    if schema_type != "object":
        raise HealthValidatorGenerationError("response component.type must be object")

    properties = _required_object(schema, "properties", "response component")
    if not properties:
        raise HealthValidatorGenerationError("response component.properties cannot be empty")
    required = _expect_string_list(
        _required(schema, "required", "response component"), "response component.required"
    )
    if len(required) != len(set(required)):
        raise HealthValidatorGenerationError("response component.required contains duplicates")
    missing_properties = sorted(set(required) - set(properties))
    if missing_properties:
        raise HealthValidatorGenerationError(
            "response component.required names missing properties: " + ", ".join(missing_properties)
        )

    fields: list[FieldSpec] = []
    for name in sorted(properties):
        if TYPESCRIPT_IDENTIFIER.fullmatch(name) is None:
            raise HealthValidatorGenerationError(
                f"response property is not a TypeScript identifier: {name}"
            )
        property_schema = _expect_object(properties[name], f"response component.properties.{name}")
        _reject_unknown_keys(
            property_schema, PROPERTY_SCHEMA_KEYS, f"response component.properties.{name}"
        )
        property_type = _expect_string(
            _required(property_schema, "type", f"response component.properties.{name}"),
            f"response component.properties.{name}.type",
        )
        if property_type != "string":
            raise HealthValidatorGenerationError(
                f"response component.properties.{name}.type must be string"
            )

        constant = property_schema.get("const", _MISSING)
        if constant is _MISSING:
            typescript_type = "string"
            predicate = f'typeof candidate.{name} === "string"'
        else:
            if not isinstance(constant, str):
                raise HealthValidatorGenerationError(
                    f"response component.properties.{name}.const must be a string"
                )
            literal = json.dumps(constant, ensure_ascii=False)
            typescript_type = literal
            predicate = f"candidate.{name} === {literal}"

        fields.append(
            FieldSpec(
                name=name,
                required=name in required,
                typescript_type=typescript_type,
                predicate=predicate,
            )
        )
    return fields


def render_health_typescript_from_document(document: Mapping[str, object]) -> bytes:
    """Render a bounded TypeScript type guard entirely from OpenAPI schema data."""
    component_name, schema = _resolve_health_component(document)
    fields = _derive_fields(schema)
    guard_name = f"is{component_name}"
    lines = [
        "// Generated from apps/api/openapi/health.openapi.json.",
        "// Do not edit by hand. Regenerate from apps/api with:",
        f"// {WRITE_COMMAND}",
        "",
        f"export type {component_name} = Readonly<{{",
    ]
    for field in fields:
        optional = "" if field.required else "?"
        lines.append(f"  readonly {field.name}{optional}: {field.typescript_type};")
    lines.extend(
        [
            "}>;",
            "",
            f"export function {guard_name}(value: unknown): value is {component_name} {{",
            '  if (typeof value !== "object" || value === null || Array.isArray(value)) {',
            "    return false;",
            "  }",
            "",
            "  const candidate = value as Record<string, unknown>;",
            "  return (",
        ]
    )
    predicates: list[str] = []
    for field in fields:
        own = f'Object.prototype.hasOwnProperty.call(candidate, "{field.name}")'
        if field.required:
            predicates.append(f"{own} && {field.predicate}")
        else:
            predicates.append(f"(!{own} || {field.predicate})")
    for index, predicate in enumerate(predicates):
        suffix = " &&" if index < len(predicates) - 1 else ""
        lines.append(f"    {predicate}{suffix}")
    lines.extend(["  );", "}"])
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_health_typescript_validator(openapi_path: Path) -> bytes:
    """Render from a canonical OpenAPI artifact after checking source drift."""
    return render_health_typescript_from_document(load_verified_openapi_document(openapi_path))


def write_validator(openapi_path: Path, typescript_path: Path) -> None:
    """Validate the whole input before intentionally replacing generated output."""
    rendered = render_health_typescript_validator(openapi_path)
    typescript_path.parent.mkdir(parents=True, exist_ok=True)
    typescript_path.write_bytes(rendered)


def check_validator(openapi_path: Path, typescript_path: Path) -> None:
    """Fail without mutation when generated TypeScript is missing or stale."""
    expected = render_health_typescript_validator(openapi_path)
    try:
        actual = typescript_path.read_bytes()
    except FileNotFoundError as error:
        raise HealthValidatorDriftError(
            f"Generated health validator is missing at {typescript_path}; regenerate with: "
            f"{WRITE_COMMAND}"
        ) from error
    if actual != expected:
        raise HealthValidatorDriftError(
            f"Generated health validator drift detected at {typescript_path}; regenerate with: "
            f"{WRITE_COMMAND}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run explicit write or non-mutating check behavior."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 3 or arguments[0] not in {"write", "check"}:
        print(USAGE, file=sys.stderr)
        return 2

    action, raw_openapi_path, raw_typescript_path = arguments
    openapi_path = Path(raw_openapi_path)
    typescript_path = Path(raw_typescript_path)
    try:
        if action == "write":
            write_validator(openapi_path, typescript_path)
            print(f"Wrote generated health validator: {typescript_path}")
        else:
            check_validator(openapi_path, typescript_path)
            print(f"Generated health validator is current: {typescript_path}")
    except (
        OpenAPIContractDriftError,
        HealthValidatorGenerationError,
        HealthValidatorDriftError,
    ) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
