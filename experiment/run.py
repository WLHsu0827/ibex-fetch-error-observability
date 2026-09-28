#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""Run the I-cache fetch-error boundary experiments with open-source Verilator."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TARGET = "0x00001000"
EXPECTED = {
    "hit_control": {
        "fault_injections": 0,
        "bus_errors": 0,
        "if_handoffs": 1,
        "if_errors": 0,
        "if_good_nops": 1,
        "cache_warmed": 1,
        "cache_hits_min": 1,
    },
    "speculative_hit": {
        "fault_injections": 1,
        "bus_errors": 1,
        "if_handoffs": 1,
        "if_errors": 0,
        "if_good_nops": 1,
        "cache_warmed": 1,
        "cache_hits_min": 1,
    },
    "demand_miss": {
        "fault_injections": 1,
        "bus_errors": 1,
        "if_handoffs": 1,
        "if_errors": 1,
        "if_good_nops": 0,
        "cache_warmed": 0,
        "cache_hits": 0,
    },
}


def command(argv, *, cwd=ROOT, timeout=600):
    result = subprocess.run(
        argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(map(str, argv))}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result.stdout


def events_and_observation(stdout, scenario):
    events = []
    results = []
    for line in stdout.splitlines():
        if line.startswith("PILOT_EVENT:"):
            events.append(json.loads(line.removeprefix("PILOT_EVENT:")))
        if line.startswith("PILOT_RESULT:"):
            results.append(json.loads(line.removeprefix("PILOT_RESULT:")))
    if len(results) != 1 or results[0]["scenario"] != scenario:
        raise RuntimeError(f"Missing or duplicate result for {scenario}:\n{stdout}")
    return events, results[0]


def classify(cases, checker):
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for case in cases.values():
        actual = case["observed"]
        predicted = actual[checker] > 0
        # Reference is the error actually handed across the cache -> IF interface.
        reference = actual["if_errors"] > 0
        counts[("t" if predicted == reference else "f") + ("p" if predicted else "n")] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", default=os.environ.get("VERILATOR", "verilator"))
    parser.add_argument("--trace", action="store_true", help="write per-case VCDs in build/")
    parser.add_argument("--output", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    build = ROOT / "build" / "fetch_error_pilot"
    build.mkdir(parents=True, exist_ok=True)
    version = command([args.verilator, "--version"]).strip()
    command(
        [
            args.verilator, "--binary", "--timing", "--trace", "-j", "2",
            "--top-module", "tb_fetch_fault", "-Wno-TIMESCALEMOD",
            "--Mdir", str(build / "obj"),
            "-Ivendor/lowrisc_ip/ip/prim/rtl",
            "rtl/ibex_pkg.sv", "rtl/ibex_icache.sv", str(HERE / "tb.sv"),
        ]
    )
    binary = build / "obj" / "Vtb_fetch_fault"
    cases = {}
    for scenario, expected in EXPECTED.items():
        case_dir = build / scenario
        case_dir.mkdir(exist_ok=True)
        stdout = command(
            [str(binary), f"+scenario={scenario}"] + (["+trace"] if args.trace else []),
            cwd=case_dir,
            timeout=30,
        )
        waveform = case_dir / "trace.vcd"
        if args.trace and (not waveform.is_file() or waveform.stat().st_size == 0):
            raise RuntimeError(f"Missing or empty waveform: {waveform}")
        events, observed = events_and_observation(stdout, scenario)
        deviations = {}
        for field, value in expected.items():
            is_minimum = field.endswith("_min")
            actual = observed[field[:-4] if is_minimum else field]
            if (actual < value if is_minimum else actual != value):
                deviations[field] = {"expected": value, "actual": actual}
        if observed["target_requests"] != 1 or observed["target_responses"] != 1:
            deviations["target_bus_transactions"] = {
                "expected": 1,
                "requests": observed["target_requests"],
                "responses": observed["target_responses"],
            }
        bus = [e for e in events if e["kind"] == "bus_response" and e["addr"] == TARGET]
        handoff = [e for e in events if e["kind"] == "if_handoff" and e["addr"] == TARGET]
        if len(bus) != 1 or len(handoff) != 1 or bus[0]["cycle"] >= handoff[0]["cycle"]:
            deviations["response_before_handoff"] = {
                "bus_events": bus, "if_events": handoff
            }
        cases[scenario] = {
            "cache_state": "cold" if scenario == "demand_miss" else "warm",
            "fault_class": "none" if scenario == "hit_control" else "single_bus_response_error",
            "fault_injection": {
                "location": "instruction bus response instr_err_i",
                "address": TARGET, "enabled": scenario != "hit_control",
                "one_shot": True, "response_latency_cycles": 1,
                "grant": "immediate",
            },
            "expected": expected, "observed": observed, "events": events,
            "deviations": deviations, "pass": not deviations,
            "waveform": str(waveform.relative_to(ROOT)) if args.trace else None,
            "trap_observed": None,
        }
        print(f"{scenario}: {'PASS' if not deviations else 'FAIL'} "
              f"(bus_err={observed['bus_errors']}, if_err={observed['if_errors']}, "
              f"cache_hits={observed['cache_hits']})")
    result = {
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "rtl/ibex_pkg.sv", "rtl/ibex_icache.sv",
                "dv/verilator/icache_fetch_fault/tb.sv",
                "dv/verilator/icache_fetch_fault/run.py",
            )
        },
        "simulator": version,
        "target": TARGET,
        "instruction_word": "0x00000013",
        "reference": "accepted cache-to-IF error, NOT architectural trap",
        "cases": cases,
        "bus_checker_vs_if_reference": classify(cases, "bus_errors"),
        "if_checker_vs_if_reference": classify(cases, "if_errors"),
        "if_checker_reference_is_self": True,
        "pass": all(case["pass"] for case in cases.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Machine-readable observations: {args.output}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"fetch-error pilot failed: {exc}", file=sys.stderr)
        sys.exit(1)
