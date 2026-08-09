from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_learning_platform_api.automation import product_gate

_HEAD_SHA = "9" * 40
_HEAD_REF = "product/g09-integration-hardening"
_ACCEPTED_SHA = "8" * 40
_FULL_STACK_PATH = "plans/full-stack-product-state.json"


def _phase(identifier: str) -> dict[str, object]:
    index = int(identifier[1:])
    active = identifier == "G09"
    return {
        "id": identifier,
        "name": f"Phase {identifier}",
        "status": "VALIDATING" if active else "PASSED",
        "branch": _HEAD_REF if active else "main",
        "dependencies": [] if index == 1 else [f"G{index - 1:02d}"],
        "dod_contracts": ["D01"],
        "risk_tiers": ["A", "B", "C", "D", "E"],
        "implementation_evidence": [f"evidence/{identifier}-implementation.txt"],
        "test_evidence": [f"evidence/{identifier}-test.txt"],
        "human_simulations": ["returning learner"],
        "human_simulation_evidence": [f"evidence/{identifier}-human.txt"],
        "accepted_sha": None if active else _ACCEPTED_SHA,
        "production_acceptance": [] if active else ["exact-main deployment passed"],
        "next_phase": "P01" if active else f"G{index + 1:02d}",
    }


def _state() -> dict[str, object]:
    return {
        "schema_version": 1,
        "program": "mission-aligned-product-completion",
        "mission_dod": "plans/product-completion-definition-of-done.md",
        "execution_dod": "plans/adaptive-product-definition-of-done.md",
        "active_phase": "G09",
        "engineering_claim_only": True,
        "validation_track_remains_external": True,
        "required_checks": list(product_gate.REQUIRED_CHECKS),
        "phases": [_phase(identifier) for identifier in product_gate.PHASE_IDS],
        "full_stack_product_state": _FULL_STACK_PATH,
    }


def _write(root: Path, state: dict[str, object] | None = None, *, full_stack: bool = True) -> dict[str, object]:
    effective = _state() if state is None else state
    plans = root / "plans"
    evidence = root / "evidence"
    plans.mkdir(parents=True)
    evidence.mkdir(parents=True)
    (plans / "product-completion-definition-of-done.md").write_text("mission\n", encoding="utf-8")
    (plans / "adaptive-product-definition-of-done.md").write_text("execution\n", encoding="utf-8")
    if full_stack:
        (plans / "full-stack-product-state.json").write_text("{}\n", encoding="utf-8")
    for identifier in product_gate.PHASE_IDS:
        for suffix in ("implementation", "test", "human"):
            (evidence / f"{identifier}-{suffix}.txt").write_text("evidence\n", encoding="utf-8")
    (root / product_gate.STATE_PATH).write_text(json.dumps(effective), encoding="utf-8")
    return effective


def _validate(root: Path) -> tuple[product_gate.ProductPhase, ...]:
    return product_gate.validate_product_state(
        root,
        expected_sha=_HEAD_SHA,
        head_ref=_HEAD_REF,
        actual_sha=_HEAD_SHA,
        ancestor_check=lambda _ancestor, _descendant: True,
    )


def _g09(state: dict[str, object]) -> dict[str, object]:
    phases = state["phases"]
    assert isinstance(phases, list)
    phase = phases[-1]
    assert isinstance(phase, dict)
    return phase


def test_full_stack_handoff_accepts_only_exact_g09_to_p01_bridge(tmp_path: Path) -> None:
    _write(tmp_path)

    phases = _validate(tmp_path)

    assert phases[-1].identifier == "G09"
    assert phases[-1].status == "VALIDATING"
    assert phases[-1].branch == _HEAD_REF


@pytest.mark.parametrize("pointer", [123, "plans/other-state.json", "../full-stack-product-state.json"])
def test_full_stack_pointer_is_exact_and_typed(tmp_path: Path, pointer: object) -> None:
    state = _write(tmp_path)
    state["full_stack_product_state"] = pointer
    (tmp_path / product_gate.STATE_PATH).write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(product_gate.ProductGateViolation, match="product_full_stack_state_invalid"):
        _validate(tmp_path)


def test_full_stack_pointer_must_resolve_to_existing_repository_file(tmp_path: Path) -> None:
    _write(tmp_path, full_stack=False)

    with pytest.raises(product_gate.ProductGateViolation, match="product_full_stack_state_invalid"):
        _validate(tmp_path)


def test_g09_cannot_handoff_to_p01_without_full_stack_state_pointer(tmp_path: Path) -> None:
    state = _write(tmp_path)
    state.pop("full_stack_product_state")
    (tmp_path / product_gate.STATE_PATH).write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(product_gate.ProductGateViolation, match="product_full_stack_handoff_invalid"):
        _validate(tmp_path)


def test_full_stack_pointer_requires_g09_p01_handoff(tmp_path: Path) -> None:
    state = _write(tmp_path)
    _g09(state)["next_phase"] = None
    (tmp_path / product_gate.STATE_PATH).write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(product_gate.ProductGateViolation, match="product_full_stack_handoff_invalid"):
        _validate(tmp_path)


def test_g09_rejects_unknown_next_phase_even_without_bridge_pointer(tmp_path: Path) -> None:
    state = _write(tmp_path)
    state.pop("full_stack_product_state")
    _g09(state)["next_phase"] = "P02"
    (tmp_path / product_gate.STATE_PATH).write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(product_gate.ProductGateViolation, match="product_full_stack_handoff_invalid"):
        _validate(tmp_path)


def test_full_stack_bridge_still_rejects_any_other_root_field(tmp_path: Path) -> None:
    state = _write(tmp_path)
    state["terminal"] = True
    (tmp_path / product_gate.STATE_PATH).write_text(json.dumps(state), encoding="utf-8")

    with pytest.raises(product_gate.ProductGateViolation, match="product_state_fields_invalid"):
        _validate(tmp_path)
