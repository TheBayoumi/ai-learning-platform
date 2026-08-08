from __future__ import annotations

import json

import pytest

from ai_learning_platform_api.learning.schemas import PlanRequest, PlanView, ReplanRequest
from ai_learning_platform_api.learning.service import LearningPlanService
from ai_learning_platform_api.tutoring.contracts import TutorTurnRequest
from ai_learning_platform_api.tutoring.policy import (
    InvalidTutorSessionError,
    TutorPolicyEngine,
    TutorSessionCodec,
)

SECRET = "g04-tutor-policy-secret-with-at-least-thirty-two-bytes"


def _plan() -> PlanView:
    return LearningPlanService(SECRET).create_plan(PlanRequest(learner_name="Tutor Learner"))


def test_first_help_request_is_socratic_no_assistance_even_when_explain_requested() -> None:
    plan = _plan()
    policy = TutorPolicyEngine(SECRET)

    result = policy.decide(
        plan=plan,
        request=TutorTurnRequest(
            state_token=plan.state_token,
            message="Explain the solution to me.",
            move="explain",
        ),
    )

    assert result.decision.requested_move == "explain"
    assert result.decision.selected_move == "hint"
    assert result.decision.hint_level == 0
    assert result.decision.assistance == "none"
    assert "Socratic" in result.decision.reason


def test_assistance_escalates_only_after_delivered_prior_policy_decisions() -> None:
    plan = _plan()
    policy = TutorPolicyEngine(SECRET)
    first = policy.decide(
        plan=plan,
        request=TutorTurnRequest(state_token=plan.state_token, message="Help", move="hint"),
    )
    first_token = policy.delivered_token(
        plan=plan,
        prior=first.prior_state,
        decision=first.decision,
    )
    second = policy.decide(
        plan=plan,
        request=TutorTurnRequest(
            state_token=plan.state_token,
            message="I am still stuck.",
            move="explain",
            tutor_session_token=first_token,
        ),
    )
    second_token = policy.delivered_token(
        plan=plan,
        prior=second.prior_state,
        decision=second.decision,
    )
    third = policy.decide(
        plan=plan,
        request=TutorTurnRequest(
            state_token=plan.state_token,
            message="One more nudge.",
            move="hint",
            tutor_session_token=second_token,
        ),
    )

    assert (first.decision.hint_level, first.decision.assistance) == (0, "none")
    assert (second.decision.hint_level, second.decision.assistance) == (1, "hint")
    assert (third.decision.hint_level, third.decision.assistance) == (2, "guided")


def test_same_policy_inputs_replay_to_same_decision_id() -> None:
    plan = _plan()
    policy = TutorPolicyEngine(SECRET)
    request = TutorTurnRequest(state_token=plan.state_token, message="Help", move="explain")

    first = policy.decide(plan=plan, request=request)
    second = policy.decide(plan=plan, request=request)

    assert first.decision == second.decision


def test_signed_assistance_ledger_is_bound_to_exact_plan_and_activity() -> None:
    plan = _plan()
    policy = TutorPolicyEngine(SECRET)
    first = policy.decide(
        plan=plan,
        request=TutorTurnRequest(state_token=plan.state_token, message="Help"),
    )
    token = policy.delivered_token(
        plan=plan,
        prior=first.prior_state,
        decision=first.decision,
    )
    replanned = LearningPlanService(SECRET).replan(
        ReplanRequest(
            state_token=plan.state_token,
            weekly_hours=4,
            focus_competency_ids=[],
        )
    )

    with pytest.raises(InvalidTutorSessionError):
        policy.decide(
            plan=replanned,
            request=TutorTurnRequest(
                state_token=replanned.state_token,
                message="Reuse old help ledger",
                tutor_session_token=token,
            ),
        )


def test_noncanonical_or_modified_session_token_is_rejected() -> None:
    plan = _plan()
    policy = TutorPolicyEngine(SECRET)
    first = policy.decide(
        plan=plan,
        request=TutorTurnRequest(state_token=plan.state_token, message="Help"),
    )
    token = policy.delivered_token(
        plan=plan,
        prior=first.prior_state,
        decision=first.decision,
    )
    changed = f"{token[:-1]}{'A' if token[-1] != 'A' else 'B'}"

    with pytest.raises(InvalidTutorSessionError):
        TutorSessionCodec(SECRET).decode(changed)


def test_session_ledger_is_bounded_under_many_delivered_turns() -> None:
    plan = _plan()
    policy = TutorPolicyEngine(SECRET)
    token: str | None = None
    for index in range(40):
        result = policy.decide(
            plan=plan,
            request=TutorTurnRequest(
                state_token=plan.state_token,
                message=f"Help attempt {index}",
                tutor_session_token=token,
            ),
        )
        token = policy.delivered_token(
            plan=plan,
            prior=result.prior_state,
            decision=result.decision,
        )
        assert len(token) < 32_768

    assert token is not None
    decoded = TutorSessionCodec(SECRET).decode(token)
    assert len(decoded.decisions) == 12
    assert json.loads(json.dumps(decoded.model_dump(mode="json")))["schema_version"] == 1
