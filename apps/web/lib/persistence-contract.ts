import {
  isAssessmentAttemptView,
  isAssessmentSubmissionView,
  isPlanView,
  type AssessmentAttemptView,
  type AssessmentSubmissionView,
  type PlanView
} from "./learning-contract";

export type PersistenceMode = "signed_state" | "postgres";

export interface RuntimeCapabilitiesView {
  readonly persistence_mode: PersistenceMode;
}

export interface PersistentPlanView {
  readonly plan: PlanView;
  readonly version: number;
}

export interface PersistentAssessmentAttemptView {
  readonly attempt: AssessmentAttemptView;
}

export interface PersistentAssessmentSubmissionView {
  readonly submission: AssessmentSubmissionView;
  readonly version: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isRuntimeCapabilitiesView(
  value: unknown
): value is RuntimeCapabilitiesView {
  return (
    isRecord(value) &&
    (value.persistence_mode === "signed_state" || value.persistence_mode === "postgres")
  );
}

export function isPersistentPlanView(value: unknown): value is PersistentPlanView {
  return (
    isRecord(value) &&
    isPlanView(value.plan) &&
    Number.isInteger(value.version) &&
    typeof value.version === "number" &&
    value.version >= 0
  );
}

export function isPersistentAssessmentAttemptView(
  value: unknown
): value is PersistentAssessmentAttemptView {
  return isRecord(value) && isAssessmentAttemptView(value.attempt);
}

export function isPersistentAssessmentSubmissionView(
  value: unknown
): value is PersistentAssessmentSubmissionView {
  return (
    isRecord(value) &&
    isAssessmentSubmissionView(value.submission) &&
    Number.isInteger(value.version) &&
    typeof value.version === "number" &&
    value.version >= 0
  );
}
