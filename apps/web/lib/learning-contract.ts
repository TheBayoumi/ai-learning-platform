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
  readonly gap_percent: number;
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
}

export interface PlanView {
  readonly state_token: string;
  readonly learner_id: string;
  readonly learner_name: string;
  readonly role: RoleView;
  readonly readiness_percent: number;
  readonly priority_competencies: readonly PriorityCompetencyView[];
  readonly current_activity: ActivityView | null;
  readonly completed_count: number;
  readonly total_count: number;
  readonly sequence: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is readonly string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
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
    typeof value.gap_percent === "number"
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
    typeof value.estimated_minutes === "number"
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
    Array.isArray(value.priority_competencies) &&
    value.priority_competencies.every(isPriority) &&
    (value.current_activity === null || isActivity(value.current_activity)) &&
    typeof value.completed_count === "number" &&
    typeof value.total_count === "number" &&
    typeof value.sequence === "number"
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
