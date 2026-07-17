import "server-only";

import { readApiBaseUrl } from "../config/api-base";
import {
  createHealthAdapter,
  type HealthAdapter,
  type HealthCheckResult
} from "./health-adapter";

// Provisional local UI safety bound: one attempt, no retry. This is not an SLA
// or a measured performance budget.
export const LOCAL_API_HEALTH_TIMEOUT_MS = 2_000;

export type ApiAvailability = HealthCheckResult["kind"];

function createRuntimeHealthAdapter(): HealthAdapter {
  return createHealthAdapter({
    apiBaseUrl: readApiBaseUrl(),
    fetch: globalThis.fetch,
    timeoutMs: LOCAL_API_HEALTH_TIMEOUT_MS
  });
}

export async function resolveRuntimeApiAvailability(
  adapter: HealthAdapter = createRuntimeHealthAdapter()
): Promise<ApiAvailability> {
  const result = await adapter.checkHealth();
  return result.kind;
}
