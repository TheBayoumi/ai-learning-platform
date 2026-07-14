import { afterEach, describe, expect, it, vi } from "vitest";

import { parseApiBaseUrl } from "../server/config/api-base";
import {
  createHealthAdapter,
  type FetchLike
} from "../server/health/health-adapter";

const API_BASE_URL = parseApiBaseUrl("http://127.0.0.1:8000");

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" }
  });
}

function adapterWith(fetchImplementation: FetchLike, timeoutMs = 2_000) {
  return createHealthAdapter({
    apiBaseUrl: API_BASE_URL,
    fetch: fetchImplementation,
    timeoutMs
  });
}

afterEach(() => {
  vi.useRealTimers();
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
      headers: { Accept: "application/json" },
      cache: "no-store",
      credentials: "omit",
      redirect: "error"
    });
    expect(options?.signal).toBeInstanceOf(AbortSignal);
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
    const fetchImplementation = vi.fn<typeof fetch>().mockImplementation(
      (_input, options) =>
        new Promise<Response>((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => {
            reject(new DOMException("sensitive abort detail", "AbortError"));
          });
        })
    );

    const result = adapterWith(fetchImplementation, 25).checkHealth();
    await vi.advanceTimersByTimeAsync(25);

    await expect(result).resolves.toEqual({
      kind: "unavailable",
      reason: "timeout"
    });
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
