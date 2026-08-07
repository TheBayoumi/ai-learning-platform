from __future__ import annotations

import asyncio
from uuid import UUID

import httpx
from fastapi import FastAPI

from ai_learning_platform_api.persistence.contracts import LearnerStateCommit, StoredLearnerState
from ai_learning_platform_api.persistence.service import PersistentLearningService
from ai_learning_platform_api.transport.http.persistent_compatibility import (
    PersistentCompatibilityService,
    create_persistent_compatibility_router,
)

_SIGNING_KEY = "persistent-career-catalog-" + ("x" * 32)


class UnusedRepository:
    """Repository contract stub; catalog reads must not touch persistence."""

    async def load(
        self,
        *,
        account_id: str,
        learner_id: UUID,
    ) -> StoredLearnerState | None:
        raise AssertionError("catalog reads must not load learner state")

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        raise AssertionError("catalog reads must not commit learner state")

    async def delete_account(self, *, account_id: str) -> bool:
        raise AssertionError("catalog reads must not delete learner state")


def _app() -> FastAPI:
    persistent = PersistentLearningService(
        secret=_SIGNING_KEY,
        repository=UnusedRepository(),
    )
    service = PersistentCompatibilityService(secret=_SIGNING_KEY, persistent=persistent)
    app = FastAPI()
    app.include_router(create_persistent_compatibility_router(service))
    return app


async def _get(path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_durable_router_preserves_legacy_roles_and_exposes_full_career_catalog() -> None:
    legacy = asyncio.run(_get("/api/v1/roles"))
    catalog = asyncio.run(_get("/api/v1/career-tracks"))

    assert legacy.status_code == 200
    assert [role["id"] for role in legacy.json()] == ["junior-python-backend-engineer"]

    assert catalog.status_code == 200
    roles = catalog.json()
    assert {role["id"] for role in roles} == {
        "junior-python-backend-engineer",
        "ai-application-engineer",
        "data-engineer",
    }
    assert all(sum(item["weight"] for item in role["competencies"]) == 100 for role in roles)
