"""Exporter-free diagnostic primitives with a fixed confidential schema."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Self

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.sampling import ALWAYS_ON, ParentBased
from opentelemetry.trace import Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

DIAGNOSTIC_LOGGER_NAME: Final = "ai_learning_platform_api.diagnostics"
DIAGNOSTIC_SCHEMA_VERSION: Final = 1
API_SERVICE_NAME: Final = "ai-learning-platform-api"
_MAX_TRACE_ID: Final = (1 << 128) - 1
_MAX_SPAN_ID: Final = (1 << 64) - 1


class DiagnosticOutcome(StrEnum):
    """Bounded completion classifications for the diagnostic health operation."""

    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


class DiagnosticReason(StrEnum):
    """Bounded reasons that never contain exception or request content."""

    OK = "ok"
    APPLICATION_ERROR = "application_error"
    CANCELLED = "cancelled"


class ParentContextClassification(StrEnum):
    """Result of validating the single supported inbound context field."""

    VALID = "valid"
    ABSENT = "absent"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class ApiHealthRequestCompleted:
    """The sole F02-01 request event, limited to validated low-cardinality fields."""

    outcome: DiagnosticOutcome
    reason: DiagnosticReason
    parent_context: ParentContextClassification
    trace_id: int
    span_id: int
    status_code: int
    duration_ms: int

    def __post_init__(self) -> None:
        if not 0 < self.trace_id <= _MAX_TRACE_ID:
            raise ValueError("trace_id must be a valid non-zero OpenTelemetry trace identifier")
        if not 0 < self.span_id <= _MAX_SPAN_ID:
            raise ValueError("span_id must be a valid non-zero OpenTelemetry span identifier")
        if self.status_code != 0 and not 100 <= self.status_code <= 599:
            raise ValueError("status_code must be zero or a valid HTTP status code")
        if self.duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")

    def to_payload(self) -> dict[str, object]:
        """Build the exact allowlisted JSON payload."""
        return {
            "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
            "event": "api.health.request.completed",
            "service": "api",
            "operation": "health_live",
            "outcome": self.outcome.value,
            "reason": self.reason.value,
            "parent_context": self.parent_context.value,
            "trace_id": trace.format_trace_id(self.trace_id),
            "span_id": trace.format_span_id(self.span_id),
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
        }


type DiagnosticEventSink = Callable[[ApiHealthRequestCompleted], None]


def emit_diagnostic_event(event: ApiHealthRequestCompleted) -> None:
    """Submit a validated event to the safe JSON formatter."""
    logging.getLogger(DIAGNOSTIC_LOGGER_NAME).info(
        "diagnostic event",
        extra={"diagnostic_event": event},
    )


class DiagnosticsRuntime:
    """Own an application-local provider without global state, egress, or persistence."""

    def __init__(
        self,
        provider: TracerProvider,
        tracer: Tracer,
        propagator: TraceContextTextMapPropagator,
    ) -> None:
        self.provider = provider
        self.tracer = tracer
        self.propagator = propagator

    @classmethod
    def create(cls) -> Self:
        """Create deterministic in-process instrumentation with no span processor."""
        provider = TracerProvider(
            sampler=ParentBased(ALWAYS_ON),
            resource=Resource({"service.name": API_SERVICE_NAME}),
            shutdown_on_exit=False,
        )
        return cls(
            provider=provider,
            tracer=provider.get_tracer("ai_learning_platform_api.health", "0.0.0"),
            propagator=TraceContextTextMapPropagator(),
        )

    def shutdown(self) -> None:
        """Release provider-owned resources during application lifespan shutdown."""
        self.provider.shutdown()


Clock = Callable[[], int]
