from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from ai_learning_platform_api.learning import LearningPlanService
from ai_learning_platform_api.learning.schemas import PlanRequest
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    StoredLearnerState,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService

_SECRET = "g09-human-simulation-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 8, 18, 30, tzinfo=UTC)
_ACCOUNT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_ACCOUNT_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


class SimulationRepository:
    def __init__(self, items: tuple[StoredLearnerState, ...]) -> None:
        self.items = list(items)
        self.force_conflict = False

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        return next(
            (
                item
                for item in self.items
                if item.account_id == account_id and item.learner_id == learner_id
            ),
            None,
        )

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        if self.force_conflict:
            raise LearnerStateConflictError
        current = await self.load(account_id=request.account_id, learner_id=request.learner_id)
        if current is None:
            raise LearnerStateNotFoundError
        if request.expected_version != current.version:
            raise LearnerStateConflictError
        stored = StoredLearnerState(
            account_id=current.account_id,
            learner_id=current.learner_id,
            version=current.version + 1,
            state=request.state,
            updated_at=request.occurred_at,
        )
        self.items = [item for item in self.items if item is not current] + [stored]
        return stored

    async def delete_account(self, *, account_id: str) -> bool:
        before = len(self.items)
        self.items = [item for item in self.items if item.account_id != account_id]
        return len(self.items) != before

    async def list_account_states(
        self,
        *,
        account_id: str,
    ) -> tuple[StoredLearnerState, ...]:
        return tuple(
            sorted(
                (item for item in self.items if item.account_id == account_id),
                key=lambda item: str(item.learner_id),
            )
        )

    async def replay(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None:
        return await self.load(account_id=account_id, learner_id=learner_id)


def _stored(account_id: str, learner_id: UUID, name: str) -> StoredLearnerState:
    core = LearningPlanService(
        _SECRET,
        clock=lambda: _NOW,
        id_factory=lambda: learner_id,
    )
    plan = core.create_plan(PlanRequest(learner_name=name, weekly_hours=4))
    state = core._codec.decode(plan.state_token).model_copy(update={"storage_mode": "durable"})
    return StoredLearnerState(
        account_id=account_id,
        learner_id=learner_id,
        version=0,
        state=state,
        updated_at=_NOW,
    )


def _service(repository: SimulationRepository) -> PersistentLearningService:
    return PersistentLearningService(
        secret=_SECRET,
        repository=repository,
        export_repository=repository,
        replay_repository=repository,
        clock=lambda: _NOW,
    )


def test_multi_learner_owner_exports_only_owned_data() -> None:
    a1 = _stored(_ACCOUNT_A, UUID("91000000-0000-4000-8000-000000000001"), "Owner A One")
    a2 = _stored(_ACCOUNT_A, UUID("91000000-0000-4000-8000-000000000002"), "Owner A Two")
    b1 = _stored(_ACCOUNT_B, UUID("92000000-0000-4000-8000-000000000001"), "Owner B")
    service = _service(SimulationRepository((a1, a2, b1)))

    exported = asyncio.run(service.export_account(account_id=_ACCOUNT_A))

    assert {item.learner_id for item in exported.learners} == {a1.learner_id, a2.learner_id}
    assert b1.learner_id not in {item.learner_id for item in exported.learners}


def test_delete_one_account_preserves_another_accounts_durable_state() -> None:
    a = _stored(_ACCOUNT_A, UUID("91000000-0000-4000-8000-000000000003"), "Delete A")
    b = _stored(_ACCOUNT_B, UUID("92000000-0000-4000-8000-000000000002"), "Keep B")
    repository = SimulationRepository((a, b))
    service = _service(repository)

    assert asyncio.run(service.delete_account(account_id=_ACCOUNT_A)) is True
    with pytest.raises(LearnerStateNotFoundError):
        asyncio.run(service.export_account(account_id=_ACCOUNT_A))
    exported_b = asyncio.run(service.export_account(account_id=_ACCOUNT_B))
    assert [item.learner_id for item in exported_b.learners] == [b.learner_id]


def test_stale_concurrent_write_remains_fail_closed() -> None:
    stored = _stored(_ACCOUNT_A, UUID("91000000-0000-4000-8000-000000000004"), "Concurrent")
    repository = SimulationRepository((stored,))
    repository.force_conflict = True

    with pytest.raises(LearnerStateConflictError):
        asyncio.run(
            repository.commit(
                LearnerStateCommit(
                    account_id=_ACCOUNT_A,
                    learner_id=stored.learner_id,
                    expected_version=0,
                    idempotency_key="g09-concurrent-command-0001",
                    event_type="learner.integration.simulated",
                    state=stored.state,
                    occurred_at=_NOW,
                )
            )
        )


def test_export_audit_preserves_validation_locked_claim_boundary() -> None:
    stored = _stored(_ACCOUNT_A, UUID("91000000-0000-4000-8000-000000000005"), "Locked Claim")
    service = _service(SimulationRepository((stored,)))

    exported = asyncio.run(service.export_account(account_id=_ACCOUNT_A))

    audit = exported.learners[0].audit
    assert audit.claim_integrity_verified is True
    assert audit.replay_verified is True
    assert audit.within_resource_bounds is True
