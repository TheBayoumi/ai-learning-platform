"""Deterministic tests for the fixed API-and-web runtime smoke."""

from __future__ import annotations

import http.client
import io
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import BinaryIO, ClassVar, TextIO, cast

import pytest

from ai_learning_platform_api.development import smoke
from ai_learning_platform_api.development import supervisor as dev_supervisor


class FakeProcess:
    def __init__(self, process_id: int, return_code: int | None = None) -> None:
        self.pid = process_id
        self.return_code = return_code
        self.stderr: io.BytesIO | None = None

    def poll(self) -> int | None:
        return self.return_code

    def send_signal(self, _signal_number: int) -> None:
        self.return_code = 0

    def kill(self) -> None:
        self.return_code = 1


class FakeController:
    def __init__(self, result: bool = True, *, raises: bool = False) -> None:
        self.result = result
        self.raises = raises
        self.calls: list[tuple[dev_supervisor.ManagedProcess, ...]] = []

    def shutdown(
        self,
        processes: Sequence[dev_supervisor.ManagedProcess],
        _signals: dev_supervisor.ShutdownSignals,
        _output: TextIO,
    ) -> bool:
        self.calls.append(tuple(processes))
        if self.raises:
            raise OSError("safe test cleanup failure")
        return self.result


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def monotonic(self) -> float:
        return self.current

    def sleep(self, duration: float) -> None:
        self.current += duration


class FakeHttpResult:
    def __init__(
        self,
        *,
        status: int = 200,
        content_type: str | None = "application/json; charset=utf-8",
        content_length: str | None = None,
        body: bytes = b"{}",
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status = status
        self._headers = {
            "content-type": content_type,
            "content-length": content_length,
        }
        if headers is not None:
            self._headers.update(headers)
        self._body = body

    def getheader(self, name: str) -> str | None:
        return self._headers[name]

    def getheaders(self) -> list[tuple[str, str]]:
        return [(name, value) for name, value in self._headers.items() if value is not None]

    def read(self, amount: int) -> bytes:
        return self._body[:amount]


class FakeHttpConnection:
    result = FakeHttpResult()
    instances: ClassVar[list[FakeHttpConnection]] = []

    def __init__(self, host: str, port: int, *, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.request_call: tuple[str, str, dict[str, str]] | None = None
        self.closed = False
        type(self).instances.append(self)

    def request(self, method: str, path: str, *, headers: dict[str, str]) -> None:
        self.request_call = (method, path, headers)

    def getresponse(self) -> FakeHttpResult:
        return type(self).result

    def close(self) -> None:
        self.closed = True


def _service(name: str) -> dev_supervisor.ServiceSpec:
    return dev_supervisor.ServiceSpec(
        name=name,
        command=(name,),
        working_directory=Path.cwd(),
        environment={},
    )


def _json_response(value: object, *, status: int = 200) -> smoke.HttpResponse:
    return smoke.HttpResponse(
        status=status,
        media_type="application/json",
        body=json.dumps(value).encode("utf-8"),
    )


def _available_html() -> str:
    return """<!doctype html>
<section data-api-state="available" aria-labelledby="api-integration-heading">
  <p role="status" aria-atomic="true" aria-labelledby="api-status-label">Local API available</p>
  <p>This status reports local process liveness only.</p>
</section>
"""


def _web_response(html: str | None = None) -> smoke.HttpResponse:
    return smoke.HttpResponse(
        status=200,
        media_type="text/html",
        body=(html or _available_html()).encode("utf-8"),
    )


def _create_repository(tmp_path: Path) -> tuple[Path, object]:
    canonical: object = {"openapi": "3.1.0", "paths": {}}
    artifact = tmp_path / "apps" / "api" / "openapi" / "health.openapi.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps(canonical), encoding="utf-8")
    (tmp_path / "apps" / "web" / ".next" / "dev").mkdir(parents=True)
    return tmp_path, canonical


def _requester(canonical: object) -> smoke.Requester:
    def request(port: int, path: str) -> smoke.HttpResponse:
        if (port, path) == (dev_supervisor.API_PORT, "/health/live"):
            return _json_response({"status": "ok", "detail": "process is live"})
        if (port, path) == (dev_supervisor.API_PORT, "/health/ready"):
            return _json_response(
                {
                    "status": "ok",
                    "detail": (
                        "configuration is valid; no external dependency checks are performed"
                    ),
                }
            )
        if (port, path) == (dev_supervisor.API_PORT, "/openapi.json"):
            return _json_response(canonical)
        if (port, path) == (dev_supervisor.WEB_PORT, "/"):
            return _web_response()
        raise AssertionError(f"unexpected request {port} {path}")

    return request


def _runtime(
    repository_root: Path,
    canonical: object,
    *,
    controller: FakeController | None = None,
    clock: FakeClock | None = None,
    requester: smoke.Requester | None = None,
    metadata_requester: smoke.MetadataRequester | None = None,
    launcher: smoke.Launcher | None = None,
    port_probe: smoke.PortProbe = lambda _port: False,
    signals: dev_supervisor.ShutdownSignals | None = None,
    resource_observer: smoke.ResourceObserver | None = None,
) -> tuple[smoke.RuntimeSmoke, FakeController, FakeClock]:
    actual_controller = controller or FakeController()
    actual_clock = clock or FakeClock()
    next_pid = iter((101, 102))
    actual_launcher = launcher or (lambda _service, _platform: FakeProcess(next(next_pid)))
    return (
        smoke.RuntimeSmoke(
            repository_root=repository_root,
            services=(_service("api"), _service("web")),
            platform="posix",
            launcher=actual_launcher,
            requester=requester or _requester(canonical),
            metadata_requester=metadata_requester or smoke.request_loopback_with_headers,
            port_probe=port_probe,
            resource_observer=resource_observer
            or (
                lambda processes: smoke.ResourceObservation(
                    process_count=len(processes), resident_bytes=8192
                )
            ),
            controller=actual_controller,
            signals=signals,
            monotonic=actual_clock.monotonic,
            sleep=actual_clock.sleep,
            output=io.StringIO(),
        ),
        actual_controller,
        actual_clock,
    )


def _trace_id(value: int) -> str:
    return f"{value:032x}"


def _span_id(value: int) -> str:
    return f"{value:016x}"


def _api_diagnostic(
    value: int,
    *,
    parent_context: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "event": smoke.API_DIAGNOSTIC_EVENT,
        "service": "api",
        "operation": "health_live",
        "outcome": "ok",
        "reason": "ok",
        "parent_context": parent_context,
        "trace_id": _trace_id(value),
        "span_id": _span_id(10_000 + value),
        "status_code": 200,
        "duration_ms": value % 7,
    }


def _web_diagnostic(
    value: int,
    *,
    outcome: str = "ok",
    result: str = "available",
    reason: str = "ok",
    status_code: int = 200,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "event": smoke.WEB_DIAGNOSTIC_EVENT,
        "service": "web",
        "operation": "health_live",
        "outcome": outcome,
        "result": result,
        "reason": reason,
        "trace_id": _trace_id(value),
        "span_id": _span_id(20_000 + value),
        "status_code": status_code,
        "duration_ms": value % 11,
    }


def _diagnostic_capture(
    *,
    correlated_requests: int,
    include_inner: bool = False,
) -> bytes:
    events: list[dict[str, object]] = []
    for value in range(10, 10 + correlated_requests):
        events.extend(
            (
                _web_diagnostic(value),
                _api_diagnostic(value, parent_context="valid"),
            )
        )
    events.extend(
        (
            _api_diagnostic(1_000, parent_context="absent"),
            _api_diagnostic(1_001, parent_context="absent"),
            _api_diagnostic(1_002, parent_context="invalid"),
            _web_diagnostic(2_000),
            _web_diagnostic(
                2_001,
                outcome="error",
                result="unavailable",
                reason="http_status",
                status_code=503,
            ),
            _web_diagnostic(
                2_002,
                outcome="error",
                result="invalid_response",
                reason="invalid_json",
                status_code=200,
            ),
        )
    )
    lines = [
        json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
        for event in reversed(events)
    ]
    if include_inner:
        inner = smoke.InnerSmokeObservation(
            runtime=smoke.SmokeObservation(1, 2, 3, 4, 5, 6, 7, 1),
            scenario=smoke.DiagnosticScenarioObservation(
                correlated_requests=smoke.FIXED_LATENCY_SAMPLE_COUNT + 1,
                latency_sample_count=smoke.FIXED_LATENCY_SAMPLE_COUNT,
                concurrent_request_count=smoke.CONCURRENT_REQUEST_WORKERS,
                correlated_latency_p50_ms=11,
                correlated_latency_p95_ms=19,
                correlated_latency_max_ms=23,
                induced_failure_ms=31,
            ),
        )
        lines.append(
            b"[smoke-inner] passed "
            + json.dumps(asdict(inner), sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
    return b"\r\n".join(lines) + b"\r\n"


def test_request_loopback_is_literal_bounded_and_normalizes_media_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeHttpConnection.instances = []
    FakeHttpConnection.result = FakeHttpResult(content_length="2", body=b"{}")
    monkeypatch.setattr(http.client, "HTTPConnection", FakeHttpConnection)

    response = smoke.request_loopback(8000, "/health/live")

    connection = FakeHttpConnection.instances[-1]
    assert (connection.host, connection.port, connection.timeout) == (
        "127.0.0.1",
        8000,
        smoke.REQUEST_TIMEOUT_SECONDS,
    )
    assert connection.request_call == (
        "GET",
        "/health/live",
        {"Accept": "application/json"},
    )
    assert connection.closed
    assert response == smoke.HttpResponse(
        200,
        "application/json",
        b"{}",
        (("content-type", "application/json; charset=utf-8"), ("content-length", "2")),
    )


def test_request_loopback_with_headers_forwards_only_the_given_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeHttpConnection.instances = []
    FakeHttpConnection.result = FakeHttpResult(body=b"{}")
    monkeypatch.setattr(http.client, "HTTPConnection", FakeHttpConnection)

    smoke.request_loopback_with_headers(
        8000,
        "/health/live",
        {"Accept": "application/json", "Traceparent": smoke.MALFORMED_TRACEPARENT},
    )

    assert FakeHttpConnection.instances[-1].request_call == (
        "GET",
        "/health/live",
        {"Accept": "application/json", "Traceparent": smoke.MALFORMED_TRACEPARENT},
    )


@pytest.mark.parametrize("content_length", ["invalid", "-1", str(smoke.MAX_RESPONSE_BYTES + 1)])
def test_request_loopback_rejects_invalid_or_oversize_declared_lengths(
    monkeypatch: pytest.MonkeyPatch, content_length: str
) -> None:
    FakeHttpConnection.result = FakeHttpResult(content_length=content_length)
    monkeypatch.setattr(http.client, "HTTPConnection", FakeHttpConnection)

    with pytest.raises(smoke.SmokeFailure, match=r"content length|byte limit"):
        smoke.request_loopback(8000, "/health/live")


def test_request_loopback_rejects_oversize_read_and_allows_absent_media_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(http.client, "HTTPConnection", FakeHttpConnection)
    FakeHttpConnection.result = FakeHttpResult(
        content_type=None,
        body=b"x" * (smoke.MAX_RESPONSE_BYTES + 1),
    )
    with pytest.raises(smoke.SmokeFailure, match="byte limit"):
        smoke.request_loopback(8000, "/")

    FakeHttpConnection.result = FakeHttpResult(content_type=None, body=b"{}")
    assert smoke.request_loopback(8000, "/").media_type is None


def test_request_loopback_bounds_response_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http.client, "HTTPConnection", FakeHttpConnection)
    FakeHttpConnection.result = FakeHttpResult(
        headers={f"x-{index}": "ok" for index in range(smoke.MAX_RESPONSE_HEADER_COUNT)}
    )
    with pytest.raises(smoke.SmokeFailure, match="too many response headers"):
        smoke.request_loopback(8000, "/")

    FakeHttpConnection.result = FakeHttpResult(
        headers={"x-large": "x" * smoke.MAX_RESPONSE_HEADER_BYTES}
    )
    with pytest.raises(smoke.SmokeFailure, match="headers exceed the byte limit"):
        smoke.request_loopback(8000, "/")


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (smoke.HttpResponse(503, "application/json", b"{}"), "HTTP 503"),
        (smoke.HttpResponse(200, "text/plain", b"{}"), "media type"),
        (smoke.HttpResponse(200, "application/json", b"not-json"), "invalid JSON"),
    ],
)
def test_json_contract_rejects_transport_shape_without_echoing_body(
    response: smoke.HttpResponse, message: str
) -> None:
    with pytest.raises(smoke.SmokeFailure, match=message) as raised:
        smoke._assert_health(response, path="/health/live", detail="process is live")
    assert "not-json" not in str(raised.value)


def test_health_and_openapi_require_exact_contracts() -> None:
    smoke._assert_health(
        _json_response({"status": "ok", "detail": "process is live"}),
        path="/health/live",
        detail="process is live",
    )
    with pytest.raises(smoke.SmokeFailure, match="health contract"):
        smoke._assert_health(
            _json_response({"status": "ok", "detail": "different"}),
            path="/health/live",
            detail="process is live",
        )
    smoke._assert_openapi(_json_response({"openapi": "3.1.0"}), {"openapi": "3.1.0"})
    with pytest.raises(smoke.SmokeFailure, match="canonical"):
        smoke._assert_openapi(_json_response({"openapi": "different"}), {"openapi": "3.1.0"})


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (smoke.HttpResponse(500, "text/html", b""), "HTTP 500"),
        (smoke.HttpResponse(200, "application/json", b"{}"), "media type"),
        (smoke.HttpResponse(200, "text/html", b"\xff"), "UTF-8"),
        (_web_response("<main>Local API available</main>"), "accessible available"),
        (
            _web_response(_available_html() + '<i data-api-state="unavailable"></i>'),
            "forbidden state",
        ),
        (
            smoke.HttpResponse(
                200,
                "text/html",
                _available_html().encode("utf-8"),
                (("x-trace_id", _trace_id(1)),),
            ),
            "headers exposed",
        ),
        (
            smoke.HttpResponse(
                200,
                "text/html",
                _available_html().encode("utf-8"),
                (("x-private", smoke.RESPONSE_DETAIL_CANARY),),
            ),
            "confidential test metadata",
        ),
    ],
)
def test_web_contract_fails_closed(response: smoke.HttpResponse, message: str) -> None:
    with pytest.raises(smoke.SmokeFailure, match=message):
        smoke._assert_available_web(response)


def test_web_contract_accepts_only_accessible_available_state() -> None:
    smoke._assert_available_web(_web_response())


def test_invalid_web_contract_is_accessible_and_confidential() -> None:
    response = _web_response(
        _available_html()
        .replace('data-api-state="available"', 'data-api-state="invalid-response"')
        .replace("Local API available", "Local API response invalid")
    )
    smoke._assert_invalid_web(response)


@pytest.mark.parametrize(
    ("assertion", "response", "message"),
    [
        (
            smoke._assert_unavailable_web,
            smoke.HttpResponse(500, "text/html", b""),
            "HTTP 500",
        ),
        (
            smoke._assert_unavailable_web,
            smoke.HttpResponse(200, "application/json", b"{}"),
            "media type",
        ),
        (
            smoke._assert_unavailable_web,
            smoke.HttpResponse(200, "text/html", b"\xff"),
            "UTF-8",
        ),
        (
            smoke._assert_unavailable_web,
            _web_response("<main>Local API unavailable</main>"),
            "accessible unavailable",
        ),
        (
            smoke._assert_unavailable_web,
            _web_response(
                _available_html()
                .replace('data-api-state="available"', 'data-api-state="unavailable"')
                .replace("Local API available", "Local API unavailable")
                + '<i data-api-state="available"></i>'
            ),
            "forbidden state",
        ),
        (
            smoke._assert_invalid_web,
            smoke.HttpResponse(500, "text/html", b""),
            "HTTP 500",
        ),
        (
            smoke._assert_invalid_web,
            smoke.HttpResponse(200, "application/json", b"{}"),
            "media type",
        ),
        (
            smoke._assert_invalid_web,
            smoke.HttpResponse(200, "text/html", b"\xff"),
            "UTF-8",
        ),
        (
            smoke._assert_invalid_web,
            _web_response("<main>Local API response invalid</main>"),
            "accessible invalid-response",
        ),
        (
            smoke._assert_invalid_web,
            _web_response(
                _available_html()
                .replace('data-api-state="available"', 'data-api-state="invalid-response"')
                .replace("Local API available", "Local API response invalid")
                + '<i data-api-state="unavailable"></i>'
            ),
            "forbidden state",
        ),
    ],
)
def test_failure_web_contracts_fail_closed(
    assertion: Callable[[smoke.HttpResponse], None],
    response: smoke.HttpResponse,
    message: str,
) -> None:
    with pytest.raises(smoke.SmokeFailure, match=message):
        assertion(response)


def test_diagnostic_service_preparation_uses_real_otel_configuration_canaries() -> None:
    services = (_service("api"), _service("web"))

    prepared = smoke._prepare_diagnostic_services(services)

    assert services[0].environment == {}
    assert prepared[0].environment["OTEL_SERVICE_NAME"] == smoke.CONFIGURATION_CANARY
    assert prepared[1].environment["OTEL_RESOURCE_ATTRIBUTES"] == (
        f"f02.canary={smoke.CONFIGURATION_CANARY}"
    )


def test_diagnostic_parser_and_correlator_are_order_independent_and_byte_exact() -> None:
    content = _diagnostic_capture(correlated_requests=2)

    smoke._validate_captured_log(content)
    proof = smoke._assert_diagnostic_proof(content, correlated_requests=2)
    raw_events = smoke._extract_diagnostic_events(content)

    assert proof == smoke.DiagnosticProofObservation(
        correlated_requests=2,
        diagnostic_event_count=10,
        diagnostic_event_bytes=sum(len(line) for line in content.splitlines()),
        api_diagnostic_bytes=sum(
            size for event, size in raw_events if event["event"] == smoke.API_DIAGNOSTIC_EVENT
        ),
        web_diagnostic_bytes=sum(
            size for event, size in raw_events if event["event"] == smoke.WEB_DIAGNOSTIC_EVENT
        ),
        captured_stderr_bytes=len(content),
    )


@pytest.mark.parametrize(
    "content",
    [
        b'{"event":"api.health.request.completed","event":"api.health.request.completed"}\n',
        b'prefix api.health.request.completed {"event":"process.log"}\n',
        b'["web.health.request.completed"]\n',
        b'{"event":"api.health.request.completed"\n',
    ],
)
def test_diagnostic_parser_rejects_duplicate_prefixed_or_corrupt_marker_lines(
    content: bytes,
) -> None:
    with pytest.raises(smoke.SmokeFailure, match=r"duplicate|corrupt|invalid JSON"):
        smoke._extract_diagnostic_events(content)


def test_diagnostic_parser_rejects_oversized_event() -> None:
    event = _api_diagnostic(10, parent_context="valid")
    event["padding"] = "x" * smoke.MAX_DIAGNOSTIC_EVENT_BYTES
    content = json.dumps(event).encode("utf-8") + b"\n"

    with pytest.raises(smoke.SmokeFailure, match="byte limit"):
        smoke._extract_diagnostic_events(content)


def test_diagnostic_parser_ignores_non_event_noise_and_bounds_total_capture() -> None:
    process_log = json.dumps(
        {
            "schema_version": 1,
            "event": "process.log",
            "service": "api",
            "outcome": "status",
            "reason": "unstructured_suppressed",
            "severity": "info",
        },
        separators=(",", ":"),
    ).encode("utf-8")
    assert smoke._extract_diagnostic_events(b"not json\n{invalid\n[]\n" + process_log) == []
    with pytest.raises(smoke.SmokeFailure, match="byte limit"):
        smoke._validate_captured_log(b"x" * (smoke.MAX_CAPTURE_BYTES + 1))
    with pytest.raises(smoke.SmokeFailure, match="process output"):
        smoke._extract_diagnostic_events(process_log.replace(b'"severity":"info"', b'"raw":1'))
    with pytest.raises(smoke.SmokeFailure, match="process output"):
        smoke._extract_diagnostic_events(
            process_log.replace(b'"schema_version":1', b'"schema_version":true')
        )
    with pytest.raises(smoke.SmokeFailure, match="corrupt event"):
        smoke._extract_diagnostic_events(b'{"event":"unknown"}\n')


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "schema"),
        ("event", smoke.WEB_DIAGNOSTIC_EVENT, "wrong service output"),
        ("service", "worker", "service"),
        ("operation", "raw_path", "operation"),
        ("trace_id", 1, "field type"),
        ("trace_id", "0" * 32, "trace identifier"),
        ("trace_id", "A" * 32, "trace identifier"),
        ("span_id", "0" * 16, "trace identifier"),
        ("status_code", True, "field type"),
        ("status_code", 99, "status code"),
        ("duration_ms", -1, "duration"),
    ],
)
def test_diagnostic_event_validator_rejects_schema_type_and_value_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    event = _api_diagnostic(10, parent_context="valid")
    event[field] = value
    with pytest.raises(smoke.SmokeFailure, match=message):
        smoke._validate_event(event, event_name=smoke.API_DIAGNOSTIC_EVENT)


@pytest.mark.parametrize(
    ("marker", "message"),
    [
        *((marker, "confidential") for marker in smoke.CONFIDENTIAL_MARKERS),
        ("http://private.invalid", "raw_url"),
        ("https://private.invalid", "raw_url"),
        ("/health/live", "raw_health_path"),
        ("authorization", "raw_authorization_header"),
        ("cookie", "raw_cookie_header"),
        ("traceparent", "raw_trace_header"),
        ("x-f02-canary", "raw_canary_header"),
        ("traceback", "raw_exception"),
    ],
)
def test_captured_log_rejects_confidential_or_raw_values(
    marker: str,
    message: str,
) -> None:
    with pytest.raises(smoke.SmokeFailure, match=message):
        smoke._validate_captured_log(marker.encode("ascii"))


def test_diagnostic_filter_maps_web_framework_output_before_outer_capture() -> None:
    raw = (
        b"\n"
        b"ready on http://127.0.0.1:3000\n"
        b"learn more at https://nextjs.org/docs\n"
        b"ordinary framework status\n"
    )
    sink = io.BytesIO()
    filtered = smoke._DiagnosticFilteredProcess(
        FakeProcess(700, return_code=0),
        io.BytesIO(raw),
        sink,
        "web",
    )

    assert filtered.diagnostic_filter_ok()
    content = sink.getvalue()
    assert b"http://" not in content
    assert b"https://" not in content
    smoke._validate_captured_log(content)
    assert smoke._extract_diagnostic_events(content) == []
    process_events = [json.loads(line) for line in content.splitlines()]
    assert len(process_events) == 3
    assert {event["service"] for event in process_events} == {"web"}
    assert {event["reason"] for event in process_events} == {"unstructured_suppressed"}


@pytest.mark.parametrize(
    "raw",
    [
        b'{"event":"unknown"}\n',
        b'{"event":"api.health.request.completed","event":"api.health.request.completed"}\n',
        b'prefix api.health.request.completed {"event":"process.log"}\n',
        smoke._INNER_PROOF_PREFIX + b"{}\n",
    ],
)
def test_diagnostic_filter_preserves_structured_proof_and_marker_candidates(
    raw: bytes,
) -> None:
    sink = io.BytesIO()
    filtered = smoke._DiagnosticFilteredProcess(
        FakeProcess(701, return_code=0),
        io.BytesIO(raw),
        sink,
        "web",
    )

    assert filtered.diagnostic_filter_ok()
    assert sink.getvalue() == raw


@pytest.mark.parametrize(
    ("service_name", "raw"),
    [
        ("api", b"api ready at http://private.invalid\n"),
        ("web", b'{"event":"unknown","raw":"http://private.invalid"}\n'),
        ("web", b"Traceback from framework\n"),
        ("web", b"framework request /health/live\n"),
    ],
)
def test_diagnostic_filter_forwards_sensitive_or_structured_candidates_for_rejection(
    service_name: str,
    raw: bytes,
) -> None:
    sink = io.BytesIO()
    filtered = smoke._DiagnosticFilteredProcess(
        FakeProcess(702, return_code=0),
        io.BytesIO(raw),
        sink,
        service_name,
    )

    assert filtered.diagnostic_filter_ok()
    assert sink.getvalue() == raw
    with pytest.raises(smoke.SmokeFailure, match=r"raw_url|raw_health_path|raw_exception"):
        smoke._validate_captured_log(sink.getvalue())


def test_diagnostic_filter_rejects_confidential_content_without_forwarding_it() -> None:
    raw = f"framework output {smoke.REQUEST_CANARY}\n".encode("ascii")
    sink = io.BytesIO()
    filtered = smoke._DiagnosticFilteredProcess(
        FakeProcess(703, return_code=0),
        io.BytesIO(raw),
        sink,
        "web",
    )

    assert not filtered.diagnostic_filter_ok()
    content = sink.getvalue()
    assert smoke.REQUEST_CANARY.encode("ascii") not in content
    assert content == smoke._FILTER_REJECTION_EVENT
    with pytest.raises(smoke.SmokeFailure, match="corrupt event"):
        smoke._extract_diagnostic_events(content)


def test_diagnostic_filter_rejects_io_failures() -> None:
    class FailingSink:
        def write(self, _content: object) -> int:
            raise OSError("private sink failure")

        def flush(self) -> None:
            pass

    class ShortWriteSink(io.BytesIO):
        def write(self, content: object) -> int:
            super().write(cast(bytes, content)[:1])
            return 1

    class FailingReader(io.BytesIO):
        def readline(self, _size: int | None = -1) -> bytes:
            raise OSError("private read failure")

    class FailingCloseReader(io.BytesIO):
        def __init__(self) -> None:
            super().__init__()
            self._failed_once = False

        def close(self) -> None:
            if not self._failed_once:
                self._failed_once = True
                raise ValueError("private close failure")
            super().close()

    write_failure = smoke._DiagnosticFilteredProcess(
        FakeProcess(707, return_code=0),
        io.BytesIO(b"ordinary output\n"),
        cast(BinaryIO, FailingSink()),
        "api",
    )
    assert not write_failure.diagnostic_filter_ok()

    short_write = smoke._DiagnosticFilteredProcess(
        FakeProcess(704, return_code=0),
        io.BytesIO(b"ordinary output\n"),
        ShortWriteSink(),
        "api",
    )
    assert not short_write.diagnostic_filter_ok()

    read_sink = io.BytesIO()
    read_failure = smoke._DiagnosticFilteredProcess(
        FakeProcess(705, return_code=0),
        FailingReader(),
        read_sink,
        "web",
    )
    assert not read_failure.diagnostic_filter_ok()
    assert read_sink.getvalue() == smoke._FILTER_REJECTION_EVENT

    close_failure = smoke._DiagnosticFilteredProcess(
        FakeProcess(706, return_code=0),
        FailingCloseReader(),
        io.BytesIO(),
        "api",
    )
    assert not close_failure.diagnostic_filter_ok()


def test_diagnostic_filter_rejects_oversized_lines_and_early_pipe_close() -> None:
    oversized_sink = io.BytesIO()
    oversized = smoke._DiagnosticFilteredProcess(
        FakeProcess(707, return_code=0),
        io.BytesIO(b"x" * (smoke.MAX_CAPTURE_BYTES + 1)),
        oversized_sink,
        "api",
    )
    assert not oversized.diagnostic_filter_ok()
    assert oversized_sink.getvalue() == smoke._FILTER_REJECTION_EVENT

    early_close = smoke._DiagnosticFilteredProcess(
        FakeProcess(708),
        io.BytesIO(),
        io.BytesIO(),
        "web",
    )
    assert early_close.diagnostic_filter_failed()


def test_diagnostic_filter_delegates_owned_process_lifecycle() -> None:
    class OwnedFakeProcess(FakeProcess):
        def __init__(self) -> None:
            super().__init__(709, return_code=0)
            self.closed = False

        def tree_active(self) -> bool:
            return not self.closed

        def terminate_tree(self) -> bool:
            self.return_code = 1
            return True

        def close_tree(self) -> None:
            self.closed = True

    process = OwnedFakeProcess()
    filtered = smoke._DiagnosticFilteredProcess(
        process,
        io.BytesIO(),
        io.BytesIO(),
        "api",
    )
    assert filtered.poll() == 0
    assert filtered.tree_active()
    assert filtered.terminate_tree()
    filtered.send_signal(int(signal.SIGTERM))
    filtered.kill()
    filtered.close_tree()
    assert process.closed


def test_launch_diagnostic_service_pipes_and_filters_child_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, object]] = []
    process = FakeProcess(710, return_code=0)
    process.stderr = io.BytesIO(b"ready at http://127.0.0.1:3000\n")

    def launch(
        _service: dev_supervisor.ServiceSpec,
        _platform: dev_supervisor.PlatformFamily,
        *,
        stdout: object = None,
        stderr: object = None,
    ) -> FakeProcess:
        calls.append((stdout, stderr))
        return process

    monkeypatch.setattr(smoke, "launch_service", launch)
    sink = io.BytesIO()
    filtered = smoke._launch_diagnostic_service(_service("web"), "posix", sink=sink)

    assert calls == [(subprocess.DEVNULL, subprocess.PIPE)]
    assert isinstance(filtered, smoke._DiagnosticFilteredProcess)
    assert filtered.diagnostic_filter_ok()
    smoke._validate_captured_log(sink.getvalue())


def test_launch_diagnostic_service_uses_default_binary_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BinaryStderr:
        def __init__(self) -> None:
            self.buffer = io.BytesIO()

    process = FakeProcess(711, return_code=0)
    process.stderr = io.BytesIO(b"ordinary output\n")
    monkeypatch.setattr(
        smoke,
        "launch_service",
        lambda _service, _platform, **_kwargs: process,
    )
    binary_stderr = BinaryStderr()
    monkeypatch.setattr(sys, "stderr", binary_stderr)

    filtered = cast(
        smoke._DiagnosticFilteredProcess,
        smoke._launch_diagnostic_service(_service("api"), "posix"),
    )

    assert filtered.diagnostic_filter_ok()
    smoke._validate_captured_log(binary_stderr.buffer.getvalue())


def test_launch_diagnostic_service_rejects_missing_binary_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "stderr", object())
    with pytest.raises(OSError, match="binary diagnostic sink"):
        smoke._launch_diagnostic_service(_service("api"), "posix")


def test_launch_diagnostic_service_fails_closed_without_stderr_pipe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CloseableProcess(FakeProcess):
        def __init__(self) -> None:
            super().__init__(712)
            self.tree_closed = False

        def close_tree(self) -> None:
            self.tree_closed = True

    process = CloseableProcess()
    monkeypatch.setattr(
        smoke,
        "launch_service",
        lambda _service, _platform, **_kwargs: process,
    )

    with pytest.raises(OSError, match="stderr pipe"):
        smoke._launch_diagnostic_service(_service("api"), "posix", sink=io.BytesIO())
    assert process.return_code == 1
    assert process.tree_closed


def test_diagnostic_proof_rejects_allowlist_trace_and_count_drift() -> None:
    events = [json.loads(line) for line in _diagnostic_capture(correlated_requests=2).splitlines()]
    events[0]["raw_url"] = "suppressed"
    allowlist_drift = b"\n".join(
        json.dumps(event, separators=(",", ":")).encode("utf-8") for event in events
    )
    with pytest.raises(smoke.SmokeFailure, match="allowlist"):
        smoke._assert_diagnostic_proof(allowlist_drift, correlated_requests=2)

    events = [json.loads(line) for line in _diagnostic_capture(correlated_requests=2).splitlines()]
    events[0]["trace_id"] = _trace_id(10)
    reused_trace = b"\n".join(
        json.dumps(event, separators=(",", ":")).encode("utf-8") for event in events
    )
    with pytest.raises(smoke.SmokeFailure, match=r"leaked|reused|matches"):
        smoke._assert_diagnostic_proof(reused_trace, correlated_requests=2)

    with pytest.raises(smoke.SmokeFailure, match="volume"):
        smoke._assert_diagnostic_proof(
            _diagnostic_capture(correlated_requests=1), correlated_requests=2
        )


def test_diagnostic_proof_rejects_every_correlation_and_isolation_drift() -> None:
    def reject(
        mutate: Callable[[list[dict[str, object]], list[dict[str, object]]], None],
        message: str,
    ) -> None:
        events = [
            cast(dict[str, object], json.loads(line))
            for line in _diagnostic_capture(correlated_requests=2).splitlines()
        ]
        api_events = [event for event in events if event["event"] == smoke.API_DIAGNOSTIC_EVENT]
        web_events = [event for event in events if event["event"] == smoke.WEB_DIAGNOSTIC_EVENT]
        mutate(api_events, web_events)
        content = b"\n".join(
            json.dumps(event, separators=(",", ":")).encode("utf-8") for event in events
        )
        with pytest.raises(smoke.SmokeFailure, match=message):
            smoke._assert_diagnostic_proof(content, correlated_requests=2)

    reject(
        lambda api, _web: api[1].update(trace_id=api[0]["trace_id"]),
        "API request context",
    )
    reject(
        lambda api, _web: api[1].update(span_id=api[0]["span_id"]),
        "API span",
    )
    reject(
        lambda _api, web: web[1].update(trace_id=web[0]["trace_id"]),
        "web request context",
    )
    reject(
        lambda _api, web: web[1].update(span_id=web[0]["span_id"]),
        "web span",
    )
    reject(
        lambda api, _web: next(event for event in api if event["parent_context"] == "valid").update(
            parent_context="absent"
        ),
        "classifications",
    )
    reject(
        lambda api, _web: api[0].update(outcome="error"),
        "API diagnostic outcome",
    )
    reject(
        lambda _api, web: next(event for event in web if event["trace_id"] == _trace_id(10)).update(
            trace_id=_trace_id(9_000)
        ),
        "did not correlate",
    )
    reject(
        lambda _api, web: next(event for event in web if event["trace_id"] == _trace_id(10)).update(
            result="unavailable"
        ),
        "correlated web",
    )
    reject(
        lambda _api, web: next(
            event for event in web if event["trace_id"] == _trace_id(2_001)
        ).update(reason="timeout"),
        "induced web",
    )
    reject(
        lambda api, web: next(event for event in web if event["trace_id"] == _trace_id(10)).update(
            span_id=next(event for event in api if event["trace_id"] == _trace_id(10))["span_id"]
        ),
        "spans were not distinct",
    )
    reject(
        lambda api, _web: next(
            event for event in api if event["parent_context"] == "invalid"
        ).update(trace_id=smoke.MALFORMED_PARENT_TRACE_ID),
        "safe root",
    )
    reject(
        lambda api, _web: next(
            event for event in api if event["parent_context"] == "absent"
        ).update(trace_id=_trace_id(2_000)),
        "safe-root API context",
    )


def test_inner_observation_parser_is_fixed_and_consistent() -> None:
    content = _diagnostic_capture(
        correlated_requests=smoke.FIXED_LATENCY_SAMPLE_COUNT + 1,
        include_inner=True,
    )

    observation = smoke._extract_inner_observation(content)

    assert observation.runtime.resident_bytes == 5
    assert observation.scenario.latency_sample_count == smoke.FIXED_LATENCY_SAMPLE_COUNT

    drifted = content.replace(b'"next_bytes_delta":1', b'"next_bytes_delta":2')
    with pytest.raises(smoke.SmokeFailure, match="cache observation"):
        smoke._extract_inner_observation(drifted)


def test_inner_observation_parser_rejects_missing_corrupt_and_schema_drift() -> None:
    content = _diagnostic_capture(
        correlated_requests=smoke.FIXED_LATENCY_SAMPLE_COUNT + 1,
        include_inner=True,
    )
    prefix = b"[smoke-inner] passed "
    result_line = next(line for line in content.splitlines() if line.startswith(prefix))
    value = cast(dict[str, object], json.loads(result_line[len(prefix) :]))

    with pytest.raises(smoke.SmokeFailure, match="missing or duplicated"):
        smoke._extract_inner_observation(b"")
    with pytest.raises(smoke.SmokeFailure, match="missing or duplicated"):
        smoke._extract_inner_observation(result_line + b"\n" + result_line)
    with pytest.raises(smoke.SmokeFailure, match="invalid"):
        smoke._extract_inner_observation(prefix + b"{")

    def encoded(changed: dict[str, object]) -> bytes:
        return prefix + json.dumps(changed, separators=(",", ":")).encode("utf-8")

    with pytest.raises(smoke.SmokeFailure, match="fixed schema"):
        smoke._extract_inner_observation(encoded({"runtime": {}}))

    runtime_drift = json.loads(json.dumps(value))
    runtime_drift["runtime"].pop("api_live_ms")
    with pytest.raises(smoke.SmokeFailure, match="runtime observation"):
        smoke._extract_inner_observation(encoded(runtime_drift))

    scenario_drift = json.loads(json.dumps(value))
    scenario_drift["scenario"].pop("induced_failure_ms")
    with pytest.raises(smoke.SmokeFailure, match="diagnostic observation"):
        smoke._extract_inner_observation(encoded(scenario_drift))

    negative = json.loads(json.dumps(value))
    negative["runtime"]["api_live_ms"] = -1
    with pytest.raises(smoke.SmokeFailure, match="invalid measurement"):
        smoke._extract_inner_observation(encoded(negative))

    nullable = json.loads(json.dumps(value))
    nullable["runtime"]["process_count"] = None
    nullable["runtime"]["resident_bytes"] = None
    assert smoke._extract_inner_observation(encoded(nullable)).runtime.process_count is None

    inconsistent = json.loads(json.dumps(value))
    inconsistent["scenario"]["correlated_latency_p50_ms"] = 100
    with pytest.raises(smoke.SmokeFailure, match="fixed latency"):
        smoke._extract_inner_observation(encoded(inconsistent))


def test_nearest_rank_uses_the_fixed_sample_without_interpolation() -> None:
    values = list(range(1, 21))
    assert smoke._nearest_rank(values, 0.50) == 10
    assert smoke._nearest_rank(values, 0.95) == 19
    assert smoke._nearest_rank(values, 1.00) == 20
    with pytest.raises(smoke.SmokeFailure, match="empty"):
        smoke._nearest_rank([], 0.95)


def test_directory_bytes_is_zero_when_absent_and_sums_files(tmp_path: Path) -> None:
    assert smoke._directory_bytes(tmp_path / "absent") == 0
    (tmp_path / "nested").mkdir()
    (tmp_path / "one").write_bytes(b"123")
    (tmp_path / "nested" / "two").write_bytes(b"45")
    assert smoke._directory_bytes(tmp_path) == 5


def test_runtime_reports_prelaunch_cache_observation_failure_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    monkeypatch.setattr(
        smoke,
        "_directory_bytes",
        lambda _path: (_ for _ in ()).throw(OSError("private cache path")),
    )
    runtime, controller, _clock = _runtime(repository_root, canonical)

    with pytest.raises(smoke.SmokeFailure, match="cache could not be measured") as raised:
        runtime.run()
    assert "private cache path" not in str(raised.value)
    assert controller.calls == []


def test_runtime_reports_postcleanup_cache_observation_failure_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    observations = 0

    def observe(_path: Path) -> int:
        nonlocal observations
        observations += 1
        if observations == 2:
            raise OSError("private cache path")
        return 0

    monkeypatch.setattr(smoke, "_directory_bytes", observe)
    runtime, controller, _clock = _runtime(repository_root, canonical)

    with pytest.raises(smoke.SmokeFailure, match="cache could not be measured") as raised:
        runtime.run()
    assert "private cache path" not in str(raised.value)
    assert len(controller.calls) == 1


def test_port_probe_reports_only_a_listening_loopback_socket() -> None:
    listener = socket.socket()
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = int(listener.getsockname()[1])
        assert smoke._port_is_open(port)
    finally:
        listener.close()
    assert not smoke._port_is_open(port)


def test_failure_proof_server_scripts_response_detail_failure_and_invalid_json() -> None:
    server = smoke._FailureProofServer()
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    thread.start()
    try:
        missing = smoke.request_loopback(dev_supervisor.API_PORT, "/missing")
        available = smoke.request_loopback(dev_supervisor.API_PORT, "/health/live")
        unavailable = smoke.request_loopback(dev_supervisor.API_PORT, "/health/live")
        invalid = smoke.request_loopback(dev_supervisor.API_PORT, "/health/live")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)

    assert missing.status == 404
    assert json.loads(available.body)["detail"] == smoke.RESPONSE_DETAIL_CANARY
    assert unavailable.status == 503
    assert unavailable.body == smoke.FAILURE_TEXT_CANARY.encode("ascii")
    with pytest.raises(json.JSONDecodeError):
        json.loads(invalid.body)
    assert server.response_count == 3
    server.handle_error(object(), object())
    assert not thread.is_alive()
    assert not smoke._port_is_open(dev_supervisor.API_PORT)


def test_linux_resource_observation_is_group_scoped_and_tolerates_proc_races(
    tmp_path: Path,
) -> None:
    proc_root = tmp_path / "proc"
    for process_id, group_id, pages in ((101, 101, 3), (102, 999, 5), (103, 101, 7)):
        process_root = proc_root / str(process_id)
        process_root.mkdir(parents=True)
        (process_root / "stat").write_text(
            f"{process_id} (process with spaces) S 1 {group_id} 0", encoding="utf-8"
        )
        (process_root / "statm").write_text(f"20 {pages}", encoding="utf-8")
    (proc_root / "104").mkdir()
    (proc_root / "104" / "stat").write_text("invalid", encoding="utf-8")
    (proc_root / "not-a-pid").mkdir()
    processes = (
        dev_supervisor.ManagedProcess(_service("api"), FakeProcess(101)),
        dev_supervisor.ManagedProcess(_service("web"), FakeProcess(200)),
    )

    assert smoke.observe_linux_resources(processes, proc_root=proc_root, page_size=4096) == (
        smoke.ResourceObservation(process_count=2, resident_bytes=10 * 4096)
    )
    assert smoke.observe_linux_resources(processes, proc_root=tmp_path / "absent") == (
        smoke.ResourceObservation(process_count=None, resident_bytes=None)
    )


def test_linux_resource_observation_can_resolve_the_host_page_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    proc_root = tmp_path / "proc"
    process_root = proc_root / "101"
    process_root.mkdir(parents=True)
    (process_root / "stat").write_text("101 (api) S 1 101 0", encoding="utf-8")
    (process_root / "statm").write_text("20 2", encoding="utf-8")
    if "sysconf" not in vars(os):
        monkeypatch.setitem(vars(os), "sysconf", lambda _name: 4096)
    processes = (dev_supervisor.ManagedProcess(_service("api"), FakeProcess(101)),)

    observation = smoke.observe_linux_resources(processes, proc_root=proc_root)

    assert observation.process_count == 1
    assert observation.resident_bytes is not None
    assert observation.resident_bytes > 0


@pytest.mark.parametrize("value", ["invalid", "1 (name) S"])
def test_linux_stat_parser_rejects_invalid_shapes(value: str) -> None:
    with pytest.raises(ValueError, match="invalid proc stat"):
        smoke._read_linux_process_group(value)


def test_runtime_smoke_passes_contract_measures_cache_and_cleans_up(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    cached = repository_root / "apps" / "web" / ".next" / "dev" / "cache"
    cached.write_bytes(b"before")

    def request(port: int, path: str) -> smoke.HttpResponse:
        if path == "/":
            cached.write_bytes(b"after smoke")
        return _requester(canonical)(port, path)

    runtime, controller, _clock = _runtime(repository_root, canonical, requester=request)
    observation = runtime.run()

    assert observation == smoke.SmokeObservation(
        api_live_ms=0,
        smoke_ms=0,
        shutdown_ms=0,
        process_count=2,
        resident_bytes=8192,
        next_bytes_before=6,
        next_bytes_after=11,
        next_bytes_delta=5,
    )
    assert [item.service.name for item in controller.calls[0]] == ["api", "web"]


def test_runtime_diagnostic_scenario_exercises_concurrency_roots_and_fixture_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    web_calls = 0
    call_lock = threading.Lock()
    request_barrier = threading.Barrier(smoke.CONCURRENT_REQUEST_WORKERS)

    def state_response(state: str, label: str) -> smoke.HttpResponse:
        html = (
            _available_html()
            .replace('data-api-state="available"', f'data-api-state="{state}"')
            .replace("Local API available", label)
        )
        return _web_response(html)

    def metadata_request(
        port: int,
        _path: str,
        headers: Mapping[str, str],
    ) -> smoke.HttpResponse:
        nonlocal web_calls
        if port == dev_supervisor.API_PORT:
            return _json_response({"status": "ok", "detail": "process is live"})
        with call_lock:
            web_calls += 1
            call = web_calls
        probe_index = headers.get("X-F02-Probe-Index")
        if probe_index is not None and int(probe_index) < smoke.CONCURRENT_REQUEST_WORKERS:
            request_barrier.wait(timeout=1.0)
        if call <= smoke.FIXED_LATENCY_SAMPLE_COUNT + 1:
            return _web_response()
        if call == smoke.FIXED_LATENCY_SAMPLE_COUNT + 2:
            return state_response("unavailable", "Local API unavailable")
        return state_response("invalid-response", "Local API response invalid")

    class FakeFailureServer:
        response_count = 3

        def serve_forever(self, *, poll_interval: float) -> None:
            assert poll_interval == smoke.POLL_INTERVAL_SECONDS

        def shutdown(self) -> None:
            pass

        def server_close(self) -> None:
            pass

    monkeypatch.setattr(smoke, "_FailureProofServer", FakeFailureServer)
    launched: list[dev_supervisor.ServiceSpec] = []

    def launch(
        service: dev_supervisor.ServiceSpec,
        _platform: dev_supervisor.PlatformFamily,
    ) -> FakeProcess:
        launched.append(service)
        return FakeProcess(100 + len(launched))

    monkeypatch.setattr(smoke, "_launch_diagnostic_service", launch)
    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        launcher=dev_supervisor.launch_service,
        metadata_requester=metadata_request,
    )
    runtime._monotonic = time.monotonic

    observation = runtime.run_diagnostic()

    scenario = observation.scenario
    assert scenario.correlated_requests == smoke.FIXED_LATENCY_SAMPLE_COUNT + 1
    assert scenario.latency_sample_count == smoke.FIXED_LATENCY_SAMPLE_COUNT
    assert scenario.concurrent_request_count == smoke.CONCURRENT_REQUEST_WORKERS
    assert (
        0
        <= scenario.correlated_latency_p50_ms
        <= scenario.correlated_latency_p95_ms
        <= scenario.correlated_latency_max_ms
    )
    assert scenario.induced_failure_ms >= 0
    assert web_calls == smoke.FIXED_LATENCY_SAMPLE_COUNT + 3
    assert launched[0].environment["OTEL_SERVICE_NAME"] == smoke.CONFIGURATION_CANARY
    assert [[item.service.name for item in call] for call in controller.calls] == [
        ["api"],
        ["web"],
    ]


def test_concurrent_diagnostic_proof_requires_in_flight_overlap(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    runtime, _controller, _clock = _runtime(
        repository_root,
        canonical,
        metadata_requester=lambda _port, _path, _headers: _web_response(),
    )

    with pytest.raises(smoke.SmokeFailure, match="did not overlap in flight"):
        runtime._exercise_concurrent_health_requests()


def test_runtime_diagnostic_helpers_fail_safely_and_require_a_scenario(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    runtime, _controller, _clock = _runtime(
        repository_root,
        canonical,
        metadata_requester=lambda _port, _path, _headers: (_ for _ in ()).throw(
            OSError(smoke.REQUEST_CANARY)
        ),
    )
    with pytest.raises(smoke.SmokeFailure, match="safe") as raised:
        runtime._request_with_metadata(
            3000,
            "/private",
            {"X-Canary": smoke.REQUEST_CANARY},
            safe_path="/safe",
        )
    assert smoke.REQUEST_CANARY not in str(raised.value)

    monkeypatch.setattr(smoke, "PORT_CLOSE_TIMEOUT_SECONDS", 0.1)
    runtime._port_probe = lambda _port: True
    assert not runtime._wait_for_port_closed(8000)

    observation = smoke.SmokeObservation(1, 2, 3, 4, 5, 6, 7, 1)
    monkeypatch.setattr(
        runtime,
        "_run",
        lambda *, diagnostic_proof: (observation, None),
    )
    with pytest.raises(smoke.SmokeFailure, match="did not produce"):
        runtime.run_diagnostic()

    web_only = [
        dev_supervisor.ManagedProcess(_service("web"), FakeProcess(102)),
    ]
    with pytest.raises(smoke.SmokeFailure, match="API process was unavailable"):
        runtime._exercise_induced_failures(web_only)


def test_induced_failure_reports_controller_and_stub_failures_safely(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    raising_controller = FakeController(raises=True)
    runtime, _controller, _clock = _runtime(
        repository_root,
        canonical,
        controller=raising_controller,
    )
    managed = [
        dev_supervisor.ManagedProcess(_service("api"), FakeProcess(101)),
        dev_supervisor.ManagedProcess(_service("web"), FakeProcess(102)),
    ]
    with pytest.raises(smoke.SmokeFailure, match="shutdown did not complete"):
        runtime._exercise_induced_failures(managed)
    assert [item.service.name for item in managed] == ["api", "web"]

    runtime, _controller, _clock = _runtime(repository_root, canonical)
    monkeypatch.setattr(
        smoke,
        "_FailureProofServer",
        lambda: (_ for _ in ()).throw(OSError(smoke.FAILURE_TEXT_CANARY)),
    )
    managed = [
        dev_supervisor.ManagedProcess(_service("api"), FakeProcess(101)),
        dev_supervisor.ManagedProcess(_service("web"), FakeProcess(102)),
    ]
    with pytest.raises(smoke.SmokeFailure, match="stub could not start") as raised:
        runtime._exercise_induced_failures(managed)
    assert smoke.FAILURE_TEXT_CANARY not in str(raised.value)


def test_runtime_retries_only_startup_connection_errors(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    calls = 0

    def request(port: int, path: str) -> smoke.HttpResponse:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionRefusedError
        if path == "/" and calls == 5:
            raise http.client.RemoteDisconnected("retry")
        return _requester(canonical)(port, path)

    runtime, _controller, clock = _runtime(repository_root, canonical, requester=request)
    runtime.run()
    assert clock.current == pytest.approx(2 * smoke.POLL_INTERVAL_SECONDS)


def test_runtime_rejects_failed_diagnostic_filter(tmp_path: Path) -> None:
    class FilterFailedProcess(FakeProcess):
        def diagnostic_filter_failed(self) -> bool:
            return True

    repository_root, canonical = _create_repository(tmp_path)
    runtime, _controller, _clock = _runtime(repository_root, canonical)
    managed = [
        dev_supervisor.ManagedProcess(_service("api"), FilterFailedProcess(713)),
    ]

    with pytest.raises(smoke.SmokeFailure, match="diagnostic output filter failed"):
        runtime._ensure_running(managed)


def test_runtime_reports_child_exit_and_still_cleans_up(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    processes = iter((FakeProcess(101, 7), FakeProcess(102)))
    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        launcher=lambda _service, _platform: next(processes),
    )

    with pytest.raises(smoke.SmokeFailure, match=r"api exited.*code 7"):
        runtime.run()
    assert len(controller.calls[0]) == 2


@pytest.mark.parametrize("failed_path", ["/health/ready", "/openapi.json"])
def test_runtime_reports_post_start_transport_failure_without_private_detail(
    tmp_path: Path, failed_path: str
) -> None:
    repository_root, canonical = _create_repository(tmp_path)

    def request(port: int, path: str) -> smoke.HttpResponse:
        if path == failed_path:
            raise OSError("private transport detail")
        return _requester(canonical)(port, path)

    runtime, controller, _clock = _runtime(repository_root, canonical, requester=request)
    with pytest.raises(smoke.SmokeFailure, match="request failed") as raised:
        runtime.run()
    assert str(raised.value) == f"{failed_path} request failed"
    assert len(controller.calls) == 1


def test_runtime_reports_invalid_canonical_artifact_safely(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    (repository_root / "apps" / "api" / "openapi" / "health.openapi.json").write_text(
        "not-json", encoding="utf-8"
    )
    runtime, controller, _clock = _runtime(repository_root, canonical)

    with pytest.raises(smoke.SmokeFailure, match="canonical OpenAPI artifact") as raised:
        runtime.run()
    assert "not-json" not in str(raised.value)
    assert len(controller.calls) == 1


def test_runtime_reports_launch_failure_and_cleans_already_owned_process(
    tmp_path: Path,
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    calls = 0

    def launch(
        _service: dev_supervisor.ServiceSpec, _platform: dev_supervisor.PlatformFamily
    ) -> FakeProcess:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("private launch detail")
        return FakeProcess(101)

    runtime, controller, _clock = _runtime(repository_root, canonical, launcher=launch)
    with pytest.raises(smoke.SmokeFailure, match="failed to launch web") as raised:
        runtime.run()
    assert "private launch detail" not in str(raised.value)
    assert len(controller.calls[0]) == 1


def test_runtime_times_out_connection_retry_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    monkeypatch.setattr(smoke, "STARTUP_TIMEOUT_SECONDS", 0.1)
    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        requester=lambda _port, _path: (_ for _ in ()).throw(ConnectionRefusedError()),
    )

    with pytest.raises(smoke.SmokeFailure, match="deadline"):
        runtime.run()
    assert len(controller.calls) == 1


def test_runtime_rejects_live_response_received_after_shared_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    monkeypatch.setattr(smoke, "STARTUP_TIMEOUT_SECONDS", 0.1)
    clock = FakeClock()

    def request(port: int, path: str) -> smoke.HttpResponse:
        clock.current = 0.2
        return _requester(canonical)(port, path)

    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        clock=clock,
        requester=request,
    )
    with pytest.raises(smoke.SmokeFailure, match=r"API liveness.*deadline"):
        runtime.run()
    assert len(controller.calls) == 1


def test_runtime_times_out_web_connection_retry_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    monkeypatch.setattr(smoke, "STARTUP_TIMEOUT_SECONDS", 0.1)

    def request(port: int, path: str) -> smoke.HttpResponse:
        if path == "/":
            raise ConnectionRefusedError
        return _requester(canonical)(port, path)

    runtime, controller, _clock = _runtime(repository_root, canonical, requester=request)
    with pytest.raises(smoke.SmokeFailure, match="web availability"):
        runtime.run()
    assert len(controller.calls) == 1


def test_runtime_rejects_web_response_received_after_shared_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    monkeypatch.setattr(smoke, "STARTUP_TIMEOUT_SECONDS", 0.1)
    clock = FakeClock()

    def request(port: int, path: str) -> smoke.HttpResponse:
        response = _requester(canonical)(port, path)
        if path == "/":
            clock.current = 0.2
        return response

    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        clock=clock,
        requester=request,
    )
    with pytest.raises(smoke.SmokeFailure, match=r"web availability.*deadline"):
        runtime.run()
    assert len(controller.calls) == 1


def test_runtime_rejects_occupied_ports_before_launch(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    launched = False

    def launch(
        _service: dev_supervisor.ServiceSpec, _platform: dev_supervisor.PlatformFamily
    ) -> FakeProcess:
        nonlocal launched
        launched = True
        return FakeProcess(101)

    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        launcher=launch,
        port_probe=lambda port: port == dev_supervisor.WEB_PORT,
    )
    with pytest.raises(smoke.SmokeFailure, match="ports must be unused"):
        runtime.run()
    assert not launched
    assert controller.calls == []


@pytest.mark.parametrize("controller", [FakeController(False), FakeController(raises=True)])
def test_runtime_cleanup_failure_overrides_contract_success(
    tmp_path: Path, controller: FakeController
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    runtime, _controller, _clock = _runtime(repository_root, canonical, controller=controller)
    with pytest.raises(smoke.SmokeFailure, match="cleanup did not complete"):
        runtime.run()


def test_runtime_requires_ports_to_close_after_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    monkeypatch.setattr(smoke, "PORT_CLOSE_TIMEOUT_SECONDS", 0.1)
    probes = 0

    def port_probe(_port: int) -> bool:
        nonlocal probes
        probes += 1
        return probes > 2

    runtime, _controller, _clock = _runtime(
        repository_root,
        canonical,
        port_probe=port_probe,
    )
    with pytest.raises(smoke.SmokeFailure, match="cleanup did not complete"):
        runtime.run()


def test_runtime_maps_interrupt_to_safe_failure_and_cleans_up(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        requester=lambda _port, _path: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    with pytest.raises(smoke.SmokeFailure, match="interrupted"):
        runtime.run()
    assert len(controller.calls) == 1


def test_runtime_signal_request_interrupts_gracefully_then_allows_force(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    signals = dev_supervisor.ShutdownSignals()

    def request(port: int, path: str) -> smoke.HttpResponse:
        signals.request()
        return _requester(canonical)(port, path)

    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        requester=request,
        signals=signals,
    )
    with pytest.raises(smoke.SmokeFailure, match="interrupted"):
        runtime.run()
    assert signals.requested.is_set()
    assert not signals.forced.is_set()
    assert len(controller.calls) == 1
    signals.request()
    assert signals.forced.is_set()


def test_runtime_reports_resource_observation_failure_safely(tmp_path: Path) -> None:
    repository_root, canonical = _create_repository(tmp_path)
    runtime, controller, _clock = _runtime(
        repository_root,
        canonical,
        resource_observer=lambda _processes: (_ for _ in ()).throw(
            OSError("private resource path")
        ),
    )
    with pytest.raises(smoke.SmokeFailure, match="resources could not be observed") as raised:
        runtime.run()
    assert "private resource path" not in str(raised.value)
    assert len(controller.calls) == 1


def test_main_has_fixed_arguments_and_stable_exit_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert smoke.main(["unexpected"]) == 2
    assert "accepts no arguments" in capsys.readouterr().err
    assert smoke._runtime_main(["unexpected"]) == 2
    assert "accepts no arguments" in capsys.readouterr().err

    class PassingRuntime:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def run_diagnostic(self) -> smoke.InnerSmokeObservation:
            return smoke.InnerSmokeObservation(
                runtime=smoke.SmokeObservation(1, 2, 3, 4, 5, 6, 7, 1),
                scenario=smoke.DiagnosticScenarioObservation(
                    correlated_requests=21,
                    latency_sample_count=20,
                    concurrent_request_count=4,
                    correlated_latency_p50_ms=8,
                    correlated_latency_p95_ms=13,
                    correlated_latency_max_ms=21,
                    induced_failure_ms=34,
                ),
            )

    monkeypatch.setattr(smoke, "_install_interrupt_handlers", lambda _signals, _platform: None)
    monkeypatch.setattr(smoke, "RuntimeSmoke", PassingRuntime)
    monkeypatch.setattr(sys, "argv", ["smoke.py"])
    assert smoke._runtime_main() == 0
    assert '"resident_bytes": 5' in capsys.readouterr().err

    class FailingRuntime:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def run_diagnostic(self) -> smoke.InnerSmokeObservation:
            raise smoke.SmokeFailure("safe failure")

    monkeypatch.setattr(smoke, "RuntimeSmoke", FailingRuntime)
    assert smoke._runtime_main([]) == 1
    assert "safe failure" in capsys.readouterr().err

    content = _diagnostic_capture(
        correlated_requests=smoke.FIXED_LATENCY_SAMPLE_COUNT + 1,
        include_inner=True,
    )

    process = cast(subprocess.Popen[bytes], object())
    monkeypatch.setattr(smoke, "_launch_inner_runtime", lambda _platform: process)
    monkeypatch.setattr(
        smoke,
        "_capture_inner_runtime",
        lambda _process, _platform: (0, content, False, False),
    )
    assert smoke.main([]) == 0
    output = capsys.readouterr().out
    assert "[smoke] passed" in output
    assert '"resident_bytes": 5' in output

    private_content = content + smoke.FAILURE_TEXT_CANARY.encode("ascii")

    monkeypatch.setattr(
        smoke,
        "_capture_inner_runtime",
        lambda _process, _platform: (1, private_content, False, False),
    )
    assert smoke.main([]) == 1
    error = capsys.readouterr().err
    assert "captured output was suppressed" in error
    assert smoke.FAILURE_TEXT_CANARY not in error

    monkeypatch.setattr(
        smoke,
        "_capture_inner_runtime",
        lambda _process, _platform: (1, private_content, True, False),
    )
    assert smoke.main([]) == 1
    error = capsys.readouterr().err
    assert "exceeded the byte limit" in error
    assert smoke.FAILURE_TEXT_CANARY not in error

    monkeypatch.setattr(
        smoke,
        "_capture_inner_runtime",
        lambda _process, _platform: (1, b"", False, True),
    )
    assert smoke.main([]) == 1
    assert "could not be captured" in capsys.readouterr().err

    monkeypatch.setattr(
        smoke,
        "_launch_inner_runtime",
        lambda _platform: (_ for _ in ()).throw(OSError("private path")),
    )
    assert smoke.main([]) == 1
    error = capsys.readouterr().err
    assert "could not be launched or captured" in error
    assert "private path" not in error

    monkeypatch.setattr(smoke, "_launch_inner_runtime", lambda _platform: process)
    monkeypatch.setattr(
        smoke,
        "_capture_inner_runtime",
        lambda _process, _platform: (0, private_content, False, False),
    )
    assert smoke.main([]) == 1
    error = capsys.readouterr().err
    assert "confidential test metadata" in error
    assert smoke.FAILURE_TEXT_CANARY not in error


def test_inner_launcher_suppresses_stdout_and_isolates_the_parent_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    process = cast(subprocess.Popen[bytes], object())

    def launch(_command: Sequence[str], **kwargs: object) -> subprocess.Popen[bytes]:
        calls.append(kwargs)
        return process

    monkeypatch.setattr(subprocess, "Popen", launch)
    assert smoke._launch_inner_runtime("windows") is process
    assert calls[-1]["stdout"] == subprocess.DEVNULL
    assert calls[-1]["stderr"] == subprocess.PIPE
    assert calls[-1]["creationflags"] == int(
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
    )
    assert "start_new_session" not in calls[-1]

    assert smoke._launch_inner_runtime("posix") is process
    assert calls[-1]["start_new_session"] is True
    assert "creationflags" not in calls[-1]


def test_outer_wait_relays_interrupt_and_bounds_inner_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InterruptingProcess:
        pid = 42

        def __init__(self, *, interrupts: int = 1, timeouts: int = 0) -> None:
            self.calls = 0
            self.signals: list[int] = []
            self.interrupts = interrupts
            self.timeouts = timeouts
            self.killed = False

        def wait(self, timeout: float | None = None) -> int:
            self.calls += 1
            if self.interrupts:
                self.interrupts -= 1
                raise KeyboardInterrupt
            if self.timeouts:
                self.timeouts -= 1
                raise subprocess.TimeoutExpired("inner", timeout or 0.0)
            return 1

        def send_signal(self, value: int) -> None:
            self.signals.append(value)

        def kill(self) -> None:
            self.killed = True

    process = InterruptingProcess()
    result = smoke._wait_for_inner_runtime(
        cast(subprocess.Popen[bytes], process),
        "windows",
    )
    assert result == 1
    assert process.signals == [int(getattr(signal, "CTRL_BREAK_EVENT", 1))]

    group_signals: list[tuple[int, int]] = []
    monkeypatch.setitem(
        vars(os),
        "killpg",
        lambda process_id, signal_number: group_signals.append((process_id, signal_number)),
    )
    posix_process = InterruptingProcess()
    assert (
        smoke._wait_for_inner_runtime(
            cast(subprocess.Popen[bytes], posix_process),
            "posix",
        )
        == 1
    )
    assert group_signals == [(42, int(signal.SIGINT))]

    monkeypatch.setitem(
        vars(os),
        "killpg",
        lambda _process_id, _signal_number: (_ for _ in ()).throw(OSError("gone")),
    )
    assert (
        smoke._wait_for_inner_runtime(
            cast(subprocess.Popen[bytes], InterruptingProcess()),
            "posix",
        )
        == 1
    )

    timed_out = InterruptingProcess(timeouts=3)
    assert smoke._wait_for_inner_runtime(cast(subprocess.Popen[bytes], timed_out), "windows") == 1
    assert timed_out.signals == [int(getattr(signal, "CTRL_BREAK_EVENT", 1))] * 2
    assert timed_out.killed

    repeatedly_interrupted = InterruptingProcess(interrupts=3)
    assert (
        smoke._wait_for_inner_runtime(
            cast(subprocess.Popen[bytes], repeatedly_interrupted),
            "windows",
        )
        == 1
    )
    assert repeatedly_interrupted.killed

    class CompletedProcess:
        def wait(self, timeout: float | None = None) -> int:
            assert timeout == smoke.POLL_INTERVAL_SECONDS
            return 0

    assert (
        smoke._wait_for_inner_runtime(
            cast(subprocess.Popen[bytes], CompletedProcess()),
            "windows",
        )
        == 0
    )


def test_bounded_capture_stops_storing_after_limit_and_requests_cleanup() -> None:
    class CapturedProcess:
        pid = 42

        def __init__(self) -> None:
            self.stderr = io.BytesIO(b"x" * (smoke.MAX_CAPTURE_BYTES * 2))
            self.signals: list[int] = []

        def wait(self, timeout: float | None = None) -> int:
            return 1

        def send_signal(self, signal_number: int) -> None:
            self.signals.append(signal_number)

        def kill(self) -> None:
            pass

    process = CapturedProcess()
    return_code, content, overflowed, read_failed = smoke._capture_inner_runtime(
        cast(subprocess.Popen[bytes], process),
        "windows",
    )

    assert return_code == 1
    assert len(content) == smoke.MAX_CAPTURE_BYTES + 1
    assert overflowed
    assert not read_failed


def test_outer_interrupt_handlers_translate_and_restore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed: list[tuple[int, object]] = []
    monkeypatch.setattr(signal, "SIGBREAK", 99, raising=False)
    monkeypatch.setattr(signal, "getsignal", lambda signal_number: f"old-{signal_number}")
    monkeypatch.setattr(
        signal,
        "signal",
        lambda signal_number, handler: installed.append((signal_number, handler)),
    )

    with smoke._outer_interrupt_handlers("windows"):
        active_handlers = installed.copy()

    assert [item[0] for item in active_handlers] == [int(signal.SIGTERM), 99]
    for _signal_number, handler in active_handlers:
        with pytest.raises(KeyboardInterrupt):
            cast(Callable[[int, object], None], handler)(1, None)
    assert installed[-2:] == [(99, "old-99"), (int(signal.SIGTERM), f"old-{int(signal.SIGTERM)}")]


def test_interrupt_handlers_reuse_supervisor_signal_primitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[dev_supervisor.ShutdownSignals, dev_supervisor.PlatformFamily]] = []
    monkeypatch.setattr(
        smoke,
        "install_signal_handlers",
        lambda signals, platform: captured.append((signals, platform)),
    )
    signals = dev_supervisor.ShutdownSignals()
    smoke._install_interrupt_handlers(signals, "posix")
    assert captured == [(signals, "posix")]


def test_documentation_and_ci_use_the_exact_same_root_command() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    command = "uv run --project apps/api --locked python scripts/smoke.py"
    assert command in (repository_root / "README.md").read_text(encoding="utf-8")
    assert command in (repository_root / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )


def test_outer_capture_failure_reaps_owned_inner_before_returning(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    process = cast(subprocess.Popen[bytes], object())
    cleanup_events: list[threading.Event] = []
    monkeypatch.setattr(smoke, "_launch_inner_runtime", lambda _platform: process)

    def reap(
        actual_process: subprocess.Popen[bytes],
        _platform: dev_supervisor.PlatformFamily,
        stop_requested: threading.Event | None = None,
    ) -> int:
        assert actual_process is process
        assert stop_requested is not None and stop_requested.is_set()
        cleanup_events.append(stop_requested)
        return 1

    monkeypatch.setattr(smoke, "_wait_for_inner_runtime", reap)
    monkeypatch.setattr(
        smoke,
        "_capture_inner_runtime",
        lambda _process, _platform: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert smoke.main([]) == 1
    assert "interrupted and reaped" in capsys.readouterr().err

    monkeypatch.setattr(
        smoke,
        "_capture_inner_runtime",
        lambda _process, _platform: (_ for _ in ()).throw(RuntimeError("private failure")),
    )
    assert smoke.main([]) == 1
    error = capsys.readouterr().err
    assert "could not be launched or captured" in error
    assert "private failure" not in error
    assert len(cleanup_events) == 2


def test_posix_force_cleanup_discovers_descendants_and_has_a_kill_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def write_stat(process_id: int, parent_id: int) -> None:
        process_root = tmp_path / str(process_id)
        process_root.mkdir()
        (process_root / "stat").write_text(
            f"{process_id} (worker {process_id}) S {parent_id} {process_id} 0",
            encoding="utf-8",
        )

    write_stat(10, 1)
    write_stat(11, 10)
    write_stat(12, 11)
    write_stat(13, 1)
    assert smoke._posix_descendant_process_ids(10, proc_root=tmp_path) == (11, 12)

    killed_processes: list[tuple[int, int]] = []
    killed_groups: list[tuple[int, int]] = []
    monkeypatch.setattr(smoke, "_posix_descendant_process_ids", lambda _process_id: (11, 12))
    monkeypatch.setattr(
        os,
        "kill",
        lambda process_id, signal_number: killed_processes.append((process_id, signal_number)),
    )
    monkeypatch.setitem(
        vars(os),
        "killpg",
        lambda process_id, signal_number: killed_groups.append((process_id, signal_number)),
    )

    class ForceProcess:
        pid = 10

        def __init__(self) -> None:
            self.killed = False

        def kill(self) -> None:
            self.killed = True

    process = ForceProcess()
    smoke._force_inner_runtime(cast(subprocess.Popen[bytes], process), "posix")
    assert killed_processes == [(12, smoke._FORCE_SIGNAL), (11, smoke._FORCE_SIGNAL)]
    assert killed_groups == [(10, smoke._FORCE_SIGNAL)]
    assert not process.killed

    monkeypatch.setitem(
        vars(os),
        "killpg",
        lambda _process_id, _signal_number: (_ for _ in ()).throw(OSError("gone")),
    )
    smoke._force_inner_runtime(cast(subprocess.Popen[bytes], process), "posix")
    assert process.killed


def test_capture_without_a_pipe_requests_cleanup_and_fails_closed() -> None:
    class MissingStreamProcess:
        pid = 42
        stderr = None

        def __init__(self) -> None:
            self.signals: list[int] = []

        def wait(self, timeout: float | None = None) -> int:
            assert timeout == smoke.INNER_CLEANUP_TIMEOUT_SECONDS / 2
            return 1

        def send_signal(self, signal_number: int) -> None:
            self.signals.append(signal_number)

        def kill(self) -> None:
            pass

    process = MissingStreamProcess()
    return_code, content, overflowed, read_failed = smoke._capture_inner_runtime(
        cast(subprocess.Popen[bytes], process),
        "windows",
    )
    assert return_code == 1
    assert content == b""
    assert not overflowed
    assert read_failed
    assert process.signals == [int(getattr(signal, "CTRL_BREAK_EVENT", 1))]
