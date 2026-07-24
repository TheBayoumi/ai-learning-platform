"""Strict request and response contracts for the learner product slice."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Forbid silent contract expansion at API boundaries."""

    model_config = ConfigDict(extra="forbid")


class CompetencyRating(StrictModel):
    """A learner self-rating on a bounded five-point scale."""

    competency_id: Annotated[str, Field(min_length=1, max_length=64)]
    score: Annotated[int, Field(ge=0, le=4)]


class PlanRequest(StrictModel):
    """Inputs required to diagnose gaps and generate the first plan."""

    learner_name: Annotated[str, Field(min_length=2, max_length=80)]
    target_role: Literal["junior-python-backend-engineer"] = "junior-python-backend-engineer"
    weekly_hours: Annotated[int, Field(ge=2, le=40)] = 8
    experience_summary: Annotated[str, Field(min_length=0, max_length=600)] = ""
    ratings: Annotated[list[CompetencyRating], Field(max_length=32)] = Field(default_factory=list)


class ResumeRequest(StrictModel):
    """Resume a signed learner state without server-side persistence."""

    state_token: Annotated[str, Field(min_length=20, max_length=65_536)]


class ProgressRequest(ResumeRequest):
    """Record one completed activity and issue the next signed state."""

    activity_id: Annotated[str, Field(min_length=1, max_length=160)]
    reflection: Annotated[str, Field(min_length=0, max_length=1_000)] = ""


class CompetencyView(StrictModel):
    """Public competency metadata."""

    id: str
    name: str
    category: str
    description: str
    weight: int


class RoleView(StrictModel):
    """Versioned target-role profile."""

    id: str
    version: str
    title: str
    summary: str
    competencies: list[CompetencyView]


class PriorityCompetencyView(StrictModel):
    """A competency prioritized from the learner's current evidence."""

    id: str
    name: str
    category: str
    mastery_percent: int
    gap_percent: int


class ActivityView(StrictModel):
    """One unique bounded work item in a learner plan."""

    id: str
    competency_id: str
    competency_name: str
    title: str
    objective: str
    deliverable: str
    acceptance_criteria: list[str]
    estimated_minutes: int


class LearnerState(StrictModel):
    """Signed stateless learner state carried by the browser."""

    schema_version: Literal[1] = 1
    learner_id: str
    learner_name: str
    target_role: Literal["junior-python-backend-engineer"]
    weekly_hours: int
    experience_summary: str
    created_at: str
    sequence: int
    mastery: dict[str, int]
    completed_activity_ids: list[str]
    activities: list[ActivityView]


class PlanView(StrictModel):
    """Dashboard projection plus the newly signed learner state."""

    state_token: str
    learner_id: str
    learner_name: str
    role: RoleView
    readiness_percent: int
    priority_competencies: list[PriorityCompetencyView]
    current_activity: ActivityView | None
    completed_count: int
    total_count: int
    sequence: int


class ApiError(StrictModel):
    """Stable product API error envelope."""

    code: str
    message: str
