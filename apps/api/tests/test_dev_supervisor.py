"""Behavior and real owned-tree tests for the development supervisor."""

from __future__ import annotations

import ctypes
import io
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from ctypes import wintypes
from pathlib import Path
from typing import Any, TextIO, cast

import pytest

from ai_learning_platform_api.development import supervisor as dev_supervisor


class FakeProcess:
    def __init__(self, process_id: int, return_code: int | None = None) -> None:
        self.pid = process_id
        self._handle = process_id
        self.return_code = return_code
        self.stderr: io.BytesIO | None = None
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


class FakeWindowsFunction:
    def __init__(self, implementation: Callable[..., int]) -> None:
        self._implementation = implementation
        self.argtypes: list[object] | None = None
        self.restype: object | None = None

    def __call__(self, *args: object) -> int:
        return self._implementation(*args)


class FakeNativeKernel32:
    def __init__(
        self,
        *,
        job_handle: int = 101,
        set_information_result: int = 1,
        assign_result: int = 1,
        active_processes: int = 2,
        snapshot_handle: int = 201,
        thread_entries: Sequence[tuple[int, int]] = (),
        open_thread_handle: int = 301,
        resume_result: int = 1,
    ) -> None:
        self.job_handle = job_handle
        self.set_information_result = set_information_result
        self.assign_result = assign_result
        self.active_processes = active_processes
        self.snapshot_handle = snapshot_handle
        self._thread_entries = iter(thread_entries)
        self.open_thread_handle = open_thread_handle
        self.resume_result = resume_result
        self.limit_flags: list[int] = []
        self.set_information_classes: list[int] = []
        self.set_information_sizes: list[int] = []
        self.assigned_job_handles: list[int] = []
        self.assigned_process_handles: list[int] = []
        self.open_thread_arguments: list[tuple[int, bool, int]] = []
        self.opened_thread_ids: list[int] = []
        self.resumed_thread_handles: list[int] = []
        self.closed_handles: list[int] = []

        self.CreateJobObjectW = FakeWindowsFunction(lambda *_args: self.job_handle)
        self.SetInformationJobObject = FakeWindowsFunction(self._set_information_job_object)
        self.AssignProcessToJobObject = FakeWindowsFunction(self._assign_process_to_job_object)
        self.QueryInformationJobObject = FakeWindowsFunction(self._query_information_job_object)
        self.TerminateJobObject = FakeWindowsFunction(lambda *_args: 1)
        self.CloseHandle = FakeWindowsFunction(self._close_handle)
        self.CreateToolhelp32Snapshot = FakeWindowsFunction(lambda *_args: self.snapshot_handle)
        self.Thread32First = FakeWindowsFunction(self._write_thread_entry)
        self.Thread32Next = FakeWindowsFunction(self._write_thread_entry)
        self.OpenThread = FakeWindowsFunction(self._open_thread)
        self.ResumeThread = FakeWindowsFunction(self._resume_thread)

    def _set_information_job_object(
        self,
        _job_handle: Any,
        information_class: Any,
        information_pointer: Any,
        information_size: Any,
    ) -> int:
        information = ctypes.cast(
            information_pointer,
            ctypes.POINTER(dev_supervisor._JobObjectExtendedLimitInformation),
        ).contents
        self.limit_flags.append(int(information.BasicLimitInformation.LimitFlags))
        self.set_information_classes.append(int(information_class))
        self.set_information_sizes.append(int(information_size))
        return self.set_information_result

    def _assign_process_to_job_object(self, job_handle: Any, process_handle: Any) -> int:
        self.assigned_job_handles.append(int(job_handle))
        self.assigned_process_handles.append(int(process_handle))
        return self.assign_result

    def _query_information_job_object(
        self,
        _job_handle: Any,
        _information_class: Any,
        information_pointer: Any,
        _information_size: Any,
        _return_length: Any,
    ) -> int:
        information = ctypes.cast(
            information_pointer,
            ctypes.POINTER(dev_supervisor._JobObjectBasicAccountingInformation),
        ).contents
        information.ActiveProcesses = self.active_processes
        return 1

    def _write_thread_entry(self, _snapshot: Any, entry_pointer: Any) -> int:
        try:
            owner_process_id, thread_id = next(self._thread_entries)
        except StopIteration:
            return 0
        entry = ctypes.cast(
            entry_pointer,
            ctypes.POINTER(dev_supervisor._ThreadEntry32),
        ).contents
        entry.th32OwnerProcessID = owner_process_id
        entry.th32ThreadID = thread_id
        return 1

    def _open_thread(self, access: Any, inherit: Any, thread_id: Any) -> int:
        self.open_thread_arguments.append((int(access), bool(inherit), int(thread_id)))
        self.opened_thread_ids.append(int(thread_id))
        return self.open_thread_handle

    def _resume_thread(self, thread_handle: Any) -> int:
        self.resumed_thread_handles.append(int(thread_handle))
        return self.resume_result

    def _close_handle(self, handle: Any) -> int:
        self.closed_handles.append(int(handle))
        return 1


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
        "--no-access-log",
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
    assert calls[-1]["stdout"] is None
    assert calls[-1]["stderr"] is None

    assert dev_supervisor._launch_service(_service("service"), "posix") is process
    assert calls[-1]["start_new_session"] is True
    assert "creationflags" not in calls[-1]
    assert calls[-1]["stdout"] is None
    assert calls[-1]["stderr"] is None

    stdout = object()
    stderr = object()
    assert (
        dev_supervisor.launch_service(
            _service("service"),
            "posix",
            stdout=stdout,
            stderr=stderr,
        )
        is process
    )
    assert calls[-1]["stdout"] is stdout
    assert calls[-1]["stderr"] is stderr


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


def test_windows_ctypes_adapters_validate_and_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    kernel32 = object()
    load_calls: list[tuple[str, bool]] = []

    def load_library(name: str, *, use_last_error: bool) -> object:
        load_calls.append((name, use_last_error))
        return kernel32

    monkeypatch.setattr(ctypes, "WinDLL", load_library, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 123, raising=False)

    assert dev_supervisor._load_windows_kernel32() is kernel32
    assert dev_supervisor._windows_last_error() == 123
    assert load_calls == [("kernel32", True)]

    monkeypatch.setattr(ctypes, "WinDLL", None)
    with pytest.raises(OSError, match="Windows ctypes API WinDLL is unavailable"):
        dev_supervisor._load_windows_kernel32()

    monkeypatch.setattr(ctypes, "get_last_error", None)
    with pytest.raises(OSError, match="Windows ctypes API get_last_error is unavailable"):
        dev_supervisor._windows_last_error()


def test_create_windows_job_configures_assigns_and_owns_handle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = FakeNativeKernel32()
    monkeypatch.setattr(dev_supervisor, "_load_windows_kernel32", lambda: kernel32)

    job = dev_supervisor._create_windows_job(444)

    assert kernel32.limit_flags == [dev_supervisor._JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE]
    assert kernel32.set_information_classes == [
        dev_supervisor._JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS
    ]
    assert kernel32.set_information_sizes == [
        ctypes.sizeof(dev_supervisor._JobObjectExtendedLimitInformation)
    ]
    assert kernel32.assigned_job_handles == [kernel32.job_handle]
    assert kernel32.assigned_process_handles == [444]
    assert kernel32.CreateJobObjectW.argtypes is not None
    assert kernel32.CloseHandle.restype is not None
    assert job.active_process_count() == 2
    assert job.terminate()
    job.close()
    assert kernel32.closed_handles == [kernel32.job_handle]


@pytest.mark.parametrize(
    ("kernel32", "message", "expected_closed_handles"),
    [
        (FakeNativeKernel32(job_handle=0), "create Windows Job Object", []),
        (
            FakeNativeKernel32(set_information_result=0),
            "configure Windows Job Object",
            [101],
        ),
        (
            FakeNativeKernel32(assign_result=0),
            "assign child process to Windows Job Object",
            [101],
        ),
    ],
)
def test_create_windows_job_failure_paths_close_owned_handle(
    monkeypatch: pytest.MonkeyPatch,
    kernel32: FakeNativeKernel32,
    message: str,
    expected_closed_handles: list[int],
) -> None:
    monkeypatch.setattr(dev_supervisor, "_load_windows_kernel32", lambda: kernel32)
    monkeypatch.setattr(dev_supervisor, "_windows_last_error", lambda: 7)

    with pytest.raises(OSError, match=message) as error:
        dev_supervisor._create_windows_job(444)

    assert error.value.errno == 7
    assert kernel32.closed_handles == expected_closed_handles


def test_resume_windows_process_finds_owned_thread_and_closes_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel32 = FakeNativeKernel32(thread_entries=((999, 41), (444, 42)))
    monkeypatch.setattr(dev_supervisor, "_load_windows_kernel32", lambda: kernel32)

    dev_supervisor._resume_windows_process(444)

    assert kernel32.open_thread_arguments == [(dev_supervisor._THREAD_SUSPEND_RESUME, False, 42)]
    assert kernel32.opened_thread_ids == [42]
    assert kernel32.resumed_thread_handles == [kernel32.open_thread_handle]
    assert kernel32.closed_handles == [kernel32.snapshot_handle, kernel32.open_thread_handle]
    assert kernel32.CreateToolhelp32Snapshot.argtypes is not None
    assert kernel32.ResumeThread.restype is not None


@pytest.mark.parametrize(
    ("kernel32", "message", "expected_closed_handles"),
    [
        (FakeNativeKernel32(snapshot_handle=0), "inspect suspended child thread", []),
        (
            FakeNativeKernel32(thread_entries=()),
            "find suspended child thread",
            [201],
        ),
        (
            FakeNativeKernel32(thread_entries=((444, 42),), open_thread_handle=0),
            "open suspended child thread",
            [201],
        ),
        (
            FakeNativeKernel32(
                thread_entries=((444, 42),),
                resume_result=int(wintypes.DWORD(-1).value),
            ),
            "resume owned child process",
            [201, 301],
        ),
    ],
)
def test_resume_windows_process_failure_paths_close_acquired_handles(
    monkeypatch: pytest.MonkeyPatch,
    kernel32: FakeNativeKernel32,
    message: str,
    expected_closed_handles: list[int],
) -> None:
    monkeypatch.setattr(dev_supervisor, "_load_windows_kernel32", lambda: kernel32)
    monkeypatch.setattr(dev_supervisor, "_windows_last_error", lambda: 9)

    with pytest.raises(OSError, match=message):
        dev_supervisor._resume_windows_process(444)

    assert kernel32.closed_handles == expected_closed_handles


def test_windows_job_wrapper_and_api_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dev_supervisor, "_windows_last_error", lambda: 5)

    query_failure = dev_supervisor._WindowsJob(1, FakeKernel32(query_result=0))
    with pytest.raises(OSError, match="inspect Windows Job Object") as query_error:
        query_failure.active_process_count()
    assert query_error.value.errno == 5

    close_failure = dev_supervisor._WindowsJob(2, FakeKernel32(close_result=0))
    with pytest.raises(OSError, match="close Windows Job Object") as close_error:
        close_failure.close()
    assert close_error.value.errno == 5

    close_success = dev_supervisor._WindowsJob(3, FakeKernel32())
    close_success.close()
    close_success.close()

    direct = FakeProcess(106, return_code=0)
    stderr = io.BytesIO()
    direct.stderr = stderr
    job = FakeWindowsJob()
    wrapper = dev_supervisor._WindowsJobProcess(cast(subprocess.Popen[bytes], direct), job)
    assert wrapper.poll() == 0
    assert wrapper.stderr is stderr
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
