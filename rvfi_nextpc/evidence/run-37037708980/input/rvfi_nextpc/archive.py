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


def verify_archive(directory: Path) -> dict[str, object]:
    manifest = json.loads((directory / "RAW_MANIFEST.json").read_text(encoding="ascii"))
    actual = {path.relative_to(directory).as_posix(): identity(path)
              for path in sorted(directory.rglob("*"))
              if path.is_file() and path.name != "RAW_MANIFEST.json"}
    if manifest["schema"] != 1 or actual != manifest["files"]:
        raise ValueError("missing, changed or unmanifested archive bytes")
    summary = json.loads((directory / "summary.json").read_text())
    dispatch = json.loads((directory / "dispatch-input.json").read_text())
    if summary["source_sha"] != manifest["source_sha"] or dispatch["source_sha"] != manifest["source_sha"]:
        raise ValueError("archive source binding mismatch")
    for name in actual:
        path = directory / name
        if path.suffix in (".o", ".a", ".fst", ".vcd", ".exe") or (
            path.suffix in (".bin", ".elf") and name not in ("fresh.bin", "fresh.elf")
        ):
            raise ValueError("model binary/build tree/wave outside public archive policy")
        data = path.read_bytes()
        if re.search(rb"(?i)(C:\\Users\\|/Users/|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|"
                     rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)", data):
            raise ValueError(f"STOP privacy review: disallowed path/credential pattern in {name}")
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
    elif summary["result"] != "STOP" or not summary.get("error"):
        raise ValueError("unrecognized/incomplete terminal closure")
    return {"archive_integrity": "PASS", "result": summary["result"],
            "scientific_result": summary.get("scientific_result", "NOT_QUALIFIED"),
            "source_sha": summary["source_sha"], "run_id": manifest["run_id"],
            "manifest": identity(directory / "RAW_MANIFEST.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", type=Path)
    args = parser.parse_args()
    directories = [args.directory] if args.directory else sorted((ROOT / "rvfi_nextpc" / "evidence").glob("run-*"))
    for directory in directories:
        print(json.dumps(verify_archive(directory), sort_keys=True))
    if not directories:
        print("NEXTPC_NO_ARCHIVE_YET: input-only, no claimed DUT result")
