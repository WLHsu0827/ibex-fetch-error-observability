"""Bounded child capture for fixed preparation probes and stdlib fake processes."""

import dataclasses
import hashlib
import os
import pathlib
import signal
import subprocess
import threading
import time


@dataclasses.dataclass(frozen=True)
class Limits:
    wall_seconds: float = 3.0
    output_bytes: int = 128 * 1024
    address_bytes: int = 512 * 1024**2
    cpu_seconds: int = 2
    file_bytes: int = 128 * 1024

    def __post_init__(self):
        if min(self.wall_seconds, self.output_bytes, self.address_bytes,
               self.cpu_seconds, self.file_bytes) <= 0:
            raise ValueError("all caps must be positive")


def _posix_limits(limits):
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (limits.address_bytes, limits.address_bytes))
    resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits.file_bytes, limits.file_bytes))


def capture(argv, directory, limits=Limits(), program_name=None, resource_limits=True):
    """Internal runner. Public entry points supply only fixed, reviewed argv."""
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    buffers = {name: bytearray() for name in ("stdout", "stderr", "program")}
    budget = [limits.output_bytes]
    lock, overflow = threading.Lock(), threading.Event()
    read_errors = []
    started = time.monotonic()
    status, detail, returncode = "spawn_error", "", None

    def append(name, data):
        with lock:
            size = min(len(data), budget[0])
            buffers[name].extend(data[:size])
            budget[0] -= size
            if size != len(data):
                overflow.set()

    def drain(stream, name):
        try:
            while chunk := stream.read(4096):
                append(name, chunk)
        except OSError as error:
            read_errors.append(str(error))
        finally:
            stream.close()

    def kill_group(process):
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # This exact child group already exited.
        elif process.poll() is None:
            process.kill()

    offset = 0
    program_path = directory / program_name if program_name else None

    def read_program():
        nonlocal offset
        if program_path is not None and program_path.exists():
            if program_path.is_symlink() or not program_path.is_file():
                raise OSError("program log must be a regular file")
            size = program_path.stat().st_size
            if size < offset:
                raise OSError("program log was truncated/replaced")
            with program_path.open("rb") as file:
                file.seek(offset)
                while chunk := file.read(4096):
                    offset += len(chunk)
                    append("program", chunk)
                    if overflow.is_set():
                        break

    process = None
    threads = []
    try:
        process = subprocess.Popen(
            argv, cwd=directory, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, start_new_session=os.name == "posix",
            preexec_fn=(lambda: _posix_limits(limits))
            if resource_limits and os.name == "posix" else None,
        )
        threads = [
            threading.Thread(target=drain, args=(process.stdout, "stdout"), daemon=True),
            threading.Thread(target=drain, args=(process.stderr, "stderr"), daemon=True),
        ]
        for thread in threads:
            thread.start()
        status = "running"
        while True:
            read_program()
            if overflow.is_set():
                status, detail = "output_limit", "combined stdout/stderr/program cap exceeded"
                break
            if time.monotonic() - started >= limits.wall_seconds:
                status, detail = "wall_timeout", "wall cap exceeded (marker is not completion)"
                break
            if process.poll() is not None and all(not t.is_alive() for t in threads):
                break
            time.sleep(0.01)
        if status in ("output_limit", "wall_timeout"):
            kill_group(process)
        returncode = process.wait(timeout=2)
        for thread in threads:
            thread.join(timeout=2)
        read_program()
        if status == "running":
            if overflow.is_set():
                status = "output_limit"
            elif read_errors:
                status, detail = "capture_error", "; ".join(read_errors)
            elif returncode == 0:
                status = "exit_zero"
            elif (resource_limits and os.name == "posix" and returncode == 78
                  and b"STOCK_RESOURCE_LIMIT address_space\n" in buffers["stderr"]):
                status, detail = "resource_limit", "child reported MemoryError under RLIMIT_AS"
            elif returncode < 0:
                resource_signals = (getattr(signal, "SIGXCPU", -999),
                                    getattr(signal, "SIGXFSZ", -998))
                status = "resource_limit" if -returncode in resource_signals else "signal"
            else:
                status = "exit_nonzero"
    except OSError as error:
        status = "spawn_error" if process is None else "capture_error"
        detail = f"{type(error).__name__}: {error}"
    except subprocess.TimeoutExpired:
        status, detail = "capture_error", "child did not terminate after bounded kill"
    finally:
        if process is not None:
            kill_group(process)
            process.wait(timeout=2)
        for thread in threads:
            thread.join(timeout=2)
    for name, data in buffers.items():
        (directory / f"{name}.log").write_bytes(data)
    receipt = {
        "argv": list(argv), "termination": status, "returncode": returncode,
        "detail": detail, "wall_seconds": time.monotonic() - started,
        "limits": dataclasses.asdict(limits),
        "resource_enforcement": "POSIX_RLIMIT" if resource_limits and os.name == "posix"
        else "NOT_ENFORCED (portable synthetic/version probes only)",
        "truncated": overflow.is_set(),
        "streams": {name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    for name, data in buffers.items()},
    }
    return receipt, {name: bytes(value) for name, value in buffers.items()}
