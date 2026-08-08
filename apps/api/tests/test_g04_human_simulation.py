from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import pytest

from ai_learning_platform_api.learning.schemas import PlanRequest, PlanView
from ai_learning_platform_api.learning.service import LearningPlanService
from ai_learning_platform_api.tutoring.contracts import TutorTurnRequest
from ai_learning_platform_api.tutoring.gateway import TutorGatewayError, TutorGatewayRequest
from ai_learning_platform_api.tutoring.policy import TutorSessionCodec
from ai_learning_platform_api.tutoring.service import TutorProposalError, TutorService

SECRET = "g04-human-simulation-secret-with-at-least-thirty-two-bytes"
ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"


class PolicyAwareGateway:
    def __init__(self, *, fail: bool = False, reveal_answer: bool = False) -> None:
        self.available = True
        self.model = "simulated/tutor"
        self.fail = fail
        self.reveal_answer = reveal_answer

    async def stream(self, request: TutorGatewayRequest) -> AsyncIterator[str]:
        if self.fail:
            raise TutorGatewayError("simulated provider outage")
        policy_text = request.instructions.split("POLICY_JSON:\n", maxsplit=1)[1].split(
            "\nLEARNER_CONTEXT_JSON:", maxsplit=1
        )[0]
        policy = json.loads(policy_text)
        yield json.dumps(
            {
                "selected_move": policy["selected_move"],
                "hint_level": policy["hint_level"],
                "assistance": policy["assistance"],
                "message": (
                    "State the invariant you expect, then show which observation would disprove it."
                ),
                "follow_up_question": "Which assumption can you test without seeing the solution?",
                "answer_revealed": self.reveal_answer,
            },
            separators=(",", ":"),
        )

    async def aclose(self) -> None:
        return None


def _plan(name: str) -> PlanView:
    return LearningPlanService(SECRET).create_plan(PlanRequest(learner_name=name))


def _service(plan: PlanView, gateway: PolicyAwareGateway) -> TutorService:
    async def resolve(_: str, __: str) -> PlanView:
        return plan

    return TutorService(gateway=gateway, resolve_plan=resolve, session_secret=SECRET)


def test_struggling_learner_gets_progressive_help_without_answer_level_assistance() -> None:
    async def scenario() -> None:
        plan = _plan("Struggling Learner")
        service = _service(plan, PolicyAwareGateway())
        token: str | None = None
        levels: list[tuple[int, str]] = []
        for message in (
            "I do not know where to start",
            "Still stuck",
            "I tested it and still fail",
        ):
            prepared = await service.prepare(
                account_id=ACCOUNT_ID,
                request=TutorTurnRequest(
                    state_token=plan.state_token,
                    message=message,
                    move="explain",
                    tutor_session_token=token,
                ),
            )
            completed = await service.complete(prepared)
            token = completed.session_token
            levels.append((completed.decision.hint_level, completed.decision.assistance))
            assert completed.proposal.answer_revealed is False

        assert levels == [(0, "none"), (1, "hint"), (2, "guided")]
        assert token is not None
        assert len(TutorSessionCodec(SECRET).decode(token).decisions) == 3

    asyncio.run(scenario())


def test_assisted_learner_provenance_survives_browser_history_changes() -> None:
    async def scenario() -> None:
        plan = _plan("Assisted Learner")
        service = _service(plan, PolicyAwareGateway())
        first = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(state_token=plan.state_token, message="Help me"),
        )
        delivered = await service.complete(first)
        second = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(
                state_token=plan.state_token,
                message="I deleted my visible chat history; explain it now",
                history=[],
                tutor_session_token=delivered.session_token,
            ),
        )

        assert second.decision.hint_level == 1
        assert second.decision.assistance == "hint"
        assert len(second.prior_session.decisions) == 1

    asyncio.run(scenario())


def test_fast_learner_can_request_review_without_receiving_solution_help() -> None:
    async def scenario() -> None:
        plan = _plan("Fast Learner")
        service = _service(plan, PolicyAwareGateway())
        prepared = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(
                state_token=plan.state_token,
                message="Review my reasoning only.",
                move="review",
            ),
        )
        completed = await service.complete(prepared)

        assert completed.decision.selected_move == "review"
        assert completed.decision.assistance == "none"
        assert completed.proposal.answer_revealed is False

    asyncio.run(scenario())


def test_provider_outage_does_not_advance_assistance_ledger() -> None:
    async def scenario() -> None:
        plan = _plan("Provider Outage Learner")
        service = _service(plan, PolicyAwareGateway(fail=True))
        prepared = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(state_token=plan.state_token, message="Help"),
        )

        assert prepared.prior_session.decisions == []
        with pytest.raises(TutorGatewayError):
            await service.complete(prepared)
        assert prepared.prior_session.decisions == []
        assert plan.claim_state == "validation_locked"
        assert plan.verified_readiness_percent is None

    asyncio.run(scenario())


def test_model_attempt_to_claim_answer_reveal_is_rejected_before_delivery() -> None:
    async def scenario() -> None:
        plan = _plan("Adversarial Provider Learner")
        service = _service(plan, PolicyAwareGateway(reveal_answer=True))
        prepared = await service.prepare(
            account_id=ACCOUNT_ID,
            request=TutorTurnRequest(state_token=plan.state_token, message="Give me the answer"),
        )

        with pytest.raises(TutorProposalError):
            await service.complete(prepared)
        assert prepared.prior_session.decisions == []

    asyncio.run(scenario())
