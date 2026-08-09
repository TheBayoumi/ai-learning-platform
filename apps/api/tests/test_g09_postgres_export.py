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

from ai_learning_platform_api.learning.schemas import LearnerState, PlanRequest
from ai_learning_platform_api.learning.service import LearningPlanService, SignedStateCodec
from ai_learning_platform_api.persistence.contracts import LearnerStateCommit
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository

_DATABASE_URL = os.environ.get("AI_PLATFORM_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ephemeral PostgreSQL integration service is not configured",
)

_SECRET = "g09-postgres-export-secret-with-more-than-thirty-two-bytes"
_NOW = datetime(2026, 8, 9, 1, 30, tzinfo=UTC)
_ACCOUNT = "99999999-9999-4999-8999-999999999999"
_OTHER_ACCOUNT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


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


def _state(name: str) -> LearnerState:
    core = LearningPlanService(_SECRET, clock=lambda: _NOW)
    plan = core.create_plan(PlanRequest(learner_name=name, ratings=[]))
    return SignedStateCodec(_SECRET).decode(plan.state_token).model_copy(
        update={"storage_mode": "durable"}
    )


def _commit(
    repository: PostgresLearnerStateRepository,
    *,
    account_id: str,
    state: LearnerState,
    key: str,
) -> None:
    asyncio.run(
        repository.commit(
            LearnerStateCommit(
                account_id=account_id,
                learner_id=UUID(state.learner_id),
                expected_version=None,
                idempotency_key=key,
                event_type="learner.plan.created",
                state=state,
                occurred_at=_NOW,
            )
        )
    )


def test_list_account_states_is_complete_owned_and_deterministically_ordered() -> None:
    assert _DATABASE_URL is not None
    runtime = DatabaseRuntime.create(_DATABASE_URL)
    repository = PostgresLearnerStateRepository(runtime.engine)
    first = _state("G09 Export A")
    second = _state("G09 Export B")
    outsider = _state("G09 Other Account")

    _commit(repository, account_id=_ACCOUNT, state=second, key="g09-export-second-command")
    _commit(repository, account_id=_ACCOUNT, state=first, key="g09-export-first-command")
    _commit(repository, account_id=_OTHER_ACCOUNT, state=outsider, key="g09-export-other-command")

    exported = asyncio.run(repository.list_account_states(account_id=_ACCOUNT))
    missing = asyncio.run(
        repository.list_account_states(account_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
    )

    assert {item.learner_id for item in exported} == {UUID(first.learner_id), UUID(second.learner_id)}
    assert [item.learner_id for item in exported] == sorted(item.learner_id for item in exported)
    assert all(item.account_id == _ACCOUNT for item in exported)
    assert UUID(outsider.learner_id) not in {item.learner_id for item in exported}
    assert missing == ()
    asyncio.run(runtime.shutdown())
