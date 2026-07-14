import "server-only";

import {
  parseApiBaseUrl,
  type ApiBaseUrl
} from "../config/api-base";
import { isHealthResponse } from "../contracts/generated/health-response";

export type HealthCheckResult =
  | { readonly kind: "available" }
  | {
      readonly kind: "unavailable";
      readonly reason: "timeout" | "network" | "http_status";
    }
  | {
      readonly kind: "invalid-response";
      readonly reason: "content_type" | "invalid_json" | "contract";
    };

export interface HealthAdapter {
  checkHealth(): Promise<HealthCheckResult>;
}

export type FetchLike = typeof fetch;

interface HealthAdapterOptions {
  readonly apiBaseUrl: ApiBaseUrl;
  readonly fetch: FetchLike;
  readonly timeoutMs: number;
}

interface ConfiguredHealthAdapterOptions {
  readonly configuredApiBaseUrl: string | undefined;
  readonly fetch: FetchLike;
  readonly timeoutMs: number;
}

export function createHealthAdapter({
  apiBaseUrl,
  fetch: fetchImplementation,
  timeoutMs
}: HealthAdapterOptions): HealthAdapter {
  if (
    !Number.isSafeInteger(timeoutMs) ||
    timeoutMs <= 0 ||
    timeoutMs > 2_147_483_647
  ) {
    throw new RangeError("Health adapter timeout must be a positive integer.");
  }

  return {
    async checkHealth(): Promise<HealthCheckResult> {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), timeoutMs);

      try {
        let response: Response;
        try {
          response = await fetchImplementation(new URL("/health/live", apiBaseUrl), {
            method: "GET",
            headers: { Accept: "application/json" },
            cache: "no-store",
            credentials: "omit",
            redirect: "error",
            signal: controller.signal
          });
        } catch {
          return controller.signal.aborted
            ? { kind: "unavailable", reason: "timeout" }
            : { kind: "unavailable", reason: "network" };
        }

        if (response.status !== 200) {
          return { kind: "unavailable", reason: "http_status" };
        }

        const mediaType = response.headers
          .get("content-type")
          ?.split(";", 1)[0]
          ?.trim()
          .toLowerCase();
        if (mediaType !== "application/json") {
          return { kind: "invalid-response", reason: "content_type" };
        }

        let body: unknown;
        try {
          body = await response.json();
        } catch {
          return controller.signal.aborted
            ? { kind: "unavailable", reason: "timeout" }
            : { kind: "invalid-response", reason: "invalid_json" };
        }

        if (!isHealthResponse(body)) {
          return { kind: "invalid-response", reason: "contract" };
        }

        return { kind: "available" };
      } finally {
        clearTimeout(timeout);
      }
    }
  };
}

export function createConfiguredHealthAdapter({
  configuredApiBaseUrl,
  fetch: fetchImplementation,
  timeoutMs
}: ConfiguredHealthAdapterOptions): HealthAdapter {
  const apiBaseUrl = parseApiBaseUrl(configuredApiBaseUrl);
  return createHealthAdapter({
    apiBaseUrl,
    fetch: fetchImplementation,
    timeoutMs
  });
}
