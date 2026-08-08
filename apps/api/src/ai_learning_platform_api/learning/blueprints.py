"""Trusted blueprint registry, learner-bound instance binding, and collision checks."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass

from ai_learning_platform_api.learning.catalog import RoleDefinition
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    CollisionFingerprintView,
    TaskExposureView,
)

_BLUEPRINT_VERSION = "g05-v1"
_ITEM_FAMILY_VERSION = "g05-v1"
_APPROVAL_VERSION = "g05-approval-v1"
_APPROVED_BY = "product-blueprint-review"
_NEAR_DUPLICATE_THRESHOLD = 0.80
_MAX_BIND_ATTEMPTS = 128

# Explicit version-bound approval registry. A future role revision is untrusted until it is
# deliberately added here after blueprint/rubric review; exact catalog matching alone is not trust.
_APPROVED_ROLE_VERSIONS = {
    "junior-python-backend-engineer": "2026.07-provisional-1",
    "ai-application-engineer": "2026.08-provisional-1",
    "data-engineer": "2026.08-provisional-1",
}

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
class BlueprintApproval:
    """Immutable approval provenance for one exact catalog blueprint revision."""

    approval_id: str
    approved_by: str
    approval_version: str


@dataclass(frozen=True, slots=True)
class BlueprintIdentity:
    item_family_id: str
    item_family_version: str
    item_family_trust: str
    blueprint_id: str
    blueprint_version: str
    blueprint_trust: str
    blueprint_approval_id: str
    blueprint_approved_by: str
    blueprint_approval_version: str
    rubric_version: str


CollisionHistoryEntry = TaskExposureView | CollisionFingerprintView


def _digest(value: str, length: int = 24) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:length]


def _rubric_version(deliverable: str, criteria: Iterable[str]) -> str:
    payload = "|".join((deliverable.strip(), *(item.strip() for item in criteria)))
    return f"rubric-{_digest(payload, 16)}"


def _catalog_title(served_title: str) -> str:
    _, separator, title = served_title.partition(". ")
    return title if separator else served_title


def _approval_for(
    *,
    role: RoleDefinition,
    competency_id: str,
    template_index: int,
    template_title: str,
    template_deliverable: str,
    template_criteria: Iterable[str],
) -> BlueprintApproval | None:
    if _APPROVED_ROLE_VERSIONS.get(role.identifier) != role.version:
        return None
    reviewed_payload = "|".join(
        (
            role.identifier,
            role.version,
            competency_id,
            str(template_index),
            template_title,
            template_deliverable,
            *template_criteria,
            _APPROVAL_VERSION,
        )
    )
    return BlueprintApproval(
        approval_id=f"approval-{_digest(reviewed_payload, 20)}",
        approved_by=_APPROVED_BY,
        approval_version=_APPROVAL_VERSION,
    )


def blueprint_identity(role: RoleDefinition, activity: ActivityView) -> BlueprintIdentity:
    """Resolve trust only for an exact catalog match with explicit version-bound approval."""
    competency = next(
        (item for item in role.competencies if item.identifier == activity.competency_id),
        None,
    )
    if competency is None:
        return BlueprintIdentity(
            "", "", "legacy_unverified", "", "", "legacy_unverified", "", "", "", ""
        )
    family_id = f"family-{_digest(f'{role.identifier}|{role.version}|{competency.identifier}', 16)}"
    for index, template in enumerate(competency.activities, start=1):
        if (
            template.deliverable == activity.deliverable
            and list(template.acceptance_criteria) == list(activity.acceptance_criteria)
            and _catalog_title(activity.title) == template.title
        ):
            approval = _approval_for(
                role=role,
                competency_id=competency.identifier,
                template_index=index,
                template_title=template.title,
                template_deliverable=template.deliverable,
                template_criteria=template.acceptance_criteria,
            )
            template_hash = _digest(
                "|".join((family_id, str(index), template.title, template.deliverable)),
                16,
            )
            trusted = approval is not None
            return BlueprintIdentity(
                item_family_id=family_id,
                item_family_version=_ITEM_FAMILY_VERSION,
                item_family_trust="trusted" if trusted else "legacy_unverified",
                blueprint_id=f"blueprint-{template_hash}",
                blueprint_version=_BLUEPRINT_VERSION,
                blueprint_trust="trusted" if trusted else "legacy_unverified",
                blueprint_approval_id="" if approval is None else approval.approval_id,
                blueprint_approved_by="" if approval is None else approval.approved_by,
                blueprint_approval_version="" if approval is None else approval.approval_version,
                rubric_version=_rubric_version(template.deliverable, template.acceptance_criteria),
            )
    return BlueprintIdentity(
        item_family_id=family_id,
        item_family_version=_ITEM_FAMILY_VERSION,
        item_family_trust="legacy_unverified",
        blueprint_id="",
        blueprint_version="",
        blueprint_trust="legacy_unverified",
        blueprint_approval_id="",
        blueprint_approved_by="",
        blueprint_approval_version="",
        rubric_version="",
    )


def attach_blueprint_identity(*, role: RoleDefinition, activity: ActivityView) -> ActivityView:
    identity = blueprint_identity(role, activity)
    approved = bool(
        identity.blueprint_approval_id
        and identity.blueprint_approved_by
        and identity.blueprint_approval_version
    )
    return activity.model_copy(
        update={
            "item_family_id": identity.item_family_id,
            "item_family_version": identity.item_family_version,
            "item_family_trust": identity.item_family_trust,
            "blueprint_id": identity.blueprint_id,
            "blueprint_version": identity.blueprint_version,
            "blueprint_trust": identity.blueprint_trust,
            "blueprint_approval_id": identity.blueprint_approval_id,
            "blueprint_approved_by": identity.blueprint_approved_by,
            "blueprint_approval_version": identity.blueprint_approval_version,
            "rubric_version": identity.rubric_version,
            "high_stakes_eligible": (
                approved
                and identity.item_family_trust == "trusted"
                and identity.blueprint_trust == "trusted"
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
    semantic_signature: str,
    semantic_tokens: Iterable[str],
    exposures: Iterable[CollisionHistoryEntry],
) -> bool:
    """Reject exact or near-duplicate content against supplied exposure history."""
    for exposure in exposures:
        if exposure.semantic_fingerprint == semantic_fingerprint:
            return True
        if exposure.semantic_signature == semantic_signature:
            return True
        if (
            semantic_similarity(semantic_tokens, exposure.semantic_tokens)
            >= _NEAR_DUPLICATE_THRESHOLD
        ):
            return True
    return False


def _instance_requirements(
    *, domain: str, failure: str, constraint: str, challenge: str
) -> list[str]:
    return [
        f"The deliverable explicitly applies the blueprint to the {domain} scenario",
        f"The deliverable demonstrates handling of {failure}",
        f"The verification evidence demonstrates how the solution will {constraint}",
        f"The design or verification note records instance identity {challenge}",
    ]


def bind_learner_instance(
    *,
    role: RoleDefinition,
    activity: ActivityView,
    learner_id: str,
    target_fingerprint: str,
    revision: int,
    position: int,
    exposures: Iterable[CollisionHistoryEntry],
) -> ActivityView:
    """Bind an approved blueprint to a deterministic, enforceable non-colliding scenario."""
    if (
        activity.item_family_trust != "trusted"
        or activity.blueprint_trust != "trusted"
        or not activity.blueprint_approval_id
        or not activity.blueprint_approved_by
        or not activity.blueprint_approval_version
    ):
        raise BlueprintTrustError(
            "unapproved blueprint cannot create a high-stakes served instance"
        )
    prior = tuple(exposures)
    for nonce in range(_MAX_BIND_ATTEMPTS):
        full_seed = hashlib.sha256(
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
        domain_index = int(full_seed[0:4], 16) % len(_DOMAIN_SCENARIOS)
        failure_index = int(full_seed[4:8], 16) % len(_FAILURE_SCENARIOS)
        constraint_index = int(full_seed[8:12], 16) % len(_CONSTRAINT_SCENARIOS)
        domain = _DOMAIN_SCENARIOS[domain_index]
        failure = _FAILURE_SCENARIOS[failure_index]
        constraint = _CONSTRAINT_SCENARIOS[constraint_index]
        challenge = f"challenge:{full_seed[12:28]}"
        semantic_tokens = [
            f"b:{_digest(activity.blueprint_id, 8)}",
            f"d:{domain_index:02d}",
            f"f:{failure_index:02d}",
            f"c:{constraint_index:02d}",
        ]
        semantic_signature = _digest("|".join(semantic_tokens), 24)
        fingerprint = _digest("|".join((*semantic_tokens, challenge)), 24)
        if collides(
            semantic_fingerprint=fingerprint,
            semantic_signature=semantic_signature,
            semantic_tokens=semantic_tokens,
            exposures=prior,
        ):
            continue
        instance_id = (
            f"activity-build-{activity.competency_id}-{_digest(f'{learner_id}|{full_seed}', 12)}"
        )
        requirements = _instance_requirements(
            domain=domain,
            failure=failure,
            constraint=constraint,
            challenge=challenge,
        )
        scenario = (
            f"Instance constraints: apply this blueprint to a {domain}; handle {failure}; "
            f"and {constraint}. Use {challenge} as the instance identity in the design note."
        )
        contract_payload = "|".join(
            (
                activity.blueprint_id,
                activity.blueprint_version,
                activity.blueprint_approval_id,
                activity.rubric_version,
                semantic_signature,
                *requirements,
            )
        )
        return activity.model_copy(
            update={
                "id": instance_id,
                "objective": f"{activity.objective} {scenario}",
                "acceptance_criteria": [*activity.acceptance_criteria, *requirements],
                "instance_seed": full_seed[:32],
                "semantic_fingerprint": fingerprint,
                "semantic_signature": semantic_signature,
                "semantic_tokens": semantic_tokens,
                "scenario_tags": [
                    f"d:{domain_index:02d}",
                    f"f:{failure_index:02d}",
                    f"c:{constraint_index:02d}",
                ],
                "instance_requirements": requirements,
                "instance_contract_hash": f"instance-{_digest(contract_payload, 32)}",
                "high_stakes_eligible": True,
            }
        )
    raise BlueprintTrustError("no non-colliding trusted instance remained in the bounded search")


def exposure_from_activity(
    *, activity: ActivityView, plan_version_id: str, served_at: str
) -> TaskExposureView:
    if (
        not activity.instance_seed
        or not activity.semantic_fingerprint
        or not activity.instance_contract_hash
    ):
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
        semantic_signature=activity.semantic_signature,
        semantic_tokens=list(activity.semantic_tokens),
        instance_contract_hash=activity.instance_contract_hash,
        high_stakes_eligible=activity.high_stakes_eligible,
        served_at=served_at,
    )
