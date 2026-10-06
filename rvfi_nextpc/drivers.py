# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Exact qualified GNU make drivers and bounded installed-input identities."""

from __future__ import annotations

import shlex
from pathlib import Path
import re

from .process import identity

DRIVERS = {
    "CXX": "/usr/bin/g++-13", "CC": "/usr/bin/gcc-13", "LINK": "/usr/bin/g++-13",
    "AR": "/usr/bin/ar", "PYTHON3": "/usr/bin/python3", "PERL": "/usr/bin/perl",
    "OBJCACHE": "",
}
MAKE = ["make", "-j1", "NUM_JOBS=1", *[f"{name}={value}" for name, value in DRIVERS.items()]]
PROBE_SCRIPT = "nextpc_driver_probe.mk"
PROBE_DIRECTORY = "nextpc_driver_probe"
PROBE_FIELDS = (*DRIVERS, "NUM_JOBS", "MAKELEVEL", "MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES",
                "NEXTPC_PROBE_MAKEFILE", "NEXTPC_PROBE_CHILD")
VALUE_END = b"\nNEXTPC_END_VALUE\n"


def prepare_probe(build: Path, script: Path, makefile: str) -> list[str]:
    if not re.fullmatch(r"V[A-Za-z0-9_]+\.mk", makefile) or not (build / makefile).is_file():
        raise ValueError("missing/invalid generated probe makefile")
    with (build / PROBE_SCRIPT).open("xb") as destination:
        destination.write(script.read_bytes())
    (build / PROBE_DIRECTORY).mkdir()
    return [*MAKE, "--no-print-directory", "-f", PROBE_SCRIPT,
            f"NEXTPC_PROBE_MAKEFILE={makefile}", "nextpc-outer-driver-probe"]


def make_words(text: str) -> list[str]:
    """GNU make escapes whitespace/backslashes, not shell quote characters."""
    words, current, escaped = [], [], False
    for char in text:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char.isspace():
            if current:
                words.append("".join(current))
                current = []
        else:
            current.append(char)
    if escaped:
        raise ValueError("truncated GNU make flags escape")
    if current:
        words.append("".join(current))
    return words


def validate_expanded(result: dict[str, str], makefile: str) -> dict[str, str]:
    if set(result) != set(PROBE_FIELDS) or any(not isinstance(value, str) for value in result.values()):
        raise ValueError("missing/duplicate/truncated expanded driver receipt")
    if any(result[key] != value for key, value in DRIVERS.items()) or (
        result["NUM_JOBS"] != "1" or result["MAKELEVEL"] != "1"
        or result["NEXTPC_PROBE_CHILD"] != "1" or result["NEXTPC_PROBE_MAKEFILE"] != makefile
    ):
        raise ValueError("unbound/incorrect recursive driver, worker or model identity")
    for name in ("MAKEFLAGS", "MFLAGS"):
        words = make_words(result[name])
        options = words[:words.index("--")] if "--" in words else words
        jobs = [word for word in options if word.startswith(("-j", "--jobs", "--jobserver"))]
        if jobs != ["-j1"]:
            raise ValueError("recursive make is not explicitly single-worker")
    return result


def read_probe(directory: Path, makefile: str) -> dict[str, str]:
    if {path.name for path in directory.iterdir()} != set(PROBE_FIELDS):
        raise ValueError("missing/extra expanded driver field files")
    result = {}
    for name in PROBE_FIELDS:
        data = (directory / name).read_bytes()
        if not data.endswith(VALUE_END):
            raise ValueError("truncated expanded driver field")
        result[name] = data[:-len(VALUE_END)].decode("utf-8")
    return validate_expanded(result, makefile)


def probe_receipt(build: Path, makefile: str) -> dict[str, object]:
    directory = build / PROBE_DIRECTORY
    return {
        "schema": 2, "result": "PASS", "expanded": read_probe(directory, makefile),
        "fields": {name: identity(directory / name) for name in PROBE_FIELDS},
        "probe_script": identity(build / PROBE_SCRIPT),
        "generated_make": identity(build / makefile), "invocation": MAKE,
        "semantics": "Original make-expanded values use file functions, never shell interpolation. Sentinel framing preserves whitespace/quotes/newlines; no flag normalization.",
    }


def validate_probe(text: str) -> dict[str, str]:
    """Legacy v1 archive check only; new invocations use framed field files."""
    lines = text.splitlines()
    pairs = [line.split("=", 1) for line in lines]
    if any(len(pair) != 2 for pair in pairs) or len(pairs) != len(DRIVERS) + 1:
        raise ValueError("missing/duplicate/truncated expanded recursive driver receipt")
    result = dict(pairs)
    if len(result) != len(pairs) or any(result.get(key) != value for key, value in DRIVERS.items()):
        raise ValueError("unbound/incorrect actual recursive compiler/link/helper driver")
    flags = shlex.split(result["MAKEFLAGS"].split(" -- ", 1)[0])
    if "-j1" not in flags or any(
        flag.startswith("-j") and flag != "-j1" or flag.startswith("--jobs") for flag in flags
    ):
        raise ValueError("recursive make is not explicitly single-worker")
    if "NUM_JOBS=1" not in shlex.split(result["MAKEFLAGS"]):
        raise ValueError("missing/truncated recursive worker assignment")
    return result


def validate_recipes(makefile: str, included: str, outer: str | None = None) -> None:
    if "include $(VERILATOR_ROOT)/include/verilated.mk" not in makefile or (
        "$(LINK)" not in makefile or "$(CXX)" not in included or "$(AR)" not in included
        or "$(PYTHON3) $(VERILATOR_ROOT)/bin/verilator_includer" not in included
    ):
        raise ValueError("actual generated/installed recursive driver recipes changed")
    assignments = {name: [line for line in included.splitlines() if line.startswith(name + " = ")]
                   for name in ("CXX", "LINK", "AR", "PYTHON3", "PERL")}
    if any(len(lines) != 1 for lines in assignments.values()):
        raise ValueError("ambiguous/missing installed make driver assignments")
    if outer is not None and (
        "$(MAKE) $(MAKE_OPTIONS) -f $<" not in outer
        or "$(VERILATOR)" not in outer
    ):
        raise ValueError("outer build is not the reviewed recursive make recipe")


def validate_commands(text: str, model: str) -> dict[str, object]:
    commands = [shlex.split(line.strip()) for line in text.splitlines()
                if line.strip().startswith(DRIVERS["CXX"] + " ")]
    compiled = [line for line in commands if "-c" in line]
    links = [line for line in commands if "-c" not in line and len(line) >= 3
             and line[-2:] == ["-o", model]]
    if not compiled or len(links) != 1 or not any(DRIVERS["AR"] in line for line in text.splitlines()):
        raise ValueError("actual compile/link/archive command closure absent or wrong driver")
    for line in text.splitlines():
        tokens = shlex.split(line.strip())
        if tokens and tokens[0] in ("g++", "g++-13", "gcc", "cc", "clang++"):
            raise ValueError("unbound actual compile/link alias")
    return {"compile_commands": len(compiled), "link_argv": links[0], "archiver": DRIVERS["AR"]}
