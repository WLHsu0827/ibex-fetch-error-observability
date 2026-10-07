"""Publish only selected logs/metadata, not downloaded sources, tools or build trees."""

import hashlib
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
RECEIPTS = HERE / "_receipts"
SELECTED = RECEIPTS / "selected"
MAXIMUM = 16 * 1024**2


if __name__ == "__main__":
    SELECTED.mkdir(parents=True, exist_ok=False)
    files = []
    for directory in ("contracts", "synthetic", "tools"):
        root = RECEIPTS / directory
        if root.exists():
            files.extend(p for p in root.rglob("*") if p.is_file()
                         and p.suffix in (".log", ".json"))
    files.extend(p for name in ("source-status.json", "tool-attempt.json", "tool-failure.json")
                 if (p := RECEIPTS / name).exists())
    total, records = 0, []
    for path in sorted(files):
        if path.is_symlink():
            raise SystemExit("symlink receipt refused; STOP")
        data = path.read_bytes()
        total += len(data)
        if total > MAXIMUM - 65536:
            raise SystemExit("16 MiB selected receipt cap exceeded; STOP; no success archive")
        relative = path.relative_to(RECEIPTS)
        target = SELECTED / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        records.append({"path": relative.as_posix(), "bytes": len(data),
                        "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"scope": "PREPARATION_ONLY", "kind": "SELECTED_RECEIPT_ARCHIVE_NOT_QUALIFICATION",
                "total_bytes": total, "files": records}
    (SELECTED / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"selected_receipt_bytes": total, "maximum": MAXIMUM}))
