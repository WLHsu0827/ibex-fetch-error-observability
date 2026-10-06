# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Exact active module identity; separately retained, strictly checked unused launcher."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path, PurePosixPath
import platform
import re
import sys

from .process import identity, write_json

MODULE = "fusesoc.main"
VERSION = "2.4.3"
FLAGS = ["-I", "-B", "-m", MODULE]
# Public pip 25.3 PipScriptMaker template, not an arbitrary shebang/body normalization.
LAUNCHER_BODY = b"""import sys
from fusesoc.main import main
if __name__ == '__main__':
    if sys.argv[0].endswith('.exe'):
        sys.argv[0] = sys.argv[0][:-4]
    sys.exit(main())
"""


def digest(data: bytes) -> dict[str, object]:
    import hashlib

    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def validate(receipt: dict[str, object], launcher: bytes) -> dict[str, object]:
    if set(receipt) != {"schema", "active", "diagnostic"} or receipt["schema"] != 1:
        raise ValueError("missing/extra entrypoint receipt")
    active, diagnostic = receipt["active"], receipt["diagnostic"]
    if set(active) != {"flags", "distribution", "version", "entry_point", "interpreter",
                       "python_version", "module", "lock", "runtime_code", "launcher_body"} or (
        active["flags"] != FLAGS or active["distribution"] != "fusesoc"
        or active["version"] != VERSION or active["entry_point"] != MODULE + ":main"
        or active["python_version"] != "3.12.3"
        or active["launcher_body"] != digest(LAUNCHER_BODY)
    ):
        raise ValueError("active invocation/version/body differs from qualified design")
    for name in ("interpreter", "module", "lock", "runtime_code", "launcher_body"):
        item = active[name]
        if not isinstance(item, dict) or set(item) != {"bytes", "sha256"} or (
            type(item["bytes"]) is not int or item["bytes"] <= 0
            or not re.fullmatch("[0-9a-f]{64}", str(item["sha256"]))
        ):
            raise ValueError("invalid/truncated active identity")
    if set(diagnostic) != {"argv", "python_resolved", "launcher_path", "launcher", "shebang"}:
        raise ValueError("missing/extra launcher diagnostics")
    argv = diagnostic["argv"]
    if not isinstance(argv, list) or len(argv) != 5 or not isinstance(argv[0], str) or argv[1:] != FLAGS or not re.fullmatch(
        r"/tmp/rvfi-nextpc-[0-9]+/tools/bin/python", argv[0]
    ):
        raise ValueError("invalid active interpreter path/invocation")
    resolved = diagnostic["python_resolved"]
    if not isinstance(resolved, str) or str(PurePosixPath(resolved)) != resolved or not re.fullmatch(
        r"/usr/bin/python3\.12|/opt/hostedtoolcache/Python/3\.12\.3/x64/bin/python3\.12", resolved
    ):
        raise ValueError("invalid resolved interpreter path")
    if diagnostic["launcher_path"] != str(PurePosixPath(argv[0]).with_name("fusesoc")) or (
        diagnostic["launcher"] != digest(launcher)
        or diagnostic["shebang"] != "#!" + argv[0]
        or launcher != ("#!" + argv[0] + "\n").encode("ascii") + LAUNCHER_BODY
    ):
        raise ValueError("unrelated launcher body, shebang, path or raw identity mismatch")
    return active


def read_receipt(path: Path) -> dict[str, object]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("duplicate identity receipt key")
        return result

    return json.loads(path.read_text(encoding="ascii"), object_pairs_hook=unique)


def compare(previous: Path, current: Path, name: str = "entrypoint.json",
            current_name: str | None = None) -> dict[str, object]:
    first = validate(read_receipt(previous / name), (previous / "fusesoc-launcher.txt").read_bytes())
    second = validate(read_receipt(current / (current_name or name)), (current / "fusesoc-launcher.txt").read_bytes())
    if first != second:
        raise ValueError("qualified active interpreter/module/package/lock identity changed")
    return first


def capture(output: Path, name: str, python: str, runtime: Path, lock: Path) -> None:
    from .toolchain import installed_report

    launcher = Path(python).with_name("fusesoc")
    raw = launcher.read_bytes()
    raw_path = output / "fusesoc-launcher.txt"
    if raw_path.exists():
        if raw_path.read_bytes() != raw:
            raise ValueError("unused launcher changed within run")
    else:
        with raw_path.open("xb") as stream:
            stream.write(raw)
    config = json.loads(lock.read_text())
    current = installed_report(config, "runtime")
    if current != json.loads(runtime.read_text()):
        raise ValueError("active installed package code/closure changed")
    if python != sys.executable or Path(python).resolve() != Path(sys.executable).resolve():
        raise ValueError("entrypoint inspection used a different interpreter")
    distribution = importlib.metadata.distribution("fusesoc")
    entries = [item for item in distribution.entry_points if item.group == "console_scripts"
               and item.name == "fusesoc"]
    if len(entries) != 1 or entries[0].value != MODULE + ":main" or distribution.version != VERSION:
        raise ValueError("pinned public package entrypoint changed")
    module = Path(importlib.util.find_spec(MODULE).origin)
    if module != Path(distribution.locate_file("fusesoc/main.py")) or not module.read_bytes().endswith(
        b'if __name__ == "__main__":\n    main()\n'
    ):
        raise ValueError("pinned package does not support the active -m invocation")
    receipt = {
        "schema": 1,
        "active": {"flags": FLAGS, "distribution": "fusesoc", "version": VERSION,
                   "entry_point": entries[0].value, "interpreter": identity(Path(python).resolve()),
                   "python_version": platform.python_version(), "module": identity(module),
                   "lock": identity(lock), "runtime_code": identity(runtime),
                   "launcher_body": digest(LAUNCHER_BODY)},
        "diagnostic": {"argv": [python, *FLAGS], "python_resolved": str(Path(python).resolve()),
                       "launcher_path": str(launcher), "launcher": digest(raw),
                       "shebang": raw.split(b"\n", 1)[0].decode("ascii")},
    }
    validate(receipt, raw)
    write_json(output / name, receipt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--name", default="entrypoint.json")
    parser.add_argument("--python", required=True)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    args = parser.parse_args()
    capture(args.output, args.name, args.python, args.runtime, args.lock)
