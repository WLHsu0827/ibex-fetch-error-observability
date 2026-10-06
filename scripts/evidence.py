#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Read strict JSON evidence and validate the shared source manifest."""

import json
import math
import re


SOURCE_PATHS = {
    "rtl/ibex_pkg.sv", "rtl/ibex_icache.sv", "rtl/ibex_if_stage.sv",
    "examples/simple_system/rtl/ibex_simple_system.sv",
    "examples/simple_system/ibex_simple_system.core",
    *(f"dv/verilator/icache_fetch_fault/{name}" for name in
      ("tb.sv", "run.py", "run_core.py", "core_program.vmem")),
}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"Non-finite JSON number is not permitted: {value}")


def finite_float(value):
    parsed = float(value)
    if not math.isfinite(parsed):
        reject_constant(value)
    return parsed


def load_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=unique_object,
                          parse_constant=reject_constant, parse_float=finite_float)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON at line {exc.lineno}, "
                         f"column {exc.colno}: {exc.msg}") from exc
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a top-level JSON object, "
                         f"received {type(data).__name__}")
    return data


def load_source_manifest(path):
    manifest = load_json(path)
    required = {"upstream_commit", "patch_sha256", "source_sha256"}
    if set(manifest) != required:
        raise ValueError(f"{path}: manifest fields must be {sorted(required)}; "
                         f"missing {sorted(required - manifest.keys())}, "
                         f"unexpected {sorted(manifest.keys() - required)}")
    for field, length in (("upstream_commit", 40), ("patch_sha256", 64)):
        value = manifest[field]
        if not isinstance(value, str) or re.fullmatch(rf"[0-9a-f]{{{length}}}", value) is None:
            raise ValueError(f"{path}: {field} must be a {length}-digit lowercase hex hash")
    sources = manifest["source_sha256"]
    if not isinstance(sources, dict) or set(sources) != SOURCE_PATHS:
        raise ValueError(f"{path}: source_sha256 must be an object listing "
                         "exactly the expected nine source files")
    for name, digest in sources.items():
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"{path}: source_sha256.{name} must be a "
                             "64-digit lowercase hex hash")
    return manifest
