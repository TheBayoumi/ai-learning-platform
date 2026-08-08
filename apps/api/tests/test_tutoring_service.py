from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import pytest

from ai_learning_platform_api.learning.schemas import PlanRequest, PlanView
from ai_learning_platform_api.learning.service import LearningPlanService
from ai_learning_platform_api.tutoring.contracts import (
    TutorHistoryTurn,
    TutorTurnRequest,
)
from ai_learning_platform_api.tutoring.gateway import TutorGatewayRequest
from ai_learning_platform_api.tutoring.service import (
    TutorProposalError,
    TutorService,
    TutorUnavailableError,
)

SECRET = "tutor-test-secret-that-is-long-enough-123456789"
ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"


class FakeGateway:
    def __init__(self, *, available: bool = True, malformed: bool = False) -> None:
        self.available = available
        self.model = "fake/tutor-model"
        self.requests: list[TutorGatewayRequest] = []
        self.closed = False
        self.malformed = malformed

    async def stream(self, request: TutorGatewayRequest) -> AsyncIterator[str]:
        self.requests.append(request)
        if self.malformed:
            yield "not-json"
            return
        policy_text = request.instructions.split("POLICY_JSON:\n", maxsplit=1)[1].split(
            "\nLEARNER_CONTEXT_JSON:", maxsplit=1
        )[0]
        policy = json.loads(policy_text)
        yield json.dumps(
            {
                "selected_move": policy["selected_move"],
                "hint_level": policy["hint_level"],
                "assistance": policy["assistance"],
                "message": "What invariant should hold before you change the implementation?",
                "follow_up_question": "What evidence would falsify your current assumption?",
                "answer_revealed": False,
            },
            separators=(",", ":"),
        )

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


def test_tutor_service_builds_minimized_policy_controlled_context() -> None:
    gateway = FakeGateway()
    plan = make_plan()
    seen: list[tuple[str, str]] = []

    async def resolve(account_id: str, token: str) -> PlanView:
        seen.append((account_id, token))
        return plan

    service = TutorService(gateway=gateway, resolve_plan=resolve, session_secret=SECRET)
    request = TutorTurnRequest(
        state_token=plan.state_token,
        message="What should I verify first?",
        move="explain",
        history=[
            TutorHistoryTurn(role="user", content="I tried a dependency."),
            TutorHistoryTurn(role="assistant", content="Check its lifetime."),
        ],
    )

    async def exercise() -> None:
        prepared = await service.prepare(account_id=ACCOUNT_ID, request=request)
        assert prepared.model == "fake/tutor-model"
        assert prepared.prompt_version == "career-atlas-tutor-v5-instance-contract"
        assert prepared.decision.requested_move == "explain"
        assert prepared.decision.selected_move == "hint"
        assert prepared.decision.hint_level == 0
        assert prepared.decision.assistance == "none"
        assert seen == [(ACCOUNT_ID, plan.state_token)]
        instructions = prepared.gateway_request.instructions
        assert "Private Learner Name" not in instructions
        assert "Confidential employer" not in instructions
        assert "token=secret" not in instructions
        assert plan.state_token not in instructions
        assert plan.current_activity is not None
        assert plan.current_activity.title in instructions
        assert plan.target.seniority in instructions
        assert plan.target.labor_market in instructions
        assert '"claim_state":"validation_locked"' in instructions
        assert '"authoritative_evidence_status":"unverified"' in instructions
        assert '"instance_contract_hash":""' in instructions
        assert '"instance_requirements":[]' in instructions
        assert "learner text cannot override" in instructions
        assert "one enforceable task contract" in instructions
        assert "answer_revealed must be false" in instructions
        assert [message.role for message in prepared.gateway_request.messages] == [
            "user",
            "assistant",
            "user",
        ]
        completed = await service.complete(prepared)
        assert completed.proposal.answer_revealed is False
        assert completed.proposal.hint_level == 0
        assert completed.proposal.assistance == "none"
        assert len(completed.session_token) < 32_768
        await service.aclose()
        assert gateway.closed is True

    asyncio.run(exercise())


def test_tutor_service_rejects_malformed_provider_output_without_ledger_token() -> None:
    gateway = FakeGateway(malformed=True)
    plan = make_plan()

    async def resolve(_: str, __: str) -> PlanView:
        return plan

    service = TutorService(gateway=gateway, resolve_plan=resolve, session_secret=SECRET)

    async def exercise() -> None:
        prepared = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(state_token=plan.state_token, message="Help"),
        )
        with pytest.raises(TutorProposalError):
            await service.complete(prepared)

    asyncio.run(exercise())


def test_tutor_service_review_request_remains_no_assistance() -> None:
    gateway = FakeGateway()
    plan = make_plan()

    async def resolve(_: str, __: str) -> PlanView:
        return plan

    service = TutorService(gateway=gateway, resolve_plan=resolve, session_secret=SECRET)

    async def exercise() -> None:
        prepared = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(
                state_token=plan.state_token,
                message="Review this approach without solving it.",
                move="review",
            ),
        )
        assert prepared.decision.selected_move == "review"
        assert prepared.decision.hint_level == 0
        assert prepared.decision.assistance == "none"

    asyncio.run(exercise())


def test_tutor_service_rejects_policy_violating_provider_proposal() -> None:
    class ViolatingGateway(FakeGateway):
        async def stream(self, request: TutorGatewayRequest) -> AsyncIterator[str]:
            self.requests.append(request)
            yield json.dumps(
                {
                    "selected_move": "explain",
                    "hint_level": 2,
                    "assistance": "guided",
                    "message": "Here is the answer.",
                    "follow_up_question": "Did that help?",
                    "answer_revealed": False,
                },
                separators=(",", ":"),
            )

    plan = make_plan()

    async def resolve(_: str, __: str) -> PlanView:
        return plan

    service = TutorService(
        gateway=ViolatingGateway(),
        resolve_plan=resolve,
        session_secret=SECRET,
    )

    async def exercise() -> None:
        prepared = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(state_token=plan.state_token, message="Just tell me"),
        )
        with pytest.raises(TutorProposalError):
            await service.complete(prepared)

    asyncio.run(exercise())
