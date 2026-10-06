# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Fail-closed stream qualification, ISA path and strict metadata comparison."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .isa import FIELDS, FIRST_ORDER, MAX_CYCLES, decode, execute, word


def parse(path: Path) -> tuple[list[dict[str, int]], int]:
    records: list[dict[str, int]] = []
    reset, started, cycle = False, False, 0
    text = path.read_text(encoding="ascii")
    if not text.endswith("\n"):
        raise ValueError("truncated unflushed stream")
    retirement_cycle = -1
    for line in text.splitlines():
        parts = line.split("\t")
        if not parts or parts[0] not in ("Q", "R"):
            raise ValueError("malformed stream tag")
        try:
            values = [int(item, 10) for item in parts[1:]]
        except ValueError as error:
            raise ValueError("malformed decimal stream") from error
        if any(value < 0 for value in values):
            raise ValueError("negative stream field")
        if parts[0] == "Q":
            if len(values) != 9 or values[0] != cycle or values[1] not in (0, 1):
                raise ValueError("malformed/missing/reordered control sample")
            cycle += 1
            if cycle > MAX_CYCLES or any(values[2:]):
                raise ValueError("cycle budget or interrupt/debug control violation")
            if not values[1]:
                if started:
                    raise ValueError("reset after measurement started")
                reset = True
            elif reset:
                started = True
        else:
            if not started or len(values) != len(FIELDS) + 1 or values[0] != cycle - 1:
                raise ValueError("unarmed/malformed retirement")
            record = dict(zip(FIELDS, values[1:]))
            if values[0] == retirement_cycle:
                raise ValueError("multiple retirements in one sampled cycle")
            retirement_cycle = values[0]
            if record["order"] != FIRST_ORDER + len(records):
                raise ValueError("duplicate/missing/reordered dynamic order")
            if any(record[key] for key in (
                "trap", "halt", "intr", "rmask", "wmask", "pre_mip", "post_mip",
                "nmi", "nmi_int", "debug_req", "debug_mode", "irq_valid", "rf_suppress",
            )):
                raise ValueError("unexpected trap/halt/interrupt/debug/memory")
            if record["mode"] != 3 or record["ixl"] != 1:
                raise ValueError("unexpected ISA/privilege mode")
            for key in ("pc", "insn", "next_pc", "a", "b", "value"):
                if record[key] > 0xFFFFFFFF:
                    raise ValueError("non-RV32 stream value")
            if any(record[key] > 31 for key in ("rs1", "rs2", "rd")):
                raise ValueError("malformed register index")
            records.append(record)
    if not reset or not started or not records:
        raise ValueError("missing reset/start/retirement")
    return records, cycle


def qualify(cpp: Path, sv: Path, image: bytes, contract: dict[str, object]) -> dict[str, object]:
    first, cpp_cycles = parse(cpp)
    second, sv_cycles = parse(sv)
    # Phases are different; join by dynamic order/PC/instruction, never cycles or static PC.
    if [(r["order"], r["pc"], r["insn"]) for r in first] != [
        (r["order"], r["pc"], r["insn"]) for r in second
    ] or first != second:
        raise ValueError("independent sampler inconsistency")
    path = contract["path"]
    if len(first) != len(path):
        raise ValueError("premature exit or extra retirement (no filtering permitted)")
    regs, cells, mismatches = [0] * 32, Counter(), []
    for index, (record, frozen) in enumerate(zip(first, path)):
        if any(record[key] != frozen[key] for key in ("order", "pc", "insn")):
            raise ValueError("execution differs from pre-run frozen ISA path")
        if record["insn"] != word(image, record["pc"]):
            raise ValueError("image/retired instruction mismatch")
        expected, cell = execute(record["pc"], record["insn"], regs)
        if expected != {key: frozen[key] for key in expected}:
            raise ValueError("frozen oracle identity mismatch")
        op = decode(record["insn"])["op"]
        if op in ("addi", "beq", "bne") and (
            record["rs1"] != expected["rs1"] or record["a"] != expected["a"]
        ):
            raise ValueError("retired rs1 differs from independent ISA state")
        if op in ("beq", "bne") and (
            record["rs2"] != expected["rs2"] or record["b"] != expected["b"]
        ):
            raise ValueError("retired branch rs2 differs from independent ISA state")
        if record["rd"] != expected["rd"] or record["value"] != expected["value"]:
            raise ValueError("retired writeback differs from ISA")
        if index + 1 < len(first) and first[index + 1]["pc"] != expected["next_pc"]:
            raise ValueError("following retirement differs from decoded ISA successor")
        if cell:
            cells[cell] += 1
        if record["next_pc"] != expected["next_pc"]:
            mismatches.append({"order": record["order"], "pc": record["pc"], "insn": record["insn"],
                               "observed": record["next_pc"], "required": expected["next_pc"],
                               "region": frozen["region"], "cell": cell})
    if dict(cells) != contract["coverage"]:
        raise ValueError("observed branch coverage differs from frozen contract")
    return {"samplers": "PASS", "isa_execution": "PASS",
            "strict_next_pc": "FAIL" if mismatches else "PASS", "mismatches": mismatches,
            "retirements": len(first), "branches": sum(cells.values()),
            "coverage": dict(sorted(cells.items())), "cpp_cycles": cpp_cycles, "sv_cycles": sv_cycles}
