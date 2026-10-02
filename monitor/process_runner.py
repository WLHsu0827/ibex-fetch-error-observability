"""Bounded subprocess execution with typed, fail-closed outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Sequence


@dataclass(frozen=True)
class ProcessStatus:
    kind: str
    code: int
    duration_seconds: float
    argv: tuple[str, ...]
    stdout: str
    stderr: str

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")


def _disable_core_dumps() -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_bounded(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: float,
    stdout_path: Path,
    stderr_path: Path,
) -> ProcessStatus:
    start = time.monotonic()
    command = tuple(str(item) for item in argv)
    options: dict[str, object] = {
        "cwd": cwd,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
    }
    if os.name == "posix":
        options.update(start_new_session=True, preexec_fn=_disable_core_dumps)
    else:
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        process = subprocess.Popen(command, **options)
    except FileNotFoundError as exc:
        status = ProcessStatus(
            "missing_tool", 127, time.monotonic() - start, command, "", str(exc)
        )
    except OSError as exc:
        status = ProcessStatus(
            "spawn_error", 126, time.monotonic() - start, command, "", str(exc)
        )
    else:
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            stdout, stderr = process.communicate()
            status = ProcessStatus(
                "timeout",
                124,
                time.monotonic() - start,
                command,
                stdout,
                stderr,
            )
        else:
            if process.returncode < 0:
                kind, code = "signaled", -process.returncode
            else:
                kind, code = "exited", process.returncode
            status = ProcessStatus(
                kind, code, time.monotonic() - start, command, stdout, stderr
            )
    stdout_path.write_text(status.stdout)
    stderr_path.write_text(status.stderr)
    return status


def require_success(status: ProcessStatus) -> None:
    if status.kind != "exited" or status.code != 0:
        raise RuntimeError(f"command failed: {status.kind}:{status.code}")


def is_expected_reset_fatal(status: ProcessStatus) -> bool:
    diagnostic = "TRACE_MONITOR_RESET_AFTER_START"
    return (
        status.kind == "signaled"
        and status.code == signal.SIGABRT
        and diagnostic in status.stdout + status.stderr
    )
