#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Compare isolated replay to the unabridged recorded observations."""

import argparse
import hashlib
import json
from pathlib import Path


BUNDLE = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(label, recorded_path, replayed_path):
    recorded = json.loads(recorded_path.read_text(encoding="utf-8"))
    replayed = json.loads(replayed_path.read_text(encoding="utf-8"))
    if not recorded["pass"] or not replayed["pass"]:
        raise RuntimeError(f"{label}: a runner did not pass its expectations")

    binary_recorded = recorded.pop("binary_sha256", None)
    binary_replayed = replayed.pop("binary_sha256", None)
    if (binary_recorded is None) != (binary_replayed is None):
        raise RuntimeError(f"{label}: compiled binary hash missing in one result")
    if recorded != replayed:
        differing = sorted(key for key in recorded.keys() | replayed.keys()
                           if recorded.get(key) != replayed.get(key))
        raise RuntimeError(f"{label}: recorded and replayed data differ in {differing}; "
                           "inspect source hashes, per-case events, and tool versions")
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
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--core", required=True, type=Path)
    args = parser.parse_args()
    compare("I-cache", BUNDLE / "observations/results.json", args.cache)
    compare("full core", BUNDLE / "observations/core_results.json", args.core)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        raise SystemExit(f"Candidate comparison failed: {exc}") from exc
