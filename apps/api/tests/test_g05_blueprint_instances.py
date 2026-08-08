from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.blueprint_service import UntrustedInstanceEvidenceError
from ai_learning_platform_api.learning.blueprints import (
    BlueprintTrustError,
    bind_learner_instance,
    semantic_similarity,
)
from ai_learning_platform_api.learning.catalog import ROLE_CATALOG
from ai_learning_platform_api.learning.planner import target_fingerprint
from ai_learning_platform_api.learning.schemas import (
    ActivityView,
    PlanRequest,
    ProgressRequest,
    ReplanRequest,
    TrustedEvidenceVerdict,
)

SECRET = "g05-blueprint-test-secret-that-is-long-enough-123456"
NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def _ids() -> Callable[[], UUID]:
    values = iter(
        [
            UUID("11111111-1111-4111-8111-111111111111"),
            UUID("22222222-2222-4222-8222-222222222222"),
            UUID("33333333-3333-4333-8333-333333333333"),
            UUID("44444444-4444-4444-8444-444444444444"),
        ]
    )
    return lambda: next(values)


def _service() -> LearningPlanService:
    return LearningPlanService(SECRET, clock=lambda: NOW, id_factory=_ids())


def test_same_track_learners_get_unique_instances_with_shared_rubric() -> None:
    service = _service()
    request = PlanRequest(
        learner_name="Same Name",
        experience_summary="same prior context",
        weekly_hours=2,
    )

    first = service.create_plan(request)
    second = service.create_plan(request)

    assert first.current_activity is not None
    assert second.current_activity is not None
    left = first.current_activity
    right = second.current_activity
    assert left.item_family_trust == "trusted"
    assert left.blueprint_trust == "trusted"
    assert left.high_stakes_eligible is True
    assert right.high_stakes_eligible is True
    assert left.blueprint_id == right.blueprint_id
    assert left.rubric_version == right.rubric_version
    assert left.id != right.id
    assert left.instance_seed != right.instance_seed
    assert left.semantic_fingerprint != right.semantic_fingerprint
    assert left.plan_version_id == first.active_plan_version.plan_version_id
    assert right.plan_version_id == second.active_plan_version.plan_version_id


def test_plan_version_carries_bounded_traceable_exposure_records() -> None:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Traceable Learner", weekly_hours=4))

    exposures = plan.active_plan_version.task_exposures
    assert exposures
    for exposure in exposures:
        activity = next(
            item for item in plan.active_plan_version.activities if item.id == exposure.instance_id
        )
        assert exposure.plan_version_id == plan.active_plan_version.plan_version_id
        assert exposure.blueprint_id == activity.blueprint_id
        assert exposure.rubric_version == activity.rubric_version
        assert exposure.semantic_fingerprint == activity.semantic_fingerprint
        assert exposure.high_stakes_eligible is True


def test_repeated_replanning_rejects_exact_and_near_duplicate_history() -> None:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Repeat Learner", weekly_hours=2))
    seen_tokens: list[list[str]] = []
    seen_fingerprints: set[str] = set()

    for _ in range(12):
        assert plan.current_activity is not None
        activity = plan.current_activity
        assert activity.semantic_fingerprint not in seen_fingerprints
        assert all(
            semantic_similarity(activity.semantic_tokens, prior) < 0.80 for prior in seen_tokens
        )
        seen_fingerprints.add(activity.semantic_fingerprint)
        seen_tokens.append(list(activity.semantic_tokens))
        plan = service.replan(
            ReplanRequest(
                state_token=plan.state_token,
                weekly_hours=2,
                focus_competency_ids=[],
            )
        )
        assert len(plan.state_token) < 65_536
        assert len(plan.active_plan_version.task_exposures) <= 64


def test_untrusted_blueprint_cannot_create_high_stakes_instance() -> None:
    role = ROLE_CATALOG["junior-python-backend-engineer"]
    target = (
        LearningPlanService(SECRET).create_plan(PlanRequest(learner_name="Target Source")).target
    )
    untrusted = ActivityView(
        id="legacy-task",
        competency_id=role.competencies[0].identifier,
        competency_name=role.competencies[0].name,
        title="Legacy generated task",
        objective="Do something generated without a trusted blueprint.",
        deliverable="Artifact",
        acceptance_criteria=["Exists"],
        estimated_minutes=60,
    )

    with pytest.raises(BlueprintTrustError):
        bind_learner_instance(
            role=role,
            activity=untrusted,
            learner_id="learner-1",
            target_fingerprint=target_fingerprint(target),
            revision=1,
            position=1,
            exposures=[],
        )


def test_untrusted_source_instance_cannot_be_promoted_by_trusted_evaluator() -> None:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Trust Boundary", weekly_hours=2))
    assert plan.current_activity is not None
    activity = plan.current_activity
    completed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="I implemented and tested the required behavior independently in detail.",
            evidence_reference="repo://artifact",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    state = service._codec.decode(completed.state_token)
    poisoned_activities = [
        item.model_copy(update={"high_stakes_eligible": False}) if item.id == activity.id else item
        for item in state.activities
    ]
    poisoned_versions = []
    for version in state.plan_versions:
        poisoned_versions.append(
            version.model_copy(
                update={
                    "activities": [
                        item.model_copy(update={"high_stakes_eligible": False})
                        if item.id == activity.id
                        else item
                        for item in version.activities
                    ]
                }
            )
        )
    poisoned = state.model_copy(
        update={"activities": poisoned_activities, "plan_versions": poisoned_versions}
    )
    token = service._codec.encode(poisoned)
    evidence = completed.evidence_history[-1]

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
                rubric_version=activity.rubric_version,
                confidence=95,
            ),
        )
