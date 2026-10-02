import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "monitor" / "SOURCE_MANIFEST.json"


def lf_bytes(path: Path) -> bytes:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    if b"\r" in data:
        raise AssertionError(f"{path}: lone carriage return")
    return data


class PublicSourceManifestTests(unittest.TestCase):
    def test_exact_public_source_hashes_and_allowlist(self):
        data = json.loads(MANIFEST.read_text())
        expected = set(data["source_sha256"]) | {"monitor/SOURCE_MANIFEST.json"}
        actual = {
            path.relative_to(ROOT).as_posix()
            for root in (ROOT / "monitor", ROOT / ".github" / "workflows")
            for path in root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and (
                not path.relative_to(ROOT).as_posix().startswith("monitor/evidence/")
                or path.name == ".gitattributes"
            )
        }
        self.assertEqual(actual, expected)
        for relative, digest in data["source_sha256"].items():
            actual_digest = hashlib.sha256(lf_bytes(ROOT / relative)).hexdigest()
            self.assertEqual(actual_digest, digest, relative)

    def test_public_payload_has_no_private_path_or_token_pattern(self):
        forbidden = (
            re.compile(r"[A-Za-z]:\\"),
            re.compile(r"/(?:home|Users)/[^/\s]+/"),
            re.compile(r"\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_]+"),
            re.compile(r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        )
        data = json.loads(MANIFEST.read_text())
        for relative in data["source_sha256"]:
            text = (ROOT / relative).read_text(errors="strict")
            for pattern in forbidden:
                self.assertIsNone(pattern.search(text), f"{relative}: {pattern.pattern}")

    def test_archived_hosted_bytes_match_raw_manifest(self):
        evidence = ROOT / "monitor" / "evidence" / "run-36952633401"
        manifest = json.loads((evidence / "RAW_MANIFEST.json").read_text())
        actual = {
            path.relative_to(evidence).as_posix()
            for path in evidence.rglob("*")
            if path.is_file() and path.name != "RAW_MANIFEST.json"
        }
        self.assertEqual(actual, set(manifest["files"]))
        for relative, expected in manifest["files"].items():
            raw = (evidence / relative).read_bytes()
            self.assertEqual(len(raw), expected["length"], relative)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected["sha256"], relative)


if __name__ == "__main__":
    unittest.main()
