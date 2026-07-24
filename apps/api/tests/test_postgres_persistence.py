"""Real PostgreSQL tests for snapshots, events, idempotency, and outbox atomicity."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from ai_learning_platform_api.learning.schemas import LearnerState, PlanRequest
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec
from ai_learning_platform_api.persistence.contracts import (
    IdempotencyConflictError,
    LearnerStateCommit,
    LearnerStateConflictError,
)
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.models import learner_events, outbox_records
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository

_DATABASE_URL = os.environ.get("AI_PLATFORM_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ephemeral PostgreSQL integration service is not configured",
)

_SIGNING_KEY = "integration-" + ("x" * 32)
_NOW = datetime(2026, 7, 24, 13, 0, tzinfo=UTC)
_ACCOUNT_ID = "33333333-3333-4333-8333-333333333333"


@pytest.fixture(scope="module", autouse=True)
def migrated_database() -> Iterator[None]:
    if _DATABASE_URL is None:
        yield
        return
    root = Path(__file__).resolve().parents[1]
    configuration = Config(root / "alembic.ini")
    command.downgrade(configuration, "base")
    command.upgrade(configuration, "head")
    try:
        yield
    finally:
        command.downgrade(configuration, "base")


def _state(name: str = "Mahmoud") -> LearnerState:
    service = LearningPlanService(_SIGNING_KEY)
    plan = service.create_plan(PlanRequest(learner_name=name, ratings=[]))
    return SignedStateCodec(_SIGNING_KEY).decode(plan.state_token)


def test_atomic_commit_load_idempotency_and_outbox() -> None:
    assert _DATABASE_URL is not None
    runtime = DatabaseRuntime.create(_DATABASE_URL)
    repository = PostgresLearnerStateRepository(runtime.engine)
    state = _state()
    learner_id = UUID(state.learner_id)
    request = LearnerStateCommit(
        account_id=_ACCOUNT_ID,
        learner_id=learner_id,
        expected_version=None,
        idempotency_key="postgres-create-command-0001",
        event_type="learner.plan.created",
        state=state,
        occurred_at=_NOW,
    )

    first = asyncio.run(repository.commit(request))
    second = asyncio.run(repository.commit(request))
    loaded = asyncio.run(repository.load(account_id=_ACCOUNT_ID, learner_id=learner_id))

    assert first == second == loaded
    assert first.version == 0

    async def counts() -> tuple[int, int]:
        async with runtime.engine.connect() as connection:
            event_count = await connection.scalar(select(func.count()).select_from(learner_events))
            outbox_count = await connection.scalar(select(func.count()).select_from(outbox_records))
        return int(event_count or 0), int(outbox_count or 0)

    assert asyncio.run(counts()) == (1, 1)
    asyncio.run(runtime.shutdown())


def test_conflicts_fail_closed_without_partial_records() -> None:
    assert _DATABASE_URL is not None
    runtime = DatabaseRuntime.create(_DATABASE_URL)
    repository = PostgresLearnerStateRepository(runtime.engine)
    state = _state("Nora")
    learner_id = UUID(state.learner_id)
    initial = LearnerStateCommit(
        account_id=_ACCOUNT_ID,
        learner_id=learner_id,
        expected_version=None,
        idempotency_key="postgres-create-command-0002",
        event_type="learner.plan.created",
        state=state,
        occurred_at=_NOW,
    )
    asyncio.run(repository.commit(initial))

    changed_state = state.model_copy(update={"sequence": 1})
    with pytest.raises(IdempotencyConflictError):
        asyncio.run(
            repository.commit(
                LearnerStateCommit(
                    account_id=_ACCOUNT_ID,
                    learner_id=learner_id,
                    expected_version=0,
                    idempotency_key=initial.idempotency_key,
                    event_type="learner.plan.replanned",
                    state=changed_state,
                    occurred_at=_NOW,
                )
            )
        )

    with pytest.raises(LearnerStateConflictError):
        asyncio.run(
            repository.commit(
                LearnerStateCommit(
                    account_id=_ACCOUNT_ID,
                    learner_id=learner_id,
                    expected_version=9,
                    idempotency_key="postgres-stale-command-0001",
                    event_type="learner.plan.replanned",
                    state=changed_state,
                    occurred_at=_NOW,
                )
            )
        )

    loaded = asyncio.run(repository.load(account_id=_ACCOUNT_ID, learner_id=learner_id))
    assert loaded is not None
    assert loaded.version == 0
    assert loaded.state.sequence == 0
    assert (
        asyncio.run(
            repository.load(
                account_id="44444444-4444-4444-8444-444444444444",
                learner_id=learner_id,
            )
        )
        is None
    )
    asyncio.run(runtime.shutdown())
