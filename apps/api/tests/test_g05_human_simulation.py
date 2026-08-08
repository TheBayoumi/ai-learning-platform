from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.blueprints import semantic_similarity
from ai_learning_platform_api.learning.schemas import PlanRequest, ReplanRequest

SECRET = "g05-human-simulation-secret-that-is-long-enough-123456"
NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def _service() -> LearningPlanService:
    values = iter(
        [
            UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        ]
    )
    return LearningPlanService(SECRET, clock=lambda: NOW, id_factory=lambda: next(values))


def test_same_track_two_learner_pair_gets_comparable_but_nonidentical_work() -> None:
    service = _service()
    request = PlanRequest(
        learner_name="Identical Profile",
        experience_summary="FastAPI and PostgreSQL learner",
        weekly_hours=2,
    )

    learner_a = service.create_plan(request)
    learner_b = service.create_plan(request)

    assert learner_a.current_activity is not None
    assert learner_b.current_activity is not None
    a = learner_a.current_activity
    b = learner_b.current_activity
    assert a.blueprint_id == b.blueprint_id
    assert a.blueprint_approval_id == b.blueprint_approval_id
    assert a.blueprint_approval_id
    assert a.rubric_version == b.rubric_version
    assert a.id != b.id
    assert a.scenario_tags != b.scenario_tags
    assert a.objective != b.objective
    assert a.instance_requirements != b.instance_requirements
    assert a.instance_contract_hash != b.instance_contract_hash
    assert set(a.instance_requirements).issubset(a.acceptance_criteria)
    assert set(b.instance_requirements).issubset(b.acceptance_criteria)


def test_repeated_regeneration_never_reuses_recent_served_scenario() -> None:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Regeneration Learner", weekly_hours=2))
    prior: list[list[str]] = []

    for _ in range(10):
        assert plan.current_activity is not None
        activity = plan.current_activity
        assert all(semantic_similarity(activity.semantic_tokens, old) < 0.80 for old in prior)
        prior.append(list(activity.semantic_tokens))
        plan = service.replan(
            ReplanRequest(
                state_token=plan.state_token,
                weekly_hours=2,
                focus_competency_ids=[],
            )
        )


def test_returning_learner_replays_exact_instance_contract_and_exposure_ledger() -> None:
    service = _service()
    plan = service.create_plan(PlanRequest(learner_name="Returning Learner", weekly_hours=4))
    resumed = service.resume(plan.state_token)

    assert resumed.current_activity == plan.current_activity
    assert resumed.current_activity is not None
    assert resumed.current_activity.instance_contract_hash
    assert resumed.active_plan_version.task_exposures == plan.active_plan_version.task_exposures
    assert resumed.state_token == plan.state_token
