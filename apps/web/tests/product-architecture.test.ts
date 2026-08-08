import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), "utf8");
}

describe("Career Atlas product architecture", () => {
  it("keeps the root layout free of feature-global stylesheet pollution", () => {
    const layout = source("app/layout.tsx");

    expect(layout).toContain('import "./globals.css"');
    expect(layout).not.toContain("adaptive-curriculum.css");
    expect(layout).not.toContain("assessment-calibration.css");
  });

  it("uses routed application surfaces instead of the retired stacked beta shell", () => {
    for (const path of [
      "app/onboarding/page.tsx",
      "app/app/page.tsx",
      "app/app/learn/page.tsx",
      "app/app/roadmap/page.tsx",
      "app/app/projects/page.tsx",
      "app/app/assessments/page.tsx",
      "app/app/readiness/page.tsx",
      "app/app/profile/page.tsx"
    ]) {
      expect(existsSync(resolve(process.cwd(), path)), path).toBe(true);
    }

    for (const retiredPath of [
      "components/platform-shell.tsx",
      "components/learning-platform.tsx",
      "components/assessment-calibration.tsx",
      "app/adaptive-curriculum.css",
      "app/assessment-calibration.css"
    ]) {
      expect(existsSync(resolve(process.cwd(), retiredPath)), retiredPath).toBe(false);
    }
  });

  it("exposes every learning workspace destination from the application shell", () => {
    const shell = source("components/app/app-shell.tsx");

    for (const href of [
      '"/app"',
      '"/app/learn"',
      '"/app/roadmap"',
      '"/app/projects"',
      '"/app/assessments"',
      '"/app/readiness"',
      '"/app/profile"'
    ]) {
      expect(shell).toContain(href);
    }
  });

  it("resolves the Target before plan creation instead of treating a role ID as sufficient", () => {
    const onboarding = source("components/onboarding/onboarding.tsx");

    expect(onboarding).toContain("loadRoles()");
    expect(onboarding).toContain("selectedRoleId");
    expect(onboarding).toContain("target_role: selectedRole.id");
    expect(onboarding).toContain("seniority: target.seniority");
    expect(onboarding).toContain("labor_market: target.laborMarket");
    expect(onboarding).toContain("timeline_weeks: target.timelineWeeks");
    expect(onboarding).toContain("geography: target.geography");
    expect(onboarding).toContain("stack_overlays: stackOverlays");
    expect(onboarding).not.toContain("const activeRole = roles[0]");
  });

  it("keeps unverified readiness and mastery claims out of learner-facing workspace code", () => {
    const dashboard = source("components/app/dashboard-view.tsx");
    const readiness = source("components/app/readiness-view.tsx");
    const roadmap = source("components/app/roadmap-view.tsx");
    const projects = source("components/app/projects-view.tsx");
    const combined = [dashboard, readiness, roadmap, projects].join("\n");

    for (const forbidden of [
      "readiness_percent",
      "evidence_readiness_percent",
      "mastery_percent",
      "effective_percent",
      "provisional_mastery_delta"
    ]) {
      expect(combined).not.toContain(forbidden);
    }
    expect(readiness).toContain("Readiness conclusion");
    expect(readiness).toContain('value="Locked"');
    expect(dashboard).toContain("planning_signal_percent");
  });

  it("keeps assessment answer keys out of the routed client application", () => {
    const assessment = source("components/app/assessments-view.tsx");

    for (const forbidden of [
      "correct_option_id",
      "CORRECT_OPTIONS",
      "QUESTION_BY_ID",
      "AI_PLATFORM_LEARNER_STATE_SECRET"
    ]) {
      expect(assessment).not.toContain(forbidden);
    }
  });
});
