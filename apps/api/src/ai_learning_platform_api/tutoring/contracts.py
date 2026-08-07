"""Strict public and internal contracts for bounded tutoring turns."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from ai_learning_platform_api.learning.schemas import StrictModel

TutorMove = Literal["explain", "hint", "review"]
TutorRole = Literal["user", "assistant"]


class TutorHistoryTurn(StrictModel):
    """One bounded browser-carried turn; transcripts are not authoritative state."""

    role: TutorRole
    content: Annotated[str, Field(min_length=1, max_length=1_200)]


class TutorTurnRequest(StrictModel):
    """One non-authoritative tutor request tied to the current learner projection."""

    state_token: Annotated[str, Field(min_length=20, max_length=65_536)]
    message: Annotated[str, Field(min_length=1, max_length=2_000)]
    move: TutorMove = "hint"
    history: Annotated[list[TutorHistoryTurn], Field(max_length=6)] = Field(
        default_factory=list
    )
