"""Confidential W3C diagnostic context for the API liveness operation."""

import asyncio
import time
from typing import Final

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace import SpanKind
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ai_learning_platform_api.diagnostics import (
    ApiHealthRequestCompleted,
    Clock,
    DiagnosticEventSink,
    DiagnosticOutcome,
    DiagnosticReason,
    DiagnosticsRuntime,
    ParentContextClassification,
)

_TRACEPARENT_HEADER: Final = b"traceparent"
_TRACEPARENT_LOCAL_BYTE_LIMIT: Final = 512
_HEALTH_PATH: Final = "/health/live"
_HEALTH_METHOD: Final = "GET"
_SPAN_NAME: Final = "GET /health/live"
_INTERNAL_ERROR_BODY: Final = b'{"detail":"internal server error"}'


def _extract_parent_context(
    scope: Scope,
    runtime: DiagnosticsRuntime,
) -> tuple[Context, ParentContextClassification]:
    values = [
        value for name, value in scope.get("headers", []) if name.lower() == _TRACEPARENT_HEADER
    ]
    if not values:
        return Context(), ParentContextClassification.ABSENT
    if len(values) != 1 or len(values[0]) > _TRACEPARENT_LOCAL_BYTE_LIMIT:
        return Context(), ParentContextClassification.INVALID

    try:
        value = values[0].decode("ascii")
    except UnicodeDecodeError:
        return Context(), ParentContextClassification.INVALID

    if value != value.strip():
        return Context(), ParentContextClassification.INVALID

    try:
        extracted = runtime.propagator.extract(
            carrier={"traceparent": value},
            context=Context(),
        )
    except Exception:
        return Context(), ParentContextClassification.INVALID

    span_context = trace.get_current_span(extracted).get_span_context()
    if not span_context.is_valid or not span_context.is_remote:
        return Context(), ParentContextClassification.INVALID
    return extracted, ParentContextClassification.VALID


class ApiHealthDiagnosticsMiddleware:
    """Own exactly one span and one safe completion event for API liveness GETs."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        runtime: DiagnosticsRuntime,
        event_sink: DiagnosticEventSink,
        clock_ns: Clock = time.perf_counter_ns,
    ) -> None:
        self._app = app
        self._runtime = runtime
        self._event_sink = event_sink
        self._clock_ns = clock_ns

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._owns(scope):
            await self._app(scope, receive, send)
            return

        parent, classification = _extract_parent_context(scope, self._runtime)
        try:
            started_ns = self._clock_ns()
        except Exception:
            await self._app(scope, receive, send)
            return
        response_started = False
        status_code = 0

        async def capture_send(message: Message) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
            await send(message)

        downstream_entered = False
        try:
            with self._runtime.tracer.start_as_current_span(
                _SPAN_NAME,
                context=parent,
                kind=SpanKind.SERVER,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                downstream_entered = True
                span_context = span.get_span_context()
                try:
                    await self._app(scope, receive, capture_send)
                except asyncio.CancelledError:
                    self._safe_emit(
                        span_context.trace_id,
                        span_context.span_id,
                        classification,
                        DiagnosticOutcome.CANCELLED,
                        DiagnosticReason.CANCELLED,
                        status_code,
                        started_ns,
                    )
                    raise
                except Exception:
                    status_code = 500 if not response_started else status_code
                    self._safe_emit(
                        span_context.trace_id,
                        span_context.span_id,
                        classification,
                        DiagnosticOutcome.ERROR,
                        DiagnosticReason.APPLICATION_ERROR,
                        status_code,
                        started_ns,
                    )
                    if response_started:
                        raise
                    await self._send_internal_error(send)
                else:
                    successful = 200 <= status_code < 400
                    self._safe_emit(
                        span_context.trace_id,
                        span_context.span_id,
                        classification,
                        DiagnosticOutcome.OK if successful else DiagnosticOutcome.ERROR,
                        DiagnosticReason.OK if successful else DiagnosticReason.APPLICATION_ERROR,
                        status_code,
                        started_ns,
                    )
        except Exception:
            if downstream_entered:
                raise
            await self._app(scope, receive, send)

    @staticmethod
    def _owns(scope: Scope) -> bool:
        return (
            scope["type"] == "http"
            and scope.get("method") == _HEALTH_METHOD
            and scope.get("path") == _HEALTH_PATH
        )

    async def _send_internal_error(self, send: Send) -> None:
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(_INTERNAL_ERROR_BODY)).encode("ascii")),
        ]
        await send({"type": "http.response.start", "status": 500, "headers": headers})
        await send({"type": "http.response.body", "body": _INTERNAL_ERROR_BODY})

    def _safe_emit(
        self,
        trace_id: int,
        span_id: int,
        parent_context: ParentContextClassification,
        outcome: DiagnosticOutcome,
        reason: DiagnosticReason,
        status_code: int,
        started_ns: int,
    ) -> None:
        try:
            duration_ms = max(0, (self._clock_ns() - started_ns) // 1_000_000)
            self._event_sink(
                ApiHealthRequestCompleted(
                    outcome=outcome,
                    reason=reason,
                    parent_context=parent_context,
                    trace_id=trace_id,
                    span_id=span_id,
                    status_code=status_code,
                    duration_ms=duration_ms,
                )
            )
        except Exception:
            return
