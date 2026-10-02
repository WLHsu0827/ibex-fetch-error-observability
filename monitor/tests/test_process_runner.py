from pathlib import Path
import signal
import tempfile
import unittest

from monitor.process_runner import (
    ProcessStatus,
    is_expected_reset_fatal,
    is_reset_text_timeout,
    run_bounded,
)


DIAG = "TRACE_MONITOR_RESET_AFTER_START"


def status(kind: str, code: int, text: str = DIAG) -> ProcessStatus:
    return ProcessStatus(kind, code, 0.01, ("fixture",), text, "")


class FatalClassificationTests(unittest.TestCase):
    def test_only_prompt_sigabrt_with_exact_diagnostic_passes(self):
        self.assertTrue(is_expected_reset_fatal(status("signaled", signal.SIGABRT)))

    def test_false_pass_statuses_are_rejected(self):
        rejected = [
            status("timeout", 124),
            status("exited", 137),
            status("signaled", 9),
            status("signaled", 15),
            status("missing_tool", 127),
            status("signaled", 11),
            status("exited", 0),
            status("exited", 1, "different diagnostic"),
            status("malformed", 6),
        ]
        for item in rejected:
            with self.subTest(kind=item.kind, code=item.code):
                self.assertFalse(is_expected_reset_fatal(item))

    def test_live_fatal_text_then_hang_is_timeout(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = run_bounded(
                [
                    __import__("sys").executable,
                    "-c",
                    f"import time; print('{DIAG}', flush=True); time.sleep(10)",
                ],
                cwd=directory,
                timeout_seconds=0.1,
                stdout_path=directory / "stdout.log",
                stderr_path=directory / "stderr.log",
            )
        self.assertEqual((result.kind, result.code), ("timeout", 124))
        self.assertIn(DIAG, result.stdout + result.stderr)
        self.assertTrue(is_reset_text_timeout(result))
        self.assertFalse(is_expected_reset_fatal(result))

    def test_silent_timeout_is_not_the_text_regression(self):
        self.assertFalse(is_reset_text_timeout(status("timeout", 124, "")))

    def test_missing_tool_is_typed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            result = run_bounded(
                ["definitely-not-a-real-trace-monitor-tool"],
                cwd=directory,
                timeout_seconds=0.1,
                stdout_path=directory / "stdout.log",
                stderr_path=directory / "stderr.log",
            )
        self.assertEqual((result.kind, result.code), ("missing_tool", 127))


if __name__ == "__main__":
    unittest.main()
