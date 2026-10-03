# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Independent small RV32I/Zca decoder/interpreter; no trace-derived oracle."""

from __future__ import annotations

from collections import Counter

BOOT = 0x80000080
TERMINAL_RETIREMENTS = 4
MAX_CYCLES = 20000
FIRST_ORDER = 1
FIELDS = (
    "order", "pc", "insn", "next_pc", "rs1", "rs2", "a", "b", "rd", "value",
    "trap", "halt", "intr", "mode", "ixl", "rmask", "wmask", "pre_mip", "post_mip",
    "nmi", "nmi_int", "debug_req", "debug_mode", "irq_valid", "rf_suppress",
)


def sext(value: int, bits: int) -> int:
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def decode(insn: int) -> dict[str, int | str]:
    if insn & 3 != 3:
        if insn >> 16 or insn & 3 != 1 or insn >> 13 not in (6, 7):
            raise ValueError(f"unsupported compressed encoding {insn:08x}")
        offset = (
            ((insn >> 12) & 1) << 8 | ((insn >> 10) & 3) << 3
            | ((insn >> 5) & 3) << 6 | ((insn >> 3) & 3) << 1
            | ((insn >> 2) & 1) << 5
        )
        return {
            "op": "beq" if insn >> 13 == 6 else "bne", "width": 2,
            "rs1": 8 + ((insn >> 7) & 7), "rs2": 0, "rd": 0,
            "imm": sext(offset, 9),
        }
    opcode = insn & 127
    rd, rs1, rs2 = (insn >> 7) & 31, (insn >> 15) & 31, (insn >> 20) & 31
    if opcode == 0x13 and (insn >> 12) & 7 == 0:
        return {"op": "addi", "width": 4, "rs1": rs1, "rs2": 0, "rd": rd,
                "imm": sext(insn >> 20, 12)}
    if opcode == 0x63 and (insn >> 12) & 7 in (0, 1):
        offset = (
            (insn >> 31) << 12 | ((insn >> 7) & 1) << 11
            | ((insn >> 25) & 63) << 5 | ((insn >> 8) & 15) << 1
        )
        return {"op": "beq" if (insn >> 12) & 7 == 0 else "bne", "width": 4,
                "rs1": rs1, "rs2": rs2, "rd": 0, "imm": sext(offset, 13)}
    if opcode == 0x6F:
        offset = (
            (insn >> 31) << 20 | ((insn >> 12) & 255) << 12
            | ((insn >> 20) & 1) << 11 | ((insn >> 21) & 1023) << 1
        )
        return {"op": "jal", "width": 4, "rs1": 0, "rs2": 0, "rd": rd,
                "imm": sext(offset, 21)}
    raise ValueError(f"unsupported base encoding {insn:08x}")


def word(image: bytes, pc: int) -> int:
    offset = pc - BOOT
    if offset < 0 or offset + 2 > len(image) or offset % 2:
        raise ValueError(f"PC outside fresh image {pc:08x}")
    half = int.from_bytes(image[offset:offset + 2], "little")
    width = 4 if half & 3 == 3 else 2
    if offset + width > len(image):
        raise ValueError("truncated instruction")
    return int.from_bytes(image[offset:offset + width], "little")


def execute(pc: int, insn: int, regs: list[int]) -> tuple[dict[str, int], str | None]:
    decoded = decode(insn)
    op = decoded["op"]
    width, rs1, rs2, rd, imm = (int(decoded[key]) for key in ("width", "rs1", "rs2", "rd", "imm"))
    a, b = regs[rs1], regs[rs2]
    successor, value, cell = pc + width, 0, None
    if op in ("beq", "bne"):
        taken = (a == b) if op == "beq" else (a != b)
        successor = pc + imm if taken else successor
        if imm == 0:
            raise ValueError("zero-offset branch outside preregistered scenario")
        cell = f"{width * 8}:{'backward' if imm < 0 else 'forward'}:{int(taken)}"
    elif op == "addi":
        value = (a + imm) & 0xFFFFFFFF
    elif op == "jal":
        value, successor = successor & 0xFFFFFFFF, pc + imm
    if rd:
        regs[rd] = value
    else:
        value = 0
    return {"pc": pc, "insn": insn, "next_pc": successor & 0xFFFFFFFF,
            "rs1": rs1, "rs2": rs2, "a": a, "b": b, "rd": rd, "value": value}, cell


def freeze(image: bytes, drain: int, terminal: int) -> dict[str, object]:
    if not BOOT < drain < terminal or word(image, terminal) != 0x0000006F:
        raise ValueError("invalid boot/drain/terminal boundary")
    if terminal + 4 != BOOT + len(image):
        raise ValueError("unexpected bytes beyond explicit terminal")
    if image[drain - BOOT:terminal - BOOT] != bytes.fromhex("13000000") * 3:
        raise ValueError("drain must be exactly three retained RV32 NOPs")
    regs, path, cells = [0] * 32, [], Counter()
    pc, terminals = BOOT, 0
    for order in range(512):
        insn = word(image, pc)
        expected, cell = execute(pc, insn, regs)
        expected["order"] = order + FIRST_ORDER
        expected["region"] = "terminal" if pc == terminal else "drain" if pc >= drain else "program"
        path.append(expected)
        if cell:
            cells[cell] += 1
        if pc == terminal:
            terminals += 1
        if terminals == TERMINAL_RETIREMENTS:
            break
        pc = expected["next_pc"]
    else:
        raise ValueError("oracle exceeded directed program bound")
    required = {f"{width}:{direction}:{outcome}"
                for width in (16, 32) for direction in ("backward", "forward") for outcome in (0, 1)}
    if set(cells) != required:
        raise ValueError(f"incomplete preregistered branch cells: {cells}")
    return {"schema": 1, "boot": BOOT, "drain": drain, "terminal": terminal,
            "terminal_retirements": TERMINAL_RETIREMENTS, "path": path,
            "coverage": dict(sorted(cells.items())), "retirements": len(path),
            "branches": sum(cells.values()), "max_cycles": MAX_CYCLES}
