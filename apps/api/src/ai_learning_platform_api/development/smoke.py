"""Run the fixed local API-and-web cross-process smoke contract."""

from __future__ import annotations

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import FrameType
from typing import Any, BinaryIO, TextIO, cast

from ai_learning_platform_api.development.supervisor import (
    API_PORT,
    WEB_PORT,
    ChildProcess,
    ManagedProcess,
    PlatformFamily,
    ProcessTreeController,
    ServiceSpec,
    ShutdownSignals,
    TreeController,
    build_service_specs,
    install_signal_handlers,
    launch_service,
)

STARTUP_TIMEOUT_SECONDS = 45.0
REQUEST_TIMEOUT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.1
PORT_CLOSE_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 1_048_576
MAX_RESPONSE_HEADER_BYTES = 65_536
MAX_RESPONSE_HEADER_COUNT = 128
FIXED_LATENCY_SAMPLE_COUNT = 20
CONCURRENT_REQUEST_WORKERS = 4
MAX_CAPTURE_BYTES = 262_144
MAX_DIAGNOSTIC_EVENT_BYTES = 512
INNER_CLEANUP_TIMEOUT_SECONDS = 20.0
INNER_FORCE_REAP_TIMEOUT_SECONDS = 5.0
API_DIAGNOSTIC_EVENT = "api.health.request.completed"
WEB_DIAGNOSTIC_EVENT = "web.health.request.completed"
REQUEST_CANARY = "F02-REQUEST-CANARY-47C1"
CONFIGURATION_CANARY = "F02-CONFIGURATION-CANARY-47C1"
RESPONSE_DETAIL_CANARY = "F02-RESPONSE-DETAIL-CANARY-47C1"
FAILURE_TEXT_CANARY = "F02-FAILURE-TEXT-CANARY-47C1"
CONFIDENTIAL_CANARIES = (
    REQUEST_CANARY,
    CONFIGURATION_CANARY,
    RESPONSE_DETAIL_CANARY,
    FAILURE_TEXT_CANARY,
)
MALFORMED_PARENT_TRACE_ID = "1" * 32
MALFORMED_TRACEPARENT = f"00-{MALFORMED_PARENT_TRACE_ID}-{'2' * 16}-zz"
CONFIDENTIAL_MARKERS = (*CONFIDENTIAL_CANARIES, MALFORMED_TRACEPARENT)
_BROWSER_HEADER_FORBIDDEN_MARKERS = (
    API_DIAGNOSTIC_EVENT,
    WEB_DIAGNOSTIC_EVENT,
    "traceparent",
    "trace_id",
    "span_id",
    "http://127.0.0.1:8000",
    "/health/live",
    "process is live",
)
_LOWER_HEXADECIMAL = frozenset("0123456789abcdef")
_FORCE_SIGNAL = int(getattr(signal, "SIGKILL", 9))
_API_EVENT_FIELDS = frozenset(
    {
        "schema_version",
        "event",
        "service",
        "operation",
        "outcome",
        "reason",
        "parent_context",
        "trace_id",
        "span_id",
        "status_code",
        "duration_ms",
    }
)
_WEB_EVENT_FIELDS = frozenset(
    {
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
        "duration_ms",
    }
)
_PROCESS_LOG_FIELDS = frozenset(
    {"schema_version", "event", "service", "outcome", "reason", "severity"}
)


class SmokeFailure(RuntimeError):
    """A safe, expected smoke assertion or lifecycle failure."""


@dataclass(frozen=True)
class HttpResponse:
    """One bounded loopback response with normalized media type."""

    status: int
    media_type: str | None
    body: bytes
    headers: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ResourceObservation:
    """Optional dependency-free process-group resource observation."""

    process_count: int | None
    resident_bytes: int | None


@dataclass(frozen=True)
class SmokeObservation:
    """Concise, non-budget local smoke measurements."""

    api_live_ms: int
    smoke_ms: int
    shutdown_ms: int
    process_count: int | None
    resident_bytes: int | None
    next_bytes_before: int
    next_bytes_after: int
    next_bytes_delta: int


@dataclass(frozen=True)
class DiagnosticScenarioObservation:
    """Fixed real-process request and induced-failure timings."""

    correlated_requests: int
    latency_sample_count: int
    concurrent_request_count: int
    correlated_latency_p50_ms: int
    correlated_latency_p95_ms: int
    correlated_latency_max_ms: int
    induced_failure_ms: int


@dataclass(frozen=True)
class DiagnosticProofObservation:
    """Bounded evidence extracted from ephemeral child-process diagnostics."""

    correlated_requests: int
    diagnostic_event_count: int
    diagnostic_event_bytes: int
    api_diagnostic_bytes: int
    web_diagnostic_bytes: int
    captured_stderr_bytes: int


@dataclass(frozen=True)
class InnerSmokeObservation:
    """The private child result consumed by the outer diagnostic gate."""

    runtime: SmokeObservation
    scenario: DiagnosticScenarioObservation


@dataclass(frozen=True)
class CompleteSmokeObservation:
    """The public aggregate emitted only after captured diagnostics pass."""

    runtime: SmokeObservation
    scenario: DiagnosticScenarioObservation
    diagnostics: DiagnosticProofObservation


Requester = Callable[[int, str], HttpResponse]
MetadataRequester = Callable[[int, str, Mapping[str, str]], HttpResponse]
Launcher = Callable[[ServiceSpec, PlatformFamily], ChildProcess]
PortProbe = Callable[[int], bool]
ResourceObserver = Callable[[Sequence[ManagedProcess]], ResourceObservation]


def _write(stream: TextIO, message: str) -> None:
    print(f"[smoke] {message}", file=stream, flush=True)


def request_loopback_with_headers(
    port: int,
    path: str,
    headers: Mapping[str, str],
) -> HttpResponse:
    """Perform one bounded loopback request with caller-owned literal headers."""

    connection = http.client.HTTPConnection(
        "127.0.0.1",
        port,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    try:
        connection.request("GET", path, headers=dict(headers))
        response = connection.getresponse()
        response_headers = tuple((name.lower(), value) for name, value in response.getheaders())
        if len(response_headers) > MAX_RESPONSE_HEADER_COUNT:
            raise SmokeFailure(f"{path} returned too many response headers")
        response_header_bytes = _serialize_response_headers(response_headers)
        if len(response_header_bytes) > MAX_RESPONSE_HEADER_BYTES:
            raise SmokeFailure(f"{path} response headers exceed the byte limit")
        content_length = response.getheader("content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError as exc:
                raise SmokeFailure(f"{path} returned an invalid content length") from exc
            if declared_length < 0 or declared_length > MAX_RESPONSE_BYTES:
                raise SmokeFailure(f"{path} response exceeds the byte limit")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise SmokeFailure(f"{path} response exceeds the byte limit")
        media_type = response.getheader("content-type")
        normalized_media_type = (
            media_type.split(";", 1)[0].strip().lower() if media_type is not None else None
        )
        return HttpResponse(
            status=response.status,
            media_type=normalized_media_type,
            body=body,
            headers=response_headers,
        )
    finally:
        connection.close()


def request_loopback(port: int, path: str) -> HttpResponse:
    """Perform one fixed, bounded HTTP request without proxy or redirect support."""

    return request_loopback_with_headers(port, path, {"Accept": "application/json"})


def _serialize_response_headers(headers: Sequence[tuple[str, str]]) -> bytes:
    try:
        return b"".join(f"{name}:{value}\n".encode("latin-1") for name, value in headers)
    except UnicodeEncodeError:
        raise SmokeFailure("response headers used an invalid character encoding") from None


def _port_is_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.1):
            return True
    except OSError:
        return False


def _decode_json(response: HttpResponse, *, path: str) -> object:
    if response.status != 200:
        raise SmokeFailure(f"{path} returned HTTP {response.status}")
    if response.media_type != "application/json":
        raise SmokeFailure(f"{path} returned an unexpected media type")
    try:
        return json.loads(response.body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeFailure(f"{path} returned invalid JSON") from exc


def _assert_health(response: HttpResponse, *, path: str, detail: str) -> None:
    body = _decode_json(response, path=path)
    expected = {"status": "ok", "detail": detail}
    if body != expected:
        raise SmokeFailure(f"{path} did not match the expected health contract")
    _assert_confidential_response(response, surface=f"{path} response")


def _assert_openapi(response: HttpResponse, canonical_document: object) -> None:
    body = _decode_json(response, path="/openapi.json")
    if body != canonical_document:
        raise SmokeFailure("/openapi.json does not match the canonical artifact")


def _assert_available_web(response: HttpResponse) -> None:
    path = "/"
    if response.status != 200:
        raise SmokeFailure(f"{path} returned HTTP {response.status}")
    if response.media_type != "text/html":
        raise SmokeFailure(f"{path} returned an unexpected media type")
    try:
        html = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SmokeFailure(f"{path} returned invalid UTF-8") from exc

    required = (
        'data-api-state="available"',
        "Local API available",
        'aria-labelledby="api-integration-heading"',
        'role="status"',
        'aria-atomic="true"',
        'aria-labelledby="api-status-label"',
        "This status reports local process liveness only.",
    )
    if any(value not in html for value in required):
        raise SmokeFailure("/ did not render the expected accessible available state")

    forbidden = (
        'data-api-state="unavailable"',
        'data-api-state="invalid-response"',
        "Local API unavailable",
        "Local API response invalid",
        "AI_PLATFORM_API_BASE_URL",
        "http://127.0.0.1:8000",
        "/health/live",
        "process is live",
        API_DIAGNOSTIC_EVENT,
        WEB_DIAGNOSTIC_EVENT,
        "traceparent",
        "trace_id",
        "span_id",
    )
    if any(value in html for value in forbidden):
        raise SmokeFailure("/ exposed a forbidden state or server-only value")
    _assert_browser_response_confidential(response, surface="available browser output")


def _assert_unavailable_web(response: HttpResponse) -> None:
    path = "/"
    if response.status != 200:
        raise SmokeFailure(f"{path} returned HTTP {response.status}")
    if response.media_type != "text/html":
        raise SmokeFailure(f"{path} returned an unexpected media type")
    try:
        html = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SmokeFailure(f"{path} returned invalid UTF-8") from exc

    required = (
        'data-api-state="unavailable"',
        "Local API unavailable",
        'aria-labelledby="api-integration-heading"',
        'role="status"',
        'aria-atomic="true"',
        'aria-labelledby="api-status-label"',
        "This status reports local process liveness only.",
    )
    if any(value not in html for value in required):
        raise SmokeFailure("/ did not render the expected accessible unavailable state")

    forbidden = (
        'data-api-state="available"',
        'data-api-state="invalid-response"',
        "Local API available",
        "Local API response invalid",
        "AI_PLATFORM_API_BASE_URL",
        "http://127.0.0.1:8000",
        "/health/live",
        API_DIAGNOSTIC_EVENT,
        WEB_DIAGNOSTIC_EVENT,
        "traceparent",
        "trace_id",
        "span_id",
    )
    if any(value in html for value in forbidden):
        raise SmokeFailure("/ exposed a forbidden state or server-only value")
    _assert_browser_response_confidential(response, surface="unavailable browser output")


def _assert_invalid_web(response: HttpResponse) -> None:
    path = "/"
    if response.status != 200:
        raise SmokeFailure(f"{path} returned HTTP {response.status}")
    if response.media_type != "text/html":
        raise SmokeFailure(f"{path} returned an unexpected media type")
    try:
        html = response.body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SmokeFailure(f"{path} returned invalid UTF-8") from exc

    required = (
        'data-api-state="invalid-response"',
        "Local API response invalid",
        'aria-labelledby="api-integration-heading"',
        'role="status"',
        'aria-atomic="true"',
        'aria-labelledby="api-status-label"',
        "This status reports local process liveness only.",
    )
    if any(value not in html for value in required):
        raise SmokeFailure("/ did not render the expected accessible invalid-response state")

    forbidden = (
        'data-api-state="available"',
        'data-api-state="unavailable"',
        "Local API available",
        "Local API unavailable",
        "AI_PLATFORM_API_BASE_URL",
        "http://127.0.0.1:8000",
        "/health/live",
        API_DIAGNOSTIC_EVENT,
        WEB_DIAGNOSTIC_EVENT,
        "traceparent",
        "trace_id",
        "span_id",
    )
    if any(value in html for value in forbidden):
        raise SmokeFailure("/ exposed a forbidden state or server-only value")
    _assert_browser_response_confidential(response, surface="invalid browser output")


def _assert_confidential_surface(content: bytes, *, surface: str) -> None:
    if any(marker.encode("ascii") in content for marker in CONFIDENTIAL_MARKERS):
        raise SmokeFailure(f"{surface} exposed confidential test metadata")


def _assert_confidential_response(response: HttpResponse, *, surface: str) -> None:
    _assert_confidential_surface(response.body, surface=surface)
    _assert_confidential_surface(
        _serialize_response_headers(response.headers),
        surface=f"{surface} headers",
    )


def _assert_browser_response_confidential(response: HttpResponse, *, surface: str) -> None:
    _assert_confidential_response(response, surface=surface)
    header_bytes = _serialize_response_headers(response.headers).lower()
    if any(marker.encode("ascii") in header_bytes for marker in _BROWSER_HEADER_FORBIDDEN_MARKERS):
        raise SmokeFailure(f"{surface} headers exposed a server-only value")


def _prepare_diagnostic_services(
    services: Sequence[ServiceSpec],
) -> tuple[ServiceSpec, ...]:
    prepared: list[ServiceSpec] = []
    for service in services:
        environment = service.environment.copy()
        environment.update(
            {
                "OTEL_SERVICE_NAME": CONFIGURATION_CANARY,
                "OTEL_RESOURCE_ATTRIBUTES": f"f02.canary={CONFIGURATION_CANARY}",
            }
        )
        prepared.append(
            replace(
                service,
                environment=environment,
            )
        )
    return tuple(prepared)


def _validate_captured_log(content: bytes) -> None:
    if len(content) > MAX_CAPTURE_BYTES:
        raise SmokeFailure("captured diagnostic output exceeded the byte limit")
    _assert_confidential_surface(content, surface="captured diagnostic output")
    lowered = content.lower()
    forbidden = (
        (b"http://", "raw_url"),
        (b"https://", "raw_url"),
        (b"/health/live", "raw_health_path"),
        (b"authorization", "raw_authorization_header"),
        (b"cookie", "raw_cookie_header"),
        (b"traceparent", "raw_trace_header"),
        (b"x-f02-canary", "raw_canary_header"),
        (b"traceback", "raw_exception"),
    )
    for value, reason in forbidden:
        if value in lowered:
            raise SmokeFailure(f"captured diagnostic output contained forbidden category {reason}")


def _extract_diagnostic_events(content: bytes) -> list[tuple[dict[str, object], int]]:
    events: list[tuple[dict[str, object], int]] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        contains_marker = any(
            marker in line
            for marker in (API_DIAGNOSTIC_EVENT.encode(), WEB_DIAGNOSTIC_EVENT.encode())
        )
        if not line.startswith(b"{"):
            if contains_marker:
                raise SmokeFailure("captured diagnostic output contained a corrupt event")
            continue
        try:
            value: object = json.loads(line, object_pairs_hook=_unique_json_object)
        except (UnicodeDecodeError, json.JSONDecodeError):
            if contains_marker or b'"event"' in line:
                raise SmokeFailure("captured diagnostic output contained invalid JSON") from None
            continue
        if not isinstance(value, dict):
            if contains_marker:
                raise SmokeFailure("captured diagnostic output contained a corrupt event")
            continue
        event_name = value.get("event")
        if event_name == "process.log":
            _validate_process_log(cast(dict[str, object], value))
            continue
        if event_name not in {API_DIAGNOSTIC_EVENT, WEB_DIAGNOSTIC_EVENT}:
            if contains_marker or event_name is not None:
                raise SmokeFailure("captured diagnostic output contained a corrupt event")
            continue
        event_bytes = len(raw_line)
        if event_bytes > MAX_DIAGNOSTIC_EVENT_BYTES:
            raise SmokeFailure("a diagnostic event exceeded the byte limit")
        events.append((cast(dict[str, object], value), event_bytes))
    return events


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise SmokeFailure("captured diagnostic output contained a duplicate JSON field")
        value[key] = item
    return value


def _validate_process_log(event: Mapping[str, object]) -> None:
    if (
        frozenset(event) != _PROCESS_LOG_FIELDS
        or type(event.get("schema_version")) is not int
        or event.get("schema_version") != 1
        or event.get("event") != "process.log"
        or event.get("service") != "api"
        or event.get("outcome") not in {"status", "error"}
        or event.get("reason") != "unstructured_suppressed"
        or event.get("severity") not in {"debug", "info", "warning", "error", "critical"}
    ):
        raise SmokeFailure("captured process output violated its fixed field allowlist")


def _required_string(event: Mapping[str, object], field: str) -> str:
    value = event.get(field)
    if not isinstance(value, str):
        raise SmokeFailure("a diagnostic event used an invalid field type")
    return value


def _required_integer(event: Mapping[str, object], field: str) -> int:
    value = event.get(field)
    if type(value) is not int:
        raise SmokeFailure("a diagnostic event used an invalid field type")
    return value


def _validate_identifier(value: str, *, length: int) -> None:
    if (
        len(value) != length
        or value == "0" * length
        or any(character not in _LOWER_HEXADECIMAL for character in value)
    ):
        raise SmokeFailure("a diagnostic event used an invalid trace identifier")


def _validate_event(
    event: Mapping[str, object],
    *,
    event_name: str,
) -> tuple[str, str]:
    expected_fields = _API_EVENT_FIELDS if event_name == API_DIAGNOSTIC_EVENT else _WEB_EVENT_FIELDS
    if frozenset(event) != expected_fields:
        raise SmokeFailure("a diagnostic event violated the fixed field allowlist")
    if _required_integer(event, "schema_version") != 1:
        raise SmokeFailure("a diagnostic event used an unsupported schema")
    if _required_string(event, "event") != event_name:
        raise SmokeFailure("a diagnostic event appeared in the wrong service output")
    expected_service = "api" if event_name == API_DIAGNOSTIC_EVENT else "web"
    if _required_string(event, "service") != expected_service:
        raise SmokeFailure("a diagnostic event used an invalid service")
    if _required_string(event, "operation") != "health_live":
        raise SmokeFailure("a diagnostic event used an invalid operation")
    trace_id = _required_string(event, "trace_id")
    span_id = _required_string(event, "span_id")
    _validate_identifier(trace_id, length=32)
    _validate_identifier(span_id, length=16)
    status_code = _required_integer(event, "status_code")
    duration_ms = _required_integer(event, "duration_ms")
    if status_code != 0 and not 100 <= status_code <= 599:
        raise SmokeFailure("a diagnostic event used an invalid status code")
    if duration_ms < 0:
        raise SmokeFailure("a diagnostic event used an invalid duration")
    return trace_id, span_id


def _assert_diagnostic_proof(
    content: bytes,
    *,
    correlated_requests: int,
) -> DiagnosticProofObservation:
    raw_events = _extract_diagnostic_events(content)
    api_raw = [item for item in raw_events if item[0].get("event") == API_DIAGNOSTIC_EVENT]
    web_raw = [item for item in raw_events if item[0].get("event") == WEB_DIAGNOSTIC_EVENT]

    api_events = [event for event, _size in api_raw]
    web_events = [event for event, _size in web_raw]
    if len(api_events) != correlated_requests + 3 or len(web_events) != correlated_requests + 3:
        raise SmokeFailure("cross-process diagnostic event volume was not exact")

    api_ids = [_validate_event(event, event_name=API_DIAGNOSTIC_EVENT) for event in api_events]
    web_ids = [_validate_event(event, event_name=WEB_DIAGNOSTIC_EVENT) for event in web_events]
    if len({trace_id for trace_id, _span_id in api_ids}) != len(api_ids):
        raise SmokeFailure("API request context leaked or was reused")
    if len({span_id for _trace_id, span_id in api_ids}) != len(api_ids):
        raise SmokeFailure("API span identifiers were reused")
    if len({trace_id for trace_id, _span_id in web_ids}) != len(web_ids):
        raise SmokeFailure("web request context leaked or was reused")
    if len({span_id for _trace_id, span_id in web_ids}) != len(web_ids):
        raise SmokeFailure("web span identifiers were reused")

    valid_api = [event for event in api_events if event.get("parent_context") == "valid"]
    absent_api = [event for event in api_events if event.get("parent_context") == "absent"]
    invalid_api = [event for event in api_events if event.get("parent_context") == "invalid"]
    if not (
        len(valid_api) == correlated_requests and len(absent_api) == 2 and len(invalid_api) == 1
    ):
        raise SmokeFailure("cross-process diagnostic classifications were not exact")

    for event in api_events:
        if (
            event.get("outcome") != "ok"
            or event.get("reason") != "ok"
            or event.get("status_code") != 200
        ):
            raise SmokeFailure("API diagnostic outcome was not bounded and exact")
    valid_api_by_trace = {
        _required_string(event, "trace_id"): _required_string(event, "span_id")
        for event in valid_api
    }
    web_by_trace = {
        _required_string(event, "trace_id"): _required_string(event, "span_id")
        for event in web_events
    }
    if not valid_api_by_trace.keys() <= web_by_trace.keys():
        raise SmokeFailure("web and API trace identifiers did not correlate")
    matched_web = [
        event for event in web_events if _required_string(event, "trace_id") in valid_api_by_trace
    ]
    unmatched_web = [
        event
        for event in web_events
        if _required_string(event, "trace_id") not in valid_api_by_trace
    ]
    for event in matched_web:
        if (
            event.get("outcome") != "ok"
            or event.get("result") != "available"
            or event.get("reason") != "ok"
            or event.get("status_code") != 200
        ):
            raise SmokeFailure("correlated web diagnostic outcome was not exact")
    fixture_combinations = {
        (
            event.get("outcome"),
            event.get("result"),
            event.get("reason"),
            event.get("status_code"),
        )
        for event in unmatched_web
    }
    if fixture_combinations != {
        ("ok", "available", "ok", 200),
        ("error", "unavailable", "http_status", 503),
        ("error", "invalid_response", "invalid_json", 200),
    }:
        raise SmokeFailure("induced web diagnostic outcomes were not exact")
    if any(
        valid_api_by_trace[trace_id] == web_span_id
        for trace_id, web_span_id in web_by_trace.items()
        if trace_id in valid_api_by_trace
    ):
        raise SmokeFailure("web and API spans were not distinct")

    invalid_trace = _required_string(invalid_api[0], "trace_id")
    if invalid_trace == MALFORMED_PARENT_TRACE_ID:
        raise SmokeFailure("malformed incoming context was not replaced with a safe root")
    non_parent_api_traces = {
        _required_string(event, "trace_id") for event in (*absent_api, *invalid_api)
    }
    if non_parent_api_traces & web_by_trace.keys():
        raise SmokeFailure("safe-root API context leaked into a web request")

    diagnostic_event_bytes = sum(size for _event, size in raw_events)
    return DiagnosticProofObservation(
        correlated_requests=correlated_requests,
        diagnostic_event_count=len(api_events) + len(web_events),
        diagnostic_event_bytes=diagnostic_event_bytes,
        api_diagnostic_bytes=sum(size for _event, size in api_raw),
        web_diagnostic_bytes=sum(size for _event, size in web_raw),
        captured_stderr_bytes=len(content),
    )


def _nearest_rank(values: Sequence[int], percentile: float) -> int:
    if not values:
        raise SmokeFailure("the fixed latency sample was empty")
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * percentile + 0.999999))
    return ordered[min(rank - 1, len(ordered) - 1)]


def _nonnegative_integer(value: object) -> int:
    if type(value) is not int or value < 0:
        raise SmokeFailure("inner smoke observation used an invalid measurement")
    return value


def _optional_nonnegative_integer(value: object) -> int | None:
    if value is None:
        return None
    return _nonnegative_integer(value)


def _extract_inner_observation(content: bytes) -> InnerSmokeObservation:
    prefix = b"[smoke-inner] passed "
    result_lines = [line[len(prefix) :] for line in content.splitlines() if line.startswith(prefix)]
    if len(result_lines) != 1:
        raise SmokeFailure("inner smoke observation was missing or duplicated")
    try:
        value: object = json.loads(result_lines[0], object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SmokeFailure("inner smoke observation was invalid") from None
    if not isinstance(value, dict) or frozenset(value) != {"runtime", "scenario"}:
        raise SmokeFailure("inner smoke observation violated its fixed schema")
    runtime_value = value.get("runtime")
    scenario_value = value.get("scenario")
    if not isinstance(runtime_value, dict) or frozenset(runtime_value) != {
        "api_live_ms",
        "smoke_ms",
        "shutdown_ms",
        "process_count",
        "resident_bytes",
        "next_bytes_before",
        "next_bytes_after",
        "next_bytes_delta",
    }:
        raise SmokeFailure("inner runtime observation violated its fixed schema")
    if not isinstance(scenario_value, dict) or frozenset(scenario_value) != {
        "correlated_requests",
        "latency_sample_count",
        "concurrent_request_count",
        "correlated_latency_p50_ms",
        "correlated_latency_p95_ms",
        "correlated_latency_max_ms",
        "induced_failure_ms",
    }:
        raise SmokeFailure("inner diagnostic observation violated its fixed schema")

    next_before = _nonnegative_integer(runtime_value.get("next_bytes_before"))
    next_after = _nonnegative_integer(runtime_value.get("next_bytes_after"))
    next_delta = runtime_value.get("next_bytes_delta")
    if type(next_delta) is not int or next_delta != next_after - next_before:
        raise SmokeFailure("inner cache observation was inconsistent")
    runtime = SmokeObservation(
        api_live_ms=_nonnegative_integer(runtime_value.get("api_live_ms")),
        smoke_ms=_nonnegative_integer(runtime_value.get("smoke_ms")),
        shutdown_ms=_nonnegative_integer(runtime_value.get("shutdown_ms")),
        process_count=_optional_nonnegative_integer(runtime_value.get("process_count")),
        resident_bytes=_optional_nonnegative_integer(runtime_value.get("resident_bytes")),
        next_bytes_before=next_before,
        next_bytes_after=next_after,
        next_bytes_delta=next_delta,
    )
    scenario = DiagnosticScenarioObservation(
        correlated_requests=_nonnegative_integer(scenario_value.get("correlated_requests")),
        latency_sample_count=_nonnegative_integer(scenario_value.get("latency_sample_count")),
        concurrent_request_count=_nonnegative_integer(
            scenario_value.get("concurrent_request_count")
        ),
        correlated_latency_p50_ms=_nonnegative_integer(
            scenario_value.get("correlated_latency_p50_ms")
        ),
        correlated_latency_p95_ms=_nonnegative_integer(
            scenario_value.get("correlated_latency_p95_ms")
        ),
        correlated_latency_max_ms=_nonnegative_integer(
            scenario_value.get("correlated_latency_max_ms")
        ),
        induced_failure_ms=_nonnegative_integer(scenario_value.get("induced_failure_ms")),
    )
    if (
        scenario.latency_sample_count != FIXED_LATENCY_SAMPLE_COUNT
        or scenario.concurrent_request_count != CONCURRENT_REQUEST_WORKERS
        or scenario.correlated_requests != FIXED_LATENCY_SAMPLE_COUNT + 1
        or not (
            scenario.correlated_latency_p50_ms
            <= scenario.correlated_latency_p95_ms
            <= scenario.correlated_latency_max_ms
        )
    ):
        raise SmokeFailure("inner fixed latency sample was inconsistent")
    return InnerSmokeObservation(runtime=runtime, scenario=scenario)


def _directory_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _measure_directory_bytes(path: Path) -> int:
    try:
        return _directory_bytes(path)
    except OSError:
        raise SmokeFailure("development cache could not be measured") from None


def _read_linux_process_group(stat_text: str) -> int:
    closing_parenthesis = stat_text.rfind(")")
    if closing_parenthesis < 0:
        raise ValueError("invalid proc stat")
    fields = stat_text[closing_parenthesis + 1 :].split()
    if len(fields) < 3:
        raise ValueError("invalid proc stat")
    return int(fields[2])


def observe_linux_resources(
    processes: Sequence[ManagedProcess],
    *,
    proc_root: Path = Path("/proc"),
    page_size: int | None = None,
) -> ResourceObservation:
    """Sum active members and resident bytes for the owned POSIX groups."""

    if os.name == "nt" and proc_root == Path("/proc"):
        return ResourceObservation(process_count=None, resident_bytes=None)
    if not proc_root.is_dir():
        return ResourceObservation(process_count=None, resident_bytes=None)
    groups = {item.process.pid for item in processes}
    if page_size is not None:
        actual_page_size = page_size
    else:
        system_configuration = cast(Callable[[str], int], vars(os)["sysconf"])
        actual_page_size = system_configuration("SC_PAGE_SIZE")
    process_count = 0
    resident_pages = 0
    for item in proc_root.iterdir():
        if not item.name.isdecimal():
            continue
        try:
            group = _read_linux_process_group((item / "stat").read_text(encoding="utf-8"))
            statm_fields = (item / "statm").read_text(encoding="utf-8").split()
            resident = int(statm_fields[1])
        except (FileNotFoundError, IndexError, OSError, ValueError):
            continue
        if group in groups:
            process_count += 1
            resident_pages += resident
    return ResourceObservation(
        process_count=process_count,
        resident_bytes=resident_pages * actual_page_size,
    )


class _FailureProofServer(ThreadingHTTPServer):
    """Ephemeral two-response loopback stub for confidential failure proof."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self) -> None:
        self._response_index = 0
        self._response_lock = threading.Lock()
        super().__init__(("127.0.0.1", API_PORT), _FailureProofHandler)

    def next_response_index(self) -> int:
        with self._response_lock:
            index = self._response_index
            self._response_index += 1
            return index

    @property
    def response_count(self) -> int:
        with self._response_lock:
            return self._response_index

    def handle_error(self, _request: object, _client_address: object) -> None:
        return


class _FailureProofHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        server = cast(_FailureProofServer, self.server)
        if self.path != "/health/live":
            self._write_response(404, b"not found", content_type="text/plain")
            return
        response_index = server.next_response_index()
        if response_index == 0:
            body = json.dumps(
                {"status": "ok", "detail": RESPONSE_DETAIL_CANARY},
                separators=(",", ":"),
            ).encode("utf-8")
            self._write_response(200, body, content_type="application/json")
            return
        if response_index == 1:
            self._write_response(
                503,
                FAILURE_TEXT_CANARY.encode("ascii"),
                content_type="text/plain",
                reason=FAILURE_TEXT_CANARY,
                extra_header=("X-F02-Failure", FAILURE_TEXT_CANARY),
            )
            return
        self._write_response(
            200,
            f'{{"status":"ok","detail":"{RESPONSE_DETAIL_CANARY}"'.encode("ascii"),
            content_type="application/json",
        )

    def _write_response(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str,
        reason: str | None = None,
        extra_header: tuple[str, str] | None = None,
    ) -> None:
        self.send_response(status, reason)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if extra_header is not None:
            self.send_header(*extra_header)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: object) -> None:
        return


class RuntimeSmoke:
    """Own, assert, measure, and clean the fixed cross-process runtime."""

    def __init__(
        self,
        *,
        repository_root: Path | None = None,
        services: Sequence[ServiceSpec] | None = None,
        platform: PlatformFamily | None = None,
        launcher: Launcher = launch_service,
        requester: Requester = request_loopback,
        metadata_requester: MetadataRequester = request_loopback_with_headers,
        port_probe: PortProbe = _port_is_open,
        resource_observer: ResourceObserver = observe_linux_resources,
        controller: TreeController | None = None,
        signals: ShutdownSignals | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        output: TextIO = sys.stdout,
    ) -> None:
        self._repository_root = repository_root or Path(__file__).resolve().parents[5]
        self._services = tuple(services) if services is not None else None
        self._platform = platform or ("windows" if os.name == "nt" else "posix")
        self._launcher = launcher
        self._requester = requester
        self._metadata_requester = metadata_requester
        self._port_probe = port_probe
        self._resource_observer = resource_observer
        self._controller = controller or ProcessTreeController(self._platform)
        self._signals = signals or ShutdownSignals()
        self._monotonic = monotonic
        self._sleep = sleep
        self._output = output

    def _ensure_running(self, processes: Sequence[ManagedProcess]) -> None:
        if self._signals.requested.is_set():
            raise SmokeFailure("smoke interrupted")
        for item in processes:
            code = item.process.poll()
            if code is not None:
                raise SmokeFailure(
                    f"{item.service.name} exited before smoke completion (code {code})"
                )

    def _wait_for_live(self, processes: Sequence[ManagedProcess], deadline: float) -> None:
        while True:
            self._ensure_running(processes)
            if self._monotonic() >= deadline:
                raise SmokeFailure("API liveness did not become available before the deadline")
            try:
                response = self._requester(API_PORT, "/health/live")
            except (ConnectionError, TimeoutError, OSError, http.client.HTTPException):
                if self._monotonic() >= deadline:
                    raise SmokeFailure(
                        "API liveness did not become available before the deadline"
                    ) from None
                self._sleep(POLL_INTERVAL_SECONDS)
                continue
            self._ensure_running(processes)
            if self._monotonic() >= deadline:
                raise SmokeFailure("API liveness did not become available before the deadline")
            _assert_health(response, path="/health/live", detail="process is live")
            return

    def _wait_for_web(self, processes: Sequence[ManagedProcess], deadline: float) -> None:
        while True:
            self._ensure_running(processes)
            if self._monotonic() >= deadline:
                raise SmokeFailure("web availability did not become available before the deadline")
            try:
                response = self._requester(WEB_PORT, "/")
            except (ConnectionError, TimeoutError, OSError, http.client.HTTPException):
                if self._monotonic() >= deadline:
                    raise SmokeFailure(
                        "web availability did not become available before the deadline"
                    ) from None
                self._sleep(POLL_INTERVAL_SECONDS)
                continue
            self._ensure_running(processes)
            if self._monotonic() >= deadline:
                raise SmokeFailure("web availability did not become available before the deadline")
            _assert_available_web(response)
            return

    def _wait_for_closed_ports(self) -> bool:
        deadline = self._monotonic() + PORT_CLOSE_TIMEOUT_SECONDS
        while self._port_probe(API_PORT) or self._port_probe(WEB_PORT):
            if self._monotonic() >= deadline:
                return False
            self._sleep(POLL_INTERVAL_SECONDS)
        return True

    def _wait_for_port_closed(self, port: int) -> bool:
        deadline = self._monotonic() + PORT_CLOSE_TIMEOUT_SECONDS
        while self._port_probe(port):
            if self._monotonic() >= deadline:
                return False
            self._sleep(POLL_INTERVAL_SECONDS)
        return True

    def _request_once(self, port: int, path: str, *, safe_path: str | None = None) -> HttpResponse:
        try:
            return self._requester(port, path)
        except (ConnectionError, TimeoutError, OSError, http.client.HTTPException):
            raise SmokeFailure(f"{safe_path or path} request failed") from None

    def _request_with_metadata(
        self,
        port: int,
        path: str,
        headers: Mapping[str, str],
        *,
        safe_path: str,
    ) -> HttpResponse:
        try:
            return self._metadata_requester(port, path, headers)
        except (ConnectionError, TimeoutError, OSError, http.client.HTTPException):
            raise SmokeFailure(f"{safe_path} request failed") from None

    def _exercise_concurrent_health_requests(self) -> list[int]:
        start_barrier = threading.Barrier(CONCURRENT_REQUEST_WORKERS)

        def invoke(index: int) -> tuple[int, int, float, float]:
            if index < CONCURRENT_REQUEST_WORKERS:
                try:
                    start_barrier.wait(timeout=REQUEST_TIMEOUT_SECONDS)
                except threading.BrokenBarrierError:
                    raise SmokeFailure("concurrent request cohort could not start") from None
            started = self._monotonic()
            response = self._request_with_metadata(
                WEB_PORT,
                "/",
                {
                    "Accept": "text/html",
                    "X-F02-Request-Canary": REQUEST_CANARY,
                    "X-F02-Response-Detail-Canary": RESPONSE_DETAIL_CANARY,
                    "X-F02-Probe-Index": str(index),
                },
                safe_path="/",
            )
            completed = self._monotonic()
            elapsed_ms = round((completed - started) * 1000)
            _assert_available_web(response)
            return index, elapsed_ms, started, completed

        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUEST_WORKERS) as executor:
            observations = list(executor.map(invoke, range(FIXED_LATENCY_SAMPLE_COUNT)))
        concurrent_cohort = [item for item in observations if item[0] < CONCURRENT_REQUEST_WORKERS]
        if len(concurrent_cohort) != CONCURRENT_REQUEST_WORKERS or max(
            item[2] for item in concurrent_cohort
        ) >= min(item[3] for item in concurrent_cohort):
            raise SmokeFailure("concurrent requests did not overlap in flight")
        return [item[1] for item in observations]

    def _exercise_malformed_context(self) -> None:
        response = self._request_with_metadata(
            API_PORT,
            "/health/live",
            {
                "Accept": "application/json",
                "Authorization": f"Bearer {REQUEST_CANARY}",
                "Cookie": f"f02={REQUEST_CANARY}",
                "Traceparent": MALFORMED_TRACEPARENT,
                "X-F02-Canary": REQUEST_CANARY,
            },
            safe_path="/health/live",
        )
        _assert_health(response, path="/health/live", detail="process is live")
        _assert_confidential_surface(response.body, surface="API health response")

    def _exercise_absent_context(self) -> None:
        response = self._request_with_metadata(
            API_PORT,
            "/health/live",
            {
                "Accept": "application/json",
                "X-F02-Request-Canary": REQUEST_CANARY,
            },
            safe_path="/health/live",
        )
        _assert_health(response, path="/health/live", detail="process is live")
        _assert_confidential_surface(response.body, surface="API health response")

    def _exercise_induced_failures(self, managed: list[ManagedProcess]) -> int:
        api_process = next(
            (item for item in managed if item.service.name == "api"),
            None,
        )
        if api_process is None:
            raise SmokeFailure("owned API process was unavailable for the failure proof")
        started = self._monotonic()
        stop_signals = ShutdownSignals()
        try:
            stopped = self._controller.shutdown((api_process,), stop_signals, self._output)
        except OSError:
            stopped = False
        if not stopped or not self._wait_for_port_closed(API_PORT):
            raise SmokeFailure("induced API shutdown did not complete")
        managed.remove(api_process)
        self._ensure_running(managed)
        try:
            server = _FailureProofServer()
        except OSError:
            raise SmokeFailure("failure-proof loopback stub could not start") from None
        thread = threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": POLL_INTERVAL_SECONDS},
            name="f02-failure-proof",
            daemon=True,
        )
        thread.start()
        try:
            available_response = self._request_with_metadata(
                WEB_PORT,
                "/",
                {
                    "Accept": "text/html",
                    "X-F02-Response-Detail-Canary": RESPONSE_DETAIL_CANARY,
                },
                safe_path="/",
            )
            _assert_available_web(available_response)
            unavailable_response = self._request_with_metadata(
                WEB_PORT,
                "/",
                {
                    "Accept": "text/html",
                    "X-F02-Failure-Text-Canary": FAILURE_TEXT_CANARY,
                },
                safe_path="/",
            )
            _assert_unavailable_web(unavailable_response)
            invalid_response = self._request_with_metadata(
                WEB_PORT,
                "/",
                {
                    "Accept": "text/html",
                    "X-F02-Response-Detail-Canary": RESPONSE_DETAIL_CANARY,
                },
                safe_path="/",
            )
            _assert_invalid_web(invalid_response)
            if server.response_count != 3:
                raise SmokeFailure("failure-proof loopback request volume was not exact")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=PORT_CLOSE_TIMEOUT_SECONDS)
        if thread.is_alive() or not self._wait_for_port_closed(API_PORT):
            raise SmokeFailure("failure-proof loopback cleanup did not complete")
        self._ensure_running(managed)
        return round((self._monotonic() - started) * 1000)

    def run(self) -> SmokeObservation:
        """Run the accepted F01 runtime contract without the F02 gate."""

        observation, _scenario = self._run(diagnostic_proof=False)
        return observation

    def run_diagnostic(self) -> InnerSmokeObservation:
        """Run the F01 contract plus the bounded F02-03 real-process scenario."""

        observation, scenario = self._run(diagnostic_proof=True)
        if scenario is None:
            raise SmokeFailure("diagnostic scenario did not produce an observation")
        return InnerSmokeObservation(runtime=observation, scenario=scenario)

    def _run(
        self,
        *,
        diagnostic_proof: bool,
    ) -> tuple[SmokeObservation, DiagnosticScenarioObservation | None]:
        start = self._monotonic()
        next_root = self._repository_root / "apps" / "web" / ".next" / "dev"
        next_before = _measure_directory_bytes(next_root)
        managed: list[ManagedProcess] = []
        failure: SmokeFailure | None = None
        resource = ResourceObservation(process_count=None, resident_bytes=None)
        api_live_ms = 0
        smoke_ms = 0
        scenario: DiagnosticScenarioObservation | None = None

        if self._port_probe(API_PORT) or self._port_probe(WEB_PORT):
            raise SmokeFailure("fixed smoke ports must be unused before launch")

        services = self._services if self._services is not None else build_service_specs()
        if diagnostic_proof:
            services = _prepare_diagnostic_services(services)
        try:
            for service in services:
                _write(self._output, f"launching {service.name} process")
                try:
                    process = self._launcher(service, self._platform)
                except OSError as exc:
                    raise SmokeFailure(f"failed to launch {service.name}") from exc
                managed.append(ManagedProcess(service=service, process=process))

            deadline = start + STARTUP_TIMEOUT_SECONDS
            self._wait_for_live(managed, deadline)
            api_live_ms = round((self._monotonic() - start) * 1000)
            _assert_health(
                self._request_once(API_PORT, "/health/ready"),
                path="/health/ready",
                detail="configuration is valid; no external dependency checks are performed",
            )
            try:
                canonical_document = json.loads(
                    (
                        self._repository_root / "apps" / "api" / "openapi" / "health.openapi.json"
                    ).read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                raise SmokeFailure("canonical OpenAPI artifact is unavailable or invalid") from None
            _assert_openapi(self._request_once(API_PORT, "/openapi.json"), canonical_document)
            self._wait_for_web(managed, deadline)
            self._ensure_running(managed)
            latencies: list[int] = []
            if diagnostic_proof:
                latencies = self._exercise_concurrent_health_requests()
                self._ensure_running(managed)
                self._exercise_absent_context()
                self._exercise_malformed_context()
                self._ensure_running(managed)
            try:
                resource = self._resource_observer(managed)
            except OSError:
                raise SmokeFailure("owned process resources could not be observed") from None
            self._ensure_running(managed)
            if diagnostic_proof:
                induced_failure_ms = self._exercise_induced_failures(managed)
                scenario = DiagnosticScenarioObservation(
                    correlated_requests=FIXED_LATENCY_SAMPLE_COUNT + 1,
                    latency_sample_count=FIXED_LATENCY_SAMPLE_COUNT,
                    concurrent_request_count=CONCURRENT_REQUEST_WORKERS,
                    correlated_latency_p50_ms=_nearest_rank(latencies, 0.50),
                    correlated_latency_p95_ms=_nearest_rank(latencies, 0.95),
                    correlated_latency_max_ms=max(latencies),
                    induced_failure_ms=induced_failure_ms,
                )
            smoke_ms = round((self._monotonic() - start) * 1000)
        except KeyboardInterrupt:
            failure = SmokeFailure("smoke interrupted")
        except SmokeFailure as exc:
            failure = exc
        finally:
            shutdown_start = self._monotonic()
            if not self._signals.requested.is_set():
                self._signals.request()
            try:
                cleanup_ok = self._controller.shutdown(managed, self._signals, self._output)
            except OSError:
                cleanup_ok = False
            shutdown_ms = round((self._monotonic() - shutdown_start) * 1000)
            ports_closed = self._wait_for_closed_ports()

        if not cleanup_ok or not ports_closed:
            raise SmokeFailure("owned runtime cleanup did not complete")
        if failure is not None:
            raise failure

        next_after = _measure_directory_bytes(next_root)
        observation = SmokeObservation(
            api_live_ms=api_live_ms,
            smoke_ms=smoke_ms,
            shutdown_ms=shutdown_ms,
            process_count=resource.process_count,
            resident_bytes=resource.resident_bytes,
            next_bytes_before=next_before,
            next_bytes_after=next_after,
            next_bytes_delta=next_after - next_before,
        )
        return observation, scenario


def _install_interrupt_handlers(signals: ShutdownSignals, platform: PlatformFamily) -> None:
    install_signal_handlers(signals, platform)


def _runtime_main(arguments: Sequence[str] | None = None) -> int:
    """Run the private child scenario whose stderr is consumed by the outer gate."""

    actual_arguments = tuple(sys.argv[1:] if arguments is None else arguments)
    if actual_arguments:
        _write(sys.stderr, "this command accepts no arguments")
        return 2
    platform: PlatformFamily = "windows" if os.name == "nt" else "posix"
    signals = ShutdownSignals()
    _install_interrupt_handlers(signals, platform)
    try:
        observation = RuntimeSmoke(platform=platform, signals=signals).run_diagnostic()
    except (OSError, ValueError, SmokeFailure) as exc:
        _write(sys.stderr, str(exc))
        return 1
    print(
        f"[smoke-inner] passed {json.dumps(asdict(observation), sort_keys=True)}",
        file=sys.stderr,
        flush=True,
    )
    return 0


def _launch_inner_runtime(platform: PlatformFamily) -> subprocess.Popen[bytes]:
    command = (sys.executable, "-m", "ai_learning_platform_api.development.smoke")
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    if platform == "windows":
        creation_flag = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
        return subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[5],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            shell=False,
            creationflags=creation_flag,
        )
    return subprocess.Popen(
        command,
        cwd=Path(__file__).resolve().parents[5],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        shell=False,
        start_new_session=True,
    )


def _signal_inner_runtime(
    process: subprocess.Popen[bytes],
    platform: PlatformFamily,
) -> None:
    try:
        if platform == "windows":
            break_event = int(getattr(signal, "CTRL_BREAK_EVENT", 1))
            process.send_signal(break_event)
        else:
            kill_group = cast(Callable[[int, int], None], vars(os)["killpg"])
            kill_group(process.pid, int(signal.SIGINT))
    except OSError:
        pass


def _posix_descendant_process_ids(
    process_id: int,
    *,
    proc_root: Path = Path("/proc"),
) -> tuple[int, ...]:
    if not proc_root.is_dir():
        return ()
    parents: dict[int, int] = {}
    for item in proc_root.iterdir():
        if not item.name.isdecimal():
            continue
        try:
            stat_text = (item / "stat").read_text(encoding="utf-8")
            closing_parenthesis = stat_text.rfind(")")
            if closing_parenthesis < 0:
                continue
            fields = stat_text[closing_parenthesis + 1 :].split()
            parents[int(item.name)] = int(fields[1])
        except (FileNotFoundError, IndexError, OSError, ValueError):
            continue
    descendants: list[int] = []
    known_parents = {process_id}
    while True:
        discovered = sorted(
            candidate
            for candidate, parent in parents.items()
            if candidate not in known_parents and parent in known_parents
        )
        if not discovered:
            break
        descendants.extend(discovered)
        known_parents.update(discovered)
    return tuple(descendants)


def _force_inner_runtime(
    process: subprocess.Popen[bytes],
    platform: PlatformFamily,
) -> None:
    if platform == "posix":
        for descendant in reversed(_posix_descendant_process_ids(process.pid)):
            try:
                os.kill(descendant, _FORCE_SIGNAL)
            except OSError:
                pass
        try:
            kill_group = cast(Callable[[int, int], None], vars(os)["killpg"])
            kill_group(process.pid, _FORCE_SIGNAL)
            return
        except OSError:
            pass
    try:
        process.kill()
    except OSError:
        pass


def _force_and_reap_inner_runtime(
    process: subprocess.Popen[bytes],
    platform: PlatformFamily,
) -> int:
    _force_inner_runtime(process, platform)
    while True:
        try:
            return process.wait(timeout=INNER_FORCE_REAP_TIMEOUT_SECONDS)
        except KeyboardInterrupt:
            _force_inner_runtime(process, platform)
        except subprocess.TimeoutExpired:
            _force_inner_runtime(process, platform)


def _wait_for_inner_runtime(
    process: subprocess.Popen[bytes],
    platform: PlatformFamily,
    stop_requested: threading.Event | None = None,
) -> int:
    requested = stop_requested or threading.Event()
    cleanup_stage = 1 if requested.is_set() else 0
    if cleanup_stage:
        _signal_inner_runtime(process, platform)
    while True:
        try:
            timeout = INNER_CLEANUP_TIMEOUT_SECONDS / 2 if cleanup_stage else POLL_INTERVAL_SECONDS
            return process.wait(timeout=timeout)
        except KeyboardInterrupt:
            _signal_inner_runtime(process, platform)
            cleanup_stage += 1
            if cleanup_stage > 2:
                return _force_and_reap_inner_runtime(process, platform)
        except subprocess.TimeoutExpired:
            if cleanup_stage == 1:
                _signal_inner_runtime(process, platform)
                cleanup_stage = 2
            elif cleanup_stage == 2:
                return _force_and_reap_inner_runtime(process, platform)
            elif requested.is_set():
                _signal_inner_runtime(process, platform)
                cleanup_stage = 1


def _read_bounded_inner_output(
    stream: BinaryIO,
    content: bytearray,
    stop_requested: threading.Event,
    overflowed: threading.Event,
    read_failed: threading.Event,
) -> None:
    try:
        while True:
            chunk = stream.read(8192)
            if not chunk:
                break
            remaining = MAX_CAPTURE_BYTES + 1 - len(content)
            if remaining > 0:
                content.extend(chunk[:remaining])
            if len(chunk) > remaining or len(content) > MAX_CAPTURE_BYTES:
                if not overflowed.is_set():
                    overflowed.set()
                    stop_requested.set()
    except OSError:
        read_failed.set()
        stop_requested.set()
    finally:
        try:
            stream.close()
        except OSError:
            read_failed.set()


def _capture_inner_runtime(
    process: subprocess.Popen[bytes],
    platform: PlatformFamily,
) -> tuple[int, bytes, bool, bool]:
    stream = process.stderr
    if stream is None:
        stop_requested = threading.Event()
        stop_requested.set()
        return_code = _wait_for_inner_runtime(process, platform, stop_requested)
        return return_code, b"", False, True

    content = bytearray()
    stop_requested = threading.Event()
    overflowed = threading.Event()
    read_failed = threading.Event()
    reader = threading.Thread(
        target=_read_bounded_inner_output,
        args=(
            cast(BinaryIO, stream),
            content,
            stop_requested,
            overflowed,
            read_failed,
        ),
        name="f02-bounded-diagnostic-capture",
        daemon=True,
    )
    reader.start()
    return_code = _wait_for_inner_runtime(process, platform, stop_requested)
    reader.join(timeout=INNER_CLEANUP_TIMEOUT_SECONDS)
    if reader.is_alive():
        read_failed.set()
        try:
            stream.close()
        except OSError:
            pass
        reader.join(timeout=INNER_CLEANUP_TIMEOUT_SECONDS)
    return return_code, bytes(content), overflowed.is_set(), read_failed.is_set()


def _raise_outer_interrupt(_signal_number: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt


@contextmanager
def _outer_interrupt_handlers(platform: PlatformFamily) -> Iterator[None]:
    signal_numbers = [int(signal.SIGTERM)]
    if platform == "windows":
        break_signal = getattr(signal, "SIGBREAK", None)
        if break_signal is not None:
            signal_numbers.append(int(break_signal))
    previous_handlers: list[tuple[int, Any]] = []
    try:
        for signal_number in signal_numbers:
            previous_handlers.append((signal_number, signal.getsignal(signal_number)))
            signal.signal(signal_number, _raise_outer_interrupt)
        yield
    finally:
        for signal_number, previous_handler in reversed(previous_handlers):
            signal.signal(signal_number, previous_handler)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the no-argument cross-process smoke and suppress all raw child output."""

    actual_arguments = tuple(sys.argv[1:] if arguments is None else arguments)
    if actual_arguments:
        _write(sys.stderr, "this command accepts no arguments")
        return 2
    platform: PlatformFamily = "windows" if os.name == "nt" else "posix"
    try:
        with _outer_interrupt_handlers(platform):
            process = _launch_inner_runtime(platform)
            try:
                return_code, content, overflowed, read_failed = _capture_inner_runtime(
                    process,
                    platform,
                )
            except BaseException:
                stop_requested = threading.Event()
                stop_requested.set()
                _wait_for_inner_runtime(process, platform, stop_requested)
                raise
    except KeyboardInterrupt:
        _write(sys.stderr, "diagnostic runtime was interrupted and reaped")
        return 1
    except (OSError, RuntimeError):
        _write(sys.stderr, "diagnostic runtime could not be launched or captured")
        return 1

    if overflowed:
        _write(sys.stderr, "captured diagnostic output exceeded the byte limit")
        return 1
    if read_failed:
        _write(sys.stderr, "diagnostic runtime output could not be captured")
        return 1
    if return_code != 0:
        _write(sys.stderr, "diagnostic runtime failed; captured output was suppressed")
        return 1
    try:
        _validate_captured_log(content)
        inner = _extract_inner_observation(content)
        proof = _assert_diagnostic_proof(
            content,
            correlated_requests=inner.scenario.correlated_requests,
        )
    except SmokeFailure as exc:
        _write(sys.stderr, str(exc))
        return 1
    complete = CompleteSmokeObservation(
        runtime=inner.runtime,
        scenario=inner.scenario,
        diagnostics=proof,
    )
    _write(sys.stdout, f"passed {json.dumps(asdict(complete), sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_runtime_main())
