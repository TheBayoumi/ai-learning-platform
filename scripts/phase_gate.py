"""Repository-root entrypoint for the deterministic phase gates."""

from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast


class _GateModule(Protocol):
    def main(self, arguments: list[str] | None = None) -> int: ...


def _load_gate(module_name: str) -> _GateModule:
    return cast(_GateModule, import_module(module_name))


def _argument_value(arguments: list[str], name: str) -> str | None:
    try:
        index = arguments.index(name)
    except ValueError:
        return None
    return arguments[index + 1] if index + 1 < len(arguments) else None


def main(arguments: list[str] | None = None) -> int:
    repository_root = Path(__file__).resolve().parents[1]
    api_source = repository_root / "apps" / "api" / "src"
    sys.path.insert(0, str(api_source))
    effective_arguments = list(sys.argv[1:] if arguments is None else arguments)
    if "--repository-root" not in effective_arguments:
        effective_arguments.extend(("--repository-root", str(repository_root)))

    phase_gate = _load_gate("ai_learning_platform_api.automation.phase_gate")
    result = phase_gate.main(effective_arguments)
    if result != 0 or not effective_arguments or effective_arguments[0] != "validate":
        return result

    head_ref = os.environ.get("GITHUB_HEAD_REF", "")
    if not head_ref.startswith("product/g"):
        return 0
    expected_sha = _argument_value(effective_arguments, "--expected-sha")
    if expected_sha is None:
        return 1
    product_gate = _load_gate("ai_learning_platform_api.automation.product_gate")
    return product_gate.main(
        [
            "validate",
            "--expected-sha",
            expected_sha,
            "--head-ref",
            head_ref,
            "--repository-root",
            str(repository_root),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
