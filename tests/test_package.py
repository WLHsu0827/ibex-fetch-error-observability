#!/usr/bin/env python3
# Copyright 2026 Wei-Lun Hsu.
# SPDX-License-Identifier: Apache-2.0
"""Small offline tests using PUBLIC frozen evidence, not executed RTL."""

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.temp = Path(self.temporary.name)
        self.cache = json.loads((ROOT / "verification/replayed_cache.json").read_text())
        self.core = json.loads((ROOT / "verification/replayed_core.json").read_text())

    def command(self, *args):
        return subprocess.run(
            [sys.executable, "-B", *map(str, args)],
            cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
            text=True, capture_output=True, check=False, timeout=30,
        )

    def compare(self, cache=None, core=None):
        paths = [self.temp / "cache.json", self.temp / "core.json"]
        for path, data in zip(paths, (self.cache if cache is None else cache,
                                     self.core if core is None else core)):
            path.write_text(json.dumps(data), encoding="utf-8")
        return self.command(ROOT / "scripts/compare.py",
                            "--cache", paths[0], "--core", paths[1])

    def assert_rejected(self, result, message):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(message, result.stdout + result.stderr)

    def copy_package(self):
        package = self.temp / "package"
        for name in audit.EXPECTED:
            destination = package / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        return package

    def test_frozen_public_evidence_passes_offline(self):
        result = self.compare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("classifications match"), 2)
        self.assertIn("compiled binary SHA-256 differs", result.stdout)
        for data in (self.cache, self.core):
            self.assertEqual(set(data["cases"]),
                             {"hit_control", "speculative_hit", "demand_miss"})
            self.assertTrue(all(case["pass"] for case in data["cases"].values()))

    def test_missing_or_extra_case_fails(self):
        for suite in ("cache", "core"):
            for change in ("missing", "extra"):
                with self.subTest(suite=suite, change=change):
                    data = copy.deepcopy(getattr(self, suite))
                    if change == "missing":
                        del data["cases"]["demand_miss"]
                    else:
                        data["cases"]["duplicate"] = data["cases"]["hit_control"]
                    self.assert_rejected(self.compare(**{suite: data}), "data differ")

    def test_duplicate_case_key_fails(self):
        cache = self.temp / "cache.json"
        core = self.temp / "core.json"
        text = json.dumps(self.cache)
        case = json.dumps(self.cache["cases"]["hit_control"])
        text = text.replace('"cases": {', f'"cases": {{"hit_control": {case},', 1)
        cache.write_text(text, encoding="utf-8")
        core.write_text(json.dumps(self.core), encoding="utf-8")
        self.assert_rejected(
            self.command(ROOT / "scripts/compare.py", "--cache", cache, "--core", core),
            "Duplicate JSON key: hit_control",
        )

    def test_required_source_hash_change_or_removal_fails(self):
        for suite in ("cache", "core"):
            for change in ("changed", "missing"):
                with self.subTest(suite=suite, change=change):
                    data = copy.deepcopy(getattr(self, suite))
                    key = "rtl/ibex_icache.sv"
                    if change == "missing":
                        del data["source_sha256"][key]
                    else:
                        data["source_sha256"][key] = "0" * 64
                    self.assert_rejected(self.compare(**{suite: data}), "source_sha256")

    def test_rvfi_csr_classification_and_event_changes_fail(self):
        for change in ("rvfi", "csr", "classification", "order", "cycle", "duplicate"):
            with self.subTest(change=change):
                data = copy.deepcopy(self.core)
                cold = data["cases"]["demand_miss"]
                if change == "rvfi":
                    cold["actual"]["target_traps"] = 0
                elif change == "csr":
                    cold["actual"]["mcause"] = 2
                elif change == "classification":
                    data["bus_checker_vs_trap"]["fp"] = 0
                elif change == "order":
                    cold["events"][0:2] = reversed(cold["events"][0:2])
                elif change == "cycle":
                    cold["events"][1]["cycle"] += 1
                else:
                    cold["events"].append(copy.deepcopy(cold["events"][0]))
                self.assert_rejected(self.compare(core=data), "data differ")
        cache = copy.deepcopy(self.cache)
        cache["cases"]["speculative_hit"]["observed"]["if_errors"] = 1
        self.assert_rejected(self.compare(cache=cache), "data differ")

    def test_failed_runner_wrong_type_and_missing_binary_fail(self):
        for change in ("failed", "boolean", "binary", "malformed"):
            with self.subTest(change=change):
                data = copy.deepcopy(self.core)
                if change == "failed":
                    data["pass"] = False
                elif change == "boolean":
                    data["warm_control_aligned"] = 1
                elif change == "binary":
                    del data["binary_sha256"]
                else:
                    data["binary_sha256"] = "not-a-sha256"
                self.assert_rejected(self.compare(core=data), "Candidate comparison failed")

    def test_audit_copied_public_package_and_frozen_byte_failure(self):
        package = self.copy_package()
        result = self.command(package / "scripts/audit.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = package / "observations/core_results.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.assert_rejected(self.command(package / "scripts/audit.py"),
                             "frozen observation bytes changed")

    def test_audit_required_manifest_source_fails(self):
        package = self.copy_package()
        path = package / "SOURCE_MANIFEST.json"
        manifest = json.loads(path.read_text())
        manifest["source_sha256"]["rtl/ibex_icache.sv"] = "0" * 64
        path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assert_rejected(self.command(package / "scripts/audit.py"),
                             "current source hash differs")

    def test_audit_excludes_only_private_app_checkpoint_refs(self):
        package = self.copy_package()
        def git(*args):
            return subprocess.run(["git", "-C", str(package), *args],
                                  capture_output=True, text=True, check=True).stdout.strip()
        git("init", "-q")
        approved = "151040862+WLHsu0827" + chr(64) + "users.noreply.github.com"
        git("-c", "user.name=Fixture", "-c", f"user.email={approved}",
            "commit", "-q", "--allow-empty", "-m", "Public fixture")
        unexpected = "fixture" + chr(64) + "example.invalid"
        checkpoint = git("-c", "user.name=Fixture", "-c", f"user.email={unexpected}",
                         "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m",
                         "Private app checkpoint")
        git("update-ref", "refs/copilot/checkpoints/offline-fixture/1", checkpoint)
        result = self.command(package / "scripts/audit.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        git("update-ref", "refs/heads/unexpected-public-author", checkpoint)
        self.assert_rejected(self.command(package / "scripts/audit.py"),
                             "unexpected email in reachable commit history")

    def test_ci_installer_refuses_local_execution(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/ci_replay.py")],
            cwd=ROOT, env=dict(os.environ, GITHUB_ACTIONS="false",
                              PYTHONDONTWRITEBYTECODE="1"),
            text=True, capture_output=True, check=False, timeout=30,
        )
        self.assert_rejected(result, "Refusing installation/build")

    def test_stage_wrong_pin_and_dirty_checkout_fail_before_writes(self):
        checkout = self.temp / "upstream"
        checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(checkout)], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture.invalid", "commit", "-q",
                        "--allow-empty", "-m", "Offline staging fixture"], check=True,
                       capture_output=True)
        result = self.command(ROOT / "scripts/stage.py", "--checkout", checkout)
        self.assert_rejected(result, "not at pinned upstream commit")
        package = self.copy_package()
        pin = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                             check=True, text=True, capture_output=True).stdout.strip()
        (package / "UPSTREAM_COMMIT").write_text(pin, encoding="ascii")
        manifest_path = package / "SOURCE_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["upstream_commit"] = pin
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (checkout / "dirty.txt").write_text("offline fixture", encoding="ascii")
        result = self.command(package / "scripts/stage.py", "--checkout", checkout)
        self.assert_rejected(result, "not clean")
        self.assertFalse((checkout / "dv").exists())

    def test_protected_bytes_match_git_blobs(self):
        if not (ROOT / ".git").exists():
            self.skipTest("Archive copy has no Git blobs; frozen hashes still audited")
        protected = list(audit.FROZEN_HASHES | audit.HISTORICAL_HASHES)
        protected += [f"experiment/{name}" for name in
                      ("tb.sv", "run.py", "run_core.py", "core_program.vmem")]
        protected += ["patches/simple-system-fetch-fault.patch", "LICENSE", "NOTICE",
                      "upstream-notices/LICENSE", "upstream-notices/NOTICE",
                      "SOURCE_MANIFEST.json", "UPSTREAM_COMMIT"]
        self.assertEqual(len(protected), 19)
        for name in protected:
            with self.subTest(path=name):
                attr = subprocess.run(["git", "check-attr", "text", "--", name],
                                      cwd=ROOT, capture_output=True, text=True, check=True)
                self.assertTrue(attr.stdout.strip().endswith(": text: unset"))
                blob = subprocess.run(["git", "show", f"HEAD:{name}"], cwd=ROOT,
                                      capture_output=True, check=True).stdout
                self.assertEqual(hashlib.sha256(blob).digest(),
                                 hashlib.sha256((ROOT / name).read_bytes()).digest())


if __name__ == "__main__":
    unittest.main()
