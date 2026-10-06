# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Real GNU make on disposable synthetic recipes only: no compiler/HDL/model."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from .archive import privacy_review
from .drivers import DRIVERS, PROBE_FIELDS, read_probe
from .hosted import Hosted
from .process import identity, require_success, run, write_json
from .seal import ROOT, verify

OUTPUT: Path
CASES: list[dict[str, object]] = []
MODELS = ("Vsampler_fixture.mk", "Vnextpc_top.mk")
FIXTURE = """# Synthetic variables only; no generated RTL or compiler recipes.
.PHONY: forbidden-build
forbidden-build:
\t$(error CODE_ONLY forbids any model/CPU/program build)
CXX = unqualified-default
CC = unqualified-default
LINK = unqualified-default
AR = unqualified-default
PYTHON3 = unqualified-default
PERL = unqualified-default
OBJCACHE = unqualified-default
NUM_JOBS = unqualified-default
define FIXTURE_VALUE_END

NEXTPC_END_VALUE
endef
nextpc-driver-probe: fixture-capture
.PHONY: fixture-capture
fixture-capture:
\t$(file >fixture-MAKEFLAGS,$(MAKEFLAGS)$(FIXTURE_VALUE_END))
\t$(file >fixture-MFLAGS,$(MFLAGS)$(FIXTURE_VALUE_END))
"""


class MakeContracts(unittest.TestCase):
    def attempt(self, name: str, model: str, extra: list[str] | None = None,
                addition: str = "", timeout: float = 10) -> tuple[dict[str, object], Path]:
        destination = OUTPUT / name
        destination.mkdir()
        with tempfile.TemporaryDirectory(prefix="rvfi-code-only-make-") as temp:
            build = Path(temp) / "synthetic output with spaces"
            build.mkdir()
            (build / model).write_text(FIXTURE + addition, encoding="ascii", newline="\n")
            work = Path(temp) / "public inputs"
            source = work / "inputs" / "rvfi_nextpc"
            source.mkdir(parents=True)
            shutil.copyfile(ROOT / "rvfi_nextpc" / "driver_probe.mk", source / "driver_probe.mk")
            hosted = Hosted.__new__(Hosted)
            hosted.work, hosted.installed_make = work, build / model
            attempted = []

            def command(stage: str, argv: list[str], cwd: Path, **kwargs: object) -> dict[str, object]:
                self.assertEqual(stage, "synthetic-code-only-probe")
                self.assertEqual(argv[-1], "nextpc-outer-driver-probe")
                self.assertEqual(kwargs["timeout"], 10)
                status = run([*argv, *(extra or [])], cwd, destination, "make", timeout)
                attempted.append(status)
                require_success(status)
                return status

            hosted.command = command
            try:
                receipt = hosted.probe_drivers(build, model, destination / "fields",
                                               "synthetic-code-only-probe")
            except ValueError as error:
                write_json(destination / "validation.json", {"result": "REJECTED", "error": str(error)})
            except RuntimeError:
                self.assertEqual(len(attempted), 1)
                self.assertNotEqual((attempted[0]["kind"], attempted[0]["code"]), ("exited", 0))
            else:
                self.assertEqual(set(receipt["expanded"]), set(PROBE_FIELDS))
                self.assertEqual(set(receipt["fields"]), set(PROBE_FIELDS))
                self.assertEqual(receipt["schema"], 2)
                self.assertEqual(receipt["result"], "PASS")
                receipt["boundary"] = "SYNTHETIC recipe only; installed_make slot identifies this fixture, not a Verilator include or actual model."
                write_json(destination / "validation.json", receipt)
            self.assertEqual(len(attempted), 1)
            status = attempted[0]
            shutil.copyfile(build / model, destination / model)
            for field in ("MAKEFLAGS", "MFLAGS"):
                path = build / ("fixture-" + field)
                if path.exists():
                    shutil.copyfile(path, destination / path.name)
            if status["kind"] == "exited" and status["code"] == 0:
                for field in ("MAKEFLAGS", "MFLAGS"):
                    self.assertEqual((destination / ("fixture-" + field)).read_bytes(),
                                     (destination / "fields" / field).read_bytes())
            CASES.append({"name": name, "model": model, "status": status["kind"],
                          "code": status["code"], "original_status": identity(destination / "make.status.json")})
        return status, destination

    def test_same_shared_path_for_both_model_names(self) -> None:
        flags = [
            [],
            ["NOTE=spaces 'quotes' \"double\" (parentheses) --eval=literal"],
            ["--eval", "NEXTPC_TEXT := spaces 'unmatched (parentheses) --eval=literal"],
            ["--eval", "define NEXTPC_TEXT\nspaces 'quotes' (parentheses)\nendef"],
        ]
        for model in MODELS:
            for number, extra in enumerate(flags):
                with self.subTest(model=model, flags=number):
                    status, destination = self.attempt(f"{model}-good-{number}", model, extra)
                    require_success(status)
                    receipt = json.loads((destination / "validation.json").read_bytes())
                    self.assertEqual(receipt["result"], "PASS")
                    values = receipt["expanded"]
                    self.assertEqual(values["NEXTPC_PROBE_MAKEFILE"], model)
                    self.assertEqual(values["MAKELEVEL"], "1")
                    self.assertEqual(values["NUM_JOBS"], "1")
                    if number:
                        self.assertIn("parentheses", values["MAKEFLAGS"])
                        self.assertIn("'", values["MAKEFLAGS"])
                    self.assertEqual({key: values[key] for key in DRIVERS}, DRIVERS)

    def test_wrong_drivers_workers_and_actual_parallelism_rejected(self) -> None:
        mutations = [[f"{key}=unqualified"] for key in DRIVERS]
        mutations += [["NUM_JOBS=2"], ["-j2"], ["-j"], ["--jobs=3"]]
        for model in MODELS:
            for number, extra in enumerate(mutations):
                with self.subTest(model=model, mutation=extra):
                    status, destination = self.attempt(f"{model}-negative-{number}", model, extra)
                    require_success(status)
                    self.assertEqual(json.loads((destination / "validation.json").read_bytes())["result"],
                                     "REJECTED")
            status, destination = self.attempt(f"{model}-override-link", model,
                                               addition="override LINK := unqualified\n")
            require_success(status)
            self.assertEqual(json.loads((destination / "validation.json").read_bytes())["result"],
                             "REJECTED")

    def test_missing_duplicate_truncated_and_incomplete_receipts(self) -> None:
        for model in MODELS:
            status, destination = self.attempt(f"{model}-shape", model)
            require_success(status)
            fields = destination / "fields"
            original = (fields / "LINK").read_bytes()
            (fields / "LINK").unlink()
            with self.assertRaises(ValueError):
                read_probe(fields, model)
            (fields / "LINK").write_bytes(original[:-1])
            with self.assertRaises(ValueError):
                read_probe(fields, model)
            (fields / "LINK").write_bytes(original)
            (fields / "duplicate-LINK").write_bytes(original)
            with self.assertRaises(ValueError):
                read_probe(fields, model)
            (fields / "duplicate-LINK").unlink()
            self.assertEqual(read_probe(fields, model)["LINK"], DRIVERS["LINK"])
            status, destination = self.attempt(f"{model}-missing-generated", model,
                                               ["NEXTPC_PROBE_MAKEFILE=Vmissing.mk"])
            self.assertEqual((status["kind"], status["code"]), ("exited", 2))
            with self.assertRaises(ValueError):
                read_probe(destination / "fields", model)

    def test_timeout_kills_recursive_fixture_without_success_receipt(self) -> None:
        for model in MODELS:
            status, destination = self.attempt(
                f"{model}-timeout", model, timeout=1,
                addition="fixture-capture: fixture-delay\n.PHONY: fixture-delay\nfixture-delay:\n\t@sleep 30\n",
            )
            self.assertEqual((status["kind"], status["code"]), ("timed_out", 124))
            with self.assertRaises(RuntimeError):
                require_success(status)
            with self.assertRaises(ValueError):
                read_probe(destination / "fields", model)


def main() -> int:
    global OUTPUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.output.resolve()
    OUTPUT.mkdir(exist_ok=False)
    if os.name != "posix" or shutil.which("make") is None:
        raise RuntimeError("CODE_ONLY actual GNU make contracts require preinstalled POSIX make; no install")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    seal = verify()
    status = run(["make", "--version"], ROOT, OUTPUT, "make-version", 5)
    require_success(status)
    if not (OUTPUT / "make-version.stdout.log").read_bytes().startswith(b"GNU Make "):
        raise RuntimeError("preinstalled make is not GNU make")
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MakeContracts))
    summary = {
        "schema": 1, "scope": "CODE_ONLY", "source_sha": source,
        "run_id": os.environ.get("GITHUB_RUN_ID"), "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "result": "PIPELINE_CONTRACTS_PASS" if result.wasSuccessful() else "PIPELINE_CONTRACTS_FAIL",
        "tests_run": result.testsRun, "attempted_synthetic_make_cases": len(CASES), "cases": CASES,
        "make_binary": identity(Path(shutil.which("make")).resolve()),
        "source_manifest": identity(ROOT / "rvfi_nextpc" / "SOURCE_MANIFEST.json"),
        "sealed_input_count": len(seal["files"]),
        "authorization": identity(ROOT / "rvfi_nextpc" / "CODE_ONLY_AUTHORIZATION.json"),
        "hdl_cpu_program_compilations_and_runs": 0,
        "observation_dispatches": 0, "scientific_result": "NOT_RUN",
        "limitations": "Disposable synthetic make variables only; no archived actual model/program probe, HDL setup/export/build or CPU execution. Historical accepted PRE-RUN STOP remains NOT_QUALIFIED.",
    }
    write_json(OUTPUT / "summary.json", summary)
    for path in OUTPUT.rglob("*"):
        if path.is_file():
            privacy_review(path.read_bytes())
    write_json(OUTPUT / "CODE_ONLY_MANIFEST.json", {
        "schema": 1, "scope": "CODE_ONLY", "source_sha": source,
        "files": {path.relative_to(OUTPUT).as_posix(): identity(path)
                  for path in sorted(OUTPUT.rglob("*")) if path.is_file()},
    })
    print(json.dumps({key: value for key, value in summary.items() if key != "cases"}, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
