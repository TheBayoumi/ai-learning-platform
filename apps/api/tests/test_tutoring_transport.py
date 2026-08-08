from __future__ import annotations

import asyncio
from typing import cast

import httpx
import pytest
from fastapi import FastAPI

from ai_learning_platform_api.learning.schemas import PlanRequest
from ai_learning_platform_api.learning.service import LearningPlanService
from ai_learning_platform_api.persistence.contracts import (
    LearnerStateConflictError,
    LearnerStateNotFoundError,
    PersistenceUnavailableError,
)
from ai_learning_platform_api.transport.http.tutoring import create_tutoring_router
from ai_learning_platform_api.tutoring.contracts import (
    TutorPolicyDecision,
    TutorProposal,
    TutorSessionState,
    TutorTurnRequest,
)
from ai_learning_platform_api.tutoring.gateway import TutorGatewayError, TutorGatewayMessage, TutorGatewayRequest
from ai_learning_platform_api.tutoring.limits import TutorTurnLimiter
from ai_learning_platform_api.tutoring.policy import InvalidTutorSessionError
from ai_learning_platform_api.tutoring.service import (
    CompletedTutorTurn,
    PreparedTutorTurn,
    TutorProposalError,
    TutorService,
    TutorUnavailableError,
)

ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SECRET = "tutor-transport-secret-with-at-least-thirty-two-bytes"
BODY = {
    "state_token": "signed-token-with-sufficient-length",
    "message": "What should I verify?",
    "move": "hint",
    "history": [],
}
PLAN = LearningPlanService(SECRET).create_plan(PlanRequest(learner_name="Transport Learner"))
assert PLAN.current_activity is not None
DECISION = TutorPolicyDecision(
    decision_id="tutor-decision-transport",
    plan_version_id=PLAN.active_plan_version.plan_version_id,
    activity_id=PLAN.current_activity.id,
    requested_move="hint",
    selected_move="hint",
    hint_level=0,
    assistance="none",
    reason="transport test",
)
PREPARED = PreparedTutorTurn(
    gateway_request=TutorGatewayRequest(
        instructions="bounded",
        messages=(TutorGatewayMessage(role="user", content="question"),),
    ),
    model="fake/model",
    plan=PLAN,
    decision=DECISION,
    prior_session=TutorSessionState(
        learner_id=PLAN.learner_id,
        plan_version_id=PLAN.active_plan_version.plan_version_id,
        activity_id=PLAN.current_activity.id,
    ),
)
COMPLETED = CompletedTutorTurn(
    proposal=TutorProposal(
        selected_move="hint",
        hint_level=0,
        assistance="none",
        message="First step",
        follow_up_question="What would falsify that?",
        answer_revealed=False,
    ),
    session_token="signed-tutor-session-token-with-sufficient-length",
    decision=DECISION,
)


class FakeTutorService:
    def __init__(
        self,
        *,
        prepare_error: Exception | None = None,
        complete_error: Exception | None = None,
    ) -> None:
        self.prepare_error = prepare_error
        self.complete_error = complete_error
        self.account_id: str | None = None
        self.request: TutorTurnRequest | None = None

    async def prepare(self, *, account_id: str, request: TutorTurnRequest) -> PreparedTutorTurn:
        self.account_id = account_id
        self.request = request
        if self.prepare_error is not None:
            raise self.prepare_error
        return PREPARED

    async def complete(self, _: PreparedTutorTurn) -> CompletedTutorTurn:
        if self.complete_error is not None:
            raise self.complete_error
        return COMPLETED


def limiter(
    *,
    max_concurrent_turns: int = 8,
    requests_per_window: int = 20,
    window_seconds: int = 60,
) -> TutorTurnLimiter:
    return TutorTurnLimiter(
        max_concurrent_turns=max_concurrent_turns,
        requests_per_window=requests_per_window,
        window_seconds=window_seconds,
    )


def app_for(service: FakeTutorService, turn_limiter: TutorTurnLimiter) -> FastAPI:
    app = FastAPI()
    app.include_router(create_tutoring_router(cast(TutorService, service), turn_limiter))
    return app


async def post(
    service: FakeTutorService,
    *,
    account_id: str = ACCOUNT_ID,
    turn_limiter: TutorTurnLimiter | None = None,
) -> httpx.Response:
    app = app_for(service, turn_limiter or limiter())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.post(
            "/api/v1/tutor/stream",
            headers={"x-platform-account-id": account_id},
            json=BODY,
        )


def test_tutoring_router_emits_metadata_only_after_validated_completion() -> None:
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
    assert '"decision_id":"tutor-decision-transport"' in response.text
    assert '"tutor_session_token":"signed-tutor-session-token-with-sufficient-length"' in response.text
    assert 'event: delta\ndata: {"text":"First step"}' in response.text
    assert '"follow_up_question":"What would falsify that?"' in response.text


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (TutorGatewayError("private provider detail"), "TUTOR_PROVIDER_UNAVAILABLE"),
        (TutorProposalError("private proposal detail"), "TUTOR_POLICY_REJECTED_OUTPUT"),
    ],
)
def test_tutoring_router_emits_safe_completion_error_without_ledger_metadata(
    error: Exception,
    code: str,
) -> None:
    response = asyncio.run(post(FakeTutorService(complete_error=error)))

    assert response.status_code == 200
    assert code in response.text
    assert "private provider detail" not in response.text
    assert "private proposal detail" not in response.text
    assert "event: meta" not in response.text
    assert "tutor_session_token" not in response.text
    assert "event: done" not in response.text


@pytest.mark.parametrize(
    ("error", "status_code", "code"),
    [
        (TutorUnavailableError(), 503, "TUTOR_UNAVAILABLE"),
        (LearnerStateNotFoundError(), 404, "LEARNER_STATE_NOT_FOUND"),
        (LearnerStateConflictError(), 409, "LEARNER_STATE_CONFLICT"),
        (PersistenceUnavailableError(), 503, "PERSISTENCE_UNAVAILABLE"),
        (InvalidTutorSessionError(), 400, "TUTOR_SESSION_INVALID"),
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


def test_tutoring_router_releases_capacity_after_preflight_failure() -> None:
    turn_limiter = limiter(max_concurrent_turns=1)

    async def exercise() -> None:
        failed_app = app_for(
            FakeTutorService(prepare_error=TutorUnavailableError()),
            turn_limiter,
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=failed_app),
            base_url="http://test",
        ) as client:
            failed = await client.post(
                "/api/v1/tutor/stream",
                headers={"x-platform-account-id": ACCOUNT_ID},
                json=BODY,
            )
        assert failed.status_code == 503

        succeeded = await post(FakeTutorService(), turn_limiter=turn_limiter)
        assert succeeded.status_code == 200

    asyncio.run(exercise())


def test_tutoring_router_rate_limits_before_provider_preflight() -> None:
    service = FakeTutorService()
    turn_limiter = limiter(requests_per_window=1)
    app = app_for(service, turn_limiter)

    async def exercise() -> tuple[httpx.Response, httpx.Response]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/api/v1/tutor/stream",
                headers={"x-platform-account-id": ACCOUNT_ID},
                json=BODY,
            )
            second = await client.post(
                "/api/v1/tutor/stream",
                headers={"x-platform-account-id": ACCOUNT_ID},
                json=BODY,
            )
            return first, second

    first, second = asyncio.run(exercise())
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "TUTOR_RATE_LIMITED"
    assert 1 <= int(second.headers["retry-after"]) <= 60


def test_tutoring_router_rejects_invalid_account_context() -> None:
    service = FakeTutorService()
    response = asyncio.run(post(service, account_id="x" * 36))
    assert response.status_code == 400
    assert response.json()["detail"] == {
        "code": "INVALID_REQUEST_CONTEXT",
        "message": "The request context is invalid.",
    }
    assert service.request is None
