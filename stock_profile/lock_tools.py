"""Maintenance-only PyPI metadata sealing; does not install or execute packages."""

import json
import lzma
import pathlib
import re
import urllib.request

PINS = {
    "fusesoc": "2.4.3", "edalize": "0.6.0", "Jinja2": "3.1.6",
    "MarkupSafe": "3.0.3", "pyparsing": "3.2.5", "PyYAML": "6.0.2",
    "simplesat": "0.9.2", "fastjsonschema": "2.21.2", "jsonschema2md": "1.5.2",
    "argcomplete": "3.6.3", "attrs": "25.4.0", "six": "1.17.0",
    "okonomiyaki": "1.4.0", "packaging": "25.0", "jsonschema": "4.25.1",
    "Markdown": "3.7", "jsonschema-specifications": "2025.9.1",
    "referencing": "0.36.2", "rpds-py": "0.27.1", "typing_extensions": "4.15.0",
    "babel": "2.17.0", "zipfile2": "0.0.12", "distro": "1.9.0",
    "pip": "25.0.1",
}


def check_exact_requirements(wheels):
    pins = {re.sub(r"[-_.]", "-", r["name"]).lower(): r["version"] for r in wheels}
    for wheel in wheels:
        for requirement in wheel["requires_dist"] or []:
            if "extra ==" in requirement:
                continue
            match = re.fullmatch(r"([\w.-]+)\s*==\s*([\w.]+)", requirement)
            if match:
                name = re.sub(r"[-_.]", "-", match[1]).lower()
                if pins.get(name) != match[2]:
                    raise ValueError(f"mandatory exact dependency conflict: {requirement}")


if __name__ == "__main__":
    wheels = []
    lines = ["# CPython 3.12 / Ubuntu 24.04 amd64; wheels only, no source builds."]
    for name, version in sorted(PINS.items()):
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        with urllib.request.urlopen(url, timeout=30) as response:
            metadata = json.load(response)
        options = [r for r in metadata["urls"] if r["filename"].endswith(".whl")
                   and ("none-any" in r["filename"]
                        or ("cp312" in r["filename"] and "manylinux" in r["filename"]
                            and "x86_64" in r["filename"]))]
        if not options:
            raise RuntimeError(f"no fixed binary wheel for {name}=={version}; STOP")
        chosen = sorted(options, key=lambda r: r["filename"])[0]
        wheels.append({
            "name": name, "version": version, "metadata_source": url,
            "requires_dist": metadata["info"]["requires_dist"],
            "filename": chosen["filename"], "url": chosen["url"],
            "sha256": chosen["digests"]["sha256"], "bytes": chosen["size"],
        })
        lines.append(f"{name}=={version} --hash=sha256:{chosen['digests']['sha256']}")
    here = pathlib.Path(__file__).resolve().parent
    check_exact_requirements(wheels)
    (here / "requirements.lock").write_text("\n".join(lines) + "\n", newline="\n")
    (here / "wheel_manifest.json").write_text(json.dumps(wheels, indent=2) + "\n", newline="\n")
    dependencies = json.loads((here / "dependencies.json").read_text())
    packages = {}
    indices = []
    import hashlib
    for component in ("main", "universe"):
        url = (dependencies["apt_snapshot"] +
               f"/dists/noble/{component}/binary-amd64/Packages.xz")
        data = urllib.request.urlopen(url, timeout=60).read()
        indices.append({"url": url, "sha256": hashlib.sha256(data).hexdigest()})
        for paragraph in lzma.decompress(data).decode().split("\n\n"):
            fields = dict(line.split(": ", 1) for line in paragraph.splitlines()
                          if ": " in line and not line.startswith(" "))
            name = fields.get("Package")
            if name in dependencies["packages"]:
                if fields["Version"] != dependencies["packages"][name]:
                    raise RuntimeError(f"snapshot version mismatch: {name}")
                packages[name] = {
                    "version": fields["Version"], "sha256": fields["SHA256"],
                    "url": dependencies["apt_snapshot"] + "/" + fields["Filename"],
                    "bytes": int(fields["Size"]), "depends": fields.get("Depends"),
                }
    if set(packages) != set(dependencies["packages"]):
        raise RuntimeError("missing fixed snapshot package; STOP")
    (here / "apt_manifest.json").write_text(
        json.dumps({"indices": indices, "packages": packages}, indent=2) + "\n", newline="\n")
