import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PlatformShell } from "../components/platform-shell";
import type { ApiAvailability } from "../server/health/runtime-health";

const STATES: ReadonlyArray<readonly [ApiAvailability, string]> = [
  ["available", "Learning service online"],
  ["unavailable", "Learning service unavailable"],
  ["invalid-response", "Learning service contract mismatch"]
];

describe("PlatformShell", () => {
  it.each(STATES)(
    "renders the %s state inside the learner-facing product",
    (apiAvailability, label) => {
      const markup = renderToStaticMarkup(
        <PlatformShell apiAvailability={apiAvailability} />
      );

      expect(markup).toContain("Career Atlas");
      expect(markup).toContain("Your target role becomes a living training system.");
      expect(markup).toContain("Junior Python Backend Engineer");
      expect(markup).toContain("Build your personal path");
      expect(markup).toContain("Rate your current evidence");
      expect(markup).toContain(label);
      expect(markup).toContain(`service-state-${apiAvailability}`);
      expect(markup).toContain('role="status"');
    }
  );

  it("does not render server-only configuration or diagnostic internals", () => {
    const markup = renderToStaticMarkup(
      <PlatformShell apiAvailability="unavailable" />
    );

    for (const internalValue of [
      "network",
      "http_status",
      "content_type",
      "invalid_json",
      "AI_PLATFORM_API_BASE_URL",
      "127.0.0.1",
      "/health/live",
      "LEARNER_STATE_SECRET"
    ]) {
      expect(markup).not.toContain(internalValue);
    }
  });
});
