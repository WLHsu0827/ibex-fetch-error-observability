# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Pure-stdlib contracts; none builds or runs an HDL model."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import signal
import struct
import sys
import tempfile
import unittest

from .check import parse, qualify
from .admission import CONTROLS, NAME, SCHEMA, control
from .drivers import DRIVERS, MAKE, validate_commands, validate_probe, validate_recipes
from .archive import privacy_review, verify_archive
from .dependencies import TARGET, canonical, compatible_wheel, graph, marker, satisfies, validate
from .history import parse_history, qualify_history
from .entrypoint import FLAGS, LAUNCHER_BODY, compare as compare_entrypoints, digest, read_receipt, validate as validate_entrypoint
from .inputs import boundaries, build_options, validate_elf
from .isa import BOOT, FIELDS, FIRST_ORDER, decode, execute, freeze, sext
from .process import expected_fatal, identity, require_success, run, write_json


def tiny_contract() -> tuple[bytes, dict[str, object]]:
    image = bytes.fromhex("130414001304140013041400")
    path, regs = [], [0] * 32
    for index in range(3):
        record, _ = execute(BOOT + 4 * index, 0x00140413, regs)
        record.update(order=index + FIRST_ORDER, region="program")
        path.append(record)
    return image, {"path": path, "coverage": {}}


def synthetic_stream(contract: dict[str, object]) -> str:
    def q(phase: str, cycle: int, reset: int) -> str:
        return phase + "\t" + str(cycle) + "\t" + "\t".join(
            str(reset if field == "reset" else 0) for field in CONTROLS
        )
    lines = [f"S\t{SCHEMA}\tcpp\t{NAME}", q("P", 0, 0), q("Q", 0, 0)]
    for index, expected in enumerate(contract["path"]):
        record = dict.fromkeys(FIELDS, 0)
        record.update({key: value for key, value in expected.items() if key in FIELDS})
        record.update(mode=3, ixl=1)
        cycle = index + 1
        lines.extend([q("P", cycle, 1), q("Q", cycle, 1)])
        lines.append("R\t" + str(cycle) + "\t" + "\t".join(str(record[key]) for key in FIELDS))
    return "\n".join(lines) + "\n"


class DecoderContracts(unittest.TestCase):
    def test_independent_known_branch_vectors(self) -> None:
        for insn, op, width, rs1, rs2, offset in (
            (0xDC65, "beq", 2, 8, 0, -8), (0xFC65, "bne", 2, 8, 0, -8),
            (0xC019, "beq", 2, 8, 0, 6), (0xE019, "bne", 2, 8, 0, 6),
            (0xFEB50CE3, "beq", 4, 10, 11, -8), (0xFEB51CE3, "bne", 4, 10, 11, -8),
            (0x00B50463, "beq", 4, 10, 11, 8), (0x00B51463, "bne", 4, 10, 11, 8),
        ):
            self.assertEqual(decode(insn),
                             dict(op=op, width=width, rs1=rs1, rs2=rs2, rd=0, imm=offset))

    def test_outcome_uses_operands_not_labels(self) -> None:
        regs = [0] * 32
        expected, cell = execute(BOOT, 0xDC65, regs)
        self.assertEqual((expected["next_pc"], cell), (BOOT - 8, "16:backward:1"))
        regs[8] = 1
        expected, cell = execute(BOOT, 0xDC65, regs)
        self.assertEqual((expected["next_pc"], cell), (BOOT + 2, "16:backward:0"))
        self.assertEqual(sext(0xFFF, 12), -1)

    def test_bad_encoding_and_bad_freeze(self) -> None:
        for insn in (0, 0xFFFFFFFF, 0x10000DC65):
            with self.assertRaises(ValueError):
                decode(insn)
        with self.assertRaises(ValueError):
            freeze(b"\x13\0\0\0" * 3 + b"\x6f\0\0\0", BOOT, BOOT + 12)

    def test_x0_writeback_is_zero(self) -> None:
        result, _ = execute(BOOT, 0x0000006F, [0] * 32)
        self.assertEqual((result["rd"], result["value"], result["next_pc"]), (0, 0, BOOT))


class DependencyContracts(unittest.TestCase):
    def test_canonical_names_and_versions(self) -> None:
        self.assertEqual(canonical("Typing__Extensions.foo"), "typing-extensions-foo")
        self.assertTrue(satisfies("3.12.3", ">=3.9,<4"))
        self.assertFalse(satisfies("3.12.3", "<3.10"))
        self.assertFalse(satisfies("3.12.3", "!=3.12.*"))
        with self.assertRaises(ValueError):
            satisfies("3.12.3", "unparsed")

    def test_target_markers_do_not_use_local_windows(self) -> None:
        self.assertTrue(marker('python_version < "3.13" and sys_platform == "linux"'))
        self.assertFalse(marker('python_version < "3.9"'))
        self.assertTrue(marker('extra == "plugin"', "plugin"))
        self.assertFalse(marker('extra == "test"'))
        with self.assertRaises(ValueError):
            marker("__import__('os').getcwd()")

    def test_platform_and_python_wheels(self) -> None:
        self.assertTrue(compatible_wheel("package-1.0-cp312-cp312-manylinux_2_17_x86_64.whl"))
        self.assertFalse(compatible_wheel("package-1.0-cp313-cp313-manylinux_2_39_x86_64.whl"))
        self.assertFalse(compatible_wheel("package-1.0-cp312-cp312-win_amd64.whl"))
        self.assertFalse(compatible_wheel("package-1.0-cp312-cp312-manylinux_2_40_x86_64.whl"))

    def test_complete_lock_and_missing_dependency(self) -> None:
        import json

        lock = json.loads(Path(__file__).with_name("DEPENDENCY_LOCK.json").read_text())
        validate(lock)
        altered = copy.deepcopy(lock)
        del altered["groups"]["runtime"]["packages"]["typing-extensions"]
        with self.assertRaises(ValueError):
            validate(altered)
        altered = copy.deepcopy(lock)
        altered["groups"]["runtime"]["packages"]["babel"]["version"] = "1.0"
        with self.assertRaises(ValueError):
            validate(altered)
        altered = copy.deepcopy(lock)
        altered["groups"]["runtime"]["packages"]["Pip"] = altered["groups"]["runtime"]["packages"].pop("pip")
        with self.assertRaises(ValueError):
            validate(altered)
        self.assertEqual(lock["target"], TARGET)
        graph(lock["groups"]["build"]["packages"], lock["source_build"]["requires"])


class HistoryContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.auth = json.loads(Path(__file__).with_name("MEMORY_ADMISSION_AUTHORIZATION.json").read_text())
        self.legacy = json.loads(Path(__file__).with_name("AUTHORIZATION.json").read_text())["identity"]
        self.source = "a" * 40
        self.closed = [
            self.record(item["id"], f"RVFI next-PC {item['mode']} p{item['preparation_attempt']} {epoch['identity']}",
                        item["conclusion"]) | {"head_sha": item["head_sha"]}
            for epoch in self.auth["closed_epochs"] for item in epoch["runs"]
        ]
        self.records = [
            *self.closed,
            self.record(3, f"RVFI next-PC prepare p1 {self.auth['identity']}", "failure"),
            self.record(4, f"RVFI next-PC prepare p2 {self.auth['identity']}", None),
        ]

    def record(self, run_id: int, title: str, conclusion: str | None) -> dict[str, object]:
        return dict(id=run_id, head_sha=self.source, display_title=title,
                    event="workflow_dispatch", run_attempt=1,
                    status="completed" if conclusion else "in_progress", conclusion=conclusion)

    def pages(self) -> str:
        return "\n".join(json.dumps({"total_count": len(self.records), "runs": page})
                         for page in (self.records[:2], self.records[2:5], self.records[5:]))

    def qualify(self, records: list[dict[str, object]]) -> list[dict[str, object]]:
        return qualify_history(records, self.auth, self.legacy, "4", self.source, "prepare", 2, "")

    def test_all_pages_both_epochs_current_exactly_once(self) -> None:
        records = parse_history(self.pages())
        self.assertEqual(len(records), len(self.closed) + 2)
        authorized = self.qualify(records)
        self.assertEqual([item["id"] for item in authorized], [3, 4])
        self.assertEqual(sum(item["id"] == 4 for item in authorized), 1)

    def test_empty_failed_truncated_malformed_or_missing_page_rejected(self) -> None:
        for text in (
            "", " ", '{"message":"API request failed"}', self.pages()[:-2],
            json.dumps({"total_count": 4, "runs": self.records[:2]}),
            self.pages() + "unparsed suffix",
            json.dumps({"total_count": 0, "runs": []}),
            json.dumps({"total_count": 1, "runs": [{"id": 4}]}),
        ):
            with self.assertRaises(ValueError):
                parse_history(text)

    def test_duplicate_current_and_rerun_rejected(self) -> None:
        duplicate = json.dumps({"total_count": len(self.records) + 1, "runs": self.records + [self.records[-1]]})
        with self.assertRaises(ValueError):
            parse_history(duplicate)
        for index in range(len(self.records)):
            records = copy.deepcopy(self.records)
            records[index]["run_attempt"] = 2
            with self.assertRaises(ValueError):
                self.qualify(records)

    def test_missing_current_counter_reset_and_pair_requires_same_source(self) -> None:
        for index, field, value in (
            (-1, "id", 5), (-1, "head_sha", "b" * 40),
            (-1, "display_title", f"RVFI next-PC prepare p1 {self.auth['identity']}"),
        ):
            records = copy.deepcopy(self.records)
            records[index][field] = value
            with self.assertRaises(ValueError):
                self.qualify(records)
        records = copy.deepcopy(self.records)
        records[-1]["conclusion"] = "success"
        records.append(self.record(5, f"RVFI next-PC pair p0 {self.auth['identity']}", None))
        result = qualify_history(records, self.auth, self.legacy, "5", self.source, "pair", 0, "4")
        self.assertEqual(len(result), 3)
        records[-2]["head_sha"] = "b" * 40
        with self.assertRaises(ValueError):
            qualify_history(records, self.auth, self.legacy, "5", self.source, "pair", 0, "4")

    def test_failed_guard_cannot_admit_tools_or_hdl_and_snapshot_follows_checks(self) -> None:
        from types import SimpleNamespace
        from unittest.mock import patch
        from .hosted import Hosted

        for case in ("head", "api_failure", "truncated_history", "rerun"):
            pipeline = Hosted.__new__(Hosted)
            pipeline.auth = self.auth
            pipeline.args = SimpleNamespace(authorization=self.auth["identity"], source_sha=self.source,
                                            mode="prepare", preparation_attempt=2, preparation_run="")
            calls = []
            records = copy.deepcopy(self.records)
            if case == "rerun":
                records[-1]["run_attempt"] = 2
            stdout = {
                "input-head": ("b" * 40 if case == "head" else self.source).encode(),
                "attempt-history": (self.pages()[:-2] if case == "truncated_history" else
                                    json.dumps({"total_count": len(records), "runs": records})).encode(),
            }

            def command(name: str, *args: object, **kwargs: object) -> None:
                calls.append(name)
                if name == "attempt-history" and case == "api_failure":
                    raise RuntimeError("typed API command exited 1")

            pipeline.command = command
            pipeline.last_stdout = lambda: stdout[calls[-1]]
            pipeline.capture_sources = lambda: calls.append("capture_sources")
            pipeline.setup = lambda: calls.append("forbidden_tools")
            environment = {
                "GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted",
                "GITHUB_REPOSITORY": self.auth["repository"], "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_RUN_ID": "4", "GITHUB_ACTOR": "WLHsu0827",
            }
            with patch.dict(os.environ, environment), patch("rvfi_nextpc.hosted.platform.system",
                                                            return_value="Linux"), patch(
                "rvfi_nextpc.hosted.verify", return_value={}
            ):
                with self.assertRaises((RuntimeError, ValueError)):
                    pipeline.execute()
            self.assertNotIn("forbidden_tools", calls)
            if case == "head":
                self.assertNotIn("capture_sources", calls)
            else:
                self.assertEqual(calls, ["input-head", "input-clean", "capture_sources", "attempt-history"])

    def test_closed_epochs_cannot_reopen_reset_or_change_identity(self) -> None:
        for field, value in (("id", 42), ("head_sha", "b" * 40), ("conclusion", "success")):
            records = copy.deepcopy(self.records)
            records[0][field] = value
            with self.assertRaises(ValueError):
                self.qualify(records)
        for epoch in self.auth["closed_epochs"]:
            records = self.records + [self.record(42, f"RVFI next-PC prepare p3 {epoch['identity']}", None)]
            with self.assertRaises(ValueError):
                self.qualify(records)


class EntrypointContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def receipt(self, run_id: int) -> tuple[dict[str, object], bytes]:
        python = f"/tmp/rvfi-nextpc-{run_id}/tools/bin/python"
        launcher = ("#!" + python + "\n").encode() + LAUNCHER_BODY
        active = {name: digest(name.encode()) for name in ("interpreter", "module", "lock", "runtime_code")}
        active.update(flags=FLAGS, distribution="fusesoc", version="2.4.3",
                      entry_point="fusesoc.main:main", python_version="3.12.3",
                      launcher_body=digest(LAUNCHER_BODY))
        return {"schema": 1, "active": active, "diagnostic": {
            "argv": [python, *FLAGS], "python_resolved": "/usr/bin/python3.12",
            "launcher_path": python.rsplit("/", 1)[0] + "/fusesoc",
            "launcher": digest(launcher), "shebang": "#!" + python,
        }}, launcher

    def store(self, run_id: int, changed: str | None = None) -> Path:
        root = self.root / str(run_id)
        root.mkdir()
        receipt, raw = self.receipt(run_id)
        if changed:
            receipt["active"][changed] = digest(b"changed")
        write_json(root / "entrypoint.json", receipt)
        (root / "fusesoc-launcher.txt").write_bytes(raw)
        return root

    def test_supported_active_module_allows_only_reviewed_unused_path_difference(self) -> None:
        first, second = self.store(100), self.store(200)
        self.assertNotEqual((first / "fusesoc-launcher.txt").read_bytes(), (second / "fusesoc-launcher.txt").read_bytes())
        self.assertEqual(compare_entrypoints(first, second)["flags"], FLAGS)

    def test_changed_interpreter_module_package_code_or_lock_fails(self) -> None:
        first = self.store(100)
        for index, field in enumerate(("interpreter", "module", "runtime_code", "lock")):
            with self.assertRaises(ValueError):
                compare_entrypoints(first, self.store(200 + index, field))

    def test_changed_version_invocation_and_malformed_identity_fails(self) -> None:
        for field, value in (
            ("version", "2.4.4"), ("flags", ["-B", "-m", "fusesoc.main"]),
            ("entry_point", "fusesoc.main:evil"), ("interpreter", {"sha256": "a" * 63, "bytes": 1}),
            ("launcher_body", digest(LAUNCHER_BODY + b"unrelated")),
        ):
            receipt, raw = self.receipt(100)
            receipt["active"][field] = value
            with self.assertRaises(ValueError):
                validate_entrypoint(receipt, raw)

    def test_realistic_unrelated_body_invalid_shebang_and_resolution_fails(self) -> None:
        receipt, raw = self.receipt(100)
        for mutated in (raw[:-1], raw + b"print('unrelated')\n", raw.replace(b"#!", b"# "),
                        raw.replace(b"/tools/bin/python", b"/tools/bin/other")):
            changed = copy.deepcopy(receipt)
            changed["diagnostic"]["launcher"] = digest(mutated)
            with self.assertRaises(ValueError):
                validate_entrypoint(changed, mutated)
        for path in ("/tmp/python", "/usr/bin/../bin/python3.12", "/usr/bin/python3.13"):
            changed = copy.deepcopy(receipt)
            changed["diagnostic"]["python_resolved"] = path
            with self.assertRaises(ValueError):
                validate_entrypoint(changed, raw)

    def test_missing_duplicate_truncated_and_unretained_raw_receipts_fail(self) -> None:
        first, second = self.store(100), self.store(200)
        path = second / "entrypoint.json"
        original = path.read_text()
        for text in ('{"schema":1,' + original[1:], original[:-3], original.replace('"module":', '"missing":')):
            path.write_text(text)
            with self.assertRaises(ValueError):
                compare_entrypoints(first, second)
        path.write_text(original)
        (second / "fusesoc-launcher.txt").unlink()
        with self.assertRaises(FileNotFoundError):
            compare_entrypoints(first, second)


class ProgramInputContracts(unittest.TestCase):
    def test_canonical_git_authorization_matches_retained_source_not_local_crlf(self) -> None:
        from .seal import git_identity, inputs

        name = "rvfi_nextpc/RECOVERY_AUTHORIZATION.json"
        snapshot = Path(__file__).with_name("evidence") / "run-37065211892/input" / name
        self.assertEqual(git_identity(name), identity(snapshot))
        self.assertEqual(inputs()[name], identity(snapshot))
        self.assertNotEqual(digest(snapshot.read_bytes().replace(b"\n", b"\r\n")), identity(snapshot))

    def test_actual_prior_generated_shell_quoting_rejected_and_repaired(self) -> None:
        root = Path(__file__).with_name("evidence") / "run-37065211892/off"
        config, vc = (root / "config.mk").read_text(), next(root.glob("*.vc")).read_text()
        with self.assertRaises(ValueError):
            build_options(config, vc)
        good = config.replace("-CFLAGS -std=c++17 -Wall -Wextra -Werror",
                              "-CFLAGS '-std=c++17 -Wall -Wextra -Werror'")
        self.assertEqual(build_options(good, vc)[-1], "-std=c++17 -Wall -Wextra -Werror")
        with self.assertRaises(ValueError):
            build_options(good, vc.replace("-DOBSERVER_TARGET=ibex_top", ""))

    def test_boundary_missing_duplicate_changed_and_boot_rejected(self) -> None:
        good = "80000080 T _start\n800000a0 T drain\n800000ac T terminal\n"
        self.assertEqual(boundaries(good)["terminal"], BOOT + 44)
        for bad in (good + good, good.replace("80000080", "80000082"),
                    good.replace("T drain", "D drain"), good.replace("T terminal", "T missing")):
            with self.assertRaises(ValueError):
                boundaries(bad)

    def test_elf_image_identity_class_boot_and_truncation(self) -> None:
        image = bytes.fromhex("130000006f000000")
        names = b"\0.text\0.shstrtab\0"
        offset = 52 + len(image) + len(names)
        header = struct.pack("<16sHHIIIIIHHHHHH", b"\x7fELF\x01\x01\x01" + b"\0" * 9,
                             2, 243, 1, BOOT, 0, offset, 1, 52, 0, 0, 40, 3, 2)
        data = header + image + names + b"\0" * 40 + struct.pack(
            "<IIIIIIIIII", 1, 1, 6, BOOT, 52, len(image), 0, 0, 2, 0
        ) + struct.pack("<IIIIIIIIII", 7, 3, 0, 0, 52 + len(image), len(names), 0, 0, 1, 0)
        validate_elf(data, image)
        for bad, binary in ((data, image[:-1]), (data[:-1], image),
                            (data.replace(b"\x7fELF", b"BAD!"), image),
                            (data[:24] + (BOOT + 2).to_bytes(4, "little") + data[28:], image)):
            with self.assertRaises(ValueError):
                validate_elf(bad, binary)


class StreamContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image, self.contract = tiny_contract()
        self.text = synthetic_stream(self.contract)
        self.cpp, self.sv = self.root / "cpp.tsv", self.root / "sv.tsv"
        self.cpp.write_text(self.text, encoding="ascii")
        self.sv.write_text(self.text, encoding="ascii")

    def test_qualified_metadata(self) -> None:
        result = qualify(self.cpp, self.sv, self.image, self.contract)
        self.assertEqual((result["retirements"], result["strict_next_pc"]), (3, "PASS"))

    def test_metadata_failure_is_not_execution_failure(self) -> None:
        parts = self.text.splitlines()
        index = next(i for i, line in enumerate(parts) if line.startswith("R\t"))
        row = parts[index].split("\t")
        row[2 + FIELDS.index("next_pc")] = str(BOOT - 8)
        parts[index] = "\t".join(row)
        changed = "\n".join(parts) + "\n"
        self.cpp.write_text(changed, encoding="ascii")
        self.sv.write_text(changed, encoding="ascii")
        result = qualify(self.cpp, self.sv, self.image, self.contract)
        self.assertEqual((result["isa_execution"], result["strict_next_pc"]), ("PASS", "FAIL"))

    def test_sampler_disagreement(self) -> None:
        self.sv.write_text(self.text.replace(str(BOOT + 4), str(BOOT + 6)), encoding="ascii")
        with self.assertRaises(ValueError):
            qualify(self.cpp, self.sv, self.image, self.contract)

    def test_missing_duplicate_reordered_malformed_and_controls(self) -> None:
        lines = self.text.splitlines()
        first_r = next(i for i, line in enumerate(lines) if line.startswith("R\t"))
        variants = [
            "\n".join(lines[2:]) + "\n",
            "\n".join(lines[:first_r + 1] + [lines[first_r]] + lines[first_r + 1:]) + "\n",
            "\n".join(lines[:first_r] + lines[first_r + 3:] + lines[first_r:first_r + 3]) + "\n",
            self.text + "unrecognized\n",
            self.text.replace("Q\t2\t1\t0", "Q\t2\t1\t1"),
            self.text + "P\t4\t0" + "\t0" * (len(CONTROLS) - 1) + "\nQ\t4\t0"
            + "\t0" * (len(CONTROLS) - 1) + "\n",
            self.text.replace("R\t1\t1\t", "R\t1\t2\t"),
            self.text.rstrip("\n"),
        ]
        for variant in variants:
            self.cpp.write_text(variant, encoding="ascii")
            with self.assertRaises(ValueError):
                parse(self.cpp)

    def test_image_path_operands_flags_and_premature_exit(self) -> None:
        for field in ("pc", "insn", "a", "value", "trap", "halt", "intr", "debug_mode"):
            parts = self.text.splitlines()
            index = next(i for i, line in enumerate(parts) if line.startswith("R\t"))
            row = parts[index].split("\t")
            position = 2 + FIELDS.index(field)
            row[position] = str(int(row[position]) + 1)
            parts[index] = "\t".join(row)
            changed = "\n".join(parts) + "\n"
            self.cpp.write_text(changed, encoding="ascii")
            self.sv.write_text(changed, encoding="ascii")
            with self.assertRaises(ValueError):
                qualify(self.cpp, self.sv, self.image, self.contract)
        short = "\n".join(self.text.splitlines()[:-3]) + "\n"
        self.cpp.write_text(short, encoding="ascii")
        self.sv.write_text(short, encoding="ascii")
        with self.assertRaises(ValueError):
            qualify(self.cpp, self.sv, self.image, self.contract)
        mutated = copy.deepcopy(self.contract)
        mutated["path"][0]["next_pc"] += 2
        self.cpp.write_text(self.text, encoding="ascii")
        self.sv.write_text(self.text, encoding="ascii")
        with self.assertRaises(ValueError):
            qualify(self.cpp, self.sv, self.image, mutated)

    def test_all_read_mask_information_retained_not_memory_metadata_pass(self) -> None:
        for mask in range(16):
            lines = self.text.splitlines()
            for index, line in enumerate(lines):
                if line.startswith("R\t"):
                    parts = line.split("\t")
                    parts[2 + FIELDS.index("rmask")] = str(mask)
                    lines[index] = "\t".join(parts)
            text = "\n".join(lines) + "\n"
            self.cpp.write_text(text, encoding="ascii")
            self.sv.write_text(text, encoding="ascii")
            result = qualify(self.cpp, self.sv, self.image, self.contract)
            self.assertEqual(result["read_mask_histogram"], {str(mask): 3})
            self.assertEqual(result["memory_metadata"], "NOT_VERIFIED")

    def test_old_schema_never_admitted_or_requalified(self) -> None:
        self.cpp.write_text(self.text.partition("\n")[2], encoding="ascii")
        with self.assertRaisesRegex(ValueError, "legacy streams"):
            parse(self.cpp)

    def test_pre_post_bus_fields_missing_out_of_domain_and_all_safety_negatives(self) -> None:
        for phase in ("P", "Q"):
            for name in CONTROLS:
                if name in ("reset", "data_be", "data_addr", "data_wdata"):
                    continue
                lines = self.text.splitlines()
                index = next(i for i, line in enumerate(lines) if line.startswith(phase + "\t1\t"))
                parts = lines[index].split("\t")
                parts[2 + CONTROLS.index(name)] = "1"
                lines[index] = "\t".join(parts)
                self.cpp.write_text("\n".join(lines) + "\n", encoding="ascii")
                with self.assertRaisesRegex(ValueError, "observed bus"):
                    parse(self.cpp)
        variants = [
            self.text.replace("P\t1\t", "P\t2\t"),
            self.text.replace("S\t2\t", "S\t3\t"),
            self.text.replace("P\t1\t", "X\t1\t"),
            "\n".join(line for line in self.text.splitlines() if not line.startswith("P\t")) + "\n",
        ]
        for text in variants:
            self.cpp.write_text(text, encoding="ascii")
            with self.assertRaises(ValueError):
                parse(self.cpp)
        for field, value in (("rmask", 16), ("wmask", 1), ("insn", 0x00042403)):
            lines = self.text.splitlines()
            index = next(i for i, line in enumerate(lines) if line.startswith("R\t"))
            parts = lines[index].split("\t")
            parts[2 + FIELDS.index(field)] = str(value)
            lines[index] = "\t".join(parts)
            self.cpp.write_text("\n".join(lines) + "\n", encoding="ascii")
            with self.assertRaises(ValueError):
                parse(self.cpp)
        for field, value in (("data_be", 16), ("data_req", 2), ("data_addr", 0x100000000)):
            values = [0] * len(CONTROLS)
            values[CONTROLS.index(field)] = value
            with self.assertRaises(ValueError):
                control(values)


class DriverContracts(unittest.TestCase):
    def test_actual_link_compile_archive_commands_and_changed_inputs(self) -> None:
        good = "/usr/bin/g++-13 -c -o main.o main.cpp\n/usr/bin/ar -rc model.a model.o\n/usr/bin/g++-13 main.o model.a -o Vfixture\n"
        self.assertEqual(validate_commands(good, "Vfixture")["compile_commands"], 1)
        for text in (good.replace("/usr/bin/g++-13", "g++"), good + good,
                     good.replace("/usr/bin/ar", "ar"), good.replace(" -c ", " ")):
            with self.assertRaises(ValueError):
                validate_commands(text, "Vfixture")
        from .hosted import Hosted

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "installed-verilated.mk"
            path.write_bytes(b"qualified original bytes")
            hosted = Hosted.__new__(Hosted)
            hosted.driver_files = {str(path): identity(path)}
            hosted.verify_drivers()
            path.write_bytes(b"changed link/include/helper bytes")
            with self.assertRaises(RuntimeError):
                hosted.verify_drivers()

    def test_exact_expanded_link_alias_and_single_worker(self) -> None:
        good = "\n".join(f"{key}={value}" for key, value in DRIVERS.items()) + "\nMAKEFLAGS= -j1 -- NUM_JOBS=1\n"
        self.assertEqual(validate_probe(good)["LINK"], "/usr/bin/g++-13")
        for bad in (good.replace("LINK=/usr/bin/g++-13", "LINK=g++"),
                    good.replace("-j1", "-j2"), good.replace("-j1", "-j"),
                    good.replace("LINK=", "MISSING="), good + "LINK=/usr/bin/g++-13\n",
                    good[:-4]):
            with self.assertRaises(ValueError):
                validate_probe(bad)
        self.assertIn("LINK=/usr/bin/g++-13", MAKE)

    def test_installed_and_generated_recipe_mutations_fail(self) -> None:
        generated = "include $(VERILATOR_ROOT)/include/verilated.mk\n$(LINK) objects\n"
        included = ("CXX = g++\nLINK = g++\nAR = ar\nPYTHON3 = python3\nPERL = perl\n"
                    "$(CXX) -c\n$(AR) -rc\n$(PYTHON3) $(VERILATOR_ROOT)/bin/verilator_includer\n")
        outer = "$(MAKE) $(MAKE_OPTIONS) -f $<\n$(VERILATOR)\n"
        validate_recipes(generated, included, outer)
        for a, b, c in ((generated.replace("$(LINK)", "g++"), included, outer),
                        (generated, included.replace("LINK = g++\n", ""), outer),
                        (generated, included, outer.replace("$(MAKE)", "make -j4"))):
            with self.assertRaises(ValueError):
                validate_recipes(a, b, c)


class ProcessContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_flushed_bytes_and_exclusive_receipts(self) -> None:
        status = run([sys.executable, "-c", "import os; os.write(1,b'last\\xff'); os.write(2,b'end')"],
                     self.root, self.root, "bytes", 5)
        require_success(status)
        self.assertEqual((self.root / "bytes.stdout.log").read_bytes(), b"last\xff")
        self.assertEqual(status["stdout"], identity(self.root / "bytes.stdout.log"))
        with self.assertRaises(FileExistsError):
            write_json(self.root / "bytes.status.json", {})

    def test_marker_then_hang_remains_timeout(self) -> None:
        status = run([sys.executable, "-c",
                      "import os,time; os.write(1,b'NEXTPC_RESET_AFTER_START\\n'); time.sleep(10)"],
                     self.root, self.root, "hang", 0.2)
        text = (self.root / "hang.stdout.log").read_bytes()
        self.assertEqual(status["kind"], "timed_out")
        self.assertIn(b"NEXTPC_RESET_AFTER_START", text)
        self.assertFalse(expected_fatal(status, text, b"NEXTPC_RESET_AFTER_START"))

    @unittest.skipUnless(os.name == "posix", "POSIX SIGABRT contract runs in hosted preparation")
    def test_prompt_signal_and_marker(self) -> None:
        status = run([sys.executable, "-c",
                      "import os; os.write(1,b'NEXTPC_RESET_AFTER_START\\n'); os.abort()"],
                     self.root, self.root, "fatal", 5)
        self.assertEqual(status["code"], signal.SIGABRT)
        self.assertTrue(expected_fatal(status, (self.root / "fatal.stdout.log").read_bytes(),
                                       b"NEXTPC_RESET_AFTER_START"))

    def test_missing_tool_and_bad_exit(self) -> None:
        status = run(["nonexistent-nextpc-executable"], self.root, self.root, "missing", 1)
        self.assertEqual(status["kind"], "spawn_error")
        with self.assertRaises(RuntimeError):
            require_success(status)
        status = run([sys.executable, "-c", "raise SystemExit(4)"], self.root, self.root, "exit", 5)
        self.assertEqual((status["kind"], status["code"]), ("exited", 4))


class ArchiveContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        write_json(self.root / "summary.json", {
            "source_sha": "a" * 40, "result": "STOP", "error": "synthetic gate failure",
        })
        write_json(self.root / "dispatch-input.json", {"source_sha": "a" * 40})
        write_json(self.root / "RAW_MANIFEST.json", {
            "schema": 1, "source_sha": "a" * 40, "run_id": "synthetic",
            "files": {path.name: identity(path) for path in self.root.iterdir()},
        })

    def test_stop_archive_is_not_scientific_pass(self) -> None:
        result = verify_archive(self.root)
        self.assertEqual((result["archive_integrity"], result["scientific_result"]),
                         ("PASS", "NOT_QUALIFIED"))

    def test_declared_pre_hdl_source_gap_is_incomplete_never_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_sha = "b" * 40
            write_json(root / "summary.json", {
                "source_sha": source_sha, "result": "STOP", "error": "pre-HDL tool failure",
                "real_compilations": [],
            })
            write_json(root / "dispatch-input.json", {"source_sha": source_sha})
            files = {path.name: identity(path) for path in root.iterdir()}
            missing = "input/.github/workflows/rvfi-nextpc.yml"
            files[missing] = {"bytes": 1, "sha256": "a" * 64}
            write_json(root / "RAW_MANIFEST.json", {
                "schema": 1, "source_sha": source_sha, "run_id": "synthetic", "files": files,
            })
            with self.assertRaises(ValueError):
                verify_archive(root)
            receipt = {"missing_files": [missing], "source_sha": source_sha, "run_id": "synthetic",
                       "manifest": identity(root / "RAW_MANIFEST.json")}
            self.assertEqual(verify_archive(root, receipt)["archive_integrity"], "INCOMPLETE")
            receipt["missing_files"] = ["off/cpp.tsv"]
            with self.assertRaises(ValueError):
                verify_archive(root, receipt)

    def test_changed_missing_or_extra_bytes_fail(self) -> None:
        (self.root / "extra.log").write_bytes(b"extra")
        with self.assertRaises(ValueError):
            verify_archive(self.root)
        (self.root / "extra.log").unlink()
        (self.root / "summary.json").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify_archive(self.root)
        (self.root / "summary.json").unlink()
        with self.assertRaises(ValueError):
            verify_archive(self.root)

    def test_source_config_and_elf_byte_mutations_fail_closed(self) -> None:
        for name in ("source.sv", "config.json", "fresh.elf"):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for source in self.root.iterdir():
                    if source.name != "RAW_MANIFEST.json":
                        (root / source.name).write_bytes(source.read_bytes())
                (root / name).write_bytes(b"public synthetic identity")
                write_json(root / "RAW_MANIFEST.json", {
                    "schema": 1, "source_sha": "a" * 40, "run_id": "synthetic",
                    "files": {p.name: identity(p) for p in root.iterdir()},
                })
                verify_archive(root)
                (root / name).write_bytes(b"changed")
                with self.assertRaises(ValueError):
                    verify_archive(root)

    def test_scanner_literals_are_not_source_exemptions(self) -> None:
        source = Path(__file__).with_name("archive.py").read_bytes()
        privacy_review(source)
        for payload in (
            ("github_" + "pat_" + "A" * 40).encode(),
            ("gh" + "p_" + "B" * 36).encode(),
            ("C:" + chr(92) + "Users" + chr(92) + "SyntheticOwner" + chr(92) + "private").encode(),
            ("/Users" + "/SyntheticOwner/private").encode(),
            ("/home" + "/SyntheticOwner/private").encode(),
            ("-----BEGIN " + "OPENSSH PRIVATE KEY-----").encode(),
        ):
            with self.assertRaises(ValueError):
                privacy_review(payload)
            with self.assertRaises(ValueError):
                privacy_review(source + payload)


if __name__ == "__main__":
    unittest.main()
