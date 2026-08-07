from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from ai_learning_platform_api.learning.schemas import PlanRequest, PlanView
from ai_learning_platform_api.learning.service import LearningPlanService
from ai_learning_platform_api.tutoring.contracts import TutorHistoryTurn, TutorTurnRequest
from ai_learning_platform_api.tutoring.gateway import TutorGatewayRequest
from ai_learning_platform_api.tutoring.service import TutorService, TutorUnavailableError

SECRET = "tutor-test-secret-that-is-long-enough-123456789"
ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"


class FakeGateway:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.model = "fake/tutor-model"
        self.requests: list[TutorGatewayRequest] = []
        self.closed = False

    async def stream(self, request: TutorGatewayRequest) -> AsyncIterator[str]:
        self.requests.append(request)
        yield "bounded"
        yield " answer"

    async def aclose(self) -> None:
        self.closed = True


def make_plan() -> PlanView:
    return LearningPlanService(SECRET).create_plan(
        PlanRequest(
            learner_name="Private Learner Name",
            experience_summary="Confidential employer transition and token=secret",
            ratings=[],
        )
    )


def test_tutor_service_builds_minimized_non_authoritative_context() -> None:
    gateway = FakeGateway()
    plan = make_plan()
    seen: list[tuple[str, str]] = []

    async def resolve(account_id: str, token: str) -> PlanView:
        seen.append((account_id, token))
        return plan

    service = TutorService(gateway=gateway, resolve_plan=resolve)
    request = TutorTurnRequest(
        state_token=plan.state_token,
        message="What should I verify first?",
        move="hint",
        history=[
            TutorHistoryTurn(role="user", content="I tried a dependency."),
            TutorHistoryTurn(role="assistant", content="Check its lifetime."),
        ],
    )

    async def exercise() -> None:
        prepared = await service.prepare(account_id=ACCOUNT_ID, request=request)
        assert prepared.model == "fake/tutor-model"
        assert prepared.prompt_version == "career-atlas-tutor-v1"
        assert seen == [(ACCOUNT_ID, plan.state_token)]
        instructions = prepared.gateway_request.instructions
        assert "Private Learner Name" not in instructions
        assert "Confidential employer" not in instructions
        assert "token=secret" not in instructions
        assert plan.state_token not in instructions
        assert plan.current_activity is not None
        assert plan.current_activity.title in instructions
        assert "Never claim" in instructions
        assert [message.role for message in prepared.gateway_request.messages] == [
            "user",
            "assistant",
            "user",
        ]
        assert [delta async for delta in service.stream(prepared)] == [
            "bounded",
            " answer",
        ]
        await service.aclose()
        assert gateway.closed is True

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("move", "expected"),
    [
        ("hint", "one progressively useful hint"),
        ("explain", "Explain the relevant concept"),
        ("review", "Review only the work described"),
    ],
)
def test_tutor_service_applies_move_specific_policy(move: str, expected: str) -> None:
    gateway = FakeGateway()
    plan = make_plan()

    async def resolve(_: str, __: str) -> PlanView:
        return plan

    service = TutorService(gateway=gateway, resolve_plan=resolve)

    async def exercise() -> None:
        prepared = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(
                state_token=plan.state_token,
                message="Help",
                move=move,  # type: ignore[arg-type]
            ),
        )
        assert expected in prepared.gateway_request.instructions

    asyncio.run(exercise())


def test_tutor_service_degrades_before_resolving_private_state() -> None:
    gateway = FakeGateway(available=False)
    called = False

    async def resolve(_: str, __: str) -> PlanView:
        nonlocal called
        called = True
        return make_plan()

    service = TutorService(gateway=gateway, resolve_plan=resolve)

    async def exercise() -> None:
        with pytest.raises(TutorUnavailableError):
            await service.prepare(
                account_id=ACCOUNT_ID,
                request=TutorTurnRequest(
                    state_token="signed-token-with-sufficient-length",
                    message="Help",
                ),
            )

    asyncio.run(exercise())
    assert called is False
