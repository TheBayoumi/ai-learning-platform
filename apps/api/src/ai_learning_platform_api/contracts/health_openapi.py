"""Generate and verify the canonical role-neutral health OpenAPI contract."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.settings import Settings

HEALTH_PATHS = frozenset({"/health/live", "/health/ready"})
USAGE = (
    "usage: python -m ai_learning_platform_api.contracts.health_openapi "
    "{write|check} <artifact-path>"
)
WRITE_COMMAND = (
    "uv run --locked python -m ai_learning_platform_api.contracts.health_openapi "
    "write openapi/health.openapi.json"
)


class OpenAPIContractDriftError(RuntimeError):
    """The committed artifact does not equal current FastAPI generation."""


def build_health_openapi_document() -> dict[str, Any]:
    """Return the complete generated document after enforcing F01 health scope."""
    app = create_app(Settings(environment="test", log_level="CRITICAL"))
    document = app.openapi()
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise RuntimeError("Generated OpenAPI document has no paths object")

    actual_paths = frozenset(str(path) for path in paths)
    if actual_paths != HEALTH_PATHS:
        raise RuntimeError(
            "F01 health OpenAPI scope changed: "
            f"expected {sorted(HEALTH_PATHS)}, generated {sorted(actual_paths)}"
        )
    return document


def render_health_openapi_document() -> bytes:
    """Render deterministic UTF-8 JSON bytes with LF and one final newline."""
    document = build_health_openapi_document()
    rendered = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return rendered.encode("utf-8")


def write_contract(path: Path) -> None:
    """Intentionally replace an artifact with current canonical bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_health_openapi_document())


def check_contract(path: Path) -> None:
    """Fail without mutation when an artifact is missing or byte-different."""
    expected = render_health_openapi_document()
    try:
        actual = path.read_bytes()
    except FileNotFoundError as error:
        raise OpenAPIContractDriftError(
            f"OpenAPI contract is missing at {path}; regenerate with: {WRITE_COMMAND}"
        ) from error

    if actual != expected:
        raise OpenAPIContractDriftError(
            f"OpenAPI contract drift detected at {path}; regenerate with: {WRITE_COMMAND}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the explicit write or non-mutating check action."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2 or arguments[0] not in {"write", "check"}:
        print(USAGE, file=sys.stderr)
        return 2

    action, raw_path = arguments
    path = Path(raw_path)
    if action == "write":
        write_contract(path)
        print(f"Wrote canonical health OpenAPI contract: {path}")
        return 0

    try:
        check_contract(path)
    except OpenAPIContractDriftError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Canonical health OpenAPI contract is current: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through main()
    raise SystemExit(main())
