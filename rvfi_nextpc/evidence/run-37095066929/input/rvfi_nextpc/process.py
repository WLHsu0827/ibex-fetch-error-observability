# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Exclusive receipts and byte-preserving bounded process execution."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from typing import Sequence


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="ascii", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=True)
        stream.write("\n")


def identity(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def no_core_dump() -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(
    argv: Sequence[str], cwd: Path, output: Path, name: str, timeout: float
) -> dict[str, object]:
    """Logs are direct binary files: no decoding/re-encoding or tail loss."""
    command = [str(item) for item in argv]
    start = time.monotonic()
    status: dict[str, object] = {
        "schema": 1, "argv": command, "cwd": str(cwd), "timeout_seconds": timeout,
    }
    with (output / f"{name}.stdout.log").open("xb") as stdout, (
        output / f"{name}.stderr.log"
    ).open("xb") as stderr:
        options: dict[str, object] = {}
        if os.name == "posix":
            options.update(start_new_session=True, preexec_fn=no_core_dump)
        try:
            child = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr, **options)
        except OSError as error:
            status.update(kind="spawn_error", code=error.errno, error=str(error))
        else:
            try:
                code = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(child.pid, signal.SIGKILL)
                else:
                    child.kill()
                child.wait()
                status.update(kind="timed_out", code=124)
            else:
                status.update(kind="signaled" if code < 0 else "exited", code=abs(code))
    status["duration_seconds"] = time.monotonic() - start
    status["stdout"] = identity(output / f"{name}.stdout.log")
    status["stderr"] = identity(output / f"{name}.stderr.log")
    write_json(output / f"{name}.status.json", status)
    return status


def require_success(status: dict[str, object]) -> None:
    if status["kind"] != "exited" or status["code"] != 0:
        raise RuntimeError(f"STOP: {status['argv']}: {status['kind']}:{status['code']}")


def expected_fatal(status: dict[str, object], text: bytes, marker: bytes) -> bool:
    return status["kind"] == "signaled" and status["code"] == signal.SIGABRT and marker in text
