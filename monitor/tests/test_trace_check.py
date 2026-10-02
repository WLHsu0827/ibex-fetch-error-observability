from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from monitor.trace_check import TraceError, parse_trace, require_positive_trace


GOOD = {
    "Q": [[0, 0, 0, 0, 0, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0, 0, 0]],
    "B": [[0, 0x100, 0x13, 1, 0, 0, 0, 0]],
    "PRE": [[0, 0x100, 0x13, 0, 0x104, 0x104, 0, 0, 1, 0]],
    "POST": [[0, 1, 0x100, 0x13, 0x104, 1, 0, 0]],
    "R": [[1, 1, 0x100, 0x13, 0x104, 0, 0, 0, 0, 0, 0, 0]],
}


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

    def test_pre_post_and_retire_association_reject(self):
        for kind, index in (("B", 0), ("PRE", 1), ("POST", 1), ("R", 0)):
            changed = deepcopy(GOOD)
            changed[kind][0][index] += 1
            with self.subTest(kind=kind):
                with self.assertRaises(TraceError):
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
        text = (
            "Q\t0\t0\t0\t0\t0000\t0\t0\t0\t0\n"
            "Q\t1\t0\t0\t0\t0000\t0\t0\t0\t0\n"
            "B\t0\t00000100\t00000013\t1\t0\t0\t00000000\t0\n"
            "PRE\t0\t00000100\t00000013\t0\t00000104\t00000104\t0\t00000000\t1\t0\n"
            "POST\t0\t1\t00000100\t00000013\t00000104\t1\t0\t0\n"
            "R\t1\t1\t00000100\t00000013\t00000104\t0\t0\t0\t0\t00000000\t0\t00000000\n"
        )
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "events.tsv"
            path.write_text(text)
            require_positive_trace(parse_trace(path))


if __name__ == "__main__":
    unittest.main()
