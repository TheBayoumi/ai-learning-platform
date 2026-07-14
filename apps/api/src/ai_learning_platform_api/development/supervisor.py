"""Own the role-neutral API and web development process trees."""

from __future__ import annotations

import ctypes
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any, Literal, Protocol, TextIO, cast

API_HOST = "127.0.0.1"
API_PORT = 8000
WEB_HOST = "127.0.0.1"
WEB_PORT = 3000
POLL_INTERVAL_SECONDS = 0.05
GRACEFUL_SHUTDOWN_SECONDS = 5.0
TERMINATE_SHUTDOWN_SECONDS = 2.0
FORCED_SHUTDOWN_SECONDS = 2.0

PlatformFamily = Literal["windows", "posix"]
_KILLPG_ATTRIBUTE = "killpg"
_SIGBREAK_ATTRIBUTE = "SIGBREAK"
_SIGKILL_ATTRIBUTE = "SIGKILL"
_CREATE_SUSPENDED = 0x00000004
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS = 1
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
_THREAD_SUSPEND_RESUME = 0x0002
_TH32CS_SNAPTHREAD = 0x00000004


class SupervisorConfigurationError(ValueError):
    """The fixed development command cannot be constructed safely."""


class ChildProcess(Protocol):
    """The subprocess behavior used by the supervisor."""

    pid: int

    def poll(self) -> int | None: ...

    def send_signal(self, sig: int) -> None: ...

    def kill(self) -> None: ...


class WindowsJobHandle(Protocol):
    """One Windows Job Object that owns a service process tree."""

    def active_process_count(self) -> int: ...

    def terminate(self) -> bool: ...

    def close(self) -> None: ...


class _JobObjectBasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JobObjectExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JobObjectBasicLimitInformation),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JobObjectBasicAccountingInformation(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


class _ThreadEntry32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ThreadID", wintypes.DWORD),
        ("th32OwnerProcessID", wintypes.DWORD),
        ("tpBasePri", wintypes.LONG),
        ("tpDeltaPri", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
    ]


class _WindowsJob:
    """Small dependency-free owner for one kill-on-close Windows Job Object."""

    def __init__(self, handle: int, kernel32: Any) -> None:
        self._handle = handle
        self._kernel32 = kernel32
        self._closed = False

    def active_process_count(self) -> int:
        information = _JobObjectBasicAccountingInformation()
        succeeded = self._kernel32.QueryInformationJobObject(
            self._handle,
            _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS,
            ctypes.byref(information),
            ctypes.sizeof(information),
            None,
        )
        if not succeeded:
            raise OSError(ctypes.get_last_error(), "could not inspect Windows Job Object")
        return int(information.ActiveProcesses)

    def terminate(self) -> bool:
        return bool(self._kernel32.TerminateJobObject(self._handle, 1))

    def close(self) -> None:
        if not self._closed:
            if not self._kernel32.CloseHandle(self._handle):
                raise OSError(ctypes.get_last_error(), "could not close Windows Job Object")
            self._closed = True


class _WindowsJobProcess:
    """Delegate direct-process status while retaining owned-tree control."""

    def __init__(self, process: subprocess.Popen[bytes], job: WindowsJobHandle) -> None:
        self._process = process
        self._job = job
        self.pid = process.pid

    def poll(self) -> int | None:
        return self._process.poll()

    def send_signal(self, signal_number: int) -> None:
        self._process.send_signal(signal_number)

    def kill(self) -> None:
        self._process.kill()

    def tree_active(self) -> bool:
        return self._job.active_process_count() > 0

    def terminate_tree(self) -> bool:
        return self._job.terminate()

    def close_tree(self) -> None:
        self._job.close()


@dataclass(frozen=True)
class ServiceSpec:
    """One fixed local development service."""

    name: str
    command: tuple[str, ...]
    working_directory: Path
    environment: dict[str, str]


@dataclass(frozen=True)
class ManagedProcess:
    """A launched service and its owned process-group leader."""

    service: ServiceSpec
    process: ChildProcess


class ShutdownSignals:
    """Thread-safe first-signal graceful and second-signal forced state."""

    def __init__(self) -> None:
        self.requested = threading.Event()
        self.forced = threading.Event()

    def request(self) -> None:
        if self.requested.is_set():
            self.forced.set()
        self.requested.set()


Launcher = Callable[[ServiceSpec, PlatformFamily], ChildProcess]
GroupSignal = Callable[[int, int], None]
Taskkill = Callable[[int], int]


class TreeController(Protocol):
    """The owned-tree cleanup behavior used by the supervisor."""

    def shutdown(
        self,
        processes: Sequence[ManagedProcess],
        signals: ShutdownSignals,
        output: TextIO,
    ) -> bool: ...


def _platform_family() -> PlatformFamily:
    return "windows" if os.name == "nt" else "posix"


def _write(stream: TextIO, message: str) -> None:
    print(f"[dev] {message}", file=stream, flush=True)


def build_service_specs(
    *,
    api_root: Path | None = None,
    node_executable: str | None = None,
    uv_executable: str | None = None,
) -> tuple[ServiceSpec, ServiceSpec]:
    """Build the fixed, literal-loopback API and web commands."""

    resolved_api_root = api_root or Path(__file__).resolve().parents[3]
    repository_root = resolved_api_root.parent.parent
    web_root = repository_root / "apps" / "web"

    if not (resolved_api_root / "pyproject.toml").is_file():
        raise SupervisorConfigurationError("API project is missing; run from this checkout.")
    if not (web_root / "package.json").is_file():
        raise SupervisorConfigurationError("Web project is missing; run from this checkout.")

    resolved_node = node_executable or shutil.which("node")
    if resolved_node is None:
        raise SupervisorConfigurationError(
            "Node.js is not available on PATH; install the version from .nvmrc."
        )

    node_path = Path(resolved_node)
    if not node_path.is_file():
        raise SupervisorConfigurationError("The resolved Node.js executable is missing.")

    resolved_uv = uv_executable or shutil.which("uv")
    if resolved_uv is None:
        raise SupervisorConfigurationError("uv is not available on PATH; install uv 0.11.18.")
    uv_path = Path(resolved_uv)
    if not uv_path.is_file():
        raise SupervisorConfigurationError("The resolved uv executable is missing.")

    next_cli = web_root / "node_modules" / "next" / "dist" / "bin" / "next"
    if not next_cli.is_file():
        raise SupervisorConfigurationError(
            "The pinned Next.js CLI is missing; run npm ci from apps/web."
        )

    api_environment = os.environ.copy()
    api_environment["PYTHONUNBUFFERED"] = "1"
    web_environment = os.environ.copy()
    web_environment["AI_PLATFORM_API_BASE_URL"] = f"http://{API_HOST}:{API_PORT}"
    web_environment["NEXT_TELEMETRY_DISABLED"] = "1"

    api = ServiceSpec(
        name="api",
        command=(
            str(uv_path.resolve()),
            "run",
            "--project",
            str(resolved_api_root.resolve()),
            "--locked",
            "python",
            "-m",
            "uvicorn",
            "ai_learning_platform_api.main:app",
            "--host",
            API_HOST,
            "--port",
            str(API_PORT),
        ),
        working_directory=resolved_api_root,
        environment=api_environment,
    )
    web = ServiceSpec(
        name="web",
        command=(
            str(node_path.resolve()),
            str(next_cli.resolve()),
            "dev",
            "--hostname",
            WEB_HOST,
            "--port",
            str(WEB_PORT),
        ),
        working_directory=web_root,
        environment=web_environment,
    )
    return api, web


def _create_windows_job(process_handle: int) -> WindowsJobHandle:
    """Assign one direct child to a kill-on-close Windows Job Object."""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
    kernel32.CreateJobObjectW.restype = ctypes.c_void_p
    kernel32.SetInformationJobObject.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.QueryInformationJobObject.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    kernel32.QueryInformationJobObject.restype = wintypes.BOOL
    kernel32.TerminateJobObject.argtypes = [ctypes.c_void_p, wintypes.UINT]
    kernel32.TerminateJobObject.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = wintypes.BOOL

    job_handle = kernel32.CreateJobObjectW(None, None)
    if not job_handle:
        raise OSError(ctypes.get_last_error(), "could not create Windows Job Object")

    job = _WindowsJob(int(job_handle), kernel32)
    try:
        limits = _JobObjectExtendedLimitInformation()
        limits.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            job_handle,
            _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            raise OSError(
                ctypes.get_last_error(),
                "could not configure Windows Job Object",
            )

        if not kernel32.AssignProcessToJobObject(job_handle, process_handle):
            raise OSError(
                ctypes.get_last_error(),
                "could not assign child process to Windows Job Object",
            )
    except BaseException:
        job.close()
        raise
    return job


def _resume_windows_process(process_id: int) -> None:
    """Resume the single initial thread of a newly created suspended child."""

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Thread32First.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ThreadEntry32)]
    kernel32.Thread32First.restype = wintypes.BOOL
    kernel32.Thread32Next.argtypes = [ctypes.c_void_p, ctypes.POINTER(_ThreadEntry32)]
    kernel32.Thread32Next.restype = wintypes.BOOL
    kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenThread.restype = ctypes.c_void_p
    kernel32.ResumeThread.argtypes = [ctypes.c_void_p]
    kernel32.ResumeThread.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = wintypes.BOOL

    snapshot = kernel32.CreateToolhelp32Snapshot(_TH32CS_SNAPTHREAD, 0)
    invalid_handle = ctypes.c_void_p(-1).value
    if not snapshot or snapshot == invalid_handle:
        raise OSError(ctypes.get_last_error(), "could not inspect suspended child thread")

    thread_id: int | None = None
    try:
        entry = _ThreadEntry32()
        entry.dwSize = ctypes.sizeof(entry)
        has_entry = bool(kernel32.Thread32First(snapshot, ctypes.byref(entry)))
        while has_entry:
            if int(entry.th32OwnerProcessID) == process_id:
                thread_id = int(entry.th32ThreadID)
                break
            has_entry = bool(kernel32.Thread32Next(snapshot, ctypes.byref(entry)))
    finally:
        kernel32.CloseHandle(snapshot)

    if thread_id is None:
        raise OSError("could not find suspended child thread")

    thread_handle = kernel32.OpenThread(_THREAD_SUSPEND_RESUME, False, thread_id)
    if not thread_handle:
        raise OSError(ctypes.get_last_error(), "could not open suspended child thread")
    try:
        previous_suspend_count = int(kernel32.ResumeThread(thread_handle))
        if previous_suspend_count == int(wintypes.DWORD(-1).value):
            raise OSError(ctypes.get_last_error(), "could not resume owned child process")
    finally:
        kernel32.CloseHandle(thread_handle)


def launch_service(service: ServiceSpec, platform: PlatformFamily) -> ChildProcess:
    """Launch a service as the leader of an isolated process group."""

    if platform == "windows":
        creation_flag = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
        creation_flag |= _CREATE_SUSPENDED
        process = subprocess.Popen(
            service.command,
            cwd=service.working_directory,
            env=service.environment,
            shell=False,
            creationflags=creation_flag,
        )
        job: WindowsJobHandle | None = None
        try:
            process_handle = cast(int, cast(Any, process)._handle)
            job = _create_windows_job(process_handle)
            _resume_windows_process(process.pid)
        except OSError:
            if job is not None:
                try:
                    job.close()
                except OSError:
                    pass
            if process.poll() is None:
                process.kill()
            process.wait()
            raise
        return _WindowsJobProcess(process, job)

    return subprocess.Popen(
        service.command,
        cwd=service.working_directory,
        env=service.environment,
        shell=False,
        start_new_session=True,
    )


# Compatibility alias for callers of the original private launcher name.
_launch_service = launch_service


def _send_posix_group_signal(process_id: int, signal_number: int) -> None:
    kill_group = cast(GroupSignal, getattr(os, _KILLPG_ATTRIBUTE))
    kill_group(process_id, signal_number)


def _taskkill_tree(process_id: int) -> int:
    completed = subprocess.run(
        ["taskkill.exe", "/PID", str(process_id), "/T", "/F"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode


class ProcessTreeController:
    """Bounded graceful and forced cleanup for owned process trees."""

    def __init__(
        self,
        platform: PlatformFamily,
        *,
        group_signal: GroupSignal = _send_posix_group_signal,
        taskkill: Taskkill = _taskkill_tree,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        graceful_seconds: float = GRACEFUL_SHUTDOWN_SECONDS,
        terminate_seconds: float = TERMINATE_SHUTDOWN_SECONDS,
        forced_seconds: float = FORCED_SHUTDOWN_SECONDS,
    ) -> None:
        self._platform = platform
        self._group_signal = group_signal
        self._taskkill = taskkill
        self._monotonic = monotonic
        self._sleep = sleep
        self._graceful_seconds = graceful_seconds
        self._terminate_seconds = terminate_seconds
        self._forced_seconds = forced_seconds

    def _signal_posix_group(self, process_id: int, signal_number: int) -> bool:
        try:
            self._group_signal(process_id, signal_number)
        except ProcessLookupError:
            return True
        except OSError:
            return False
        return True

    def _group_exists(self, process_id: int) -> bool:
        try:
            self._group_signal(process_id, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _trees_active(self, processes: Sequence[ManagedProcess]) -> bool:
        if self._platform == "posix":
            for item in processes:
                item.process.poll()
            return any(self._group_exists(item.process.pid) for item in processes)
        return any(self._windows_tree_active(item) for item in processes)

    def _windows_tree_active(self, item: ManagedProcess) -> bool:
        item.process.poll()
        tree_active = getattr(item.process, "tree_active", None)
        if tree_active is None:
            return item.process.poll() is None
        try:
            return bool(cast(Callable[[], bool], tree_active)())
        except OSError:
            return True

    def _wait_for_exit(
        self,
        processes: Sequence[ManagedProcess],
        timeout: float,
        signals: ShutdownSignals,
        *,
        honor_force: bool,
    ) -> bool:
        deadline = self._monotonic() + timeout
        while self._trees_active(processes):
            if honor_force and signals.forced.is_set():
                return False
            if self._monotonic() >= deadline:
                return False
            self._sleep(POLL_INTERVAL_SECONDS)
        for item in processes:
            item.process.poll()
        return True

    def _request_graceful(self, item: ManagedProcess) -> bool:
        if self._platform == "posix":
            return self._signal_posix_group(item.process.pid, int(signal.SIGINT))
        if item.process.poll() is not None:
            return not self._windows_tree_active(item)
        break_event = int(getattr(signal, "CTRL_BREAK_EVENT", 1))
        try:
            item.process.send_signal(break_event)
        except OSError:
            return False
        return True

    def _force_windows_tree(self, item: ManagedProcess) -> bool:
        terminate_tree = getattr(item.process, "terminate_tree", None)
        if terminate_tree is not None:
            try:
                return bool(cast(Callable[[], bool], terminate_tree)())
            except OSError:
                return False
        if item.process.poll() is not None:
            return True
        if self._taskkill(item.process.pid) == 0:
            return True
        try:
            item.process.kill()
        except OSError:
            return False
        return True

    def _shutdown(
        self,
        processes: Sequence[ManagedProcess],
        signals: ShutdownSignals,
        output: TextIO,
    ) -> bool:
        """Stop every owned tree, escalating within fixed deadlines."""

        if not processes:
            return True

        _write(output, "stopping owned development process trees")
        graceful_results = [self._request_graceful(item) for item in reversed(tuple(processes))]
        graceful_ok = all(graceful_results)
        if graceful_ok and self._wait_for_exit(
            processes,
            self._graceful_seconds,
            signals,
            honor_force=True,
        ):
            return True

        if self._platform == "posix" and not signals.forced.is_set():
            _write(output, "grace period expired; sending SIGTERM to owned groups")
            terminate_results = [
                self._signal_posix_group(item.process.pid, int(signal.SIGTERM))
                for item in reversed(tuple(processes))
            ]
            terminate_ok = all(terminate_results)
            if terminate_ok and self._wait_for_exit(
                processes,
                self._terminate_seconds,
                signals,
                honor_force=True,
            ):
                return True

        _write(output, "forcing remaining owned process trees to stop")
        if self._platform == "posix":
            force_results = [
                self._signal_posix_group(
                    item.process.pid,
                    int(getattr(signal, _SIGKILL_ATTRIBUTE, 9)),
                )
                for item in reversed(tuple(processes))
            ]
            force_ok = all(force_results)
        else:
            force_results = [self._force_windows_tree(item) for item in reversed(tuple(processes))]
            force_ok = all(force_results)

        stopped = self._wait_for_exit(
            processes,
            self._forced_seconds,
            signals,
            honor_force=False,
        )
        return force_ok and stopped

    def shutdown(
        self,
        processes: Sequence[ManagedProcess],
        signals: ShutdownSignals,
        output: TextIO,
    ) -> bool:
        """Stop every owned tree and release every retained ownership handle."""

        cleanup_ok = False
        close_ok = True
        try:
            cleanup_ok = self._shutdown(processes, signals, output)
        finally:
            if self._platform == "windows":
                for item in reversed(tuple(processes)):
                    close_tree = getattr(item.process, "close_tree", None)
                    if close_tree is None:
                        continue
                    try:
                        cast(Callable[[], None], close_tree)()
                    except OSError:
                        close_ok = False
        return cleanup_ok and close_ok


def _supervisor_exit_code(child_code: int) -> int:
    if 1 <= child_code <= 125:
        return child_code
    if -127 <= child_code < 0:
        return 128 + abs(child_code)
    return 1


class DevSupervisor:
    """Start, monitor, and stop the fixed development services."""

    def __init__(
        self,
        services: Sequence[ServiceSpec],
        *,
        platform: PlatformFamily,
        signals: ShutdownSignals,
        controller: TreeController,
        launcher: Launcher = launch_service,
        output: TextIO = sys.stdout,
        error: TextIO = sys.stderr,
    ) -> None:
        self._services = tuple(services)
        self._platform = platform
        self._signals = signals
        self._controller = controller
        self._launcher = launcher
        self._output = output
        self._error = error

    def run(self) -> int:
        managed: list[ManagedProcess] = []
        result = 0

        try:
            for service in self._services:
                if self._signals.requested.is_set():
                    break
                _write(self._output, f"launching {service.name} process")
                try:
                    process = self._launcher(service, self._platform)
                except OSError as exc:
                    _write(self._error, f"failed to launch {service.name}: {exc}")
                    result = 1
                    break
                managed.append(ManagedProcess(service=service, process=process))
                _write(self._output, f"launched {service.name} process (pid {process.pid})")

            if len(managed) == len(self._services):
                _write(
                    self._output,
                    f"processes launched: api http://{API_HOST}:{API_PORT}; "
                    f"web http://{WEB_HOST}:{WEB_PORT}; press Ctrl+C to stop",
                )
                while not self._signals.requested.wait(POLL_INTERVAL_SECONDS):
                    exited = next(
                        (item for item in managed if item.process.poll() is not None),
                        None,
                    )
                    if exited is None:
                        continue
                    child_code = exited.process.poll()
                    assert child_code is not None
                    _write(
                        self._error,
                        f"{exited.service.name} exited unexpectedly with code {child_code}",
                    )
                    result = _supervisor_exit_code(child_code)
                    break
        except KeyboardInterrupt:
            self._signals.request()
        finally:
            cleanup_ok = self._controller.shutdown(managed, self._signals, self._output)

        if not cleanup_ok:
            _write(self._error, "failed to stop every owned development process tree")
            return 1
        return result


def _install_signal_handlers(signals: ShutdownSignals, platform: PlatformFamily) -> None:
    def request_shutdown(_signal_number: int, _frame: FrameType | None) -> None:
        signals.request()

    handled_signals = [signal.SIGINT, signal.SIGTERM]
    if platform == "windows":
        handled_signals.append(cast(signal.Signals, getattr(signal, _SIGBREAK_ATTRIBUTE)))
    for handled_signal in handled_signals:
        signal.signal(handled_signal, request_shutdown)


# Public reuse surface for development commands that share the same lifecycle.
install_signal_handlers = _install_signal_handlers


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the fixed development supervisor CLI."""

    actual_arguments = tuple(sys.argv[1:] if arguments is None else arguments)
    if actual_arguments:
        _write(sys.stderr, "this command accepts no arguments")
        return 2

    try:
        services = build_service_specs()
    except SupervisorConfigurationError as exc:
        _write(sys.stderr, str(exc))
        return 1

    platform = _platform_family()
    signals = ShutdownSignals()
    _install_signal_handlers(signals, platform)
    controller = ProcessTreeController(platform)
    return DevSupervisor(
        services,
        platform=platform,
        signals=signals,
        controller=controller,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
