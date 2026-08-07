"""Fail closed when deployment compute drifts away from the selected database region."""

from __future__ import annotations

import json
from pathlib import Path

_SELECTED_REGION = "pdx1"
_REQUIRED_PREFERRED_REGION_FILES = (
    Path("apps/web/app/api/platform/[...path]/route.ts"),
    Path("apps/web/app/page.tsx"),
    Path("apps/web/app/status/page.tsx"),
)


class TopologyVerificationError(RuntimeError):
    """The committed deployment topology does not match the selected region."""


def verify_topology(root: Path | None = None) -> dict[str, object]:
    """Verify committed deployment-region controls from the selected repository root."""
    repository_root = root if root is not None else Path.cwd()
    workflow = (repository_root / ".github/workflows/product-deployment.yml").read_text(
        encoding="utf-8"
    )
    if f"VERCEL_FUNCTION_REGION: {_SELECTED_REGION}" not in workflow:
        raise TopologyVerificationError("deployment_region_missing")
    if "serverlessFunctionRegion:$region" not in workflow:
        raise TopologyVerificationError("project_region_update_missing")
    if "fra1" in workflow:
        raise TopologyVerificationError("legacy_cross_region_target_present")

    checked_files: list[str] = []
    expected_export = f'export const preferredRegion = "{_SELECTED_REGION}";'
    for relative_path in _REQUIRED_PREFERRED_REGION_FILES:
        content = (repository_root / relative_path).read_text(encoding="utf-8")
        if expected_export not in content:
            raise TopologyVerificationError(
                f"preferred_region_missing:{relative_path.as_posix()}"
            )
        checked_files.append(relative_path.as_posix())

    return {
        "checked_files": checked_files,
        "region": _SELECTED_REGION,
        "status": "passed",
    }


def main() -> int:
    try:
        report = verify_topology()
    except (OSError, TopologyVerificationError) as error:
        print(f"topology_verification_failed:{error}")
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
