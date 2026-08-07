"""Concurrent PostgreSQL delivery tests for idempotent learner commands."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select

from ai_learning_platform_api.learning.schemas import PlanRequest
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec
from ai_learning_platform_api.persistence.contracts import LearnerStateCommit
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.models import learner_events, outbox_records
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository

_DATABASE_URL = os.environ.get("AI_PLATFORM_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ephemeral PostgreSQL integration service is not configured",
)


def test_concurrent_identical_commands_return_one_committed_result() -> None:
    assert _DATABASE_URL is not None

    async def scenario() -> None:
        runtime = DatabaseRuntime.create(_DATABASE_URL)
        repository = PostgresLearnerStateRepository(runtime.engine)
        signing_key = "concurrent-" + ("x" * 32)
        plan = LearningPlanService(signing_key).create_plan(
            PlanRequest(learner_name="Concurrent Learner", ratings=[])
        )
        state = SignedStateCodec(signing_key).decode(plan.state_token)
        learner_id = UUID(state.learner_id)
        request = LearnerStateCommit(
            account_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            learner_id=learner_id,
            expected_version=None,
            idempotency_key="concurrent-identical-create-command",
            event_type="learner.plan.created",
            state=state,
            occurred_at=datetime(2026, 7, 24, 16, 0, tzinfo=UTC),
        )

        first, second = await asyncio.gather(
            repository.commit(request),
            repository.commit(request),
        )
        assert first == second

        async with runtime.engine.connect() as connection:
            event_count = await connection.scalar(
                select(func.count())
                .select_from(learner_events)
                .where(learner_events.c.learner_id == learner_id)
            )
            outbox_count = await connection.scalar(
                select(func.count())
                .select_from(outbox_records)
                .join(learner_events, outbox_records.c.event_id == learner_events.c.id)
                .where(learner_events.c.learner_id == learner_id)
            )
        assert event_count == 1
        assert outbox_count == 1
        await runtime.shutdown()

    asyncio.run(scenario())
