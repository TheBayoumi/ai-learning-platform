"""Deterministic tutoring policy and signed assistance-ledger codec."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass

from pydantic import ValidationError

from ai_learning_platform_api.learning.schemas import PlanView
from ai_learning_platform_api.tutoring.contracts import (
    TutorPolicyDecision,
    TutorSessionState,
    TutorTurnRequest,
)

_MAX_SESSION_DECISIONS = 12


class TutorPolicyError(ValueError):
    """Fail-closed tutor policy/session error."""


class InvalidTutorSessionError(TutorPolicyError):
    """The assistance ledger is malformed, forged, stale, or bound to another plan."""


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(value + padding)
    except (ValueError, UnicodeEncodeError) as error:
        raise InvalidTutorSessionError from error
    if _encode(decoded) != value:
        raise InvalidTutorSessionError
    return decoded


class TutorSessionCodec:
    """Canonical HMAC codec for non-authoritative tutoring assistance provenance."""

    def __init__(self, secret: str) -> None:
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("tutor session secret must contain at least 32 UTF-8 bytes")
        self._secret = secret.encode("utf-8")

    def encode(self, state: TutorSessionState) -> str:
        payload = json.dumps(
            state.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(self._secret, payload, hashlib.sha256).digest()
        return f"{_encode(payload)}.{_encode(signature)}"

    def decode(self, token: str) -> TutorSessionState:
        if len(token) > 32_768 or token.count(".") != 1:
            raise InvalidTutorSessionError
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
        payload = _decode(encoded_payload)
        signature = _decode(encoded_signature)
        expected = hmac.new(self._secret, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise InvalidTutorSessionError
        try:
            return TutorSessionState.model_validate(json.loads(payload))
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as error:
            raise InvalidTutorSessionError from error


@dataclass(frozen=True, slots=True)
class TutorPolicyResult:
    decision: TutorPolicyDecision
    prior_state: TutorSessionState


class TutorPolicyEngine:
    """Select bounded tutoring behavior from deterministic state and assistance history."""

    def __init__(self, secret: str) -> None:
        self._codec = TutorSessionCodec(secret)

    def decide(self, *, plan: PlanView, request: TutorTurnRequest) -> TutorPolicyResult:
        activity = plan.current_activity
        if activity is None:
            raise TutorPolicyError("no active activity is available for tutoring")
        prior = self._session(plan=plan, activity_id=activity.id, token=request.tutor_session_token)
        history = [item for item in prior.decisions if item.activity_id == activity.id]
        evidence = next(
            (
                item
                for item in plan.competency_evidence
                if item.competency_id == activity.competency_id
            ),
            None,
        )
        if evidence is not None and evidence.status == "independent":
            selected_move = "review"
            hint_level = 0
            assistance = "none"
            reason = "independent evidence exists; use retrieval/review without added solution help"
        elif request.move == "review":
            selected_move = "review"
            hint_level = 0
            assistance = "none"
            reason = "review requested; critique learner-supplied work without supplying an answer"
        elif not history:
            selected_move = "hint"
            hint_level = 0
            assistance = "none"
            reason = "first attempt; ask a diagnostic Socratic question before giving help"
        elif max(item.hint_level for item in history) == 0:
            selected_move = "hint"
            hint_level = 1
            assistance = "hint"
            reason = "prior no-assistance probe did not resolve the request; allow one bounded hint"
        else:
            selected_move = "explain"
            hint_level = 2
            assistance = "guided"
            reason = (
                "prior hint exists; allow guided explanation but still forbid answer-level help"
            )
        decision_id = self._decision_id(
            learner_id=plan.learner_id,
            plan_version_id=plan.active_plan_version.plan_version_id,
            activity_id=activity.id,
            requested_move=request.move,
            selected_move=selected_move,
            hint_level=hint_level,
            history_count=len(history),
        )
        return TutorPolicyResult(
            decision=TutorPolicyDecision(
                decision_id=decision_id,
                plan_version_id=plan.active_plan_version.plan_version_id,
                activity_id=activity.id,
                requested_move=request.move,
                selected_move=selected_move,
                hint_level=hint_level,
                assistance=assistance,
                reason=reason,
            ),
            prior_state=prior,
        )

    def delivered_token(
        self,
        *,
        plan: PlanView,
        prior: TutorSessionState,
        decision: TutorPolicyDecision,
    ) -> str:
        activity = plan.current_activity
        if activity is None:
            raise TutorPolicyError("no active activity is available for tutoring")
        next_state = TutorSessionState(
            learner_id=plan.learner_id,
            plan_version_id=plan.active_plan_version.plan_version_id,
            activity_id=activity.id,
            decisions=[*prior.decisions, decision][-_MAX_SESSION_DECISIONS:],
        )
        return self._codec.encode(next_state)

    def _session(
        self,
        *,
        plan: PlanView,
        activity_id: str,
        token: str | None,
    ) -> TutorSessionState:
        if token is None:
            return TutorSessionState(
                learner_id=plan.learner_id,
                plan_version_id=plan.active_plan_version.plan_version_id,
                activity_id=activity_id,
            )
        state = self._codec.decode(token)
        if (
            state.learner_id != plan.learner_id
            or state.plan_version_id != plan.active_plan_version.plan_version_id
            or state.activity_id != activity_id
        ):
            raise InvalidTutorSessionError
        return state

    @staticmethod
    def _decision_id(
        *,
        learner_id: str,
        plan_version_id: str,
        activity_id: str,
        requested_move: str,
        selected_move: str,
        hint_level: int,
        history_count: int,
    ) -> str:
        payload = "|".join(
            (
                learner_id,
                plan_version_id,
                activity_id,
                requested_move,
                selected_move,
                str(hint_level),
                str(history_count),
            )
        )
        return f"tutor-decision-{hashlib.sha256(payload.encode()).hexdigest()[:24]}"
