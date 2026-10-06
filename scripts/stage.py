#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Stage this bundle into a clean, pinned Ibex checkout without downloading tools."""

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
from evidence import load_source_manifest


BUNDLE = Path(__file__).resolve().parents[1]
EXPERIMENT = BUNDLE / "experiment"
DESTINATION = Path("dv/verilator/icache_fetch_fault")
FILES = ("tb.sv", "run.py", "run_core.py", "core_program.vmem")
PATCH = BUNDLE / "patches/simple-system-fetch-fault.patch"


def git(checkout, *args):
    completed = subprocess.run(
        ("git", "-C", str(checkout), *args),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path,
                        help="separate clean lowRISC/ibex checkout at UPSTREAM_COMMIT")
    args = parser.parse_args()
    checkout = args.checkout.resolve(strict=True)
    pin = (BUNDLE / "UPSTREAM_COMMIT").read_text(encoding="ascii").strip()
    manifest = load_source_manifest(BUNDLE / "SOURCE_MANIFEST.json")
    sources = manifest["source_sha256"]
    if manifest["upstream_commit"] != pin or sha256(PATCH) != manifest["patch_sha256"]:
        raise RuntimeError("Bundle pin or patch differs from source manifest")

    if Path(git(checkout, "rev-parse", "--show-toplevel")).resolve() != checkout:
        raise RuntimeError("Checkout must be the root of a separate Git worktree")
    if git(checkout, "rev-parse", "HEAD") != pin:
        raise RuntimeError(f"Checkout is not at pinned upstream commit {pin}")
    if git(checkout, "status", "--porcelain"):
        raise RuntimeError("Upstream checkout is not clean; use a new isolated checkout")

    for name in FILES:
        expected = sources[str(DESTINATION / name).replace("\\", "/")]
        if sha256(EXPERIMENT / name) != expected:
            raise RuntimeError(f"Bundled fixture differs from source manifest: {name}")

    for path in ("rtl/ibex_pkg.sv", "rtl/ibex_icache.sv", "rtl/ibex_if_stage.sv"):
        digest = sources[path]
        if sha256(checkout / path) != digest:
            raise RuntimeError(f"Pinned upstream source bytes differ from manifest: {path}; "
                               "check checkout line-ending configuration")

    target = checkout / DESTINATION
    if any((target / name).exists() for name in FILES):
        raise RuntimeError("Pilot fixture already exists in checkout; use a clean pinned tree")
    git(checkout, "apply", "--check", str(PATCH))
    git(checkout, "apply", str(PATCH))
    for path in ("examples/simple_system/rtl/ibex_simple_system.sv",
                 "examples/simple_system/ibex_simple_system.core"):
        if sha256(checkout / path) != sources[path]:
            raise RuntimeError(f"Patched Simple System differs from manifest: {path}")
    target.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(EXPERIMENT / name, target / name)
        if sha256(EXPERIMENT / name) != sha256(target / name):
            raise RuntimeError(f"Staged fixture does not match bundle: {name}")
    print(f"Staged four hash-verified fixture files and Simple System patch at {pin}")
    print(f"Checkout: {checkout}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, RuntimeError) as exc:
        raise SystemExit(f"Candidate staging failed: {exc}") from exc
