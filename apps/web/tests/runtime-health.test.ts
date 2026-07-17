import { afterEach, describe, expect, it, vi } from "vitest";

import {
  API_BASE_ENV_NAME,
  ApiBaseConfigurationError
} from "../server/config/api-base";
import type {
  HealthAdapter,
  HealthCheckResult
} from "../server/health/health-adapter";
import {
  LOCAL_API_HEALTH_TIMEOUT_MS,
  resolveRuntimeApiAvailability
} from "../server/health/runtime-health";

const originalApiBase = process.env[API_BASE_ENV_NAME];

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  if (originalApiBase === undefined) {
    delete process.env[API_BASE_ENV_NAME];
  } else {
    process.env[API_BASE_ENV_NAME] = originalApiBase;
  }
});

describe("runtime API availability", () => {
  it.each<readonly [HealthCheckResult, HealthCheckResult["kind"]]>([
    [{ kind: "available" }, "available"],
    [{ kind: "unavailable", reason: "timeout" }, "unavailable"],
    [{ kind: "unavailable", reason: "network" }, "unavailable"],
    [{ kind: "unavailable", reason: "http_status" }, "unavailable"],
    [
      { kind: "invalid-response", reason: "content_type" },
      "invalid-response"
    ],
    [
      { kind: "invalid-response", reason: "invalid_json" },
      "invalid-response"
    ],
    [{ kind: "invalid-response", reason: "contract" }, "invalid-response"]
  ])("maps only $expected.kind to presentation", async (result, expected) => {
    const adapter: HealthAdapter = {
      checkHealth: vi.fn().mockResolvedValue(result)
    };

    await expect(resolveRuntimeApiAvailability(adapter)).resolves.toBe(expected);
  });

  it("uses the configured origin and global server fetch", async () => {
    process.env[API_BASE_ENV_NAME] = "http://127.0.0.1:8000";
    const fetchImplementation = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", detail: "process is live" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      })
    );
    vi.stubGlobal("fetch", fetchImplementation);

    await expect(resolveRuntimeApiAvailability()).resolves.toBe("available");
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
    expect(fetchImplementation.mock.calls[0]?.[0]).toEqual(
      new URL("http://127.0.0.1:8000/health/live")
    );
  });

  it("applies the provisional 2,000 ms one-attempt deadline", async () => {
    vi.useFakeTimers();
    process.env[API_BASE_ENV_NAME] = "http://127.0.0.1:8000";
    const fetchImplementation = vi.fn<typeof fetch>().mockImplementation(
      (_input, options) =>
        new Promise<Response>((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => {
            reject(new DOMException("aborted", "AbortError"));
          });
        })
    );
    vi.stubGlobal("fetch", fetchImplementation);

    const result = resolveRuntimeApiAvailability();
    const signal = fetchImplementation.mock.calls[0]?.[1]?.signal;
    await vi.advanceTimersByTimeAsync(LOCAL_API_HEALTH_TIMEOUT_MS - 1);
    expect(signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);

    await expect(result).resolves.toBe("unavailable");
    expect(signal?.aborted).toBe(true);
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
  });

  it("propagates invalid configuration before fetch", async () => {
    process.env[API_BASE_ENV_NAME] = "https://public.example:443";
    const fetchImplementation = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchImplementation);

    await expect(resolveRuntimeApiAvailability()).rejects.toBeInstanceOf(
      ApiBaseConfigurationError
    );
    expect(fetchImplementation).not.toHaveBeenCalled();
  });

  it("propagates unexpected adapter failures", async () => {
    const failure = new Error("programming defect");
    const adapter: HealthAdapter = {
      checkHealth: vi.fn().mockRejectedValue(failure)
    };

    await expect(resolveRuntimeApiAvailability(adapter)).rejects.toBe(failure);
  });
});
