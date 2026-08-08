"""Trusted blueprint registry, learner-bound instance binding, and collision checks."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from ai_learning_platform_api.learning.catalog import RoleDefinition
from ai_learning_platform_api.learning.schemas import ActivityView, TaskExposureView

_BLUEPRINT_VERSION = "2026-08-g05-v1"
_ITEM_FAMILY_VERSION = "2026-08-g05-v1"
_NEAR_DUPLICATE_THRESHOLD = 0.80
_MAX_BIND_ATTEMPTS = 128

_DOMAIN_SCENARIOS = (
    "latency-sensitive API",
    "batch data import",
    "multi-tenant admin workflow",
    "event-driven worker",
    "scheduled reconciliation job",
    "read-heavy reporting endpoint",
    "write-heavy transactional endpoint",
    "background document processor",
    "feature-flag rollout",
    "external provider integration",
    "audit-log pipeline",
    "idempotent command handler",
    "large dataset migration",
    "rate-limited public API",
    "failure-recovery worker",
    "production observability path",
)
_FAILURE_SCENARIOS = (
    "partial downstream outage",
    "duplicate delivery",
    "stale write conflict",
    "timeout during dependency call",
    "invalid boundary input",
    "retry storm",
    "schema-version mismatch",
    "missing dependency response",
    "transaction rollback",
    "concurrent update",
    "slow query regression",
    "unexpected empty result",
    "partial batch failure",
    "permission denial",
    "cache inconsistency",
    "process restart during work",
)
_CONSTRAINT_SCENARIOS = (
    "preserve idempotency",
    "keep p95 latency bounded",
    "avoid destructive migration",
    "retain deterministic errors",
    "preserve auditability",
    "support rollback",
    "keep memory bounded",
    "preserve strict typing",
    "avoid broad exception swallowing",
    "maintain transaction isolation",
    "keep retries bounded",
    "preserve backward compatibility",
    "expose measurable verification",
    "keep secrets out of logs",
    "support concurrent callers",
    "prove recovery after interruption",
)


class BlueprintTrustError(ValueError):
    """A served instance cannot be trusted or cannot be made collision-safe."""


@dataclass(frozen=True, slots=True)
class BlueprintIdentity:
    item_family_id: str
    item_family_version: str
    item_family_trust: str
    blueprint_id: str
    blueprint_version: str
    blueprint_trust: str
    rubric_version: str


def _digest(value: str, length: int = 24) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def _rubric_version(deliverable: str, criteria: Iterable[str]) -> str:
    payload = "|".join((deliverable.strip(), *(item.strip() for item in criteria)))
    return f"rubric-{_digest(payload, 20)}"


def _catalog_title(served_title: str) -> str:
    _, separator, title = served_title.partition(". ")
    return title if separator else served_title


def blueprint_identity(role: RoleDefinition, activity: ActivityView) -> BlueprintIdentity:
    """Resolve trust only for an exact code-reviewed catalog template match."""
    competency = next(
        (item for item in role.competencies if item.identifier == activity.competency_id),
        None,
    )
    if competency is None:
        return BlueprintIdentity("", "", "legacy_unverified", "", "", "legacy_unverified", "")
    family_id = f"item-family:{role.identifier}:{role.version}:{competency.identifier}"
    for index, template in enumerate(competency.activities, start=1):
        if (
            template.deliverable == activity.deliverable
            and list(template.acceptance_criteria) == list(activity.acceptance_criteria)
            and _catalog_title(activity.title) == template.title
        ):
            return BlueprintIdentity(
                item_family_id=family_id,
                item_family_version=_ITEM_FAMILY_VERSION,
                item_family_trust="trusted",
                blueprint_id=(
                    f"blueprint:{role.identifier}:{role.version}:{competency.identifier}:{index:02d}"
                ),
                blueprint_version=_BLUEPRINT_VERSION,
                blueprint_trust="trusted",
                rubric_version=_rubric_version(template.deliverable, template.acceptance_criteria),
            )
    return BlueprintIdentity(
        item_family_id=family_id,
        item_family_version=_ITEM_FAMILY_VERSION,
        item_family_trust="trusted",
        blueprint_id="",
        blueprint_version="",
        blueprint_trust="legacy_unverified",
        rubric_version="",
    )


def attach_blueprint_identity(*, role: RoleDefinition, activity: ActivityView) -> ActivityView:
    identity = blueprint_identity(role, activity)
    return activity.model_copy(
        update={
            "item_family_id": identity.item_family_id,
            "item_family_version": identity.item_family_version,
            "item_family_trust": identity.item_family_trust,
            "blueprint_id": identity.blueprint_id,
            "blueprint_version": identity.blueprint_version,
            "blueprint_trust": identity.blueprint_trust,
            "rubric_version": identity.rubric_version,
            "high_stakes_eligible": (
                identity.item_family_trust == "trusted" and identity.blueprint_trust == "trusted"
            ),
        }
    )


def semantic_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 1.0
    union = left_set | right_set
    return len(left_set & right_set) / max(len(union), 1)


def collides(
    *,
    semantic_fingerprint: str,
    semantic_tokens: Iterable[str],
    exposures: Iterable[TaskExposureView],
) -> bool:
    """Reject exact or near-duplicate content against supplied exposure history."""
    for exposure in exposures:
        if exposure.semantic_fingerprint == semantic_fingerprint:
            return True
        if (
            semantic_similarity(semantic_tokens, exposure.semantic_tokens)
            >= _NEAR_DUPLICATE_THRESHOLD
        ):
            return True
    return False


def bind_learner_instance(
    *,
    role: RoleDefinition,
    activity: ActivityView,
    learner_id: str,
    target_fingerprint: str,
    revision: int,
    position: int,
    exposures: Iterable[TaskExposureView],
) -> ActivityView:
    """Bind a trusted blueprint to a deterministic non-colliding learner scenario."""
    if activity.item_family_trust != "trusted" or activity.blueprint_trust != "trusted":
        raise BlueprintTrustError("untrusted blueprint cannot create a high-stakes served instance")
    prior = tuple(exposures)
    for nonce in range(_MAX_BIND_ATTEMPTS):
        seed = hashlib.sha256(
            "|".join(
                (
                    learner_id,
                    role.identifier,
                    role.version,
                    target_fingerprint,
                    str(revision),
                    activity.blueprint_id,
                    str(position),
                    str(nonce),
                )
            ).encode()
        ).hexdigest()
        domain = _DOMAIN_SCENARIOS[int(seed[0:4], 16) % len(_DOMAIN_SCENARIOS)]
        failure = _FAILURE_SCENARIOS[int(seed[4:8], 16) % len(_FAILURE_SCENARIOS)]
        constraint = _CONSTRAINT_SCENARIOS[int(seed[8:12], 16) % len(_CONSTRAINT_SCENARIOS)]
        challenge = f"challenge:{seed[12:28]}"
        semantic_tokens = [
            f"blueprint:{activity.blueprint_id}",
            f"domain:{domain}",
            f"failure:{failure}",
            f"constraint:{constraint}",
        ]
        fingerprint = _digest("|".join((*semantic_tokens, challenge)), 32)
        if collides(
            semantic_fingerprint=fingerprint,
            semantic_tokens=semantic_tokens,
            exposures=prior,
        ):
            continue
        instance_id = f"task-instance-{_digest(f'{learner_id}|{seed}', 28)}"
        scenario = (
            f"Instance constraints: apply this blueprint to a {domain}; handle {failure}; "
            f"and {constraint}. Use {challenge} as the instance identity in the design note."
        )
        return activity.model_copy(
            update={
                "id": instance_id,
                "objective": f"{activity.objective} {scenario}",
                "instance_seed": seed,
                "semantic_fingerprint": fingerprint,
                "semantic_tokens": semantic_tokens,
                "scenario_tags": [domain, failure, constraint, challenge],
                "high_stakes_eligible": True,
            }
        )
    raise BlueprintTrustError("no non-colliding trusted instance remained in the bounded search")


def exposure_from_activity(
    *, activity: ActivityView, plan_version_id: str, served_at: str
) -> TaskExposureView:
    if not activity.instance_seed or not activity.semantic_fingerprint:
        raise BlueprintTrustError("served instance is missing learner-bound traceability")
    return TaskExposureView(
        instance_id=activity.id,
        item_family_id=activity.item_family_id,
        item_family_version=activity.item_family_version,
        blueprint_id=activity.blueprint_id,
        blueprint_version=activity.blueprint_version,
        rubric_version=activity.rubric_version,
        plan_version_id=plan_version_id,
        semantic_fingerprint=activity.semantic_fingerprint,
        semantic_tokens=list(activity.semantic_tokens),
        high_stakes_eligible=activity.high_stakes_eligible,
        served_at=served_at,
    )
