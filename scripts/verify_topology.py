"""Fail closed when deployment compute or promotion controls drift."""

from __future__ import annotations

import json
from pathlib import Path

_SELECTED_REGION = "pdx1"
_REQUIRED_PREFERRED_REGION_FILES = (
    Path("apps/web/app/api/platform/[...path]/route.ts"),
    Path("apps/web/app/page.tsx"),
    Path("apps/web/app/status/page.tsx"),
)
_DEPLOYMENT_WORKFLOW = Path(".github/workflows/product-deployment.yml")
_DEPLOYMENT_SCRIPT = Path("scripts/deploy-product.sh")


class TopologyVerificationError(RuntimeError):
    """The committed deployment topology or promotion contract is unsafe."""


def verify_topology(root: Path | None = None) -> dict[str, object]:
    """Verify committed deployment-region and safe-promotion controls."""
    repository_root = root if root is not None else Path.cwd()
    workflow = (repository_root / _DEPLOYMENT_WORKFLOW).read_text(encoding="utf-8")
    deployment_script = (repository_root / _DEPLOYMENT_SCRIPT).read_text(encoding="utf-8")

    if f"VERCEL_FUNCTION_REGION: {_SELECTED_REGION}" not in workflow:
        raise TopologyVerificationError("deployment_region_missing")
    if "serverlessFunctionRegion:$region" not in workflow:
        raise TopologyVerificationError("project_region_update_missing")
    if "VERCEL_FUNCTION_REGION" not in deployment_script:
        raise TopologyVerificationError("deploy_script_region_input_missing")
    if "serverlessFunctionRegion:$region" not in deployment_script:
        raise TopologyVerificationError("deploy_script_region_update_missing")
    if "fra1" in workflow or "fra1" in deployment_script:
        raise TopologyVerificationError("legacy_cross_region_target_present")

    if "vc deploy --cwd apps/api --yes --archive=tgz --prod" in deployment_script:
        raise TopologyVerificationError("backend_unverified_direct_production_deploy")
    required_promotion_controls = (
        'phase="backend-candidate-deployment"',
        'phase="backend-candidate-verification"',
        'vc curl --url "$backend_deployment_url/health/live"',
        '--silent --show-error --output "$candidate_health"',
        'vc curl --url "$backend_deployment_url/api/v1/roles"',
        '--silent --show-error --output "$candidate_roles"',
        'phase="backend-promotion"',
        'vc promote "$backend_deployment_url" --yes',
        'phase="backend-public-verification"',
    )
    if any(marker not in deployment_script for marker in required_promotion_controls):
        raise TopologyVerificationError("backend_promotion_control_missing")

    checked_files = [
        _DEPLOYMENT_WORKFLOW.as_posix(),
        _DEPLOYMENT_SCRIPT.as_posix(),
    ]
    expected_export = f'export const preferredRegion = "{_SELECTED_REGION}";'
    for relative_path in _REQUIRED_PREFERRED_REGION_FILES:
        content = (repository_root / relative_path).read_text(encoding="utf-8")
        if expected_export not in content:
            raise TopologyVerificationError(f"preferred_region_missing:{relative_path.as_posix()}")
        checked_files.append(relative_path.as_posix())

    return {
        "backend_promotion": "candidate_verified_before_promotion",
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
