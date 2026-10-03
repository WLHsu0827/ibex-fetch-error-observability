# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Stdlib public-metadata lock generation; no installation or source execution."""

from __future__ import annotations

import argparse
import ast
from functools import lru_cache
import json
from pathlib import Path
import re
import urllib.request

from .process import identity, write_json

ROOT = Path(__file__).resolve().parent
TARGET = {
    "python_version": "3.12", "python_full_version": "3.12.3", "sys_platform": "linux",
    "platform_system": "Linux", "platform_machine": "x86_64",
    "platform_python_implementation": "CPython", "implementation_name": "cpython",
    "implementation_version": "3.12.3", "os_name": "posix",
}


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def version(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+)*", value):
        raise ValueError(f"unsupported non-release version {value}")
    return tuple(map(int, value.split(".")))


def satisfies(value: str, spec: str) -> bool:
    for part in spec.strip(" ()").split(","):
        if not part.strip():
            continue
        match = re.fullmatch(r"\s*(==|!=|>=|<=|>|<|~=)\s*(\d+(?:\.\d+)*(?:\.\*)?)\s*", part)
        if not match:
            raise ValueError(f"unsupported version constraint {part}")
        op, required = match.groups()
        if required.endswith(".*"):
            equal = value == required[:-2] or value.startswith(required[:-1])
            if op not in ("==", "!="):
                raise ValueError("unsupported wildcard operator")
            result = equal if op == "==" else not equal
        else:
            left, right = version(value), version(required)
            size = max(len(left), len(right))
            left, right = left + (0,) * (size - len(left)), right + (0,) * (size - len(right))
            if op == "~=":
                prefix = version(required)[:-1]
                result = left >= right and version(value)[:len(prefix)] == prefix
            else:
                result = {"==": left == right, "!=": left != right, ">=": left >= right,
                          "<=": left <= right, ">": left > right, "<": left < right}[op]
        if not result:
            return False
    return True


def marker(expression: str, extra: str = "") -> bool:
    environment = TARGET | {"extra": extra}

    def evaluate(node: ast.AST) -> object:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in environment:
            return environment[node.id]
        if isinstance(node, ast.BoolOp):
            values = [bool(evaluate(item)) for item in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right, op = str(evaluate(node.left)), str(evaluate(node.comparators[0])), node.ops[0]
            operators = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
                         ast.Gt: ">", ast.GtE: ">="}
            if isinstance(node.left, ast.Name) and node.left.id in (
                "python_version", "python_full_version", "implementation_version"
            ) and type(op) in operators:
                return satisfies(left, operators[type(op)] + right)
            if isinstance(op, ast.In):
                return left in right
            if isinstance(op, ast.NotIn):
                return left not in right
            if isinstance(op, ast.Eq):
                return left == right
            if isinstance(op, ast.NotEq):
                return left != right
        raise ValueError(f"unsupported dependency marker {expression}")

    return bool(evaluate(ast.parse(expression, mode="eval")))


def requirement(text: str, extras: set[str]) -> tuple[str, str, set[str]] | None:
    body, _, condition = text.partition(";")
    if condition and not any(marker(condition.strip(), extra) for extra in extras | {""}):
        return None
    match = re.fullmatch(r"\s*([A-Za-z0-9_.-]+)(?:\[([A-Za-z0-9_,.-]+)\])?\s*(.*?)\s*", body)
    if not match:
        raise ValueError(f"unsupported dependency requirement {text}")
    name, requested_extras, spec = match.groups()
    return canonical(name), spec.strip(" ()"), set((requested_extras or "").split(",")) - {""}


@lru_cache(maxsize=None)
def public_metadata(name: str, release: str = "") -> dict[str, object]:
    suffix = f"/{release}" if release else ""
    with urllib.request.urlopen(f"https://pypi.org/pypi/{name}{suffix}/json", timeout=30) as stream:
        return json.load(stream)


def compatible_wheel(filename: str) -> bool:
    if filename.endswith(("-py3-none-any.whl", "-py2.py3-none-any.whl")):
        return True
    match = re.search(r"-(cp\d+)-(cp312|abi3)-(.+)\.whl$", filename)
    if not match or not filename.endswith("x86_64.whl"):
        return False
    interpreter, abi, platform = match.groups()
    if abi == "cp312" and interpreter != "cp312":
        return False
    if abi == "abi3" and int(interpreter[2:]) > 312:
        return False
    floors = re.findall(r"manylinux_(\d+)_(\d+)", platform)
    return bool(floors) and any((int(a), int(b)) <= (2, 39) for a, b in floors)


def curated(name: str, release: str, retained: dict[str, object] | None = None) -> dict[str, object]:
    data = public_metadata(name, release)
    info = data["info"]
    if not satisfies(TARGET["python_full_version"], info.get("requires_python") or ""):
        raise ValueError(f"Python-incompatible distribution {name}=={release}")
    if retained:
        url = retained["download_info"]["url"]
        artifact = next(item for item in data["urls"] if item["url"] == url)
        if artifact["digests"]["sha256"] != retained["download_info"]["archive_info"]["hashes"]["sha256"]:
            raise ValueError("retained/public artifact hash disagreement")
    else:
        choices = [item for item in data["urls"] if compatible_wheel(item["filename"]) and not item["yanked"]]
        if not choices:
            raise ValueError(f"no compatible wheel for {name}=={release}")
        artifact = sorted(choices, key=lambda item: item["filename"])[0]
    if artifact["packagetype"] == "bdist_wheel" and not compatible_wheel(artifact["filename"]):
        raise ValueError("retained wheel incompatible with target")
    deps = info.get("requires_dist") or []
    provenance = f"https://pypi.org/pypi/{name}/{release}/json"
    if name == "okonomiyaki":
        # Legacy PyPI JSON omits Requires-Dist; the pinned public setup.py supplies it.
        deps = ["attrs>=16.1.0", "jsonschema>=2.5.1", "six>=1.9.0", "zipfile2>=0.0.12"]
        provenance = "https://github.com/enthought/okonomiyaki/blob/v0.17.1/setup.py"
    licenses = [item for item in info.get("classifiers", []) if item.startswith("License ::")]
    return {
        "name": name, "version": release, "requires_python": info.get("requires_python") or "",
        "requires_dist": deps, "metadata_provenance": provenance,
        "license_expression": info.get("license_expression"), "license_classifiers": licenses,
        "artifact": {"filename": artifact["filename"], "url": artifact["url"],
                     "bytes": artifact["size"], "sha256": artifact["digests"]["sha256"],
                     "kind": artifact["packagetype"]},
    }


def graph(packages: dict[str, dict[str, object]], roots: list[str]) -> set[str]:
    pending = list(roots)
    visited: dict[str, set[str]] = {}
    while pending:
        name, spec, extras = requirement(pending.pop(), {""})
        if name not in packages or not satisfies(packages[name]["version"], spec):
            raise ValueError(f"missing/incompatible dependency {name}{spec}")
        old = visited.get(name)
        if old is not None and extras <= old:
            continue
        active = (old or set()) | extras
        visited[name] = active
        for dep in packages[name]["requires_dist"]:
            parsed = requirement(dep, active)
            if parsed:
                child, constraint, child_extras = parsed
                pending.append(child + ("[" + ",".join(sorted(child_extras)) + "]" if child_extras else "")
                               + constraint)
    return set(visited)


def validate(lock: dict[str, object]) -> None:
    if lock["schema"] != 1 or lock["target"] != TARGET:
        raise ValueError("unknown dependency target/schema")
    for group in lock["groups"].values():
        packages = group["packages"]
        if any(name != canonical(name) or name != item["name"] for name, item in packages.items()):
            raise ValueError("noncanonical/duplicate distribution identity")
        if graph(packages, group["roots"]) != set(packages):
            raise ValueError("unreachable/unpinned dependency closure")
        for item in packages.values():
            if not satisfies(TARGET["python_full_version"], item["requires_python"]):
                raise ValueError("Python version incompatibility")
            artifact = item["artifact"]
            if not re.fullmatch("[0-9a-f]{64}", artifact["sha256"]) or artifact["bytes"] <= 0:
                raise ValueError("invalid artifact identity")
            if artifact["kind"] == "bdist_wheel" and not compatible_wheel(artifact["filename"]):
                raise ValueError("incompatible locked wheel")
            if artifact["kind"] != "bdist_wheel" and item["name"] != "jsonschema2md":
                raise ValueError("unlocked source-build backend")


def create() -> None:
    report_path = ROOT / "evidence" / "run-37039019400" / "pip-install.json"
    report = json.loads(report_path.read_text())
    runtime = {canonical(item["name"]): curated(canonical(item["name"]), item["version"], item)
               for item in report["packages"]}
    runtime["pip"] = curated("pip", "25.3")
    roots = [f"{name}=={item['version']}" for name, item in runtime.items()
             if name in ("pip", "packaging", "fusesoc", "mako")]
    build_roots = ["pip==25.3", "poetry-core==2.2.1", "poetry-dynamic-versioning[plugin]==1.9.1",
                   "poetry==2.2.1", "babel==2.17.0"]
    build: dict[str, dict[str, object]] = {}
    pending = list(build_roots)
    extras_seen: dict[str, set[str]] = {}
    while pending:
        name, constraint, extras = requirement(pending.pop(), {""})
        if name in build:
            if not satisfies(build[name]["version"], constraint):
                raise ValueError(f"build resolver conflict: {name}{constraint}; pin explicitly")
        else:
            candidates = [release for release in public_metadata(name)["releases"]
                          if re.fullmatch(r"\d+(?:\.\d+)*", release) and satisfies(release, constraint)]
            for release in sorted(candidates, key=version, reverse=True):
                data = public_metadata(name, release)
                if not satisfies(TARGET["python_full_version"], data["info"].get("requires_python") or ""):
                    continue
                if any(compatible_wheel(item["filename"]) and not item["yanked"] for item in data["urls"]):
                    build[name] = curated(name, release)
                    break
            else:
                raise ValueError(f"no locked compatible build artifact: {name}")
        if name in extras_seen and extras <= extras_seen[name]:
            continue
        active = extras_seen.get(name, set()) | extras
        extras_seen[name] = active
        for dependency in build[name]["requires_dist"]:
            parsed = requirement(dependency, active)
            if parsed:
                child, spec, child_extras = parsed
                pending.append(child + ("[" + ",".join(sorted(child_extras)) + "]" if child_extras else "")
                               + spec)
    lock = {
        "schema": 1, "target": TARGET, "retained_report": identity(report_path),
        "groups": {"runtime": {"roots": roots, "packages": runtime},
                   "build": {"roots": build_roots, "packages": build}},
        "source_build": {
            "name": "jsonschema2md", "version": "1.7.0",
            "public_pyproject": "https://github.com/sbrunner/jsonschema2md/blob/1.7.0/pyproject.toml",
            "requires": ["poetry-core>=1.0.0", "poetry-dynamic-versioning[plugin]>=0.19.0",
                         "poetry-dynamic-versioning", "babel==2.17.0"],
            "backend": "poetry.core.masonry.api",
            "policy": "Separate fully locked build venv, no isolation downloads; runtime retains Babel 2.18.0.",
        },
    }
    validate(lock)
    graph(build, lock["source_build"]["requires"])
    write_json(ROOT / "DEPENDENCY_LOCK.json", lock)
    for group, filename in (("runtime", "requirements.txt"), ("build", "build-requirements.txt")):
        with (ROOT / filename).open("w", encoding="ascii", newline="\n") as stream:
            stream.write("# SPDX-License-Identifier: Apache-2.0\n# Copyright 2026 Wei-Lun Hsu\n")
            for name, item in sorted(lock["groups"][group]["packages"].items()):
                stream.write(f"{name}=={item['version']} --hash=sha256:{item['artifact']['sha256']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    args = parser.parse_args()
    if args.create:
        create()
    else:
        validate(json.loads((ROOT / "DEPENDENCY_LOCK.json").read_text()))
        print("NEXTPC_DEPENDENCY_LOCK_PASS")
