# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Pure-stdlib contracts; none builds or runs an HDL model."""

from __future__ import annotations

import copy
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest

from .check import parse, qualify
from .archive import privacy_review, verify_archive
from .isa import BOOT, FIELDS, decode, execute, freeze, sext
from .process import expected_fatal, identity, require_success, run, write_json


def tiny_contract() -> tuple[bytes, dict[str, object]]:
    image = bytes.fromhex("130414001304140013041400")
    path, regs = [], [0] * 32
    for index in range(3):
        record, _ = execute(BOOT + 4 * index, 0x00140413, regs)
        record.update(order=index, region="program")
        path.append(record)
    return image, {"path": path, "coverage": {}}


def synthetic_stream(contract: dict[str, object]) -> str:
    lines = ["Q\t0\t1\t0\t0\t0\t0\t0\t0\t0", "Q\t1\t0\t0\t0\t0\t0\t0\t0\t0"]
    for index, expected in enumerate(contract["path"]):
        record = dict.fromkeys(FIELDS, 0)
        record.update({key: value for key, value in expected.items() if key in FIELDS})
        record.update(mode=3, ixl=1)
        cycle = index + 2
        lines.append(f"Q\t{cycle}\t1\t0\t0\t0\t0\t0\t0\t0")
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
        row = parts[3].split("\t")
        row[2 + FIELDS.index("next_pc")] = str(BOOT - 8)
        parts[3] = "\t".join(row)
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
        variants = [
            "\n".join(lines[2:]) + "\n",
            "\n".join(lines[:4] + [lines[3]] + lines[4:]) + "\n",
            "\n".join(lines[:4] + lines[6:] + lines[4:6]) + "\n",
            self.text + "unrecognized\n",
            self.text.replace("Q\t2\t1\t0", "Q\t2\t1\t1"),
            self.text + "Q\t5\t0\t0\t0\t0\t0\t0\t0\t0\n",
            self.text.replace("R\t2\t0\t", "R\t2\t1\t"),
        ]
        for variant in variants:
            self.cpp.write_text(variant, encoding="ascii")
            with self.assertRaises(ValueError):
                parse(self.cpp)

    def test_image_path_operands_flags_and_premature_exit(self) -> None:
        for field in ("pc", "insn", "a", "value", "trap", "halt", "intr", "debug_mode"):
            parts = self.text.splitlines()
            row = parts[3].split("\t")
            position = 2 + FIELDS.index(field)
            row[position] = str(int(row[position]) + 1)
            parts[3] = "\t".join(row)
            changed = "\n".join(parts) + "\n"
            self.cpp.write_text(changed, encoding="ascii")
            self.sv.write_text(changed, encoding="ascii")
            with self.assertRaises(ValueError):
                qualify(self.cpp, self.sv, self.image, self.contract)
        short = "\n".join(self.text.splitlines()[:-2]) + "\n"
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
