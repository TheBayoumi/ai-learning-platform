import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AssessmentCalibration } from "../components/assessment-calibration";

describe("AssessmentCalibration", () => {
  it("renders the bounded calibration policy before a plan is available", () => {
    const markup = renderToStaticMarkup(<AssessmentCalibration />);

    expect(markup).toContain("Objective planning calibration");
    expect(markup).toContain("30-minute signed attempt");
    expect(markup).toContain("Answers hidden until submission");
    expect(markup).toContain("30% maximum readiness influence");
    expect(markup).toContain("Create your adaptive learning plan first.");
  });

  it("does not embed answer keys or server configuration in client source", () => {
    const source = readFileSync(
      resolve(process.cwd(), "components/assessment-calibration.tsx"),
      "utf8"
    );

    for (const forbidden of [
      "correct_option_id",
      "CORRECT_OPTIONS",
      "AI_PLATFORM_LEARNER_STATE_SECRET",
      "AI_PLATFORM_API_BASE_URL",
      "127.0.0.1",
      "QUESTION_BY_ID"
    ]) {
      expect(source).not.toContain(forbidden);
    }
  });
});
