"""Run offline stdlib contracts, preserving bounded original test output."""

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from bounded import capture, Limits
from config import HERE

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=pathlib.Path, default=HERE / "_receipts")
    args = parser.parse_args()
    receipts = args.receipts.resolve()
    if not receipts.is_relative_to(HERE / "_receipts"):
        raise SystemExit("receipts must remain inside stock_profile/_receipts")
    os.environ["STOCK_PROFILE_TEST_RECEIPTS"] = str(receipts / "synthetic")
    record, streams = capture(
        [sys.executable, "-I", "-B", str(HERE / "tests" / "test_contracts.py"), "-v"],
        receipts / "contracts", Limits(wall_seconds=90, output_bytes=512 * 1024),
        resource_limits=False,
    )
    record["argv"] = ["python", "-I", "-B", "stock_profile/tests/test_contracts.py", "-v"]
    (receipts / "contracts" / "status.json").write_text(json.dumps(record, indent=2) + "\n")
    print(streams["stdout"].decode(errors="strict"), end="")
    print(streams["stderr"].decode(errors="strict"), end="", file=sys.stderr)
    if record["termination"] != "exit_zero":
        raise SystemExit("stdlib contracts failed; STOP")
