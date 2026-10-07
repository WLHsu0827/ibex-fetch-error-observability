"""Acquire and seal only the two pinned public source archives; never execute them."""

import argparse
import hashlib
import json
import pathlib
import tarfile
import urllib.request

IBEX = "af456e25575013668ab56725268126f6b0feca35"
EMBENCH = "09c2ed8c3b7008c95d08b038de4a3f6dc103ed70"
PINS = {
    "ibex": ("lowRISC/ibex", IBEX),
    "embench": ("embench/embench-iot", EMBENCH),
}
IDENTITIES = {
    "ibex": ("7a9f3750e5ab7f75ac5504b528fc677fb77f22dc",
             "bc353cf3d99af40ccd8f7b36872c36ad9ddc74240f4bd943907dd2c48fb30e39"),
    "embench": ("b88459b702d04b50488f4ca9c4002d44657fd830",
                "715bd9f368564cebb2694c555d35d58028fe0293ac7635a2528863fde57f0480"),
}
LIMIT = 5 * 1024**3
ARCHIVE_LIMIT = 128 * 1024**2


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def tree_id(entries):
    root = {}
    for path, mode, oid in entries:
        parts = path.split("/")
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = (mode, oid)

    def encode(node):
        result = b""
        for name, value in sorted(
            node.items(), key=lambda pair: pair[0] + ("/" if isinstance(pair[1], dict) else "")
        ):
            mode, oid = ("40000", encode(value)) if isinstance(value, dict) else value
            result += mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid)
        return hashlib.sha1(b"tree " + str(len(result)).encode() + b"\0" + result).hexdigest()

    return encode(root)


def acquire(destination):
    destination.mkdir(parents=True, exist_ok=True)
    inventories = {}
    total = sum(p.stat().st_size for p in destination.rglob("*") if p.is_file())
    for name, (repo, commit) in PINS.items():
        url = f"https://codeload.github.com/{repo}/tar.gz/{commit}"
        archive = destination / f"{name}.tar.gz"
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=60) as response, archive.open("xb") as out:
                size = 0
                while chunk := response.read(65536):
                    size += len(chunk)
                    total += len(chunk)
                    if size > ARCHIVE_LIMIT or total > LIMIT:
                        raise RuntimeError("source cap exceeded; STOP (no automatic expansion)")
                    out.write(chunk)
        if archive.stat().st_size > ARCHIVE_LIMIT:
            raise RuntimeError("archive cap exceeded")
        if digest(archive.read_bytes()) != IDENTITIES[name][1]:
            raise RuntimeError("pinned archive hash mismatch; STOP, no fallback")
        entries, records = [], []
        base = destination / name
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                parts = pathlib.PurePosixPath(member.name).parts
                if member.isdir():
                    continue
                if (len(parts) < 2 or any(p in ("..", "") for p in parts)
                        or parts[0] == "/" or "\\" in member.name or ":" in member.name):
                    raise RuntimeError("unsafe archive path")
                relative = pathlib.PurePosixPath(*parts[1:])
                if member.issym():
                    data = member.linkname.encode()
                    mode = "120000"
                elif member.isfile():
                    if member.size > ARCHIVE_LIMIT or total + member.size > LIMIT:
                        raise RuntimeError("expanded source cap exceeded; STOP")
                    data = tar.extractfile(member).read()
                    mode = "100755" if member.mode & 0o111 else "100644"
                    target = base.joinpath(*relative.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        if target.read_bytes() != data:
                            raise RuntimeError(f"frozen source changed: {name}/{relative}")
                    else:
                        target.write_bytes(data)
                        total += len(data)
                else:
                    raise RuntimeError("unsupported archive member")
                entries.append((relative.as_posix(), mode, blob(data)))
                records.append({
                    "path": relative.as_posix(), "mode": mode, "bytes": len(data),
                    "sha256": digest(data), "git_blob": blob(data),
                })
        root_tree = tree_id(entries)
        if root_tree != IDENTITIES[name][0]:
            raise RuntimeError("pinned Git root tree mismatch; STOP")
        inventories[name] = {
            "repository": repo, "commit": commit, "url": url,
            "archive_sha256": digest(archive.read_bytes()),
            "root_tree": root_tree, "files": sorted(records, key=lambda r: r["path"]),
            "execution": "NOT_AUTHORIZED",
        }
    return inventories


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args()
    receipt = acquire(args.destination)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {f: v[f] for f in ("commit", "root_tree", "archive_sha256")}
                      for k, v in receipt.items()}, indent=2))
