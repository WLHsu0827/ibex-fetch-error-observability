import hashlib
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from bounded import Limits, capture
from config import CONFIG, CONFIG_SHA, WORKLOADS, cpu_observation
from result import classify, coremark_selfcheck


class ProcessContracts(unittest.TestCase):
    def run_case(self, case, workload="aha-mont64", **caps):
        with tempfile.TemporaryDirectory() as root:
            record, streams = capture(
                [sys.executable, "-I", "-B", str(HERE / "synthetic_child.py"), case],
                pathlib.Path(root) / case,
                Limits(wall_seconds=1.5, **caps), program_name="benchmark.log",
            )
            for key, stream in streams.items():
                self.assertEqual(record["streams"][key]["sha256"],
                                 hashlib.sha256(stream).hexdigest())
            self.assertLessEqual(sum(map(len, streams.values())), record["limits"]["output_bytes"])
            outcome = classify(record["termination"], streams["stdout"],
                               streams["stderr"], streams["program"], workload)
            artifact = os.environ.get("STOCK_PROFILE_TEST_RECEIPTS")
            if artifact:
                folder = pathlib.Path(artifact) / case
                folder.mkdir(parents=True, exist_ok=False)
                # Do not publish interpreter paths or host environment.
                record["argv"] = ["python", "-I", "-B", "synthetic_child.py", case]
                for key, stream in streams.items():
                    (folder / f"{key}.log").write_bytes(stream)
                (folder / "status.json").write_text(
                    json.dumps({"capture": record, "contract": outcome}, indent=2) + "\n"
                )
            return record, outcome, streams

    def test_complete_selfcheck(self):
        record, result, streams = self.run_case("pass")
        self.assertEqual((record["termination"], result["completed"], result["verification"]),
                         ("exit_zero", True, "VERIFIED"))
        self.assertEqual(streams["stdout"], ("synthetic stdout" + os.linesep).encode())
        self.assertEqual(streams["stderr"], ("synthetic stderr" + os.linesep).encode())

    def test_bad_markers_never_pass(self):
        for case in ("missing", "duplicate", "truncated", "malformed", "configwrong",
                     "workloadwrong", "selfcheck_invalid", "bad_utf8", "wrong_channel"):
            with self.subTest(case=case):
                _, result, _ = self.run_case(case)
                self.assertFalse(result["completed"])
                self.assertEqual(result["verification"], "NOT_VERIFIED")

    def test_verifier_tristate(self):
        for case, expected in (("selfcheck_minus1", "NOT_VERIFIED"),
                               ("selfcheck_fail", "FAILED")):
            _, result, _ = self.run_case(case)
            self.assertTrue(result["completed"])
            self.assertEqual(result["verification"], expected)

    def test_marker_followed_by_failure(self):
        for case, kind in (("marker_hang", "wall_timeout"), ("hang", "wall_timeout"),
                           ("cycle_timeout", "cycle_timeout"), ("trap", "trap"),
                           ("nonzero", "exit_nonzero"),
                           ("signal", "signal" if os.name == "posix" else "exit_nonzero")):
            with self.subTest(case=case):
                _, result, _ = self.run_case(case)
                self.assertEqual(result["termination"], kind)
                self.assertFalse(result["completed"])
                self.assertNotEqual(result["verification"], "VERIFIED")

    def test_all_output_channels_bounded(self):
        for case in ("flood_stdout", "flood_stderr", "flood_program"):
            record, result, _ = self.run_case(case, file_bytes=512 * 1024)
            self.assertEqual(record["termination"], "output_limit")
            self.assertTrue(record["truncated"])
            self.assertNotEqual(result["verification"], "VERIFIED")

    @unittest.skipUnless(os.name == "posix", "POSIX resource/descendant caps; Windows NOT_VERIFIED")
    def test_real_resource_and_descendant_cases(self):
        for case in ("resource_cpu", "resource_file", "resource_address", "orphan_pipe"):
            record, result, _ = self.run_case(case, cpu_seconds=1, file_bytes=32768)
            self.assertEqual(record["termination"],
                             "wall_timeout" if case == "orphan_pipe" else "resource_limit")
            self.assertNotEqual(result["verification"], "VERIFIED")

    def test_spawn_error(self):
        with tempfile.TemporaryDirectory() as root:
            record, streams = capture([str(pathlib.Path(root) / "absent-executable")],
                                      pathlib.Path(root) / "spawn")
            self.assertEqual(record["termination"], "spawn_error")
            self.assertIsNone(record["returncode"])
            self.assertEqual(streams["stdout"], b"")
            artifact = os.environ.get("STOCK_PROFILE_TEST_RECEIPTS")
            if artifact:
                folder = pathlib.Path(artifact) / "spawn_error"
                folder.mkdir(parents=True, exist_ok=False)
                record["argv"] = ["<ABSENT_SYNTHETIC_EXECUTABLE>"]
                record["detail"] = record["detail"].replace(root, "<SYNTHETIC_ROOT>")
                (folder / "status.json").write_text(json.dumps(record, indent=2) + "\n")
                for key, stream in streams.items():
                    (folder / f"{key}.log").write_bytes(stream)

    def test_coremark_official_semantics(self):
        for case, expected in (("coremark", "VERIFIED"), ("coremark_bad_crc", "FAILED"),
                               ("coremark_unknown", "FAILED"), ("coremark_missing", "NOT_VERIFIED"),
                               ("coremark_duplicate", "NOT_VERIFIED"),
                               ("coremark_wrong_input", "FAILED"), ("coremark_error", "FAILED"),
                               ("coremark_forged_verify", "NOT_VERIFIED")):
            with self.subTest(case=case):
                _, result, _ = self.run_case(case, workload="coremark")
                self.assertEqual(result["verification"], expected)


class ScopeContracts(unittest.TestCase):
    def test_cpu_always_refused(self):
        for flag in (False, True, "AUTHORIZED"):
            with self.assertRaisesRegex(PermissionError, "NO_CPU_RUN"):
                cpu_observation(authorization=flag)

    def test_local_tool_install_refused(self):
        from host import install_and_probe
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with self.assertRaisesRegex(RuntimeError, "no local installation"):
                install_and_probe()

    def test_configuration(self):
        self.assertEqual(len(CONFIG["parameters"]), 19)
        self.assertEqual(CONFIG["parameters"]["BaseIsa"], "ibex_pkg::BaseIsaRV32I")
        self.assertEqual(CONFIG["parameters"]["MHPMCounterNum"], 10)
        self.assertEqual(CONFIG["parameters"]["MHPMCounterWidth"], 40)
        self.assertEqual(len(set(WORKLOADS)), 19)
        self.assertEqual(len(CONFIG_SHA), 64)

    def test_invalid_caps(self):
        for field in ("wall_seconds", "output_bytes", "address_bytes", "cpu_seconds", "file_bytes"):
            with self.assertRaises(ValueError):
                Limits(**{field: 0})

    def test_source_seal_covers_every_workload(self):
        seal = json.loads((HERE / "source_manifest.json").read_text())
        self.assertEqual(set(seal["workloads"]), set(WORKLOADS))
        for name, record in seal["workloads"].items():
            self.assertEqual(record["classification"], "EXPLORATORY")
            self.assertEqual(record["verifier"]["execution"], "NOT_VERIFIED")
            files = [r for r in seal["sources"]["embench"]["files"]
                     if r["path"].startswith("src/" + name + "/")]
            self.assertTrue(files)
            self.assertTrue(all(len(r["sha256"]) == 64 for r in files))

    def test_published_receipts_preserve_original_bytes(self):
        from import_receipts import physical
        for path in physical(HERE / "receipts").glob("*/artifact_manifest.json"):
            manifest = json.loads(path.read_bytes())
            self.assertEqual(manifest["kind"], "SELECTED_RECEIPT_ARCHIVE_NOT_QUALIFICATION")
            for record in manifest["files"]:
                data = path.parent.joinpath(*record["path"].split("/")).read_bytes()
                self.assertEqual(len(data), record["bytes"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), record["sha256"])
            run = json.loads((path.parent / "run.json").read_bytes())
            self.assertFalse(run["archive_is_qualification"])

    def test_fixed_exact_tool_dependency_contract(self):
        from lock_tools import check_exact_requirements
        wheels = json.loads((HERE / "wheel_manifest.json").read_bytes())
        check_exact_requirements(wheels)
        broken = [dict(r, version="6.0.3") if r["name"] == "PyYAML" else r for r in wheels]
        with self.assertRaisesRegex(ValueError, "mandatory exact dependency conflict"):
            check_exact_requirements(broken)

    def test_extension_reservation_fail_closed(self):
        from hosted_gate import reservation
        self.assertEqual(reservation("extension-1", 1, 2, 0), 1)
        for arguments in (("original", 1, 2, 0), ("original", 1, 1, 1),
                          ("original", 2, 0, 0), ("extension-1", 2, 2, 0),
                          ("extension-1", 1, 2, 1), ("extension-1", 1, 2, 2),
                          ("extension-1", 1, 1, 0), ("extension-1", 1, 3, 0),
                          ("unknown", 1, 2, 0)):
            with self.subTest(arguments=arguments), self.assertRaises(RuntimeError):
                reservation(*arguments)

    def test_started_reservation_ledger(self):
        from hosted_gate import LEGACY_STEP, EXTENSION_STEP, started_reservations
        jobs = [{"steps": [
            {"name": LEGACY_STEP, "started_at": "time", "conclusion": "success"},
            {"name": LEGACY_STEP, "started_at": "time", "conclusion": "skipped"},
            {"name": EXTENSION_STEP, "started_at": None, "conclusion": "cancelled"},
            {"name": EXTENSION_STEP, "started_at": "time", "conclusion": "failure"},
        ]}]
        self.assertEqual(started_reservations(jobs), {LEGACY_STEP: 1, EXTENSION_STEP: 1})

    def test_extension_accepted_identities_and_changed_lock_refused(self):
        import hosted_gate
        self.assertEqual(len(hosted_gate.check_extension_identities()), 64)
        with tempfile.TemporaryDirectory() as root:
            root = pathlib.Path(root)
            approval = json.loads((HERE / "tool_extension_approval.json").read_bytes())
            (root / "tool_extension_approval.json").write_text(json.dumps(approval))
            (root / "source_manifest.json").write_text("altered")
            with mock.patch.object(hosted_gate, "HERE", root):
                with self.assertRaisesRegex(RuntimeError, "immutable identity changed"):
                    hosted_gate.check_extension_identities()

    def test_entry_outputs_refuse_duplicate_rerun_old_or_wrong_event(self):
        import contextlib
        import io
        import hosted_gate
        for case in ("approved", "duplicate", "rerun", "old_entry", "wrong_label"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as root:
                root = pathlib.Path(root)
                event = {"number": 4, "action": "labeled",
                         "label": {"name": hosted_gate.LABEL},
                         "pull_request": {"head": {"ref": "wlhsu0827-stock-workload-preparation",
                                                   "sha": "a" * 40,
                                                   "repo": {"full_name": "WLHsu0827/ibex-fetch-error-observability"}}}}
                if case == "wrong_label":
                    event["label"]["name"] = "unapproved"
                (root / "event.json").write_text(json.dumps(event))
                (root / "output").write_text("")
                env = {"GITHUB_REPOSITORY": "WLHsu0827/ibex-fetch-error-observability",
                       "GITHUB_EVENT_NAME": "pull_request", "GITHUB_RUN_ID": "99",
                       "GITHUB_RUN_ATTEMPT": "2" if case == "rerun" else "1",
                       "GITHUB_SHA": "a" * 40, "GITHUB_EVENT_PATH": str(root / "event.json"),
                       "GITHUB_OUTPUT": str(root / "output")}
                runs = [{"id": n, "run_attempt": 1} for n in (10, 11)]
                if case == "duplicate":
                    runs.append({"id": 12, "run_attempt": 1})

                def fake_api(path):
                    if path == "actions/runs/99":
                        return {"workflow_id": 1}
                    if path.startswith("actions/workflows/"):
                        return {"total_count": len(runs), "workflow_runs": runs}
                    name = (hosted_gate.EXTENSION_STEP if "/12/" in path
                            else hosted_gate.LEGACY_STEP)
                    return {"total_count": 1, "jobs": [{"steps": [
                        {"name": name, "started_at": "time", "conclusion": "success"}]}]}

                mode = "original" if case == "old_entry" else "extension-1"
                with mock.patch.dict(os.environ, env), mock.patch.object(hosted_gate, "HERE", root), \
                        mock.patch.object(hosted_gate, "api", side_effect=fake_api), \
                        mock.patch.object(hosted_gate, "check_extension_identities",
                                          return_value="b" * 64), \
                        contextlib.redirect_stdout(io.StringIO()):
                    if case == "approved":
                        hosted_gate.run_gate(mode)
                        self.assertEqual((root / "output").read_text(), "authorized=true\n")
                    else:
                        with self.assertRaises(SystemExit):
                            hosted_gate.run_gate(mode)
                        self.assertEqual((root / "output").read_text(), "")


if __name__ == "__main__":
    unittest.main()
