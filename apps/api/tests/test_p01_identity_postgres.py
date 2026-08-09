from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config

from ai_learning_platform_api.identity.contracts import OidcPrincipal
from ai_learning_platform_api.identity.postgres import PostgresIdentityRepository
from ai_learning_platform_api.persistence.database import DatabaseRuntime
from ai_learning_platform_api.persistence.postgres import PostgresLearnerStateRepository
from ai_learning_platform_api.persistence.schemas import PersistentPlanCreateRequest
from ai_learning_platform_api.persistence.service import PersistentLearningService

_DATABASE_URL = os.environ.get("AI_PLATFORM_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ephemeral PostgreSQL integration service is not configured",
)
_SECRET = "p01-identity-postgres-test-secret-longer-than-thirty-two-bytes"
_ANONYMOUS = "44444444-4444-4444-8444-444444444444"


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


def test_identity_resolution_is_stable_and_defaults_to_learner_role() -> None:
    assert _DATABASE_URL is not None
    runtime = DatabaseRuntime.create(_DATABASE_URL)
    repository = PostgresIdentityRepository(runtime.engine)
    principal = OidcPrincipal(issuer="https://tenant.example/", subject="auth0|stable-user")

    first = asyncio.run(repository.resolve(principal))
    second = asyncio.run(repository.resolve(principal))
    other = asyncio.run(
        repository.resolve(
            OidcPrincipal(issuer="https://tenant.example/", subject="auth0|different-user")
        )
    )

    assert first == second
    assert first.roles == ("learner",)
    assert first.account_id != other.account_id
    asyncio.run(runtime.shutdown())


def test_authenticated_identity_can_claim_only_an_unbound_anonymous_account() -> None:
    assert _DATABASE_URL is not None
    runtime = DatabaseRuntime.create(_DATABASE_URL)
    state_repository = PostgresLearnerStateRepository(runtime.engine)
    identity_repository = PostgresIdentityRepository(runtime.engine)
    service = PersistentLearningService(
        secret=_SECRET,
        repository=state_repository,
        exposure_repository=state_repository,
        export_repository=state_repository,
        replay_repository=state_repository,
    )
    identity = asyncio.run(
        identity_repository.resolve(
            OidcPrincipal(issuer="https://tenant.example/", subject="auth0|claim-owner")
        )
    )
    created = asyncio.run(
        service.create_plan(
            account_id=_ANONYMOUS,
            request=PersistentPlanCreateRequest(
                idempotency_key="p01-anonymous-plan-create",
                learner_name="Anonymous P01 Learner",
                ratings=[],
            ),
        )
    )
    learner_id = UUID(created.plan.learner_id)

    assert asyncio.run(
        identity_repository.claim_anonymous_account(
            identity=identity,
            anonymous_account_id=_ANONYMOUS,
        )
    )
    resumed = asyncio.run(service.resume_plan(account_id=identity.account_id, learner_id=learner_id))
    assert resumed.plan.learner_id == str(learner_id)
    assert asyncio.run(state_repository.load(account_id=_ANONYMOUS, learner_id=learner_id)) is None
    assert not asyncio.run(
        identity_repository.claim_anonymous_account(
            identity=identity,
            anonymous_account_id=_ANONYMOUS,
        )
    )
    asyncio.run(runtime.shutdown())
