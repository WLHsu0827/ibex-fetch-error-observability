"""Produce/recheck a references-and-hashes-only public source/input/license seal."""

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import HERE, WORKLOADS, CONFIG_SHA, make_adapter
from sources import acquire, digest, tree_id

IBEX_FILES = (
    "ibex_configs.yaml", "util/ibex_config.py", "util/tool_requirements.py",
    "python-requirements.txt", "LICENSE", "NOTICE",
    "vendor/eembc_coremark.lock.hjson",
    "vendor/patches/eembc_coremark/0001-no-minimum-run-time.patch",
)
PREFIXES = (
    "rtl/", "examples/simple_system/", "examples/sw/simple_system/common/",
    "examples/sw/benchmarks/coremark/", "vendor/eembc_coremark/",
    "shared/rtl/sim/simulator_ctrl.sv",
    "vendor/lowrisc_ip/dv/verilator/simutil_verilator/cpp/",
)


def annotate(record, root):
    result = dict(record)
    path = root.joinpath(*record["path"].split("/"))
    if record["mode"] != "120000" and path.suffix in (".c", ".h", ".S", ".sv", ".md"):
        text = path.read_text(encoding="utf-8", errors="strict")
        result["spdx"] = sorted(set(s.strip() for s in re.findall(
            r"SPDX-License-Identifier:\s*([^\r\n*]+)", text)))
        result["copyright_notices"] = sorted(set(s.strip(" /*\t") for s in re.findall(
            r"^[^\r\n]*[Cc]opyright[^\r\n]*", text, re.M)))
    return result


def manifest(inventory, sources):
    result = {"scope": "PREPARATION_ONLY", "classification": "EXPLORATORY",
              "config_sha256": CONFIG_SHA, "distribution": "REFS_HASHES_NOT_SOURCE_BYTES",
              "sources": {}, "workloads": {}}
    for name, source in inventory.items():
        selected = source["files"] if name == "embench" else [
            r for r in source["files"]
            if r["path"] in IBEX_FILES or r["path"].startswith(PREFIXES)]
        result["sources"][name] = {
            k: source[k] for k in ("repository", "commit", "url", "root_tree", "archive_sha256")
        }
        result["sources"][name]["files"] = [
            annotate(r, sources / name) for r in selected
        ]
    embench = sources / "embench" / "src"
    actual = sorted(p.name for p in embench.iterdir() if p.is_dir())
    if actual != sorted(WORKLOADS):
        raise ValueError("official full 19-workload list changed")
    for workload in WORKLOADS:
        verifiers = []
        for path in sorted((embench / workload).rglob("*.c")):
            text = path.read_bytes().decode("utf-8")
            match = re.search(r"\bverify_benchmark\s*\(", text)
            if match:
                start = text.find("{", match.end())
                end, depth = start + 1, 1
                while depth:
                    depth += (text[end] == "{") - (text[end] == "}")
                    end += 1
                verifiers.append({
                    "path": path.relative_to(sources / "embench").as_posix(),
                    "function_sha256": digest(text[match.start():end].encode()),
                    "function_start_line": text[:match.start()].count("\n") + 1,
                    "function_end_line": text[:end].count("\n") + 1,
                    "execution": "NOT_VERIFIED",
                })
        if len(verifiers) != 1:
            raise ValueError(f"expected exactly one official verifier for {workload}")
        result["workloads"][workload] = {
            "classification": "EXPLORATORY", "gsf": 1, "warmup_heat": 1,
            "algorithm_input_scope": f"ALL src/{workload}/ bytes in source inventory",
            "verifier": verifiers[0], "runtime_selfcheck": "NOT_VERIFIED",
            "redistribution": "NOT_PERFORMED; preserve individual notices; no Apache relabel",
        }
    result["workloads"]["md5sum"]["limitation"] = "official source calls this not a proper check"
    result["workloads"]["xgboost"]["limitation"] = (
        "official verifier uses (LOCAL_SCALE_FACTOR, GLOBAL_SCALE_FACTOR / 12); "
        "at gsf=1 the threshold is zero; preserve, do not strengthen or claim independent correctness"
    )
    for prefix, expected in (
        ("vendor/eembc_coremark/", "8e634d5b42c34a6e1e049e75a7bc070c50d2326b"),
        ("examples/sw/benchmarks/coremark/", "e86619e4e7bbdd084ff0ffa12cc65e7b69798eec"),
    ):
        entries = [(r["path"][len(prefix):], r["mode"], r["git_blob"])
                   for r in inventory["ibex"]["files"] if r["path"].startswith(prefix)]
        if tree_id(entries) != expected:
            raise ValueError("vendored CoreMark/port subtree mismatch")
    result["coremark"] = {
        "vendor_tree": "8e634d5b42c34a6e1e049e75a7bc070c50d2326b",
        "port_tree": "e86619e4e7bbdd084ff0ffa12cc65e7b69798eec",
        "pristine_upstream": False, "mode": "selfcheck_only", "known_id": 3,
        "seedcrc": "e9f5", "crclist": "e714", "crcmatrix": "1fd7", "crcstate": "8e3a",
        "crcfinal_expected": None, "official_score_compliance": "NOT_CLAIMED",
        "clock_500000": "port conversion constant, not measured silicon frequency",
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=pathlib.Path, default=HERE / "_sources")
    parser.add_argument("--receipts", type=pathlib.Path, default=HERE / "_receipts")
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    inventory = acquire(args.sources)
    sealed = manifest(inventory, args.sources)
    destination = HERE / "source_manifest.json"
    if args.write_manifest:
        destination.write_text(json.dumps(sealed, indent=2) + "\n", encoding="utf-8", newline="\n")
    elif json.loads(destination.read_text()) != sealed:
        raise ValueError("source/input/license/config seal mismatch; STOP")
    args.receipts.mkdir(parents=True, exist_ok=True)
    binding = make_adapter(args.sources / "ibex", args.receipts / "adapter")
    receipt = {
        "scope": "PREPARATION_ONLY", "source_bytes_and_hashes": "SEALED_STATIC_ONLY",
        "manifest_sha256": digest(destination.read_bytes()), "binding": binding,
        "cpu_implementation_changes": "NONE",
        "cpu_program_compile_run": "NOT_AUTHORIZED",
    }
    (args.receipts / "source-status.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"manifest_sha256": receipt["manifest_sha256"],
                      "static_source_checks": binding["static_source_checks"],
                      "hdl_binding": binding["hdl_binding"]}))


if __name__ == "__main__":
    main()
