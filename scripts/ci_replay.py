#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Install and replay ONLY on a disposable GitHub-hosted Ubuntu runner."""

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time

from evidence import load_json


PIN = "7cd891ef267e8db36813b29cb8851142ab2636d5"
BUNDLE = Path(__file__).resolve().parents[1]
LOG_LIMIT = 200_000


class Replay:
    def __init__(self, temporary):
        self.checkout = temporary / "ibex-dependency"
        self.output = temporary / "public-replay-evidence"
        self.output.mkdir(exist_ok=False)
        (self.output / "logs").mkdir()
        self.commands = []
        self.environment = {
            "kind": "fresh automated GitHub-hosted RTL replay, NOT human validation",
            "event_commit": os.environ["GITHUB_SHA"],
            "upstream_commit": PIN,
            "run_url": (f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
                        f"{os.environ['GITHUB_RUN_ID']}"),
            "python": sys.version,
            "runner_os": os.environ["RUNNER_OS"],
            "runner_image": os.environ.get("ImageVersion"),
            "build_jobs_maximum": 2,
            "compiled_cache_restored": False,
        }
        self.replacements = sorted(
            [(str(BUNDLE), "$BUNDLE"), (str(temporary), "$RUNNER_TEMP"),
             (str(Path.home()), "$HOME")], key=lambda item: -len(item[0]),
        )

    def public(self, text):
        for original, replacement in self.replacements:
            text = text.replace(original, replacement)
        return text

    def save(self):
        for name, data in (("commands.json", self.commands),
                           ("environment.json", self.environment)):
            (self.output / name).write_text(json.dumps(data, indent=2) + "\n",
                                           encoding="utf-8")

    def run(self, label, argv, *, cwd=BUNDLE, timeout=600):
        start = time.monotonic()
        outcome = {
            "step": label, "command": self.public(shlex.join(map(str, argv))),
            "cwd": self.public(str(cwd)), "exit_code": None,
        }
        print(f"Running {label}: {outcome['command']}", flush=True)
        with tempfile.TemporaryFile() as log:
            try:
                completed = subprocess.run(
                    list(map(str, argv)), cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                    timeout=timeout, check=False,
                )
                outcome["exit_code"] = completed.returncode
            except subprocess.TimeoutExpired:
                outcome["exit_code"] = 124
                outcome["error"] = f"Timed out after {timeout} seconds"
            except OSError as exc:
                outcome["error"] = self.public(str(exc))
            log.seek(0, 2)
            size = log.tell()
            log.seek(max(0, size - LOG_LIMIT))
            text = self.public(log.read().decode("utf-8", errors="replace"))
            text = text.encode("utf-8")[-LOG_LIMIT:].decode("utf-8", errors="ignore")
        outcome["seconds"] = round(time.monotonic() - start, 3)
        outcome["log_truncated"] = size > LOG_LIMIT
        (self.output / "logs" / f"{label}.log").write_text(text, encoding="utf-8")
        self.commands.append(outcome)
        self.save()
        if outcome["exit_code"] != 0:
            print(text[-8_000:], file=sys.stderr)
            raise RuntimeError(f"{label} failed: {outcome}")
        return text

    def capture_results(self):
        hashes = {}
        for suite in ("cache", "core"):
            source = self.checkout / "build/fetch_error_pilot" / f"replayed_{suite}.json"
            if source.is_file():
                data = source.read_bytes()
                if len(data) > 1_000_000:
                    raise RuntimeError(f"{suite} replay JSON exceeds artifact size limit")
                (self.output / source.name).write_bytes(data)
                hashes[source.name] = hashlib.sha256(data).hexdigest()
        binary = self.checkout / "build/fetch_error_pilot/system_pilot/Vibex_simple_system"
        if binary.is_file():
            digest = hashlib.sha256()
            with binary.open("rb") as stream:
                for block in iter(lambda: stream.read(1_048_576), b""):
                    digest.update(block)
            hashes["whole_core_binary_sha256_only"] = digest.hexdigest()
        (self.output / "hashes.json").write_text(json.dumps(hashes, indent=2) + "\n",
                                              encoding="utf-8")

    def execute(self):
        if sys.version_info[:3] != (3, 12, 3):
            raise RuntimeError("Fresh replay requires exactly Python 3.12.3")
        if (BUNDLE / "UPSTREAM_COMMIT").read_text().strip() != PIN:
            raise RuntimeError("Bundle upstream pin changed")
        self.environment["bundle_commit"] = self.run(
            "bundle-version", ["git", "rev-parse", "HEAD"],
        ).strip()
        self.environment["ubuntu"] = Path("/etc/os-release").read_text()
        if 'VERSION_ID="24.04"' not in self.environment["ubuntu"]:
            raise RuntimeError("Fresh replay requires Ubuntu 24.04")
        self.run("apt-update", ["sudo", "apt-get", "-qq", "update"])
        self.run("apt-install", ["sudo", "apt-get", "-y", "--no-install-recommends",
                                 "install", "verilator=5.020-1", "g++-13",
                                 "make", "libelf-dev"])
        self.environment["apt_packages"] = self.run(
            "apt-versions", ["dpkg-query", "-W", "-f=${Package}=${Version}\n",
                             "verilator", "g++-13", "make", "libelf-dev"],
        ).strip().splitlines()
        self.run("pip-install", [sys.executable, "-m", "pip", "install",
                                 "--no-cache-dir", "fusesoc==2.4.3", "edalize==0.6.8"])
        self.environment["python_packages"] = self.run(
            "pip-versions", [sys.executable, "-m", "pip", "freeze", "--all"],
        ).strip().splitlines()
        for name, version in (("fusesoc", "2.4.3"), ("edalize", "0.6.8")):
            if importlib.metadata.version(name) != version:
                raise RuntimeError(f"Installed {name} version differs from {version}")
        self.environment["verilator"] = self.run(
            "verilator-version", ["verilator", "--version"],
        ).strip()
        if self.environment["verilator"] != "Verilator 5.020 2024-01-01 rev (Debian 5.020-1)":
            raise RuntimeError("Installed Verilator version differs from frozen evidence")
        self.environment["compiler"] = self.run(
            "compiler-version", ["g++-13", "-dumpfullversion"],
        ).strip()
        if self.environment["compiler"] != "13.3.0":
            raise RuntimeError("Installed g++-13 must be 13.3.0")
        self.environment["make"] = self.run("make-version", ["make", "--version"]).splitlines()[0]
        if self.environment["make"] != "GNU Make 4.3":
            raise RuntimeError("Installed GNU make must be 4.3")
        os.environ.update(CXX="g++-13", CC="gcc-13", MAKEFLAGS="-j2")
        self.run("upstream-clone", ["git", "clone", "--no-checkout", "--depth=1",
                                    "https://github.com/lowRISC/ibex.git", self.checkout])
        self.run("upstream-fetch", ["git", "-C", self.checkout, "fetch", "--depth=1",
                                    "origin", PIN])
        self.run("upstream-line-endings", ["git", "-C", self.checkout, "config",
                                          "--local", "core.autocrlf", "true"])
        self.run("upstream-checkout", ["git", "-C", self.checkout, "checkout",
                                      "--detach", PIN])
        actual = self.run("upstream-version", ["git", "-C", self.checkout,
                                              "rev-parse", "HEAD"]).strip()
        if actual != PIN:
            raise RuntimeError("Upstream checkout is not at the required commit")
        self.run("stage", [sys.executable, "-B", BUNDLE / "scripts/stage.py",
                           "--checkout", self.checkout])
        self.run("staged-status", ["git", "-C", self.checkout, "status", "--short"])
        pilot = self.checkout / "dv/verilator/icache_fetch_fault"
        self.run("standalone-replay", [sys.executable, pilot / "run.py", "--trace",
                                      "--output", "build/fetch_error_pilot/replayed_cache.json"],
                 cwd=self.checkout)
        fusesoc = ["fusesoc", "--cores-root=.", "run"]
        core = "lowrisc:ibex:ibex_simple_system"
        help_text = self.run("backend-options", fusesoc + ["--target=sim", core, "--help"],
                             cwd=self.checkout)
        if "--make_options" not in help_text:
            raise RuntimeError("Pinned backend does not expose the required make_options cap")
        self.run("core-build", fusesoc + [
            "--target=sim", "--work-root=build/fetch_error_pilot/system_pilot",
            "--setup", "--build", core, "--make_options=-j2",
            "--ICache=1", "--FetchFaultPilot=1",
        ], cwd=self.checkout, timeout=1_200)
        self.run("core-replay", [sys.executable, pilot / "run_core.py",
                                "--output", "build/fetch_error_pilot/replayed_core.json"],
                 cwd=self.checkout)
        self.run("default-off-lint", fusesoc + [
            "--target=lint", "--work-root=build/fetch_error_pilot/lint_default",
            "--setup", "--build", core, "--make_options=-j2", "--ICache=1",
        ], cwd=self.checkout)
        self.run("strict-compare", [
            sys.executable, "-B", BUNDLE / "scripts/compare.py",
            "--cache", "build/fetch_error_pilot/replayed_cache.json",
            "--core", "build/fetch_error_pilot/replayed_core.json",
        ], cwd=self.checkout)
        self.run("final-package-audit", [sys.executable, "-B", BUNDLE / "scripts/audit.py"])
        summary = {"kind": "fresh automated RTL, NOT human-run", "pass": True}
        for suite in ("cache", "core"):
            data = load_json(self.checkout / "build/fetch_error_pilot" /
                             f"replayed_{suite}.json")
            if set(data["cases"]) != {"hit_control", "speculative_hit", "demand_miss"}:
                raise RuntimeError(f"{suite}: incomplete three-case suite")
            count = sum(case["pass"] is True for case in data["cases"].values())
            if data["pass"] is not True or count != 3:
                raise RuntimeError(f"{suite}: not all three cases passed")
            summary[f"{suite}_passed"] = count
            summary[f"{suite}_total"] = 3
        summary["required_commands_exit_zero"] = all(
            command["exit_code"] == 0 for command in self.commands)
        (self.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                               encoding="utf-8")
        print(json.dumps(summary), flush=True)


def main():
    if (os.environ.get("GITHUB_ACTIONS") != "true" or
            os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted" or
            os.environ.get("RUNNER_OS") != "Linux"):
        raise SystemExit("Refusing installation/build outside a GitHub-hosted Linux runner")
    replay = Replay(Path(os.environ["RUNNER_TEMP"]))
    try:
        replay.execute()
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        replay.environment["failure"] = replay.public(str(exc))
        print(f"Fresh replay failed: {replay.environment['failure']}", file=sys.stderr)
        return 1
    finally:
        replay.capture_results()
        replay.save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
