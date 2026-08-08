export type EvidenceSource = "learner_attested" | "calibration" | "trusted_evaluator";
export type EvidenceDisposition = "recorded" | "accepted" | "rejected" | "disputed";
export type EvidenceIndependence = "unverified" | "assisted" | "independent";
export type AssistanceLevel = "unknown" | "none" | "hint" | "guided" | "answer_level";
export type ReasoningState = "not_observed" | "submitted" | "verified";
export type CompetencyEvidenceStatus = "unverified" | "partial" | "independent";
export type CurriculumTrigger =
  | "initial"
  | "assessment"
  | "manual_replan"
  | "trusted_evidence"
  | "state_migration";

export interface CompetencyView {
  readonly id: string;
  readonly name: string;
  readonly category: string;
  readonly description: string;
  readonly weight: number;
  readonly prerequisites: readonly string[];
  readonly evidence_requirements: readonly string[];
}

export interface TargetView {
  readonly role_id: string;
  readonly role_version: string;
  readonly seniority: string;
  readonly labor_market: string;
  readonly timeline_weeks: number;
  readonly geography: string;
  readonly stack_overlays: readonly string[];
  readonly industry_overlay: string | null;
  readonly company_overlay: string | null;
  readonly validation_state: "provisional" | "approved";
  readonly scope: string;
  readonly exclusions: readonly string[];
}

export interface RoleView {
  readonly id: string;
  readonly version: string;
  readonly title: string;
  readonly summary: string;
  readonly graph_version: string;
  readonly evidence_policy_version: string;
  readonly validation_state: "provisional" | "approved";
  readonly default_target: TargetView;
  readonly competencies: readonly CompetencyView[];
}

export interface CompetencyEvidenceState {
  readonly competency_id: string;
  readonly status: CompetencyEvidenceStatus;
  readonly accepted_evidence_ids: readonly string[];
  readonly disputed_evidence_ids: readonly string[];
  readonly last_evaluated_at: string | null;
  readonly no_hint_verified: boolean;
  readonly reasoning_verified: boolean;
  readonly assistance: AssistanceLevel;
}

export interface PriorityCompetencyView {
  readonly id: string;
  readonly name: string;
  readonly category: string;
  readonly planning_signal_percent: number;
  readonly diagnostic_signal_percent: number;
  readonly assessment_percent: number | null;
  readonly priority_gap_percent: number;
  readonly authoritative_gap_percent: number;
  readonly evidence_status: CompetencyEvidenceStatus;
  readonly prerequisite_ids: readonly string[];
  readonly blocked_by: readonly string[];
  readonly active_misconception_codes: readonly string[];
  readonly priority_reason: string;
  readonly focused: boolean;
}

export interface ActivityView {
  readonly id: string;
  readonly competency_id: string;
  readonly competency_name: string;
  readonly title: string;
  readonly objective: string;
  readonly deliverable: string;
  readonly acceptance_criteria: readonly string[];
  readonly estimated_minutes: number;
  readonly kind: "build" | "review";
  readonly rationale: string;
  readonly generation: number;
  readonly available_from: string | null;
}

export interface PlanPrioritySnapshot {
  readonly competency_id: string;
  readonly rank: number;
  readonly evidence_status: CompetencyEvidenceStatus;
  readonly diagnostic_signal_percent: number;
  readonly authoritative_gap_percent: number;
  readonly prerequisite_ids: readonly string[];
  readonly blocked_by: readonly string[];
  readonly active_misconception_codes: readonly string[];
  readonly focused: boolean;
  readonly reason: string;
}

export interface PlanDeltaView {
  readonly previous_plan_version_id: string | null;
  readonly added_activity_ids: readonly string[];
  readonly removed_activity_ids: readonly string[];
  readonly retained_activity_ids: readonly string[];
  readonly priority_changes: readonly string[];
  readonly reason: string;
}

export interface LearnerPlanVersion {
  readonly plan_version_id: string;
  readonly revision: number;
  readonly created_at: string;
  readonly trigger: CurriculumTrigger;
  readonly role_id: string;
  readonly role_version: string;
  readonly graph_version: string;
  readonly evidence_policy_version: string;
  readonly target_fingerprint: string;
  readonly weekly_hours: number;
  readonly focus_competency_ids: readonly string[];
  readonly priorities: readonly PlanPrioritySnapshot[];
  readonly activities: readonly ActivityView[];
  readonly delta: PlanDeltaView;
}

export interface EvidenceRecordView {
  readonly evidence_id: string;
  readonly activity_id: string;
  readonly competency_id: string;
  readonly competency_name: string;
  readonly title: string;
  readonly submitted_at: string;
  readonly reflection: string;
  readonly evidence_reference: string;
  readonly criteria_met: readonly string[];
  readonly confidence: number;
  readonly source: EvidenceSource;
  readonly disposition: EvidenceDisposition;
  readonly independence: EvidenceIndependence;
  readonly assistance: AssistanceLevel;
  readonly reasoning: ReasoningState;
  readonly planning_signal_delta: number;
  readonly next_review_at: string;
}

export interface EvidenceEvaluationRecord {
  readonly evaluation_id: string;
  readonly evidence_id: string;
  readonly competency_id: string;
  readonly source: "trusted_evaluator";
  readonly disposition: "accepted" | "rejected" | "disputed";
  readonly independence: EvidenceIndependence;
  readonly assistance: AssistanceLevel;
  readonly reasoning: ReasoningState;
  readonly evaluator_id: string;
  readonly evaluator_version: string;
  readonly rubric_version: string;
  readonly confidence: number;
  readonly findings: readonly string[];
  readonly misconception_codes: readonly string[];
  readonly occurred_at: string;
}

export interface MisconceptionRecord {
  readonly misconception_id: string;
  readonly competency_id: string;
  readonly code: string;
  readonly status: "active" | "resolved";
  readonly evidence_id: string;
  readonly observed_at: string;
}

export interface ReviewState {
  readonly competency_id: string;
  readonly due_at: string;
  readonly stage: "evidence_follow_up" | "retention_candidate";
  readonly source_evidence_id: string;
  readonly reason: string;
}

export interface AssessmentRecordView {
  readonly attempt_id: string;
  readonly bank_version: string;
  readonly submitted_at: string;
  readonly score_percent: number;
  readonly correct_count: number;
  readonly total_count: number;
  readonly competency_scores: Readonly<Record<string, number>>;
}

export interface AssessmentOptionView {
  readonly id: string;
  readonly text: string;
}

export interface AssessmentQuestionView {
  readonly id: string;
  readonly competency_id: string;
  readonly competency_name: string;
  readonly prompt: string;
  readonly options: readonly AssessmentOptionView[];
}

export interface AssessmentAttemptView {
  readonly attempt_token: string;
  readonly bank_version: string;
  readonly issued_at: string;
  readonly expires_at: string;
  readonly questions: readonly AssessmentQuestionView[];
}

export interface AssessmentFeedbackView {
  readonly question_id: string;
  readonly competency_id: string;
  readonly correct: boolean;
  readonly explanation: string;
}

export type ClaimState =
  | "engineering_available"
  | "validation_locked"
  | "partial_profile_evidence"
  | "ready_against_profile";

export interface PlanView {
  readonly state_token: string;
  readonly learner_id: string;
  readonly learner_name: string;
  readonly role: RoleView;
  readonly target: TargetView;
  readonly claim_state: ClaimState;
  readonly verified_readiness_percent: number | null;
  readonly planning_signal_percent: number;
  readonly diagnostic_signal_percent: number;
  readonly assessment_coverage_percent: number;
  readonly priority_competencies: readonly PriorityCompetencyView[];
  readonly competency_evidence: readonly CompetencyEvidenceState[];
  readonly evidence_evaluations: readonly EvidenceEvaluationRecord[];
  readonly active_misconceptions: readonly MisconceptionRecord[];
  readonly review_state: readonly ReviewState[];
  readonly current_activity: ActivityView | null;
  readonly completed_count: number;
  readonly total_count: number;
  readonly sequence: number;
  readonly weekly_hours: number;
  readonly plan_revision: number;
  readonly active_plan_version: LearnerPlanVersion;
  readonly plan_history: readonly LearnerPlanVersion[];
  readonly focus_competency_ids: readonly string[];
  readonly evidence_history: readonly EvidenceRecordView[];
  readonly assessment_history: readonly AssessmentRecordView[];
  readonly next_review_at: string | null;
}

export interface AssessmentSubmissionView {
  readonly score_percent: number;
  readonly correct_count: number;
  readonly total_count: number;
  readonly feedback: readonly AssessmentFeedbackView[];
  readonly plan: PlanView;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is readonly string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isNumberRecord(value: unknown): value is Readonly<Record<string, number>> {
  return isRecord(value) && Object.values(value).every((item) => typeof item === "number");
}

function isAssistance(value: unknown): value is AssistanceLevel {
  return ["unknown", "none", "hint", "guided", "answer_level"].includes(String(value));
}

function isIndependence(value: unknown): value is EvidenceIndependence {
  return ["unverified", "assisted", "independent"].includes(String(value));
}

function isReasoning(value: unknown): value is ReasoningState {
  return ["not_observed", "submitted", "verified"].includes(String(value));
}

function isEvidenceStatus(value: unknown): value is CompetencyEvidenceStatus {
  return value === "unverified" || value === "partial" || value === "independent";
}

function isCompetency(value: unknown): value is CompetencyView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    typeof value.category === "string" &&
    typeof value.description === "string" &&
    typeof value.weight === "number" &&
    isStringArray(value.prerequisites) &&
    isStringArray(value.evidence_requirements)
  );
}

function isTarget(value: unknown): value is TargetView {
  return (
    isRecord(value) &&
    typeof value.role_id === "string" &&
    typeof value.role_version === "string" &&
    typeof value.seniority === "string" &&
    typeof value.labor_market === "string" &&
    typeof value.timeline_weeks === "number" &&
    typeof value.geography === "string" &&
    isStringArray(value.stack_overlays) &&
    (value.industry_overlay === null || typeof value.industry_overlay === "string") &&
    (value.company_overlay === null || typeof value.company_overlay === "string") &&
    (value.validation_state === "provisional" || value.validation_state === "approved") &&
    typeof value.scope === "string" &&
    isStringArray(value.exclusions)
  );
}

function isRole(value: unknown): value is RoleView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.version === "string" &&
    typeof value.title === "string" &&
    typeof value.summary === "string" &&
    typeof value.graph_version === "string" &&
    typeof value.evidence_policy_version === "string" &&
    (value.validation_state === "provisional" || value.validation_state === "approved") &&
    isTarget(value.default_target) &&
    Array.isArray(value.competencies) &&
    value.competencies.every(isCompetency)
  );
}

function isCompetencyEvidence(value: unknown): value is CompetencyEvidenceState {
  return (
    isRecord(value) &&
    typeof value.competency_id === "string" &&
    isEvidenceStatus(value.status) &&
    isStringArray(value.accepted_evidence_ids) &&
    isStringArray(value.disputed_evidence_ids) &&
    (value.last_evaluated_at === null || typeof value.last_evaluated_at === "string") &&
    typeof value.no_hint_verified === "boolean" &&
    typeof value.reasoning_verified === "boolean" &&
    isAssistance(value.assistance)
  );
}

function isPriority(value: unknown): value is PriorityCompetencyView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    typeof value.category === "string" &&
    typeof value.planning_signal_percent === "number" &&
    typeof value.diagnostic_signal_percent === "number" &&
    (value.assessment_percent === null || typeof value.assessment_percent === "number") &&
    typeof value.priority_gap_percent === "number" &&
    typeof value.authoritative_gap_percent === "number" &&
    isEvidenceStatus(value.evidence_status) &&
    isStringArray(value.prerequisite_ids) &&
    isStringArray(value.blocked_by) &&
    isStringArray(value.active_misconception_codes) &&
    typeof value.priority_reason === "string" &&
    typeof value.focused === "boolean"
  );
}

function isActivity(value: unknown): value is ActivityView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.competency_id === "string" &&
    typeof value.competency_name === "string" &&
    typeof value.title === "string" &&
    typeof value.objective === "string" &&
    typeof value.deliverable === "string" &&
    isStringArray(value.acceptance_criteria) &&
    typeof value.estimated_minutes === "number" &&
    (value.kind === "build" || value.kind === "review") &&
    typeof value.rationale === "string" &&
    typeof value.generation === "number" &&
    (value.available_from === null || typeof value.available_from === "string")
  );
}

function isPlanPriority(value: unknown): value is PlanPrioritySnapshot {
  return (
    isRecord(value) &&
    typeof value.competency_id === "string" &&
    typeof value.rank === "number" &&
    isEvidenceStatus(value.evidence_status) &&
    typeof value.diagnostic_signal_percent === "number" &&
    typeof value.authoritative_gap_percent === "number" &&
    isStringArray(value.prerequisite_ids) &&
    isStringArray(value.blocked_by) &&
    isStringArray(value.active_misconception_codes) &&
    typeof value.focused === "boolean" &&
    typeof value.reason === "string"
  );
}

function isPlanDelta(value: unknown): value is PlanDeltaView {
  return (
    isRecord(value) &&
    (value.previous_plan_version_id === null || typeof value.previous_plan_version_id === "string") &&
    isStringArray(value.added_activity_ids) &&
    isStringArray(value.removed_activity_ids) &&
    isStringArray(value.retained_activity_ids) &&
    isStringArray(value.priority_changes) &&
    typeof value.reason === "string"
  );
}

function isCurriculumTrigger(value: unknown): value is CurriculumTrigger {
  return ["initial", "assessment", "manual_replan", "trusted_evidence", "state_migration"].includes(
    String(value)
  );
}

function isPlanVersion(value: unknown): value is LearnerPlanVersion {
  return (
    isRecord(value) &&
    typeof value.plan_version_id === "string" &&
    typeof value.revision === "number" &&
    typeof value.created_at === "string" &&
    isCurriculumTrigger(value.trigger) &&
    typeof value.role_id === "string" &&
    typeof value.role_version === "string" &&
    typeof value.graph_version === "string" &&
    typeof value.evidence_policy_version === "string" &&
    typeof value.target_fingerprint === "string" &&
    typeof value.weekly_hours === "number" &&
    isStringArray(value.focus_competency_ids) &&
    Array.isArray(value.priorities) &&
    value.priorities.every(isPlanPriority) &&
    Array.isArray(value.activities) &&
    value.activities.every(isActivity) &&
    isPlanDelta(value.delta)
  );
}

function isEvidence(value: unknown): value is EvidenceRecordView {
  return (
    isRecord(value) &&
    typeof value.evidence_id === "string" &&
    typeof value.activity_id === "string" &&
    typeof value.competency_id === "string" &&
    typeof value.competency_name === "string" &&
    typeof value.title === "string" &&
    typeof value.submitted_at === "string" &&
    typeof value.reflection === "string" &&
    typeof value.evidence_reference === "string" &&
    isStringArray(value.criteria_met) &&
    typeof value.confidence === "number" &&
    ["learner_attested", "calibration", "trusted_evaluator"].includes(String(value.source)) &&
    ["recorded", "accepted", "rejected", "disputed"].includes(String(value.disposition)) &&
    isIndependence(value.independence) &&
    isAssistance(value.assistance) &&
    isReasoning(value.reasoning) &&
    typeof value.planning_signal_delta === "number" &&
    typeof value.next_review_at === "string"
  );
}

function isEvidenceEvaluation(value: unknown): value is EvidenceEvaluationRecord {
  return (
    isRecord(value) &&
    typeof value.evaluation_id === "string" &&
    typeof value.evidence_id === "string" &&
    typeof value.competency_id === "string" &&
    value.source === "trusted_evaluator" &&
    ["accepted", "rejected", "disputed"].includes(String(value.disposition)) &&
    isIndependence(value.independence) &&
    isAssistance(value.assistance) &&
    isReasoning(value.reasoning) &&
    typeof value.evaluator_id === "string" &&
    typeof value.evaluator_version === "string" &&
    typeof value.rubric_version === "string" &&
    typeof value.confidence === "number" &&
    isStringArray(value.findings) &&
    isStringArray(value.misconception_codes) &&
    typeof value.occurred_at === "string"
  );
}

function isMisconception(value: unknown): value is MisconceptionRecord {
  return (
    isRecord(value) &&
    typeof value.misconception_id === "string" &&
    typeof value.competency_id === "string" &&
    typeof value.code === "string" &&
    (value.status === "active" || value.status === "resolved") &&
    typeof value.evidence_id === "string" &&
    typeof value.observed_at === "string"
  );
}

function isReviewState(value: unknown): value is ReviewState {
  return (
    isRecord(value) &&
    typeof value.competency_id === "string" &&
    typeof value.due_at === "string" &&
    (value.stage === "evidence_follow_up" || value.stage === "retention_candidate") &&
    typeof value.source_evidence_id === "string" &&
    typeof value.reason === "string"
  );
}

function isAssessmentRecord(value: unknown): value is AssessmentRecordView {
  return (
    isRecord(value) &&
    typeof value.attempt_id === "string" &&
    typeof value.bank_version === "string" &&
    typeof value.submitted_at === "string" &&
    typeof value.score_percent === "number" &&
    typeof value.correct_count === "number" &&
    typeof value.total_count === "number" &&
    isNumberRecord(value.competency_scores)
  );
}

function isAssessmentOption(value: unknown): value is AssessmentOptionView {
  return isRecord(value) && typeof value.id === "string" && typeof value.text === "string";
}

function isAssessmentQuestion(value: unknown): value is AssessmentQuestionView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.competency_id === "string" &&
    typeof value.competency_name === "string" &&
    typeof value.prompt === "string" &&
    Array.isArray(value.options) &&
    value.options.length >= 2 &&
    value.options.every(isAssessmentOption)
  );
}

function isClaimState(value: unknown): value is ClaimState {
  return (
    value === "engineering_available" ||
    value === "validation_locked" ||
    value === "partial_profile_evidence" ||
    value === "ready_against_profile"
  );
}

export function isRoleList(value: unknown): value is readonly RoleView[] {
  return Array.isArray(value) && value.length > 0 && value.every(isRole);
}

export function isPlanView(value: unknown): value is PlanView {
  return (
    isRecord(value) &&
    typeof value.state_token === "string" &&
    typeof value.learner_id === "string" &&
    typeof value.learner_name === "string" &&
    isRole(value.role) &&
    isTarget(value.target) &&
    isClaimState(value.claim_state) &&
    (value.verified_readiness_percent === null ||
      typeof value.verified_readiness_percent === "number") &&
    typeof value.planning_signal_percent === "number" &&
    typeof value.diagnostic_signal_percent === "number" &&
    typeof value.assessment_coverage_percent === "number" &&
    Array.isArray(value.priority_competencies) &&
    value.priority_competencies.every(isPriority) &&
    Array.isArray(value.competency_evidence) &&
    value.competency_evidence.every(isCompetencyEvidence) &&
    Array.isArray(value.evidence_evaluations) &&
    value.evidence_evaluations.every(isEvidenceEvaluation) &&
    Array.isArray(value.active_misconceptions) &&
    value.active_misconceptions.every(isMisconception) &&
    Array.isArray(value.review_state) &&
    value.review_state.every(isReviewState) &&
    (value.current_activity === null || isActivity(value.current_activity)) &&
    typeof value.completed_count === "number" &&
    typeof value.total_count === "number" &&
    typeof value.sequence === "number" &&
    typeof value.weekly_hours === "number" &&
    typeof value.plan_revision === "number" &&
    isPlanVersion(value.active_plan_version) &&
    Array.isArray(value.plan_history) &&
    value.plan_history.length > 0 &&
    value.plan_history.every(isPlanVersion) &&
    value.plan_history.some(
      (item) => item.plan_version_id === value.active_plan_version.plan_version_id
    ) &&
    isStringArray(value.focus_competency_ids) &&
    Array.isArray(value.evidence_history) &&
    value.evidence_history.every(isEvidence) &&
    Array.isArray(value.assessment_history) &&
    value.assessment_history.every(isAssessmentRecord) &&
    (value.next_review_at === null || typeof value.next_review_at === "string")
  );
}

export function isAssessmentAttemptView(value: unknown): value is AssessmentAttemptView {
  return (
    isRecord(value) &&
    typeof value.attempt_token === "string" &&
    typeof value.bank_version === "string" &&
    typeof value.issued_at === "string" &&
    typeof value.expires_at === "string" &&
    Array.isArray(value.questions) &&
    value.questions.length >= 2 &&
    value.questions.every(isAssessmentQuestion)
  );
}

export function isAssessmentSubmissionView(value: unknown): value is AssessmentSubmissionView {
  return (
    isRecord(value) &&
    typeof value.score_percent === "number" &&
    typeof value.correct_count === "number" &&
    typeof value.total_count === "number" &&
    Array.isArray(value.feedback) &&
    value.feedback.every(
      (item) =>
        isRecord(item) &&
        typeof item.question_id === "string" &&
        typeof item.competency_id === "string" &&
        typeof item.correct === "boolean" &&
        typeof item.explanation === "string"
    ) &&
    isPlanView(value.plan)
  );
}

export function readPlatformError(value: unknown): string {
  if (!isRecord(value) || !isRecord(value.detail)) {
    return "The platform request could not be completed.";
  }
  return typeof value.detail.message === "string"
    ? value.detail.message
    : "The platform request could not be completed.";
}
