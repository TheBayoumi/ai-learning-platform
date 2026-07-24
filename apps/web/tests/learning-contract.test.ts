import { describe, expect, it } from "vitest";

import { isPlanView, isRoleList, readPlatformError } from "../lib/learning-contract";

const role = {
  id: "junior-python-backend-engineer",
  version: "2026.07-provisional-1",
  title: "Junior Python Backend Engineer",
  summary: "Role",
  competencies: [
    {
      id: "python",
      name: "Python engineering",
      category: "language",
      description: "Typed Python",
      weight: 14
    }
  ]
};

const activity = {
  id: "activity-build-python-123",
  competency_id: "python",
  competency_name: "Python engineering",
  title: "Build a module",
  objective: "Create a typed service.",
  deliverable: "Code and tests",
  acceptance_criteria: ["Typed", "Tested"],
  estimated_minutes: 90,
  kind: "build",
  rationale: "Current gap and role weight",
  generation: 0,
  available_from: null
};

const evidence = {
  activity_id: activity.id,
  competency_id: "python",
  competency_name: "Python engineering",
  title: activity.title,
  submitted_at: "2026-07-24T12:00:00+00:00",
  reflection: "I built and tested the service.",
  evidence_reference: "pull/7",
  criteria_met: ["Typed", "Tested"],
  confidence: 3,
  provisional_mastery_delta: 18,
  next_review_at: "2026-07-31T12:00:00+00:00"
};

const assessment = {
  attempt_id: "attempt-1",
  bank_version: "2026.07-calibration-1",
  submitted_at: "2026-07-24T12:30:00+00:00",
  score_percent: 100,
  correct_count: 1,
  total_count: 1,
  competency_scores: { python: 100 }
};

const validPlan = {
  state_token: "signed-token",
  learner_id: "learner-1",
  learner_name: "Mahmoud",
  role,
  readiness_percent: 48,
  evidence_readiness_percent: 25,
  assessment_coverage_percent: 10,
  priority_competencies: [
    {
      id: "python",
      name: "Python engineering",
      category: "language",
      mastery_percent: 25,
      effective_percent: 48,
      assessment_percent: 100,
      gap_percent: 52,
      focused: true
    }
  ],
  current_activity: activity,
  completed_count: 0,
  total_count: 4,
  sequence: 1,
  weekly_hours: 8,
  plan_revision: 1,
  focus_competency_ids: ["python"],
  evidence_history: [evidence],
  assessment_history: [assessment],
  next_review_at: evidence.next_review_at
};

describe("learning contract guards", () => {
  it("accepts evidence, calibration, and blended plan projections", () => {
    expect(isRoleList([role])).toBe(true);
    expect(isPlanView(validPlan)).toBe(true);
  });

  it("rejects malformed nested adaptive data", () => {
    expect(isRoleList([{ ...role, competencies: [{ id: "python" }] }])).toBe(false);
    expect(
      isPlanView({
        ...validPlan,
        current_activity: { ...activity, kind: "invalid" }
      })
    ).toBe(false);
    expect(
      isPlanView({
        ...validPlan,
        evidence_history: [{ ...evidence, criteria_met: "not-an-array" }]
      })
    ).toBe(false);
    expect(
      isPlanView({
        ...validPlan,
        assessment_history: [{ ...assessment, competency_scores: { python: "high" } }]
      })
    ).toBe(false);
  });

  it("extracts only the stable public error message", () => {
    expect(
      readPlatformError({
        detail: {
          code: "INVALID_STATE_TOKEN",
          message: "The saved learning session is invalid or has been modified.",
          internal: "secret"
        }
      })
    ).toBe("The saved learning session is invalid or has been modified.");
    expect(readPlatformError({ detail: "bad" })).toBe(
      "The platform request could not be completed."
    );
  });
});
