"""Fail-closed acceptance gate for the mission-aligned G01-G09 product program."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

STATE_PATH: Final = Path("plans/adaptive-product-state.json")
FULL_STACK_STATE_PATH: Final = Path("plans/full-stack-product-state.json")
PHASE_IDS: Final = tuple(f"G{index:02d}" for index in range(1, 10))
REQUIRED_CHECKS: Final = (
    "API quality",
    "Web quality",
    "Runtime smoke",
    "Phase gate",
    "Gate projection",
)
RISK_TIERS: Final = ("A", "B", "C", "D", "E")
ACTIVE_STATUSES: Final = frozenset(
    {"IMPLEMENTING", "VALIDATING", "FAILED_RETRYABLE", "BLOCKED_EXTERNAL"}
)
SHA_PATTERN: Final = re.compile(r"^[0-9a-f]{40}$")
PRODUCT_BRANCH_PATTERN: Final = re.compile(r"^product/(?P<phase>g[0-9]{2})-[a-z0-9][a-z0-9-]*$")
DOD_PATTERN: Final = re.compile(r"^D(?:0[1-9]|1[0-2])$")


class ProductGateViolation(RuntimeError):
    """One stable fail-closed product gate code."""


@dataclass(frozen=True, slots=True)
class ProductPhase:
    identifier: str
    status: str
    branch: str | None
    dependencies: tuple[str, ...]
    accepted_sha: str | None


def _violation(code: str) -> ProductGateViolation:
    return ProductGateViolation(code)


def _mapping(value: object, code: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise _violation(code)
    return cast(dict[str, object], value)


def _sequence(value: object, code: str) -> list[object]:
    if not isinstance(value, list):
        raise _violation(code)
    return cast(list[object], value)


def _string(value: object, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise _violation(code)
    return value


def _optional_string(value: object, code: str) -> str | None:
    if value is None:
        return None
    return _string(value, code)


def _strings(value: object, code: str) -> list[str]:
    values = _sequence(value, code)
    if not all(isinstance(item, str) and item for item in values):
        raise _violation(code)
    return cast(list[str], values)


def _exact_keys(value: Mapping[str, object], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise _violation(code)


def _load_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size > 131_072:
        raise _violation("product_state_missing_or_oversized")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _violation("product_state_invalid_json") from error
    return _mapping(raw, "product_state_invalid")


def _validate_evidence_paths(root: Path, paths: Sequence[str], code: str) -> None:
    for value in paths:
        path = Path(value)
        if path.is_absolute():
            raise _violation(code)
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root) or not resolved.exists():
            raise _violation(code)


def _parse_phase(
    raw: Mapping[str, object],
    *,
    identifier: str,
    root: Path,
    active_phase: str,
) -> ProductPhase:
    _exact_keys(
        raw,
        {
            "id",
            "name",
            "status",
            "branch",
            "dependencies",
            "dod_contracts",
            "risk_tiers",
            "implementation_evidence",
            "test_evidence",
            "human_simulations",
            "human_simulation_evidence",
            "accepted_sha",
            "production_acceptance",
            "next_phase",
        },
        "product_phase_fields_invalid",
    )
    if _string(raw["id"], "product_phase_id_invalid") != identifier:
        raise _violation("product_phase_order_invalid")
    _string(raw["name"], "product_phase_name_invalid")
    status = _string(raw["status"], "product_phase_status_invalid")
    if status not in {"NOT_STARTED", "PASSED", *ACTIVE_STATUSES}:
        raise _violation("product_phase_status_invalid")
    branch = _optional_string(raw["branch"], "product_phase_branch_invalid")
    accepted_sha = _optional_string(raw["accepted_sha"], "product_phase_sha_invalid")
    dependencies = tuple(_strings(raw["dependencies"], "product_phase_dependencies_invalid"))
    expected_dependencies = (
        () if identifier == "G01" else (PHASE_IDS[PHASE_IDS.index(identifier) - 1],)
    )
    if dependencies != expected_dependencies:
        raise _violation("product_phase_dependencies_invalid")
    contracts = _strings(raw["dod_contracts"], "product_phase_dod_invalid")
    if (
        not contracts
        or len(contracts) != len(set(contracts))
        or any(DOD_PATTERN.fullmatch(item) is None for item in contracts)
    ):
        raise _violation("product_phase_dod_invalid")
    if tuple(_strings(raw["risk_tiers"], "product_phase_risk_invalid")) != RISK_TIERS:
        raise _violation("product_phase_risk_invalid")

    implementation = _strings(raw["implementation_evidence"], "product_phase_evidence_invalid")
    tests = _strings(raw["test_evidence"], "product_phase_evidence_invalid")
    personas = _strings(raw["human_simulations"], "product_phase_human_invalid")
    human_evidence = _strings(raw["human_simulation_evidence"], "product_phase_human_invalid")
    production = _strings(raw["production_acceptance"], "product_phase_production_invalid")
    if identifier == "G09":
        if raw["next_phase"] not in {None, "P01"}:
            raise _violation("product_phase_next_invalid")
    else:
        expected_next = PHASE_IDS[PHASE_IDS.index(identifier) + 1]
        if raw["next_phase"] != expected_next:
            raise _violation("product_phase_next_invalid")

    if status == "PASSED":
        if branch is None or accepted_sha is None or SHA_PATTERN.fullmatch(accepted_sha) is None:
            raise _violation("product_passed_identity_invalid")
        if not implementation or not tests or not personas or not human_evidence or not production:
            raise _violation("product_passed_evidence_missing")
        _validate_evidence_paths(
            root,
            [*implementation, *tests, *human_evidence],
            "product_evidence_path_invalid",
        )
    elif identifier == active_phase:
        if status not in ACTIVE_STATUSES or branch is None or accepted_sha is not None:
            raise _violation("product_active_state_invalid")
        if not implementation or not tests or not personas or not human_evidence:
            raise _violation("product_active_evidence_missing")
        _validate_evidence_paths(
            root,
            [*implementation, *tests, *human_evidence],
            "product_evidence_path_invalid",
        )
    else:
        if status != "NOT_STARTED" or branch is not None or accepted_sha is not None:
            raise _violation("product_future_phase_started")
        if implementation or tests or human_evidence or production:
            raise _violation("product_future_evidence_invalid")

    return ProductPhase(
        identifier=identifier,
        status=status,
        branch=branch,
        dependencies=dependencies,
        accepted_sha=accepted_sha,
    )


def validate_product_state(
    repository_root: Path,
    *,
    expected_sha: str,
    head_ref: str,
    actual_sha: str | None = None,
    ancestor_check: Callable[[str, str], bool] | None = None,
) -> tuple[ProductPhase, ...]:
    """Validate exact-revision G-series state without mutating repository data."""

    root = repository_root.resolve()
    if SHA_PATTERN.fullmatch(expected_sha) is None:
        raise _violation("product_expected_sha_invalid")
    exact_sha = (
        actual_sha
        or subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    )
    if exact_sha != expected_sha:
        raise _violation("product_exact_head_mismatch")
    branch_match = PRODUCT_BRANCH_PATTERN.fullmatch(head_ref)
    if branch_match is None:
        raise _violation("product_branch_invalid")
    branch_phase = branch_match.group("phase").upper()

    state = _load_json(root / STATE_PATH)
    base_state_fields = {
        "schema_version",
        "program",
        "mission_dod",
        "execution_dod",
        "active_phase",
        "engineering_claim_only",
        "validation_track_remains_external",
        "required_checks",
        "phases",
    }
    state_fields = set(state)
    full_stack_bridge = "full_stack_product_state" in state
    expected_fields = (
        base_state_fields | {"full_stack_product_state"}
        if full_stack_bridge
        else base_state_fields
    )
    if state_fields != expected_fields:
        raise _violation("product_state_fields_invalid")
    if full_stack_bridge:
        full_stack_state = _string(
            state["full_stack_product_state"],
            "product_full_stack_state_invalid",
        )
        if full_stack_state != FULL_STACK_STATE_PATH.as_posix():
            raise _violation("product_full_stack_state_invalid")
        _validate_evidence_paths(
            root,
            [full_stack_state],
            "product_full_stack_state_invalid",
        )
    if state["schema_version"] != 1 or state["program"] != "mission-aligned-product-completion":
        raise _violation("product_state_schema_invalid")
    if (
        state["engineering_claim_only"] is not True
        or state["validation_track_remains_external"] is not True
    ):
        raise _violation("product_claim_boundary_invalid")
    if tuple(_strings(state["required_checks"], "product_checks_invalid")) != REQUIRED_CHECKS:
        raise _violation("product_checks_invalid")
    for key in ("mission_dod", "execution_dod"):
        _validate_evidence_paths(
            root,
            [_string(state[key], "product_dod_path_invalid")],
            "product_dod_path_invalid",
        )

    active_phase = _string(state["active_phase"], "product_active_phase_invalid")
    if active_phase not in PHASE_IDS or active_phase != branch_phase:
        raise _violation("product_branch_phase_mismatch")
    phase_values = _sequence(state["phases"], "product_phases_invalid")
    if len(phase_values) != len(PHASE_IDS):
        raise _violation("product_phase_set_invalid")
    g09_raw = _mapping(phase_values[-1], "product_phase_invalid")
    if full_stack_bridge:
        if g09_raw.get("next_phase") != "P01":
            raise _violation("product_full_stack_handoff_invalid")
    elif g09_raw.get("next_phase") is not None:
        raise _violation("product_full_stack_handoff_invalid")
    phases = tuple(
        _parse_phase(
            _mapping(raw, "product_phase_invalid"),
            identifier=identifier,
            root=root,
            active_phase=active_phase,
        )
        for identifier, raw in zip(PHASE_IDS, phase_values, strict=True)
    )
    active_index = PHASE_IDS.index(active_phase)
    if any(phase.status != "PASSED" for phase in phases[:active_index]):
        raise _violation("product_dependency_not_passed")
    if any(phase.status != "NOT_STARTED" for phase in phases[active_index + 1 :]):
        raise _violation("product_phase_skip_invalid")
    if phases[active_index].branch != head_ref:
        raise _violation("product_active_branch_mismatch")

    checker = ancestor_check
    if checker is None:

        def checker(ancestor: str, descendant: str) -> bool:
            return (
                subprocess.run(
                    ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                    cwd=root,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                ).returncode
                == 0
            )

    for phase in phases[:active_index]:
        if phase.accepted_sha is None or not checker(phase.accepted_sha, exact_sha):
            raise _violation("product_passed_sha_not_ancestor")
    return phases


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the adaptive G-series product DoD state")
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    try:
        phases = validate_product_state(
            args.repository_root,
            expected_sha=args.expected_sha,
            head_ref=args.head_ref,
        )
    except (OSError, subprocess.SubprocessError, ProductGateViolation) as error:
        code = (
            str(error) if isinstance(error, ProductGateViolation) else "product_gate_runtime_error"
        )
        print(json.dumps({"status": "failed", "code": code}, sort_keys=True))
        return 1
    active = next(phase.identifier for phase in phases if phase.status in ACTIVE_STATUSES)
    print(json.dumps({"status": "passed", "active_phase": active}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
