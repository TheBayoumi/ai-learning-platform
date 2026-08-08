"""Strict public and internal contracts for bounded tutoring turns."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from ai_learning_platform_api.learning.schemas import StrictModel

TutorMove = Literal["explain", "hint", "review"]
TutorRole = Literal["user", "assistant"]
TutorAssistance = Literal["none", "hint", "guided"]


class TutorHistoryTurn(StrictModel):
    """One bounded browser-carried turn; transcripts are not authoritative state."""

    role: TutorRole
    content: Annotated[str, Field(min_length=1, max_length=1_200)]


class TutorPolicyDecision(StrictModel):
    """One deterministic, replayable tutor-policy decision."""

    decision_id: str
    plan_version_id: str
    activity_id: str
    requested_move: TutorMove
    selected_move: TutorMove
    hint_level: Annotated[int, Field(ge=0, le=2)]
    assistance: TutorAssistance
    reason: str


class TutorSessionState(StrictModel):
    """Signed browser-carried assistance ledger bound to one learner plan/activity."""

    schema_version: Literal[1] = 1
    learner_id: str
    plan_version_id: str
    activity_id: str
    decisions: Annotated[list[TutorPolicyDecision], Field(max_length=12)] = Field(
        default_factory=list
    )


class TutorProposal(StrictModel):
    """Schema-validated model proposal; it can never claim authoritative outcomes."""

    selected_move: TutorMove
    hint_level: Annotated[int, Field(ge=0, le=2)]
    assistance: TutorAssistance
    message: Annotated[str, Field(min_length=1, max_length=8_000)]
    follow_up_question: Annotated[str, Field(min_length=1, max_length=1_000)]
    answer_revealed: Literal[False] = False


class TutorTurnRequest(StrictModel):
    """One non-authoritative tutor request tied to the current learner projection."""

    state_token: Annotated[str, Field(min_length=20, max_length=65_536)]
    message: Annotated[str, Field(min_length=1, max_length=2_000)]
    move: TutorMove = "hint"
    tutor_session_token: Annotated[str, Field(min_length=20, max_length=32_768)] | None = None
    history: Annotated[list[TutorHistoryTurn], Field(max_length=6)] = Field(default_factory=list)
