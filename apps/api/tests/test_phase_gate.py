"""Adversarial contracts for the deterministic GitHub phase gate."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from ai_learning_platform_api.automation import phase_gate

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXACT_SHA = "a" * 40
SUCCESS_RESULTS = (
    "API quality=success",
    "Web quality=success",
    "Runtime smoke=success",
    "Phase gate=success",
)


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def _copy_controller_fixture(destination: Path) -> Path:
    root = destination / "repository"
    policy = _read_json(REPOSITORY_ROOT / phase_gate.POLICY_PATH)
    state_path = REPOSITORY_ROOT / cast(dict[str, str], policy["sources"])["state"]
    state = _read_json(state_path)
    paths = {
        phase_gate.POLICY_PATH.as_posix(),
        *cast(dict[str, str], policy["sources"]).values(),
        *cast(dict[str, str], state["authoritative_file_hashes"]).keys(),
    }
    for relative in paths:
        source = REPOSITORY_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return root


@pytest.fixture
def controller_root(tmp_path: Path) -> Path:
    return _copy_controller_fixture(tmp_path)


def _refresh_hash(root: Path, relative: str) -> None:
    state_path = root / "plans/autonomous-loop/state.json"
    state = _read_json(state_path)
    hashes = cast(dict[str, str], state["authoritative_file_hashes"])
    hashes[relative] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    _write_json(state_path, state)


def _mutate_json(
    root: Path,
    relative: str,
    mutation: Callable[[dict[str, Any]], object],
    *,
    refresh_hash: bool = True,
) -> None:
    path = root / relative
    value = _read_json(path)
    mutation(value)
    _write_json(path, value)
    if refresh_hash and relative != "plans/autonomous-loop/state.json":
        _refresh_hash(root, relative)


def _mutate_text(
    root: Path,
    relative: str,
    mutation: Callable[[str], str],
    *,
    refresh_hash: bool = True,
) -> None:
    path = root / relative
    path.write_text(mutation(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    if refresh_hash:
        _refresh_hash(root, relative)


def _phase(inventory: dict[str, Any], identifier: str) -> dict[str, Any]:
    phases = cast(list[dict[str, Any]], inventory["phases"])
    return next(item for item in phases if item["id"] == identifier)


def _validate(root: Path, *, ancestor: bool = True) -> phase_gate.RepositoryModel:
    return phase_gate.validate_repository(
        root,
        EXACT_SHA,
        actual_sha=EXACT_SHA,
        clean_check=lambda: True,
        ancestor_check=lambda _ancestor, _descendant: ancestor,
    )


def _assert_violation(root: Path, code: str) -> None:
    with pytest.raises(phase_gate.GateViolation, match=f"^{code}$"):
        _validate(root)


def _retarget_active_foundation(value: dict[str, Any], identifier: str) -> None:
    value["active_phase"] = identifier
    cast(dict[str, Any], value["foundation_track"])["active_phase"] = identifier


def _projection_model(
    model: phase_gate.RepositoryModel,
    *,
    status: str,
    pending_entries: tuple[str, ...],
    blocker_ids: tuple[str, ...],
    missing_outputs: tuple[str, ...],
) -> phase_gate.RepositoryModel:
    state = cast(dict[str, Any], json.loads(json.dumps(model.state)))
    foundation = cast(dict[str, Any], state["foundation_track"])
    foundation["status"] = status
    active_phase = cast(str, foundation["active_phase"])
    phases = dict(model.phases)
    phases[active_phase] = replace(
        phases[active_phase],
        status="PASSED" if status == "PHASE_PASSED" else "IMPLEMENTED_UNVERIFIED",
        pending_entries=pending_entries,
        blocker_ids=blocker_ids,
        missing_outputs=missing_outputs,
    )
    return replace(model, state=state, phases=phases)


def test_known_good_fixture_projects_deterministically_without_mutation(
    controller_root: Path, tmp_path: Path
) -> None:
    before = {
        path.relative_to(controller_root): path.read_bytes()
        for path in controller_root.rglob("*")
        if path.is_file()
    }

    model = _validate(controller_root)
    transition_model = _projection_model(
        model,
        status="IMPLEMENTED_UNVERIFIED",
        pending_entries=(model.policy.implementation_pending_condition,),
        blocker_ids=tuple(model.policy.implementation_transition_blockers),
        missing_outputs=model.policy.implementation_transition_missing_outputs,
    )
    waiting = phase_gate.build_projection(transition_model)
    accepted = phase_gate.build_projection(
        transition_model, SUCCESS_RESULTS, require_check_results=True
    )

    assert waiting.upstream_success is False
    assert waiting.payload["autonomous_acceptance"] == {
        "eligible": False,
        "reason_codes": ["CHECK_RESULTS_NOT_SUPPLIED"],
    }
    assert accepted.upstream_success is True
    assert accepted.payload["commit_sha"] == EXACT_SHA
    assert accepted.payload["passed_prerequisite_chain"] == ["F00", "F01", "F02", "F03"]
    assert accepted.payload["next_action"] == {
        "code": "CREATE_ACCEPTANCE_STATE_REVISION",
        "kind": "acceptance",
        "phase": "F04",
    }
    assert (
        accepted.as_json()
        == phase_gate.build_projection(
            transition_model, SUCCESS_RESULTS, require_check_results=True
        ).as_json()
    )
    summary = phase_gate.render_step_summary(accepted)
    assert summary == phase_gate.render_step_summary(accepted)
    assert f"Exact commit: `{EXACT_SHA}`" in summary
    assert "v00.symmetric_demand" in summary

    summary_path = tmp_path / "summary.md"
    phase_gate._append_summary(controller_root, summary_path, summary)
    assert summary_path.read_text(encoding="utf-8") == summary
    with pytest.raises(phase_gate.GateViolation, match=r"^summary_path_invalid$"):
        phase_gate._append_summary(controller_root, controller_root / "summary.md", summary)

    after = {
        path.relative_to(controller_root): path.read_bytes()
        for path in controller_root.rglob("*")
        if path.is_file()
    }
    assert after == before


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b'{"a": 1, "a": 2}\n', "json_duplicate_key"),
        (b'{"a": NaN}\n', "json_non_finite_number"),
        (b"{broken}\n", "sample_invalid"),
        (b'\xef\xbb\xbf{"a": 1}\n', "sample_invalid"),
        (b'{"a": "\\u0000"}\x00', "sample_invalid"),
        (b"[]\n", "sample_invalid"),
        (b"", "sample_invalid"),
        (b"\xff", "sample_invalid"),
    ],
)
def test_strict_json_rejects_malformed_inputs(tmp_path: Path, payload: bytes, code: str) -> None:
    path = tmp_path / "sample.json"
    path.write_bytes(payload)
    with pytest.raises(phase_gate.GateViolation, match=f"^{code}$"):
        phase_gate.load_json_strict(path, 1024, "sample_invalid")


def test_strict_json_enforces_size_and_object_shape(tmp_path: Path) -> None:
    path = tmp_path / "sample.json"
    path.write_text('{"ok": true}\n', encoding="utf-8")
    with pytest.raises(phase_gate.GateViolation, match=r"^sample_invalid$"):
        phase_gate.load_json_strict(path, 2, "sample_invalid")
    assert phase_gate.load_json_strict(path, 1024, "sample_invalid") == {"ok": True}


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(schema_version=2), "policy_schema_invalid"),
        (lambda value: value.update(policy_id="other"), "policy_id_invalid"),
        (lambda value: value.update(extra=True), "policy_fields_invalid"),
        (
            lambda value: cast(dict[str, Any], value["sources"]).pop("workflow"),
            "policy_sources_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["schemas"]).update(state="3"),
            "policy_schemas_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["vocabulary"]).update(lanes=["foundation"]),
            "policy_lanes_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["vocabulary"]).update(status_projection={}),
            "policy_status_projection_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["phase_rules"]).update(
                require_passed_dependencies=False
            ),
            "policy_phase_rules_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["phase_rules"]).update(
                foundation_id_pattern="["
            ),
            "policy_phase_rules_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["blocker_catalog"]).update(
                {"Bad blocker": "external"}
            ),
            "policy_blockers_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["blocker_catalog"]).update(
                {"v00.symmetric_demand": "human_decision"}
            ),
            "policy_blockers_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["claim_rules"]).update({"bad claim": []}),
            "policy_claims_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["github"]).update(required_checks=[]),
            "policy_checks_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["github"]).update(
                implementation_pending_condition="wrong"
            ),
            "policy_transition_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["github"]).update(
                implementation_transition_blockers=[]
            ),
            "policy_transition_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["github"]).update(
                implementation_transition_missing_outputs=[]
            ),
            "policy_transition_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["github"]).update(branch="other"),
            "policy_branch_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["limits"]).update(policy_bytes=2),
            "policy_limits_invalid",
        ),
        (
            lambda value: value.update(required_authoritative_hashes=["a", "a"]),
            "policy_hashes_invalid",
        ),
        (lambda value: value.update(state_claim_fields=[]), "policy_claims_invalid"),
        (
            lambda value: cast(dict[str, Any], value["claim_rules"]).update(target_selected=[]),
            "policy_claims_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["claim_rules"]).update(
                target_selected=["V99"]
            ),
            "policy_claims_invalid",
        ),
    ],
)
def test_policy_schema_fails_closed(
    controller_root: Path,
    mutation: Callable[[dict[str, Any]], object],
    code: str,
) -> None:
    _mutate_json(
        controller_root,
        phase_gate.POLICY_PATH.as_posix(),
        lambda value: mutation(value),
        refresh_hash=False,
    )
    _assert_violation(controller_root, code)


@pytest.mark.parametrize(
    ("roadmap", "code"),
    [
        ("# no phases\n", "roadmap_phase_missing"),
        (
            "### F00 - One\n\n- **Dependencies:** None.\n\n"
            "### F00 - Two\n\n- **Dependencies:** None.\n",
            "roadmap_phase_duplicate",
        ),
        ("### F00 - One\n", "roadmap_dependency_missing"),
        (
            "### F00 - One\n\n- **Dependencies:** something.\n",
            "roadmap_dependency_syntax_invalid",
        ),
        (
            "### F00 - One\n\n- **Dependencies:** `F00`.\n",
            "roadmap_dependency_unknown_or_forward",
        ),
        (
            "### F00 - One\n\n- **Dependencies:** None.\n\n"
            "### F01 - Two\n\n- **Dependencies:** `F99`.\n",
            "roadmap_dependency_unknown_or_forward",
        ),
        (
            "### F00 - One\n\n- **Dependencies:** None.\n\n"
            "### V00 - Validation\n\n- **Dependencies:** `F00`.\n",
            "roadmap_cross_lane_dependency",
        ),
        (
            "### V00 - One\n\n- **Dependencies:** None.\n\n"
            "### V01 - Two\n\n- **Dependencies:** `V01` through `V00`.\n",
            "roadmap_dependency_range_invalid",
        ),
    ],
)
def test_roadmap_dependency_language_fails_closed(
    controller_root: Path, roadmap: str, code: str
) -> None:
    policy = phase_gate.load_policy(controller_root)
    with pytest.raises(phase_gate.GateViolation, match=f"^{code}$"):
        phase_gate.parse_roadmap(roadmap, policy)


def test_roadmap_parses_ranges_all_preceding_and_horizons(controller_root: Path) -> None:
    policy = phase_gate.load_policy(controller_root)
    roadmap = phase_gate.parse_roadmap(
        (controller_root / "specs/roadmap.md").read_text(encoding="utf-8"), policy
    )
    phases = {item.identifier: item for item in roadmap}
    assert phases["V17B"].dependencies[0] == "V07"
    assert "V08R" in phases["V17B"].dependencies
    assert phases["V22"].dependencies[-1] == "V21"
    assert phases["Q2"].kind == "horizon"


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(schema_version=99), "inventory_schema_invalid"),
        (lambda value: value.update(extra=True), "inventory_fields_invalid"),
        (
            lambda value: cast(dict[str, Any], value["repository"]).update(branch="wrong"),
            "inventory_branch_invalid",
        ),
        (lambda value: _phase(value, "F03").update(name="Wrong"), "roadmap_inventory_disagreement"),
        (lambda value: _phase(value, "F03").update(status="UNKNOWN"), "inventory_status_invalid"),
        (
            lambda value: _phase(value, "V01").update(gate_decision="Continue"),
            "nonterminal_gate_present",
        ),
        (
            lambda value: _phase(value, "F00").update(gate_decision="Revise"),
            "passed_gate_not_continue",
        ),
        (
            lambda value: _phase(value, "V00").update(blocker_ids=["unknown"]),
            "inventory_blockers_invalid",
        ),
        (
            lambda value: _phase(value, "V00").update(human_decisions=["approval"]),
            "external_blocker_projection_invalid",
        ),
        (
            lambda value: _phase(value, "F03").update(claims=["target_selected"]),
            "foundation_human_or_claim_invalid",
        ),
        (
            lambda value: _phase(value, "Q2").update(status="IN_PROGRESS"),
            "horizon_progress_invalid",
        ),
        (
            lambda value: cast(list[dict[str, Any]], value["phases"]).pop(),
            "roadmap_inventory_phase_set_disagreement",
        ),
    ],
)
def test_inventory_schema_and_vocabulary_fail_closed(
    controller_root: Path,
    mutation: Callable[[dict[str, Any]], object],
    code: str,
) -> None:
    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        lambda value: mutation(value),
    )
    _assert_violation(controller_root, code)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: cast(list[dict[str, Any]], _phase(value, "F03")["entry_conditions"])[
                0
            ].update(result="FAILED"),
            "passed_entry_failed_or_pending",
        ),
        (
            lambda value: _phase(value, "F03").update(missing_outputs=["missing"]),
            "passed_evidence_incomplete",
        ),
        (
            lambda value: _phase(value, "F03").update(implemented_files=[]),
            "passed_evidence_incomplete",
        ),
        (
            lambda value: _phase(value, "F03").update(tests=[]),
            "passed_evidence_incomplete",
        ),
    ],
)
def test_passed_phase_requires_complete_evidence(
    controller_root: Path,
    mutation: Callable[[dict[str, Any]], object],
    code: str,
) -> None:
    def make_passed(value: dict[str, Any]) -> None:
        phase = _phase(value, "F03")
        phase["status"] = "PASSED"
        phase["gate_decision"] = "Continue"
        phase["missing_outputs"] = []
        phase["blocker_ids"] = []
        for entry in cast(list[dict[str, Any]], phase["entry_conditions"]):
            entry["result"] = "PASSED"
            entry["evidence"] = ["fixed evidence"]
        mutation(value)

    _mutate_json(controller_root, "plans/implementation-inventory.json", make_passed)
    _assert_violation(controller_root, code)


def test_dependency_closure_and_lane_effects_fail_closed(controller_root: Path) -> None:
    def break_dependency(value: dict[str, Any]) -> None:
        _phase(value, "F02")["status"] = "IN_PROGRESS"
        _phase(value, "F02")["gate_decision"] = None

    _mutate_json(controller_root, "plans/implementation-inventory.json", break_dependency)
    _assert_violation(controller_root, "dependency_not_passed")

    controller_root = _copy_controller_fixture(controller_root.parent / "second")

    def add_effect(value: dict[str, Any]) -> None:
        cast(dict[str, list[str]], _phase(value, "F03")["gate_effects"])["satisfies"] = ["V00"]

    _mutate_json(controller_root, "plans/implementation-inventory.json", add_effect)
    _assert_violation(controller_root, "foundation_validation_effect_invalid")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(schema_version=2), "state_schema_invalid"),
        (lambda value: value.update(status="RUNNING"), "state_controller_status_disagreement"),
        (lambda value: value.update(active_phase="F02"), "state_active_phase_disagreement"),
        (
            lambda value: _retarget_active_foundation(value, "F03"),
            "state_active_phase_disagreement",
        ),
        (
            lambda value: cast(dict[str, Any], value["foundation_track"]).update(
                status="IN_PROGRESS"
            ),
            "state_inventory_status_disagreement",
        ),
        (
            lambda value: cast(dict[str, Any], value["foundation_track"]).update(
                gate_decision="Continue"
            ),
            "state_inventory_gate_disagreement",
        ),
        (
            lambda value: cast(dict[str, Any], value["implementation_inventory"]).update(
                generated_at="different"
            ),
            "state_inventory_timestamp_disagreement",
        ),
        (
            lambda value: value.update(external_blockers=["controller.implementation_checks"]),
            "state_external_blockers_invalid",
        ),
        (
            lambda value: value.update(human_decisions_required=["v00.symmetric_demand"]),
            "state_human_blockers_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["future_phase_boundary"]).update(phase="F04"),
            "state_future_boundary_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["claims"]).update(product_readiness=True),
            "unsupported_product_or_readiness_claim",
        ),
        (
            lambda value: cast(dict[str, str], value["authoritative_file_hashes"]).update(
                {"AGENTS.md": "0" * 64}
            ),
            "state_hash_mismatch",
        ),
    ],
)
def test_state_drift_and_claims_fail_closed(
    controller_root: Path,
    mutation: Callable[[dict[str, Any]], object],
    code: str,
) -> None:
    _mutate_json(
        controller_root,
        "plans/autonomous-loop/state.json",
        lambda value: mutation(value),
        refresh_hash=False,
    )
    _assert_violation(controller_root, code)


def test_authoritative_hashes_are_checkout_line_ending_stable(
    controller_root: Path,
) -> None:
    path = controller_root / "AGENTS.md"
    text = path.read_text(encoding="utf-8")
    assert "\r" not in text
    path.write_bytes(text.replace("\n", "\r\n").encode())
    _validate(controller_root)


def test_external_blockers_cannot_become_human_wait(controller_root: Path) -> None:
    def reclassify_inventory(value: dict[str, Any]) -> None:
        v00 = _phase(value, "V00")
        v00["status"] = "BLOCKED_HUMAN"
        v00["gate_decision"] = "Revise"

    _mutate_json(controller_root, "plans/implementation-inventory.json", reclassify_inventory)
    _assert_violation(controller_root, "human_blocker_class_invalid")


def test_coordinated_external_to_human_reclassification_fails_closed(
    controller_root: Path,
) -> None:
    blocker_ids = [
        "v00.symmetric_demand",
        "v00.practitioner_confirmations",
        "v00.recruitment_channel",
        "v00.measured_cost",
    ]

    def reclassify_policy(value: dict[str, Any]) -> None:
        catalog = cast(dict[str, str], value["blocker_catalog"])
        for identifier in blocker_ids:
            catalog[identifier] = "human_decision"

    def reclassify_inventory(value: dict[str, Any]) -> None:
        v00 = _phase(value, "V00")
        v00["status"] = "BLOCKED_HUMAN"
        v00["blocker_ids"] = blocker_ids
        v00["external_blockers"] = []
        v00["human_decisions"] = ["Irreversible validation decision"]

    def reclassify_state(value: dict[str, Any]) -> None:
        validation = cast(dict[str, Any], value["validation_track"])
        validation["status"] = "WAITING_HUMAN"
        validation["blocking_inputs"] = []
        value["external_blockers"] = []
        value["human_decisions_required"] = blocker_ids

    _mutate_json(
        controller_root,
        phase_gate.POLICY_PATH.as_posix(),
        reclassify_policy,
        refresh_hash=False,
    )
    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        reclassify_inventory,
    )
    _mutate_json(
        controller_root,
        "plans/autonomous-loop/state.json",
        reclassify_state,
        refresh_hash=False,
    )
    _refresh_hash(controller_root, phase_gate.POLICY_PATH.as_posix())
    _assert_violation(controller_root, "policy_blockers_invalid")


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("pull_request:", "pull_request_target:", "workflow_privilege_invalid"),
        ("contents: read", "contents: write", "workflow_privilege_invalid"),
        ("  cancel-in-progress: true\n", "", "workflow_concurrency_invalid"),
        (
            "EXACT_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}",
            "EXACT_HEAD_SHA: ${{ github.sha }}",
            "workflow_exact_head_invalid",
        ),
        ("    name: Phase gate", "    name: Other", "workflow_required_checks_invalid"),
        ("          persist-credentials: false\n", "", "workflow_checkout_credentials_invalid"),
        ("          ref: ${{ env.EXACT_HEAD_SHA }}\n", "", "workflow_checkout_ref_invalid"),
        (
            "needs: [api, web, runtime-smoke, phase-gate]",
            "needs: [phase-gate]",
            "workflow_projection_dependencies_invalid",
        ),
        (
            "scripts/phase_gate.py validate",
            "scripts/other.py validate",
            "workflow_controller_commands_invalid",
        ),
    ],
)
def test_workflow_contract_fails_closed(
    controller_root: Path, old: str, new: str, code: str
) -> None:
    _mutate_text(
        controller_root,
        ".github/workflows/ci.yml",
        lambda text: text.replace(old, new, 1),
    )
    _assert_violation(controller_root, code)


@pytest.mark.parametrize("result", ["failure", "cancelled", "skipped", "pending"])
def test_projection_rejects_every_non_success_result(controller_root: Path, result: str) -> None:
    model = _validate(controller_root)
    values = list(SUCCESS_RESULTS)
    values[0] = f"API quality={result}"
    projection = phase_gate.build_projection(model, values, require_check_results=True)
    assert projection.upstream_success is False
    acceptance = cast(dict[str, Any], projection.payload["autonomous_acceptance"])
    assert acceptance["eligible"] is False
    assert acceptance["reason_codes"] == [f"CHECK_API_QUALITY_{result.upper()}"]


@pytest.mark.parametrize(
    "values",
    [
        ("bad",),
        ("Unknown=success",),
        ("API quality=unknown",),
        ("API quality=success", "API quality=success"),
    ],
)
def test_projection_rejects_malformed_check_results(
    controller_root: Path, values: tuple[str, ...]
) -> None:
    model = _validate(controller_root)
    with pytest.raises(phase_gate.GateViolation, match=r"^check_result_invalid$"):
        phase_gate.build_projection(model, values, require_check_results=True)
    with pytest.raises(phase_gate.GateViolation, match=r"^check_result_missing$"):
        phase_gate.build_projection(model, SUCCESS_RESULTS[:-1], require_check_results=True)


def test_exact_head_worktree_and_verified_ancestor_fail_closed(controller_root: Path) -> None:
    with pytest.raises(phase_gate.GateViolation, match=r"^expected_sha_invalid$"):
        phase_gate.validate_repository(controller_root, "short", actual_sha=EXACT_SHA)
    with pytest.raises(phase_gate.GateViolation, match=r"^exact_head_mismatch$"):
        phase_gate.validate_repository(controller_root, "b" * 40, actual_sha=EXACT_SHA)
    with pytest.raises(phase_gate.GateViolation, match=r"^worktree_not_exact_head$"):
        phase_gate.validate_repository(
            controller_root,
            EXACT_SHA,
            actual_sha=EXACT_SHA,
            clean_check=lambda: False,
        )
    with pytest.raises(phase_gate.GateViolation, match=r"^state_verified_head_stale$"):
        _validate(controller_root, ancestor=False)


def test_paths_cannot_escape_repository(controller_root: Path) -> None:
    with pytest.raises(phase_gate.GateViolation, match=r"^escape$"):
        phase_gate._resolve_input(controller_root, "../outside", "escape")
    with pytest.raises(phase_gate.GateViolation, match=r"^escape$"):
        phase_gate._resolve_input(controller_root, str(controller_root.resolve()), "escape")


def test_markdown_escapes_untrusted_cells() -> None:
    projection = phase_gate.GateProjection(
        payload={
            "schema_version": 1,
            "commit_sha": "<sha>|&",
            "validation_lane": {"phase": "V00", "status": "WAITING", "gate": None},
            "foundation_lane": {"phase": "F03", "status": "READY", "gate": None},
            "passed_prerequisite_chain": [],
            "blockers": {"external": [], "technical": [], "human_decision": []},
            "next_action": {"kind": "repair", "phase": "F03", "code": "SAFE"},
            "autonomous_acceptance": {"eligible": False, "reason_codes": []},
        },
        upstream_success=False,
    )
    summary = phase_gate.render_step_summary(projection)
    assert "&lt;sha&gt;\\|&amp;" in summary
    assert "<sha>" not in summary


def test_cli_success_failure_and_safe_io_error(
    controller_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(phase_gate, "_git_head", lambda _root: EXACT_SHA)
    monkeypatch.setattr(phase_gate, "_git_worktree_clean", lambda _root: True)
    monkeypatch.setattr(phase_gate, "_git_is_ancestor", lambda _root, _a, _d: True)
    common = ["--repository-root", str(controller_root), "--expected-sha", EXACT_SHA]
    assert phase_gate.main(["validate", *common]) == 0
    assert "valid exact head" in capsys.readouterr().out

    summary_path = tmp_path / "cli-summary.md"
    project = [
        "project",
        *common,
        *(part for value in SUCCESS_RESULTS for part in ("--check-result", value)),
        "--require-check-results",
        "--github-summary",
        str(summary_path),
    ]
    assert phase_gate.main(project) == 0
    assert json.loads(capsys.readouterr().out)["commit_sha"] == EXACT_SHA
    assert summary_path.is_file()

    assert phase_gate.main(["validate", *common[:-1], "short"]) == 1
    assert "expected_sha_invalid" in capsys.readouterr().err
    monkeypatch.setattr(phase_gate, "_git_head", lambda _root: (_ for _ in ()).throw(OSError()))
    assert phase_gate.main(["validate", *common]) == 1
    assert capsys.readouterr().err == "phase-gate-error: controller_io_failure\n"


def test_private_type_and_timestamp_guards_fail_closed() -> None:
    with pytest.raises(phase_gate.GateViolation, match=r"^bad_sequence$"):
        phase_gate._sequence("not-a-list", "bad_sequence")
    with pytest.raises(phase_gate.GateViolation, match=r"^bad_string$"):
        phase_gate._string("", "bad_string")
    with pytest.raises(phase_gate.GateViolation, match=r"^bad_strings$"):
        phase_gate._string_list(["ok", 1], "bad_strings")
    with pytest.raises(phase_gate.GateViolation, match=r"^bad_map$"):
        phase_gate._policy_string_map({"key": 1}, "bad_map")
    with pytest.raises(phase_gate.GateViolation, match=r"^bad_time$"):
        phase_gate._timestamp("2026-07-16T00:00:00+00:00", "bad_time")
    with pytest.raises(phase_gate.GateViolation, match=r"^bad_time$"):
        phase_gate._timestamp("not-a-timeZ", "bad_time")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: cast(dict[str, Any], value["vocabulary"]).update(
                controller_projection={}
            ),
            "policy_controller_projection_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["vocabulary"])["controller_projection"].update(
                {"NOT_STARTED": "UNKNOWN"}
            ),
            "policy_controller_projection_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["phase_rules"]).update(
                validation_lock_roots=["V00"]
            ),
            "policy_phase_rules_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["sources"]).update(roadmap="../outside.md"),
            "roadmap_path_invalid",
        ),
    ],
)
def test_additional_policy_guards(
    controller_root: Path,
    mutation: Callable[[dict[str, Any]], object],
    code: str,
) -> None:
    _mutate_json(
        controller_root,
        phase_gate.POLICY_PATH.as_posix(),
        lambda value: mutation(value),
        refresh_hash=False,
    )
    _assert_violation(controller_root, code)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (
            lambda value: _phase(value, "F03").update(gate_decision="Unknown"),
            "inventory_gate_invalid",
        ),
        (
            lambda value: cast(list[dict[str, Any]], _phase(value, "F03")["entry_conditions"])[
                0
            ].update(result="UNKNOWN"),
            "inventory_entry_result_invalid",
        ),
        (
            lambda value: cast(list[dict[str, Any]], _phase(value, "F03")["entry_conditions"])[
                0
            ].update(evidence=[]),
            "passed_entry_evidence_missing",
        ),
        (lambda value: value.update(claims=["target_selected"]), "repository_claim_invalid"),
        (
            lambda value: _phase(value, "V00").update(
                blocker_ids=["controller.implementation_checks"]
            ),
            "external_blocker_class_invalid",
        ),
        (
            lambda value: _phase(value, "F03").update(
                status="IMPLEMENTED_UNVERIFIED",
                gate_decision=None,
                blocker_ids=["v00.symmetric_demand"],
            ),
            "foundation_blocker_class_invalid",
        ),
        (
            lambda value: _phase(value, "F00").update(
                blocker_ids=["controller.implementation_checks"]
            ),
            "passed_blockers_present",
        ),
        (
            lambda value: cast(dict[str, list[str]], _phase(value, "F03")["gate_effects"]).update(
                satisfies=["UNKNOWN"]
            ),
            "gate_effect_target_unknown",
        ),
        (
            lambda value: _phase(value, "V00").update(gate_decision=None),
            "external_gate_invalid",
        ),
    ],
)
def test_additional_inventory_guards(
    controller_root: Path,
    mutation: Callable[[dict[str, Any]], object],
    code: str,
) -> None:
    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        lambda value: mutation(value),
    )
    _assert_violation(controller_root, code)


def test_validation_lock_roots_are_enforced_independently(controller_root: Path) -> None:
    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        lambda value: _phase(value, "V01").update(status="IN_PROGRESS"),
    )
    _assert_violation(controller_root, "v00_lock_violated")

    controller_root = _copy_controller_fixture(controller_root.parent / "v01")

    def violate_v01(value: dict[str, Any]) -> None:
        v00 = _phase(value, "V00")
        v00["status"] = "PASSED"
        v00["gate_decision"] = "Continue"
        v00["missing_outputs"] = []
        v00["blocker_ids"] = []
        v00["external_blockers"] = []
        v00["tests"] = ["evidence test"]
        _phase(value, "V02")["status"] = "IN_PROGRESS"

    _mutate_json(controller_root, "plans/implementation-inventory.json", violate_v01)
    _assert_violation(controller_root, "v01_lock_violated")


def test_claim_prerequisites_are_enforced(controller_root: Path) -> None:
    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        lambda value: _phase(value, "V00").update(claims=["target_selected"]),
    )
    _assert_violation(controller_root, "claim_prerequisite_missing")


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda value: value.update(status="UNKNOWN"), "state_status_invalid"),
        (lambda value: value.update(gate_decision="Unknown"), "state_gate_invalid"),
        (
            lambda value: cast(dict[str, Any], value["validation_track"]).update(
                active_phase="F03"
            ),
            "state_track_phase_invalid",
        ),
        (
            lambda value: cast(dict[str, Any], value["foundation_track"]).update(status="UNKNOWN"),
            "state_track_status_invalid",
        ),
        (
            lambda value: value.update(gate_decision="Continue"),
            "state_controller_gate_disagreement",
        ),
        (
            lambda value: cast(dict[str, Any], value["implementation_inventory"]).update(
                path="other.json"
            ),
            "state_inventory_ref_invalid",
        ),
        (
            lambda value: value.update(last_run_started_at="2026-07-16T00:00:00.000Z"),
            "state_inventory_timestamp_disagreement",
        ),
        (
            lambda value: value.update(last_run_completed_at="2020-01-01T00:00:00.000Z"),
            "state_timestamp_order_invalid",
        ),
        (lambda value: value.update(run_number=0), "state_run_number_invalid"),
        (
            lambda value: cast(dict[str, Any], value["validation_track"]).update(
                blocking_inputs=["v00.symmetric_demand"]
            ),
            "state_external_projection_disagreement",
        ),
        (
            lambda value: cast(dict[str, str], value["authoritative_file_hashes"]).pop("AGENTS.md"),
            "state_required_hash_missing",
        ),
        (
            lambda value: cast(dict[str, str], value["authoritative_file_hashes"]).update(
                {"AGENTS.md": "invalid"}
            ),
            "state_hash_invalid",
        ),
        (
            lambda value: value.update(last_verified_commit="b" * 40),
            "state_verified_head_disagreement",
        ),
    ],
)
def test_additional_state_guards(
    controller_root: Path,
    mutation: Callable[[dict[str, Any]], object],
    code: str,
) -> None:
    _mutate_json(
        controller_root,
        "plans/autonomous-loop/state.json",
        lambda value: mutation(value),
        refresh_hash=False,
    )
    _assert_violation(controller_root, code)


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("permissions:\n  contents: read", "permissions:", "workflow_permissions_invalid"),
        (
            'branches: [main, "automation/**"]',
            "branches: [main]",
            "workflow_trigger_invalid",
        ),
        (
            "      - uses: actions/checkout@",
            "      - uses: example/other@",
            "workflow_checkout_count_invalid",
        ),
        (
            "actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e",
            "actions/setup-node@v6",
            "workflow_action_pin_invalid",
        ),
        ("  gate-projection:", "  removed-projection:", "workflow_projection_job_missing"),
        (
            '--check-result "API quality=${{ needs.api.result }}"',
            '--check-result "API quality=success"',
            "workflow_projection_result_sources_invalid",
        ),
        (
            "      - name: Validate the exact revision phase state\n",
            "      - name: Validate the exact revision phase state\n"
            "        continue-on-error: true\n",
            "workflow_controller_bypass_invalid",
        ),
        (
            "      - name: Validate the exact revision phase state\n",
            "      - name: Validate the exact revision phase state\n        if: false\n",
            "workflow_controller_bypass_invalid",
        ),
        (
            '--expected-sha "$EXACT_HEAD_SHA"',
            '--expected-sha "$EXACT_HEAD_SHA" || true',
            "workflow_controller_commands_invalid",
        ),
        ("    timeout-minutes: 5", "    timeout-minutes: 30", "workflow_job_contract_invalid"),
    ],
)
def test_additional_workflow_guards(controller_root: Path, old: str, new: str, code: str) -> None:
    _mutate_text(
        controller_root,
        ".github/workflows/ci.yml",
        lambda text: text.replace(old, new, 1),
    )
    _assert_violation(controller_root, code)


def test_projection_covers_passed_repair_and_validation_human_paths(
    controller_root: Path,
) -> None:
    model = _validate(controller_root)

    passed_model = _projection_model(
        model,
        status="PHASE_PASSED",
        pending_entries=(),
        blocker_ids=(),
        missing_outputs=(),
    )
    passed = phase_gate.build_projection(passed_model, SUCCESS_RESULTS, require_check_results=True)
    assert passed.payload["next_action"] == {
        "code": "STOP_AT_FOUNDATION_BOUNDARY",
        "kind": "stop",
        "phase": "F04",
    }

    repair_model = _projection_model(
        model,
        status="IMPLEMENTED_UNVERIFIED",
        pending_entries=("Independent verification remains pending",),
        blocker_ids=("controller.independent_verification",),
        missing_outputs=("Independent verification remains pending",),
    )
    repair = phase_gate.build_projection(repair_model, SUCCESS_RESULTS, require_check_results=True)
    acceptance = cast(dict[str, Any], repair.payload["autonomous_acceptance"])
    assert repair.payload["next_action"] == {
        "code": "REPAIR_FOUNDATION_STATE",
        "kind": "repair",
        "phase": "F04",
    }
    assert acceptance["reason_codes"] == ["IMPLEMENTATION_EVIDENCE_INCOMPLETE"]
    assert acceptance["eligible"] is False

    extra_output_model = _projection_model(
        model,
        status="IMPLEMENTED_UNVERIFIED",
        pending_entries=(model.policy.implementation_pending_condition,),
        blocker_ids=tuple(model.policy.implementation_transition_blockers),
        missing_outputs=(
            *model.policy.implementation_transition_missing_outputs,
            "Unrelated output remains missing",
        ),
    )
    extra_output_projection = phase_gate.build_projection(
        extra_output_model,
        SUCCESS_RESULTS,
        require_check_results=True,
    )
    assert extra_output_projection.payload["autonomous_acceptance"] == {
        "eligible": False,
        "reason_codes": ["IMPLEMENTATION_EVIDENCE_INCOMPLETE"],
    }

    extra_blocker_model = _projection_model(
        model,
        status="IMPLEMENTED_UNVERIFIED",
        pending_entries=(model.policy.implementation_pending_condition,),
        blocker_ids=(
            *model.policy.implementation_transition_blockers,
            "controller.independent_verification",
        ),
        missing_outputs=model.policy.implementation_transition_missing_outputs,
    )
    extra_blocker_projection = phase_gate.build_projection(
        extra_blocker_model,
        SUCCESS_RESULTS,
        require_check_results=True,
    )
    assert extra_blocker_projection.payload["autonomous_acceptance"] == {
        "eligible": False,
        "reason_codes": ["IMPLEMENTATION_EVIDENCE_INCOMPLETE"],
    }

    transition_model = _projection_model(
        model,
        status="IMPLEMENTED_UNVERIFIED",
        pending_entries=(model.policy.implementation_pending_condition,),
        blocker_ids=tuple(model.policy.implementation_transition_blockers),
        missing_outputs=model.policy.implementation_transition_missing_outputs,
    )
    validation_wait_state = cast(dict[str, Any], json.loads(json.dumps(transition_model.state)))
    validation_wait_state["human_decisions_required"] = ["validation.irreversible_decision"]
    validation_wait = phase_gate.build_projection(
        replace(transition_model, state=validation_wait_state),
        SUCCESS_RESULTS,
        require_check_results=True,
    )
    validation_acceptance = cast(dict[str, Any], validation_wait.payload["autonomous_acceptance"])
    assert validation_wait.payload["next_action"] == {
        "code": "CREATE_ACCEPTANCE_STATE_REVISION",
        "kind": "acceptance",
        "phase": "F04",
    }
    assert validation_acceptance == {"eligible": True, "reason_codes": []}
    assert cast(dict[str, Any], validation_wait.payload["blockers"])["human_decision"] == [
        "validation.irreversible_decision"
    ]


def test_valid_new_foundation_successor_projects_start_action(controller_root: Path) -> None:
    synthetic_roadmap = """### F05 - Synthetic Successor

- **Dependencies:** `F04` only.

"""
    _mutate_text(
        controller_root,
        "specs/roadmap.md",
        lambda value: value.replace(
            "## Initial Validation Sequence", synthetic_roadmap + "## Initial Validation Sequence"
        ),
    )

    def add_successor(value: dict[str, Any]) -> None:
        f04 = _phase(value, "F04")
        f04["status"] = "PASSED"
        f04["gate_decision"] = "Continue"
        f04["missing_outputs"] = []
        f04["blocker_ids"] = []
        phases = cast(list[dict[str, Any]], value["phases"])
        validation_start = next(index for index, item in enumerate(phases) if item["id"] == "V00")
        phases.insert(
            validation_start,
            {
                "id": "F05",
                "name": "Synthetic Successor",
                "lane": "foundation",
                "status": "NOT_STARTED",
                "entry_conditions": [
                    {
                        "condition": "F04 passed",
                        "result": "PASSED",
                        "evidence": ["synthetic exact F04 evidence"],
                    }
                ],
                "implemented_files": [],
                "tests": [],
                "missing_outputs": ["Synthetic implementation remains pending"],
                "external_blockers": [],
                "human_decisions": [],
                "next_smallest_action": "Start the synthetic successor",
                "gate_decision": None,
                "blocker_ids": [],
                "claims": [],
                "gate_effects": {"satisfies": [], "unlocks": [], "weakens": []},
            },
        )

    _mutate_json(controller_root, "plans/implementation-inventory.json", add_successor)

    def retarget_state(value: dict[str, Any]) -> None:
        value["status"] = "READY"
        value["active_phase"] = "F05"
        value["active_slice"] = "F05-not-started"
        value["gate_decision"] = None
        foundation = cast(dict[str, Any], value["foundation_track"])
        foundation.update(
            active_phase="F05",
            status="NOT_STARTED",
            gate_decision=None,
            next_action="Start the synthetic successor",
        )

    _mutate_json(controller_root, "plans/autonomous-loop/state.json", retarget_state)
    model = _validate(controller_root)
    projection = phase_gate.build_projection(
        model,
        SUCCESS_RESULTS,
        require_check_results=True,
    )

    assert projection.payload["foundation_lane"] == {
        "gate": None,
        "phase": "F05",
        "status": "NOT_STARTED",
    }
    assert projection.payload["next_action"] == {
        "code": "START_FOUNDATION_PHASE",
        "kind": "phase",
        "phase": "F05",
    }
    assert projection.payload["autonomous_acceptance"] == {
        "eligible": True,
        "reason_codes": [],
    }

    def fail_successor_entry(value: dict[str, Any]) -> None:
        entries = cast(list[dict[str, Any]], _phase(value, "F05")["entry_conditions"])
        entries[0]["result"] = "FAILED"

    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        fail_successor_entry,
    )
    blocked = phase_gate.build_projection(
        _validate(controller_root),
        SUCCESS_RESULTS,
        require_check_results=True,
    )
    assert blocked.payload["next_action"] == {
        "code": "AWAIT_FOUNDATION_ENTRY_CONDITIONS",
        "kind": "wait",
        "phase": "F05",
    }
    assert blocked.payload["autonomous_acceptance"] == {
        "eligible": False,
        "reason_codes": ["FOUNDATION_ENTRY_CONDITIONS_INCOMPLETE"],
    }

    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        lambda value: _phase(value, "F05").update(entry_conditions=[]),
    )
    empty_entries = phase_gate.build_projection(
        _validate(controller_root),
        SUCCESS_RESULTS,
        require_check_results=True,
    )
    assert empty_entries.payload["next_action"] == {
        "code": "AWAIT_FOUNDATION_ENTRY_CONDITIONS",
        "kind": "wait",
        "phase": "F05",
    }
    assert empty_entries.payload["autonomous_acceptance"] == {
        "eligible": False,
        "reason_codes": ["FOUNDATION_ENTRY_CONDITIONS_INCOMPLETE"],
    }


def test_failed_entry_cannot_advance_implementation_to_acceptance(
    controller_root: Path,
) -> None:
    policy = _read_json(controller_root / phase_gate.POLICY_PATH)
    github = cast(dict[str, Any], policy["github"])
    pending_condition = cast(str, github["implementation_pending_condition"])
    transition_blockers = cast(list[str], github["implementation_transition_blockers"])
    transition_outputs = cast(list[str], github["implementation_transition_missing_outputs"])

    def prepare_failed_transition(value: dict[str, Any]) -> None:
        phase = _phase(value, "F04")
        phase["status"] = "IMPLEMENTED_UNVERIFIED"
        phase["gate_decision"] = None
        phase["blocker_ids"] = transition_blockers
        phase["missing_outputs"] = transition_outputs
        entries = cast(list[dict[str, Any]], phase["entry_conditions"])
        assert len(entries) >= 2
        entries[0]["result"] = "FAILED"
        entries[1].update(
            condition=pending_condition,
            result="PENDING",
            evidence=[],
        )

    _mutate_json(
        controller_root,
        "plans/implementation-inventory.json",
        prepare_failed_transition,
    )

    def prepare_transition_state(value: dict[str, Any]) -> None:
        value["status"] = "IMPLEMENTED_UNVERIFIED"
        value["gate_decision"] = None
        value["next_action"] = "Repair the failed entry before acceptance"
        foundation = cast(dict[str, Any], value["foundation_track"])
        foundation.update(
            status="IMPLEMENTED_UNVERIFIED",
            gate_decision=None,
            next_action="Repair the failed entry before acceptance",
        )

    _mutate_json(
        controller_root,
        "plans/autonomous-loop/state.json",
        prepare_transition_state,
    )
    model = _validate(controller_root)
    projection = phase_gate.build_projection(
        model,
        SUCCESS_RESULTS,
        require_check_results=True,
    )

    assert model.phases["F04"].failed_entries
    assert projection.payload["next_action"] == {
        "code": "REPAIR_FOUNDATION_STATE",
        "kind": "repair",
        "phase": "F04",
    }
    assert projection.payload["autonomous_acceptance"] == {
        "eligible": False,
        "reason_codes": ["IMPLEMENTATION_EVIDENCE_INCOMPLETE"],
    }


def test_real_git_helpers_read_exact_local_history() -> None:
    head = phase_gate._git_head(REPOSITORY_ROOT)
    assert phase_gate.SHA_PATTERN.fullmatch(head)
    assert phase_gate._git_is_ancestor(REPOSITORY_ROOT, head, head) is True
