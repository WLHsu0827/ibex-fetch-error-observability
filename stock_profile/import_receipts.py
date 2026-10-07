"""Seal selected hosted receipts into this package, preserving every original byte."""

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
MAXIMUM = 16 * 1024**2


def physical(path):
    path = pathlib.Path(path).resolve()
    if os.name == "nt" and not str(path).startswith("\\\\?\\"):
        return pathlib.Path("\\\\?\\" + str(path))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--conclusion", choices=("success", "failure", "cancelled", "timed_out"),
                        required=True)
    parser.add_argument("--zip-sha256")
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-f]{40}", args.head):
        raise SystemExit("exact immutable code head required")
    artifact = args.artifact.resolve()
    if not artifact.is_relative_to(HERE / "_published"):
        raise SystemExit("artifact must be inside ignored stock_profile/_published")
    zip_digest = None
    if artifact.suffix == ".zip":
        zip_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if zip_digest != args.zip_sha256:
            raise SystemExit("GitHub artifact ZIP digest mismatch; STOP")
        destination = physical(HERE / "_published" / (str(args.run) + "-complete"))
        destination.mkdir(exist_ok=False)
        with zipfile.ZipFile(artifact) as archive:
            if sum(info.file_size for info in archive.infolist()) > MAXIMUM:
                raise SystemExit("16 MiB ZIP expansion cap exceeded")
            for info in archive.infolist():
                relative = pathlib.PurePosixPath(info.filename)
                if (relative.is_absolute() or ".." in relative.parts
                        or "\\" in info.filename or ":" in info.filename
                        or relative.suffix not in (".json", ".log")):
                    raise SystemExit("unsafe/non-log ZIP entry refused")
                target = destination.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(archive.read(info))
        artifact = destination
    else:
        artifact = physical(artifact)
    manifest_path = artifact / "artifact_manifest.json"
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest["kind"] != "SELECTED_RECEIPT_ARCHIVE_NOT_QUALIFICATION":
        raise SystemExit("incorrect artifact contract")
    expected_paths = {r["path"] for r in manifest["files"]} | {"artifact_manifest.json"}
    actual_paths = {p.relative_to(artifact).as_posix() for p in artifact.rglob("*") if p.is_file()}
    if actual_paths != expected_paths:
        raise SystemExit("missing/extra artifact files; STOP")
    total = len(raw_manifest)
    for record in manifest["files"]:
        relative = pathlib.PurePosixPath(record["path"])
        if (relative.is_absolute() or ".." in relative.parts
                or "\\" in record["path"] or ":" in record["path"]
                or relative.suffix not in (".json", ".log")):
            raise SystemExit("unsafe/non-log artifact path")
        path = artifact.joinpath(*relative.parts)
        if path.is_symlink() or not path.resolve().is_relative_to(artifact):
            raise SystemExit("symlink/outside artifact file refused")
        data = path.read_bytes()
        if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise SystemExit("original receipt byte/hash mismatch; STOP")
        if re.search(rb"(?:gh[pousr]_[A-Za-z0-9]{30}|github_pat_|-----BEGIN.*PRIVATE KEY|C:\\Users\\)",
                     data):
            raise SystemExit("potential credential/private-path publication refused; STOP")
        total += len(data)
    if total - len(raw_manifest) != manifest["total_bytes"]:
        raise SystemExit("artifact total-byte mismatch")
    receipts = physical(HERE / "receipts")
    existing = sum(p.stat().st_size for p in receipts.rglob("*") if p.is_file())
    if existing + total + 65536 > MAXIMUM:
        raise SystemExit("aggregate 16 MiB publication cap exceeded; STOP")
    destination = receipts / str(args.run)
    destination.mkdir(parents=True, exist_ok=False)
    for relative in sorted(actual_paths):
        target = destination.joinpath(*pathlib.PurePosixPath(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact.joinpath(*pathlib.PurePosixPath(relative).parts), target)
    receipt = {
        "scope": "PREPARATION_ONLY", "code_head": args.head,
        "run_id": args.run, "conclusion": args.conclusion,
        "url": f"https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/{args.run}",
        "artifact_manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "github_zip_sha256_locally_checked": zip_digest,
        "original_selected_bytes": total, "archive_is_qualification": False,
        "cpu_program_compile_run": "NOT_AUTHORIZED",
    }
    (destination / "run.json").write_text(json.dumps(receipt, indent=2) + "\n", newline="\n")
    print(json.dumps(receipt))
