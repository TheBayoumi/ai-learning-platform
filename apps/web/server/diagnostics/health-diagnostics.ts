import "server-only";

import {
  isSpanContextValid,
  ROOT_CONTEXT,
  SpanKind,
  SpanStatusCode,
  trace,
  type Span,
  type TextMapPropagator,
  type TextMapSetter
} from "@opentelemetry/api";
import {
  parseTraceParent,
  W3CTraceContextPropagator
} from "@opentelemetry/core";
import {
  AlwaysOnSampler,
  ParentBasedSampler,
  TracerProvider
} from "@opentelemetry/sdk-trace";

export const WEB_HEALTH_DIAGNOSTIC_EVENT =
  "web.health.request.completed" as const;

export type WebHealthDiagnosticResult =
  | "available"
  | "unavailable"
  | "invalid_response"
  | "exception";

export type WebHealthDiagnosticReason =
  | "ok"
  | "timeout"
  | "network"
  | "http_status"
  | "content_type"
  | "invalid_json"
  | "contract"
  | "application_error";

export interface WebHealthRequestCompleted {
  readonly schema_version: 1;
  readonly event: typeof WEB_HEALTH_DIAGNOSTIC_EVENT;
  readonly service: "web";
  readonly operation: "health_live";
  readonly outcome: "ok" | "error";
  readonly result: WebHealthDiagnosticResult;
  readonly reason: WebHealthDiagnosticReason;
  readonly trace_id: string;
  readonly span_id: string;
  readonly status_code: number;
  readonly duration_ms: number;
}

export interface WebHealthDiagnosticCompletion {
  readonly result: WebHealthDiagnosticResult;
  readonly reason: WebHealthDiagnosticReason;
  readonly statusCode: number;
}

export interface WebHealthDiagnosticAttempt {
  readonly traceparent: string;
  complete(completion: WebHealthDiagnosticCompletion): void;
}

export interface WebHealthDiagnostics {
  startAttempt(): WebHealthDiagnosticAttempt | undefined;
}

type WebHealthEventSink = (event: WebHealthRequestCompleted) => void;
type MonotonicClock = () => number;
type SpanStarter = () => Span;
type StringCarrier = Record<string, string>;

interface InjectedTraceContext {
  readonly traceparent: string;
  readonly traceId: string;
  readonly spanId: string;
}

interface WebHealthInstrumentation {
  readonly propagator: TextMapPropagator<StringCarrier>;
  readonly startSpan: SpanStarter;
}

type InstrumentationFactory = () => WebHealthInstrumentation;

export interface WebHealthDiagnosticsOptions {
  readonly clock?: MonotonicClock;
  readonly instrumentationFactory?: InstrumentationFactory;
  readonly eventSink?: WebHealthEventSink;
  readonly propagator?: TextMapPropagator<StringCarrier>;
  readonly startSpan?: SpanStarter;
}

const STRING_CARRIER_SETTER: TextMapSetter<StringCarrier> = Object.freeze({
  set(carrier: StringCarrier, key: string, value: string): void {
    carrier[key] = value;
  }
});

function monotonicNow(): number {
  return globalThis.performance.now();
}

function writeEventToStandardError(event: WebHealthRequestCompleted): void {
  process.stderr.write(`${JSON.stringify(event)}\n`);
}

function isSafeIntegerStatus(statusCode: number): boolean {
  return (
    Number.isSafeInteger(statusCode) &&
    (statusCode === 0 || (statusCode >= 100 && statusCode <= 599))
  );
}

function hasValidCompletionCombination(
  result: WebHealthDiagnosticResult,
  reason: WebHealthDiagnosticReason,
  statusCode: number
): boolean {
  switch (result) {
    case "available":
      return reason === "ok" && statusCode === 200;
    case "unavailable":
      if (reason === "timeout" || reason === "network") {
        return statusCode === 0;
      }
      return reason === "http_status" && statusCode !== 0 && statusCode !== 200;
    case "invalid_response":
      return (
        statusCode === 200 &&
        (reason === "content_type" ||
          reason === "invalid_json" ||
          reason === "contract")
      );
    case "exception":
      return reason === "application_error";
  }
}

function createCompletionEvent(
  completion: WebHealthDiagnosticCompletion,
  traceId: string,
  spanId: string,
  durationMs: number
): WebHealthRequestCompleted {
  if (
    !isSafeIntegerStatus(completion.statusCode) ||
    !Number.isSafeInteger(durationMs) ||
    durationMs < 0 ||
    !hasValidCompletionCombination(
      completion.result,
      completion.reason,
      completion.statusCode
    )
  ) {
    throw new TypeError("Invalid bounded web health diagnostic completion.");
  }

  return Object.freeze({
    schema_version: 1,
    event: WEB_HEALTH_DIAGNOSTIC_EVENT,
    service: "web",
    operation: "health_live",
    outcome: completion.result === "available" ? "ok" : "error",
    result: completion.result,
    reason: completion.reason,
    trace_id: traceId,
    span_id: spanId,
    status_code: completion.statusCode,
    duration_ms: durationMs
  });
}

export function isCanonicalTraceparent(value: string): boolean {
  const parsed = parseTraceParent(value);
  if (parsed === null) {
    return false;
  }
  const canonical = `00-${parsed.traceId}-${parsed.spanId}-${parsed.traceFlags
    .toString(16)
    .padStart(2, "0")}`;
  return value === canonical;
}

function injectCanonicalTraceparent(
  span: Span,
  propagator: TextMapPropagator<StringCarrier>
): InjectedTraceContext | undefined {
  const spanContext = span.spanContext();
  if (
    !isSpanContextValid(spanContext) ||
    spanContext.traceId !== spanContext.traceId.toLowerCase() ||
    spanContext.spanId !== spanContext.spanId.toLowerCase()
  ) {
    return undefined;
  }

  const carrier = Object.create(null) as StringCarrier;
  propagator.inject(
    trace.setSpan(ROOT_CONTEXT, span),
    carrier,
    STRING_CARRIER_SETTER
  );
  const traceparent = carrier.traceparent;
  const parsed =
    typeof traceparent === "string" && isCanonicalTraceparent(traceparent)
      ? parseTraceParent(traceparent)
      : null;
  const expectedFlags = (spanContext.traceFlags & 0xff)
    .toString(16)
    .padStart(2, "0");
  if (
    parsed !== null &&
    parsed.traceId === spanContext.traceId &&
    parsed.spanId === spanContext.spanId &&
    parsed.traceFlags.toString(16).padStart(2, "0") === expectedFlags
  ) {
    return {
      traceparent,
      traceId: spanContext.traceId,
      spanId: spanContext.spanId
    };
  }
  return undefined;
}

function safeEnd(span: Span): void {
  try {
    span.end();
  } catch {
    return;
  }
}

export const noOpWebHealthDiagnostics: WebHealthDiagnostics = Object.freeze({
  startAttempt: () => undefined
});

function createDefaultInstrumentation(): WebHealthInstrumentation {
  const provider = new TracerProvider({
    sampler: new ParentBasedSampler({ root: new AlwaysOnSampler() }),
    spanProcessors: []
  });
  const tracer = provider.getTracer("ai-learning-platform-web.health", "0.0.0");
  const propagator = new W3CTraceContextPropagator();
  return Object.freeze({
    propagator,
    startSpan: () =>
      tracer.startSpan(
        "GET /health/live",
        { kind: SpanKind.CLIENT },
        ROOT_CONTEXT
      )
  });
}

export function createWebHealthDiagnostics(
  options: WebHealthDiagnosticsOptions = {}
): WebHealthDiagnostics {
  const clock = options.clock ?? monotonicNow;
  const eventSink = options.eventSink ?? writeEventToStandardError;
  let propagator = options.propagator;
  let startSpan = options.startSpan;
  if (propagator === undefined || startSpan === undefined) {
    let instrumentation: WebHealthInstrumentation;
    try {
      instrumentation = (
        options.instrumentationFactory ?? createDefaultInstrumentation
      )();
      propagator ??= instrumentation.propagator;
      startSpan ??= instrumentation.startSpan;
    } catch {
      return noOpWebHealthDiagnostics;
    }
  }

  return Object.freeze({
    startAttempt(): WebHealthDiagnosticAttempt | undefined {
      let span: Span;
      try {
        span = startSpan();
      } catch {
        return undefined;
      }

      let startedAt: number;
      let injected: InjectedTraceContext | undefined;
      try {
        startedAt = clock();
        injected = injectCanonicalTraceparent(span, propagator);
      } catch {
        safeEnd(span);
        return undefined;
      }
      if (!Number.isFinite(startedAt) || injected === undefined) {
        safeEnd(span);
        return undefined;
      }

      const { traceparent, traceId, spanId } = injected;
      let completed = false;
      return Object.freeze({
        traceparent,
        complete(completion: WebHealthDiagnosticCompletion): void {
          if (completed) {
            return;
          }
          completed = true;

          let event: WebHealthRequestCompleted | undefined;
          try {
            const elapsed = clock() - startedAt;
            const durationMs = Math.max(0, Math.trunc(elapsed));
            event = createCompletionEvent(
              completion,
              traceId,
              spanId,
              durationMs
            );
          } catch {
            event = undefined;
          }

          try {
            span.setStatus({
              code:
                completion.result === "available"
                  ? SpanStatusCode.OK
                  : SpanStatusCode.ERROR
            });
          } catch {
            // Span status is diagnostic-only and cannot affect health behavior.
          }
          safeEnd(span);

          if (event !== undefined) {
            try {
              eventSink(event);
            } catch {
              return;
            }
          }
        }
      });
    }
  });
}

export const webHealthDiagnostics = createWebHealthDiagnostics();
