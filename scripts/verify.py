#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Verify the public package and checker contracts; never execute RTL."""

import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Requires Python and Git only. For fresh RTL, see the separately "
               "labeled GitHub-hosted workflow in REPRODUCE.md.",
    )
    parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    commands = [
        [sys.executable, "-B", "scripts/audit.py"],
        [sys.executable, "-B", "scripts/compare.py",
         "--cache", "verification/replayed_cache.json",
         "--core", "verification/replayed_core.json"],
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
    ]
    print("PACKAGE/OFFLINE validation of frozen public evidence, NOT fresh RTL.",
          flush=True)
    for command in commands:
        completed = subprocess.run(command, cwd=root, env=env, check=False)
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
