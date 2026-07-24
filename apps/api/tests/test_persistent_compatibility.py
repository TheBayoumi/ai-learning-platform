"""End-to-end API tests for the existing UI contract over durable state."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import httpx
from fastapi import FastAPI

from ai_learning_platform_api.persistence.contracts import (
    LearnerStateCommit,
    LearnerStateConflictError,
    StoredLearnerState,
)
from ai_learning_platform_api.persistence.service import PersistentLearningService
from ai_learning_platform_api.transport.http.persistence import create_runtime_router
from ai_learning_platform_api.transport.http.persistent_compatibility import (
    PersistentCompatibilityService,
    create_persistent_compatibility_router,
)

_SIGNING_KEY = "compatibility-" + ("x" * 32)
_ACCOUNT_ID = "55555555-5555-4555-8555-555555555555"
_COMMAND_ID = "66666666-6666-4666-8666-666666666666"
_NOW = datetime(2026, 7, 24, 14, 0, tzinfo=UTC)


class MemoryRepository:
    def __init__(self) -> None:
        self.values: dict[tuple[str, UUID], StoredLearnerState] = {}
        self.idempotent: dict[tuple[str, str], StoredLearnerState] = {}

    async def load(self, *, account_id: str, learner_id: UUID) -> StoredLearnerState | None:
        return self.values.get((account_id, learner_id))

    async def commit(self, request: LearnerStateCommit) -> StoredLearnerState:
        idempotent = self.idempotent.get((request.account_id, request.idempotency_key))
        if idempotent is not None:
            return idempotent
        current = self.values.get((request.account_id, request.learner_id))
        if request.expected_version is None:
            if current is not None:
                raise LearnerStateConflictError
            version = 0
        else:
            if current is None or current.version != request.expected_version:
                raise LearnerStateConflictError
            version = current.version + 1
        stored = StoredLearnerState(
            account_id=request.account_id,
            learner_id=request.learner_id,
            version=version,
            state=request.state,
            updated_at=request.occurred_at,
        )
        self.values[(request.account_id, request.learner_id)] = stored
        self.idempotent[(request.account_id, request.idempotency_key)] = stored
        return stored


def _app() -> FastAPI:
    persistent = PersistentLearningService(
        secret=_SIGNING_KEY,
        repository=MemoryRepository(),
        clock=lambda: _NOW,
    )
    app = FastAPI()
    app.include_router(create_runtime_router("postgres"))
    app.include_router(
        create_persistent_compatibility_router(
            PersistentCompatibilityService(
                secret=_SIGNING_KEY,
                persistent=persistent,
            )
        )
    )
    return app


async def _request(
    method: str,
    path: str,
    *,
    body: object | None = None,
    account_id: str = _ACCOUNT_ID,
    command_id: str = _COMMAND_ID,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app())
    headers = {
        "x-platform-account-id": account_id,
        "x-platform-command-id": command_id,
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, json=body, headers=headers)


def test_runtime_and_complete_existing_ui_flow() -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            runtime = await client.get("/api/v1/runtime")
            assert runtime.json() == {"persistence_mode": "postgres"}

            created = await client.post(
                "/api/v1/plans",
                headers={
                    "x-platform-account-id": _ACCOUNT_ID,
                    "x-platform-command-id": _COMMAND_ID,
                },
                json={
                    "learner_name": "Mahmoud",
                    "target_role": "junior-python-backend-engineer",
                    "weekly_hours": 8,
                    "experience_summary": "Embedded to backend transition",
                    "ratings": [],
                },
            )
            assert created.status_code == 201
            plan = created.json()
            activity = plan["current_activity"]
            assert activity is not None

            resumed = await client.post(
                "/api/v1/plans/resume",
                headers={
                    "x-platform-account-id": _ACCOUNT_ID,
                    "x-platform-command-id": "77777777-7777-4777-8777-777777777777",
                },
                json={"state_token": plan["state_token"]},
            )
            assert resumed.status_code == 200
            assert resumed.json()["learner_id"] == plan["learner_id"]

            progressed = await client.post(
                "/api/v1/progress",
                headers={
                    "x-platform-account-id": _ACCOUNT_ID,
                    "x-platform-command-id": "88888888-8888-4888-8888-888888888888",
                },
                json={
                    "state_token": plan["state_token"],
                    "activity_id": activity["id"],
                    "reflection": "Implemented and verified.",
                    "evidence_reference": "commit/abc",
                    "criteria_met": activity["acceptance_criteria"],
                    "confidence": 3,
                },
            )
            assert progressed.status_code == 200
            progressed_plan = progressed.json()
            assert progressed_plan["completed_count"] == 1

            stale = await client.post(
                "/api/v1/plans/replan",
                headers={
                    "x-platform-account-id": _ACCOUNT_ID,
                    "x-platform-command-id": "99999999-9999-4999-8999-999999999999",
                },
                json={
                    "state_token": plan["state_token"],
                    "weekly_hours": 10,
                    "focus_competency_ids": [],
                },
            )
            assert stale.status_code == 409
            assert stale.json()["detail"]["code"] == "LEARNER_STATE_CONFLICT"

            attempt = await client.post(
                "/api/v1/assessments/start",
                headers={"x-platform-account-id": _ACCOUNT_ID},
                json={
                    "state_token": progressed_plan["state_token"],
                    "question_count": 2,
                },
            )
            assert attempt.status_code == 200
            attempt_body = attempt.json()
            answers = [
                {
                    "question_id": question["id"],
                    "option_id": question["options"][0]["id"],
                }
                for question in attempt_body["questions"]
            ]
            submitted = await client.post(
                "/api/v1/assessments/submit",
                headers={
                    "x-platform-account-id": _ACCOUNT_ID,
                    "x-platform-command-id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                },
                json={
                    "state_token": progressed_plan["state_token"],
                    "attempt_token": attempt_body["attempt_token"],
                    "answers": answers,
                },
            )
            assert submitted.status_code == 200
            assert submitted.json()["plan"]["assessment_history"]

    asyncio.run(scenario())


def test_invalid_request_context_fails_before_storage() -> None:
    response = asyncio.run(
        _request(
            "POST",
            "/api/v1/plans",
            body={"learner_name": "Mahmoud", "ratings": []},
            account_id="not-a-uuid",
        )
    )
    assert response.status_code == 422
