from __future__ import annotations

from dataclasses import replace

import pytest

from ai_learning_platform_api.learning.blueprint_service import (
    BlueprintLearningPlanService as LearningPlanService,
)
from ai_learning_platform_api.learning.blueprint_service import UntrustedInstanceEvidenceError
from ai_learning_platform_api.learning.blueprints import (
    BlueprintTrustError,
    _catalog_digest,
    attach_blueprint_identity,
    bind_learner_instance,
    blueprint_identity,
    collides,
    exposure_from_activity,
    semantic_similarity,
)
from ai_learning_platform_api.learning.catalog import ROLE_CATALOG
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    CollisionFingerprintView,
    PlanRequest,
    ProgressRequest,
    ReplanRequest,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import LearningPlanError

_SECRET = "g05-edge-case-secret-with-more-than-thirty-two-bytes"


def _catalog_activity(
    *, competency_id: str | None = None, mutate_criteria: bool = False
) -> ActivityView:
    role = ROLE_CATALOG["junior-python-backend-engineer"]
    competency = role.competencies[0]
    template = competency.activities[0]
    criteria = list(template.acceptance_criteria)
    if mutate_criteria:
        criteria.append("not part of the approved catalog")
    return ActivityView(
        id="catalog-edge-task",
        competency_id=competency_id or competency.identifier,
        competency_name=competency.name,
        title=template.title,
        objective=template.objective,
        deliverable=template.deliverable,
        acceptance_criteria=criteria,
        estimated_minutes=template.estimated_minutes,
    )


def _collision_from(plan_activity: ActivityView) -> CollisionFingerprintView:
    return CollisionFingerprintView(
        item_family_id=plan_activity.item_family_id,
        blueprint_id=plan_activity.blueprint_id,
        semantic_fingerprint=plan_activity.semantic_fingerprint,
        semantic_signature=plan_activity.semantic_signature,
        semantic_tokens=list(plan_activity.semantic_tokens),
        served_at="2026-08-08T12:00:00+00:00",
    )


def test_blueprint_identity_fails_closed_for_unknown_or_unapproved_catalog_state() -> None:
    role = ROLE_CATALOG["junior-python-backend-engineer"]

    unknown = blueprint_identity(role, _catalog_activity(competency_id="unknown-competency"))
    assert unknown.item_family_id == ""
    assert unknown.blueprint_trust == "legacy_unverified"

    mismatched = blueprint_identity(role, _catalog_activity(mutate_criteria=True))
    assert mismatched.item_family_id
    assert mismatched.blueprint_id == ""
    assert mismatched.blueprint_trust == "legacy_unverified"

    unapproved_role = replace(role, version="future-unreviewed-role-version")
    unapproved = blueprint_identity(unapproved_role, _catalog_activity())
    assert unapproved.blueprint_id
    assert unapproved.blueprint_approval_id == ""
    assert unapproved.blueprint_trust == "legacy_unverified"
    attached = attach_blueprint_identity(role=unapproved_role, activity=_catalog_activity())
    assert attached.high_stakes_eligible is False


def test_canonical_objective_change_requires_reviewed_manifest_refresh() -> None:
    role = ROLE_CATALOG["junior-python-backend-engineer"]
    competency = role.competencies[0]
    template = competency.activities[0]
    changed_template = replace(template, objective=f"{template.objective} changed without review")
    changed_competency = replace(
        competency,
        activities=(changed_template, *competency.activities[1:]),
    )
    changed_role = replace(
        role,
        competencies=(changed_competency, *role.competencies[1:]),
    )

    assert _catalog_digest(changed_role) != _catalog_digest(role)
    changed = blueprint_identity(changed_role, _catalog_activity())
    assert changed.item_family_trust == "trusted"
    assert changed.blueprint_trust == "legacy_unverified"
    assert changed.blueprint_approval_id == ""
    assert (
        attach_blueprint_identity(
            role=changed_role,
            activity=_catalog_activity(),
        ).high_stakes_eligible
        is False
    )


def test_item_family_and_blueprint_trust_can_be_demoted_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ai_learning_platform_api.learning.blueprints as blueprints_module

    role = ROLE_CATALOG["junior-python-backend-engineer"]
    activity = _catalog_activity()
    identity = blueprint_identity(role, activity)
    assert identity.item_family_trust == "trusted"
    assert identity.blueprint_trust == "trusted"

    monkeypatch.setitem(
        blueprints_module._APPROVED_ITEM_FAMILY_ROLE_VERSIONS,
        role.identifier,
        "different-unapproved-version",
    )
    separated = blueprint_identity(role, activity)
    assert separated.item_family_trust == "legacy_unverified"
    assert separated.blueprint_trust == "trusted"
    assert attach_blueprint_identity(role=role, activity=activity).high_stakes_eligible is False


def test_similarity_and_collision_checks_cover_exact_near_and_distinct_cases() -> None:
    assert semantic_similarity([], []) == 1.0
    assert semantic_similarity(["a", "b"], ["a", "c"]) == pytest.approx(1 / 3)
    exposure = CollisionFingerprintView(
        item_family_id="family",
        blueprint_id="blueprint",
        semantic_fingerprint="fingerprint",
        semantic_signature="signature",
        semantic_tokens=["a", "b", "c", "d"],
        served_at="2026-08-08T12:00:00+00:00",
    )
    assert collides(
        semantic_fingerprint="fingerprint",
        semantic_signature="other",
        semantic_tokens=["x"],
        exposures=[exposure],
    )
    assert collides(
        semantic_fingerprint="other",
        semantic_signature="signature",
        semantic_tokens=["x"],
        exposures=[exposure],
    )
    assert collides(
        semantic_fingerprint="other",
        semantic_signature="other",
        semantic_tokens=["a", "b", "c", "d", "e"],
        exposures=[exposure],
    )
    assert not collides(
        semantic_fingerprint="other",
        semantic_signature="other",
        semantic_tokens=["x", "y"],
        exposures=[exposure],
    )


def test_generated_one_dimension_variant_is_near_duplicate_but_two_dimension_variant_is_not() -> (
    None
):
    exposure = CollisionFingerprintView(
        item_family_id="family",
        blueprint_id="blueprint",
        semantic_fingerprint="old-fingerprint",
        semantic_signature="old-signature",
        semantic_tokens=["b:abcd", "d:01", "f:02", "c:03"],
        served_at="2026-08-08T12:00:00+00:00",
    )
    assert collides(
        semantic_fingerprint="new-fingerprint",
        semantic_signature="new-signature",
        semantic_tokens=["b:abcd", "d:01", "f:02", "c:09"],
        exposures=[exposure],
    )
    assert not collides(
        semantic_fingerprint="newer-fingerprint",
        semantic_signature="newer-signature",
        semantic_tokens=["b:abcd", "d:01", "f:08", "c:09"],
        exposures=[exposure],
    )


def test_binding_and_exposure_traceability_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    import ai_learning_platform_api.learning.blueprints as blueprints_module

    service = LearningPlanService(_SECRET)
    plan = service.create_plan(PlanRequest(learner_name="Edge Binder"))
    activity = plan.current_activity
    assert activity is not None
    role = ROLE_CATALOG[plan.role.id]

    monkeypatch.setattr(blueprints_module, "_MAX_BIND_ATTEMPTS", 0)
    with pytest.raises(BlueprintTrustError, match="bounded search"):
        bind_learner_instance(
            role=role,
            activity=activity,
            learner_id=plan.learner_id,
            target_fingerprint=plan.active_plan_version.target_fingerprint,
            revision=plan.plan_revision,
            position=1,
            exposures=[],
        )

    malformed = activity.model_copy(update={"instance_contract_hash": ""})
    with pytest.raises(BlueprintTrustError, match="traceability"):
        exposure_from_activity(
            activity=malformed,
            plan_version_id=plan.active_plan_version.plan_version_id,
            served_at=plan.active_plan_version.created_at,
        )


def test_rebind_empty_history_is_exact_resume_and_unknown_activity_fails_closed() -> None:
    service = LearningPlanService(_SECRET)
    plan = service.create_plan(PlanRequest(learner_name="No Collision"))
    resumed = service.rebind_external_exposures(
        state_token=plan.state_token,
        external_exposures=(),
    )
    assert resumed.state_token == plan.state_token

    with pytest.raises(LearningPlanError):
        service.complete_activity(
            ProgressRequest(
                state_token=plan.state_token,
                activity_id="activity-that-does-not-exist",
                reflection="No matching activity exists.",
                criteria_met=[],
                confidence=0,
            )
        )


def test_rebind_rejects_unknown_role_missing_active_plan_and_missing_previous_snapshot() -> None:
    service = LearningPlanService(_SECRET)
    plan = service.create_plan(PlanRequest(learner_name="Corrupt Rebind"))
    activity = plan.current_activity
    assert activity is not None
    collision = _collision_from(activity)
    state = service._codec.decode(plan.state_token)

    unknown_role = state.model_copy(update={"target_role": "unknown-role"})
    with pytest.raises(LearningPlanError):
        service.rebind_external_exposures(
            state_token=service._codec.encode(unknown_role),
            external_exposures=(collision,),
        )

    missing_active = state.model_copy(update={"active_plan_version_id": "missing-plan-version"})
    with pytest.raises(LearningPlanError):
        service.rebind_external_exposures(
            state_token=service._codec.encode(missing_active),
            external_exposures=(collision,),
        )

    replanned = service.replan(
        ReplanRequest(
            state_token=plan.state_token,
            weekly_hours=plan.weekly_hours,
            focus_competency_ids=[],
        )
    )
    replanned_state = service._codec.decode(replanned.state_token)
    active = service._active_plan_version(replanned_state)
    assert active is not None
    isolated = replanned_state.model_copy(update={"plan_versions": [active]})
    with pytest.raises(LearningPlanError):
        service.rebind_external_exposures(
            state_token=service._codec.encode(isolated),
            external_exposures=(_collision_from(active.activities[0]),),
        )


def test_evaluator_rejects_incomplete_immutable_provenance() -> None:
    service = LearningPlanService(_SECRET)
    plan = service.create_plan(PlanRequest(learner_name="Incomplete Provenance"))
    activity = plan.current_activity
    assert activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="Completed every exact task requirement.",
            evidence_reference="repo://complete",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    evidence = progressed.evidence_history[-1]
    state = service._codec.decode(progressed.state_token)
    poisoned = [
        item.model_copy(update={"source_blueprint_approval_id": ""})
        if item.evidence_id == evidence.evidence_id
        else item
        for item in state.evidence_history
    ]
    token = service._codec.encode(state.model_copy(update={"evidence_history": poisoned}))
    with pytest.raises(UntrustedInstanceEvidenceError):
        service.evaluate_evidence(
            state_token=token,
            verdict=TrustedEvidenceVerdict(
                evidence_id=evidence.evidence_id,
                competency_id=evidence.competency_id,
                disposition="accepted",
                independence="independent",
                assistance="none",
                reasoning="verified",
                evaluator_id="trusted-evaluator",
                evaluator_version="v1",
                rubric_version=evidence.source_rubric_version,
                instance_contract_hash=evidence.source_instance_contract_hash,
                confidence=90,
            ),
        )
