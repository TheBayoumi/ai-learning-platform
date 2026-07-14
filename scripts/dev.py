"""Repository-root entrypoint for the development process supervisor."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Protocol, cast


class _SupervisorModule(Protocol):
    def main(self) -> int: ...


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    api_source = repository_root / "apps" / "api" / "src"
    sys.path.insert(0, str(api_source))
    supervisor = cast(
        _SupervisorModule,
        import_module("ai_learning_platform_api.development.supervisor"),
    )
    return supervisor.main()


if __name__ == "__main__":
    raise SystemExit(main())
