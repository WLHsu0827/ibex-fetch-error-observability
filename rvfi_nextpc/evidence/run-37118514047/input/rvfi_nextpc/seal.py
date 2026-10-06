# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Machine-computed immutable source manifest; excludes prose and later evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from .process import write_json

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "rvfi_nextpc" / "SOURCE_MANIFEST.json"


def inputs() -> dict[str, object]:
    paths = sorted(path for path in (ROOT / "rvfi_nextpc").iterdir()
                   if path.is_file() and path.suffix in
                   (".py", ".sv", ".cpp", ".hpp", ".core", ".S", ".ld", ".txt", ".json", ".mk")
                   and path != MANIFEST)
    paths += [ROOT / ".github" / "workflows" / "rvfi-nextpc.yml", ROOT / "LICENSE"]
    result = {}
    for path in paths:
        data = path.read_bytes()
        if path != ROOT / "LICENSE":
            data = data.replace(b"\r\n", b"\n")
        result[path.relative_to(ROOT).as_posix()] = {
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        }
    return result


def verify() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="ascii"))
    if manifest["schema"] != 1 or manifest["files"] != inputs():
        raise ValueError("source/workflow/license manifest mismatch")
    return manifest


def git_identity(name: str, ref: str = "HEAD") -> dict[str, object]:
    if name not in inputs():
        raise ValueError("not a sealed public input")
    data = subprocess.check_output(["git", "show", f"{ref}:{name}"], cwd=ROOT)
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    if args.create:
        write_json(MANIFEST, {
            "schema": 1, "files": inputs(),
            "representation": "Git LF-normalized new text; existing LICENSE retains original bytes",
        })
    else:
        verify()
        print("NEXTPC_SOURCE_MANIFEST_PASS")
