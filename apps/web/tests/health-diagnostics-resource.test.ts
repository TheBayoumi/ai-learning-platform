import { describe, expect, it } from "vitest";

import { parseApiBaseUrl } from "../server/config/api-base";
import {
  createWebHealthDiagnostics,
  type WebHealthDiagnostics,
  type WebHealthRequestCompleted
} from "../server/diagnostics/health-diagnostics";
import {
  createHealthAdapter,
  type FetchLike,
  type HealthAdapter
} from "../server/health/health-adapter";

const SAMPLE_SIZE = 500;
const WARMUP_SIZE = 20;
const API_BASE_URL = parseApiBaseUrl("http://127.0.0.1:8000");

function percentile(sortedValues: readonly number[], percentileValue: number) {
  const index = Math.max(
    0,
    Math.ceil((percentileValue / 100) * sortedValues.length) - 1
  );
  return sortedValues[index] ?? 0;
}

function summary(values: readonly number[]) {
  const sorted = [...values].sort((left, right) => left - right);
  return {
    p50_ms: Number(percentile(sorted, 50).toFixed(3)),
    p95_ms: Number(percentile(sorted, 95).toFixed(3)),
    max_ms: Number((sorted.at(-1) ?? 0).toFixed(3))
  };
}

async function measure(adapter: HealthAdapter): Promise<number> {
  const startedAt = performance.now();
  await adapter.checkHealth();
  return performance.now() - startedAt;
}

describe("F02-02 web diagnostic resource observation", () => {
  it("records a fixed adapter sample without defining a product budget", async () => {
    const events: WebHealthRequestCompleted[] = [];
    const instrumentedDiagnostics = createWebHealthDiagnostics({
      eventSink: (event) => events.push(event)
    });
    const uninstrumentedDiagnostics: WebHealthDiagnostics = {
      startAttempt: () => undefined
    };
    const fetchImplementation: FetchLike = async () =>
      new Response(JSON.stringify({ status: "ok", detail: "" }), {
        status: 200,
        headers: { "content-type": "application/json" }
      });
    const baseline = createHealthAdapter({
      apiBaseUrl: API_BASE_URL,
      diagnostics: uninstrumentedDiagnostics,
      fetch: fetchImplementation,
      timeoutMs: 2_000
    });
    const instrumented = createHealthAdapter({
      apiBaseUrl: API_BASE_URL,
      diagnostics: instrumentedDiagnostics,
      fetch: fetchImplementation,
      timeoutMs: 2_000
    });

    for (let index = 0; index < WARMUP_SIZE; index += 1) {
      await baseline.checkHealth();
      await instrumented.checkHealth();
    }
    events.length = 0;

    const baselineLatencies: number[] = [];
    const instrumentedLatencies: number[] = [];
    for (let index = 0; index < SAMPLE_SIZE; index += 1) {
      baselineLatencies.push(await measure(baseline));
      instrumentedLatencies.push(await measure(instrumented));
    }

    const eventBytes = events.map((event) =>
      new TextEncoder().encode(JSON.stringify(event)).byteLength
    );
    expect(events).toHaveLength(SAMPLE_SIZE);
    expect(events.every((event) => event.result === "available")).toBe(true);
    expect(eventBytes.every((size) => Number.isSafeInteger(size) && size > 0)).toBe(
      true
    );

    console.info(
      `[f02-02-resource] ${JSON.stringify({
        sample_size: SAMPLE_SIZE,
        warmup_size: WARMUP_SIZE,
        baseline: summary(baselineLatencies),
        instrumented: summary(instrumentedLatencies),
        events: events.length,
        event_bytes_min: Math.min(...eventBytes),
        event_bytes_max: Math.max(...eventBytes),
        event_bytes_total: eventBytes.reduce((total, size) => total + size, 0)
      })}`
    );
  });
});
