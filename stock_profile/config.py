"""Static, source-hash-checked SimpleSystem binding; no HDL tooling."""

import hashlib
import json
import os
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
CONFIG_BYTES = (HERE / "config.json").read_bytes().replace(b"\r\n", b"\n")
CONFIG = json.loads(CONFIG_BYTES)
CONFIG_SHA = hashlib.sha256(CONFIG_BYTES).hexdigest()
WORKLOADS = (
    "aha-mont64", "crc32", "depthconv", "edn", "huffbench", "matmult-int",
    "md5sum", "nettle-aes", "nettle-sha256", "nsichneu", "picojpeg", "qrduino",
    "sglib-combined", "slre", "statemate", "tarfind", "ud", "wikisort", "xgboost",
)


def checked(path, expected):
    data = path.read_bytes()
    oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if oid != expected:
        raise ValueError(f"pinned source hash mismatch: {path.name}")
    return data.decode()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"adapter anchor mismatch: {old!r}")
    return text.replace(old, new)


def make_adapter(source, output):
    system = source / "examples" / "simple_system"
    sv = checked(system / "rtl" / "ibex_simple_system.sv",
                 "11184df4e07f55d995432b5b48ac8de6ed5030d4")
    core = checked(system / "ibex_simple_system.core",
                   "ad773acd75f483004966b7f87a65cd338136b9c9")
    child = checked(system / "ibex_simple_system_core.core",
                    "86a827497126bbced77ddf9aa4ab1ad710432528")
    config_source = checked(source / "ibex_configs.yaml",
                            "865d2615fc262281c97c227b4218804fa194c5e6")
    official_text = config_source.split("\nsmall:\n", 1)[1].split("\n\n", 1)[0]
    official = {}
    for key, value in re.findall(r"^\s+(\w+)\s*:\s*(.+)$", official_text, re.M):
        official[key] = value.strip('"') if value.startswith('"') else int(value)
    expected = dict(CONFIG["parameters"], MHPMCounterNum=0)
    if official != expected:
        raise ValueError("complete official small configuration does not match")
    for key in expected:
        if not re.search(r"\." + key + r"\s*\(\s*" + key + r"\s*\)", sv):
            raise ValueError(f"missing downstream parameter: {key}")
    rel = pathlib.Path(os.path.relpath(system, output)).as_posix()
    child = once(child, 'name: "lowrisc:ibex:ibex_simple_system_core"',
                 'name: "owner:stock_profile:system_core:0.1"')
    child = once(child, "      - rtl/ibex_simple_system.sv",
                 "      - base_isa_shim.sv\n"
                 f"      - {rel}/rtl/ibex_simple_system.sv: {{is_include_file: true}}")
    for filename in ("ibex_simple_system.cc", "ibex_simple_system.h",
                     "lint/verilator_waiver.vlt", "lint/verible_waiver.vbw"):
        child = once(child, "      - " + filename, "      - " + rel + "/" + filename)
    core = once(core, 'name: "lowrisc:ibex:ibex_simple_system"',
                'name: "owner:stock_profile:system:0.1"')
    core = once(core, "- lowrisc:ibex:ibex_simple_system_core",
                "- owner:stock_profile:system_core:0.1")
    core = once(core, "(ibex_simple_system_main.cc)",
                f"({rel}/ibex_simple_system_main.cc)")
    core = once(core, "\nparameters:\n", """
parameters:
  BaseIsa:
    datatype: str
    paramtype: vlogdefine
    default: ibex_pkg::BaseIsaRV32I
    description: "External BaseIsa -> BASE_ISA shim; static only, NOT_VERIFIED"

""")
    core = once(core, "    parameters:\n", "    parameters:\n      - BaseIsa\n")
    # All nineteen known_fields are explicitly bound; no simplified ISA helper.
    for key, value in CONFIG["parameters"].items():
        core = once(core, f"      - {key}\n", f"      - {key}={value}\n")
    if output.exists() and any(output.iterdir()):
        raise ValueError("adapter output already exists; do not overwrite receipts")
    output.mkdir(parents=True, exist_ok=True)
    (output / "system.core").write_text(core, encoding="utf-8")
    (output / "system_core.core").write_text(child, encoding="utf-8")
    (output / "base_isa_shim.sv").write_text(
        '`ifdef BASE_ISA\n`undef BASE_ISA\n`endif\n'
        '`define BASE_ISA `BaseIsa\n`include "ibex_simple_system.sv"\n',
        encoding="utf-8",
    )
    (output / "stock_profile_config.h").write_text(
        f'#define STOCK_PROFILE_CONFIG_SHA "{CONFIG_SHA}"\n', encoding="utf-8"
    )
    return {
        "config_sha256": CONFIG_SHA, "parameters": CONFIG["parameters"],
        "static_source_checks": "PASSED", "hdl_binding": "NOT_VERIFIED",
        "differences": [
            "External core names/fileset and shim; unchanged original SimpleSystem/top/C++",
            "BaseIsa vlogdefine explicitly aliases BASE_ISA; pure RV32I",
            "All 19 official small fields fixed; MHPMCounterNum alone changes 0 -> 10",
        ],
        "extra_system_defaults": {
            "INSTR_CYCLE_DELAY": 0, "LockstepOffset": 1,
            "ICacheTweakInfection": 0, "SRAMInitFile": "",
        },
        "generated_files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()
        },
        "proposed_future_runtime_argv": [
            "<NOT_AUTHORIZED_SIMULATOR>", "--meminit=ram,<NOT_AUTHORIZED_ELF>",
            "--term-after-cycles=50000000", "+ibex_tracer_enable=0",
        ],
    }


def cpu_observation(*args, **kwargs):
    raise PermissionError("PREPARATION_ONLY / NO_CPU_RUN: a new user decision is required")
