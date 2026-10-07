"""Strict transcript contract. This is not evidence of a benchmark/CPU run."""

import re

try:
    from .config import CONFIG_SHA, WORKLOADS
except ImportError:
    from config import CONFIG_SHA, WORKLOADS

PREFIX = "STOCK_PROFILE_V1"
MARKER = re.compile(
    r"STOCK_PROFILE_V1 workload=([a-z0-9-]+) config=([0-9a-f]{64}) "
    r"mode=selfcheck_only verify=(-1|0|1) complete=1"
)
VALIDATED = "Correct operation validated. See README.md for run and reporting rules."


def classify(termination, stdout, stderr, program, workload):
    result = {"termination": termination, "completed": False,
              "verification": "NOT_VERIFIED", "reason": ""}
    combined = stdout + b"\n" + stderr + b"\n" + program
    if termination != "exit_zero":
        result["reason"] = termination
        return result
    if b"Simulation timeout of " in combined:
        result.update(termination="cycle_timeout", reason="stock cycle-limit message")
        return result
    if any(word in combined for word in
           (b"EXCEPTION!!!", b"%Error", b"Assertion failed", b"Received stop request")):
        result.update(termination="trap", verification="FAILED", reason="trap/stop diagnostic")
        return result
    try:
        text = program.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        result["reason"] = "non-UTF8 program output"
        return result
    if workload not in (*WORKLOADS, "coremark"):
        result["reason"] = "unlisted workload"
        return result
    lines = [line for line in text.splitlines() if PREFIX in line]
    if len(lines) != 1 or not text.endswith("\n"):
        result["reason"] = "missing/duplicate/truncated marker"
        return result
    match = MARKER.fullmatch(lines[0])
    if match is None or match[1] != workload or match[2] != CONFIG_SHA:
        result["reason"] = "malformed marker or workload/config mismatch"
        return result
    result["completed"] = True
    if workload == "coremark":
        verified, reason = coremark_selfcheck(text)
        result.update(verification=verified, reason=reason)
    else:
        result["verification"] = {"1": "VERIFIED", "0": "FAILED", "-1": "NOT_VERIFIED"}[match[3]]
        result["reason"] = "official verifier return (1/0/-1); selfcheck_only"
    return result


def coremark_selfcheck(text):
    # crcfinal is printed but is NOT an official expected-CRC table entry.
    expected = {
        r"CoreMark Size\s*:\s*(\d+)": "666",
        r"Iterations\s*:\s*(\d+)": "10",
        r"Memory location\s*:\s*(\w+)": "STACK",
        r"seedcrc\s*:\s*0x([0-9a-fA-F]{4})": "e9f5",
        r"\[0\]crclist\s*:\s*0x([0-9a-fA-F]{4})": "e714",
        r"\[0\]crcmatrix\s*:\s*0x([0-9a-fA-F]{4})": "1fd7",
        r"\[0\]crcstate\s*:\s*0x([0-9a-fA-F]{4})": "8e3a",
    }
    if any(word in text for word in ("ERROR!", "Errors detected", "Cannot validate")):
        return "FAILED", "official CoreMark error diagnostic"
    for pattern, value in expected.items():
        matches = re.findall("^" + pattern + "$", text, re.M)
        if len(matches) != 1:
            return "NOT_VERIFIED", "missing/duplicate/malformed CoreMark validation field"
        if matches[0].lower() != value.lower():
            return "FAILED", "official CRC or fixed input configuration mismatch"
    if text.splitlines().count(VALIDATED) != 1:
        return "NOT_VERIFIED", "missing/duplicate official validation sentence"
    if len(re.findall(r"^\[0\]crcfinal\s*:\s*0x[0-9a-fA-F]{4}$", text, re.M)) != 1:
        return "NOT_VERIFIED", "missing/duplicate/malformed final CRC (no guessed expected value)"
    if re.search(r"^\[[1-9]\d*\]crc", text, re.M) or "Parallel " in text:
        return "FAILED", "unexpected additional contexts"
    return "VERIFIED", "vendored official known_id=3 CRC semantics; NOT an official score"
