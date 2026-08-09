"""Repository-root entrypoint for the deterministic phase gates."""

from __future__ import annotations

import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast


class _PhaseGateModule(Protocol):
    def main(self, arguments: list[str] | None = None) -> int: ...


def _argument_value(arguments: list[str], name: str) -> str | None:
    try:
        index = arguments.index(name)
    except ValueError:
        return None
    if index + 1 >= len(arguments):
        return None
    return arguments[index + 1]


def main(arguments: list[str] | None = None) -> int:
    repository_root = Path(__file__).resolve().parents[1]
    api_source = repository_root / "apps" / "api" / "src"
    sys.path.insert(0, str(api_source))
    phase_gate = cast(
        _PhaseGateModule,
        import_module("ai_learning_platform_api.automation.phase_gate"),
    )
    effective_arguments = list(sys.argv[1:] if arguments is None else arguments)
    if "--repository-root" not in effective_arguments:
        effective_arguments.extend(("--repository-root", str(repository_root)))
    result = phase_gate.main(effective_arguments)
    if result != 0:
        return result

    head_ref = os.environ.get("GITHUB_HEAD_REF", "").strip()
    is_validation = bool(effective_arguments) and effective_arguments[0] == "validate"
    if not head_ref.startswith("product/p") or not is_validation:
        return 0
    expected_sha = _argument_value(effective_arguments, "--expected-sha")
    if expected_sha is None:
        return 1
    full_stack_gate = cast(
        _PhaseGateModule,
        import_module("ai_learning_platform_api.automation.full_stack_gate"),
    )
    return full_stack_gate.main(
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
