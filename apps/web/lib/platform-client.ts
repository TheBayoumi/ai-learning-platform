import {
  isAssessmentAttemptView,
  isAssessmentSubmissionView,
  isPlanView,
  isRoleList,
  readPlatformError,
  type AssessmentAttemptView,
  type AssessmentSubmissionView,
  type PlanView,
  type RoleView
} from "./learning-contract";

interface RequestOptions {
  readonly method?: "GET" | "POST" | "DELETE";
  readonly body?: unknown;
}

export async function platformRequest(path: string, options: RequestOptions = {}): Promise<unknown> {
  const response = await fetch(`/api/platform/${path}`, {
    method: options.method ?? "GET",
    headers:
      options.body === undefined
        ? { accept: "application/json" }
        : { accept: "application/json", "content-type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
    credentials: "same-origin"
  });

  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new Error("The learning service returned an unreadable response.");
  }
  if (!response.ok) {
    throw new Error(readPlatformError(value));
  }
  return value;
}

export async function loadRoles(): Promise<readonly RoleView[]> {
  const value = await platformRequest("career-tracks");
  if (!isRoleList(value)) {
    throw new Error("The career catalog did not match the expected contract.");
  }
  return value;
}

export async function resumePlan(stateToken: string): Promise<PlanView> {
  const value = await platformRequest("plans/resume", {
    method: "POST",
    body: { state_token: stateToken }
  });
  if (!isPlanView(value)) {
    throw new Error("The saved learning plan did not match the expected contract.");
  }
  return value;
}

export async function createPlan(body: Readonly<{
  learner_name: string;
  target_role: string;
  target: Readonly<{
    seniority: string;
    labor_market: string;
    timeline_weeks: number;
    geography: string;
    stack_overlays: readonly string[];
    industry_overlay: string | null;
    company_overlay: string | null;
  }>;
  weekly_hours: number;
  experience_summary: string;
  ratings: readonly Readonly<{ competency_id: string; score: number }>[];
}>): Promise<PlanView> {
  const value = await platformRequest("plans", { method: "POST", body });
  if (!isPlanView(value)) {
    throw new Error("The generated learning plan did not match the expected contract.");
  }
  return value;
}

export async function completeActivity(body: Readonly<{
  state_token: string;
  activity_id: string;
  reflection: string;
  evidence_reference: string;
  criteria_met: readonly string[];
  confidence: number;
}>): Promise<PlanView> {
  const value = await platformRequest("progress", { method: "POST", body });
  if (!isPlanView(value)) {
    throw new Error("The updated learning plan did not match the expected contract.");
  }
  return value;
}

export async function replan(body: Readonly<{
  state_token: string;
  weekly_hours: number;
  focus_competency_ids: readonly string[];
}>): Promise<PlanView> {
  const value = await platformRequest("plans/replan", { method: "POST", body });
  if (!isPlanView(value)) {
    throw new Error("The replanned curriculum did not match the expected contract.");
  }
  return value;
}

export async function startAssessment(stateToken: string): Promise<AssessmentAttemptView> {
  const value = await platformRequest("assessments/start", {
    method: "POST",
    body: { state_token: stateToken, question_count: 4 }
  });
  if (!isAssessmentAttemptView(value)) {
    throw new Error("The assessment attempt did not match the expected contract.");
  }
  return value;
}

export async function submitAssessment(body: Readonly<{
  state_token: string;
  attempt_token: string;
  answers: readonly Readonly<{ question_id: string; option_id: string }>[];
}>): Promise<AssessmentSubmissionView> {
  const value = await platformRequest("assessments/submit", { method: "POST", body });
  if (!isAssessmentSubmissionView(value)) {
    throw new Error("The assessment result did not match the expected contract.");
  }
  return value;
}

export async function deleteAccount(): Promise<void> {
  const value = await platformRequest("account", {
    method: "DELETE",
    body: { confirmation: "DELETE" }
  });
  if (
    typeof value !== "object" ||
    value === null ||
    !("deleted" in value) ||
    value.deleted !== true
  ) {
    throw new Error("The account deletion response did not match the expected contract.");
  }
}


export interface AccountDataExport {
  readonly schema_version: 1;
  readonly generated_at: string;
  readonly learners: readonly unknown[];
  readonly redactions: readonly string[];
  readonly retention_notes: readonly string[];
}

function isAccountDataExport(value: unknown): value is AccountDataExport {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Partial<AccountDataExport>;
  return (
    candidate.schema_version === 1 &&
    typeof candidate.generated_at === "string" &&
    Array.isArray(candidate.learners) &&
    Array.isArray(candidate.redactions) &&
    Array.isArray(candidate.retention_notes)
  );
}

export async function exportAccount(): Promise<AccountDataExport> {
  const value = await platformRequest("account/export");
  if (!isAccountDataExport(value)) {
    throw new Error("The account export response did not match the expected contract.");
  }
  return value;
}
