from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.blueprint_service import EvidenceRubricMismatchError
from ai_learning_platform_api.learning.schemas import (
    PlanRequest,
    ProgressRequest,
    ReplanRequest,
    TaskExposureView,
    TrustedEvidenceVerdict,
)
from ai_learning_platform_api.learning.service import SignedStateCodec
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    StoredLearnerState,
    TaskExposureConflictError,
)
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "g05-durable-index-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


class ExposureRepository:
    def __init__(self, exposure: TaskExposureView) -> None:
        self.exposure = exposure
        self.calls: list[tuple[str, ...]] = []

    async def list_recent_task_exposures(
        self,
        *,
        item_family_ids: tuple[str, ...],
        limit: int = 512,
    ) -> tuple[TaskExposureView, ...]:
        self.calls.append(item_family_ids)
        assert limit == 512
        return (self.exposure,)


class NoopStateRepository:
    async def load(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None:
        del account_id, learner_id
        return None

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        raise AssertionError(f"unexpected commit: {request.event_type}")

    async def delete_account(self, *, account_id: str) -> bool:
        del account_id
        return False


def test_persistent_service_rebinds_a_forced_cross_learner_collision() -> None:
    core = LearningPlanService(_SECRET)
    plan = core.create_plan(PlanRequest(learner_name="Cohort Learner", weekly_hours=4))
    first = plan.active_plan_version.task_exposures[0]
    external = first.model_copy(update={"instance_id": "other-learner-instance"})
    exposure_repository = ExposureRepository(external)
    service = PersistentLearningService(
        secret=_SECRET,
        repository=cast(Any, NoopStateRepository()),
        exposure_repository=exposure_repository,
        clock=lambda: _NOW,
    )

    rebound = asyncio.run(service._deduplicate_plan(plan))

    assert exposure_repository.calls
    assert rebound.active_plan_version.task_exposures[0].semantic_signature != first.semantic_signature
    assert rebound.active_plan_version.activities[0].id != plan.active_plan_version.activities[0].id


def test_evaluator_uses_immutable_source_rubric_after_plan_history_pruning() -> None:
    service = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = service.create_plan(PlanRequest(learner_name="Pruned Provenance", weekly_hours=4))
    activity = plan.current_activity
    assert activity is not None
    progressed = service.complete_activity(
        ProgressRequest(
            state_token=plan.state_token,
            activity_id=activity.id,
            reflection="Implemented, tested, debugged, and explained the behavior independently.",
            evidence_reference="repo://evidence/pruned-provenance",
            criteria_met=list(activity.acceptance_criteria),
            confidence=4,
        )
    )
    evidence = progressed.evidence_history[-1]
    assert evidence.source_rubric_version == activity.rubric_version
    assert evidence.source_blueprint_id == activity.blueprint_id
    assert evidence.source_high_stakes_eligible is True

    current = progressed
    for _ in range(5):
        current = service.replan(
            ReplanRequest(
                state_token=current.state_token,
                weekly_hours=current.weekly_hours,
                focus_competency_ids=[],
            )
        )
    assert activity.id not in {
        item.id for version in current.plan_history for item in version.activities
    }

    wrong = TrustedEvidenceVerdict(
        evidence_id=evidence.evidence_id,
        competency_id=evidence.competency_id,
        disposition="accepted",
        independence="independent",
        assistance="none",
        reasoning="verified",
        evaluator_id="trusted-evaluator",
        evaluator_version="v1",
        rubric_version="wrong-rubric",
        confidence=95,
    )
    with pytest.raises(EvidenceRubricMismatchError):
        service.evaluate_evidence(state_token=current.state_token, verdict=wrong)

    accepted = service.evaluate_evidence(
        state_token=current.state_token,
        verdict=wrong.model_copy(update={"rubric_version": evidence.source_rubric_version}),
    )
    state = SignedStateCodec(_SECRET).decode(accepted.state_token)
    competency = next(
        item
        for item in state.competency_evidence.values()
        if item.competency_id == evidence.competency_id
    )
    assert competency.status == "independent"


def test_postgres_index_fails_closed_on_semantic_collision_and_cascades() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if database_url is None:
        pytest.skip("DATABASE_URL is required for the PostgreSQL exposure-index integration test")

    async def scenario() -> None:
        runtime = DatabaseRuntime.create(database_url)
        repository = PostgresLearnerStateRepository(runtime.engine)
        codec = SignedStateCodec(_SECRET)
        core = LearningPlanService(_SECRET, clock=lambda: _NOW)
        account_a = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        account_b = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        try:
            first_plan = core.create_plan(PlanRequest(learner_name="Database A", weekly_hours=4))
            first_state = codec.decode(first_plan.state_token)
            first = first_plan.active_plan_version.task_exposures[0]
            await repository.commit(
                LearnerStateCommit(
                    account_id=account_a,
                    learner_id=UUID(first_state.learner_id),
                    expected_version=None,
                    idempotency_key="g05-db-first",
                    event_type="test.g05.first",
                    state=first_state,
                    occurred_at=_NOW,
                )
            )
            indexed = await repository.list_recent_task_exposures(
                item_family_ids=(first.item_family_id,)
            )
            assert any(item.semantic_signature == first.semantic_signature for item in indexed)

            second_plan = core.create_plan(PlanRequest(learner_name="Database B", weekly_hours=4))
            second_state = codec.decode(second_plan.state_token)
            active = next(
                item
                for item in second_state.plan_versions
                if item.plan_version_id == second_state.active_plan_version_id
            )
            collision = active.task_exposures[0].model_copy(
                update={
                    "blueprint_id": first.blueprint_id,
                    "semantic_signature": first.semantic_signature,
                    "semantic_fingerprint": first.semantic_fingerprint,
                }
            )
            poisoned_active = active.model_copy(update={"task_exposures": [collision]})
            poisoned_state = second_state.model_copy(
                update={
                    "plan_versions": [
                        poisoned_active if item.plan_version_id == active.plan_version_id else item
                        for item in second_state.plan_versions
                    ]
                }
            )
            request = LearnerStateCommit(
                account_id=account_b,
                learner_id=UUID(poisoned_state.learner_id),
                expected_version=None,
                idempotency_key="g05-db-collision",
                event_type="test.g05.collision",
                state=poisoned_state,
                occurred_at=_NOW,
            )
            with pytest.raises(TaskExposureConflictError):
                await repository.commit(request)

            assert await repository.delete_account(account_id=account_a) is True
            stored = await repository.commit(request)
            assert stored.version == 0
        finally:
            await repository.delete_account(account_id=account_a)
            await repository.delete_account(account_id=account_b)
            await runtime.shutdown()

    asyncio.run(scenario())
