import asyncio
import json
import logging
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.trace import Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ai_learning_platform_api.app import create_app
from ai_learning_platform_api.diagnostics import (
    ApiHealthRequestCompleted,
    DiagnosticOutcome,
    DiagnosticReason,
    DiagnosticsRuntime,
    ParentContextClassification,
    emit_diagnostic_event,
)
from ai_learning_platform_api.logging import configure_logging
from ai_learning_platform_api.settings import Settings
from ai_learning_platform_api.transport.http.diagnostics import ApiHealthDiagnosticsMiddleware

_TRACE_ID = "0123456789abcdef0123456789abcdef"
_SECOND_TRACE_ID = "1123456789abcdef0123456789abcdef"
_PARENT_ID = "0123456789abcdef"
_VALID_TRACEPARENT = f"00-{_TRACE_ID}-{_PARENT_ID}-01".encode()
_CANARY = "CONFIDENTIAL-CANARY-42"


@pytest.fixture
def diagnostics_runtime() -> Iterator[DiagnosticsRuntime]:
    runtime = DiagnosticsRuntime.create()
    try:
        yield runtime
    finally:
        runtime.shutdown()


def _create_test_app(
    runtime: DiagnosticsRuntime,
    events: list[ApiHealthRequestCompleted],
) -> FastAPI:
    return create_app(
        Settings(environment="test", log_level="INFO"),
        diagnostics_runtime=runtime,
        diagnostic_event_sink=events.append,
    )


async def _invoke(
    app: ASGIApp,
    *,
    path: str = "/health/live",
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    query: bytes = b"",
    body: bytes = b"",
) -> list[Message]:
    messages: list[Message] = []
    request_sent = False

    async def receive() -> Message:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: Message) -> None:
        messages.append(message)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query,
        "root_path": "",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "state": {},
    }
    await app(scope, cast(Receive, receive), cast(Send, send))
    return messages


def _status(messages: list[Message]) -> int:
    return int(
        next(message["status"] for message in messages if message["type"] == "http.response.start")
    )


def _body(messages: list[Message]) -> bytes:
    return b"".join(
        message.get("body", b"") for message in messages if message["type"] == "http.response.body"
    )


def test_valid_remote_parent_is_preserved_without_echo(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)

    messages = asyncio.run(_invoke(app, headers=[(b"traceparent", _VALID_TRACEPARENT)]))

    assert _status(messages) == 200
    assert len(events) == 1
    event = events[0]
    assert event.parent_context is ParentContextClassification.VALID
    assert event.trace_id == int(_TRACE_ID, 16)
    assert event.span_id != int(_PARENT_ID, 16)
    response_headers = next(
        message["headers"] for message in messages if message["type"] == "http.response.start"
    )
    assert all(name.lower() != b"traceparent" for name, _ in response_headers)


@pytest.mark.parametrize(
    "value",
    [
        b"",
        b" " + _VALID_TRACEPARENT,
        _VALID_TRACEPARENT + b" ",
        _VALID_TRACEPARENT.upper(),
        b"ff-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
        b"00-00000000000000000000000000000000-0123456789abcdef-01",
        b"00-0123456789abcdef0123456789abcdef-0000000000000000-01",
        b"00-0123456789abcdef0123456789abcdef-0123456789abcdef-0",
        b"00-0123456789abcdef0123456789abcdef-0123456789abcdef-0g",
        b"00-0123456789abcdef0123456789abcdef-0123456789abcdeg-01",
        b"00-0123456789abcdef0123456789abcdef-0123456789abcdef-01-extra",
        b"\xff",
        b"a" * 513,
    ],
)
def test_hostile_traceparent_values_create_isolated_safe_roots(
    diagnostics_runtime: DiagnosticsRuntime,
    value: bytes,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)

    messages = asyncio.run(_invoke(app, headers=[(b"traceparent", value)]))

    assert _status(messages) == 200
    assert len(events) == 1
    assert events[0].parent_context is ParentContextClassification.INVALID
    assert events[0].trace_id != int(_TRACE_ID, 16)


@pytest.mark.parametrize(
    "value",
    [
        b"00-0123456789abcdef0123456789abcdef-0123456789abcdef-02",
        b"01-0123456789abcdef0123456789abcdef-0123456789abcdef-01-extra",
    ],
)
def test_reserved_flags_and_future_versions_are_delegated_to_official_propagator(
    diagnostics_runtime: DiagnosticsRuntime,
    value: bytes,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)

    messages = asyncio.run(_invoke(app, headers=[(b"traceparent", value)]))

    assert _status(messages) == 200
    assert events[0].parent_context is ParentContextClassification.VALID
    assert events[0].trace_id == int(_TRACE_ID, 16)


def test_duplicate_traceparent_is_invalid_and_tracestate_is_ignored(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    duplicate_events: list[ApiHealthRequestCompleted] = []
    duplicate_app = _create_test_app(diagnostics_runtime, duplicate_events)
    duplicate_headers = [
        (b"traceparent", _VALID_TRACEPARENT),
        (b"TraceParent", _VALID_TRACEPARENT),
    ]

    messages = asyncio.run(_invoke(duplicate_app, headers=duplicate_headers))

    assert _status(messages) == 200
    assert duplicate_events[0].parent_context is ParentContextClassification.INVALID

    valid_events: list[ApiHealthRequestCompleted] = []
    valid_app = _create_test_app(diagnostics_runtime, valid_events)
    hostile_metadata = [
        (b"traceparent", _VALID_TRACEPARENT),
        (b"tracestate", _CANARY.encode()),
        (b"baggage", _CANARY.encode()),
        (b"x-canary", _CANARY.encode()),
    ]

    asyncio.run(
        _invoke(
            valid_app,
            headers=hostile_metadata,
            query=f"secret={_CANARY}".encode(),
            body=_CANARY.encode(),
        )
    )

    payload = json.dumps(valid_events[0].to_payload())
    assert valid_events[0].parent_context is ParentContextClassification.VALID
    assert _CANARY not in payload


def test_absent_context_does_not_inherit_outer_context_and_is_restored(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)

    with diagnostics_runtime.tracer.start_as_current_span("outer") as outer:
        outer_context = outer.get_span_context()
        messages = asyncio.run(_invoke(app))
        assert trace.get_current_span() is outer

    assert _status(messages) == 200
    assert events[0].parent_context is ParentContextClassification.ABSENT
    assert events[0].trace_id != outer_context.trace_id
    assert not trace.get_current_span().get_span_context().is_valid


def test_concurrent_requests_keep_trace_and_span_context_isolated(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)
    second_parent = f"00-{_SECOND_TRACE_ID}-{_PARENT_ID}-01".encode()

    async def run_concurrently() -> None:
        await asyncio.gather(
            _invoke(app, headers=[(b"traceparent", _VALID_TRACEPARENT)]),
            _invoke(app, headers=[(b"traceparent", second_parent)]),
            _invoke(app),
        )

    asyncio.run(run_concurrently())

    assert len(events) == 3
    valid_trace_ids = {
        event.trace_id
        for event in events
        if event.parent_context is ParentContextClassification.VALID
    }
    assert valid_trace_ids == {int(_TRACE_ID, 16), int(_SECOND_TRACE_ID, 16)}
    assert len({event.span_id for event in events}) == 3
    assert len({event.trace_id for event in events}) == 3
    assert not trace.get_current_span().get_span_context().is_valid


@pytest.mark.parametrize(
    ("path", "method"),
    [
        ("/health/ready", "GET"),
        ("/health/live", "POST"),
        ("/health/live", "HEAD"),
        ("/health/live/", "GET"),
        ("/missing", "GET"),
        ("/openapi.json", "GET"),
    ],
)
def test_unowned_routes_and_methods_emit_no_diagnostic_event(
    diagnostics_runtime: DiagnosticsRuntime,
    path: str,
    method: str,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)

    asyncio.run(_invoke(app, path=path, method=method))

    assert events == []


def test_query_does_not_change_exactly_one_owned_completion_event(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)

    messages = asyncio.run(_invoke(app, query=b"ignored=true"))

    assert _status(messages) == 200
    assert len(events) == 1
    assert events[0].outcome is DiagnosticOutcome.OK
    assert events[0].reason is DiagnosticReason.OK
    assert events[0].status_code == 200


def test_downstream_exception_before_response_returns_fixed_safe_error(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []

    async def failing_app(_: Scope, __: Receive, ___: Send) -> None:
        raise RuntimeError(_CANARY)

    middleware = ApiHealthDiagnosticsMiddleware(
        cast(ASGIApp, failing_app),
        runtime=diagnostics_runtime,
        event_sink=events.append,
    )

    with diagnostics_runtime.tracer.start_as_current_span("outer") as outer:
        messages = asyncio.run(_invoke(middleware))
        assert trace.get_current_span() is outer

    assert _status(messages) == 500
    assert _body(messages) == b'{"detail":"internal server error"}'
    assert len(events) == 1
    assert events[0].outcome is DiagnosticOutcome.ERROR
    assert events[0].reason is DiagnosticReason.APPLICATION_ERROR
    assert events[0].status_code == 500
    assert _CANARY not in json.dumps(events[0].to_payload())


def test_downstream_exception_after_response_start_is_re_raised_safely(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []

    async def late_failure(_: Scope, __: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 204, "headers": []})
        raise RuntimeError(_CANARY)

    middleware = ApiHealthDiagnosticsMiddleware(
        cast(ASGIApp, late_failure),
        runtime=diagnostics_runtime,
        event_sink=events.append,
    )

    with diagnostics_runtime.tracer.start_as_current_span("outer") as outer:
        with pytest.raises(RuntimeError, match=_CANARY):
            asyncio.run(_invoke(middleware))
        assert trace.get_current_span() is outer

    assert len(events) == 1
    assert events[0].outcome is DiagnosticOutcome.ERROR
    assert events[0].status_code == 204


def test_downstream_cancellation_is_recorded_once_and_propagated(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []

    async def cancelled(_: Scope, __: Receive, ___: Send) -> None:
        raise asyncio.CancelledError

    middleware = ApiHealthDiagnosticsMiddleware(
        cast(ASGIApp, cancelled),
        runtime=diagnostics_runtime,
        event_sink=events.append,
    )

    with diagnostics_runtime.tracer.start_as_current_span("outer") as outer:
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(_invoke(middleware))
        assert trace.get_current_span() is outer

    assert len(events) == 1
    assert events[0].outcome is DiagnosticOutcome.CANCELLED
    assert events[0].reason is DiagnosticReason.CANCELLED
    assert events[0].status_code == 0


def test_non_success_response_is_classified_without_raw_content(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    events: list[ApiHealthRequestCompleted] = []

    async def unavailable(_: Scope, __: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 503, "headers": []})
        await send({"type": "http.response.body", "body": _CANARY.encode()})

    middleware = ApiHealthDiagnosticsMiddleware(
        cast(ASGIApp, unavailable),
        runtime=diagnostics_runtime,
        event_sink=events.append,
        clock_ns=iter([1_000_000, 3_500_000]).__next__,
    )

    messages = asyncio.run(_invoke(middleware))

    assert _status(messages) == 503
    assert _body(messages) == _CANARY.encode()
    assert events[0].outcome is DiagnosticOutcome.ERROR
    assert events[0].reason is DiagnosticReason.APPLICATION_ERROR
    assert events[0].duration_ms == 2
    assert _CANARY not in json.dumps(events[0].to_payload())


def test_event_sink_failure_cannot_change_health_response(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    def failing_sink(_: ApiHealthRequestCompleted) -> None:
        raise RuntimeError(_CANARY)

    app = create_app(
        Settings(environment="test", log_level="INFO"),
        diagnostics_runtime=diagnostics_runtime,
        diagnostic_event_sink=failing_sink,
    )

    messages = asyncio.run(_invoke(app))

    assert _status(messages) == 200
    assert json.loads(_body(messages)) == {"status": "ok", "detail": "process is live"}


@pytest.mark.parametrize("failing_call", [1, 2])
def test_clock_failure_cannot_change_health_response(
    diagnostics_runtime: DiagnosticsRuntime,
    failing_call: int,
) -> None:
    events: list[ApiHealthRequestCompleted] = []
    calls = 0

    def clock() -> int:
        nonlocal calls
        calls += 1
        if calls == failing_call:
            raise RuntimeError(_CANARY)
        return calls * 1_000_000

    async def healthy(_: Scope, __: Receive, send: Send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"healthy"})

    middleware = ApiHealthDiagnosticsMiddleware(
        cast(ASGIApp, healthy),
        runtime=diagnostics_runtime,
        event_sink=events.append,
        clock_ns=clock,
    )

    messages = asyncio.run(_invoke(middleware))

    assert _status(messages) == 200
    assert _body(messages) == b"healthy"
    assert events == []


def test_propagator_failure_creates_invalid_safe_root(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    class FailingPropagator:
        def extract(self, *_: object, **__: object) -> ContextNever:
            raise RuntimeError(_CANARY)

    events: list[ApiHealthRequestCompleted] = []
    diagnostics_runtime.propagator = cast(
        TraceContextTextMapPropagator,
        FailingPropagator(),
    )
    app = _create_test_app(diagnostics_runtime, events)

    messages = asyncio.run(_invoke(app, headers=[(b"traceparent", _VALID_TRACEPARENT)]))

    assert _status(messages) == 200
    assert events[0].parent_context is ParentContextClassification.INVALID


class ContextNever:
    """Unreachable marker used to type the deliberately failing propagator."""


def test_span_start_failure_falls_back_to_unchanged_health_response(
    diagnostics_runtime: DiagnosticsRuntime,
) -> None:
    class FailingTracer:
        def start_as_current_span(self, *_: object, **__: object) -> ContextNever:
            raise RuntimeError(_CANARY)

    diagnostics_runtime.tracer = cast(Tracer, FailingTracer())
    events: list[ApiHealthRequestCompleted] = []
    app = _create_test_app(diagnostics_runtime, events)

    messages = asyncio.run(_invoke(app))

    assert _status(messages) == 200
    assert events == []


def test_application_lifespan_shuts_down_owned_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = DiagnosticsRuntime.create()
    shutdown_calls = 0

    def shutdown() -> None:
        nonlocal shutdown_calls
        shutdown_calls += 1

    monkeypatch.setattr(runtime, "shutdown", shutdown)
    app = create_app(
        Settings(environment="test", log_level="INFO"),
        diagnostics_runtime=runtime,
    )

    async def run_lifespan() -> None:
        async with app.router.lifespan_context(app):
            assert shutdown_calls == 0

    asyncio.run(run_lifespan())

    assert shutdown_calls == 1


def test_runtime_is_app_local_and_ignores_environment_sampler_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    global_provider = trace.get_tracer_provider()
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "always_off")
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", f"canary={_CANARY}")

    runtime = DiagnosticsRuntime.create()
    try:
        with runtime.tracer.start_as_current_span("root") as span:
            assert span.is_recording()
        assert trace.get_tracer_provider() is global_provider
        assert dict(runtime.provider.resource.attributes) == {
            "service.name": "ai-learning-platform-api"
        }
    finally:
        runtime.shutdown()


def test_diagnostic_event_formatter_emits_only_exact_allowlist(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    event = ApiHealthRequestCompleted(
        outcome=DiagnosticOutcome.OK,
        reason=DiagnosticReason.OK,
        parent_context=ParentContextClassification.VALID,
        trace_id=int(_TRACE_ID, 16),
        span_id=int(_PARENT_ID, 16),
        status_code=200,
        duration_ms=7,
    )

    emit_diagnostic_event(event)

    assert json.loads(capsys.readouterr().err) == event.to_payload()


@pytest.mark.parametrize(
    ("level", "severity", "outcome"),
    [
        (logging.DEBUG, "debug", "status"),
        (logging.INFO, "info", "status"),
        (logging.WARNING, "warning", "status"),
        (logging.ERROR, "error", "error"),
        (logging.CRITICAL, "critical", "error"),
    ],
)
def test_unstructured_logs_suppress_message_arguments_and_exception(
    capsys: pytest.CaptureFixture[str],
    level: int,
    severity: str,
    outcome: str,
) -> None:
    configure_logging("DEBUG")
    logger = logging.getLogger(f"{_CANARY}.logger")

    try:
        raise RuntimeError(_CANARY)
    except RuntimeError:
        logger.log(level, "%s", _CANARY, exc_info=True)

    serialized = capsys.readouterr().err
    assert _CANARY not in serialized
    assert json.loads(serialized) == {
        "schema_version": 1,
        "event": "process.log",
        "service": "api",
        "outcome": outcome,
        "reason": "unstructured_suppressed",
        "severity": severity,
    }


def test_uvicorn_access_logger_is_disabled() -> None:
    configure_logging("INFO")

    assert logging.getLogger("uvicorn.access").disabled


def test_invalid_environment_startup_does_not_leak_raw_value_or_traceback() -> None:
    environment = os.environ.copy()
    environment["AI_PLATFORM_ENVIRONMENT"] = _CANARY

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "ai_learning_platform_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--no-access-log",
        ],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert _CANARY not in combined
    assert "Traceback" not in combined
    assert "input_value" not in combined
    assert json.loads(result.stderr) == {
        "schema_version": 1,
        "event": "process.log",
        "service": "api",
        "outcome": "error",
        "reason": "unstructured_suppressed",
        "severity": "error",
    }


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"trace_id": 0}, "trace_id"),
        ({"span_id": 0}, "span_id"),
        ({"status_code": 99}, "status_code"),
        ({"status_code": 600}, "status_code"),
        ({"duration_ms": -1}, "duration_ms"),
    ],
)
def test_diagnostic_event_rejects_invalid_numeric_fields(
    overrides: dict[str, int],
    error: str,
) -> None:
    values = {
        "trace_id": int(_TRACE_ID, 16),
        "span_id": int(_PARENT_ID, 16),
        "status_code": 200,
        "duration_ms": 1,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=error):
        ApiHealthRequestCompleted(
            outcome=DiagnosticOutcome.OK,
            reason=DiagnosticReason.OK,
            parent_context=ParentContextClassification.ABSENT,
            **values,
        )
