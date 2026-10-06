from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from monitor.run_all import check_trace
from monitor.trace_check import TraceError, parse_trace, require_positive_trace


GOOD = {
    "Q": [[0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0, 0, 0]],
    "B": [[0, 0x100, 0x13, 1, 0, 0, 0, 0]],
    "PRE": [[0, 0x100, 0x13, 0, 0x104, 0x104, 0, 0, 1, 0]],
    "POST": [[0, 1, 0x100, 0x13, 0x104, 1, 0, 0]],
    "R": [[1, 1, 0x100, 0x13, 0x104, 0, 0, 0, 0, 0, 0, 0]],
}
GOOD_TEXT = (
    "Q\t0\t0\t0\t0\t0000\t0\t0\t0\t0\n"
    "B\t0\t00000100\t00000013\t1\t0\t0\t00000000\t0\n"
    "PRE\t0\t00000100\t00000013\t0\t00000104\t00000104\t0\t00000000\t1\t0\n"
    "POST\t0\t1\t00000100\t00000013\t00000104\t1\t0\t0\n"
    "Q\t1\t0\t0\t0\t0000\t0\t0\t0\t0\n"
    "R\t1\t1\t00000100\t00000013\t00000104\t0\t0\t0\t0\t00000000\t0\t00000000\n"
)


class TraceContractTests(unittest.TestCase):
    def test_positive_trace(self):
        require_positive_trace(deepcopy(GOOD))

    def test_bad_cycles_and_counts_reject(self):
        mutations = []
        for q in (
            [[0, *([0] * 8)], [0, *([0] * 8)]],
            [[0, *([0] * 8)], [2, *([0] * 8)]],
            [[1, *([0] * 8)]],
            GOOD["Q"] + [[2, *([0] * 8)]],
        ):
            changed = deepcopy(GOOD)
            changed["Q"] = q
            mutations.append(changed)
        for kind in ("B", "PRE", "POST", "R"):
            missing = deepcopy(GOOD)
            missing[kind] = []
            mutations.append(missing)
            extra = deepcopy(GOOD)
            extra[kind].append(deepcopy(extra[kind][0]))
            mutations.append(extra)
        for changed in mutations:
            with self.subTest(changed=changed):
                with self.assertRaises(TraceError):
                    require_positive_trace(changed)

    def test_every_event_field_is_checked(self):
        for kind in ("B", "PRE", "POST", "R"):
            for index in range(len(GOOD[kind][0])):
                changed = deepcopy(GOOD)
                changed[kind][0][index] += 1
                with self.subTest(kind=kind, index=index):
                    with self.assertRaisesRegex(TraceError, f"{kind} row differs"):
                        require_positive_trace(changed)

    def test_parser_rejects_unknown_malformed_and_non_integer_rows(self):
        samples = (
            "X\t0\n",
            "Q\t0\n",
            "Q\tzero\t0\t0\t0\t0000\t0\t0\t0\t0\n",
        )
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.tsv"
            for sample in samples:
                path.write_text(sample)
                with self.subTest(sample=sample):
                    with self.assertRaises(TraceError):
                        parse_trace(path)

    def test_parser_uses_schema_bases_for_digit_only_hex(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.tsv"
            path.write_text(GOOD_TEXT)
            require_positive_trace(parse_trace(path))

    def test_physical_row_order_is_required(self):
        lines = GOOD_TEXT.splitlines()
        lines[1], lines[2] = lines[2], lines[1]
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.tsv"
            path.write_text("\n".join(lines) + "\n")
            with self.assertRaisesRegex(TraceError, "row sequence must be"):
                require_positive_trace(parse_trace(path))

    def test_numeric_syntax_and_ranges_are_strict(self):
        replacements = {
            "\t0\t0\t0\t0\t0000": "\t-1\t0\t0\t0\t0000",
            "\t00000100\t00000013": "\t000000100\t00000013",
            "\t1\t0\t0\t00000000": "\t2\t0\t0\t00000000",
            "\t0\t00000000\t0\t00000000\n": "\t32\t00000000\t0\t00000000\n",
        }
        for old, new in replacements.items():
            with self.subTest(replacement=new):
                with tempfile.TemporaryDirectory() as raw:
                    path = Path(raw) / "events.tsv"
                    path.write_text(GOOD_TEXT.replace(old, new, 1))
                    with self.assertRaises(TraceError):
                        require_positive_trace(parse_trace(path))

    def test_check_entrypoint_reports_pass_and_actionable_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.tsv"
            path.write_text(GOOD_TEXT)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                check_trace(path)
            result = json.loads(output.getvalue())
            self.assertEqual(result["result"], "PASS")
            self.assertEqual(result["row_counts"]["Q"], 2)
            path.write_text("Q\t0\n")
            with self.assertRaisesRegex(
                SystemExit, r"trace rejected: line 1 Q: expected 10 columns, got 2"
            ):
                check_trace(path)

    def test_module_cli_returns_nonzero_for_partial_trace(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.tsv"
            path.write_text(GOOD_TEXT)
            command = [
                sys.executable,
                "-B",
                "-m",
                "monitor.run_all",
                "--mode",
                "check",
                "--trace",
                str(path),
            ]
            accepted = subprocess.run(
                command, cwd=Path(__file__).resolve().parents[2],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(json.loads(accepted.stdout)["result"], "PASS")
            path.write_text(GOOD_TEXT.rsplit("\n", 2)[0] + "\n")
            rejected = subprocess.run(
                command, cwd=Path(__file__).resolve().parents[2],
                text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("row sequence must be", rejected.stderr)

    def test_excessively_long_decimal_has_context_without_traceback(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.tsv"
            path.write_text(GOOD_TEXT.replace("Q\t0\t", f"Q\t{'9' * 5000}\t", 1))
            with self.assertRaisesRegex(
                TraceError, r"line 1 Q\.cycle: integer conversion rejected"
            ):
                parse_trace(path)
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "monitor.run_all",
                    "--mode",
                    "check",
                    "--trace",
                    str(path),
                ],
                cwd=Path(__file__).resolve().parents[2],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn(
                "trace rejected: line 1 Q.cycle: integer conversion rejected",
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
