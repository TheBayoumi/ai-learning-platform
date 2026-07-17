import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import {
  diag,
  DiagLogLevel,
  propagation,
  trace,
  type Context,
  type DiagLogger,
  type TextMapPropagator,
  type TextMapSetter
} from "@opentelemetry/api";
import { parseTraceParent } from "@opentelemetry/core";
import { TracerProvider } from "@opentelemetry/sdk-trace";
import { describe, expect, it, vi } from "vitest";

import {
  createWebHealthDiagnostics,
  isCanonicalTraceparent,
  noOpWebHealthDiagnostics,
  WEB_HEALTH_DIAGNOSTIC_EVENT,
  type WebHealthRequestCompleted
} from "../server/diagnostics/health-diagnostics";

const testProvider = new TracerProvider({ spanProcessors: [] });
const testTracer = testProvider.getTracer("web-health-diagnostics-tests");

function createTestSpan() {
  return testTracer.startSpan("test span");
}

function throwingPropagator(): TextMapPropagator<Record<string, string>> {
  return {
    inject(): void {
      throw new Error("injection canary");
    },
    extract(context: Context): Context {
      return context;
    },
    fields(): string[] {
      return ["traceparent"];
    }
  };
}

function invalidPropagator(): TextMapPropagator<Record<string, string>> {
  return {
    inject(
      _context: Context,
      carrier: Record<string, string>,
      setter: TextMapSetter<Record<string, string>>
    ): void {
      setter.set(carrier, "traceparent", "invalid-propagation-canary");
    },
    extract(context: Context): Context {
      return context;
    },
    fields(): string[] {
      return ["traceparent"];
    }
  };
}

describe("server web health diagnostics", () => {
  it("falls back to one frozen no-op when default instrumentation setup fails", () => {
    const diagnostics = createWebHealthDiagnostics({
      instrumentationFactory(): never {
        throw new Error("default instrumentation canary");
      }
    });

    expect(diagnostics).toBe(noOpWebHealthDiagnostics);
    expect(Object.isFrozen(diagnostics)).toBe(true);
    expect(diagnostics.startAttempt()).toBeUndefined();
  });

  it("accepts only canonical validated version-00 trace parents", () => {
    expect(
      isCanonicalTraceparent(
        "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
      )
    ).toBe(true);
    expect(
      isCanonicalTraceparent(
        "00-00000000000000000000000000000000-0123456789abcdef-01"
      )
    ).toBe(false);
    expect(
      isCanonicalTraceparent(
        "00-0123456789abcdef0123456789abcdef-0000000000000000-01"
      )
    ).toBe(false);
    expect(
      isCanonicalTraceparent(
        "00-0123456789ABCDEF0123456789ABCDEF-0123456789abcdef-01"
      )
    ).toBe(false);
    expect(
      isCanonicalTraceparent(
        " 00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
      )
    ).toBe(false);
  });

  it("injects one canonical W3C parent and emits one exact frozen event", () => {
    const events: WebHealthRequestCompleted[] = [];
    let now = 100;
    const diagnostics = createWebHealthDiagnostics({
      clock: () => now,
      eventSink: (event) => events.push(event)
    });

    const attempt = diagnostics.startAttempt();
    expect(attempt).toBeDefined();
    const parsed = parseTraceParent(attempt?.traceparent ?? "");
    expect(attempt?.traceparent).toMatch(
      /^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/
    );

    now = 107.9;
    attempt?.complete({ result: "available", reason: "ok", statusCode: 200 });
    attempt?.complete({ result: "available", reason: "ok", statusCode: 200 });

    expect(events).toHaveLength(1);
    expect(Object.keys(events[0] ?? {})).toEqual([
      "schema_version",
      "event",
      "service",
      "operation",
      "outcome",
      "result",
      "reason",
      "trace_id",
      "span_id",
      "status_code",
      "duration_ms"
    ]);
    expect(events[0]).toEqual({
      schema_version: 1,
      event: WEB_HEALTH_DIAGNOSTIC_EVENT,
      service: "web",
      operation: "health_live",
      outcome: "ok",
      result: "available",
      reason: "ok",
      trace_id: parsed?.traceId,
      span_id: parsed?.spanId,
      status_code: 200,
      duration_ms: 7
    });
    expect(Object.isFrozen(events[0])).toBe(true);
  });

  it("ignores hostile ambient OpenTelemetry configuration without leaking it", () => {
    const diagnosticMessages: unknown[][] = [];
    const capture = (...args: unknown[]): void => {
      diagnosticMessages.push(args);
    };
    const logger: DiagLogger = {
      error: capture,
      warn: capture,
      info: capture,
      debug: capture,
      verbose: capture
    };
    vi.stubEnv("OTEL_SDK_DISABLED", "true");
    vi.stubEnv("OTEL_TRACES_SAMPLER", "always_off");
    vi.stubEnv("OTEL_SERVICE_NAME", "service-secret-canary");
    vi.stubEnv(
      "OTEL_RESOURCE_ATTRIBUTES",
      "private.attribute=resource-secret-canary"
    );
    diag.setLogger(logger, DiagLogLevel.ALL);

    try {
      const events: WebHealthRequestCompleted[] = [];
      const diagnostics = createWebHealthDiagnostics({
        clock: () => 1,
        eventSink: (event) => events.push(event)
      });
      const attempt = diagnostics.startAttempt();

      expect(attempt?.traceparent).toMatch(
        /^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/
      );
      attempt?.complete({ result: "available", reason: "ok", statusCode: 200 });

      expect(events).toHaveLength(1);
      const observableOutput = JSON.stringify({ diagnosticMessages, events });
      expect(observableOutput).not.toContain("service-secret-canary");
      expect(observableOutput).not.toContain("resource-secret-canary");
    } finally {
      diag.disable();
      vi.unstubAllEnvs();
    }
  });

  it("writes one compact newline-delimited JSON event to standard error", () => {
    const write = vi
      .spyOn(process.stderr, "write")
      .mockImplementation(() => true);
    let now = 20;
    const diagnostics = createWebHealthDiagnostics({ clock: () => now++ });

    diagnostics
      .startAttempt()
      ?.complete({ result: "available", reason: "ok", statusCode: 200 });

    expect(write).toHaveBeenCalledTimes(1);
    const line = String(write.mock.calls[0]?.[0]);
    expect(line.endsWith("\n")).toBe(true);
    expect(line.split("\n")).toHaveLength(2);
    expect(JSON.parse(line)).toMatchObject({
      event: WEB_HEALTH_DIAGNOSTIC_EVENT,
      outcome: "ok",
      result: "available",
      reason: "ok",
      status_code: 200,
      duration_ms: 1
    });
    write.mockRestore();
  });

  it("isolates unique roots across sequential and concurrent attempts", () => {
    const events: WebHealthRequestCompleted[] = [];
    const diagnostics = createWebHealthDiagnostics({
      clock: () => 10,
      eventSink: (event) => events.push(event)
    });

    const attempts = Array.from({ length: 12 }, () => diagnostics.startAttempt());
    const parents = attempts.map((attempt) => parseTraceParent(attempt?.traceparent ?? ""));

    expect(parents.every((parent) => parent !== null)).toBe(true);
    expect(new Set(parents.map((parent) => parent?.traceId))).toHaveLength(12);
    expect(new Set(parents.map((parent) => parent?.spanId))).toHaveLength(12);

    for (const attempt of attempts.reverse()) {
      attempt?.complete({ result: "available", reason: "ok", statusCode: 200 });
    }
    expect(events).toHaveLength(12);
    expect(new Set(events.map((event) => event.trace_id))).toHaveLength(12);
    expect(new Set(events.map((event) => event.span_id))).toHaveLength(12);
  });

  it("ends setup spans and emits nothing when clock or propagation setup fails", () => {
    for (const options of [
      { clock: () => { throw new Error("clock canary"); } },
      { propagator: throwingPropagator() },
      { propagator: invalidPropagator() }
    ]) {
      const span = createTestSpan();
      const end = vi.spyOn(span, "end");
      const eventSink = vi.fn();
      const diagnostics = createWebHealthDiagnostics({
        ...options,
        eventSink,
        startSpan: () => span
      });

      expect(diagnostics.startAttempt()).toBeUndefined();
      expect(end).toHaveBeenCalledTimes(1);
      expect(eventSink).not.toHaveBeenCalled();
      end.mockRestore();
    }
  });

  it("suppresses span-start failure", () => {
    const diagnostics = createWebHealthDiagnostics({
      startSpan(): never {
        throw new Error("span start canary");
      }
    });

    expect(diagnostics.startAttempt()).toBeUndefined();
  });

  it("ends a span whose identifiers are invalid", () => {
    const span = createTestSpan();
    vi.spyOn(span, "spanContext").mockReturnValue({
      traceId: "00000000000000000000000000000000",
      spanId: "0000000000000000",
      traceFlags: 1
    });
    const end = vi.spyOn(span, "end");
    const diagnostics = createWebHealthDiagnostics({ startSpan: () => span });

    expect(diagnostics.startAttempt()).toBeUndefined();
    expect(end).toHaveBeenCalledTimes(1);
  });

  it("ends once without an event when the completion clock fails", () => {
    const span = createTestSpan();
    const end = vi.spyOn(span, "end");
    const eventSink = vi.fn();
    let callCount = 0;
    const diagnostics = createWebHealthDiagnostics({
      clock(): number {
        callCount += 1;
        if (callCount === 1) {
          return 10;
        }
        throw new Error("completion clock canary");
      },
      eventSink,
      startSpan: () => span
    });

    const attempt = diagnostics.startAttempt();
    expect(() =>
      attempt?.complete({ result: "available", reason: "ok", statusCode: 200 })
    ).not.toThrow();
    attempt?.complete({ result: "available", reason: "ok", statusCode: 200 });

    expect(end).toHaveBeenCalledTimes(1);
    expect(eventSink).not.toHaveBeenCalled();
  });

  it("suppresses status, span-end, and sink failures after one bounded completion", () => {
    const span = createTestSpan();
    const setStatus = vi.spyOn(span, "setStatus").mockImplementation(() => {
      throw new Error("status canary");
    });
    const end = vi.spyOn(span, "end").mockImplementation(() => {
      throw new Error("end canary");
    });
    const eventSink = vi.fn(() => {
      throw new Error("sink canary");
    });
    let now = 1;
    const diagnostics = createWebHealthDiagnostics({
      clock: () => now++,
      eventSink,
      startSpan: () => span
    });

    const attempt = diagnostics.startAttempt();
    expect(() =>
      attempt?.complete({ result: "available", reason: "ok", statusCode: 200 })
    ).not.toThrow();
    attempt?.complete({ result: "available", reason: "ok", statusCode: 200 });

    expect(setStatus).toHaveBeenCalledTimes(1);
    expect(end).toHaveBeenCalledTimes(1);
    expect(eventSink).toHaveBeenCalledTimes(1);
  });

  it("rejects invalid completion combinations without leaking or throwing", () => {
    const events: WebHealthRequestCompleted[] = [];
    const diagnostics = createWebHealthDiagnostics({
      clock: () => 1,
      eventSink: (event) => events.push(event)
    });
    const attempt = diagnostics.startAttempt();

    expect(() =>
      attempt?.complete({
        result: "available",
        reason: "application_error",
        statusCode: 999
      })
    ).not.toThrow();
    expect(events).toEqual([]);
  });

  it("does not register global telemetry or add broad Next instrumentation", () => {
    const globalProvider = trace.getTracerProvider();
    const globalPropagationFields = propagation.fields();
    const diagnostics = createWebHealthDiagnostics({ eventSink: () => undefined });
    diagnostics
      .startAttempt()
      ?.complete({ result: "available", reason: "ok", statusCode: 200 });

    expect(trace.getTracerProvider()).toBe(globalProvider);
    expect(propagation.fields()).toEqual(globalPropagationFields);
    const source = readFileSync(
      resolve(process.cwd(), "server/diagnostics/health-diagnostics.ts"),
      "utf8"
    );
    expect(source).toContain("ROOT_CONTEXT");
    expect(source).toContain("new TracerProvider");
    expect(source).not.toContain("BasicTracerProvider");
    expect(source).not.toContain("process.env");
    expect(source).not.toContain("OTEL_");
    expect(source).not.toMatch(
      /setGlobalTracerProvider|setGlobalPropagator|setGlobalContextManager/
    );
    expect(existsSync(resolve(process.cwd(), "instrumentation.ts"))).toBe(false);
    expect(existsSync(resolve(process.cwd(), "src/instrumentation.ts"))).toBe(false);
  });
});
