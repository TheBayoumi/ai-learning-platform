"""Behavior and real owned-tree tests for the development supervisor."""

from __future__ import annotations

import io
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO, cast

import pytest

from ai_learning_platform_api.development import supervisor as dev_supervisor


class FakeProcess:
    def __init__(self, process_id: int, return_code: int | None = None) -> None:
        self.pid = process_id
        self._handle = process_id
        self.return_code = return_code
        self.sent_signals: list[int] = []
        self.kill_calls = 0
        self.signal_error = False
        self.kill_error = False

    def poll(self) -> int | None:
        return self.return_code

    def send_signal(self, signal_number: int) -> None:
        self.sent_signals.append(signal_number)
        if self.signal_error:
            raise OSError("signal failed")
        self.return_code = 0

    def kill(self) -> None:
        self.kill_calls += 1
        if self.kill_error:
            raise OSError("kill failed")
        self.return_code = 1

    def wait(self) -> int:
        assert self.return_code is not None
        return self.return_code


class FakeWindowsJob:
    def __init__(self, active_processes: int = 1) -> None:
        self.active_processes = active_processes
        self.terminate_calls = 0
        self.closed = False

    def active_process_count(self) -> int:
        return self.active_processes

    def terminate(self) -> bool:
        self.terminate_calls += 1
        self.active_processes = 0
        return True

    def close(self) -> None:
        self.closed = True


class FakeKernel32:
    def __init__(self, *, query_result: int = 1, close_result: int = 1) -> None:
        self.query_result = query_result
        self.close_result = close_result

    def QueryInformationJobObject(self, *_args: object) -> int:
        return self.query_result

    def TerminateJobObject(self, *_args: object) -> int:
        return 1

    def CloseHandle(self, *_args: object) -> int:
        return self.close_result


class SequencedProcess(FakeProcess):
    def __init__(self, process_id: int, return_codes: Sequence[int | None]) -> None:
        super().__init__(process_id)
        self._return_codes = iter(return_codes)

    def poll(self) -> int | None:
        self.return_code = next(self._return_codes, self.return_code)
        return self.return_code


class FakeController:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.shutdown_calls: list[tuple[dev_supervisor.ManagedProcess, ...]] = []

    def shutdown(
        self,
        processes: Sequence[dev_supervisor.ManagedProcess],
        _signals: dev_supervisor.ShutdownSignals,
        _output: TextIO,
    ) -> bool:
        self.shutdown_calls.append(tuple(processes))
        return self.result


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def monotonic(self) -> float:
        return self.current

    def sleep(self, duration: float) -> None:
        self.current += duration


def _service(name: str) -> dev_supervisor.ServiceSpec:
    return dev_supervisor.ServiceSpec(
        name=name,
        command=(name,),
        working_directory=Path.cwd(),
        environment={},
    )


def _managed(name: str, process: dev_supervisor.ChildProcess) -> dev_supervisor.ManagedProcess:
    return dev_supervisor.ManagedProcess(service=_service(name), process=process)


def _create_checkout(tmp_path: Path) -> tuple[Path, Path]:
    api_root = tmp_path / "apps" / "api"
    web_root = tmp_path / "apps" / "web"
    (web_root / "node_modules" / "next" / "dist" / "bin").mkdir(parents=True)
    api_root.mkdir(parents=True)
    (api_root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (web_root / "package.json").write_text("{}\n", encoding="utf-8")
    (web_root / "node_modules" / "next" / "dist" / "bin" / "next").write_text(
        "next\n", encoding="utf-8"
    )
    node = tmp_path / ("node.exe" if os.name == "nt" else "node")
    node.write_text("node\n", encoding="utf-8")
    return api_root, node


def test_build_service_specs_are_fixed_loopback_commands(tmp_path: Path) -> None:
    api_root, node = _create_checkout(tmp_path)

    api, web = dev_supervisor.build_service_specs(
        api_root=api_root,
        node_executable=str(node),
        uv_executable=sys.executable,
    )

    assert api.name == "api"
    assert api.command == (
        str(Path(sys.executable).resolve()),
        "run",
        "--project",
        str(api_root.resolve()),
        "--locked",
        "python",
        "-m",
        "uvicorn",
        "ai_learning_platform_api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    )
    assert api.working_directory == api_root
    assert api.environment["PYTHONUNBUFFERED"] == "1"
    assert "--reload" not in api.command

    assert web.name == "web"
    assert web.command[0] == str(node.resolve())
    assert web.command[2:] == (
        "dev",
        "--hostname",
        "127.0.0.1",
        "--port",
        "3000",
    )
    assert web.working_directory == tmp_path / "apps" / "web"
    assert web.environment["AI_PLATFORM_API_BASE_URL"] == "http://127.0.0.1:8000"
    assert web.environment["NEXT_TELEMETRY_DISABLED"] == "1"
    assert not any(key.startswith("NEXT_PUBLIC_") for key in web.environment)


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        ("api", "API project is missing"),
        ("web", "Web project is missing"),
        ("node", "Node.js executable is missing"),
        ("next", "Next.js CLI is missing"),
        ("uv", "uv executable is missing"),
    ],
)
def test_build_service_specs_fail_closed(tmp_path: Path, missing: str, message: str) -> None:
    api_root, node = _create_checkout(tmp_path)
    if missing == "api":
        (api_root / "pyproject.toml").unlink()
    elif missing == "web":
        (tmp_path / "apps" / "web" / "package.json").unlink()
    elif missing == "node":
        node.unlink()
    elif missing == "next":
        (tmp_path / "apps" / "web" / "node_modules" / "next" / "dist" / "bin" / "next").unlink()

    with pytest.raises(dev_supervisor.SupervisorConfigurationError, match=message):
        dev_supervisor.build_service_specs(
            api_root=api_root,
            node_executable=str(node),
            uv_executable=(str(tmp_path / "missing-uv.exe") if missing == "uv" else sys.executable),
        )


@pytest.mark.parametrize("missing", ["node", "uv"])
def test_build_service_specs_reports_executable_missing_from_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    api_root, node = _create_checkout(tmp_path)
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: None if name == missing else (str(node) if name == "node" else sys.executable),
    )

    with pytest.raises(dev_supervisor.SupervisorConfigurationError, match="not available"):
        dev_supervisor.build_service_specs(api_root=api_root)


def test_launch_service_uses_platform_group_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    process = FakeProcess(101)

    def fake_popen(_command: Sequence[str], **kwargs: object) -> FakeProcess:
        calls.append(kwargs)
        return process

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    job = FakeWindowsJob()
    assigned_handles: list[int] = []
    resumed_processes: list[int] = []

    def create_job(process_handle: int) -> FakeWindowsJob:
        assigned_handles.append(process_handle)
        return job

    monkeypatch.setattr(dev_supervisor, "_create_windows_job", create_job)
    monkeypatch.setattr(dev_supervisor, "_resume_windows_process", resumed_processes.append)

    windows_process = dev_supervisor._launch_service(_service("service"), "windows")
    assert windows_process.pid == process.pid
    assert cast(dev_supervisor._WindowsJobProcess, windows_process).tree_active()
    assert calls[-1]["shell"] is False
    assert calls[-1]["creationflags"] == (
        int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
        | dev_supervisor._CREATE_SUSPENDED
    )
    assert assigned_handles == [process._handle]
    assert resumed_processes == [process.pid]
    assert "start_new_session" not in calls[-1]

    assert dev_supervisor._launch_service(_service("service"), "posix") is process
    assert calls[-1]["start_new_session"] is True
    assert "creationflags" not in calls[-1]


def test_windows_launch_fails_closed_when_job_assignment_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess(102)
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(
        dev_supervisor,
        "_create_windows_job",
        lambda _process_handle: (_ for _ in ()).throw(OSError("job assignment failed")),
    )
    with pytest.raises(OSError, match="job assignment failed"):
        dev_supervisor._launch_service(_service("service"), "windows")
    assert process.kill_calls == 1


def test_windows_launch_fails_closed_when_suspended_child_cannot_resume(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess(104)
    job = FakeWindowsJob()
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(dev_supervisor, "_create_windows_job", lambda _process_handle: job)
    monkeypatch.setattr(
        dev_supervisor,
        "_resume_windows_process",
        lambda _process_id: (_ for _ in ()).throw(OSError("resume failed")),
    )
    with pytest.raises(OSError, match="resume failed"):
        dev_supervisor._launch_service(_service("service"), "windows")
    assert job.closed
    assert process.kill_calls == 1


def test_windows_launch_preserves_resume_error_when_job_close_also_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    process = FakeProcess(105)

    class CloseErrorJob(FakeWindowsJob):
        def close(self) -> None:
            raise OSError("close failed")

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(dev_supervisor, "_create_windows_job", lambda _handle: CloseErrorJob())
    monkeypatch.setattr(
        dev_supervisor,
        "_resume_windows_process",
        lambda _process_id: (_ for _ in ()).throw(OSError("resume failed")),
    )
    with pytest.raises(OSError, match="resume failed"):
        dev_supervisor._launch_service(_service("service"), "windows")
    assert process.kill_calls == 1


def test_windows_job_wrapper_and_api_failures() -> None:
    query_failure = dev_supervisor._WindowsJob(1, FakeKernel32(query_result=0))
    with pytest.raises(OSError, match="inspect Windows Job Object"):
        query_failure.active_process_count()

    close_failure = dev_supervisor._WindowsJob(2, FakeKernel32(close_result=0))
    with pytest.raises(OSError, match="close Windows Job Object"):
        close_failure.close()

    close_success = dev_supervisor._WindowsJob(3, FakeKernel32())
    close_success.close()
    close_success.close()

    direct = FakeProcess(106, return_code=0)
    job = FakeWindowsJob()
    wrapper = dev_supervisor._WindowsJobProcess(cast(subprocess.Popen[bytes], direct), job)
    assert wrapper.poll() == 0
    assert wrapper.tree_active()
    assert wrapper.terminate_tree()
    assert not wrapper.tree_active()
    wrapper.kill()
    wrapper.close_tree()
    assert direct.kill_calls == 1
    assert job.closed


def test_platform_wrappers_delegate_to_os_and_taskkill(monkeypatch: pytest.MonkeyPatch) -> None:
    group_calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        os,
        dev_supervisor._KILLPG_ATTRIBUTE,
        lambda process_id, signal_number: group_calls.append((process_id, signal_number)),
        raising=False,
    )
    dev_supervisor._send_posix_group_signal(77, 15)
    assert group_calls == [(77, 15)]

    commands: list[Sequence[str]] = []

    def run_command(
        command: Sequence[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 9)

    monkeypatch.setattr(subprocess, "run", run_command)
    assert dev_supervisor._taskkill_tree(88) == 9
    assert commands == [["taskkill.exe", "/PID", "88", "/T", "/F"]]


@pytest.mark.parametrize(
    ("child_code", "expected"),
    [(0, 1), (1, 1), (42, 42), (125, 125), (126, 1), (-2, 130), (-127, 255), (-128, 1)],
)
def test_supervisor_exit_code(child_code: int, expected: int) -> None:
    assert dev_supervisor._supervisor_exit_code(child_code) == expected


def test_supervisor_propagates_child_failure_and_cleans_sibling() -> None:
    controller = FakeController()
    launched = iter((FakeProcess(201, return_code=23), FakeProcess(202)))
    output = io.StringIO()
    error = io.StringIO()
    supervisor = dev_supervisor.DevSupervisor(
        (_service("api"), _service("web")),
        platform="windows",
        signals=dev_supervisor.ShutdownSignals(),
        controller=controller,
        launcher=lambda _spec, _platform: next(launched),
        output=output,
        error=error,
    )
    assert supervisor.run() == 23
    assert len(controller.shutdown_calls[0]) == 2
    assert "api exited unexpectedly with code 23" in error.getvalue()
    assert "processes launched" in output.getvalue()
    assert "ready" not in output.getvalue().lower()


def test_supervisor_second_spawn_failure_cleans_first() -> None:
    controller = FakeController()
    calls = 0

    def launcher(
        _spec: dev_supervisor.ServiceSpec, _platform: dev_supervisor.PlatformFamily
    ) -> FakeProcess:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("cannot spawn")
        return FakeProcess(301)

    error = io.StringIO()
    supervisor = dev_supervisor.DevSupervisor(
        (_service("api"), _service("web")),
        platform="posix",
        signals=dev_supervisor.ShutdownSignals(),
        controller=controller,
        launcher=launcher,
        output=io.StringIO(),
        error=error,
    )
    assert supervisor.run() == 1
    assert len(controller.shutdown_calls[0]) == 1
    assert "failed to launch web" in error.getvalue()


def test_supervisor_clean_signal_shutdown_and_cleanup_failure() -> None:
    signals = dev_supervisor.ShutdownSignals()
    calls = 0

    def launcher(
        _spec: dev_supervisor.ServiceSpec, _platform: dev_supervisor.PlatformFamily
    ) -> FakeProcess:
        nonlocal calls
        calls += 1
        if calls == 2:
            signals.request()
        return FakeProcess(400 + calls)

    error = io.StringIO()
    supervisor = dev_supervisor.DevSupervisor(
        (_service("api"), _service("web")),
        platform="windows",
        signals=signals,
        controller=FakeController(result=False),
        launcher=launcher,
        output=io.StringIO(),
        error=error,
    )
    assert supervisor.run() == 1
    assert "failed to stop every owned" in error.getvalue()


def test_shutdown_signals_force_on_second_request() -> None:
    signals = dev_supervisor.ShutdownSignals()
    signals.request()
    assert signals.requested.is_set()
    assert not signals.forced.is_set()
    signals.request()
    assert signals.forced.is_set()


def test_windows_controller_graceful_forced_and_exited_leader_paths() -> None:
    output = io.StringIO()
    signals = dev_supervisor.ShutdownSignals()
    graceful = FakeProcess(501)
    controller = dev_supervisor.ProcessTreeController("windows")
    assert controller.shutdown((_managed("web", graceful),), signals, output)
    assert graceful.sent_signals == [int(getattr(signal, "CTRL_BREAK_EVENT", 1))]

    stubborn = FakeProcess(502)
    stubborn.signal_error = True

    def taskkill(process_id: int) -> int:
        assert process_id == stubborn.pid
        stubborn.return_code = 1
        return 0

    assert dev_supervisor.ProcessTreeController("windows", taskkill=taskkill).shutdown(
        (_managed("web", stubborn),), signals, output
    )

    fallback = FakeProcess(503)
    fallback.signal_error = True
    assert dev_supervisor.ProcessTreeController("windows", taskkill=lambda _process_id: 1).shutdown(
        (_managed("web", fallback),), signals, output
    )
    assert fallback.kill_calls == 1

    exited = FakeProcess(506, return_code=0)
    job = FakeWindowsJob(active_processes=1)
    owned = dev_supervisor._WindowsJobProcess(cast(subprocess.Popen[bytes], exited), job)
    assert dev_supervisor.ProcessTreeController("windows").shutdown(
        (_managed("api", owned),), signals, output
    )
    assert job.terminate_calls == 1
    assert job.closed


def test_windows_controller_reports_unrecoverable_failures() -> None:
    process = FakeProcess(504)
    process.signal_error = True
    process.kill_error = True
    clock = FakeClock()
    controller = dev_supervisor.ProcessTreeController(
        "windows",
        taskkill=lambda _process_id: 1,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        forced_seconds=0.1,
    )
    assert not controller.shutdown(
        (_managed("web", process),), dev_supervisor.ShutdownSignals(), io.StringIO()
    )

    class ErrorJobProcess(FakeProcess):
        def tree_active(self) -> bool:
            raise OSError("query failed")

        def terminate_tree(self) -> bool:
            raise OSError("terminate failed")

        def close_tree(self) -> None:
            raise OSError("close failed")

    error_process = ErrorJobProcess(507, return_code=0)
    clock = FakeClock()
    controller = dev_supervisor.ProcessTreeController(
        "windows",
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        graceful_seconds=0.1,
        forced_seconds=0.1,
    )
    assert not controller.shutdown(
        (_managed("api", error_process),), dev_supervisor.ShutdownSignals(), io.StringIO()
    )


def test_controller_handles_absent_and_uncontrollable_processes() -> None:
    controller = dev_supervisor.ProcessTreeController("windows")
    exited = FakeProcess(505, return_code=0)
    assert controller.shutdown((), dev_supervisor.ShutdownSignals(), io.StringIO())
    assert controller._request_graceful(_managed("web", exited))
    assert controller._force_windows_tree(_managed("web", exited))

    def missing_group(_pid: int, _signal_number: int) -> None:
        raise ProcessLookupError

    controller = dev_supervisor.ProcessTreeController("posix", group_signal=missing_group)
    assert controller._signal_posix_group(1, int(signal.SIGTERM))
    assert not controller._group_exists(1)

    def denied_group(_pid: int, signal_number: int) -> None:
        if signal_number == 0:
            raise PermissionError
        raise OSError("denied")

    controller = dev_supervisor.ProcessTreeController("posix", group_signal=denied_group)
    assert not controller._signal_posix_group(1, int(signal.SIGTERM))
    assert controller._group_exists(1)
    controller = dev_supervisor.ProcessTreeController(
        "posix", group_signal=lambda _pid, _sig: (_ for _ in ()).throw(OSError())
    )
    assert not controller._group_exists(1)


def test_posix_controller_escalates_every_group_in_reverse_order() -> None:
    alive = {601, 602}
    calls: list[tuple[int, int]] = []
    clock = FakeClock()

    def group_signal(process_id: int, signal_number: int) -> None:
        calls.append((process_id, signal_number))
        if signal_number == 0 and process_id not in alive:
            raise ProcessLookupError
        if signal_number == int(signal.SIGTERM):
            alive.discard(process_id)

    controller = dev_supervisor.ProcessTreeController(
        "posix",
        group_signal=group_signal,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        graceful_seconds=0.1,
        terminate_seconds=0.1,
    )
    processes = (_managed("api", FakeProcess(601)), _managed("web", FakeProcess(602)))
    assert controller.shutdown(processes, dev_supervisor.ShutdownSignals(), io.StringIO())
    assert [item for item in calls if item[1] != 0] == [
        (602, int(signal.SIGINT)),
        (601, int(signal.SIGINT)),
        (602, int(signal.SIGTERM)),
        (601, int(signal.SIGTERM)),
    ]


def test_posix_second_signal_skips_to_forced_cleanup() -> None:
    alive = {701}
    calls: list[int] = []
    signals = dev_supervisor.ShutdownSignals()
    signals.request()
    signals.request()

    def group_signal(process_id: int, signal_number: int) -> None:
        if signal_number == 0:
            if process_id not in alive:
                raise ProcessLookupError
            return
        calls.append(signal_number)
        if signal_number == int(getattr(signal, "SIGKILL", 9)):
            alive.discard(process_id)

    controller = dev_supervisor.ProcessTreeController("posix", group_signal=group_signal)
    assert controller.shutdown((_managed("api", FakeProcess(701)),), signals, io.StringIO())
    assert calls == [int(signal.SIGINT), int(getattr(signal, "SIGKILL", 9))]


def test_install_signal_handlers_requests_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    handlers: dict[int, object] = {}

    def install(signal_number: int, handler: object) -> None:
        handlers[int(signal_number)] = handler

    monkeypatch.setattr(signal, "signal", install)
    signals = dev_supervisor.ShutdownSignals()
    dev_supervisor._install_signal_handlers(signals, "posix")
    cast(Callable[[int, object], None], handlers[int(signal.SIGINT)])(int(signal.SIGINT), None)
    assert signals.requested.is_set()

    handlers.clear()
    monkeypatch.setattr(signal, dev_supervisor._SIGBREAK_ATTRIBUTE, signal.SIGTERM, raising=False)
    dev_supervisor._install_signal_handlers(signals, "windows")
    assert int(signal.SIGTERM) in handlers


def test_main_rejects_arguments_configuration_and_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    assert dev_supervisor.main(("--port",)) == 2

    def fail_specs() -> tuple[dev_supervisor.ServiceSpec, dev_supervisor.ServiceSpec]:
        raise dev_supervisor.SupervisorConfigurationError("configuration failed")

    monkeypatch.setattr(dev_supervisor, "build_service_specs", fail_specs)
    assert dev_supervisor.main(()) == 1

    services = (_service("api"), _service("web"))
    monkeypatch.setattr(dev_supervisor, "build_service_specs", lambda: services)
    monkeypatch.setattr(dev_supervisor, "_platform_family", lambda: "posix")
    monkeypatch.setattr(
        dev_supervisor, "_install_signal_handlers", lambda _signals, _platform: None
    )

    class StubSupervisor:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def run(self) -> int:
            return 17

    monkeypatch.setattr(dev_supervisor, "DevSupervisor", StubSupervisor)
    assert dev_supervisor.main(()) == 17


def test_supervisor_honors_prelaunch_keyboard_interrupt_and_polling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signals = dev_supervisor.ShutdownSignals()
    signals.request()
    controller = FakeController()
    supervisor = dev_supervisor.DevSupervisor(
        (_service("api"),),
        platform="windows",
        signals=signals,
        controller=controller,
        launcher=lambda _spec, _platform: (_ for _ in ()).throw(AssertionError("must not launch")),
        output=io.StringIO(),
        error=io.StringIO(),
    )
    assert supervisor.run() == 0
    assert controller.shutdown_calls == [()]

    interrupt_signals = dev_supervisor.ShutdownSignals()
    monkeypatch.setattr(
        interrupt_signals.requested,
        "wait",
        lambda _timeout: (_ for _ in ()).throw(KeyboardInterrupt),
    )
    supervisor = dev_supervisor.DevSupervisor(
        (_service("api"),),
        platform="windows",
        signals=interrupt_signals,
        controller=FakeController(),
        launcher=lambda _spec, _platform: FakeProcess(801),
        output=io.StringIO(),
        error=io.StringIO(),
    )
    assert supervisor.run() == 0
    assert interrupt_signals.requested.is_set()

    process = SequencedProcess(802, (None, 7, 7))
    supervisor = dev_supervisor.DevSupervisor(
        (_service("api"),),
        platform="windows",
        signals=dev_supervisor.ShutdownSignals(),
        controller=FakeController(),
        launcher=lambda _spec, _platform: process,
        output=io.StringIO(),
        error=io.StringIO(),
    )
    assert supervisor.run() == 7


def _pid_exists(process_id: int) -> bool:
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist.exe", "/FI", f"PID eq {process_id}", "/FO", "CSV", "/NH"],
            capture_output=True,
            check=False,
            text=True,
        )
        return f'"{process_id}"' in completed.stdout
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_pid_file(path: Path) -> tuple[int, int]:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if path.is_file():
            values = path.read_text(encoding="utf-8").splitlines()
            if len(values) == 2:
                return int(values[0]), int(values[1])
        time.sleep(0.02)
    raise AssertionError("helper process tree did not report its PIDs")


def _wait_until_gone(process_ids: Sequence[int]) -> None:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if not any(_pid_exists(process_id) for process_id in process_ids):
            return
        time.sleep(0.05)
    raise AssertionError(f"owned helper PIDs remain: {process_ids}")


def _force_remove_recorded_pids(process_ids: Sequence[int]) -> None:
    for process_id in process_ids:
        if not _pid_exists(process_id):
            continue
        if os.name == "nt":
            subprocess.run(
                ["taskkill.exe", "/PID", str(process_id), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            try:
                os.kill(process_id, int(getattr(signal, "SIGKILL", 9)))
            except ProcessLookupError:
                pass
    _wait_until_gone(process_ids)


@pytest.mark.parametrize("stubborn", [False, True])
def test_real_owned_parent_and_grandchild_tree_is_removed(tmp_path: Path, stubborn: bool) -> None:
    helper = Path(__file__).parent / "fixtures" / "process_tree_helper.py"
    pid_file = tmp_path / "tree-pids.txt"
    command = [sys.executable, str(helper), "--pid-file", str(pid_file)]
    if stubborn:
        command.append("--stubborn")
    spec = dev_supervisor.ServiceSpec(
        name="helper",
        command=tuple(command),
        working_directory=tmp_path,
        environment=os.environ.copy(),
    )
    platform = dev_supervisor._platform_family()
    process = dev_supervisor._launch_service(spec, platform)
    process_ids = _wait_for_pid_file(pid_file)
    controller = dev_supervisor.ProcessTreeController(
        platform,
        graceful_seconds=0.2,
        terminate_seconds=0.2,
        forced_seconds=2.0,
    )
    try:
        assert controller.shutdown(
            (dev_supervisor.ManagedProcess(spec, process),),
            dev_supervisor.ShutdownSignals(),
            io.StringIO(),
        )
        _wait_until_gone(process_ids)
    finally:
        if process.poll() is None:
            process.kill()
        _force_remove_recorded_pids(process_ids)


def test_real_descendant_is_removed_after_group_leader_exits(tmp_path: Path) -> None:
    helper = Path(__file__).parent / "fixtures" / "process_tree_helper.py"
    pid_file = tmp_path / "exited-leader-pids.txt"
    spec = dev_supervisor.ServiceSpec(
        name="exiting-helper",
        command=(
            sys.executable,
            str(helper),
            "--pid-file",
            str(pid_file),
            "--exit-after-spawn",
        ),
        working_directory=tmp_path,
        environment=os.environ.copy(),
    )
    platform = dev_supervisor._platform_family()
    process = dev_supervisor._launch_service(spec, platform)
    process_ids = _wait_for_pid_file(pid_file)
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and process.poll() is None:
        time.sleep(0.02)
    assert process.poll() == 0
    assert _pid_exists(process_ids[1])
    controller = dev_supervisor.ProcessTreeController(
        platform,
        graceful_seconds=0.2,
        terminate_seconds=0.2,
        forced_seconds=2.0,
    )
    try:
        assert controller.shutdown(
            (dev_supervisor.ManagedProcess(spec, process),),
            dev_supervisor.ShutdownSignals(),
            io.StringIO(),
        )
        _wait_until_gone(process_ids)
    finally:
        if process.poll() is None:
            process.kill()
        _force_remove_recorded_pids(process_ids)
