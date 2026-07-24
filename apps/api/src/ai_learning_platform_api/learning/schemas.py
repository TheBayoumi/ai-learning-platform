"""Strict contracts for adaptive learning evidence and assessment calibration."""

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
    """Record one evidence cycle and issue the next signed adaptive state."""

    activity_id: Annotated[str, Field(min_length=1, max_length=160)]
    reflection: Annotated[str, Field(min_length=0, max_length=1_000)] = ""
    evidence_reference: Annotated[str, Field(min_length=0, max_length=500)] = ""
    criteria_met: Annotated[list[str], Field(max_length=16)] = Field(default_factory=list)
    confidence: Annotated[int, Field(ge=0, le=4)] = 0


class ReplanRequest(ResumeRequest):
    """Regenerate the active curriculum around capacity and explicit focus."""

    weekly_hours: Annotated[int, Field(ge=2, le=40)]
    focus_competency_ids: Annotated[list[str], Field(max_length=4)] = Field(default_factory=list)


class AssessmentStartRequest(ResumeRequest):
    """Start a signed, expiring calibration attempt for current priority gaps."""

    question_count: Annotated[int, Field(ge=2, le=4)] = 4


class AssessmentAnswer(StrictModel):
    """One selected option for one assessment question."""

    question_id: Annotated[str, Field(min_length=1, max_length=120)]
    option_id: Annotated[str, Field(min_length=1, max_length=16)]


class AssessmentSubmitRequest(ResumeRequest):
    """Score an expiring signed attempt and replan from the calibration signal."""

    attempt_token: Annotated[str, Field(min_length=20, max_length=16_384)]
    answers: Annotated[list[AssessmentAnswer], Field(min_length=1, max_length=4)]


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
    """A competency prioritized from evidence and optional assessment calibration."""

    id: str
    name: str
    category: str
    mastery_percent: int
    effective_percent: int
    assessment_percent: int | None = None
    gap_percent: int
    focused: bool = False


class ActivityView(StrictModel):
    """One unique bounded work item in an adaptive learner plan."""

    id: str
    competency_id: str
    competency_name: str
    title: str
    objective: str
    deliverable: str
    acceptance_criteria: list[str]
    estimated_minutes: int
    kind: Literal["build", "review"] = "build"
    rationale: str = ""
    generation: int = 0
    available_from: str | None = None


class EvidenceRecordView(StrictModel):
    """A learner-attested evidence record; it is not an external assessment."""

    activity_id: str
    competency_id: str
    competency_name: str
    title: str
    submitted_at: str
    reflection: str
    evidence_reference: str
    criteria_met: list[str]
    confidence: int
    provisional_mastery_delta: int
    next_review_at: str


class AssessmentOptionView(StrictModel):
    """One public option; it intentionally contains no correctness marker."""

    id: str
    text: str


class AssessmentQuestionView(StrictModel):
    """One public single-choice calibration question."""

    id: str
    competency_id: str
    competency_name: str
    prompt: str
    options: list[AssessmentOptionView]


class AssessmentAttemptView(StrictModel):
    """An expiring assessment attempt with signed server-verifiable identity."""

    attempt_token: str
    bank_version: str
    issued_at: str
    expires_at: str
    questions: list[AssessmentQuestionView]


class AssessmentFeedbackView(StrictModel):
    """Question feedback returned only after submission."""

    question_id: str
    competency_id: str
    correct: bool
    explanation: str


class AssessmentRecordView(StrictModel):
    """A bounded calibration result retained in signed learner state."""

    attempt_id: str
    bank_version: str
    submitted_at: str
    score_percent: int
    correct_count: int
    total_count: int
    competency_scores: dict[str, int]


class LearnerState(StrictModel):
    """Signed stateless learner state carried by the browser."""

    schema_version: Literal[1, 2, 3] = 3
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
    plan_revision: int = 0
    focus_competency_ids: list[str] = Field(default_factory=list)
    evidence_history: list[EvidenceRecordView] = Field(default_factory=list)
    assessment_scores: dict[str, int] = Field(default_factory=dict)
    assessment_history: list[AssessmentRecordView] = Field(default_factory=list)


class PlanView(StrictModel):
    """Dashboard projection plus the newly signed learner state."""

    state_token: str
    learner_id: str
    learner_name: str
    role: RoleView
    readiness_percent: int
    evidence_readiness_percent: int
    assessment_coverage_percent: int
    priority_competencies: list[PriorityCompetencyView]
    current_activity: ActivityView | None
    completed_count: int
    total_count: int
    sequence: int
    weekly_hours: int
    plan_revision: int
    focus_competency_ids: list[str]
    evidence_history: list[EvidenceRecordView]
    assessment_history: list[AssessmentRecordView]
    next_review_at: str | None


class AssessmentSubmissionView(StrictModel):
    """Post-assessment feedback plus the recalibrated learner plan."""

    score_percent: int
    correct_count: int
    total_count: int
    feedback: list[AssessmentFeedbackView]
    plan: PlanView


class ApiError(StrictModel):
    """Stable product API error envelope."""

    code: str
    message: str
