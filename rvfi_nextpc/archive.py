# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Offline-only byte manifest and scientific-result requalification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from .check import qualify
from .isa import freeze
from .process import identity
from .seal import ROOT


def privacy_review(data: bytes) -> None:
    pattern = (
        rb"(?i)(C:\\Users\\[A-Za-z0-9_.-]+\\|/Users/[A-Za-z0-9_.-]+/|"
        rb"/home/(?!runner/)[A-Za-z0-9_.-]+/|gh[pousr]_[A-Za-z0-9]{20,}|"
        rb"github_pat_[A-Za-z0-9_]{20,}|"
        rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)"
    )
    if re.search(pattern, data):
        raise ValueError("credential/private-path candidate")


def verify_code_only(directory: Path) -> dict[str, object]:
    privacy_review((directory / "CODE_ONLY_MANIFEST.json").read_bytes())
    manifest = json.loads((directory / "CODE_ONLY_MANIFEST.json").read_bytes())
    actual = {path.relative_to(directory).as_posix(): identity(path)
              for path in sorted(directory.rglob("*"))
              if path.is_file() and path.name != "CODE_ONLY_MANIFEST.json"}
    if manifest["schema"] != 1 or manifest["scope"] != "CODE_ONLY" or actual != manifest["files"]:
        raise ValueError("changed/missing/extra code-only artifact bytes")
    summary = json.loads((directory / "summary.json").read_bytes())
    if summary["scope"] != "CODE_ONLY" or summary["source_sha"] != manifest["source_sha"] or (
        summary["result"] not in ("PIPELINE_CONTRACTS_PASS", "PIPELINE_CONTRACTS_FAIL")
        or summary["scientific_result"] != "NOT_RUN" or summary["observation_dispatches"] != 0
        or summary["hdl_cpu_program_compilations_and_runs"] != 0
        or summary["attempted_synthetic_make_cases"] != len(summary["cases"])
    ):
        raise ValueError("code-only artifact misrepresented as measurement")
    for name in actual:
        path = directory / name
        privacy_review(path.read_bytes())
        if path.suffix in (".o", ".a", ".fst", ".vcd", ".exe", ".bin", ".elf"):
            raise ValueError("binary/wave outside code-only archive policy")
        if name.endswith(".status.json"):
            status = json.loads(path.read_bytes())
            if status["kind"] not in ("exited", "signaled", "timed_out", "spawn_error") or (
                status["argv"][0] != "make"
            ):
                raise ValueError("untyped or non-make code-only command")
            prefix = name.removesuffix(".status.json")
            for stream in ("stdout", "stderr"):
                if status[stream] != identity(directory / f"{prefix}.{stream}.log"):
                    raise ValueError("code-only original command bytes changed")
    return {"scope": "CODE_ONLY", "archive_integrity": "PASS", "source_sha": manifest["source_sha"],
            "result": summary["result"], "scientific_result": "NOT_RUN", "members": len(actual)}


def verify_archive(directory: Path, collection: dict[str, object] | None = None) -> dict[str, object]:
    manifest = json.loads((directory / "RAW_MANIFEST.json").read_text(encoding="ascii"))
    actual = {path.relative_to(directory).as_posix(): identity(path)
              for path in sorted(directory.rglob("*"))
              if path.is_file() and path.name != "RAW_MANIFEST.json"}
    expected = manifest["files"]
    missing = sorted(expected.keys() - actual.keys())
    if manifest["schema"] != 1 or any(actual[name] != expected.get(name) for name in actual):
        raise ValueError("missing, changed or unmanifested archive bytes")
    if collection is not None and collection["missing_files"] != missing:
        raise ValueError("collection gap differs from unchanged artifact")
    if missing and (collection is None or missing != ["input/.github/workflows/rvfi-nextpc.yml"]):
        raise ValueError("missing archive bytes")
    summary = json.loads((directory / "summary.json").read_text())
    dispatch = json.loads((directory / "dispatch-input.json").read_text())
    if missing:
        if (
            collection is None or collection["missing_files"] != missing
            or collection["manifest"] != identity(directory / "RAW_MANIFEST.json")
            or collection["source_sha"] != manifest["source_sha"]
            or str(collection["run_id"]) != str(manifest["run_id"])
            or summary["result"] != "STOP" or summary.get("real_compilations") != []
            or missing != ["input/.github/workflows/rvfi-nextpc.yml"]
        ):
            raise ValueError("missing archive bytes; no matching explicit pre-HDL STOP collection receipt")
    if summary["source_sha"] != manifest["source_sha"] or dispatch["source_sha"] != manifest["source_sha"]:
        raise ValueError("archive source binding mismatch")
    for name in actual:
        path = directory / name
        if path.suffix in (".o", ".a", ".fst", ".vcd", ".exe") or (
            path.suffix in (".bin", ".elf") and name not in ("fresh.bin", "fresh.elf")
        ):
            raise ValueError("model binary/build tree/wave outside public archive policy")
        data = path.read_bytes()
        try:
            privacy_review(data)
        except ValueError as error:
            raise ValueError(f"STOP privacy review: credential/private-path candidate in {name}") from error
        if name.endswith(".status.json"):
            status = json.loads(data)
            if status["kind"] not in ("exited", "signaled", "timed_out", "spawn_error"):
                raise ValueError("untyped attempted command")
            prefix = name.removesuffix(".status.json")
            for stream in ("stdout", "stderr"):
                if status[stream] != identity(directory / f"{prefix}.{stream}.log"):
                    raise ValueError("terminal console byte identity mismatch")
    if summary["result"] == "PAIR_OBSERVED":
        contract = json.loads((directory / "program-contract.json").read_text())
        image = (directory / "fresh.bin").read_bytes()
        if freeze(image, contract["drain"], contract["terminal"]) != contract:
            raise ValueError("pre-run ISA contract/image mismatch")
        frozen = json.loads((directory / "freeze.json").read_text())
        if frozen["source_sha"] != summary["source_sha"] or frozen["program_bytes"] != identity(directory / "fresh.bin"):
            raise ValueError("freeze/archive binding mismatch")
        for name, expected in frozen["prior_receipts"].items():
            if identity(directory / name) != expected:
                raise ValueError("pre-run frozen receipt changed")
        for label in ("off", "on"):
            result = qualify(directory / label / "cpp.tsv", directory / label / "sv.tsv", image, contract)
            recorded = json.loads((directory / label / "qualification.json").read_text())
            if any(recorded[key] != value for key, value in result.items()):
                raise ValueError("recorded raw qualification does not recompute")
            if any(summary[label][key] != value for key, value in result.items()):
                raise ValueError("summary/raw scientific mismatch")
        if summary["off"]["strict_next_pc"] != "PASS" or summary["scientific_result"] != summary["on"]["strict_next_pc"]:
            raise ValueError("scientific result incorrectly promoted")
        if summary["real_compilations"] != ["off", "on"]:
            raise ValueError("pair build journal mismatch")
    elif summary["result"] == "PREPARATION_PASS":
        if summary["real_compilations"] or summary["scientific_result"] != "NOT_RUN":
            raise ValueError("preparation masquerades as real evidence")
        miniature = json.loads((directory / "miniature-qualification.json").read_text())
        if miniature["good"]["samplers"] != "PASS":
            raise ValueError("preparation missing independent miniature qualification")
        if summary["authorization"] in (
            "WLHsu0827-2026-10-03-rvfi-nextpc-recovery-1",
            "WLHsu0827-2026-10-03-rvfi-nextpc-stable-tools-1",
            "WLHsu0827-2026-10-03-rvfi-nextpc-memory-admission-1",
        ):
            loader = json.loads((directory / "loader-qualification.json").read_text())
            if set(loader) != {"good", "empty", "truncated", "oversized", "wrong_terminal",
                               "wrong_boundary", "negative", "overflow", "trailing_text",
                               "zero_budget", "over_budget"} or any(
                item["contract"] != "PASS" for item in loader.values()
            ):
                raise ValueError("preparation missing actual shared loader qualification")
            for group in ("runtime", "build"):
                tools = json.loads((directory / f"{group}-installed-tools.json").read_text())
                if not tools["closure"].startswith("PASS"):
                    raise ValueError("preparation missing strict installed dependency closure")
        if summary["authorization"] in (
            "WLHsu0827-2026-10-03-rvfi-nextpc-stable-tools-1",
            "WLHsu0827-2026-10-03-rvfi-nextpc-memory-admission-1",
        ):
            from .entrypoint import compare

            compare(directory, directory)
            for label in ("off", "on"):
                if json.loads((directory / label / "build-command-contract.json").read_text())["result"] != "PASS":
                    raise ValueError("preparation missing actual generated build command check")
        if summary["authorization"] == "WLHsu0827-2026-10-03-rvfi-nextpc-memory-admission-1":
            from .drivers import read_probe, validate_probe, validate_recipes
            from .tests import tiny_contract

            scope = json.loads((directory / "driver-scope.json").read_text())
            recursive = json.loads((directory / "recursive-drivers.json").read_text())
            if recursive["result"] != "PASS" or recursive["installed_make"] != identity(
                directory / "installed-verilated.mk"
            ):
                raise ValueError("missing qualified actual LINK/driver identities")
            if recursive.get("schema") == 2:
                if read_probe(directory / "miniature-driver-probe", "Vsampler_fixture.mk") != recursive["expanded"]:
                    raise ValueError("original framed driver receipt changed")
                if recursive["probe_script"] != identity(directory / "input/rvfi_nextpc/driver_probe.mk"):
                    raise ValueError("shared probe source identity changed")
            else:
                validate_probe("\n".join(key + "=" + value for key, value in recursive["expanded"].items()))
            validate_recipes((directory / "miniature-generated.mk").read_text(),
                             (directory / "installed-verilated.mk").read_text())
            if not scope["files"] or scope["make"] != recursive["invocation"]:
                raise ValueError("missing installed helper/include scope")
            required = {"good", "extra_read", "no_reset", "reset_again", "pre_request", "post_request",
                        "grant", "response", "data_error", "write_control", "minor_alert", "internal_alert",
                        "bus_alert", "irq", "debug_req", "debug_mode", "memory_opcode", "write_mask",
                        "trap", "halt", "intr", "privilege", "rf_suppress", "hang"}
            if set(miniature) != required:
                raise ValueError("missing actual independent bus/admission miniature cases")
            image, contract = tiny_contract()
            for scenario in ("good", "extra_read"):
                result = qualify(directory / f"miniature-{scenario}/cpp.tsv",
                                 directory / f"miniature-{scenario}/sv.tsv", image, contract)
                if miniature[scenario] != result:
                    raise ValueError("miniature v2 raw/qualification mismatch")
            if any(miniature[scenario]["expected_negative"] != "PASS" for scenario in required - {
                "good", "extra_read"
            }):
                raise ValueError("actual admission negative not qualified")
    elif summary["result"] != "STOP" or not summary.get("error"):
        raise ValueError("unrecognized/incomplete terminal closure")
    return {"archive_integrity": "INCOMPLETE" if missing else "PASS", "missing_files": missing,
            "result": summary["result"],
            "scientific_result": summary.get("scientific_result", "NOT_QUALIFIED"),
            "source_sha": summary["source_sha"], "run_id": manifest["run_id"],
            "manifest": identity(directory / "RAW_MANIFEST.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path)
    args = parser.parse_args()
    directories = [args.directory] if args.directory else sorted((ROOT / "rvfi_nextpc" / "evidence").glob("run-*"))
    collection_path = ROOT / "rvfi_nextpc" / "evidence" / "COLLECTION.json"
    collections = json.loads(collection_path.read_text())["archives"] if collection_path.exists() else {}
    for directory in directories:
        print(json.dumps(verify_archive(directory, collections.get(directory.name)), sort_keys=True))
    if args.directory is None:
        for directory in sorted((ROOT / "rvfi_nextpc" / "evidence").glob("code-only-*")):
            print(json.dumps(verify_code_only(directory), sort_keys=True))
    if not directories:
        print("NEXTPC_NO_ARCHIVE_YET: input-only, no claimed DUT result")
