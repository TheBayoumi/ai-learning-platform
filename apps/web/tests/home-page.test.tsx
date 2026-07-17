import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiAvailability } from "../server/health/runtime-health";

const runtime = vi.hoisted(() => ({
  resolveRuntimeApiAvailability: vi.fn()
}));

vi.mock("../server/health/runtime-health", () => runtime);

import HomePage, { dynamic } from "../app/page";

const LABELS: ReadonlyArray<readonly [ApiAvailability, string]> = [
  ["available", "Local API available"],
  ["unavailable", "Local API unavailable"],
  ["invalid-response", "Local API response invalid"]
];

beforeEach(() => {
  runtime.resolveRuntimeApiAvailability.mockReset();
});

describe("HomePage", () => {
  it("is explicitly rendered at request time", () => {
    expect(dynamic).toBe("force-dynamic");
  });

  it.each(LABELS)("renders the resolved %s state", async (state, label) => {
    runtime.resolveRuntimeApiAvailability.mockResolvedValue(state);

    const markup = renderToStaticMarkup(await HomePage());

    expect(runtime.resolveRuntimeApiAvailability).toHaveBeenCalledTimes(1);
    expect(markup).toContain(label);
  });

  it("keeps server diagnostic context out of rendered output", async () => {
    runtime.resolveRuntimeApiAvailability.mockResolvedValue("available");

    const markup = renderToStaticMarkup(await HomePage());

    expect(markup).not.toContain("traceparent");
    expect(markup).not.toContain("web.health.request.completed");
    expect(markup).not.toContain("0123456789abcdef0123456789abcdef");
    expect(markup).not.toContain("0123456789abcdef");
  });
});
