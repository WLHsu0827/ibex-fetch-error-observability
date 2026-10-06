# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Hosted-only locked artifact inspection and independently parsed PEP-508 closure."""

from __future__ import annotations

import argparse
import email
import hashlib
import importlib.metadata
import json
from pathlib import Path
import tarfile
import tomllib
import urllib.request
import zipfile

from .dependencies import TARGET, canonical, graph, validate
from .process import identity, write_json


def wheel_metadata(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path) as archive:
        metadata = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("ambiguous wheel distribution metadata")
        message = email.message_from_bytes(archive.read(metadata[0]))
        licenses = {
            name: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name in archive.namelist()
            if ".dist-info/" in name and (
                "/licenses/" in name or Path(name).name.lower().startswith(("license", "copying", "notice"))
            ) and not name.endswith("/") and (data := archive.read(name))
        }
    return {
        "name": canonical(message["Name"]), "version": message["Version"],
        "requires_python": message.get("Requires-Python", ""),
        "requires_dist": message.get_all("Requires-Dist", []),
        "license_expression": message.get("License-Expression"),
        "license_files": licenses,
    }


def download(lock: dict[str, object], directory: Path, output: Path) -> None:
    validate(lock)
    directory.mkdir(exist_ok=False)
    inspected = {}
    for group, config in lock["groups"].items():
        target = directory / group
        target.mkdir()
        packages = {}
        for name, item in config["packages"].items():
            artifact = item["artifact"]
            path = target / artifact["filename"]
            with urllib.request.urlopen(artifact["url"], timeout=30) as response, path.open("xb") as file:
                while chunk := response.read(1024 * 1024):
                    file.write(chunk)
            if identity(path) != {"bytes": artifact["bytes"], "sha256": artifact["sha256"]}:
                raise ValueError(f"locked artifact byte mismatch: {name}")
            print(f"LOCKED_ARTIFACT {group} {name}=={item['version']} {artifact['sha256']}", flush=True)
            if artifact["kind"] == "bdist_wheel":
                actual = wheel_metadata(path)
            else:
                with tarfile.open(path) as archive:
                    matches = [entry for entry in archive.getmembers() if entry.name.endswith("/pyproject.toml")]
                    if len(matches) != 1 or not matches[0].isfile():
                        raise ValueError("ambiguous source build system")
                    project = tomllib.loads(archive.extractfile(matches[0]).read().decode())
                    system = project["build-system"]
                    if system["requires"] != lock["source_build"]["requires"] or (
                        system["build-backend"] != lock["source_build"]["backend"]
                    ):
                        raise ValueError("unlocked sdist build requirements")
                    metadata = [entry for entry in archive.getmembers() if entry.name.count("/") == 1
                                and entry.name.endswith("/PKG-INFO")]
                    if len(metadata) != 1:
                        raise ValueError("missing sdist metadata")
                    message = email.message_from_bytes(archive.extractfile(metadata[0]).read())
                    actual = {
                        "name": canonical(message["Name"]), "version": message["Version"],
                        "requires_python": message.get("Requires-Python", ""),
                        "requires_dist": message.get_all("Requires-Dist", []),
                        "build_system": system,
                    }
            if actual["name"] != name or actual["version"] != item["version"]:
                raise ValueError("artifact/distribution identity mismatch")
            packages[name] = actual
        graph(packages, config["roots"])
        inspected[group] = packages
    write_json(output / "downloaded-tool-metadata.json", {
        "schema": 1, "lock": identity(Path(__file__).with_name("DEPENDENCY_LOCK.json")),
        "groups": inspected, "privacy": "No author/maintainer/environment fields or source execution.",
    })


def installed(lock: dict[str, object], group: str, output: Path) -> None:
    from packaging.markers import default_environment
    from packaging.requirements import Requirement
    from packaging.specifiers import SpecifierSet

    packages = lock["groups"][group]["packages"]
    distributions = list(importlib.metadata.distributions())
    actual = {canonical(item.metadata["Name"]): item.version for item in distributions}
    expected = {name: item["version"] for name, item in packages.items()}
    if actual != expected or len(distributions) != len(actual):
        raise ValueError(f"installed exact closure mismatch: {actual}")
    environment = default_environment()
    if any(environment[key] != value for key, value in TARGET.items()
           if key not in ("python_full_version", "implementation_version")):
        raise ValueError("actual Python/platform differs from locked target")
    by_name = {canonical(item.metadata["Name"]): item for item in distributions}
    pending, seen = list(lock["groups"][group]["roots"]), {}
    while pending:
        request = Requirement(pending.pop())
        name = canonical(request.name)
        if name not in actual or actual[name] not in request.specifier:
            raise ValueError("independent PEP-508 dependency incompatibility")
        active = seen.get(name, set()) | request.extras
        if name in seen and active == seen[name]:
            continue
        seen[name] = active
        item = by_name[name]
        if environment["python_full_version"] not in SpecifierSet(item.metadata.get("Requires-Python", "")):
            raise ValueError("installed actual Python requirement mismatch")
        for raw in item.requires or []:
            dep = Requirement(raw)
            if dep.marker is None or any(dep.marker.evaluate(environment | {"extra": extra})
                                         for extra in active | {""}):
                pending.append(str(dep))
    if set(seen) != set(actual):
        raise ValueError("installed unreachable distribution")
    sources = {}
    for name, item in by_name.items():
        for entry in item.files or []:
            if str(entry).endswith((".py", ".so", ".pyd")) and ".." not in Path(str(entry)).parts:
                sources[f"{name}/{entry}"] = identity(Path(item.locate_file(entry)))
    write_json(output / f"{group}-installed-tools.json", {
        "schema": 1, "packages": actual,
        "actual_marker_environment": {key: environment[key] for key in TARGET},
        "installed_code": sources, "closure": "PASS (exact equality and independent packaging parser)",
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("download", "installed"))
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--group", choices=("runtime", "build"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    lock = json.loads(Path(__file__).with_name("DEPENDENCY_LOCK.json").read_text())
    if args.action == "download":
        download(lock, args.directory, args.output)
    else:
        installed(lock, args.group, args.output)
