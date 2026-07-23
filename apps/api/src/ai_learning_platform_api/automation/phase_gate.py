"""Fail-closed, non-mutating phase acceptance controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Final, cast

POLICY_PATH: Final = Path("plans/autonomous-loop/controller-policy.json")
SHA_PATTERN: Final = re.compile(r"^[0-9a-f]{40}$")
BLOCKER_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
PHASE_HEADING: Final = re.compile(
    r"^### (?P<id>[FV][0-9]{2}[A-Z]?|Q[0-9]+) (?:-|—) (?P<name>.+)$",
    re.MULTILINE,
)
DEPENDENCY_CLAUSE: Final = re.compile(
    r"^- \*\*Dependencies:\*\* (?P<value>.*?)(?=^\s*- \*\*|^### |\Z)",
    re.MULTILINE | re.DOTALL,
)


class GateViolation(RuntimeError):
    """A fixed-code validation failure safe to print in CI."""


@dataclass(frozen=True)
class Policy:
    sources: Mapping[str, str]
    state_schema: int
    inventory_schema: int
    lanes: frozenset[str]
    controller_statuses: frozenset[str]
    track_statuses: frozenset[str]
    inventory_statuses: frozenset[str]
    entry_results: frozenset[str]
    gate_decisions: frozenset[str]
    status_projection: Mapping[str, str]
    controller_projection: Mapping[str, str]
    foundation_pattern: re.Pattern[str]
    validation_pattern: re.Pattern[str]
    horizon_pattern: re.Pattern[str]
    validation_lock_roots: tuple[str, ...]
    blocker_catalog: Mapping[str, str]
    claim_rules: Mapping[str, tuple[str, ...]]
    required_checks: tuple[str, ...]
    implementation_pending_condition: str
    implementation_transition_blockers: frozenset[str]
    implementation_transition_missing_outputs: tuple[str, ...]
    branch: str
    limits: Mapping[str, int]
    required_hashes: tuple[str, ...]
    state_claim_fields: tuple[str, ...]


@dataclass(frozen=True)
class RoadmapPhase:
    identifier: str
    name: str
    lane: str
    kind: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class InventoryPhase:
    identifier: str
    name: str
    lane: str
    status: str
    gate_decision: str | None
    dependencies: tuple[str, ...]
    blocker_ids: tuple[str, ...]
    missing_outputs: tuple[str, ...]
    entry_condition_count: int
    pending_entries: tuple[str, ...]
    failed_entries: tuple[str, ...]
    claims: tuple[str, ...]


@dataclass(frozen=True)
class RepositoryModel:
    policy: Policy
    exact_sha: str
    roadmap: tuple[RoadmapPhase, ...]
    phases: Mapping[str, InventoryPhase]
    state: Mapping[str, object]


@dataclass(frozen=True)
class GateProjection:
    payload: Mapping[str, object]
    upstream_success: bool

    def as_json(self) -> str:
        return json.dumps(self.payload, indent=2, sort_keys=True) + "\n"


def _violation(code: str) -> GateViolation:
    return GateViolation(code)


def _reject_constant(_value: str) -> object:
    raise _violation("json_non_finite_number")


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _violation("json_duplicate_key")
        result[key] = value
    return result


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


def _integer(value: object, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _violation(code)
    return value


def _timestamp(value: object, code: str) -> tuple[str, datetime]:
    raw = _string(value, code)
    if not raw.endswith("Z"):
        raise _violation(code)
    try:
        parsed = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as error:
        raise _violation(code) from error
    if parsed.tzinfo != UTC:
        raise _violation(code)
    return raw, parsed


def _string_list(value: object, code: str) -> list[str]:
    items = _sequence(value, code)
    if not all(isinstance(item, str) and item for item in items):
        raise _violation(code)
    return cast(list[str], items)


def _exact_keys(value: Mapping[str, object], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise _violation(code)


def _resolve_input(repository_root: Path, relative_path: str, code: str) -> Path:
    if Path(relative_path).is_absolute():
        raise _violation(code)
    root = repository_root.resolve()
    resolved = (root / relative_path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise _violation(code)
    return resolved


def _read_text(path: Path, maximum_bytes: int, code: str) -> str:
    data = path.read_bytes()
    if not data or len(data) > maximum_bytes:
        raise _violation(code)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _violation(code) from error
    if text.startswith("\ufeff") or "\x00" in text:
        raise _violation(code)
    return text


def load_json_strict(path: Path, maximum_bytes: int, code: str) -> dict[str, object]:
    """Load one bounded UTF-8 JSON object with duplicate keys rejected."""

    text = _read_text(path, maximum_bytes, code)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except GateViolation:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise _violation(code) from error
    return _mapping(value, code)


def _policy_string_map(value: object, code: str) -> dict[str, str]:
    mapping = _mapping(value, code)
    if not all(isinstance(item, str) and item for item in mapping.values()):
        raise _violation(code)
    return cast(dict[str, str], mapping)


def load_policy(repository_root: Path) -> Policy:
    """Load and self-validate the versioned controller policy."""

    path = _resolve_input(repository_root, POLICY_PATH.as_posix(), "policy_path_invalid")
    raw = load_json_strict(path, 131072, "policy_invalid")
    _exact_keys(
        raw,
        {
            "schema_version",
            "policy_id",
            "sources",
            "schemas",
            "vocabulary",
            "phase_rules",
            "blocker_catalog",
            "claim_rules",
            "github",
            "limits",
            "required_authoritative_hashes",
            "state_claim_fields",
        },
        "policy_fields_invalid",
    )
    if _integer(raw["schema_version"], "policy_schema_invalid") != 1:
        raise _violation("policy_schema_invalid")
    if _string(raw["policy_id"], "policy_id_invalid") != "github-phase-gate-v1":
        raise _violation("policy_id_invalid")

    sources = _policy_string_map(raw["sources"], "policy_sources_invalid")
    _exact_keys(sources, {"roadmap", "state", "inventory", "workflow"}, "policy_sources_invalid")
    schemas = _mapping(raw["schemas"], "policy_schemas_invalid")
    _exact_keys(schemas, {"state", "inventory"}, "policy_schemas_invalid")

    vocabulary = _mapping(raw["vocabulary"], "policy_vocabulary_invalid")
    _exact_keys(
        vocabulary,
        {
            "lanes",
            "controller_statuses",
            "track_statuses",
            "inventory_statuses",
            "entry_results",
            "gate_decisions",
            "status_projection",
            "controller_projection",
        },
        "policy_vocabulary_invalid",
    )
    lanes = frozenset(_string_list(vocabulary["lanes"], "policy_lanes_invalid"))
    if lanes != {"foundation", "validation"}:
        raise _violation("policy_lanes_invalid")
    controller_statuses = frozenset(
        _string_list(vocabulary["controller_statuses"], "policy_statuses_invalid")
    )
    track_statuses = frozenset(
        _string_list(vocabulary["track_statuses"], "policy_statuses_invalid")
    )
    inventory_statuses = frozenset(
        _string_list(vocabulary["inventory_statuses"], "policy_statuses_invalid")
    )
    entry_results = frozenset(
        _string_list(vocabulary["entry_results"], "policy_entry_results_invalid")
    )
    gate_decisions = frozenset(
        _string_list(vocabulary["gate_decisions"], "policy_gate_decisions_invalid")
    )
    status_projection = _policy_string_map(
        vocabulary["status_projection"], "policy_status_projection_invalid"
    )
    controller_projection = _policy_string_map(
        vocabulary["controller_projection"], "policy_controller_projection_invalid"
    )
    if (
        set(status_projection) != inventory_statuses
        or set(status_projection.values()) != track_statuses
    ):
        raise _violation("policy_status_projection_invalid")
    if set(controller_projection) != track_statuses:
        raise _violation("policy_controller_projection_invalid")
    if not set(controller_projection.values()).issubset(controller_statuses):
        raise _violation("policy_controller_projection_invalid")

    phase_rules = _mapping(raw["phase_rules"], "policy_phase_rules_invalid")
    _exact_keys(
        phase_rules,
        {
            "foundation_id_pattern",
            "validation_id_pattern",
            "horizon_id_pattern",
            "dependency_syntax_version",
            "require_passed_dependencies",
            "foundation_may_satisfy_validation",
            "foundation_requires_human_acceptance",
            "validation_lock_roots",
        },
        "policy_phase_rules_invalid",
    )
    if (
        _integer(phase_rules["dependency_syntax_version"], "policy_phase_rules_invalid") != 1
        or phase_rules["require_passed_dependencies"] is not True
        or phase_rules["foundation_may_satisfy_validation"] is not False
        or phase_rules["foundation_requires_human_acceptance"] is not False
    ):
        raise _violation("policy_phase_rules_invalid")
    try:
        foundation_pattern = re.compile(
            _string(phase_rules["foundation_id_pattern"], "policy_phase_rules_invalid")
        )
        validation_pattern = re.compile(
            _string(phase_rules["validation_id_pattern"], "policy_phase_rules_invalid")
        )
        horizon_pattern = re.compile(
            _string(phase_rules["horizon_id_pattern"], "policy_phase_rules_invalid")
        )
    except re.error as error:
        raise _violation("policy_phase_rules_invalid") from error
    validation_lock_roots = tuple(
        _string_list(phase_rules["validation_lock_roots"], "policy_phase_rules_invalid")
    )
    if validation_lock_roots != ("V00", "V01"):
        raise _violation("policy_phase_rules_invalid")

    blocker_catalog = _policy_string_map(raw["blocker_catalog"], "policy_blockers_invalid")
    if not blocker_catalog or any(
        BLOCKER_PATTERN.fullmatch(identifier) is None
        or category not in {"external", "technical", "human_decision"}
        for identifier, category in blocker_catalog.items()
    ):
        raise _violation("policy_blockers_invalid")
    canonical_blocker_classes = {
        "controller.implementation_checks": "technical",
        "controller.acceptance_revision": "technical",
        "controller.local_validation": "technical",
        "controller.independent_verification": "technical",
        "v00.symmetric_demand": "external",
        "v00.practitioner_confirmations": "external",
        "v00.recruitment_channel": "external",
        "v00.measured_cost": "external",
    }
    if any(
        blocker_catalog.get(identifier) != category
        for identifier, category in canonical_blocker_classes.items()
    ):
        raise _violation("policy_blockers_invalid")
    claim_source = _mapping(raw["claim_rules"], "policy_claims_invalid")
    claim_rules: dict[str, tuple[str, ...]] = {}
    for claim, prerequisites in claim_source.items():
        if BLOCKER_PATTERN.fullmatch(claim) is None:
            raise _violation("policy_claims_invalid")
        claim_rules[claim] = tuple(_string_list(prerequisites, "policy_claims_invalid"))

    github = _mapping(raw["github"], "policy_github_invalid")
    _exact_keys(
        github,
        {
            "required_checks",
            "exact_head_required",
            "implementation_and_acceptance_heads_required",
            "implementation_pending_condition",
            "implementation_transition_blockers",
            "implementation_transition_missing_outputs",
            "branch",
        },
        "policy_github_invalid",
    )
    required_checks = tuple(_string_list(github["required_checks"], "policy_checks_invalid"))
    if (
        required_checks
        != (
            "API quality",
            "Web quality",
            "Runtime smoke",
            "Phase gate",
            "Gate projection",
        )
        or github["exact_head_required"] is not True
        or github["implementation_and_acceptance_heads_required"] is not True
    ):
        raise _violation("policy_checks_invalid")
    implementation_pending_condition = _string(
        github["implementation_pending_condition"], "policy_transition_invalid"
    )
    implementation_transition_blockers = frozenset(
        _string_list(github["implementation_transition_blockers"], "policy_transition_invalid")
    )
    implementation_transition_missing_outputs = tuple(
        _string_list(
            github["implementation_transition_missing_outputs"],
            "policy_transition_invalid",
        )
    )
    if (
        implementation_pending_condition
        != "The exact implementation revision passes all five required GitHub jobs"
        or implementation_transition_blockers
        != {"controller.implementation_checks", "controller.acceptance_revision"}
        or implementation_transition_missing_outputs
        != (
            "Exact implementation revision must pass all five required GitHub checks",
            "Separate acceptance-state revision must pass all five required GitHub checks",
        )
        or any(
            blocker_catalog.get(identifier) != "technical"
            for identifier in implementation_transition_blockers
        )
    ):
        raise _violation("policy_transition_invalid")

    limits_source = _mapping(raw["limits"], "policy_limits_invalid")
    _exact_keys(
        limits_source,
        {"policy_bytes", "state_bytes", "inventory_bytes", "roadmap_bytes", "workflow_bytes"},
        "policy_limits_invalid",
    )
    limits = {key: _integer(value, "policy_limits_invalid") for key, value in limits_source.items()}
    if limits["policy_bytes"] != 131072 or any(value <= 0 for value in limits.values()):
        raise _violation("policy_limits_invalid")

    required_hashes = tuple(
        _string_list(raw["required_authoritative_hashes"], "policy_hashes_invalid")
    )
    if len(required_hashes) != len(set(required_hashes)):
        raise _violation("policy_hashes_invalid")
    state_claim_fields = tuple(_string_list(raw["state_claim_fields"], "policy_claims_invalid"))
    if state_claim_fields != (
        "product_readiness",
        "role_readiness",
        "validation_satisfied_by_foundation",
    ):
        raise _violation("policy_claims_invalid")

    branch = _string(github["branch"], "policy_branch_invalid")
    if branch != "automation/**":
        raise _violation("policy_branch_invalid")

    return Policy(
        sources=sources,
        state_schema=_integer(schemas["state"], "policy_schemas_invalid"),
        inventory_schema=_integer(schemas["inventory"], "policy_schemas_invalid"),
        lanes=lanes,
        controller_statuses=controller_statuses,
        track_statuses=track_statuses,
        inventory_statuses=inventory_statuses,
        entry_results=entry_results,
        gate_decisions=gate_decisions,
        status_projection=status_projection,
        controller_projection=controller_projection,
        foundation_pattern=foundation_pattern,
        validation_pattern=validation_pattern,
        horizon_pattern=horizon_pattern,
        validation_lock_roots=validation_lock_roots,
        blocker_catalog=blocker_catalog,
        claim_rules=claim_rules,
        required_checks=required_checks,
        implementation_pending_condition=implementation_pending_condition,
        implementation_transition_blockers=implementation_transition_blockers,
        implementation_transition_missing_outputs=implementation_transition_missing_outputs,
        branch=branch,
        limits=limits,
        required_hashes=required_hashes,
        state_claim_fields=state_claim_fields,
    )


def _dependency_sentence(section: str) -> str:
    match = DEPENDENCY_CLAUSE.search(section)
    if match is None:
        raise _violation("roadmap_dependency_missing")
    return " ".join(match.group("value").split()).split(".", 1)[0]


def _derive_dependencies(
    identifier: str,
    lane: str,
    sentence: str,
    ordered_ids: Sequence[str],
    lanes: Mapping[str, str],
) -> tuple[str, ...]:
    preceding = list(ordered_ids[: ordered_ids.index(identifier)])
    if sentence == "None":
        return ()
    if sentence == "All preceding phases":
        return tuple(item for item in preceding if lanes[item] == lane)
    references = re.findall(r"`([FV][0-9]{2}[A-Z]?)`", sentence)
    if not references:
        raise _violation("roadmap_dependency_syntax_invalid")
    if any(reference not in ordered_ids for reference in references):
        raise _violation("roadmap_dependency_unknown_or_forward")
    allowed = re.sub(r"`[FV][0-9]{2}[A-Z]?`", "ID", sentence)
    allowed = re.sub(r"\bID\s+through\s+ID\b", "IDS", allowed)
    allowed = re.sub(r"\b(?:ID|IDS)\b", "", allowed)
    allowed = re.sub(r"\b(?:only|including|and)\b", "", allowed)
    if allowed.replace(",", "").strip():
        raise _violation("roadmap_dependency_syntax_invalid")
    expanded = list(references)
    if " through " in sentence:
        first, last = references[0], references[1]
        if first not in preceding or last not in preceding:
            raise _violation("roadmap_dependency_range_invalid")
        start = ordered_ids.index(first)
        end = ordered_ids.index(last)
        if start > end or lanes[first] != lane or lanes[last] != lane:
            raise _violation("roadmap_dependency_range_invalid")
        expanded.extend(item for item in ordered_ids[start : end + 1] if lanes[item] == lane)
    unique = tuple(item for item in ordered_ids if item in set(expanded))
    if any(item not in preceding for item in unique):
        raise _violation("roadmap_dependency_unknown_or_forward")
    if any(lanes[item] != lane for item in unique):
        raise _violation("roadmap_cross_lane_dependency")
    return unique


def parse_roadmap(text: str, policy: Policy) -> tuple[RoadmapPhase, ...]:
    """Parse strict phase headings and authoritative dependency clauses."""

    matches = list(PHASE_HEADING.finditer(text))
    if not matches:
        raise _violation("roadmap_phase_missing")
    identifiers = [match.group("id") for match in matches]
    if len(identifiers) != len(set(identifiers)):
        raise _violation("roadmap_phase_duplicate")
    lanes: dict[str, str] = {}
    kinds: dict[str, str] = {}
    for identifier in identifiers:
        if policy.foundation_pattern.fullmatch(identifier):
            lanes[identifier], kinds[identifier] = "foundation", "phase"
        elif policy.validation_pattern.fullmatch(identifier):
            lanes[identifier], kinds[identifier] = "validation", "phase"
        elif policy.horizon_pattern.fullmatch(identifier):
            lanes[identifier], kinds[identifier] = "validation", "horizon"
        else:
            raise _violation("roadmap_phase_id_invalid")

    phases: list[RoadmapPhase] = []
    for index, match in enumerate(matches):
        identifier = match.group("id")
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : section_end]
        dependencies: tuple[str, ...] = ()
        if kinds[identifier] == "phase":
            dependencies = _derive_dependencies(
                identifier,
                lanes[identifier],
                _dependency_sentence(section),
                identifiers,
                lanes,
            )
        phases.append(
            RoadmapPhase(
                identifier=identifier,
                name=match.group("name").strip(),
                lane=lanes[identifier],
                kind=kinds[identifier],
                dependencies=dependencies,
            )
        )
    return tuple(phases)


def _lane_phases(roadmap: Sequence[RoadmapPhase], lane: str) -> tuple[RoadmapPhase, ...]:
    phases = tuple(phase for phase in roadmap if phase.lane == lane and phase.kind == "phase")
    if not phases:
        raise _violation("roadmap_lane_empty")
    return phases


def _expected_active_phase(
    roadmap: Sequence[RoadmapPhase],
    inventory: Mapping[str, InventoryPhase],
    lane: str,
) -> RoadmapPhase:
    phases = _lane_phases(roadmap, lane)
    return next(
        (phase for phase in phases if inventory[phase.identifier].status != "PASSED"),
        phases[-1],
    )


def _next_lane_phase(
    roadmap: Sequence[RoadmapPhase], active_phase: str, lane: str
) -> RoadmapPhase | None:
    phases = _lane_phases(roadmap, lane)
    for index, phase in enumerate(phases):
        if phase.identifier == active_phase:
            return phases[index + 1] if index + 1 < len(phases) else None
    raise _violation("state_track_phase_invalid")


def _expected_future_boundary(
    roadmap: Sequence[RoadmapPhase],
    inventory: Mapping[str, InventoryPhase],
    active_phase: str,
) -> tuple[str | None, str]:
    successor = _next_lane_phase(roadmap, active_phase, "foundation")
    active_accepted = inventory[active_phase].status == "PASSED"
    if not active_accepted:
        return (
            successor.identifier if successor is not None else None,
            "LOCKED_UNTIL_ACTIVE_PHASE_ACCEPTED",
        )
    if successor is None:
        return None, "NO_DEFINED_SUCCESSOR"
    dependencies_passed = all(
        inventory[dependency].status == "PASSED" for dependency in successor.dependencies
    )
    return successor.identifier, "ELIGIBLE" if dependencies_passed else "LOCKED_BY_DEPENDENCIES"


def _validate_claim_rules(policy: Policy, roadmap: Sequence[RoadmapPhase]) -> None:
    known = {phase.identifier: phase for phase in roadmap}
    for prerequisites in policy.claim_rules.values():
        if (
            not prerequisites
            or len(prerequisites) != len(set(prerequisites))
            or any(
                identifier not in known
                or known[identifier].lane != "validation"
                or known[identifier].kind != "phase"
                for identifier in prerequisites
            )
        ):
            raise _violation("policy_claims_invalid")


def _validate_gate(status: str, gate: str | None) -> None:
    if status == "PASSED" and gate != "Continue":
        raise _violation("passed_gate_not_continue")
    if status in {"NOT_STARTED", "IN_PROGRESS", "IMPLEMENTED_UNVERIFIED", "QUOTA_PAUSED"}:
        if gate is not None:
            raise _violation("nonterminal_gate_present")
    elif status == "BLOCKED_EXTERNAL" and gate not in {"Revise", "Narrow", "Stop"}:
        raise _violation("external_gate_invalid")
    elif status == "BLOCKED_HUMAN" and gate is None:
        raise _violation("human_gate_missing")


def _validate_inventory_phase(
    raw: Mapping[str, object],
    roadmap: RoadmapPhase,
    policy: Policy,
) -> InventoryPhase:
    _exact_keys(
        raw,
        {
            "id",
            "name",
            "lane",
            "status",
            "gate_decision",
            "entry_conditions",
            "implemented_files",
            "tests",
            "missing_outputs",
            "blocker_ids",
            "external_blockers",
            "human_decisions",
            "claims",
            "gate_effects",
            "next_smallest_action",
        },
        "inventory_phase_fields_invalid",
    )
    identifier = _string(raw["id"], "inventory_phase_id_invalid")
    name = _string(raw["name"], "inventory_phase_name_invalid")
    lane = _string(raw["lane"], "inventory_phase_lane_invalid")
    if (identifier, name, lane) != (roadmap.identifier, roadmap.name, roadmap.lane):
        raise _violation("roadmap_inventory_disagreement")
    status = _string(raw["status"], "inventory_status_invalid")
    if status not in policy.inventory_statuses:
        raise _violation("inventory_status_invalid")
    gate = _optional_string(raw["gate_decision"], "inventory_gate_invalid")
    if gate is not None and gate not in policy.gate_decisions:
        raise _violation("inventory_gate_invalid")
    _validate_gate(status, gate)

    entries = _sequence(raw["entry_conditions"], "inventory_entries_invalid")
    pending_entries: list[str] = []
    failed_entries: list[str] = []
    for entry_value in entries:
        entry = _mapping(entry_value, "inventory_entry_invalid")
        _exact_keys(entry, {"condition", "result", "evidence"}, "inventory_entry_fields_invalid")
        condition = _string(entry["condition"], "inventory_entry_invalid")
        result = _string(entry["result"], "inventory_entry_result_invalid")
        if result not in policy.entry_results:
            raise _violation("inventory_entry_result_invalid")
        evidence = _string_list(entry["evidence"], "inventory_entry_evidence_invalid")
        if result == "PASSED" and not evidence:
            raise _violation("passed_entry_evidence_missing")
        if result == "PENDING":
            pending_entries.append(condition)
        elif result == "FAILED":
            failed_entries.append(condition)
    implemented_files = _string_list(raw["implemented_files"], "inventory_files_invalid")
    tests = _string_list(raw["tests"], "inventory_tests_invalid")
    missing_outputs = tuple(_string_list(raw["missing_outputs"], "inventory_outputs_invalid"))
    blockers = tuple(_string_list(raw["blocker_ids"], "inventory_blockers_invalid"))
    if len(blockers) != len(set(blockers)) or any(
        blocker not in policy.blocker_catalog for blocker in blockers
    ):
        raise _violation("inventory_blockers_invalid")
    external_descriptions = _string_list(
        raw["external_blockers"], "inventory_external_blockers_invalid"
    )
    human_descriptions = _string_list(raw["human_decisions"], "inventory_human_invalid")
    claims = tuple(_string_list(raw["claims"], "inventory_claims_invalid"))
    if len(claims) != len(set(claims)) or any(claim not in policy.claim_rules for claim in claims):
        raise _violation("inventory_claims_invalid")
    effects = _mapping(raw["gate_effects"], "inventory_effects_invalid")
    _exact_keys(effects, {"satisfies", "unlocks", "weakens"}, "inventory_effects_invalid")
    for effect in effects.values():
        _string_list(effect, "inventory_effects_invalid")
    _string(raw["next_smallest_action"], "inventory_next_action_invalid")

    if roadmap.kind == "horizon" and status != "NOT_STARTED":
        raise _violation("horizon_progress_invalid")
    if status == "PASSED":
        if not entries or any(
            _mapping(entry, "inventory_entry_invalid")["result"] != "PASSED" for entry in entries
        ):
            raise _violation("passed_entry_failed_or_pending")
        if missing_outputs or not implemented_files or not tests:
            raise _violation("passed_evidence_incomplete")
        if blockers or external_descriptions or human_descriptions:
            raise _violation("passed_blockers_present")
    if status == "BLOCKED_EXTERNAL":
        if not blockers or any(policy.blocker_catalog[item] != "external" for item in blockers):
            raise _violation("external_blocker_class_invalid")
        if not external_descriptions or human_descriptions:
            raise _violation("external_blocker_projection_invalid")
    if status == "BLOCKED_HUMAN":
        if not blockers or any(
            policy.blocker_catalog[item] != "human_decision" for item in blockers
        ):
            raise _violation("human_blocker_class_invalid")
        if not human_descriptions or external_descriptions:
            raise _violation("human_blocker_projection_invalid")
    if lane == "foundation":
        if any(policy.blocker_catalog[item] != "technical" for item in blockers):
            raise _violation("foundation_blocker_class_invalid")
        if status == "BLOCKED_HUMAN" or external_descriptions or human_descriptions or claims:
            raise _violation("foundation_human_or_claim_invalid")

    return InventoryPhase(
        identifier=identifier,
        name=name,
        lane=lane,
        status=status,
        gate_decision=gate,
        dependencies=roadmap.dependencies,
        blocker_ids=blockers,
        missing_outputs=missing_outputs,
        entry_condition_count=len(entries),
        pending_entries=tuple(pending_entries),
        failed_entries=tuple(failed_entries),
        claims=claims,
    )


def _validate_inventory(
    raw: Mapping[str, object],
    roadmap: Sequence[RoadmapPhase],
    policy: Policy,
) -> dict[str, InventoryPhase]:
    _exact_keys(
        raw,
        {
            "schema_version",
            "generated_at",
            "repository",
            "runtime_capabilities",
            "claims",
            "phases",
        },
        "inventory_fields_invalid",
    )
    if _integer(raw["schema_version"], "inventory_schema_invalid") != policy.inventory_schema:
        raise _violation("inventory_schema_invalid")
    _string(raw["generated_at"], "inventory_timestamp_invalid")
    repository = _mapping(raw["repository"], "inventory_repository_invalid")
    _exact_keys(
        repository,
        {"branch", "head", "working_tree", "source_of_truth"},
        "inventory_repository_invalid",
    )
    if not fnmatchcase(_string(repository["branch"], "inventory_branch_invalid"), policy.branch):
        raise _violation("inventory_branch_invalid")
    _string(repository["head"], "inventory_head_invalid")
    _string(repository["working_tree"], "inventory_repository_invalid")
    _string_list(repository["source_of_truth"], "inventory_repository_invalid")
    runtime = _mapping(raw["runtime_capabilities"], "inventory_runtime_invalid")
    _exact_keys(runtime, {"implemented", "not_implemented"}, "inventory_runtime_invalid")
    _string_list(runtime["implemented"], "inventory_runtime_invalid")
    _string_list(runtime["not_implemented"], "inventory_runtime_invalid")
    root_claims = _string_list(raw["claims"], "inventory_claims_invalid")
    if root_claims:
        raise _violation("repository_claim_invalid")

    phase_values = _sequence(raw["phases"], "inventory_phases_invalid")
    if len(phase_values) != len(roadmap):
        raise _violation("roadmap_inventory_phase_set_disagreement")
    result: dict[str, InventoryPhase] = {}
    for roadmap_phase, phase_value in zip(roadmap, phase_values, strict=True):
        phase = _validate_inventory_phase(
            _mapping(phase_value, "inventory_phase_invalid"), roadmap_phase, policy
        )
        if phase.identifier in result:
            raise _violation("inventory_phase_duplicate")
        result[phase.identifier] = phase

    if result["V00"].status != "PASSED":
        for roadmap_phase in roadmap:
            if (
                roadmap_phase.lane == "validation"
                and roadmap_phase.kind == "phase"
                and roadmap_phase.identifier != "V00"
            ):
                if result[roadmap_phase.identifier].status != "NOT_STARTED":
                    raise _violation("v00_lock_violated")
    elif result["V01"].status != "PASSED":
        passed_v01 = False
        for roadmap_phase in roadmap:
            if roadmap_phase.identifier == "V01":
                passed_v01 = True
                continue
            if (
                passed_v01
                and roadmap_phase.lane == "validation"
                and result[roadmap_phase.identifier].status != "NOT_STARTED"
            ):
                raise _violation("v01_lock_violated")

    for inventory_phase in result.values():
        if inventory_phase.status != "NOT_STARTED" and any(
            result[dependency].status != "PASSED" for dependency in inventory_phase.dependencies
        ):
            raise _violation("dependency_not_passed")
        for claim in inventory_phase.claims:
            if any(result[required].status != "PASSED" for required in policy.claim_rules[claim]):
                raise _violation("claim_prerequisite_missing")
    return result


def _validate_effects(
    raw_inventory: Mapping[str, object],
    roadmap: Sequence[RoadmapPhase],
) -> None:
    phases = _sequence(raw_inventory["phases"], "inventory_phases_invalid")
    known = {phase.identifier: phase for phase in roadmap}
    for value in phases:
        raw = _mapping(value, "inventory_phase_invalid")
        identifier = _string(raw["id"], "inventory_phase_id_invalid")
        effects = _mapping(raw["gate_effects"], "inventory_effects_invalid")
        for effect_values in effects.values():
            for target in _string_list(effect_values, "inventory_effects_invalid"):
                if target not in known:
                    raise _violation("gate_effect_target_unknown")
                if known[identifier].lane == "foundation" and known[target].lane == "validation":
                    raise _violation("foundation_validation_effect_invalid")


def _validate_state(
    raw: Mapping[str, object],
    roadmap: Sequence[RoadmapPhase],
    inventory: Mapping[str, InventoryPhase],
    raw_inventory: Mapping[str, object],
    policy: Policy,
) -> None:
    _exact_keys(
        raw,
        {
            "schema_version",
            "status",
            "active_phase",
            "active_slice",
            "gate_decision",
            "last_completed_action",
            "next_action",
            "stop_reason",
            "validation_track",
            "foundation_track",
            "implementation_inventory",
            "external_blockers",
            "controller_decisions_owned",
            "human_decisions_required",
            "future_phase_boundary",
            "claims",
            "last_verified_commit",
            "authoritative_file_hashes",
            "evidence_fingerprint",
            "run_number",
            "last_run_started_at",
            "last_run_completed_at",
        },
        "state_fields_invalid",
    )
    if _integer(raw["schema_version"], "state_schema_invalid") != policy.state_schema:
        raise _violation("state_schema_invalid")
    controller_status = _string(raw["status"], "state_status_invalid")
    if controller_status not in policy.controller_statuses:
        raise _violation("state_status_invalid")
    active_phase = _string(raw["active_phase"], "state_active_phase_invalid")
    _string(raw["active_slice"], "state_active_slice_invalid")
    top_gate = _optional_string(raw["gate_decision"], "state_gate_invalid")
    if top_gate is not None and top_gate not in policy.gate_decisions:
        raise _violation("state_gate_invalid")
    for field in ("last_completed_action", "next_action", "stop_reason", "evidence_fingerprint"):
        _string(raw[field], "state_text_invalid")
    _string_list(raw["controller_decisions_owned"], "state_decisions_invalid")

    tracks: dict[str, Mapping[str, object]] = {}
    for lane, field in (("validation", "validation_track"), ("foundation", "foundation_track")):
        track = _mapping(raw[field], "state_track_invalid")
        expected = {"active_phase", "status", "gate_decision", "next_action"}
        if lane == "validation":
            expected.add("blocking_inputs")
        _exact_keys(track, expected, "state_track_fields_invalid")
        phase_id = _string(track["active_phase"], "state_track_phase_invalid")
        if phase_id not in inventory or inventory[phase_id].lane != lane:
            raise _violation("state_track_phase_invalid")
        if phase_id != _expected_active_phase(roadmap, inventory, lane).identifier:
            raise _violation("state_active_phase_disagreement")
        status = _string(track["status"], "state_track_status_invalid")
        if status not in policy.track_statuses:
            raise _violation("state_track_status_invalid")
        if policy.status_projection[inventory[phase_id].status] != status:
            raise _violation("state_inventory_status_disagreement")
        gate = _optional_string(track["gate_decision"], "state_track_gate_invalid")
        if gate != inventory[phase_id].gate_decision:
            raise _violation("state_inventory_gate_disagreement")
        _string(track["next_action"], "state_track_next_action_invalid")
        tracks[lane] = track
    foundation = tracks["foundation"]
    if _string(foundation["active_phase"], "state_track_phase_invalid") != active_phase:
        raise _violation("state_active_phase_disagreement")
    foundation_status = _string(foundation["status"], "state_track_status_invalid")
    if policy.controller_projection[foundation_status] != controller_status:
        raise _violation("state_controller_status_disagreement")
    if top_gate != _optional_string(foundation["gate_decision"], "state_track_gate_invalid"):
        raise _violation("state_controller_gate_disagreement")

    inventory_ref = _mapping(raw["implementation_inventory"], "state_inventory_ref_invalid")
    _exact_keys(inventory_ref, {"path", "generated_at"}, "state_inventory_ref_invalid")
    if _string(inventory_ref["path"], "state_inventory_ref_invalid") != policy.sources["inventory"]:
        raise _violation("state_inventory_ref_invalid")
    inventory_timestamp, inventory_time = _timestamp(
        raw_inventory["generated_at"], "inventory_timestamp_invalid"
    )
    if _string(inventory_ref["generated_at"], "state_inventory_ref_invalid") != inventory_timestamp:
        raise _violation("state_inventory_timestamp_disagreement")
    started_at, started_time = _timestamp(raw["last_run_started_at"], "state_timestamp_invalid")
    if started_at != inventory_timestamp or started_time != inventory_time:
        raise _violation("state_inventory_timestamp_disagreement")
    _completed_at, completed_time = _timestamp(
        raw["last_run_completed_at"], "state_timestamp_invalid"
    )
    if completed_time < started_time:
        raise _violation("state_timestamp_order_invalid")
    if _integer(raw["run_number"], "state_run_number_invalid") < 1:
        raise _violation("state_run_number_invalid")

    external = _string_list(raw["external_blockers"], "state_external_blockers_invalid")
    human = _string_list(raw["human_decisions_required"], "state_human_blockers_invalid")
    if any(policy.blocker_catalog.get(item) != "external" for item in external):
        raise _violation("state_external_blockers_invalid")
    if any(policy.blocker_catalog.get(item) != "human_decision" for item in human):
        raise _violation("state_human_blockers_invalid")
    validation = tracks["validation"]
    validation_blockers = _string_list(
        validation["blocking_inputs"], "state_validation_blockers_invalid"
    )
    if set(validation_blockers) != set(external):
        raise _violation("state_external_projection_disagreement")
    validation_id = _string(validation["active_phase"], "state_track_phase_invalid")
    validation_blocker_ids = inventory[validation_id].blocker_ids
    inventory_external = {
        item for item in validation_blocker_ids if policy.blocker_catalog[item] == "external"
    }
    inventory_human = {
        item for item in validation_blocker_ids if policy.blocker_catalog[item] == "human_decision"
    }
    if inventory_external != set(external) or inventory_human != set(human):
        raise _violation("state_blocker_projection_disagreement")
    if external and (
        human
        or inventory[validation_id].status != "BLOCKED_EXTERNAL"
        or _string(validation["status"], "state_track_status_invalid") != "WAITING_EXTERNAL"
    ):
        raise _violation("external_wait_misclassified")
    if human and (
        inventory[validation_id].status != "BLOCKED_HUMAN"
        or _string(validation["status"], "state_track_status_invalid") != "WAITING_HUMAN"
    ):
        raise _violation("human_wait_misclassified")

    future = _mapping(raw["future_phase_boundary"], "state_future_boundary_invalid")
    _exact_keys(future, {"phase", "status", "next_action"}, "state_future_boundary_invalid")
    future_status = _string(future["status"], "state_future_boundary_invalid")
    expected_future_phase, expected_future_status = _expected_future_boundary(
        roadmap, inventory, active_phase
    )
    if (
        _optional_string(future["phase"], "state_future_boundary_invalid") != expected_future_phase
        or future_status != expected_future_status
    ):
        raise _violation("state_future_boundary_invalid")
    _string(future["next_action"], "state_future_boundary_invalid")
    claims = _mapping(raw["claims"], "state_claims_invalid")
    _exact_keys(claims, set(policy.state_claim_fields), "state_claims_invalid")
    if any(claims[field] is not False for field in policy.state_claim_fields):
        raise _violation("unsupported_product_or_readiness_claim")


def _canonical_file_hash(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _validate_hashes(repository_root: Path, state: Mapping[str, object], policy: Policy) -> None:
    hashes = _mapping(state["authoritative_file_hashes"], "state_hashes_invalid")
    if not set(policy.required_hashes).issubset(hashes):
        raise _violation("state_required_hash_missing")
    for relative_path, expected_value in hashes.items():
        expected = _string(expected_value, "state_hash_invalid")
        if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            raise _violation("state_hash_invalid")
        path = _resolve_input(repository_root, relative_path, "state_hash_path_invalid")
        if _canonical_file_hash(path) != expected:
            raise _violation("state_hash_mismatch")


def _workflow_job(text: str, identifier: str, missing_code: str) -> str:
    match = re.search(
        rf"^  {re.escape(identifier)}:\n(?P<body>.*?)(?=^  [a-z][a-z0-9-]*:\n|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise _violation(missing_code)
    return match.group("body")


def _workflow_folded_command(body: str, step_name: str) -> tuple[str, ...]:
    match = re.search(
        rf"^      - name: {re.escape(step_name)}\n"
        r"        run: >-\n(?P<command>(?:          [^\n]*(?:\n|\Z))+)",
        body,
        re.MULTILINE,
    )
    if match is None:
        return ()
    return tuple(line.strip() for line in match.group("command").splitlines())


def validate_workflow_contract(text: str, policy: Policy) -> None:
    """Verify the exact-head, read-only five-job workflow contract."""

    if "pull_request_target:" in text or "secrets." in text or re.search(r"\bwrite\b", text):
        raise _violation("workflow_privilege_invalid")
    if re.search(r"continue-on-error\s*:", text):
        raise _violation("workflow_controller_bypass_invalid")
    if re.findall(r"^\s*if\s*:\s*(.+)$", text, re.MULTILINE) != ["${{ always() }}"]:
        raise _violation("workflow_controller_bypass_invalid")
    if "permissions:\n  contents: read" not in text:
        raise _violation("workflow_permissions_invalid")
    if "pull_request:" not in text or 'branches: [main, "automation/**"]' not in text:
        raise _violation("workflow_trigger_invalid")
    if "cancel-in-progress: true" not in text:
        raise _violation("workflow_concurrency_invalid")
    expected_expression = "EXACT_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}"
    if text.count(expected_expression) != 1:
        raise _violation("workflow_exact_head_invalid")
    job_names = re.findall(r"^    name: (.+)$", text, re.MULTILINE)
    if len(job_names) != len(set(job_names)) or set(job_names) != set(policy.required_checks):
        raise _violation("workflow_required_checks_invalid")
    checkout_count = text.count("uses: actions/checkout@")
    if checkout_count != len(policy.required_checks):
        raise _violation("workflow_checkout_count_invalid")
    if text.count("ref: ${{ env.EXACT_HEAD_SHA }}") != checkout_count:
        raise _violation("workflow_checkout_ref_invalid")
    if text.count("persist-credentials: false") != checkout_count:
        raise _violation("workflow_checkout_credentials_invalid")
    uses = re.findall(r"^\s*-?\s*uses: ([^\s]+)", text, re.MULTILINE)
    if not uses or any(re.fullmatch(r"[^@]+@[0-9a-f]{40}", item) is None for item in uses):
        raise _violation("workflow_action_pin_invalid")
    job_contracts = {
        "api": 10,
        "web": 10,
        "runtime-smoke": 10,
        "phase-gate": 5,
        "gate-projection": 5,
    }
    job_bodies = {
        identifier: _workflow_job(
            text,
            identifier,
            (
                "workflow_projection_job_missing"
                if identifier == "gate-projection"
                else "workflow_required_checks_invalid"
            ),
        )
        for identifier in job_contracts
    }
    for identifier, timeout in job_contracts.items():
        body = job_bodies[identifier]
        if (
            body.count("runs-on: ubuntu-latest") != 1
            or body.count(f"timeout-minutes: {timeout}") != 1
            or body.count("uses: actions/checkout@") != 1
            or body.count("ref: ${{ env.EXACT_HEAD_SHA }}") != 1
            or body.count("persist-credentials: false") != 1
        ):
            raise _violation("workflow_job_contract_invalid")
    phase_job = job_bodies["phase-gate"]
    projection = job_bodies["gate-projection"]
    if (
        "needs: [api, web, runtime-smoke, phase-gate]" not in projection
        or "if: ${{ always() }}" not in projection
        or "--require-check-results" not in projection
        or '--github-summary "$GITHUB_STEP_SUMMARY"' not in projection
    ):
        raise _violation("workflow_projection_dependencies_invalid")
    expected_result_arguments = (
        '--check-result "API quality=${{ needs.api.result }}"',
        '--check-result "Web quality=${{ needs.web.result }}"',
        '--check-result "Runtime smoke=${{ needs.runtime-smoke.result }}"',
        '--check-result "Phase gate=${{ needs.phase-gate.result }}"',
    )
    if any(
        projection.count(argument) != 1 for argument in expected_result_arguments
    ) or projection.count("--check-result") != len(expected_result_arguments):
        raise _violation("workflow_projection_result_sources_invalid")
    expected_validation_command = (
        "uv run --project apps/api --locked python scripts/phase_gate.py validate",
        '--expected-sha "$EXACT_HEAD_SHA"',
    )
    expected_projection_command = (
        "uv run --project apps/api --locked python scripts/phase_gate.py project",
        '--expected-sha "$EXACT_HEAD_SHA"',
        '--check-result "API quality=${{ needs.api.result }}"',
        '--check-result "Web quality=${{ needs.web.result }}"',
        '--check-result "Runtime smoke=${{ needs.runtime-smoke.result }}"',
        '--check-result "Phase gate=${{ needs.phase-gate.result }}"',
        "--require-check-results",
        '--github-summary "$GITHUB_STEP_SUMMARY"',
    )
    if (
        _workflow_folded_command(phase_job, "Validate the exact revision phase state")
        != expected_validation_command
        or _workflow_folded_command(projection, "Project the exact revision gate state")
        != expected_projection_command
    ):
        raise _violation("workflow_controller_commands_invalid")


def _git_head(repository_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def _git_worktree_clean(repository_root: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return not result.stdout.strip()


def _git_is_ancestor(repository_root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


def validate_repository(
    repository_root: Path,
    expected_sha: str,
    *,
    actual_sha: str | None = None,
    clean_check: Callable[[], bool] | None = None,
    ancestor_check: Callable[[str, str], bool] | None = None,
) -> RepositoryModel:
    """Validate all controller inputs without changing repository state."""

    root = repository_root.resolve()
    if SHA_PATTERN.fullmatch(expected_sha) is None:
        raise _violation("expected_sha_invalid")
    exact_sha = _git_head(root) if actual_sha is None else actual_sha
    if SHA_PATTERN.fullmatch(exact_sha) is None or exact_sha != expected_sha:
        raise _violation("exact_head_mismatch")
    if not (clean_check() if clean_check is not None else _git_worktree_clean(root)):
        raise _violation("worktree_not_exact_head")
    policy = load_policy(root)
    roadmap_path = _resolve_input(root, policy.sources["roadmap"], "roadmap_path_invalid")
    state_path = _resolve_input(root, policy.sources["state"], "state_path_invalid")
    inventory_path = _resolve_input(root, policy.sources["inventory"], "inventory_path_invalid")
    workflow_path = _resolve_input(root, policy.sources["workflow"], "workflow_path_invalid")
    roadmap_text = _read_text(roadmap_path, policy.limits["roadmap_bytes"], "roadmap_invalid")
    workflow_text = _read_text(workflow_path, policy.limits["workflow_bytes"], "workflow_invalid")
    state = load_json_strict(state_path, policy.limits["state_bytes"], "state_invalid")
    raw_inventory = load_json_strict(
        inventory_path, policy.limits["inventory_bytes"], "inventory_invalid"
    )
    roadmap = parse_roadmap(roadmap_text, policy)
    _validate_claim_rules(policy, roadmap)
    inventory = _validate_inventory(raw_inventory, roadmap, policy)
    _validate_effects(raw_inventory, roadmap)
    _validate_state(state, roadmap, inventory, raw_inventory, policy)
    _validate_hashes(root, state, policy)
    validate_workflow_contract(workflow_text, policy)

    verified_sha = _string(state["last_verified_commit"], "state_verified_head_invalid")
    repository = _mapping(raw_inventory["repository"], "inventory_repository_invalid")
    if SHA_PATTERN.fullmatch(verified_sha) is None or repository["head"] != verified_sha:
        raise _violation("state_verified_head_disagreement")
    checker = ancestor_check
    if checker is None:

        def checker(ancestor: str, descendant: str) -> bool:
            return _git_is_ancestor(root, ancestor, descendant)

    if not checker(verified_sha, exact_sha):
        raise _violation("state_verified_head_stale")

    return RepositoryModel(
        policy=policy,
        exact_sha=exact_sha,
        roadmap=roadmap,
        phases=inventory,
        state=state,
    )


def _track_payload(state: Mapping[str, object], field: str) -> dict[str, object]:
    track = _mapping(state[field], "state_track_invalid")
    return {
        "gate": track["gate_decision"],
        "phase": track["active_phase"],
        "status": track["status"],
    }


def _passed_prerequisites(model: RepositoryModel) -> list[str]:
    wanted: set[str] = set()

    def visit(identifier: str) -> None:
        for dependency in model.phases[identifier].dependencies:
            visit(dependency)
            if model.phases[dependency].status == "PASSED":
                wanted.add(dependency)

    foundation = _mapping(model.state["foundation_track"], "state_track_invalid")
    validation = _mapping(model.state["validation_track"], "state_track_invalid")
    visit(_string(foundation["active_phase"], "state_track_phase_invalid"))
    visit(_string(validation["active_phase"], "state_track_phase_invalid"))
    return [phase.identifier for phase in model.roadmap if phase.identifier in wanted]


def _check_results(
    policy: Policy,
    values: Sequence[str],
    *,
    required: bool,
) -> tuple[dict[str, str], list[str], bool]:
    upstream_names = tuple(name for name in policy.required_checks if name != "Gate projection")
    results: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise _violation("check_result_invalid")
        name, result = value.split("=", 1)
        if name not in upstream_names or name in results:
            raise _violation("check_result_invalid")
        if result not in {"success", "failure", "cancelled", "skipped", "pending"}:
            raise _violation("check_result_invalid")
        results[name] = result
    if required and set(results) != set(upstream_names):
        raise _violation("check_result_missing")
    if not results:
        return results, ["CHECK_RESULTS_NOT_SUPPLIED"], False
    reasons = [
        "CHECK_" + re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_") + "_" + result.upper()
        for name, result in results.items()
        if result != "success"
    ]
    return results, reasons, not reasons and set(results) == set(upstream_names)


def build_projection(
    model: RepositoryModel,
    check_results: Sequence[str] = (),
    *,
    require_check_results: bool = False,
) -> GateProjection:
    """Build a deterministic projection from a completely validated model."""

    _results, reasons, upstream_success = _check_results(
        model.policy, check_results, required=require_check_results
    )
    state = model.state
    foundation_track = _mapping(state["foundation_track"], "state_track_invalid")
    foundation_id = _string(foundation_track["active_phase"], "state_track_phase_invalid")
    foundation_status = _string(foundation_track["status"], "state_track_status_invalid")
    external = sorted(_string_list(state["external_blockers"], "state_external_blockers_invalid"))
    human = sorted(_string_list(state["human_decisions_required"], "state_human_blockers_invalid"))
    foundation_phase = model.phases[foundation_id]
    technical = sorted(foundation_phase.blocker_ids)
    transition_ready = (
        foundation_status == "IMPLEMENTED_UNVERIFIED"
        and not foundation_phase.failed_entries
        and foundation_phase.pending_entries == (model.policy.implementation_pending_condition,)
        and frozenset(foundation_phase.blocker_ids)
        == model.policy.implementation_transition_blockers
        and foundation_phase.missing_outputs
        == model.policy.implementation_transition_missing_outputs
    )
    accepted_ready = (
        foundation_status == "PHASE_PASSED"
        and not foundation_phase.pending_entries
        and not foundation_phase.blocker_ids
        and not foundation_phase.missing_outputs
    )
    start_ready = (
        foundation_status == "NOT_STARTED"
        and foundation_phase.entry_condition_count > 0
        and not foundation_phase.pending_entries
        and not foundation_phase.failed_entries
        and not foundation_phase.blocker_ids
        and all(model.phases[item].status == "PASSED" for item in foundation_phase.dependencies)
    )

    if not upstream_success:
        next_action = {
            "code": "AWAIT_OR_REPAIR_EXACT_CHECKS",
            "kind": "repair",
            "phase": foundation_id,
        }
    elif transition_ready:
        next_action = {
            "code": "CREATE_ACCEPTANCE_STATE_REVISION",
            "kind": "acceptance",
            "phase": foundation_id,
        }
    elif start_ready:
        next_action = {
            "code": "START_FOUNDATION_PHASE",
            "kind": "phase",
            "phase": foundation_id,
        }
    elif accepted_ready:
        next_action = {
            "code": "STOP_AT_FOUNDATION_BOUNDARY",
            "kind": "stop",
            "phase": foundation_id,
        }
    elif foundation_status == "NOT_STARTED":
        reasons.append("FOUNDATION_ENTRY_CONDITIONS_INCOMPLETE")
        next_action = {
            "code": "AWAIT_FOUNDATION_ENTRY_CONDITIONS",
            "kind": "wait",
            "phase": foundation_id,
        }
    else:
        reasons.append("IMPLEMENTATION_EVIDENCE_INCOMPLETE")
        next_action = {"code": "REPAIR_FOUNDATION_STATE", "kind": "repair", "phase": foundation_id}
    eligible = upstream_success and (start_ready or transition_ready or accepted_ready)
    payload: dict[str, object] = {
        "schema_version": 1,
        "commit_sha": model.exact_sha,
        "validation_lane": _track_payload(state, "validation_track"),
        "foundation_lane": _track_payload(state, "foundation_track"),
        "passed_prerequisite_chain": _passed_prerequisites(model),
        "blockers": {
            "external": external,
            "technical": technical,
            "human_decision": human,
        },
        "next_action": next_action,
        "autonomous_acceptance": {
            "eligible": eligible,
            "reason_codes": sorted(set(reasons)),
        },
    }
    return GateProjection(payload=payload, upstream_success=upstream_success)


def _markdown_cell(value: object) -> str:
    text = "none" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "\\|")


def render_step_summary(projection: GateProjection) -> str:
    """Render the bounded deterministic GitHub Step Summary."""

    payload = projection.payload
    validation = _mapping(payload["validation_lane"], "projection_invalid")
    foundation = _mapping(payload["foundation_lane"], "projection_invalid")
    blockers = _mapping(payload["blockers"], "projection_invalid")
    next_action = _mapping(payload["next_action"], "projection_invalid")
    acceptance = _mapping(payload["autonomous_acceptance"], "projection_invalid")
    chain = _string_list(payload["passed_prerequisite_chain"], "projection_invalid")
    lines = [
        "# Gate projection",
        "",
        f"Exact commit: `{_markdown_cell(payload['commit_sha'])}`",
        "",
        "| Lane | Phase | Status | Gate |",
        "| --- | --- | --- | --- |",
        "| Validation | "
        + " | ".join(_markdown_cell(validation[key]) for key in ("phase", "status", "gate"))
        + " |",
        "| Foundation | "
        + " | ".join(_markdown_cell(foundation[key]) for key in ("phase", "status", "gate"))
        + " |",
        "",
        "## Passed prerequisite chain",
        "",
        ", ".join(f"`{_markdown_cell(item)}`" for item in chain) if chain else "None",
    ]
    for category in ("external", "technical", "human_decision"):
        values = _string_list(blockers[category], "projection_invalid")
        lines.extend(
            (
                "",
                "## " + category.replace("_", " ").title() + " blockers",
                "",
                *(f"- `{_markdown_cell(item)}`" for item in values),
            )
        )
        if not values:
            lines.append("None")
    lines.extend(
        (
            "",
            "## Next action",
            "",
            f"`{_markdown_cell(next_action['kind'])}` / `{_markdown_cell(next_action['phase'])}` / "
            f"`{_markdown_cell(next_action['code'])}`",
            "",
            "## Autonomous acceptance",
            "",
            "Eligible" if acceptance["eligible"] is True else "Not eligible",
        )
    )
    reasons = _string_list(acceptance["reason_codes"], "projection_invalid")
    lines.append(
        ", ".join(f"`{_markdown_cell(item)}`" for item in reasons) if reasons else "No reason codes"
    )
    return "\n".join(lines) + "\n"


def _append_summary(repository_root: Path, path: Path, summary: str) -> None:
    resolved = path.resolve()
    if resolved.is_relative_to(repository_root.resolve()) or not resolved.parent.is_dir():
        raise _violation("summary_path_invalid")
    with resolved.open("a", encoding="utf-8", newline="\n") as output:
        output.write(summary)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and project deterministic phase state")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "project"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--repository-root", type=Path, default=Path.cwd())
        subparser.add_argument("--expected-sha", required=True)
        if command == "project":
            subparser.add_argument("--check-result", action="append", default=[])
            subparser.add_argument("--require-check-results", action="store_true")
            subparser.add_argument("--github-summary", type=Path)
    return parser


def main(arguments: list[str] | None = None) -> int:
    """Run the command-line controller with fixed safe failures."""

    try:
        namespace = _parser().parse_args(arguments)
        root = cast(Path, namespace.repository_root)
        model = validate_repository(root, cast(str, namespace.expected_sha))
        if namespace.command == "validate":
            print(f"phase-gate: valid exact head {model.exact_sha}")
            return 0
        projection = build_projection(
            model,
            cast(list[str], namespace.check_result),
            require_check_results=cast(bool, namespace.require_check_results),
        )
        payload = projection.as_json()
        print(payload, end="")
        summary_path = cast(Path | None, namespace.github_summary)
        if summary_path is not None:
            _append_summary(root, summary_path, render_step_summary(projection))
        return 0 if projection.upstream_success else 1
    except GateViolation as error:
        print(f"phase-gate-error: {error}", file=sys.stderr)
        return 1
    except (OSError, subprocess.SubprocessError):
        print("phase-gate-error: controller_io_failure", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
