import "server-only";

import {
  parseApiBaseUrl,
  type ApiBaseUrl
} from "../config/api-base";
import { isHealthResponse } from "../contracts/generated/health-response";
import {
  isCanonicalTraceparent,
  webHealthDiagnostics,
  type WebHealthDiagnosticAttempt,
  type WebHealthDiagnosticReason,
  type WebHealthDiagnosticResult,
  type WebHealthDiagnostics
} from "../diagnostics/health-diagnostics";

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
  readonly diagnostics?: WebHealthDiagnostics;
  readonly fetch: FetchLike;
  readonly timeoutMs: number;
}

interface ConfiguredHealthAdapterOptions {
  readonly configuredApiBaseUrl: string | undefined;
  readonly diagnostics?: WebHealthDiagnostics;
  readonly fetch: FetchLike;
  readonly timeoutMs: number;
}

interface StartedDiagnosticAttempt {
  readonly attempt: WebHealthDiagnosticAttempt | undefined;
  readonly traceparent: string | undefined;
}

function startDiagnosticAttempt(
  diagnostics: WebHealthDiagnostics
): StartedDiagnosticAttempt {
  let attempt: WebHealthDiagnosticAttempt | undefined;
  try {
    attempt = diagnostics.startAttempt();
  } catch {
    return { attempt: undefined, traceparent: undefined };
  }
  if (attempt === undefined) {
    return { attempt, traceparent: undefined };
  }

  try {
    const traceparent = attempt.traceparent;
    return {
      attempt,
      traceparent: isCanonicalTraceparent(traceparent)
        ? traceparent
        : undefined
    };
  } catch {
    return { attempt, traceparent: undefined };
  }
}

function completeDiagnosticAttempt(
  attempt: WebHealthDiagnosticAttempt | undefined,
  result: WebHealthDiagnosticResult,
  reason: WebHealthDiagnosticReason,
  statusCode: number
): void {
  try {
    attempt?.complete({ result, reason, statusCode });
  } catch {
    return;
  }
}

export function createHealthAdapter({
  apiBaseUrl,
  diagnostics = webHealthDiagnostics,
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
      const diagnosticAttempt = startDiagnosticAttempt(diagnostics);
      let diagnosticResult: WebHealthDiagnosticResult = "exception";
      let diagnosticReason: WebHealthDiagnosticReason = "application_error";
      let statusCode = 0;
      let timeout: ReturnType<typeof setTimeout> | undefined;

      try {
        const controller = new AbortController();
        timeout = setTimeout(() => controller.abort(), timeoutMs);
        let response: Response;
        try {
          response = await fetchImplementation(
            new URL("/health/live", apiBaseUrl),
            {
              method: "GET",
              headers:
                diagnosticAttempt.traceparent === undefined
                  ? { Accept: "application/json" }
                  : {
                      Accept: "application/json",
                      traceparent: diagnosticAttempt.traceparent
                    },
              cache: "no-store",
              credentials: "omit",
              redirect: "error",
              signal: controller.signal
            }
          );
        } catch {
          diagnosticResult = "unavailable";
          diagnosticReason = controller.signal.aborted ? "timeout" : "network";
          return { kind: "unavailable", reason: diagnosticReason };
        }

        statusCode = response.status;
        if (statusCode !== 200) {
          diagnosticResult = "unavailable";
          diagnosticReason = "http_status";
          return { kind: "unavailable", reason: "http_status" };
        }

        const mediaType = response.headers
          .get("content-type")
          ?.split(";", 1)[0]
          ?.trim()
          .toLowerCase();
        if (mediaType !== "application/json") {
          diagnosticResult = "invalid_response";
          diagnosticReason = "content_type";
          return { kind: "invalid-response", reason: "content_type" };
        }

        let body: unknown;
        try {
          body = await response.json();
        } catch {
          if (controller.signal.aborted) {
            diagnosticResult = "unavailable";
            diagnosticReason = "timeout";
            statusCode = 0;
            return { kind: "unavailable", reason: "timeout" };
          }
          diagnosticResult = "invalid_response";
          diagnosticReason = "invalid_json";
          return { kind: "invalid-response", reason: "invalid_json" };
        }

        if (!isHealthResponse(body)) {
          diagnosticResult = "invalid_response";
          diagnosticReason = "contract";
          return { kind: "invalid-response", reason: "contract" };
        }

        diagnosticResult = "available";
        diagnosticReason = "ok";
        return { kind: "available" };
      } finally {
        try {
          if (timeout !== undefined) {
            clearTimeout(timeout);
          }
        } finally {
          completeDiagnosticAttempt(
            diagnosticAttempt.attempt,
            diagnosticResult,
            diagnosticReason,
            statusCode
          );
        }
      }
    }
  };
}

export function createConfiguredHealthAdapter({
  configuredApiBaseUrl,
  diagnostics,
  fetch: fetchImplementation,
  timeoutMs
}: ConfiguredHealthAdapterOptions): HealthAdapter {
  const apiBaseUrl = parseApiBaseUrl(configuredApiBaseUrl);
  return createHealthAdapter({
    apiBaseUrl,
    diagnostics,
    fetch: fetchImplementation,
    timeoutMs
  });
}
