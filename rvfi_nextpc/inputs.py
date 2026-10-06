# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Fail-closed generated build command and ELF/image boundary checks."""

from __future__ import annotations

import shlex
import struct

from .isa import BOOT


def build_options(config: str, vc: str) -> list[str]:
    lines = [line.split(":=", 1)[1].strip() for line in config.splitlines()
             if line.startswith("VERILATOR_OPTIONS :=")]
    if len(lines) != 1:
        raise ValueError("missing/duplicate generated build options")
    args = shlex.split(lines[0])
    if args != ["-DDISABLE_PRIM_CDC_RAND_DELAY", "-Wall", "--unroll-count", "72",
                "-CFLAGS", "-std=c++17 -Wall -Wextra -Werror"]:
        raise ValueError("actual make shell loses CFLAGS quoting or adds unchecked options")
    tokens = shlex.split(vc)
    if tokens.count("--cc") != 1 or tokens.count("--exe") != 1 or (
        "-DRVFI=1" not in tokens or "-DOBSERVER_TARGET=ibex_top" not in tokens
        or not any(token.endswith("/main.cpp") for token in tokens)
    ):
        raise ValueError("missing real model mode/observer/CPU harness inputs")
    return args


def validate_elf(data: bytes, image: bytes) -> None:
    if len(data) < 52:
        raise ValueError("truncated ELF")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    magic, kind, machine, version, entry, _, sections, _, size, _, _, shsize, count, strings = header
    if magic[:7] != b"\x7fELF\x01\x01\x01" or (kind, machine, version, entry, size, shsize) != (
        2, 243, 1, BOOT, 52, 40
    ) or not 0 < strings < count or sections + count * shsize > len(data):
        raise ValueError("wrong ELF ISA, entry, class or section boundary")
    table = [struct.unpack_from("<IIIIIIIIII", data, sections + index * shsize)
             for index in range(count)]
    offset, length = table[strings][4:6]
    names = data[offset:offset + length]
    if len(names) != length or not names.endswith(b"\0"):
        raise ValueError("truncated ELF section names")
    allocated = []
    for item in table:
        name, section_type, flags, address, offset, length = item[:6]
        if name >= len(names):
            raise ValueError("invalid ELF section name")
        if flags & 2 and length:
            end = names.find(b"\0", name)
            allocated.append((names[name:end], section_type, address, data[offset:offset + length]))
            if offset + length > len(data):
                raise ValueError("truncated ELF allocated bytes")
    if allocated != [(b".text", 1, BOOT, image)]:
        raise ValueError("ELF/objcopy image or allocated-section mismatch")


def boundaries(text: str) -> dict[str, int]:
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] in ("_start", "drain", "terminal"):
            if parts[2] in result or parts[1] not in ("T", "t"):
                raise ValueError("duplicate/non-text program boundary")
            result[parts[2]] = int(parts[0], 16)
    if set(result) != {"_start", "drain", "terminal"} or result["_start"] != BOOT:
        raise ValueError("missing program or incorrect boot boundary")
    return result
