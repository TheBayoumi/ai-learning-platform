from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.schemas import PlanRequest
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    LearnerStateNotFoundError,
    ReplayDivergenceError,
    StoredLearnerState,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "g09-account-export-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 18, 0, tzinfo=UTC)
_ACCOUNT = "g09-export-account"


class ExportRepository:
    def __init__(self, stored: tuple[StoredLearnerState, ...]) -> None:
        self.stored = list(stored)
        self.replay_override: StoredLearnerState | None = None

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        return next(
            (
                item
                for item in self.stored
                if item.account_id == account_id and item.learner_id == learner_id
            ),
            None,
        )

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        raise AssertionError("export test must not commit")

    async def delete_account(self, *, account_id: str) -> bool:
        before = len(self.stored)
        self.stored = [item for item in self.stored if item.account_id != account_id]
        return len(self.stored) != before

    async def list_account_states(
        self,
        *,
        account_id: str,
    ) -> tuple[StoredLearnerState, ...]:
        return tuple(item for item in self.stored if item.account_id == account_id)

    async def replay(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None:
        if self.replay_override is not None:
            return self.replay_override
        return await self.load(account_id=account_id, learner_id=learner_id)


def _stored(name: str, learner_id: UUID, version: int) -> StoredLearnerState:
    core = LearningPlanService(
        _SECRET,
        clock=lambda: _NOW,
        id_factory=lambda: learner_id,
    )
    plan = core.create_plan(PlanRequest(learner_name=name, weekly_hours=4))
    state = core._codec.decode(plan.state_token).model_copy(update={"storage_mode": "durable"})
    return StoredLearnerState(
        account_id=_ACCOUNT,
        learner_id=learner_id,
        version=version,
        state=state,
        updated_at=_NOW,
    )


def test_export_returns_all_owned_learners_with_replay_and_resource_audit() -> None:
    first = _stored("Export One", UUID("90000000-0000-4000-8000-000000000001"), 2)
    second = _stored("Export Two", UUID("90000000-0000-4000-8000-000000000002"), 5)
    repository = ExportRepository((first, second))
    service = PersistentLearningService(
        secret=_SECRET,
        repository=repository,
        export_repository=repository,
        replay_repository=repository,
        clock=lambda: _NOW,
    )

    exported = asyncio.run(service.export_account(account_id=_ACCOUNT))

    assert exported.schema_version == 1
    assert [item.learner_id for item in exported.learners] == [first.learner_id, second.learner_id]
    assert [item.aggregate_version for item in exported.learners] == [2, 5]
    assert all(item.audit.replay_verified for item in exported.learners)
    assert all(item.audit.within_resource_bounds for item in exported.learners)
    assert all(item.audit.claim_integrity_verified for item in exported.learners)
    payload = exported.model_dump_json()
    assert _ACCOUNT not in payload
    assert "server_secrets" in exported.redactions
    assert "provider_credentials" in exported.redactions
    assert "unlinkable_task_collision_fingerprints" in exported.retention_notes


def test_export_fails_closed_when_append_only_replay_diverges() -> None:
    stored = _stored("Replay Divergence", UUID("90000000-0000-4000-8000-000000000003"), 4)
    repository = ExportRepository((stored,))
    repository.replay_override = StoredLearnerState(
        account_id=stored.account_id,
        learner_id=stored.learner_id,
        version=3,
        state=stored.state,
        updated_at=stored.updated_at,
    )
    service = PersistentLearningService(
        secret=_SECRET,
        repository=repository,
        export_repository=repository,
        replay_repository=repository,
        clock=lambda: _NOW,
    )

    with pytest.raises(ReplayDivergenceError):
        asyncio.run(service.export_account(account_id=_ACCOUNT))


def test_export_is_unavailable_after_account_deletion() -> None:
    stored = _stored("Deleted Export", UUID("90000000-0000-4000-8000-000000000004"), 0)
    repository = ExportRepository((stored,))
    service = PersistentLearningService(
        secret=_SECRET,
        repository=repository,
        export_repository=repository,
        replay_repository=repository,
        clock=lambda: _NOW,
    )

    assert asyncio.run(service.delete_account(account_id=_ACCOUNT)) is True
    with pytest.raises(LearnerStateNotFoundError):
        asyncio.run(service.export_account(account_id=_ACCOUNT))
