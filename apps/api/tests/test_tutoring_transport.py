from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import cast

import httpx
import pytest
from fastapi import FastAPI

from ai_learning_platform_api.persistence.contracts import (
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    PersistenceUnavailableError,
)
from ai_learning_platform_api.transport.http.tutoring import create_tutoring_router
from ai_learning_platform_api.tutoring.contracts import TutorTurnRequest
from ai_learning_platform_api.tutoring.gateway import (
    TutorGatewayError,
    TutorGatewayMessage,
    TutorGatewayRequest,
)
from ai_learning_platform_api.tutoring.service import (
    PreparedTutorTurn,
    TutorService,
    TutorUnavailableError,
)

ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
BODY = {
    "state_token": "signed-token-with-sufficient-length",
    "message": "What should I verify?",
    "move": "hint",
    "history": [],
}
PREPARED = PreparedTutorTurn(
    gateway_request=TutorGatewayRequest(
        instructions="bounded",
        messages=(TutorGatewayMessage(role="user", content="question"),),
    ),
    model="fake/model",
)


class FakeTutorService:
    def __init__(
        self,
        *,
        prepare_error: Exception | None = None,
        stream_error: bool = False,
    ) -> None:
        self.prepare_error = prepare_error
        self.stream_error = stream_error
        self.account_id: str | None = None
        self.request: TutorTurnRequest | None = None

    async def prepare(self, *, account_id: str, request: TutorTurnRequest) -> PreparedTutorTurn:
        self.account_id = account_id
        self.request = request
        if self.prepare_error is not None:
            raise self.prepare_error
        return PREPARED

    async def stream(self, _: PreparedTutorTurn) -> AsyncIterator[str]:
        yield "First"
        if self.stream_error:
            raise TutorGatewayError("secret provider failure")
        yield " step"


async def post(service: FakeTutorService, *, account_id: str = ACCOUNT_ID) -> httpx.Response:
    app = FastAPI()
    app.include_router(create_tutoring_router(cast(TutorService, service)))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post(
            "/api/v1/tutor/stream",
            headers={"x-platform-account-id": account_id},
            json=BODY,
        )


def test_tutoring_router_streams_normalized_events_after_preflight() -> None:
    service = FakeTutorService()
    response = asyncio.run(post(service))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-accel-buffering"] == "no"
    assert service.account_id == ACCOUNT_ID
    assert service.request is not None
    assert "event: meta" in response.text
    assert '"authoritative":false' in response.text
    assert 'event: delta\ndata: {"text":"First"}' in response.text
    assert 'event: delta\ndata: {"text":" step"}' in response.text
    assert 'event: done\ndata: {"status":"complete"}' in response.text


def test_tutoring_router_emits_safe_stream_error_without_mutating_state() -> None:
    response = asyncio.run(post(FakeTutorService(stream_error=True)))
    assert response.status_code == 200
    assert 'event: delta\ndata: {"text":"First"}' in response.text
    assert "TUTOR_PROVIDER_UNAVAILABLE" in response.text
    assert "secret provider failure" not in response.text
    assert "event: done" not in response.text


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (TutorUnavailableError(), 503, "TUTOR_UNAVAILABLE"),
        (LearnerStateNotFoundError(), 404, "LEARNER_STATE_NOT_FOUND"),
        (LearnerStateConflictError(), 409, "LEARNER_STATE_CONFLICT"),
        (PersistenceUnavailableError(), 503, "PERSISTENCE_UNAVAILABLE"),
    ],
)
def test_tutoring_router_maps_preflight_failures(
    error: Exception,
    status_code: int,
    code: str,
) -> None:
    response = asyncio.run(post(FakeTutorService(prepare_error=error)))
    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code


def test_tutoring_router_rejects_invalid_account_context() -> None:
    service = FakeTutorService()
    response = asyncio.run(post(service, account_id="x" * 36))
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "code": "INVALID_REQUEST_CONTEXT",
        "message": "The request context is invalid.",
    }
    assert service.request is None
