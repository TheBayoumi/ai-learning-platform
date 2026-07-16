"""Repository-root entrypoint for the deterministic phase gate."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast


class _PhaseGateModule(Protocol):
    def main(self, arguments: list[str] | None = None) -> int: ...


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
    return phase_gate.main(effective_arguments)


if __name__ == "__main__":
    raise SystemExit(main())
