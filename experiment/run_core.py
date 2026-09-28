#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

"""Check bus, cache-to-IF, retirement and trap observations in Simple System."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BUILD = ROOT / "build" / "fetch_error_pilot"
TARGET = "0x00100100"
NOP = "0x00000013"
EXPECTED = {
    "hit_control": {
        "bus_errors": 0, "if_error_after_bus": 0, "target_traps": 0,
        "handler_retired": 0, "target_cached": 1, "target_hit_seen": 1,
        "cache_hits_min": 1, "if_good_after_bus_min": 1, "retired_after_bus_min": 1,
    },
    "speculative_hit": {
        "bus_errors": 1, "if_error_after_bus": 0, "target_traps": 0,
        "handler_retired": 0, "target_cached": 1, "target_hit_seen": 1,
        "cache_hits_min": 1, "if_good_after_bus_min": 1, "retired_after_bus_min": 1,
    },
    "demand_miss": {
        "bus_errors": 1, "if_good_after_bus": 0, "target_traps": 1,
        "retired_after_bus": 0, "cache_hits": 0,
        "if_error_after_bus_min": 1, "handler_retired_min": 1,
        "mcause": 1, "mepc": TARGET, "mtval": TARGET,
    },
}
EXPECTED_PATH = {
    "hit_control": {
        "lookup_line": TARGET, "lookup_valid": 1, "tag_hit": 1,
        "fill_hit_nonzero": True, "fill_data_hit_nonzero": True,
        "fill_data_rvd": 0, "fetch_valid": 1, "fetch_ready": 1,
        "fetch_addr": TARGET, "fetch_err": 0,
    },
    "speculative_hit": {
        "lookup_line": TARGET, "lookup_valid": 1, "tag_hit": 1,
        "fill_hit_nonzero": True, "fill_data_hit_nonzero": True,
        "fill_data_rvd": 0, "fetch_valid": 1, "fetch_ready": 1,
        "fetch_addr": TARGET, "fetch_err": 0,
    },
    "demand_miss": {
        "tag_hit": 0, "fill_hit_nonzero": False,
        "fill_data_hit_nonzero": False, "fill_data_rvd_nonzero": True,
        "fetch_valid": 1, "fetch_ready": 1, "fetch_addr": TARGET, "fetch_err": 1,
    },
}


def classify(cases, field):
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for case in cases.values():
        actual = case["actual"]
        predicted = actual[field] > 0
        reference = actual["target_traps"] > 0
        counts[("t" if predicted == reference else "f") +
               ("p" if predicted else "n")] += 1
    return counts


def run_case(binary, scenario):
    case_dir = BUILD / f"core_{scenario}"
    case_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(binary), f"--meminit=ram,{HERE / 'core_program.vmem'}",
        "--term-after-cycles=2000", f"+pilot_case={scenario}",
    ]
    completed = subprocess.run(
        command, cwd=case_dir, capture_output=True, text=True,
        check=False, timeout=60
    )
    if completed.returncode:
        raise RuntimeError(
            f"{scenario}: simulator exited {completed.returncode}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    events = []
    results = []
    for line in completed.stdout.splitlines():
        if line.startswith("PILOT_CORE_EVENT:"):
            events.append(json.loads(line.removeprefix("PILOT_CORE_EVENT:")))
        if line.startswith("PILOT_CORE_RESULT:"):
            results.append(json.loads(line.removeprefix("PILOT_CORE_RESULT:")))
    if len(results) != 1 or results[0]["scenario"] != scenario:
        raise RuntimeError(f"{scenario}: expected one matching result\n{completed.stdout}")
    return events, results[0]


def single_event(events, kind, deviations):
    matching = [event for event in events if event["kind"] == kind]
    if len(matching) != 1:
        deviations[kind] = {"expected_count": 1, "events": matching}
        return None
    return matching[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path,
                        default=BUILD / "system_pilot" / "Vibex_simple_system")
    parser.add_argument("--output", type=Path, default=HERE / "core_results.json")
    args = parser.parse_args()
    if not args.binary.is_file():
        raise RuntimeError(f"Missing Simple System binary: {args.binary}")
    binary = args.binary.resolve()
    staged = BUILD / "system_pilot" / "src" / (
        "lowrisc_ibex_ibex_simple_system_core_0"
    ) / "rtl" / "ibex_simple_system.sv"
    source = ROOT / "examples" / "simple_system" / "rtl" / "ibex_simple_system.sv"
    if binary == (BUILD / "system_pilot" / "Vibex_simple_system").resolve():
        if (not staged.is_file() or staged.read_bytes() != source.read_bytes() or
                binary.stat().st_mtime_ns < staged.stat().st_mtime_ns):
            raise RuntimeError("Simple System source changed or binary is stale; rebuild first")
    cases = {}
    for scenario, expected in EXPECTED.items():
        events, actual = run_case(binary, scenario)
        deviations = {}
        for field, value in expected.items():
            minimum = field.endswith("_min")
            observed = actual[field[:-4] if minimum else field]
            if (observed < value if minimum else observed != value):
                deviations[field] = {"expected": value, "actual": observed}
        request = single_event(events, "request", deviations)
        response = single_event(events, "bus_response", deviations)
        path = single_event(events, "cache_at_response", deviations)
        if request is not None:
            for field, value in {
                "addr": TARGET,
                "branch": 1,
                "cache_enabled": 1,
                "target_cached": 0 if scenario == "demand_miss" else 1,
                "target_hit_seen": 0 if scenario == "demand_miss" else 1,
            }.items():
                if request[field] != value:
                    deviations[f"request.{field}"] = {
                        "expected": value, "actual": request[field],
                    }
            if scenario != "demand_miss" and request["target_retired"] < 4:
                deviations["request.target_retired"] = {
                    "minimum": 4, "actual": request["target_retired"],
                }
        if request is not None and response is not None:
            if response["cycle"] != request["cycle"] + 1 or (
                response["err"] != (scenario != "hit_control")
            ):
                deviations["bus_sequence"] = {"request": request, "response": response}
        if response is not None and path is not None:
            if path["cycle"] != response["cycle"]:
                deviations["cache_response_cycle"] = {
                    "response": response["cycle"], "cache": path["cycle"],
                }
            for field, value in EXPECTED_PATH[scenario].items():
                observed = bool(path[field[:-8]]) if field.endswith("_nonzero") else path[field]
                if observed != value:
                    deviations[f"cache_at_response.{field}"] = {
                        "expected": value, "actual": observed,
                    }
        handoffs = [event for event in events if event["kind"] == "if_handoff"]
        if response is not None and not any(
            event["cycle"] == response["cycle"] and
            event["addr"] == TARGET and
            event["err"] == (scenario == "demand_miss") and
            (scenario == "demand_miss" or event["rdata"] == NOP)
            for event in handoffs
        ):
            deviations["if_handoff_at_response"] = {
                "expected_cycle": response["cycle"], "handoffs": handoffs[:2],
            }
        traps = [event for event in events if event["kind"] == "rvfi_trap"]
        retires = [event for event in events if event["kind"] == "rvfi_retire"]
        if len(traps) != (scenario == "demand_miss") or (
            traps and response is not None and traps[0]["cycle"] <= response["cycle"]
        ):
            deviations["trap_events"] = {"events": traps}
        if scenario == "demand_miss":
            if retires:
                deviations["unexpected_retire_events"] = {"events": retires}
        elif len(retires) != 1 or retires[0]["pc"] != TARGET or (
            retires[0]["insn"] != NOP
        ) or (response is not None and retires[0]["cycle"] <= response["cycle"]):
            deviations["retire_events"] = {"events": retires}
        cases[scenario] = {
            "fault_class": ("none" if scenario == "hit_control" else
                            "speculative_hit_bus_error" if scenario == "speculative_hit" else
                            "demanded_miss_bus_error"),
            "fault_injection": {
                "location": "instruction bus response instr_err_i",
                "address": TARGET,
                "enabled": scenario != "hit_control",
                "one_shot": True,
                "grant": "immediate",
                "response_latency_cycles": 1,
                "arming": ("first target request" if scenario == "demand_miss" else
                           "observed target cache hit and four retired target instructions"),
            },
            "expected": expected,
            "expected_cache_at_response": EXPECTED_PATH[scenario],
            "actual": actual,
            "events": events,
            "deviations": deviations,
            "pass": not deviations,
        }
        print(f"{scenario}: {'PASS' if not deviations else 'FAIL'} "
              f"(bus={actual['bus_errors']}, IF={actual['if_error_after_bus']}, "
              f"trap={actual['target_traps']}, retired={actual['retired_after_bus']})")

    control = cases["hit_control"]["events"]
    fault = cases["speculative_hit"]["events"]
    matching_kinds = ("request", "cache_at_response")
    control_path = [
        {k: v for k, v in e.items() if k != "fetch_err"}
        for e in control if e["kind"] in matching_kinds
    ]
    fault_path = [
        {k: v for k, v in e.items() if k != "fetch_err"}
        for e in fault if e["kind"] in matching_kinds
    ]
    warm_control_aligned = control_path == fault_path
    if not warm_control_aligned:
        cases["speculative_hit"]["deviations"]["warm_control_alignment"] = {
            "control": control_path, "fault": fault_path,
        }
        cases["speculative_hit"]["pass"] = False
    data = {
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "examples/simple_system/rtl/ibex_simple_system.sv",
                "examples/simple_system/ibex_simple_system.core",
                "rtl/ibex_icache.sv",
                "rtl/ibex_if_stage.sv",
                "dv/verilator/icache_fetch_fault/core_program.vmem",
                "dv/verilator/icache_fetch_fault/run_core.py",
            )
        },
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "program": {
            "boot": "0x00100080", "handler": "0x00100000",
            "target": TARGET, "instruction": NOP,
        },
        "warm_control_aligned": warm_control_aligned,
        "reference": "RVFI trap at target PC and entry into handler",
        "cases": cases,
        "bus_checker_vs_trap": classify(cases, "bus_errors"),
        "if_checker_vs_trap": classify(cases, "if_error_after_bus"),
        "pass": all(case["pass"] for case in cases.values()),
    }
    args.output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Machine-readable core observations: {args.output}")
    return 0 if data["pass"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"core pilot failed: {exc}", file=sys.stderr)
        sys.exit(1)
