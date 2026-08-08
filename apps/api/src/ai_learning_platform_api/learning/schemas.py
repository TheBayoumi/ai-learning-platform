"""Strict contracts for adaptive learning evidence and assessment calibration."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Forbid silent contract expansion at API boundaries."""

    model_config = ConfigDict(extra="forbid")


TargetText = Annotated[str, Field(min_length=2, max_length=160)]
OverlayText = Annotated[str, Field(min_length=1, max_length=120)]
ClaimState = Literal[
    "engineering_available",
    "validation_locked",
    "partial_profile_evidence",
    "ready_against_profile",
]


class CompetencyRating(StrictModel):
    """A learner self-rating used only to prioritize diagnosis and planning."""

    competency_id: Annotated[str, Field(min_length=1, max_length=64)]
    score: Annotated[int, Field(ge=0, le=4)]


class TargetRequest(StrictModel):
    """Every required dimension that must be resolved before a curriculum is planned."""

    seniority: TargetText
    labor_market: TargetText
    timeline_weeks: Annotated[int, Field(ge=1, le=104)]
    geography: TargetText
    stack_overlays: Annotated[list[OverlayText], Field(min_length=1, max_length=24)]
    industry_overlay: TargetText | None = None
    company_overlay: TargetText | None = None


class TargetView(StrictModel):
    """A fully resolved, version-bound career Target and its explicit claim boundary."""

    role_id: str
    role_version: str
    seniority: str
    labor_market: str
    timeline_weeks: int
    geography: str
    stack_overlays: list[str]
    industry_overlay: str | None = None
    company_overlay: str | None = None
    validation_state: Literal["provisional", "approved"]
    scope: str
    exclusions: list[str]


class PlanRequest(StrictModel):
    """Inputs required to create a resolved Target and the first planning hypothesis."""

    learner_name: Annotated[str, Field(min_length=2, max_length=80)]
    target_role: Annotated[str, Field(min_length=2, max_length=80)] = (
        "junior-python-backend-engineer"
    )
    target: TargetRequest | None = None
    weekly_hours: Annotated[int, Field(ge=2, le=40)] = 8
    experience_summary: Annotated[str, Field(min_length=0, max_length=600)] = ""
    ratings: Annotated[list[CompetencyRating], Field(max_length=32)] = Field(default_factory=list)


class ResumeRequest(StrictModel):
    """Resume a signed learner state."""

    state_token: Annotated[str, Field(min_length=20, max_length=65_536)]


class ProgressRequest(ResumeRequest):
    """Record learner-attested work and issue the next signed planning state."""

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
    """Score an expiring signed attempt and replan from the diagnostic signal."""

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
    """Versioned role-profile candidate plus the explicit Target defaults used by onboarding."""

    id: str
    version: str
    title: str
    summary: str
    validation_state: Literal["provisional", "approved"] = "provisional"
    default_target: TargetView
    competencies: list[CompetencyView]


class PriorityCompetencyView(StrictModel):
    """A competency prioritized from non-authoritative planning and diagnostic signals."""

    id: str
    name: str
    category: str
    planning_signal_percent: int
    diagnostic_signal_percent: int
    assessment_percent: int | None = None
    priority_gap_percent: int
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
    """A learner-attested record that may prioritize later diagnosis but grants no mastery."""

    activity_id: str
    competency_id: str
    competency_name: str
    title: str
    submitted_at: str
    reflection: str
    evidence_reference: str
    criteria_met: list[str]
    confidence: int
    planning_signal_delta: int = Field(
        validation_alias=AliasChoices("planning_signal_delta", "provisional_mastery_delta")
    )
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
    """A bounded calibration result retained as a diagnostic signal, not mastery evidence."""

    attempt_id: str
    bank_version: str
    submitted_at: str
    score_percent: int
    correct_count: int
    total_count: int
    competency_scores: dict[str, int]


class LearnerState(StrictModel):
    """Signed learner state carried by the browser and optionally owned by durable storage."""

    schema_version: Literal[1, 2, 3, 4] = 4
    storage_mode: Literal["browser", "durable"] = "browser"
    learner_id: str
    learner_name: str
    target_role: Annotated[str, Field(min_length=2, max_length=80)]
    target: TargetView | None = None
    weekly_hours: int
    experience_summary: str
    created_at: str
    sequence: int
    planning_signal: dict[str, int] = Field(default_factory=dict)
    # Legacy schema 1-3 field. New transitions clear it after migrating it into planning_signal.
    mastery: dict[str, int] = Field(default_factory=dict)
    completed_activity_ids: list[str]
    activities: list[ActivityView]
    plan_revision: int = 0
    focus_competency_ids: list[str] = Field(default_factory=list)
    evidence_history: list[EvidenceRecordView] = Field(default_factory=list)
    assessment_scores: dict[str, int] = Field(default_factory=dict)
    assessment_history: list[AssessmentRecordView] = Field(default_factory=list)


class PlanView(StrictModel):
    """Planning projection that never presents unverified evidence as mastery or readiness."""

    state_token: str
    learner_id: str
    learner_name: str
    role: RoleView
    target: TargetView
    claim_state: ClaimState = "validation_locked"
    verified_readiness_percent: Annotated[int, Field(ge=0, le=100)] | None = None
    planning_signal_percent: Annotated[int, Field(ge=0, le=100)]
    diagnostic_signal_percent: Annotated[int, Field(ge=0, le=100)]
    assessment_coverage_percent: Annotated[int, Field(ge=0, le=100)]
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
    """Post-assessment feedback plus the recalibrated planning projection."""

    score_percent: int
    correct_count: int
    total_count: int
    feedback: list[AssessmentFeedbackView]
    plan: PlanView


class ApiError(StrictModel):
    """Stable product API error envelope."""

    code: str
    message: str
