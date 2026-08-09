from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_learning_platform_api.automation import full_stack_gate

_HEAD_SHA = "a" * 40
_HEAD_REF = "product/p01-identity-account-sessions"


def _state() -> dict[str, object]:
    phases: list[dict[str, object]] = []
    for index, identifier in enumerate(full_stack_gate.PHASE_IDS):
        phases.append(
            {
                "id": identifier,
                "name": f"Phase {identifier}",
                "status": "IMPLEMENTING" if index == 0 else "LOCKED",
                "branch": _HEAD_REF if index == 0 else None,
                "dependencies": ["G09"] if index == 0 else [full_stack_gate.PHASE_IDS[index - 1]],
            }
        )
    return {
        "schema_version": 1,
        "program": "full-stack-product-completion",
        "definition_of_done": "plans/full-stack-product-definition-of-done.md",
        "engineering_kernel": {
            "program": "G01-G09",
            "status": "PASSED",
            "accepted_g09_sha": "b" * 40,
            "production_main_sha": "c" * 40,
            "production_run_id": 123,
            "terminal_for_product": False,
        },
        "external_validation_remains_separate": True,
        "full_stack_product_complete": False,
        "required_checks": list(full_stack_gate.REQUIRED_CHECKS),
        "active_phase": "P01",
        "phases": phases,
        "terminal_acceptance": {
            "state": "NOT_ELIGIBLE",
            "requires": ["P01-P08 all passed"],
        },
    }


def _write(root: Path, state: dict[str, object]) -> None:
    plans = root / "plans"
    plans.mkdir(parents=True)
    (plans / "full-stack-product-definition-of-done.md").write_text("DoD\n", encoding="utf-8")
    (plans / "full-stack-product-state.json").write_text(json.dumps(state), encoding="utf-8")


def _validate(root: Path, state: dict[str, object]) -> tuple[full_stack_gate.FullStackPhase, ...]:
    _write(root, state)
    return full_stack_gate.validate_full_stack_state(
        root,
        expected_sha=_HEAD_SHA,
        actual_sha=_HEAD_SHA,
        head_ref=_HEAD_REF,
    )


def test_p01_active_state_passes(tmp_path: Path) -> None:
    phases = _validate(tmp_path, _state())
    assert phases[0].identifier == "P01"
    assert phases[0].status == "IMPLEMENTING"


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda state: state.update(full_stack_product_complete=True), "full_stack_premature_completion"),
        (lambda state: state.update(external_validation_remains_separate=False), "full_stack_validation_boundary_invalid"),
        (lambda state: state.update(active_phase="P02"), "full_stack_branch_phase_mismatch"),
        (lambda state: state["engineering_kernel"].update(status="BRIDGING"), "full_stack_kernel_not_passed"),
        (lambda state: state["engineering_kernel"].update(terminal_for_product=True), "full_stack_kernel_terminal_invalid"),
    ],
)
def test_full_stack_gate_fails_closed(tmp_path: Path, mutate: object, code: str) -> None:
    state = _state()
    assert callable(mutate)
    mutate(state)
    with pytest.raises(full_stack_gate.FullStackGateViolation, match=code):
        _validate(tmp_path, state)


def test_future_phase_cannot_start_early(tmp_path: Path) -> None:
    state = _state()
    phases = state["phases"]
    assert isinstance(phases, list)
    p02 = phases[1]
    assert isinstance(p02, dict)
    p02.update(status="IMPLEMENTING", branch="product/p02-role-admin")
    with pytest.raises(full_stack_gate.FullStackGateViolation, match="full_stack_future_phase_invalid"):
        _validate(tmp_path, state)


def test_active_branch_must_match_state(tmp_path: Path) -> None:
    state = _state()
    phases = state["phases"]
    assert isinstance(phases, list)
    p01 = phases[0]
    assert isinstance(p01, dict)
    p01["branch"] = "product/p01-other"
    with pytest.raises(full_stack_gate.FullStackGateViolation, match="full_stack_active_branch_mismatch"):
        _validate(tmp_path, state)


def test_unknown_root_field_is_rejected(tmp_path: Path) -> None:
    state = _state()
    state["done"] = True
    with pytest.raises(full_stack_gate.FullStackGateViolation, match="full_stack_state_fields_invalid"):
        _validate(tmp_path, state)
