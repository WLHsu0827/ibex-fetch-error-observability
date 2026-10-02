# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Machine-computed immutable source manifest; excludes prose and later evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .process import identity, write_json

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rvfi_nextpc" / "SOURCE_MANIFEST.json"


def inputs() -> dict[str, object]:
    paths = sorted(path for path in (ROOT / "rvfi_nextpc").iterdir()
                   if path.is_file() and path.suffix in
                   (".py", ".sv", ".cpp", ".hpp", ".core", ".S", ".ld", ".txt", ".json")
                   and path != MANIFEST)
    paths += [ROOT / ".github" / "workflows" / "rvfi-nextpc.yml", ROOT / "LICENSE"]
    return {path.relative_to(ROOT).as_posix(): identity(path) for path in paths}


def verify() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
    if manifest["schema"] != 1 or manifest["files"] != inputs():
        raise ValueError("source/workflow/license manifest mismatch")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    if args.create:
        write_json(MANIFEST, {"schema": 1, "files": inputs()})
    else:
        verify()
        print("NEXTPC_SOURCE_MANIFEST_PASS")
