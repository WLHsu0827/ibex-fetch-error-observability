"""Strict parser and checker for the synthetic monitor trace."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re


WIDTHS = {"Q": 10, "B": 9, "PRE": 11, "POST": 9, "R": 13}
FIELDS = {
    "Q": (
        ("cycle", 10, None),
        ("control_software", 10, 1),
        ("control_timer", 10, 1),
        ("control_external", 10, 1),
        ("control_fast", 16, 0x7FFF),
        ("control_nm", 10, 1),
        ("debug_request", 10, 1),
        ("debug_mode", 10, 1),
        ("new_control", 10, 1),
    ),
    "B": (
        ("cycle", 10, None), ("label", 16, 0xFFFFFFFF),
        ("word", 16, 0xFFFFFFFF), ("decision", 10, 1),
        ("predicted_taken", 10, 1), ("correction", 10, 1),
        ("correction_label", 16, 0xFFFFFFFF), ("redirect", 10, 1),
    ),
    "PRE": (
        ("cycle", 10, None), ("label", 16, 0xFFFFFFFF),
        ("word", 16, 0xFFFFFFFF), ("redirect", 10, 1),
        ("next_label", 16, 0xFFFFFFFF), ("target_label", 16, 0xFFFFFFFF),
        ("correction", 10, 1), ("correction_label", 16, 0xFFFFFFFF),
        ("decision", 10, 1), ("predicted_taken", 10, 1),
    ),
    "POST": (
        ("cycle", 10, None), ("order", 10, None),
        ("label", 16, 0xFFFFFFFF), ("word", 16, 0xFFFFFFFF),
        ("next_label", 16, 0xFFFFFFFF), ("valid", 10, 1),
        ("trap", 10, 1), ("interrupt", 10, 1),
    ),
    "R": (
        ("cycle", 10, None), ("order", 10, None),
        ("label", 16, 0xFFFFFFFF), ("word", 16, 0xFFFFFFFF),
        ("next_label", 16, 0xFFFFFFFF), ("trap", 10, 1),
        ("interrupt", 10, 1), ("halt", 10, 1),
        ("operand_a_index", 10, 31), ("operand_a_value", 16, 0xFFFFFFFF),
        ("operand_b_index", 10, 31), ("operand_b_value", 16, 0xFFFFFFFF),
    ),
}
EXPECTED_SEQUENCE = ("Q", "B", "PRE", "POST", "Q", "R")
DECIMAL = re.compile(r"[0-9]+")
HEX = {
    4: re.compile(r"[0-9a-fA-F]{4}"),
    8: re.compile(r"[0-9a-fA-F]{8}"),
}


class TraceError(ValueError):
    pass


class TraceRows(dict[str, list[list[int]]]):
    def __init__(self, rows: dict[str, list[list[int]]], sequence: list[str]):
        super().__init__(rows)
        self.sequence = tuple(sequence)


def _parse_field(
    raw: str, *, kind: str, line_number: int, name: str, base: int, maximum: int | None
) -> int:
    hex_width = 4 if name == "control_fast" else 8
    pattern = DECIMAL if base == 10 else HEX[hex_width]
    if pattern.fullmatch(raw) is None:
        syntax = (
            "unsigned decimal" if base == 10 else f"exactly {hex_width} hex digits"
        )
        raise TraceError(f"line {line_number} {kind}.{name}: expected {syntax}")
    value = int(raw, base)
    if maximum is not None and value > maximum:
        raise TraceError(
            f"line {line_number} {kind}.{name}: {value} exceeds {maximum}"
        )
    return value


def parse_trace(path: Path) -> TraceRows:
    rows: dict[str, list[list[int]]] = defaultdict(list)
    sequence: list[str] = []
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        columns = raw.split("\t")
        kind = columns[0]
        if kind not in WIDTHS:
            raise TraceError(f"line {line_number}: unknown row {kind!r}")
        if len(columns) != WIDTHS[kind]:
            raise TraceError(
                f"line {line_number} {kind}: expected {WIDTHS[kind]} columns, "
                f"got {len(columns)}"
            )
        values = [
            _parse_field(
                value,
                kind=kind,
                line_number=line_number,
                name=name,
                base=base,
                maximum=maximum,
            )
            for value, (name, base, maximum) in zip(
                columns[1:], FIELDS[kind], strict=True
            )
        ]
        rows[kind].append(values)
        sequence.append(kind)
    return TraceRows({kind: rows.get(kind, []) for kind in WIDTHS}, sequence)


def require_positive_trace(rows: dict[str, list[list[int]]]) -> None:
    sequence = getattr(rows, "sequence", None)
    if sequence is not None and sequence != EXPECTED_SEQUENCE:
        raise TraceError(
            f"row sequence must be {list(EXPECTED_SEQUENCE)}, got {list(sequence)}"
        )
    if [row[0] for row in rows["Q"]] != [0, 1]:
        raise TraceError("Q cycles must be consecutive and exactly [0, 1]")
    expected_counts = {"B": 1, "PRE": 1, "POST": 1, "R": 1}
    actual_counts = {kind: len(rows[kind]) for kind in expected_counts}
    if actual_counts != expected_counts:
        raise TraceError(f"event counts differ: {actual_counts}")
    if any(row[1:] != [0] * 8 for row in rows["Q"]):
        raise TraceError("control fields are not the controlled zero values")
    branch, pre, post, retire = (
        rows["B"][0],
        rows["PRE"][0],
        rows["POST"][0],
        rows["R"][0],
    )
    expected_rows = {
        "B": [0, 0x100, 0x13, 1, 0, 0, 0, 0],
        "PRE": [0, 0x100, 0x13, 0, 0x104, 0x104, 0, 0, 1, 0],
        "POST": [0, 1, 0x100, 0x13, 0x104, 1, 0, 0],
        "R": [1, 1, 0x100, 0x13, 0x104, 0, 0, 0, 0, 0, 0, 0],
    }
    for kind, actual in {
        "B": branch, "PRE": pre, "POST": post, "R": retire
    }.items():
        if actual != expected_rows[kind]:
            raise TraceError(
                f"{kind} row differs: expected {expected_rows[kind]}, got {actual}"
            )
