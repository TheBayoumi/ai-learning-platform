from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.schemas import (
    CollisionFingerprintView,
    PlanRequest,
    TaskExposureView,
)
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    StoredLearnerState,
    TaskExposureConflictError,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "g05-race-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def _fingerprint(exposure: TaskExposureView) -> CollisionFingerprintView:
    return CollisionFingerprintView(
        item_family_id=exposure.item_family_id,
        blueprint_id=exposure.blueprint_id,
        semantic_fingerprint=exposure.semantic_fingerprint,
        semantic_signature=exposure.semantic_signature,
        semantic_tokens=list(exposure.semantic_tokens),
        served_at=exposure.served_at,
    )


class RaceRepository:
    def __init__(self) -> None:
        self.commits: list[LearnerStateCommit] = []

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        del account_id, learner_id
        return None

    async def delete_account(self, *, account_id: str) -> bool:
        del account_id
        return False

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        self.commits.append(request)
        if len(self.commits) == 1:
            raise TaskExposureConflictError
        return StoredLearnerState(
            account_id=request.account_id,
            learner_id=request.learner_id,
            version=0 if request.expected_version is None else request.expected_version + 1,
            state=request.state,
            updated_at=request.occurred_at,
        )


class RaceExposureIndex:
    def __init__(self, collision: CollisionFingerprintView) -> None:
        self.collision = collision
        self.calls = 0

    async def list_task_collision_fingerprints(
        self,
        *,
        item_family_ids: tuple[str, ...],
    ) -> tuple[CollisionFingerprintView, ...]:
        assert item_family_ids
        self.calls += 1
        return () if self.calls == 1 else (self.collision,)


def test_generated_plan_rereads_and_rebinds_after_concurrent_exposure_conflict() -> None:
    core = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = core.create_plan(PlanRequest(learner_name="Concurrent Learner", weekly_hours=4))
    original = plan.active_plan_version.task_exposures[0]
    repository = RaceRepository()
    index = RaceExposureIndex(_fingerprint(original))
    service = PersistentLearningService(
        secret=_SECRET,
        repository=cast(Any, repository),
        exposure_repository=index,
        clock=lambda: _NOW,
    )

    stored, rebound = asyncio.run(
        service._commit_generated_plan(
            account_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            learner_id=UUID(plan.learner_id),
            expected_version=None,
            idempotency_key="g05-race-create-0001",
            event_type="learner.plan.created",
            plan=plan,
        )
    )

    assert index.calls == 2
    assert len(repository.commits) == 2
    assert rebound.active_plan_version.task_exposures[0].semantic_signature != (
        original.semantic_signature
    )
    assert stored.state.active_plan_version_id == rebound.active_plan_version.plan_version_id
