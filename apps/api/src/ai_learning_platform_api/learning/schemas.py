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
EvidenceSource = Literal["learner_attested", "calibration", "trusted_evaluator"]
EvidenceDisposition = Literal["recorded", "accepted", "rejected", "disputed"]
EvidenceIndependence = Literal["unverified", "assisted", "independent"]
AssistanceLevel = Literal["unknown", "none", "hint", "guided", "answer_level"]
ReasoningState = Literal["not_observed", "submitted", "verified"]
VerificationClass = Literal["independent", "retention_7d", "retention_30d", "transfer"]
ProbeStatus = Literal["scheduled", "passed", "failed"]
ProbeDisposition = Literal["passed", "failed"]
WorkVerificationKind = Literal["modification", "debugging", "defense"]
WorkProvenanceStatus = Literal[
    "challenge_issued", "captured", "verified", "reviewed_blocked", "rejected", "disputed"
]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
CompetencyEvidenceStatus = Literal["unverified", "partial", "independent"]
MisconceptionStatus = Literal["active", "resolved"]
ReviewStage = Literal["evidence_follow_up", "retention_candidate"]
CurriculumTrigger = Literal[
    "initial",
    "assessment",
    "manual_replan",
    "trusted_evidence",
    "state_migration",
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


class TrustedEvidenceVerdict(StrictModel):
    """Server-side trusted evaluator verdict; this contract is not a learner HTTP request."""

    evidence_id: Annotated[str, Field(min_length=8, max_length=160)]
    competency_id: Annotated[str, Field(min_length=1, max_length=64)]
    disposition: Literal["accepted", "rejected", "disputed"]
    independence: EvidenceIndependence = "unverified"
    assistance: AssistanceLevel = "unknown"
    reasoning: ReasoningState = "not_observed"
    evaluator_id: Annotated[str, Field(min_length=2, max_length=120)]
    evaluator_version: Annotated[str, Field(min_length=1, max_length=80)]
    rubric_version: Annotated[str, Field(min_length=1, max_length=80)]
    instance_contract_hash: Annotated[str, Field(max_length=80)] = ""
    confidence: Annotated[int, Field(ge=0, le=100)]
    findings: Annotated[list[str], Field(max_length=12)] = Field(default_factory=list)
    misconception_codes: Annotated[list[str], Field(max_length=12)] = Field(default_factory=list)


class TrustedProbeVerdict(StrictModel):
    """Internal trusted verdict for one scheduled retention/transfer probe."""

    probe_id: Annotated[str, Field(min_length=8, max_length=160)]
    competency_id: Annotated[str, Field(min_length=1, max_length=64)]
    verification_class: VerificationClass
    disposition: ProbeDisposition
    independence: EvidenceIndependence = "unverified"
    assistance: AssistanceLevel = "unknown"
    reasoning: ReasoningState = "not_observed"
    evaluator_id: Annotated[str, Field(min_length=2, max_length=120)]
    evaluator_version: Annotated[str, Field(min_length=1, max_length=80)]
    confidence: Annotated[int, Field(ge=0, le=100)]
    findings: Annotated[list[str], Field(max_length=12)] = Field(default_factory=list)


class VerificationProbeView(StrictModel):
    """One server-scheduled independent retention or unseen-transfer obligation."""

    probe_id: str
    competency_id: str
    verification_class: VerificationClass
    source_evidence_id: str
    due_at: str
    status: ProbeStatus = "scheduled"
    unseen_instance_fingerprint: str = ""
    completed_at: str | None = None
    evaluation_id: str = ""
    evaluator_id: str = ""
    evaluator_version: str = ""


class CompetencyQualificationState(StrictModel):
    """Authoritative exact proof classes for one competency."""

    competency_id: str
    satisfied_classes: list[VerificationClass] = Field(default_factory=list)
    failed_classes: list[VerificationClass] = Field(default_factory=list)
    independent_evidence_ids: list[str] = Field(default_factory=list)
    assisted_evidence_ids: list[str] = Field(default_factory=list)
    last_updated_at: str | None = None


class CompetencyQualificationView(StrictModel):
    """Projection of exact immediate/retention/transfer proof obligations."""

    competency_id: str
    satisfied_classes: list[VerificationClass]
    missing_classes: list[VerificationClass]
    failed_classes: list[VerificationClass]
    independent_evidence_ids: list[str]
    assisted_evidence_ids: list[str]
    scheduled_probe_ids: list[str]
    next_probe_at: str | None
    fully_qualified: bool


class ArtifactCheckpointView(StrictModel):
    """One immutable learner work checkpoint bound to content hash and declared assistance."""

    checkpoint_id: Annotated[str, Field(min_length=4, max_length=160)]
    artifact_sha256: Sha256Hex
    parent_checkpoint_id: Annotated[str, Field(max_length=160)] = ""
    created_at: Annotated[str, Field(min_length=10, max_length=64)]
    change_summary: Annotated[str, Field(min_length=2, max_length=1000)]
    toolchain: Annotated[list[str], Field(min_length=1, max_length=24)]
    assistance: AssistanceLevel = "unknown"


class WorkVerificationChallengeView(StrictModel):
    """Post-artifact hidden modification/debugging/defense challenge."""

    challenge_id: str
    evidence_id: str
    kind: WorkVerificationKind
    prompt: str
    issued_at: str


class WorkProvenanceSubmission(StrictModel):
    """Learner-declared artifact history and responses to server-issued work challenges."""

    evidence_id: Annotated[str, Field(min_length=8, max_length=160)]
    artifact_id: Annotated[str, Field(min_length=4, max_length=160)]
    final_artifact_sha256: Sha256Hex
    checkpoints: Annotated[list[ArtifactCheckpointView], Field(min_length=1, max_length=24)]
    assistance_disclosure: AssistanceLevel = "unknown"
    source_attribution: Annotated[str, Field(max_length=1000)] = ""
    modification_challenge_id: Annotated[str, Field(min_length=8, max_length=160)]
    modification_evidence_reference: Annotated[str, Field(max_length=1000)] = ""
    debugging_challenge_id: Annotated[str, Field(min_length=8, max_length=160)]
    debugging_evidence_reference: Annotated[str, Field(max_length=1000)] = ""
    defense_challenge_id: Annotated[str, Field(min_length=8, max_length=160)]
    defense_response: Annotated[str, Field(max_length=4000)] = ""


class TrustedWorkProvenanceVerdict(StrictModel):
    """Trusted evaluator result for authorship, modification/debugging work, and defense."""

    evidence_id: Annotated[str, Field(min_length=8, max_length=160)]
    artifact_id: Annotated[str, Field(min_length=4, max_length=160)]
    disposition: Literal["accepted", "rejected", "disputed"]
    authorship_verified: bool
    modification_verified: bool
    debugging_verified: bool
    defense_verified: bool
    evaluator_id: Annotated[str, Field(min_length=2, max_length=120)]
    evaluator_version: Annotated[str, Field(min_length=1, max_length=80)]
    confidence: Annotated[int, Field(ge=0, le=100)]
    findings: Annotated[list[str], Field(max_length=16)] = Field(default_factory=list)


class WorkProvenanceState(StrictModel):
    """Deterministic work provenance state; missing legacy history remains explicitly missing."""

    evidence_id: str
    artifact_id: str = ""
    status: WorkProvenanceStatus = "challenge_issued"
    challenges: Annotated[list[WorkVerificationChallengeView], Field(max_length=3)] = Field(
        default_factory=list
    )
    final_artifact_sha256: str = ""
    checkpoints: Annotated[list[ArtifactCheckpointView], Field(max_length=24)] = Field(
        default_factory=list
    )
    assistance_disclosure: AssistanceLevel = "unknown"
    source_attribution: str = ""
    modification_evidence_reference: str = ""
    debugging_evidence_reference: str = ""
    defense_response: str = ""
    source_high_stakes_eligible: bool = False
    authorship_verified: bool = False
    modification_verified: bool = False
    debugging_verified: bool = False
    defense_verified: bool = False
    evaluator_id: str = ""
    evaluator_version: str = ""
    evaluation_id: str = ""
    captured_at: str = ""
    evaluated_at: str | None = None
    issues: Annotated[list[str], Field(max_length=24)] = Field(default_factory=list)
    eligible_for_readiness: bool = False


class CompetencyView(StrictModel):
    """Public competency metadata including exact dependency/evidence requirements."""

    id: str
    name: str
    category: str
    description: str
    weight: int
    prerequisites: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)


class RoleView(StrictModel):
    """Versioned role-profile candidate plus the exact graph/policy versions used by planning."""

    id: str
    version: str
    title: str
    summary: str
    graph_version: str
    evidence_policy_version: str
    validation_state: Literal["provisional", "approved"] = "provisional"
    default_target: TargetView
    competencies: list[CompetencyView]


class CompetencyEvidenceState(StrictModel):
    """Deterministic authoritative evidence state for one competency."""

    competency_id: str
    status: CompetencyEvidenceStatus = "unverified"
    accepted_evidence_ids: list[str] = Field(default_factory=list)
    disputed_evidence_ids: list[str] = Field(default_factory=list)
    last_evaluated_at: str | None = None
    no_hint_verified: bool = False
    reasoning_verified: bool = False
    assistance: AssistanceLevel = "unknown"


class PriorityCompetencyView(StrictModel):
    """Evidence-aware curriculum priority with diagnostics retained only as an ordering signal."""

    id: str
    name: str
    category: str
    planning_signal_percent: int
    diagnostic_signal_percent: int
    assessment_percent: int | None = None
    priority_gap_percent: int
    authoritative_gap_percent: int = 100
    evidence_status: CompetencyEvidenceStatus = "unverified"
    prerequisite_ids: list[str] = Field(default_factory=list)
    blocked_by: list[str] = Field(default_factory=list)
    active_misconception_codes: list[str] = Field(default_factory=list)
    priority_reason: str = ""
    focused: bool = False


class ActivityView(StrictModel):
    """One unique bounded work item with explicit G05 blueprint provenance."""

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
    item_family_id: str = ""
    item_family_version: str = ""
    item_family_trust: Literal["legacy_unverified", "trusted"] = "legacy_unverified"
    blueprint_id: str = ""
    blueprint_version: str = ""
    blueprint_trust: Literal["legacy_unverified", "trusted"] = "legacy_unverified"
    blueprint_approval_id: str = ""
    blueprint_approved_by: str = ""
    blueprint_approval_version: str = ""
    rubric_version: str = ""
    instance_seed: str = ""
    semantic_fingerprint: str = ""
    semantic_signature: str = ""
    semantic_tokens: list[str] = Field(default_factory=list, max_length=12)
    scenario_tags: list[str] = Field(default_factory=list, max_length=8)
    instance_requirements: list[str] = Field(default_factory=list, max_length=8)
    instance_contract_hash: str = ""
    plan_version_id: str = ""
    high_stakes_eligible: bool = False


class TaskExposureView(StrictModel):
    """Persisted served-instance exposure for replay and collision rejection."""

    instance_id: str
    item_family_id: str
    item_family_version: str
    blueprint_id: str
    blueprint_version: str
    rubric_version: str
    plan_version_id: str
    semantic_fingerprint: str
    semantic_signature: str
    semantic_tokens: list[str] = Field(default_factory=list, max_length=12)
    instance_contract_hash: str = ""
    high_stakes_eligible: bool = False
    served_at: str


class CollisionFingerprintView(StrictModel):
    """Unlinkable cohort-history fingerprint retained after learner data deletion."""

    item_family_id: str
    blueprint_id: str
    semantic_fingerprint: str
    semantic_signature: str
    semantic_tokens: list[str] = Field(default_factory=list, max_length=12)
    served_at: str


class PlanPrioritySnapshot(StrictModel):
    """Immutable scheduling evidence for one competency inside one plan version."""

    competency_id: str
    rank: Annotated[int, Field(ge=1)]
    evidence_status: CompetencyEvidenceStatus
    diagnostic_signal_percent: Annotated[int, Field(ge=0, le=100)]
    authoritative_gap_percent: Annotated[int, Field(ge=0, le=100)]
    prerequisite_ids: list[str]
    blocked_by: list[str]
    active_misconception_codes: list[str]
    focused: bool
    reason: str


class PlanDeltaView(StrictModel):
    """Deterministic difference from the immediately preceding immutable plan version."""

    previous_plan_version_id: str | None = None
    added_activity_ids: list[str] = Field(default_factory=list)
    removed_activity_ids: list[str] = Field(default_factory=list)
    retained_activity_ids: list[str] = Field(default_factory=list)
    priority_changes: list[str] = Field(default_factory=list)
    reason: str


class LearnerPlanVersion(StrictModel):
    """Immutable learner-specific curriculum snapshot bound to exact target/profile versions."""

    plan_version_id: str
    revision: Annotated[int, Field(ge=0)]
    created_at: str
    trigger: CurriculumTrigger
    role_id: str
    role_version: str
    graph_version: str
    evidence_policy_version: str
    target_fingerprint: str
    weekly_hours: Annotated[int, Field(ge=2, le=40)]
    focus_competency_ids: list[str]
    priorities: list[PlanPrioritySnapshot]
    activities: list[ActivityView]
    delta: PlanDeltaView
    task_exposures: list[TaskExposureView] = Field(default_factory=list, max_length=16)


class EvidenceRecordView(StrictModel):
    """A recorded evidence candidate; source/trust fields prevent silent promotion."""

    evidence_id: str = ""
    activity_id: str
    competency_id: str
    competency_name: str
    title: str
    submitted_at: str
    reflection: str
    evidence_reference: str
    criteria_met: list[str]
    confidence: int
    source: EvidenceSource = "learner_attested"
    disposition: EvidenceDisposition = "recorded"
    independence: EvidenceIndependence = "unverified"
    assistance: AssistanceLevel = "unknown"
    reasoning: ReasoningState = "not_observed"
    planning_signal_delta: int = Field(
        validation_alias=AliasChoices("planning_signal_delta", "provisional_mastery_delta")
    )
    next_review_at: str
    source_item_family_id: str = ""
    source_item_family_version: str = ""
    source_blueprint_id: str = ""
    source_blueprint_version: str = ""
    source_blueprint_approval_id: str = ""
    source_rubric_version: str = ""
    source_instance_contract_hash: str = ""
    source_plan_version_id: str = ""
    source_semantic_fingerprint: str = ""
    source_semantic_signature: str = ""
    source_high_stakes_eligible: bool = False


class EvidenceEvaluationRecord(StrictModel):
    """Immutable trusted evaluator observation retained in learner state and event snapshots."""

    evaluation_id: str
    evidence_id: str
    competency_id: str
    source: Literal["trusted_evaluator"] = "trusted_evaluator"
    disposition: Literal["accepted", "rejected", "disputed"]
    independence: EvidenceIndependence
    assistance: AssistanceLevel
    reasoning: ReasoningState
    evaluator_id: str
    evaluator_version: str
    rubric_version: str
    instance_contract_hash: str = ""
    confidence: int
    findings: list[str]
    misconception_codes: list[str]
    occurred_at: str


class MisconceptionRecord(StrictModel):
    """A deterministic misconception marker sourced from a trusted evaluation."""

    misconception_id: str
    competency_id: str
    code: str
    status: MisconceptionStatus = "active"
    evidence_id: str
    observed_at: str


class ReviewState(StrictModel):
    """Explicit review state; retention qualification is implemented by later DoD slices."""

    competency_id: str
    due_at: str
    stage: ReviewStage
    source_evidence_id: str
    reason: str


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

    schema_version: Literal[1, 2, 3, 4, 5, 6] = 6
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
    mastery: dict[str, int] = Field(default_factory=dict)
    completed_activity_ids: list[str]
    activities: list[ActivityView]
    plan_revision: int = 0
    active_plan_version_id: str | None = None
    plan_versions: list[LearnerPlanVersion] = Field(default_factory=list)
    focus_competency_ids: list[str] = Field(default_factory=list)
    evidence_history: list[EvidenceRecordView] = Field(default_factory=list)
    evidence_evaluations: list[EvidenceEvaluationRecord] = Field(default_factory=list)
    competency_evidence: dict[str, CompetencyEvidenceState] = Field(default_factory=dict)
    competency_qualification: dict[str, CompetencyQualificationState] = Field(default_factory=dict)
    verification_probes: list[VerificationProbeView] = Field(default_factory=list)
    work_provenance: dict[str, WorkProvenanceState] = Field(default_factory=dict)
    misconceptions: list[MisconceptionRecord] = Field(default_factory=list)
    review_state: dict[str, ReviewState] = Field(default_factory=dict)
    assessment_scores: dict[str, int] = Field(default_factory=dict)
    assessment_history: list[AssessmentRecordView] = Field(default_factory=list)


class PlanView(StrictModel):
    """Projection that separates planning signals from authoritative competency evidence."""

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
    competency_evidence: list[CompetencyEvidenceState]
    evidence_evaluations: list[EvidenceEvaluationRecord]
    qualifications: list[CompetencyQualificationView] = Field(default_factory=list)
    verification_probes: list[VerificationProbeView] = Field(default_factory=list)
    work_provenance: list[WorkProvenanceState] = Field(default_factory=list)
    active_misconceptions: list[MisconceptionRecord]
    review_state: list[ReviewState]
    current_activity: ActivityView | None
    completed_count: int
    total_count: int
    sequence: int
    weekly_hours: int
    plan_revision: int
    active_plan_version: LearnerPlanVersion
    plan_history: list[LearnerPlanVersion]
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
