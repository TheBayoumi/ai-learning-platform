export interface CompetencyView {
  readonly id: string;
  readonly name: string;
  readonly category: string;
  readonly description: string;
  readonly weight: number;
}

export interface RoleView {
  readonly id: string;
  readonly version: string;
  readonly title: string;
  readonly summary: string;
  readonly competencies: readonly CompetencyView[];
}

export interface PriorityCompetencyView {
  readonly id: string;
  readonly name: string;
  readonly category: string;
  readonly mastery_percent: number;
  readonly effective_percent: number;
  readonly assessment_percent: number | null;
  readonly gap_percent: number;
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

export interface EvidenceRecordView {
  readonly activity_id: string;
  readonly competency_id: string;
  readonly competency_name: string;
  readonly title: string;
  readonly submitted_at: string;
  readonly reflection: string;
  readonly evidence_reference: string;
  readonly criteria_met: readonly string[];
  readonly confidence: number;
  readonly provisional_mastery_delta: number;
  readonly next_review_at: string;
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

export interface PlanView {
  readonly state_token: string;
  readonly learner_id: string;
  readonly learner_name: string;
  readonly role: RoleView;
  readonly readiness_percent: number;
  readonly evidence_readiness_percent: number;
  readonly assessment_coverage_percent: number;
  readonly priority_competencies: readonly PriorityCompetencyView[];
  readonly current_activity: ActivityView | null;
  readonly completed_count: number;
  readonly total_count: number;
  readonly sequence: number;
  readonly weekly_hours: number;
  readonly plan_revision: number;
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

function isCompetency(value: unknown): value is CompetencyView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    typeof value.category === "string" &&
    typeof value.description === "string" &&
    typeof value.weight === "number"
  );
}

function isRole(value: unknown): value is RoleView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.version === "string" &&
    typeof value.title === "string" &&
    typeof value.summary === "string" &&
    Array.isArray(value.competencies) &&
    value.competencies.every(isCompetency)
  );
}

function isPriority(value: unknown): value is PriorityCompetencyView {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.name === "string" &&
    typeof value.category === "string" &&
    typeof value.mastery_percent === "number" &&
    typeof value.effective_percent === "number" &&
    (value.assessment_percent === null || typeof value.assessment_percent === "number") &&
    typeof value.gap_percent === "number" &&
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

function isEvidence(value: unknown): value is EvidenceRecordView {
  return (
    isRecord(value) &&
    typeof value.activity_id === "string" &&
    typeof value.competency_id === "string" &&
    typeof value.competency_name === "string" &&
    typeof value.title === "string" &&
    typeof value.submitted_at === "string" &&
    typeof value.reflection === "string" &&
    typeof value.evidence_reference === "string" &&
    isStringArray(value.criteria_met) &&
    typeof value.confidence === "number" &&
    typeof value.provisional_mastery_delta === "number" &&
    typeof value.next_review_at === "string"
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
    typeof value.readiness_percent === "number" &&
    typeof value.evidence_readiness_percent === "number" &&
    typeof value.assessment_coverage_percent === "number" &&
    Array.isArray(value.priority_competencies) &&
    value.priority_competencies.every(isPriority) &&
    (value.current_activity === null || isActivity(value.current_activity)) &&
    typeof value.completed_count === "number" &&
    typeof value.total_count === "number" &&
    typeof value.sequence === "number" &&
    typeof value.weekly_hours === "number" &&
    typeof value.plan_revision === "number" &&
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
