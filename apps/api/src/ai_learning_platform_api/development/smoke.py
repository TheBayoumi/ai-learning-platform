"""Run the fixed local API-and-web cross-process smoke contract."""

from __future__ import annotations

import http.client
import json
import os
import socket
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TextIO, cast

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


class SmokeFailure(RuntimeError):
    """A safe, expected smoke assertion or lifecycle failure."""


@dataclass(frozen=True)
class HttpResponse:
    """One bounded loopback response with normalized media type."""

    status: int
    media_type: str | None
    body: bytes


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


Requester = Callable[[int, str], HttpResponse]
Launcher = Callable[[ServiceSpec, PlatformFamily], ChildProcess]
PortProbe = Callable[[int], bool]
ResourceObserver = Callable[[Sequence[ManagedProcess]], ResourceObservation]


def _write(stream: TextIO, message: str) -> None:
    print(f"[smoke] {message}", file=stream, flush=True)


def request_loopback(port: int, path: str) -> HttpResponse:
    """Perform one fixed, bounded HTTP request without proxy or redirect support."""

    connection = http.client.HTTPConnection(
        "127.0.0.1",
        port,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    try:
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
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
        )
    finally:
        connection.close()


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
    )
    if any(value in html for value in forbidden):
        raise SmokeFailure("/ exposed a forbidden state or server-only value")


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

    def _request_once(self, port: int, path: str) -> HttpResponse:
        try:
            return self._requester(port, path)
        except (ConnectionError, TimeoutError, OSError, http.client.HTTPException):
            raise SmokeFailure(f"{path} request failed") from None

    def run(self) -> SmokeObservation:
        start = self._monotonic()
        next_root = self._repository_root / "apps" / "web" / ".next" / "dev"
        next_before = _measure_directory_bytes(next_root)
        managed: list[ManagedProcess] = []
        failure: SmokeFailure | None = None
        resource = ResourceObservation(process_count=None, resident_bytes=None)
        api_live_ms = 0
        smoke_ms = 0

        if self._port_probe(API_PORT) or self._port_probe(WEB_PORT):
            raise SmokeFailure("fixed smoke ports must be unused before launch")

        services = self._services if self._services is not None else build_service_specs()
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
            try:
                resource = self._resource_observer(managed)
            except OSError:
                raise SmokeFailure("owned process resources could not be observed") from None
            self._ensure_running(managed)
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
        return SmokeObservation(
            api_live_ms=api_live_ms,
            smoke_ms=smoke_ms,
            shutdown_ms=shutdown_ms,
            process_count=resource.process_count,
            resident_bytes=resource.resident_bytes,
            next_bytes_before=next_before,
            next_bytes_after=next_after,
            next_bytes_delta=next_after - next_before,
        )


def _install_interrupt_handlers(signals: ShutdownSignals, platform: PlatformFamily) -> None:
    install_signal_handlers(signals, platform)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the no-argument cross-process smoke CLI."""

    actual_arguments = tuple(sys.argv[1:] if arguments is None else arguments)
    if actual_arguments:
        _write(sys.stderr, "this command accepts no arguments")
        return 2
    platform: PlatformFamily = "windows" if os.name == "nt" else "posix"
    signals = ShutdownSignals()
    _install_interrupt_handlers(signals, platform)
    try:
        observation = RuntimeSmoke(platform=platform, signals=signals).run()
    except (OSError, ValueError, SmokeFailure) as exc:
        _write(sys.stderr, str(exc))
        return 1
    _write(sys.stdout, f"passed {json.dumps(asdict(observation), sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
