"""Real PostgreSQL cascade tests for anonymous account deletion."""

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

from ai_learning_platform_api.learning.schemas import PlanRequest
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec
from ai_learning_platform_api.persistence.contracts import LearnerStateCommit
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.models import (
    accounts,
    learner_events,
    learner_states,
    outbox_records,
)
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository

_DATABASE_URL = os.environ.get("AI_PLATFORM_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ephemeral PostgreSQL integration service is not configured",
)

_SECRET = "deletion-integration-" + ("x" * 32)
_NOW = datetime(2026, 8, 7, 4, 0, tzinfo=UTC)
_ACCOUNT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_ACCOUNT_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture(scope="module", autouse=True)
def migrated_database() -> Iterator[None]:
    if _DATABASE_URL is None:
        yield
        return
    root = Path(__file__).resolve().parents[1]
    configuration = Config(str(root / "alembic.ini"))
    command.downgrade(configuration, "base")
    command.upgrade(configuration, "head")
    try:
        yield
    finally:
        command.downgrade(configuration, "base")


def state(name: str):
    plan = LearningPlanService(_SECRET).create_plan(
        PlanRequest(learner_name=name, ratings=[])
    )
    return SignedStateCodec(_SECRET).decode(plan.state_token)


def test_delete_account_cascades_only_the_current_anonymous_account() -> None:
    assert _DATABASE_URL is not None
    runtime = DatabaseRuntime.create(_DATABASE_URL)
    repository = PostgresLearnerStateRepository(runtime.engine)
    state_a = state("Delete A")
    state_b = state("Keep B")

    asyncio.run(
        repository.commit(
            LearnerStateCommit(
                account_id=_ACCOUNT_A,
                learner_id=UUID(state_a.learner_id),
                expected_version=None,
                idempotency_key="delete-account-a-create",
                event_type="learner.plan.created",
                state=state_a,
                occurred_at=_NOW,
            )
        )
    )
    asyncio.run(
        repository.commit(
            LearnerStateCommit(
                account_id=_ACCOUNT_B,
                learner_id=UUID(state_b.learner_id),
                expected_version=None,
                idempotency_key="delete-account-b-create",
                event_type="learner.plan.created",
                state=state_b,
                occurred_at=_NOW,
            )
        )
    )

    assert asyncio.run(repository.delete_account(account_id=_ACCOUNT_A)) is True
    assert asyncio.run(repository.delete_account(account_id=_ACCOUNT_A)) is False
    assert (
        asyncio.run(
            repository.load(
                account_id=_ACCOUNT_A,
                learner_id=UUID(state_a.learner_id),
            )
        )
        is None
    )
    assert (
        asyncio.run(
            repository.load(
                account_id=_ACCOUNT_B,
                learner_id=UUID(state_b.learner_id),
            )
        )
        is not None
    )

    async def counts() -> tuple[int, int, int, int]:
        async with runtime.engine.connect() as connection:
            values = []
            for table in (accounts, learner_states, learner_events, outbox_records):
                count = await connection.scalar(select(func.count()).select_from(table))
                values.append(int(count or 0))
            return tuple(values)  # type: ignore[return-value]

    assert asyncio.run(counts()) == (1, 1, 1, 1)
    asyncio.run(runtime.shutdown())


def test_delete_account_rejects_noncanonical_identifiers_before_sql() -> None:
    assert _DATABASE_URL is not None
    runtime = DatabaseRuntime.create(_DATABASE_URL)
    repository = PostgresLearnerStateRepository(runtime.engine)

    with pytest.raises(ValueError, match="canonical token"):
        asyncio.run(repository.delete_account(account_id=" invalid "))

    asyncio.run(runtime.shutdown())
