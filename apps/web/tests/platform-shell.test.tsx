import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PlatformShell } from "../components/platform-shell";
import type { ApiAvailability } from "../server/health/runtime-health";

const STATES: ReadonlyArray<
  readonly [ApiAvailability, string, string]
> = [
  [
    "available",
    "Local API available",
    "The local API returned the expected liveness response."
  ],
  [
    "unavailable",
    "Local API unavailable",
    "The local API could not be confirmed within the local check window."
  ],
  [
    "invalid-response",
    "Local API response invalid",
    "The local API response did not match the expected liveness contract."
  ]
];

describe("PlatformShell", () => {
  it.each(STATES)(
    "renders the %s state with visible text and semantic status markup",
    (apiAvailability, label, description) => {
      const markup = renderToStaticMarkup(
        <PlatformShell apiAvailability={apiAvailability} />
      );

      expect(markup).toContain("AI Career Learning Platform");
      expect(markup).toContain('aria-labelledby="api-integration-heading"');
      expect(markup).toContain('role="status"');
      expect(markup).toContain('aria-atomic="true"');
      expect(markup).toContain('class="status-marker" aria-hidden="true"');
      expect(markup).toContain(`data-api-state="${apiAvailability}"`);
      expect(markup).toContain(label);
      expect(markup).toContain(description);
      expect(markup).toContain("local process liveness only");
    }
  );

  it("does not render adapter internals or server-only configuration", () => {
    const markup = renderToStaticMarkup(
      <PlatformShell apiAvailability="unavailable" />
    );

    for (const internalValue of [
      "timeout",
      "network",
      "http_status",
      "content_type",
      "invalid_json",
      "contract",
      "AI_PLATFORM_API_BASE_URL",
      "127.0.0.1",
      "/health/live"
    ]) {
      expect(markup).not.toContain(internalValue);
    }
  });
});
