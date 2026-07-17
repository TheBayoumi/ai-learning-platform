import { describe, expect, it } from "vitest";

import {
  isHealthResponse,
  type HealthResponse
} from "../server/contracts/generated/health-response";

describe("generated health response contract", () => {
  it("accepts the OpenAPI response shape, empty detail, and allowed extra properties", () => {
    const response: unknown = { status: "ok", detail: "", trace: "ignored" };

    expect(isHealthResponse(response)).toBe(true);
    if (isHealthResponse(response)) {
      const typed: HealthResponse = response;
      expect(typed.status).toBe("ok");
      expect(typed.detail).toBe("");
    }
  });

  it("rejects invalid unknown values without coercion", () => {
    const invalidValues: unknown[] = [
      null,
      [],
      "ok",
      {},
      { status: "ok" },
      { detail: "process is live" },
      { status: "ready", detail: "process is live" },
      { status: "ok", detail: 1 }
    ];

    for (const value of invalidValues) {
      expect(isHealthResponse(value)).toBe(false);
    }
  });

  it("rejects inherited-only required properties", () => {
    const inheritedOnly = Object.create({
      status: "ok",
      detail: "process is live"
    }) as unknown;

    expect(isHealthResponse(inheritedOnly)).toBe(false);
  });
});
