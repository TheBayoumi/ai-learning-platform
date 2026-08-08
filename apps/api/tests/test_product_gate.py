from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import cast

import pytest

from ai_learning_platform_api.automation import product_gate

OLD_SHA = "1" * 40
HEAD_SHA = "2" * 40
HEAD_REF = "product/g02-evidence-state"


def _phase(identifier: str, status: str) -> dict[str, object]:
    index = int(identifier[1:])
    previous = [] if index == 1 else [f"G{index - 1:02d}"]
    next_phase = None if index == 9 else f"G{index + 1:02d}"
    active = identifier == "G02"
    passed = identifier == "G01"
    return {
        "id": identifier,
        "name": f"Phase {identifier}",
        "status": status,
        "branch": "main" if passed else HEAD_REF if active else None,
        "dependencies": previous,
        "dod_contracts": ["D01"],
        "risk_tiers": ["A", "B", "C", "D", "E"],
        "implementation_evidence": (
            [f"evidence/{identifier}-implementation.txt"] if passed or active else []
        ),
        "test_evidence": (
            [f"evidence/{identifier}-test.txt"] if passed or active else []
        ),
        "human_simulations": ["returning learner"],
        "human_simulation_evidence": (
            [f"evidence/{identifier}-human.txt"] if passed or active else []
        ),
        "accepted_sha": OLD_SHA if passed else None,
        "production_acceptance": ["deployed exact-head journey"] if passed else [],
        "next_phase": next_phase,
    }


def _state() -> dict[str, object]:
    return {
        "schema_version": 1,
        "program": "mission-aligned-product-completion",
        "mission_dod": "plans/product-completion-definition-of-done.md",
        "execution_dod": "plans/adaptive-product-definition-of-done.md",
        "active_phase": "G02",
        "engineering_claim_only": True,
        "validation_track_remains_external": True,
        "required_checks": list(product_gate.REQUIRED_CHECKS),
        "phases": [
            _phase(
                identifier,
                (
                    "PASSED"
                    if identifier == "G01"
                    else "VALIDATING"
                    if identifier == "G02"
                    else "NOT_STARTED"
                ),
            )
            for identifier in product_gate.PHASE_IDS
        ],
    }


def _write_repository(
    root: Path, state: dict[str, object] | None = None
) -> dict[str, object]:
    effective = _state() if state is None else state
    plans = root / "plans"
    evidence = root / "evidence"
    plans.mkdir(parents=True)
    evidence.mkdir(parents=True)
    (plans / "product-completion-definition-of-done.md").write_text(
        "mission\n", encoding="utf-8"
    )
    (plans / "adaptive-product-definition-of-done.md").write_text(
        "execution\n", encoding="utf-8"
    )
    for identifier in ("G01", "G02"):
        for suffix in ("implementation", "test", "human"):
            (evidence / f"{identifier}-{suffix}.txt").write_text(
                "evidence\n", encoding="utf-8"
            )
    (plans / "adaptive-product-state.json").write_text(
        json.dumps(effective),
        encoding="utf-8",
    )
    return effective


def _phases(state: dict[str, object]) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], state["phases"])


def _validate(
    root: Path, **overrides: object
) -> tuple[product_gate.ProductPhase, ...]:
    expected_sha = cast(str, overrides.get("expected_sha", HEAD_SHA))
    head_ref = cast(str, overrides.get("head_ref", HEAD_REF))
    actual_sha = cast(str, overrides.get("actual_sha", HEAD_SHA))
    ancestor_result = cast(bool, overrides.get("ancestor_result", True))
    return product_gate.validate_product_state(
        root,
        expected_sha=expected_sha,
        head_ref=head_ref,
        actual_sha=actual_sha,
        ancestor_check=lambda _ancestor, _descendant: ancestor_result,
    )


def test_committed_product_state_matches_the_exact_pr_revision() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    exact_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    head_ref = os.environ.get(
        "GITHUB_HEAD_REF", "product/g02-deterministic-evidence-state"
    )

    phases = product_gate.validate_product_state(
        repository_root,
        expected_sha=exact_sha,
        head_ref=head_ref,
        actual_sha=exact_sha,
        ancestor_check=lambda _ancestor, _descendant: True,
    )

    assert phases[1].identifier == "G02"
    assert phases[1].status == "VALIDATING"


def test_valid_product_state_accepts_exact_active_phase(tmp_path: Path) -> None:
    _write_repository(tmp_path)

    phases = _validate(tmp_path)

    assert phases[0].status == "PASSED"
    assert phases[1].status == "VALIDATING"
    assert phases[1].branch == HEAD_REF


@pytest.mark.parametrize(
    ("expected_sha", "actual_sha", "code"),
    [
        ("bad", HEAD_SHA, "product_expected_sha_invalid"),
        (HEAD_SHA, "3" * 40, "product_exact_head_mismatch"),
    ],
)
def test_exact_revision_identity_fails_closed(
    tmp_path: Path,
    expected_sha: str,
    actual_sha: str,
    code: str,
) -> None:
    _write_repository(tmp_path)

    with pytest.raises(product_gate.ProductGateViolation, match=code):
        _validate(tmp_path, expected_sha=expected_sha, actual_sha=actual_sha)


def test_non_product_branch_is_rejected(tmp_path: Path) -> None:
    _write_repository(tmp_path)

    with pytest.raises(product_gate.ProductGateViolation, match="product_branch_invalid"):
        _validate(tmp_path, head_ref="feature/g02-evidence-state")


def test_branch_must_match_active_machine_phase(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    state["active_phase"] = "G03"
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_branch_phase_mismatch"
    ):
        _validate(tmp_path)


def test_claim_boundary_cannot_be_disabled(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    state["engineering_claim_only"] = False
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_claim_boundary_invalid"
    ):
        _validate(tmp_path)


def test_required_five_check_contract_is_exact(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    state["required_checks"] = ["API quality"]
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(product_gate.ProductGateViolation, match="product_checks_invalid"):
        _validate(tmp_path)


def test_prior_phase_must_be_passed(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    _phases(state)[0]["status"] = "NOT_STARTED"
    _phases(state)[0]["branch"] = None
    _phases(state)[0]["accepted_sha"] = None
    _phases(state)[0]["implementation_evidence"] = []
    _phases(state)[0]["test_evidence"] = []
    _phases(state)[0]["human_simulation_evidence"] = []
    _phases(state)[0]["production_acceptance"] = []
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_dependency_not_passed"
    ):
        _validate(tmp_path)


def test_future_phase_cannot_start_early(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    future = _phases(state)[2]
    future["status"] = "IMPLEMENTING"
    future["branch"] = "product/g03-planner"
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_future_phase_started"
    ):
        _validate(tmp_path)


def test_future_phase_cannot_preclaim_evidence(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    _phases(state)[2]["test_evidence"] = ["evidence/future.txt"]
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_future_evidence_invalid"
    ):
        _validate(tmp_path)


def test_passed_phase_requires_production_and_human_evidence(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    _phases(state)[0]["production_acceptance"] = []
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_passed_evidence_missing"
    ):
        _validate(tmp_path)


def test_active_phase_requires_executable_human_simulation(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    _phases(state)[1]["human_simulation_evidence"] = []
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_active_evidence_missing"
    ):
        _validate(tmp_path)


def test_evidence_paths_cannot_escape_repository(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    _phases(state)[1]["test_evidence"] = ["../outside.txt"]
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_evidence_path_invalid"
    ):
        _validate(tmp_path)


def test_passed_sha_must_be_ancestor_of_exact_head(tmp_path: Path) -> None:
    _write_repository(tmp_path)

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_passed_sha_not_ancestor"
    ):
        _validate(tmp_path, ancestor_result=False)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("dependencies", [], "product_phase_dependencies_invalid"),
        ("dod_contracts", ["D99"], "product_phase_dod_invalid"),
        ("risk_tiers", ["A"], "product_phase_risk_invalid"),
        ("next_phase", "G09", "product_phase_next_invalid"),
    ],
)
def test_phase_contracts_are_fail_closed(
    tmp_path: Path,
    field: str,
    value: object,
    code: str,
) -> None:
    state = _write_repository(tmp_path)
    _phases(state)[1][field] = value
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(product_gate.ProductGateViolation, match=code):
        _validate(tmp_path)


def test_state_requires_exact_fields(tmp_path: Path) -> None:
    state = _write_repository(tmp_path)
    state["unexpected"] = True
    (tmp_path / product_gate.STATE_PATH).write_text(
        json.dumps(state), encoding="utf-8"
    )

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_state_fields_invalid"
    ):
        _validate(tmp_path)


def test_invalid_json_is_rejected(tmp_path: Path) -> None:
    _write_repository(tmp_path)
    (tmp_path / product_gate.STATE_PATH).write_text("{", encoding="utf-8")

    with pytest.raises(
        product_gate.ProductGateViolation, match="product_state_invalid_json"
    ):
        _validate(tmp_path)


def test_cli_returns_stable_failure_payload(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(
        *_args: object, **_kwargs: object
    ) -> tuple[product_gate.ProductPhase, ...]:
        raise product_gate.ProductGateViolation("simulated_failure")

    monkeypatch.setattr(product_gate, "validate_product_state", fail)

    result = product_gate.main(
        ["validate", "--expected-sha", HEAD_SHA, "--head-ref", HEAD_REF]
    )

    assert result == 1
    assert json.loads(capsys.readouterr().out) == {
        "code": "simulated_failure",
        "status": "failed",
    }


def test_cli_reports_active_phase(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    phases = (
        product_gate.ProductPhase("G01", "PASSED", "main", (), OLD_SHA),
        product_gate.ProductPhase("G02", "VALIDATING", HEAD_REF, ("G01",), None),
    )
    monkeypatch.setattr(
        product_gate, "validate_product_state", lambda *_args, **_kwargs: phases
    )

    result = product_gate.main(
        ["validate", "--expected-sha", HEAD_SHA, "--head-ref", HEAD_REF]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "active_phase": "G02",
        "status": "passed",
    }
