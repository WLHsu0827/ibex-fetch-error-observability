# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Hosted-only preparation and single-attempt pair; always closes raw receipts."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
import traceback

from .check import qualify
from .isa import BOOT, MAX_CYCLES, freeze
from .process import expected_fatal, identity, require_success, run, write_json
from .seal import ROOT, verify
from .tests import tiny_contract


class Hosted:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.output = Path(args.output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.auth = json.loads((ROOT / "rvfi_nextpc" / "AUTHORIZATION.json").read_text())
        self.work = Path("/tmp") / f"rvfi-nextpc-{os.environ.get('GITHUB_RUN_ID', 'human')}"
        self.stage = 0
        self.deadline = time.monotonic() + 55 * 60
        self.summary: dict[str, object] = {
            "schema": 1, "result": "STOP", "mode": args.mode,
            "source_sha": args.source_sha, "authorization": args.authorization,
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "preparation_run": args.preparation_run, "real_compilations": [],
        }
        write_json(self.output / "dispatch-input.json", {
            "schema": 1, "mode": args.mode, "source_sha": args.source_sha,
            "authorization": args.authorization, "preparation_run": args.preparation_run,
            "preparation_attempt": args.preparation_attempt,
            "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        })

    def command(self, name: str, argv: list[str], cwd: Path | None = None,
                timeout: float = 300, check: bool = True) -> dict[str, object]:
        self.stage += 1
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("STOP: hosted pipeline wall-time budget")
        status = run(argv, cwd or self.work, self.output, f"{self.stage:02d}-{name}",
                     min(timeout, remaining))
        if check:
            require_success(status)
        return status

    def last_stdout(self) -> bytes:
        return next(self.output.glob(f"{self.stage:02d}-*.stdout.log")).read_bytes()

    def guard(self) -> None:
        if platform.system() != "Linux" or os.environ.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("STOP: agent replay requires a GitHub-hosted Linux dispatch")
        if os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
            raise RuntimeError("STOP: self-hosted runners are outside authorization")
        if self.args.authorization != self.auth["identity"]:
            raise RuntimeError("STOP: authorization identity mismatch")
        if os.environ.get("GITHUB_REPOSITORY") != self.auth["repository"]:
            raise RuntimeError("STOP: repository mismatch")
        if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
            raise RuntimeError("STOP: reruns are not authorized")
        if len(self.args.source_sha) != 40 or any(c not in "0123456789abcdef" for c in self.args.source_sha):
            raise RuntimeError("STOP: full immutable source SHA required")
        self.command("input-head", ["git", "rev-parse", "HEAD"], ROOT)
        if self.last_stdout().decode().strip() != self.args.source_sha:
            raise RuntimeError("STOP: checkout/source SHA mismatch")
        verify()
        self.command("input-clean", ["git", "diff", "--exit-code", "HEAD"], ROOT)
        self.command("attempt-history", [
            "gh", "api", f"repos/{self.auth['repository']}/actions/workflows/rvfi-nextpc.yml/runs?per_page=100",
            "--jq", "{total_count, runs:[.workflow_runs[]|{id,head_sha,display_title,event,run_attempt,status,conclusion}]}",
        ], ROOT)
        history = json.loads(self.last_stdout())
        if history["total_count"] > 100:
            raise RuntimeError("STOP: bounded history page insufficient")
        authorized = [r for r in history["runs"]
                      if r["event"] == "workflow_dispatch" and self.auth["identity"] in r["display_title"]]
        prepares = [r for r in authorized if " prepare " in r["display_title"]]
        pairs = [r for r in authorized if " pair " in r["display_title"]]
        if len(prepares) > 2 or len(pairs) > 1:
            raise RuntimeError("STOP: authorization attempt budget exhausted")
        current = [r for r in authorized if str(r["id"]) == os.environ["GITHUB_RUN_ID"]]
        if len(current) != 1 or current[0]["head_sha"] != self.args.source_sha:
            raise RuntimeError("STOP: workflow/source binding mismatch")
        if self.args.mode == "prepare":
            if pairs or self.args.preparation_attempt != len(prepares):
                raise RuntimeError("STOP: invalid preparation journal sequence")
        else:
            previous = [r for r in prepares if str(r["id"]) == self.args.preparation_run]
            if len(previous) != 1 or previous[0]["conclusion"] != "success":
                raise RuntimeError("STOP: missing successful preparation run")
            if previous[0]["head_sha"] != self.args.source_sha:
                raise RuntimeError("STOP: changed inputs require requalification")
            if len(pairs) != 1:
                raise RuntimeError("STOP: pair journal mismatch")
        write_json(self.output / "attempt.json", {
            "schema": 1, "authorization": self.auth, "source_sha": self.args.source_sha,
            "run_id": os.environ["GITHUB_RUN_ID"], "run_attempt": 1,
            "mode": self.args.mode, "preparation_attempt": self.args.preparation_attempt,
            "preparation_run": self.args.preparation_run, "history": authorized,
            "receipt_semantics": "exclusive creation in this run; GitHub history is the attempt gate",
        })

    def setup(self) -> None:
        self.work.mkdir(exist_ok=False)
        (self.output / "input").mkdir()
        shutil.copytree(ROOT / "rvfi_nextpc", self.work / "inputs" / "rvfi_nextpc",
                        ignore=shutil.ignore_patterns("evidence", "__pycache__"))
        for filename in verify()["files"]:
            destination = self.output / "input" / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / filename, destination)
        shutil.copyfile(ROOT / "rvfi_nextpc" / "SOURCE_MANIFEST.json",
                        self.output / "input" / "rvfi_nextpc" / "SOURCE_MANIFEST.json")
        release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines()
                       if "=" in line)
        memory = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                          if line.startswith("MemTotal:"))) * 1024
        disk = shutil.disk_usage(self.work)
        cpus = len(os.sched_getaffinity(0))
        preflight = {
            "os_id": release["ID"].strip('"'), "os_version": release["VERSION_ID"].strip('"'),
            "python": platform.python_version(), "affinity_cpus": cpus,
            "reported_memtotal_bytes": memory, "free_disk_bytes": disk.free,
            "runner_environment": os.environ["RUNNER_ENVIRONMENT"],
            "runner_os": os.environ["RUNNER_OS"], "make_workers": 1,
            "limitations": "reported hosted values; no exclusivity, local floor or PPA/performance claim",
        }
        for name in ("memory.max", "cpu.max"):
            path = Path("/sys/fs/cgroup") / name
            if path.exists():
                preflight[name] = path.read_text().strip()
        write_json(self.output / "preflight.json", preflight)
        if preflight["os_id"] != "ubuntu" or preflight["os_version"] != "24.04":
            raise RuntimeError("STOP: Ubuntu 24.04 required")
        if cpus < 1 or memory < 2 * 1024**3 or disk.free < 8 * 1024**3:
            raise RuntimeError("STOP: insufficient reported hosted resources")
        os.environ.update(MAKEFLAGS="-j1", CMAKE_BUILD_PARALLEL_LEVEL="1", PYTHONDONTWRITEBYTECODE="1")
        self.command("offline-contracts", [sys.executable, "-B", "-m", "unittest", "rvfi_nextpc.tests", "-v"], ROOT)
        self.command("apt-update", ["sudo", "apt-get", "update", "-qq"], timeout=480)
        self.command("apt-tools", [
            "sudo", "apt-get", "install", "-y", "--no-install-recommends",
            "verilator=5.020-1", "gcc-riscv64-unknown-elf=13.2.0-11ubuntu1+12",
            "binutils-riscv64-unknown-elf=2.42-1ubuntu1+6",
        ], timeout=480)
        self.command("package-versions", [
            "dpkg-query", "-W", "-f=${Package}=${Version}\\n", "verilator",
            "gcc-riscv64-unknown-elf", "binutils-riscv64-unknown-elf",
        ])
        packages = self.last_stdout().decode()
        required = ("verilator=5.020-1", "gcc-riscv64-unknown-elf=13.2.0-11ubuntu1+12",
                    "binutils-riscv64-unknown-elf=2.42-1ubuntu1+6")
        if set(packages.splitlines()) != set(required):
            raise RuntimeError("STOP: installed package version mismatch")
        self.command("venv", [sys.executable, "-m", "venv", "tools"])
        self.python = self.work / "tools" / "bin" / "python"
        self.fusesoc = self.work / "tools" / "bin" / "fusesoc"
        os.environ["PATH"] = str(self.work / "tools" / "bin") + os.pathsep + os.environ["PATH"]
        self.command("python-tools", [
            str(self.python), "-m", "pip", "install", "--disable-pip-version-check",
            "--report", str(self.work / "pip-install.json"),
            "-r", "inputs/rvfi_nextpc/requirements.txt",
        ], timeout=480)
        pins = dict(line.split("==") for line in (ROOT / "rvfi_nextpc" / "requirements.txt").read_text().splitlines()
                    if "==" in line)
        normalize = lambda name: name.lower().replace("_", "-")
        pins = {normalize(name): version for name, version in pins.items()}
        report = json.loads((self.work / "pip-install.json").read_text())
        write_json(self.output / "pip-install.json", {
            "schema": 1,
            "packages": [{"name": item["metadata"]["name"], "version": item["metadata"]["version"],
                          "download_info": item["download_info"], "license": item["metadata"].get("license"),
                          "classifiers": item["metadata"].get("classifiers", [])}
                         for item in report["install"]],
            "boundary": "whitelisted dependency identities, not an environment or author-email dump",
        })
        installed = {normalize(item["metadata"]["name"]): item["metadata"]["version"]
                     for item in report["install"]}
        if installed != pins:
            raise RuntimeError(f"STOP: unpinned dependency closure: {installed}")
        self.command("tool-versions", [
            str(self.python), "-c",
            "import importlib.metadata as m,json; print(json.dumps([{"
            "'name':d.metadata['Name'],'version':d.version,'license':d.metadata.get('License'),"
            "'classifiers':d.metadata.get_all('Classifier',[])} for d in m.distributions()],sort_keys=True))",
        ])
        self.command("verilator-version", ["verilator", "--version"])
        if not self.last_stdout().decode().startswith("Verilator 5.020 "):
            raise RuntimeError("STOP: Verilator version mismatch")
        self.command("cxx-version", ["c++", "--version"])
        self.command("gcc-version", ["riscv64-unknown-elf-gcc", "--version"])
        self.command("binutils-version", ["riscv64-unknown-elf-objcopy", "--version"])
        self.tool_identities = {
            name: identity(Path(shutil.which(name)).resolve())
            for name in ("verilator", "c++", "make", "riscv64-unknown-elf-gcc",
                         "riscv64-unknown-elf-objcopy", "python3", "fusesoc")
        }
        write_json(self.output / "tool-identities.json", self.tool_identities)
        self.command("git-init", ["git", "init", "-q", "upstream"])
        upstream = self.work / "upstream"
        self.command("git-origin", ["git", "remote", "add", "origin", "https://github.com/lowRISC/ibex.git"], upstream)
        self.command("git-fetch", ["git", "fetch", "-q", "--depth=1", "origin", self.auth["ibex"]], upstream)
        self.command("git-checkout", ["git", "checkout", "-q", "--detach", "FETCH_HEAD"], upstream)
        self.command("stock-head", ["git", "rev-parse", "HEAD"], upstream)
        if self.last_stdout().decode().strip() != self.auth["ibex"]:
            raise RuntimeError("STOP: stock RTL SHA mismatch")
        self.command("stock-clean", ["git", "diff", "--exit-code", "HEAD"], upstream)
        notices = self.output / "public-notices"
        notices.mkdir()
        for name in ("LICENSE", "NOTICE"):
            shutil.copyfile(upstream / name, notices / f"ibex-{name}")
        for package in ("verilator", "gcc-riscv64-unknown-elf", "binutils-riscv64-unknown-elf"):
            shutil.copyfile(Path("/usr/share/doc") / package / "copyright", notices / f"{package}-copyright")

    def configure(self, bp: int) -> tuple[Path, dict[str, object]]:
        label = "off" if bp == 0 else "on"
        build = self.work / "builds" / label
        self.command(f"configure-{label}", [
            str(self.fusesoc), "--cores-root=upstream", "--cores-root=inputs/rvfi_nextpc",
            "run", "--setup", "--target=sim", f"--build-root={build}",
            "wlh:observations:nextpc:1.0", f"--BranchPredictor={bp}",
        ])
        edam_path = next(build.glob("*.eda.yml"))
        self.command(f"edam-{label}", [
            str(self.python), "-c",
            "import json,sys,yaml; print(json.dumps(yaml.safe_load(open(sys.argv[1])),sort_keys=True))",
            str(edam_path),
        ])
        edam = json.loads(self.last_stdout())
        files = {item["name"]: identity(build / item["name"]) for item in edam["files"]}
        destination = self.output / label
        destination.mkdir()
        shutil.copyfile(edam_path, destination / "effective.eda.yml")
        for path in build.glob("*.vc"):
            shutil.copyfile(path, destination / path.name)
        shutil.copyfile(build / "Makefile", destination / "Makefile")
        config = {
            "BranchPredictor": bp, "WritebackStage": 0, "BranchTargetALU": 0,
            "RV32ZC": "RV32Zca", "RV32M": "RV32MFast", "RV32B": "RV32BNone",
            "RegFile": "RegFileFF", "BaseIsa": "BaseIsaRV32I", "RV32E": 0,
            "ICache": 0, "ICacheECC": 0, "ICacheScramble": 0, "SecureIbex": 0,
            "DbgTriggerEn": 0, "PMPEnable": 0, "PMPGranularity": 0,
            "PMPNumRegions": 4, "MHPMCounterNum": 0, "MHPMCounterWidth": 40, "RVFI": 1,
            "other_parameters": "unchanged pinned ibex_top defaults; hashed source, no core modification",
        }
        write_json(destination / "config.json", config)
        write_json(destination / "compiled-sources.json", files)
        return build, edam

    def lint(self, bp: int, build: Path, edam: dict[str, object]) -> None:
        args = ["verilator", "--lint-only", "-Wall", "--unroll-count", "72",
                "--top-module", "nextpc_top", "+define+RVFI", "+define+OBSERVER_TARGET=ibex_top",
                f"-GBranchPredictor={bp}"]
        for item in edam["files"]:
            if item.get("is_include_file"):
                args.append(f"-I{Path(item['name']).parent}")
        # Only the unaltered stock .vlt is used. No new lint disable/waiver/nonfatal switch.
        for kind in ("vlt", "systemVerilogSource", "verilogSource"):
            args += [item["name"] for item in edam["files"]
                     if item["file_type"] == kind and not item.get("is_include_file")]
        self.command(f"fatal-warning-bind-lint-{bp}", args, build, timeout=300)

    def miniature(self) -> None:
        build = self.work / "miniature"
        self.command("miniature-build", [
            "verilator", "--cc", "--exe", "--build", "-j", "1", "-Wall",
            "--top-module", "sampler_fixture", "-DOBSERVER_TARGET=sampler_fixture",
            "--Mdir", str(build), "-CFLAGS", "-std=c++17 -Wall -Wextra -Werror",
            str(self.work / "inputs/rvfi_nextpc/sampler_fixture.sv"),
            str(self.work / "inputs/rvfi_nextpc/rvfi_observer.sv"),
            str(self.work / "inputs/rvfi_nextpc/fixture.cpp"),
        ], timeout=300)
        results: dict[str, object] = {}
        for scenario in ("good", "no_reset", "reset_again"):
            destination = self.output / f"miniature-{scenario}"
            destination.mkdir()
            status = self.command(f"miniature-{scenario}", [
                str(build / "Vsampler_fixture"), scenario, str(destination / "cpp.tsv"),
                f"+sv_log={destination / 'sv.tsv'}",
            ], timeout=10, check=False)
            if scenario == "good":
                require_success(status)
                image, contract = tiny_contract()
                results[scenario] = qualify(destination / "cpp.tsv", destination / "sv.tsv", image, contract)
            else:
                prefix = f"{self.stage:02d}-miniature-{scenario}"
                text = (self.output / f"{prefix}.stdout.log").read_bytes() + (
                    self.output / f"{prefix}.stderr.log").read_bytes()
                marker = b"NEXTPC_MISSING_RESET" if scenario == "no_reset" else b"NEXTPC_RESET_AFTER_START"
                if not expected_fatal(status, text, marker):
                    raise RuntimeError(f"STOP: miniature {scenario} was not a prompt SIGABRT + marker")
                if scenario == "reset_again" and b"R\t" not in (destination / "sv.tsv").read_bytes():
                    raise RuntimeError("STOP: reset fixture did not preserve preceding observations")
                results[scenario] = {"expected_negative": "PASS", "kind": status["kind"], "code": status["code"]}
        write_json(self.output / "miniature-qualification.json", results)

    def program(self) -> tuple[bytes, dict[str, object]]:
        self.command("compile-program-once", [
            "riscv64-unknown-elf-gcc", "-march=rv32ic", "-mabi=ilp32", "-nostdlib", "-nostartfiles",
            "-Wl,--no-relax", "-T", "inputs/rvfi_nextpc/link.ld", "inputs/rvfi_nextpc/program.S",
            "-o", "fresh.elf",
        ])
        self.command("program-bytes", ["riscv64-unknown-elf-objcopy", "-O", "binary", "fresh.elf", "fresh.bin"])
        self.command("program-symbols", ["riscv64-unknown-elf-nm", "-n", "fresh.elf"])
        symbols = {parts[2]: int(parts[0], 16) for line in self.last_stdout().decode().splitlines()
                   if len(parts := line.split()) == 3}
        if symbols["_start"] != BOOT:
            raise RuntimeError("STOP: boot/image mismatch")
        image = (self.work / "fresh.bin").read_bytes()
        contract = freeze(image, symbols["drain"], symbols["terminal"])
        shutil.copyfile(self.work / "fresh.elf", self.output / "fresh.elf")
        shutil.copyfile(self.work / "fresh.bin", self.output / "fresh.bin")
        write_json(self.output / "program-contract.json", contract)
        self.command("program-disassembly", ["riscv64-unknown-elf-objdump", "-d", "fresh.elf"])
        return image, contract

    def compare_inputs(self, builds: list[tuple[Path, dict[str, object]]]) -> None:
        first, second = [json.loads((self.output / label / "compiled-sources.json").read_text())
                         for label in ("off", "on")]
        if first != second:
            raise RuntimeError("STOP: OFF/ON compiled source mismatch")
        configs = [json.loads((self.output / label / "config.json").read_text()) for label in ("off", "on")]
        if configs[0] | {"BranchPredictor": 1} != configs[1]:
            raise RuntimeError("STOP: OFF/ON effective configuration mismatch")
        edams = [json.loads(json.dumps(edam)) for _, edam in builds]
        for edam in edams:
            if edam["parameters"]["BranchPredictor"]["default"] not in (0, 1):
                raise RuntimeError("STOP: unexpected exported BranchPredictor value")
            edam["parameters"]["BranchPredictor"]["default"] = 0
        if edams[0] != edams[1]:
            raise RuntimeError("STOP: exported EDAM differs beyond BranchPredictor")
        a, b = [json.dumps(config, indent=2, sort_keys=True).splitlines(True) for config in configs]
        with (self.output / "config.diff").open("x", encoding="ascii") as stream:
            stream.writelines(difflib.unified_diff(a, b, fromfile="off", tofile="on"))
        write_json(self.output / "input-equivalence.json", {
            "result": "PASS", "only_effective_difference": "BranchPredictor 0 -> 1",
            "compiled_sources_equal": True, "normalized_edam_equal": True,
        })

    def measure(self, bp: int, build: Path, image: bytes, contract: dict[str, object]) -> dict[str, object]:
        label = "off" if bp == 0 else "on"
        verify()
        if self.tool_identities != {
            name: identity(Path(shutil.which(name)).resolve()) for name in self.tool_identities
        }:
            raise RuntimeError("STOP: frozen executable tool identity changed")
        write_json(self.output / f"{label}.compile-started.json", {
            "source_sha": self.args.source_sha, "freeze": identity(self.output / "freeze.json"),
            "label": label, "retry_allowed": False,
        })
        self.summary["real_compilations"].append(label)
        self.command(f"{label}-compile-once", ["make", "-j1", "NUM_JOBS=1"], build, timeout=1500)
        binary = build / "Vnextpc_top"
        if not binary.exists():
            binary = build / "obj_dir" / "Vnextpc_top"
        if not binary.is_file():
            raise RuntimeError("STOP: missing actual model executable")
        write_json(self.output / label / "model-identity.json", identity(binary))
        destination = self.output / label
        status = self.command(f"{label}-run-once", [
            str(binary), str(self.work / "fresh.bin"), str(destination / "cpp.tsv"),
            str(contract["terminal"]), str(MAX_CYCLES), f"+sv_log={destination / 'sv.tsv'}",
        ], timeout=60)
        prefix = f"{self.stage:02d}-{label}-run-once"
        text = (self.output / f"{prefix}.stdout.log").read_text()
        if f"NEXTPC_CONFIG BP={bp} WB=0 BTA=0 ZC=0 IC=0" not in text or "NEXTPC_COMPLETE" not in text:
            raise RuntimeError("STOP: model configuration/termination identity mismatch")
        if identity(self.work / "fresh.bin") != identity(self.output / "fresh.bin"):
            raise RuntimeError("STOP: loaded program bytes changed")
        result = qualify(destination / "cpp.tsv", destination / "sv.tsv", image, contract)
        result["process"] = {"kind": status["kind"], "code": status["code"]}
        write_json(destination / "qualification.json", result)
        self.summary[label] = result
        verify()
        return result

    def execute(self) -> None:
        self.guard()
        self.setup()
        self.miniature()
        builds = [self.configure(bp) for bp in (0, 1)]
        for bp, (build, edam) in enumerate(builds):
            self.lint(bp, build, edam)
        self.compare_inputs(builds)
        if self.args.mode == "prepare":
            self.summary.update(result="PREPARATION_PASS", scientific_result="NOT_RUN")
            return
        image, contract = self.program()
        frozen = {
            "schema": 1, "source_sha": self.args.source_sha, "ibex_sha": self.auth["ibex"],
            "authorization": self.auth["identity"], "run_id": os.environ["GITHUB_RUN_ID"],
            "source_manifest": verify(), "program_elf": identity(self.output / "fresh.elf"),
            "program_bytes": identity(self.output / "fresh.bin"),
            "contract": identity(self.output / "program-contract.json"),
            "equivalence": identity(self.output / "input-equivalence.json"),
            "prior_receipts": {p.relative_to(self.output).as_posix(): identity(p)
                               for p in sorted(self.output.rglob("*")) if p.is_file()},
            "receipt_semantics": "exclusive freeze closed before first real CPU compile; not a trusted timestamp",
        }
        write_json(self.output / "freeze.json", frozen)
        off = self.measure(0, builds[0][0], image, contract)
        if off["strict_next_pc"] != "PASS":
            raise RuntimeError("STOP: OFF strict metadata failed; ON not authorized")
        on = self.measure(1, builds[1][0], image, contract)
        self.summary.update(result="PAIR_OBSERVED",
                            scientific_result="FAIL" if on["strict_next_pc"] == "FAIL" else "PASS",
                            interpretation="output-port observation only; no overall pair PASS or DUT/novelty claim")

    def close(self, error: Exception | None) -> None:
        if error is not None:
            self.summary["error"] = str(error)
            with (self.output / "pipeline-error.log").open("x", encoding="ascii", errors="backslashreplace") as stream:
                traceback.print_exception(error, file=stream)
        self.summary["attempted_stages"] = self.stage
        write_json(self.output / "summary.json", self.summary)
        write_json(self.output / "RAW_MANIFEST.json", {
            "schema": 1, "source_sha": self.args.source_sha, "run_id": os.environ.get("GITHUB_RUN_ID"),
            "files": {p.relative_to(self.output).as_posix(): identity(p)
                      for p in sorted(self.output.rglob("*")) if p.is_file()},
            "self_hash": "intentionally absent; immutable artifact/commit identity is the outer closure",
        })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("prepare", "pair"))
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--authorization", required=True)
    parser.add_argument("--preparation-attempt", type=int, default=0)
    parser.add_argument("--preparation-run", default="")
    parser.add_argument("--output", default="nextpc-output")
    args = parser.parse_args()
    pipeline = Hosted(args)
    error = None
    try:
        pipeline.execute()
    except Exception as caught:
        error = caught
        print(f"NEXTPC_PIPELINE_STOP: {caught}", file=sys.stderr, flush=True)
    finally:
        pipeline.close(error)
    print(json.dumps(pipeline.summary, sort_keys=True), flush=True)
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
