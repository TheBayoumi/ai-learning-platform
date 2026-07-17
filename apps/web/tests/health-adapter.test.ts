import { afterEach, describe, expect, it, vi } from "vitest";

import { parseApiBaseUrl } from "../server/config/api-base";
import {
  createHealthAdapter,
  type FetchLike
} from "../server/health/health-adapter";
import {
  createWebHealthDiagnostics,
  type WebHealthDiagnostics,
  type WebHealthRequestCompleted
} from "../server/diagnostics/health-diagnostics";

const API_BASE_URL = parseApiBaseUrl("http://127.0.0.1:8000");

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}

function quietDiagnostics(): WebHealthDiagnostics {
  return createWebHealthDiagnostics({ eventSink: () => undefined });
}

function adapterWith(
  fetchImplementation: FetchLike,
  timeoutMs = 2_000,
  diagnostics: WebHealthDiagnostics = quietDiagnostics()
) {
  return createHealthAdapter({
    apiBaseUrl: API_BASE_URL,
    diagnostics,
    fetch: fetchImplementation,
    timeoutMs
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("server health adapter", () => {
  it("uses the injected fetch and exact bounded liveness request", async () => {
    const fetchImplementation = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse({ status: "ok", detail: "", extra: "allowed" })
    );

    await expect(adapterWith(fetchImplementation).checkHealth()).resolves.toEqual({
      kind: "available"
    });
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
    const [url, options] = fetchImplementation.mock.calls[0] ?? [];
    expect(url).toEqual(new URL("http://127.0.0.1:8000/health/live"));
    expect(options).toMatchObject({
      method: "GET",
      cache: "no-store",
      credentials: "omit",
      redirect: "error"
    });
    expect(options?.headers).toEqual({
      Accept: "application/json",
      traceparent: expect.stringMatching(
        /^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$/
      )
    });
    expect(options?.signal).toBeInstanceOf(AbortSignal);
  });

  it("emits exactly one fixed event for every non-timeout result category", async () => {
    const cases: ReadonlyArray<{
      readonly expectedReason: WebHealthRequestCompleted["reason"];
      readonly expectedResult: WebHealthRequestCompleted["result"];
      readonly expectedStatus: number;
      readonly fetch: FetchLike;
      readonly name: string;
    }> = [
      {
        name: "available",
        fetch: vi
          .fn<typeof fetch>()
          .mockResolvedValue(
            jsonResponse({
              status: "ok",
              detail: "available-response-detail-canary"
            })
          ),
        expectedResult: "available",
        expectedReason: "ok",
        expectedStatus: 200
      },
      {
        name: "network",
        fetch: vi.fn<typeof fetch>().mockRejectedValue(new Error("network canary")),
        expectedResult: "unavailable",
        expectedReason: "network",
        expectedStatus: 0
      },
      {
        name: "http status",
        fetch: vi.fn<typeof fetch>().mockResolvedValue(new Response("body canary", { status: 503 })),
        expectedResult: "unavailable",
        expectedReason: "http_status",
        expectedStatus: 503
      },
      {
        name: "content type",
        fetch: vi.fn<typeof fetch>().mockResolvedValue(new Response("body canary", { status: 200 })),
        expectedResult: "invalid_response",
        expectedReason: "content_type",
        expectedStatus: 200
      },
      {
        name: "invalid JSON",
        fetch: vi.fn<typeof fetch>().mockResolvedValue(
          new Response("body canary", {
            status: 200,
            headers: { "content-type": "application/json" }
          })
        ),
        expectedResult: "invalid_response",
        expectedReason: "invalid_json",
        expectedStatus: 200
      },
      {
        name: "contract",
        fetch: vi.fn<typeof fetch>().mockResolvedValue(jsonResponse({ detail: "body canary" })),
        expectedResult: "invalid_response",
        expectedReason: "contract",
        expectedStatus: 200
      }
    ];

    for (const testCase of cases) {
      const events: WebHealthRequestCompleted[] = [];
      let now = 10;
      const diagnostics = createWebHealthDiagnostics({
        clock: () => now++,
        eventSink: (event) => events.push(event)
      });

      await adapterWith(testCase.fetch, 2_000, diagnostics).checkHealth();

      expect(events, testCase.name).toHaveLength(1);
      expect(events[0], testCase.name).toMatchObject({
        result: testCase.expectedResult,
        reason: testCase.expectedReason,
        status_code: testCase.expectedStatus,
        duration_ms: 1
      });
      expect(JSON.stringify(events), testCase.name).not.toContain("canary");
    }
  });

  it("keeps URL, response metadata, headers, and content canaries out of events", async () => {
    const events: WebHealthRequestCompleted[] = [];
    const diagnostics = createWebHealthDiagnostics({
      clock: () => 1,
      eventSink: (event) => events.push(event)
    });
    const response = new Response("response-body-canary", {
      status: 503,
      statusText: "response-status-canary",
      headers: { "x-response-canary": "response-header-canary" }
    });

    await adapterWith(
      vi.fn<typeof fetch>().mockResolvedValue(response),
      2_000,
      diagnostics
    ).checkHealth();

    const serialized = JSON.stringify(events);
    expect(events).toHaveLength(1);
    expect(serialized).not.toContain("127.0.0.1");
    expect(serialized).not.toContain("/health/live");
    expect(serialized).not.toContain("response-body-canary");
    expect(serialized).not.toContain("response-status-canary");
    expect(serialized).not.toContain("response-header-canary");
    expect(serialized).not.toContain("x-response-canary");
  });

  it("uses isolated IDs for concurrent health operations", async () => {
    const events: WebHealthRequestCompleted[] = [];
    const diagnostics = createWebHealthDiagnostics({
      clock: () => 5,
      eventSink: (event) => events.push(event)
    });
    const fetchImplementation = vi.fn<typeof fetch>().mockImplementation(
      async () => {
        await Promise.resolve();
        return jsonResponse({ status: "ok", detail: "" });
      }
    );
    const adapter = adapterWith(fetchImplementation, 2_000, diagnostics);

    await Promise.all(Array.from({ length: 10 }, () => adapter.checkHealth()));

    expect(events).toHaveLength(10);
    expect(new Set(events.map((event) => event.trace_id))).toHaveLength(10);
    expect(new Set(events.map((event) => event.span_id))).toHaveLength(10);
    const propagatedParents = fetchImplementation.mock.calls.map((call) => {
      const headers = call[1]?.headers as Record<string, string>;
      return headers.traceparent;
    });
    expect(new Set(propagatedParents)).toHaveLength(10);
    expect(
      new Set(propagatedParents.map((parent) => parent.split("-")[1]))
    ).toEqual(new Set(events.map((event) => event.trace_id)));
    expect(
      new Set(propagatedParents.map((parent) => parent.split("-")[2]))
    ).toEqual(new Set(events.map((event) => event.span_id)));
  });

  it.each([204, 302, 404, 500])(
    "classifies HTTP %s without returning response content",
    async (status) => {
      const fetchImplementation = vi
        .fn<typeof fetch>()
        .mockResolvedValue(
          new Response(status === 204 ? null : "sensitive", { status })
        );

      await expect(adapterWith(fetchImplementation).checkHealth()).resolves.toEqual({
        kind: "unavailable",
        reason: "http_status"
      });
    }
  );

  it("classifies a network or redirect rejection without exposing the exception", async () => {
    const fetchImplementation = vi
      .fn<typeof fetch>()
      .mockRejectedValue(new Error("sensitive network detail"));

    await expect(adapterWith(fetchImplementation).checkHealth()).resolves.toEqual({
      kind: "unavailable",
      reason: "network"
    });
  });

  it("aborts and classifies a request that exceeds the bounded timeout", async () => {
    vi.useFakeTimers();
    const events: WebHealthRequestCompleted[] = [];
    const diagnostics = createWebHealthDiagnostics({
      clock: () => performance.now(),
      eventSink: (event) => events.push(event)
    });
    const fetchImplementation = vi.fn<typeof fetch>().mockImplementation(
      (_input, options) =>
        new Promise<Response>((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => {
            reject(new DOMException("sensitive abort detail", "AbortError"));
          });
        })
    );

    const result = adapterWith(fetchImplementation, 25, diagnostics).checkHealth();
    await vi.advanceTimersByTimeAsync(25);

    await expect(result).resolves.toEqual({
      kind: "unavailable",
      reason: "timeout"
    });
    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      outcome: "error",
      result: "unavailable",
      reason: "timeout",
      status_code: 0,
      duration_ms: 25
    });
    expect(vi.getTimerCount()).toBe(0);
  });

  it("rethrows unexpected adapter failures after one confidential completion", async () => {
    const failure = new Error("unexpected-response-canary");
    const response = jsonResponse({ status: "ok" });
    vi.spyOn(response.headers, "get").mockImplementation(() => {
      throw failure;
    });
    const events: WebHealthRequestCompleted[] = [];
    let now = 40;
    const diagnostics = createWebHealthDiagnostics({
      clock: () => now++,
      eventSink: (event) => events.push(event)
    });

    await expect(
      adapterWith(
        vi.fn<typeof fetch>().mockResolvedValue(response),
        2_000,
        diagnostics
      ).checkHealth()
    ).rejects.toBe(failure);

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({
      outcome: "error",
      result: "exception",
      reason: "application_error",
      status_code: 200
    });
    expect(JSON.stringify(events)).not.toContain("unexpected-response-canary");
  });

  it("keeps the health operation unchanged when diagnostics setup fails", async () => {
    const diagnostics: WebHealthDiagnostics = {
      startAttempt(): undefined {
        throw new Error("diagnostic setup canary");
      }
    };
    const fetchImplementation = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse({ status: "ok", detail: "" }));

    await expect(
      adapterWith(fetchImplementation, 2_000, diagnostics).checkHealth()
    ).resolves.toEqual({ kind: "available" });
    expect(fetchImplementation.mock.calls[0]?.[1]?.headers).toEqual({
      Accept: "application/json"
    });
  });

  it.each(["invalid", "throwing getter"])(
    "omits a %s diagnostic header without changing health behavior",
    async (variant) => {
      const complete = vi.fn();
      const diagnostics: WebHealthDiagnostics = {
        startAttempt: () =>
          variant === "invalid"
            ? {
                traceparent:
                  "00-00000000000000000000000000000000-0000000000000000-01",
                complete
              }
            : {
                get traceparent(): string {
                  throw new Error("traceparent getter canary");
                },
                complete
              }
      };
      const fetchImplementation = vi
        .fn<typeof fetch>()
        .mockResolvedValue(jsonResponse({ status: "ok", detail: "" }));

      await expect(
        adapterWith(fetchImplementation, 2_000, diagnostics).checkHealth()
      ).resolves.toEqual({ kind: "available" });
      expect(fetchImplementation.mock.calls[0]?.[1]?.headers).toEqual({
        Accept: "application/json"
      });
      expect(complete).toHaveBeenCalledTimes(1);
    }
  );

  it("keeps the health result unchanged when diagnostics completion fails", async () => {
    const diagnostics: WebHealthDiagnostics = {
      startAttempt: () => ({
        traceparent:
          "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
        complete(): void {
          throw new Error("diagnostic completion canary");
        }
      })
    };

    await expect(
      adapterWith(
        vi
          .fn<typeof fetch>()
          .mockResolvedValue(jsonResponse({ status: "ok", detail: "" })),
        2_000,
        diagnostics
      ).checkHealth()
    ).resolves.toEqual({ kind: "available" });
  });

  it.each([0, -1, 1.5, Number.NaN, 2_147_483_648])(
    "rejects invalid timeout %s",
    (timeoutMs) => {
      expect(() => adapterWith(vi.fn<typeof fetch>(), timeoutMs)).toThrow(
        "Health adapter timeout must be a positive integer."
      );
    }
  );

  it.each([undefined, "text/plain", "application/problem+json"])(
    "rejects wrong media type %s before parsing a body",
    async (contentType) => {
      const headers = contentType ? { "content-type": contentType } : undefined;
      const response = new Response('{"status":"ok","detail":"secret"}', {
        status: 200,
        headers
      });
      const jsonSpy = vi.spyOn(response, "json");
      const fetchImplementation = vi
        .fn<typeof fetch>()
        .mockResolvedValue(response);

      await expect(adapterWith(fetchImplementation).checkHealth()).resolves.toEqual({
        kind: "invalid-response",
        reason: "content_type"
      });
      expect(jsonSpy).not.toHaveBeenCalled();
    }
  );

  it("rejects malformed JSON without returning the raw body", async () => {
    const fetchImplementation = vi.fn<typeof fetch>().mockResolvedValue(
      new Response("sensitive malformed body", {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );

    await expect(adapterWith(fetchImplementation).checkHealth()).resolves.toEqual({
      kind: "invalid-response",
      reason: "invalid_json"
    });
  });

  it.each([
    {},
    { status: "ready", detail: "not the contract" },
    { status: "ok", detail: 7 }
  ])("rejects schema-invalid JSON without returning it", async (body) => {
    const fetchImplementation = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(body));

    await expect(adapterWith(fetchImplementation).checkHealth()).resolves.toEqual({
      kind: "invalid-response",
      reason: "contract"
    });
  });
});
