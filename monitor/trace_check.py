"""Strict parser and checker for the synthetic monitor trace."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


WIDTHS = {"Q": 10, "B": 9, "PRE": 11, "POST": 9, "R": 13}
BASES = {
    "Q": (10, 10, 10, 10, 16, 10, 10, 10, 10),
    "B": (10, 16, 16, 10, 10, 10, 16, 10),
    "PRE": (10, 16, 16, 10, 16, 16, 10, 16, 10, 10),
    "POST": (10, 10, 16, 16, 16, 10, 10, 10),
    "R": (10, 10, 16, 16, 16, 10, 10, 10, 10, 16, 10, 16),
}


class TraceError(ValueError):
    pass


def parse_trace(path: Path) -> dict[str, list[list[int]]]:
    rows: dict[str, list[list[int]]] = defaultdict(list)
    for line_number, raw in enumerate(path.read_text().splitlines(), 1):
        columns = raw.split("\t")
        kind = columns[0]
        if kind not in WIDTHS:
            raise TraceError(f"line {line_number}: unknown row {kind!r}")
        if len(columns) != WIDTHS[kind]:
            raise TraceError(f"line {line_number}: malformed {kind} width")
        try:
            values = [
                int(value, base)
                for value, base in zip(columns[1:], BASES[kind], strict=True)
            ]
        except ValueError as exc:
            raise TraceError(f"line {line_number}: non-integer field") from exc
        rows[kind].append(values)
    return {kind: rows.get(kind, []) for kind in WIDTHS}


def require_positive_trace(rows: dict[str, list[list[int]]]) -> None:
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
    if branch[:6] != [0, 0x100, 0x13, 1, 0, 0]:
        raise TraceError("B phase association differs")
    if pre[:3] != [0, 0x100, 0x13]:
        raise TraceError("PRE phase association differs")
    if post[:6] != [0, 1, 0x100, 0x13, 0x104, 1]:
        raise TraceError("POST phase/order association differs")
    if retire[:5] != [1, 1, 0x100, 0x13, 0x104]:
        raise TraceError("R phase/order association differs")
