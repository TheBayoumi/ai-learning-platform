"""Deterministic tests for the fixed API-and-web runtime smoke."""

from __future__ import annotations

import http.client
import io
import json
import os
import socket
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, TextIO

import pytest

from ai_learning_platform_api.development import smoke
from ai_learning_platform_api.development import supervisor as dev_supervisor


class FakeProcess:
    def __init__(self, process_id: int, return_code: int | None = None) -> None:
        self.pid = process_id
        self.return_code = return_code

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
    ) -> None:
        self.status = status
        self._headers = {
            "content-type": content_type,
            "content-length": content_length,
        }
        self._body = body

    def getheader(self, name: str) -> str | None:
        return self._headers[name]

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
    assert response == smoke.HttpResponse(200, "application/json", b"{}")


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
    ],
)
def test_web_contract_fails_closed(response: smoke.HttpResponse, message: str) -> None:
    with pytest.raises(smoke.SmokeFailure, match=message):
        smoke._assert_available_web(response)


def test_web_contract_accepts_only_accessible_available_state() -> None:
    smoke._assert_available_web(_web_response())


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

    class PassingRuntime:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def run(self) -> smoke.SmokeObservation:
            return smoke.SmokeObservation(1, 2, 3, 4, 5, 6, 7, 1)

    monkeypatch.setattr(smoke, "_install_interrupt_handlers", lambda _signals, _platform: None)
    monkeypatch.setattr(smoke, "RuntimeSmoke", PassingRuntime)
    monkeypatch.setattr(sys, "argv", ["smoke.py"])
    assert smoke.main() == 0
    output = capsys.readouterr().out
    assert "[smoke] passed" in output
    assert '"resident_bytes": 5' in output

    class FailingRuntime:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def run(self) -> smoke.SmokeObservation:
            raise smoke.SmokeFailure("safe failure")

    monkeypatch.setattr(smoke, "RuntimeSmoke", FailingRuntime)
    assert smoke.main([]) == 1
    assert "safe failure" in capsys.readouterr().err


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
