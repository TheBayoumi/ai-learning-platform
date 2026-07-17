"""Create a parent/grandchild tree for supervisor lifecycle tests."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import FrameType

_stop_requested = False
_SIGBREAK_ATTRIBUTE = "SIGBREAK"


def _request_stop(_signal_number: int, _frame: FrameType | None) -> None:
    global _stop_requested
    _stop_requested = True


def _configure_signals(*, stubborn: bool) -> None:
    handled = [signal.SIGINT, signal.SIGTERM]
    if os.name == "nt":
        handled.append(getattr(signal, _SIGBREAK_ATTRIBUTE))
    for handled_signal in handled:
        signal.signal(handled_signal, signal.SIG_IGN if stubborn else _request_stop)


def _wait() -> None:
    while not _stop_requested:
        time.sleep(0.02)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid-file", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--stubborn", action="store_true")
    parser.add_argument("--exit-after-spawn", action="store_true")
    arguments = parser.parse_args()

    _configure_signals(stubborn=arguments.stubborn)
    if arguments.child:
        _wait()
        return 0

    command = [sys.executable, __file__, "--pid-file", str(arguments.pid_file), "--child"]
    if arguments.stubborn:
        command.append("--stubborn")
    child = subprocess.Popen(command)
    arguments.pid_file.write_text(f"{os.getpid()}\n{child.pid}\n", encoding="utf-8")

    if arguments.exit_after_spawn:
        return 0

    _wait()
    child.wait(timeout=2.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
