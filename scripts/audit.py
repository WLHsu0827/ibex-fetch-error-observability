#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Scan exactly the candidate, not its external Ibex checkout."""

import hashlib
from pathlib import Path
import re
import subprocess

from evidence import load_json


BUNDLE = Path(__file__).resolve().parents[1]
EXPECTED = {
    ".gitattributes", ".gitignore", "README.md", "REPRODUCE.md", "REVIEW.md",
    "VERIFICATION.md", "UPSTREAM_COMMIT", "SOURCE_MANIFEST.json", "LICENSE", "NOTICE",
    "experiment/tb.sv", "experiment/run.py", "experiment/run_core.py",
    "experiment/core_program.vmem",
    "observations/results.json", "observations/core_results.json",
    "verification/replayed_cache.json", "verification/replayed_core.json",
    "historical/README.md",
    "historical/observations/results.json", "historical/observations/core_results.json",
    "historical/verification/replayed_cache.json",
    "historical/verification/replayed_core.json",
    "patches/simple-system-fetch-fault.patch",
    "scripts/stage.py", "scripts/compare.py", "scripts/audit.py",
    "scripts/evidence.py", "scripts/verify.py", "scripts/ci_replay.py",
    "tests/test_package.py", ".github/workflows/replay.yml",
    "upstream-notices/LICENSE", "upstream-notices/NOTICE",
}
FROZEN_HASHES = {
    "observations/results.json": "440a64d2eb4fd3b9ebbb956eb3c7ea0f4daa4859ace7935d846d7afc1cfe291f",
    "observations/core_results.json": "48fd2235e5472c88d4935577dc1322590dbfbfe9174c218501c408207d3ff2c3",
    "verification/replayed_cache.json": "440a64d2eb4fd3b9ebbb956eb3c7ea0f4daa4859ace7935d846d7afc1cfe291f",
    "verification/replayed_core.json": "cb843d8296b220757bc0f79cb1e9e206a110fd9d921ae26b281ccfc8c85b40da",
}
HISTORICAL_HASHES = {
    "historical/observations/results.json": "5a0ea2a6e530f88083b9cce9c85a7bcda366dcd9458a801dd0dc388c314b0728",
    "historical/observations/core_results.json": "79a21458bd0a70578937a7b648035e4058751d6a9e325b15ae22fdd21e1cb526",
    "historical/verification/replayed_cache.json": "5a0ea2a6e530f88083b9cce9c85a7bcda366dcd9458a801dd0dc388c314b0728",
    "historical/verification/replayed_core.json": "5c0721d1a0c58f9b66b69d6f36ebf5c4fb1b4042a4d0a3aaaa8b20de9b220791",
}
SOURCE_PATHS = {
    "rtl/ibex_pkg.sv", "rtl/ibex_icache.sv", "rtl/ibex_if_stage.sv",
    "examples/simple_system/rtl/ibex_simple_system.sv",
    "examples/simple_system/ibex_simple_system.core",
    *(f"dv/verilator/icache_fetch_fault/{name}" for name in
      ("tb.sv", "run.py", "run_core.py", "core_program.vmem")),
}
PATTERNS = {
    "local absolute path": re.compile(
        r"(?i)(?:(?<![a-z0-9])[A-Z]:[\\/]|/mnt/[a-z]/|/home/[a-z][a-z0-9._-]*/)"
    ),
    "credential signature": re.compile(
        r"(?i)(?:github_pat_[a-zA-Z0-9_]{10,}|gh[pousr]_[a-zA-Z0-9]{20,}|"
        r"AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
        r"(?:Bearer|token|password|secret)\s*[:=]\s*[A-Za-z0-9_./+-]{12,})"
    ),
    "email address": re.compile(r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}"),
}


def main():
    findings = []
    found = {str(path.relative_to(BUNDLE)).replace("\\", "/")
             for path in BUNDLE.rglob("*")
             if path.relative_to(BUNDLE).parts[0] != ".git"
             and (path.is_file() or path.is_symlink())}
    for name in sorted(found - EXPECTED):
        findings.append(f"{name}: not on the candidate allowlist")
    for name in sorted(EXPECTED - found):
        findings.append(f"{name}: missing candidate file")

    total_bytes = 0
    for name in sorted(found):
        path = BUNDLE / name
        if path.is_symlink():
            findings.append(f"{name}: symlink (may point outside candidate)")
            continue
        data = path.read_bytes()
        total_bytes += len(data)
        if len(data) > 1_000_000 or b"\0" in data:
            findings.append(f"{name}: file too large or binary")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(f"{name}: not UTF-8 text")
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append(f"{name}:{text.count(chr(10), 0, match.start()) + 1}: {label}")

    git_dir = BUNDLE / ".git"
    if git_dir.exists() or git_dir.is_symlink():
        if git_dir.is_symlink() or not (git_dir.is_dir() or git_dir.is_file()):
            findings.append(".git: unexpected or symlinked Git history")
        else:
            top = subprocess.run(
                ("git", "-C", str(BUNDLE), "rev-parse", "--show-toplevel"),
                capture_output=True, text=True, check=False,
            )
            if top.returncode or Path(top.stdout.strip()).resolve() != BUNDLE:
                findings.append(".git: not a repository/worktree rooted at this bundle")
            else:
                approved = "151040862+WLHsu0827" + chr(64) + "users.noreply.github.com"
                copilot = "223556219+Copilot" + chr(64) + "users.noreply.github.com"
                commits = subprocess.run(
                    ("git", "-C", str(BUNDLE), "rev-list", "--max-count=1",
                     "--exclude=refs/copilot/checkpoints/*", "--all"),
                    capture_output=True, text=True, check=False,
                )
                if commits.returncode:
                    findings.append(".git: could not inspect reachable commits")
                elif not commits.stdout.strip():
                    local = subprocess.run(
                        ("git", "-C", str(BUNDLE), "config", "--local", "--get", "user.email"),
                        capture_output=True, text=True, check=False,
                    )
                    if local.returncode or local.stdout.strip() != approved:
                        findings.append(".git: local author email is not the approved noreply identity")
                history = subprocess.run(
                    ("git", "-C", str(BUNDLE), "log",
                     "--exclude=refs/copilot/checkpoints/*", "--all",
                     "--format=%ae%n%ce%n%B"),
                    capture_output=True, text=True, check=False,
                )
                if history.returncode:
                    findings.append(".git: could not inspect reachable commit history")
                elif any(match.group() not in (approved, copilot)
                         for match in PATTERNS["email address"].finditer(history.stdout)):
                    findings.append(".git: unexpected email in reachable commit history")
    for name, expected in (FROZEN_HASHES | HISTORICAL_HASHES).items():
        if name in found and hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest() != expected:
            findings.append(f"{name}: frozen observation bytes changed")
    if {"upstream-notices/LICENSE", "upstream-notices/NOTICE", "LICENSE", "NOTICE"} <= found:
        license_text = (BUNDLE / "upstream-notices/LICENSE").read_text(encoding="utf-8")
        notice_text = (BUNDLE / "upstream-notices/NOTICE").read_text(encoding="utf-8")
        if "Apache License" not in license_text or "The Ibex Project" not in notice_text:
            findings.append("upstream-notices: Ibex license or NOTICE absent")
        if (BUNDLE / "LICENSE").read_bytes() != (BUNDLE / "upstream-notices/LICENSE").read_bytes():
            findings.append("LICENSE: differs from bundled Apache-2.0 license")
        if ("Copyright 2026 Wei-Lun Hsu" not in (BUNDLE / "NOTICE").read_text(encoding="utf-8")
                or "upstream-notices/NOTICE" not in (BUNDLE / "NOTICE").read_text(encoding="utf-8")):
            findings.append("NOTICE: original author or upstream attribution absent")
    if "SOURCE_MANIFEST.json" in found:
        manifest = load_json(BUNDLE / "SOURCE_MANIFEST.json")
        if set(manifest["source_sha256"]) != SOURCE_PATHS:
            findings.append("SOURCE_MANIFEST.json: source list differs from expected nine files")
        if (BUNDLE / "UPSTREAM_COMMIT").read_text(encoding="ascii").strip() != manifest["upstream_commit"]:
            findings.append("SOURCE_MANIFEST.json: upstream pin differs")
        patch = BUNDLE / "patches/simple-system-fetch-fault.patch"
        if patch.is_file() and hashlib.sha256(patch.read_bytes()).hexdigest() != manifest["patch_sha256"]:
            findings.append("SOURCE_MANIFEST.json: patch bytes differ")
        for name in ("tb.sv", "run.py", "run_core.py", "core_program.vmem"):
            path = f"experiment/{name}"
            if path in found:
                recorded = manifest["source_sha256"][f"dv/verilator/icache_fetch_fault/{name}"]
                actual = hashlib.sha256((BUNDLE / path).read_bytes()).hexdigest()
                if actual != recorded:
                    findings.append(f"{path}: differs from source manifest")
    if {"observations/results.json", "observations/core_results.json", "SOURCE_MANIFEST.json"} <= found:
        cache = load_json(BUNDLE / "observations/results.json")
        core = load_json(BUNDLE / "observations/core_results.json")
        for source in (cache, core):
            if source["pass"] is not True:
                findings.append("observations: a recorded experiment failed")
            for path, digest in source["source_sha256"].items():
                if manifest["source_sha256"].get(path) != digest:
                    findings.append(f"observations: current source hash differs for {path}")
    for name in ("tb.sv", "run.py", "run_core.py", "core_program.vmem"):
        if f"experiment/{name}" not in found:
            continue
        header = (BUNDLE / "experiment" / name).read_text(encoding="utf-8")[:400]
        if "Copyright 2026 Wei-Lun Hsu" not in header or "SPDX-License-Identifier: Apache-2.0" not in header:
            findings.append(f"experiment/{name}: original author or SPDX header missing")
    for name in ("stage.py", "compare.py", "audit.py", "evidence.py",
                 "verify.py", "ci_replay.py"):
        if f"scripts/{name}" not in found:
            continue
        header = (BUNDLE / "scripts" / name).read_text(encoding="utf-8")[:400]
        if "Copyright 2026 Wei-Lun Hsu" not in header or "SPDX-License-Identifier: Apache-2.0" not in header:
            findings.append(f"scripts/{name}: original author or SPDX header missing")

    print(f"Candidate audit: {len(found)} files, {total_bytes} bytes, "
          f"{len(findings)} flagged locations")
    for finding in findings:
        print(finding)
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(f"Candidate audit failed: {exc}") from exc
