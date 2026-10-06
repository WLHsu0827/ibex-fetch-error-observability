# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Code-only remaining-path contracts, never an execution authorization."""

from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from .entrypoint import read_receipt
from .isa import MAX_CYCLES, TERMINAL_RETIREMENTS
from .process import identity, require_success
from .seal import ROOT


def require_measurement_authorization() -> None:
    scope = read_receipt(ROOT / "rvfi_nextpc" / "CODE_ONLY_AUTHORIZATION.json")
    if scope["measurement_authorized"] is not True or scope["all_measurement_epochs_closed"] is True:
        raise RuntimeError("STOP: CODE_ONLY readiness authorizes no measurement; all epochs CLOSED")


def verify_freeze(output: Path, source_sha: str) -> None:
    frozen = read_receipt(output / "freeze.json")
    if frozen["schema"] != 2 or frozen["source_sha"] != source_sha:
        raise ValueError("frozen source/schema identity changed")
    for name, expected in frozen["prior_receipts"].items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or not path.parts:
            raise ValueError("invalid frozen receipt path")
        if identity(output / name) != expected:
            raise ValueError("frozen prior receipt changed: " + name)
    for name, key in (("fresh.elf", "program_elf"), ("fresh.bin", "program_bytes"),
                      ("program-contract.json", "contract"), ("input-equivalence.json", "equivalence")):
        if frozen["prior_receipts"].get(name) != frozen[key]:
            raise ValueError("missing/inconsistent frozen program or configuration")


def model_binary(build: Path, model: str) -> Path:
    candidates = [build / model, build / "obj_dir" / model]
    present = [path for path in candidates if path.exists()]
    if len(present) != 1 or not present[0].is_file() or not os.access(present[0], os.X_OK):
        raise ValueError("missing/ambiguous/non-executable actual model")
    return present[0]


def termination(text: str, bp: int, status: dict[str, object]) -> int:
    require_success(status)
    lines = text.splitlines()
    configs = [line for line in lines if line.startswith("NEXTPC_CONFIG")]
    ends = [line for line in lines if line.startswith("NEXTPC_COMPLETE")]
    if configs != [f"NEXTPC_CONFIG BP={bp} WB=0 BTA=0 ZC=0 IC=0"] or len(ends) != 1:
        raise ValueError("missing/duplicate model configuration or termination marker")
    match = re.fullmatch(r"NEXTPC_COMPLETE terminal_records=(\d+) cycles=(\d+)", ends[0])
    if match is None or int(match[1]) != TERMINAL_RETIREMENTS or not 1 <= int(match[2]) <= MAX_CYCLES:
        raise ValueError("invalid terminal boundary/cycle receipt")
    if lines.index(configs[0]) >= lines.index(ends[0]) or any(
        line.startswith("NEXTPC_STOP") for line in lines
    ):
        raise ValueError("failure or reversed model terminal markers")
    return int(match[2])


def require_qualified_off(result: dict[str, object]) -> None:
    if any(result.get(key) != "PASS" for key in (
        "samplers", "observed_no_data_transactions", "isa_execution", "strict_next_pc",
    )) or result.get("process") != {"kind": "exited", "code": 0}:
        raise RuntimeError("STOP: OFF controls/samplers/ISA/strict metadata not qualified; ON not authorized")


def source_changed() -> bool:
    current = subprocess.check_output(["git", "show", "HEAD:rvfi_nextpc/SOURCE_MANIFEST.json"], cwd=ROOT)
    previous = subprocess.check_output(["git", "show", "HEAD^:rvfi_nextpc/SOURCE_MANIFEST.json"], cwd=ROOT)
    return current != previous


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-changed", action="store_true", required=True)
    parser.parse_args()
    print("changed=" + str(source_changed()).lower())
