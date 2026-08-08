import { describe, expect, it } from "vitest";

import { isPlanView, isRoleList, readPlatformError } from "../lib/learning-contract";

const target = {
  role_id: "junior-python-backend-engineer",
  role_version: "2026.07-provisional-1",
  seniority: "Entry-level / junior individual contributor",
  labor_market: "Egypt and MENA local roles or English-speaking remote roles",
  timeline_weeks: 20,
  geography: "Egypt / MENA",
  stack_overlays: ["Python", "FastAPI", "PostgreSQL"],
  industry_overlay: null,
  company_overlay: null,
  validation_state: "provisional" as const,
  scope: "Provisional adult B2C preparation.",
  exclusions: ["No employment guarantee."]
};

const role = {
  id: "junior-python-backend-engineer",
  version: "2026.07-provisional-1",
  title: "Junior Python Backend Engineer",
  summary: "Role",
  graph_version: "2026.07-provisional-1.graph-v1",
  evidence_policy_version: "competency-evidence-v1",
  validation_state: "provisional" as const,
  default_target: target,
  competencies: [
    {
      id: "python",
      name: "Python engineering",
      category: "language",
      description: "Typed Python",
      weight: 14,
      prerequisites: [],
      evidence_requirements: ["trusted_evaluator", "independent", "no_assistance", "reasoning_verified"]
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
  rationale: "Current planning priority and role weight",
  generation: 0,
  available_from: null
};


const planPriority = {
  competency_id: "python",
  rank: 1,
  evidence_status: "independent" as const,
  diagnostic_signal_percent: 48,
  authoritative_gap_percent: 0,
  prerequisite_ids: [],
  blocked_by: [],
  active_misconception_codes: ["boundary-condition-omission"],
  focused: true,
  reason: "Authoritative evidence is independent."
};

const planVersion = {
  plan_version_id: "plan-version-1",
  revision: 1,
  created_at: "2026-07-24T12:10:00+00:00",
  trigger: "trusted_evidence" as const,
  role_id: role.id,
  role_version: role.version,
  graph_version: role.graph_version,
  evidence_policy_version: role.evidence_policy_version,
  target_fingerprint: "target-fingerprint",
  weekly_hours: 8,
  focus_competency_ids: ["python"],
  priorities: [planPriority],
  activities: [activity],
  delta: {
    previous_plan_version_id: "plan-version-0",
    added_activity_ids: [activity.id],
    removed_activity_ids: [],
    retained_activity_ids: [],
    priority_changes: ["python:2->1"],
    reason: "trusted_evidence: deterministic replan"
  }
};

const evidence = {
  evidence_id: "evidence-123",
  activity_id: activity.id,
  competency_id: "python",
  competency_name: "Python engineering",
  title: activity.title,
  submitted_at: "2026-07-24T12:00:00+00:00",
  reflection: "I built and tested the service.",
  evidence_reference: "pull/7",
  criteria_met: ["Typed", "Tested"],
  confidence: 3,
  source: "learner_attested" as const,
  disposition: "accepted" as const,
  independence: "independent" as const,
  assistance: "none" as const,
  reasoning: "verified" as const,
  planning_signal_delta: 18,
  next_review_at: "2026-07-31T12:00:00+00:00"
};

const competencyEvidence = {
  competency_id: "python",
  status: "independent" as const,
  accepted_evidence_ids: [evidence.evidence_id],
  disputed_evidence_ids: [],
  last_evaluated_at: "2026-07-24T12:10:00+00:00",
  no_hint_verified: true,
  reasoning_verified: true,
  assistance: "none" as const
};

const evaluation = {
  evaluation_id: "evaluation-123",
  evidence_id: evidence.evidence_id,
  competency_id: "python",
  source: "trusted_evaluator" as const,
  disposition: "accepted" as const,
  independence: "independent" as const,
  assistance: "none" as const,
  reasoning: "verified" as const,
  evaluator_id: "deterministic-evaluator",
  evaluator_version: "g02-v1",
  rubric_version: "role-rubric-v1",
  confidence: 92,
  findings: ["Behavior matched the evaluated criterion."],
  misconception_codes: ["boundary-condition-omission"],
  occurred_at: "2026-07-24T12:10:00+00:00"
};

const misconception = {
  misconception_id: "misconception-123",
  competency_id: "python",
  code: "boundary-condition-omission",
  status: "active" as const,
  evidence_id: evidence.evidence_id,
  observed_at: evaluation.occurred_at
};

const reviewState = {
  competency_id: "python",
  due_at: "2026-07-31T12:10:00+00:00",
  stage: "retention_candidate" as const,
  source_evidence_id: evidence.evidence_id,
  reason: "Independent evidence qualified for a later retention probe."
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
  target,
  claim_state: "validation_locked" as const,
  verified_readiness_percent: null,
  planning_signal_percent: 25,
  diagnostic_signal_percent: 48,
  assessment_coverage_percent: 10,
  priority_competencies: [
    {
      id: "python",
      name: "Python engineering",
      category: "language",
      planning_signal_percent: 25,
      diagnostic_signal_percent: 48,
      assessment_percent: 100,
      priority_gap_percent: 52,
      authoritative_gap_percent: 0,
      evidence_status: "independent" as const,
      prerequisite_ids: [],
      blocked_by: [],
      active_misconception_codes: ["boundary-condition-omission"],
      priority_reason: "Independent evidence closes this authoritative gap.",
      focused: true
    }
  ],
  competency_evidence: [competencyEvidence],
  evidence_evaluations: [evaluation],
  active_misconceptions: [misconception],
  review_state: [reviewState],
  current_activity: activity,
  completed_count: 0,
  total_count: 4,
  sequence: 2,
  weekly_hours: 8,
  plan_revision: 1,
  active_plan_version: planVersion,
  plan_history: [planVersion],
  focus_competency_ids: ["python"],
  evidence_history: [evidence],
  assessment_history: [assessment],
  next_review_at: evidence.next_review_at
};

describe("learning contract guards", () => {
  it("accepts resolved targets and deterministic evidence projections", () => {
    expect(isRoleList([role])).toBe(true);
    expect(isPlanView(validPlan)).toBe(true);
  });

  it("rejects malformed nested evidence state and fake readiness claims", () => {
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
        evidence_history: [{ ...evidence, source: "invented" }]
      })
    ).toBe(false);
    expect(
      isPlanView({
        ...validPlan,
        competency_evidence: [{ ...competencyEvidence, status: "mastered" }]
      })
    ).toBe(false);
    expect(
      isPlanView({
        ...validPlan,
        evidence_evaluations: [{ ...evaluation, source: "learner_attested" }]
      })
    ).toBe(false);
    expect(
      isPlanView({
        ...validPlan,
        assessment_history: [{ ...assessment, competency_scores: { python: "high" } }]
      })
    ).toBe(false);
    expect(isPlanView({ ...validPlan, claim_state: "made-up" })).toBe(false);
    expect(isRoleList([{ ...role, graph_version: 42 }])).toBe(false);
    expect(
      isPlanView({
        ...validPlan,
        priority_competencies: [{ ...validPlan.priority_competencies[0], blocked_by: "python" }]
      })
    ).toBe(false);
    expect(
      isPlanView({ ...validPlan, active_plan_version: { ...planVersion, trigger: "invented" } })
    ).toBe(false);
    expect(isPlanView({ ...validPlan, plan_history: [] })).toBe(false);
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
