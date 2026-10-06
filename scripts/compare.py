#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Compare isolated replay to the unabridged recorded observations."""

import argparse
import hashlib
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from evidence import load_json


BUNDLE = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_difference(recorded, replayed, path="$"):
    if type(recorded) is not type(replayed):
        return f"{path}: expected {type(recorded).__name__}, received {type(replayed).__name__}"
    if isinstance(recorded, dict):
        missing = recorded.keys() - replayed.keys()
        extra = replayed.keys() - recorded.keys()
        if missing:
            return f"{path}.{sorted(missing)[0]}: missing field"
        if extra:
            return f"{path}.{sorted(extra)[0]}: unexpected field"
        for key in sorted(recorded):
            difference = first_difference(recorded[key], replayed[key], f"{path}.{key}")
            if difference is not None:
                return difference
    elif isinstance(recorded, list):
        if len(recorded) != len(replayed):
            return f"{path}: expected {len(recorded)} entries, received {len(replayed)}"
        for index, (expected, actual) in enumerate(zip(recorded, replayed)):
            difference = first_difference(expected, actual, f"{path}[{index}]")
            if difference is not None:
                return difference
    elif recorded != replayed or (
        isinstance(recorded, float) and recorded.hex() != replayed.hex()
    ):
        return f"{path}: value differs"
    return None


def compare(label, recorded_path, replayed_path):
    recorded = load_json(recorded_path)
    replayed = load_json(replayed_path)
    for path, data in ((recorded_path, recorded), (replayed_path, replayed)):
        if data.get("pass") is not True:
            raise RuntimeError(f"{label}: {path}: 'pass' must be the JSON boolean true; "
                               "a runner did not pass its expectations")

    has_binary = "binary_sha256" in recorded
    if has_binary != ("binary_sha256" in replayed):
        raise RuntimeError(f"{label}: {replayed_path}: compiled binary hash field "
                           "is missing or unexpected for this suite")
    binary_recorded = binary_replayed = None
    if has_binary:
        binary_recorded = recorded.pop("binary_sha256")
        binary_replayed = replayed.pop("binary_sha256")
        if any(not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
               for value in (binary_recorded, binary_replayed)):
            raise RuntimeError(f"{label}: malformed compiled binary SHA-256")

    difference = first_difference(recorded, replayed)
    if difference is not None:
        raise RuntimeError(f"{label}: {replayed_path}: recorded and replayed data differ "
                           f"at {difference}; inspect source hashes, per-case events, "
                           "and tool versions")
    print(f"{label}: source hashes, complete case events, assertions and "
          "checker classifications match")
    if binary_recorded is not None:
        print(f"{label}: compiled binary SHA-256 "
              f"{'matches' if binary_recorded == binary_replayed else 'differs'}")
    if sha256(recorded_path) == sha256(replayed_path):
        print(f"{label}: JSON byte-identical")
    else:
        print(f"{label}: JSON NOT byte-identical (binary hash or serialization differs)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path,
                        help="complete standalone replay JSON (not a log or summary)")
    parser.add_argument("--core", required=True, type=Path,
                        help="complete whole-core replay JSON; only its valid binary "
                             "hash value may differ from the recorded evidence")
    args = parser.parse_args()
    compare("I-cache", BUNDLE / "observations/results.json", args.cache)
    compare("full core", BUNDLE / "observations/core_results.json", args.core)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        raise SystemExit(f"Candidate comparison failed: {exc}") from exc
