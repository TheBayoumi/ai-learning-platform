"""Fail-closed exact-revision gate for the P01-P08 full-stack product program."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

STATE_PATH: Final = Path("plans/full-stack-product-state.json")
PHASE_IDS: Final = tuple(f"P{index:02d}" for index in range(1, 9))
REQUIRED_CHECKS: Final = (
    "API quality",
    "Web quality",
    "Runtime smoke",
    "Phase gate",
    "Gate projection",
)
ACTIVE_STATUSES: Final = frozenset(
    {"IMPLEMENTING", "VALIDATING", "FAILED_RETRYABLE", "BLOCKED_EXTERNAL"}
)
SHA_PATTERN: Final = re.compile(r"^[0-9a-f]{40}$")
BRANCH_PATTERN: Final = re.compile(r"^product/(?P<phase>p0[1-8])-[a-z0-9][a-z0-9-]*$")


class FullStackGateViolation(RuntimeError):
    """Stable fail-closed full-stack gate code."""


@dataclass(frozen=True, slots=True)
class FullStackPhase:
    identifier: str
    status: str
    branch: str | None


def _violation(code: str) -> FullStackGateViolation:
    return FullStackGateViolation(code)


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


def _load(path: Path) -> dict[str, object]:
    if not path.is_file() or path.stat().st_size > 131_072:
        raise _violation("full_stack_state_missing_or_oversized")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _violation("full_stack_state_invalid_json") from error
    return _mapping(raw, "full_stack_state_invalid")


def _validate_kernel(raw: Mapping[str, object]) -> None:
    _exact_keys(
        raw,
        {
            "program",
            "status",
            "accepted_g09_sha",
            "production_main_sha",
            "production_run_id",
            "terminal_for_product",
        },
        "full_stack_kernel_fields_invalid",
    )
    if raw["program"] != "G01-G09" or raw["status"] != "PASSED":
        raise _violation("full_stack_kernel_not_passed")
    for key in ("accepted_g09_sha", "production_main_sha"):
        if SHA_PATTERN.fullmatch(_string(raw[key], "full_stack_kernel_sha_invalid")) is None:
            raise _violation("full_stack_kernel_sha_invalid")
    if not isinstance(raw["production_run_id"], int) or raw["production_run_id"] <= 0:
        raise _violation("full_stack_kernel_run_invalid")
    if raw["terminal_for_product"] is not False:
        raise _violation("full_stack_kernel_terminal_invalid")


def _parse_phase(raw: Mapping[str, object], identifier: str, active_phase: str) -> FullStackPhase:
    _exact_keys(raw, {"id", "name", "status", "branch", "dependencies"}, "full_stack_phase_fields_invalid")
    if raw["id"] != identifier:
        raise _violation("full_stack_phase_order_invalid")
    _string(raw["name"], "full_stack_phase_name_invalid")
    status = _string(raw["status"], "full_stack_phase_status_invalid")
    branch = _optional_string(raw["branch"], "full_stack_phase_branch_invalid")
    index = PHASE_IDS.index(identifier)
    expected_dependencies = ["G09"] if index == 0 else [PHASE_IDS[index - 1]]
    if _strings(raw["dependencies"], "full_stack_phase_dependencies_invalid") != expected_dependencies:
        raise _violation("full_stack_phase_dependencies_invalid")

    if identifier == active_phase:
        if status not in ACTIVE_STATUSES or branch is None:
            raise _violation("full_stack_active_phase_invalid")
    elif index < PHASE_IDS.index(active_phase):
        if status != "PASSED" or branch != "main":
            raise _violation("full_stack_previous_phase_invalid")
    else:
        if status != "LOCKED" or branch is not None:
            raise _violation("full_stack_future_phase_invalid")
    return FullStackPhase(identifier=identifier, status=status, branch=branch)


def validate_full_stack_state(
    repository_root: Path,
    *,
    expected_sha: str,
    head_ref: str,
    actual_sha: str | None = None,
) -> tuple[FullStackPhase, ...]:
    """Validate the active P-phase against one exact repository revision."""
    root = repository_root.resolve()
    if SHA_PATTERN.fullmatch(expected_sha) is None:
        raise _violation("full_stack_expected_sha_invalid")
    exact_sha = actual_sha or subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    if exact_sha != expected_sha:
        raise _violation("full_stack_exact_head_mismatch")
    branch_match = BRANCH_PATTERN.fullmatch(head_ref)
    if branch_match is None:
        raise _violation("full_stack_branch_invalid")
    branch_phase = branch_match.group("phase").upper()

    state = _load(root / STATE_PATH)
    _exact_keys(
        state,
        {
            "schema_version",
            "program",
            "definition_of_done",
            "engineering_kernel",
            "external_validation_remains_separate",
            "full_stack_product_complete",
            "required_checks",
            "active_phase",
            "phases",
            "terminal_acceptance",
        },
        "full_stack_state_fields_invalid",
    )
    if state["schema_version"] != 1 or state["program"] != "full-stack-product-completion":
        raise _violation("full_stack_state_schema_invalid")
    if state["external_validation_remains_separate"] is not True:
        raise _violation("full_stack_validation_boundary_invalid")
    if state["full_stack_product_complete"] is not False:
        raise _violation("full_stack_premature_completion")
    if tuple(_strings(state["required_checks"], "full_stack_checks_invalid")) != REQUIRED_CHECKS:
        raise _violation("full_stack_checks_invalid")
    dod_path = Path(_string(state["definition_of_done"], "full_stack_dod_invalid"))
    if dod_path.is_absolute() or not (root / dod_path).is_file():
        raise _violation("full_stack_dod_invalid")
    _validate_kernel(_mapping(state["engineering_kernel"], "full_stack_kernel_invalid"))

    active_phase = _string(state["active_phase"], "full_stack_active_phase_invalid")
    if active_phase not in PHASE_IDS or active_phase != branch_phase:
        raise _violation("full_stack_branch_phase_mismatch")
    phase_values = _sequence(state["phases"], "full_stack_phases_invalid")
    if len(phase_values) != len(PHASE_IDS):
        raise _violation("full_stack_phase_set_invalid")
    phases = tuple(
        _parse_phase(_mapping(raw, "full_stack_phase_invalid"), identifier, active_phase)
        for identifier, raw in zip(PHASE_IDS, phase_values, strict=True)
    )
    if phases[PHASE_IDS.index(active_phase)].branch != head_ref:
        raise _violation("full_stack_active_branch_mismatch")

    terminal = _mapping(state["terminal_acceptance"], "full_stack_terminal_invalid")
    _exact_keys(terminal, {"state", "requires"}, "full_stack_terminal_fields_invalid")
    if terminal["state"] != "NOT_ELIGIBLE" or not _strings(
        terminal["requires"], "full_stack_terminal_invalid"
    ):
        raise _violation("full_stack_terminal_invalid")
    return phases


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the P01-P08 full-stack product state")
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    try:
        phases = validate_full_stack_state(
            args.repository_root,
            expected_sha=args.expected_sha,
            head_ref=args.head_ref,
        )
    except (OSError, subprocess.SubprocessError, FullStackGateViolation) as error:
        code = str(error) if isinstance(error, FullStackGateViolation) else "full_stack_gate_runtime_error"
        print(json.dumps({"status": "failed", "code": code}, sort_keys=True))
        return 1
    active = next(phase.identifier for phase in phases if phase.status in ACTIVE_STATUSES)
    print(json.dumps({"status": "passed", "active_phase": active}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
