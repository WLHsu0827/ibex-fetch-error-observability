# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Exact qualified GNU make drivers and bounded installed-input identities."""

from __future__ import annotations

import shlex

DRIVERS = {
    "CXX": "/usr/bin/g++-13", "CC": "/usr/bin/gcc-13", "LINK": "/usr/bin/g++-13",
    "AR": "/usr/bin/ar", "PYTHON3": "/usr/bin/python3", "PERL": "/usr/bin/perl",
    "OBJCACHE": "",
}
MAKE = ["make", "-j1", "NUM_JOBS=1", *[f"{name}={value}" for name, value in DRIVERS.items()]]
PROBE = (
    "nextpc-driver-probe: ; @printf '%s\\n' "
    + " ".join(f"'{name}=$({name})'" for name in DRIVERS)
    + " 'MAKEFLAGS=$(MAKEFLAGS)'"
)


def validate_probe(text: str) -> dict[str, str]:
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
