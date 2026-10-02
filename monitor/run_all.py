"""One-command offline contracts or real hosted Verilator replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest

from monitor.process_runner import (
    is_expected_reset_fatal,
    require_success,
    run_bounded,
)
from monitor.trace_check import TraceError, parse_trace, require_positive_trace


ROOT = Path(__file__).resolve().parents[1]
MONITOR = ROOT / "monitor"
POSITIVE_CASES = ("delayed", "initial_low", "held_reset", "async_between_edges")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_offline() -> None:
    suite = unittest.defaultTestLoader.discover(str(MONITOR / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


def execute(
    argv: list[str], directory: Path, name: str, timeout_seconds: float
):
    status = run_bounded(
        argv,
        cwd=directory,
        timeout_seconds=timeout_seconds,
        stdout_path=directory / f"{name}.stdout.log",
        stderr_path=directory / f"{name}.stderr.log",
    )
    status.write(directory / f"{name}.status.json")
    return status


def build_model(output: Path, top: str, sources: list[Path]) -> Path:
    build = output / f"build-{top}"
    build.mkdir()
    status = execute(
        [
            "verilator",
            "--binary",
            "--timing",
            "--timescale",
            "1ns/1ps",
            "--top-module",
            top,
            "--Wall",
            "-j",
            "1",
            "--Mdir",
            str(build),
            *map(str, sources),
        ],
        output,
        f"build-{top}",
        120,
    )
    require_success(status)
    model = build / f"V{top}"
    if not model.is_file():
        raise RuntimeError(f"model missing: {model}")
    return model


def run_case(
    output: Path, model: Path, name: str, scenario: str | None = None
):
    directory = output / name
    directory.mkdir()
    trace = directory / "events.tsv"
    argv = [str(model), f"+trace_log={trace}"]
    if scenario is not None:
        argv.append(f"+CASE={scenario}")
    status = execute(argv, directory, "run", 3)
    return status, trace


def environment_record() -> dict[str, object]:
    commands = {}
    for name, argv in {
        "verilator": ["verilator", "--version"],
        "compiler": ["c++", "--version"],
        "python": [sys.executable, "--version"],
    }.items():
        result = subprocess.run(argv, check=True, text=True, capture_output=True)
        commands[name] = result.stdout.splitlines()[0]
    return {
        "platform": platform.platform(),
        "python": sys.version,
        "tools": commands,
        "github": {
            "run_id": os.environ.get("GITHUB_RUN_ID", ""),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
            "sha": os.environ.get("GITHUB_SHA", ""),
            "ref": os.environ.get("GITHUB_REF", ""),
            "runner_os": os.environ.get("RUNNER_OS", ""),
            "runner_arch": os.environ.get("RUNNER_ARCH", ""),
        },
    }


def run_real(output: Path) -> None:
    if shutil.which("verilator") is None:
        raise SystemExit("verilator is required for --mode real")
    version = subprocess.run(
        ["verilator", "--version"], check=True, text=True, capture_output=True
    ).stdout
    if not version.startswith("Verilator 5.020 "):
        raise SystemExit(f"expected Verilator 5.020, got {version.strip()}")
    output.mkdir(parents=True)
    model = build_model(
        output,
        "trace_monitor_fixture",
        [MONITOR / "observer.sv", MONITOR / "fixture.sv"],
    )
    case_results: dict[str, object] = {}
    for scenario in POSITIVE_CASES:
        status, trace = run_case(output, model, scenario, scenario)
        require_success(status)
        require_positive_trace(parse_trace(trace))
        case_results[scenario] = {
            "status": f"{status.kind}:{status.code}",
            "trace_sha256": sha256(trace),
        }
    status, trace = run_case(output, model, "no_reset", "no_reset")
    require_success(status)
    rows = parse_trace(trace)
    try:
        require_positive_trace(rows)
    except TraceError:
        pass
    else:
        raise RuntimeError("no-reset empty trace was accepted")
    case_results["no_reset"] = {
        "status": f"{status.kind}:{status.code}",
        "strictly_rejected": True,
        "trace_sha256": sha256(trace),
    }
    status, _ = run_case(output, model, "reset_again", "reset_again")
    if not is_expected_reset_fatal(status):
        raise RuntimeError(
            f"reset fatal classification differed: {status.kind}:{status.code}"
        )
    case_results["reset_again"] = {
        "status": f"{status.kind}:{status.code}",
        "expected_fatal": True,
    }
    status, _ = run_case(
        output, model, "fatal_text_then_hang", "fatal_text_then_hang"
    )
    if status.kind != "timeout" or is_expected_reset_fatal(status):
        raise RuntimeError("fatal text followed by hang was not classified timeout")
    case_results["fatal_text_then_hang"] = {
        "status": f"{status.kind}:{status.code}",
        "expected_fatal": False,
    }
    unarmed = build_model(
        output,
        "unarmed_trace_counterexample",
        [MONITOR / "unarmed_fixture.sv"],
    )
    status, trace = run_case(output, unarmed, "unarmed_counterexample")
    require_success(status)
    rows = parse_trace(trace)
    cycles = [row[0] for row in rows["Q"]]
    if cycles != [0, 1, 0, 1]:
        raise RuntimeError(f"unarmed counterexample differed: {cycles}")
    try:
        require_positive_trace(rows)
    except TraceError:
        pass
    else:
        raise RuntimeError("unarmed duplicate-Q counterexample was accepted")
    case_results["unarmed_counterexample"] = {
        "status": f"{status.kind}:{status.code}",
        "q_cycles": cycles,
        "strictly_rejected": True,
        "trace_sha256": sha256(trace),
    }
    source_hashes = {
        path.name: sha256(path)
        for path in (
            MONITOR / "observer.sv",
            MONITOR / "fixture.sv",
            MONITOR / "unarmed_fixture.sv",
            MONITOR / "process_runner.py",
            MONITOR / "trace_check.py",
            MONITOR / "run_all.py",
        )
    }
    summary = {
        "schema": 1,
        "scope": "synthetic instrument-only trace validation",
        "cases": case_results,
        "environment": environment_record(),
        "source_sha256": source_hashes,
        "model_sha256": sha256(model),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({"result": "PASS", **summary}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("offline", "real"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "offline":
        run_offline()
        return
    if args.output is None:
        with tempfile.TemporaryDirectory(prefix="trace-monitor-") as directory:
            run_real(Path(directory))
    else:
        run_real(args.output.resolve())


if __name__ == "__main__":
    main()
