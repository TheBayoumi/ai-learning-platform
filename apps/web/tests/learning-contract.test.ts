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
  id: "activity-python-123",
  competency_id: "python",
  competency_name: "Python engineering",
  title: "Build a module",
  objective: "Create a typed service.",
  deliverable: "Code and tests",
  acceptance_criteria: ["Typed", "Tested"],
  estimated_minutes: 90
};

describe("learning contract guards", () => {
  it("accepts the bounded role and plan projections", () => {
    expect(isRoleList([role])).toBe(true);
    expect(
      isPlanView({
        state_token: "signed-token",
        learner_id: "learner-1",
        learner_name: "Mahmoud",
        role,
        readiness_percent: 25,
        priority_competencies: [
          {
            id: "python",
            name: "Python engineering",
            category: "language",
            mastery_percent: 25,
            gap_percent: 75
          }
        ],
        current_activity: activity,
        completed_count: 0,
        total_count: 4,
        sequence: 0
      })
    ).toBe(true);
  });

  it("rejects malformed nested data", () => {
    expect(isRoleList([{ ...role, competencies: [{ id: "python" }] }])).toBe(false);
    expect(
      isPlanView({
        state_token: "token",
        learner_id: "learner-1",
        learner_name: "Mahmoud",
        role,
        readiness_percent: 25,
        priority_competencies: [],
        current_activity: { ...activity, acceptance_criteria: "not-an-array" },
        completed_count: 0,
        total_count: 4,
        sequence: 0
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
