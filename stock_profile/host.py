"""Install fixed public binary distributions in a job-local prefix; metadata ONLY."""

import argparse
import hashlib
import json
import os
import pathlib
import sys
import tarfile
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from bounded import capture, Limits
from config import HERE
from sources import LIMIT, digest

WORK = HERE / "_sources" / "tools"
RECEIPTS = HERE / "_receipts" / "tools"
MAX_RECEIPTS = 16 * 1024**2


def size(directory):
    return sum(p.stat().st_size for p in directory.rglob("*") if p.is_file()
               and not p.is_symlink())


def caps():
    if size(HERE / "_sources") + size(HERE / "_receipts") > LIMIT:
        raise RuntimeError("5 GiB source/artifact increment cap exceeded; STOP")
    if size(HERE / "_receipts") > MAX_RECEIPTS:
        raise RuntimeError("16 MiB selected receipt cap exceeded; STOP")


def download(url, path, expected, expected_bytes):
    if path.exists():
        raise RuntimeError("refusing to overwrite a download")
    total, checksum = 0, hashlib.sha256()
    receipt = {"url": url, "expected_bytes": expected_bytes, "expected_sha256": expected,
               "status": "BLOCKED", "format": "stdlib HTTPS transfer, not a command"}
    try:
        with urllib.request.urlopen(url, timeout=60) as response, path.open("xb") as out:
            while chunk := response.read(65536):
                total += len(chunk)
                if total > expected_bytes:
                    raise RuntimeError("download size cap exceeded; STOP")
                checksum.update(chunk)
                out.write(chunk)
        if total != expected_bytes or checksum.hexdigest() != expected:
            raise RuntimeError("immutable distribution bytes/hash mismatch; STOP")
        receipt["status"] = "HASH_MATCHED"
    except (OSError, RuntimeError) as error:
        receipt["error"] = str(error)
        raise
    finally:
        receipt.update(actual_bytes=total, actual_sha256=checksum.hexdigest())
        (RECEIPTS / ("download-" + path.name + ".json")).write_text(
            json.dumps(receipt, indent=2) + "\n")
    caps()


def probe(name, argv, seconds=30):
    caps()
    remaining = MAX_RECEIPTS - size(HERE / "_receipts")
    if remaining < 4096:
        raise RuntimeError("receipt cap has no room; STOP")
    record, streams = capture(
        argv, RECEIPTS / name, Limits(wall_seconds=seconds,
                                      output_bytes=min(512 * 1024, remaining)),
        resource_limits=False,
    )
    # Preserve stdout/stderr exactly; argv paths use a documented public job prefix.
    record["argv"] = [str(a).replace(str(HERE), "<PACKAGE>")
                      .replace(sys.prefix, "<PYTHON>") for a in argv]
    (RECEIPTS / name / "status.json").write_text(json.dumps(record, indent=2) + "\n")
    caps()
    if record["termination"] != "exit_zero":
        raise RuntimeError(f"{name}: {record['termination']}; original bounded streams retained")
    return streams["stdout"].decode("utf-8", errors="strict").strip()


def install_and_probe():
    deps = json.loads((HERE / "dependencies.json").read_text())
    if (os.environ.get("GITHUB_ACTIONS") != "true" or sys.platform != "linux"
            or sys.version.split()[0] != deps["python"]):
        raise RuntimeError("fixed hosted Linux/Python preparation job only; no local installation")
    gate = json.loads((HERE / "_receipts" / "tool-attempt.json").read_text())
    if gate["reserved_attempt"] not in (1, 2) or gate["scope"] != "PREPARATION_ONLY":
        raise RuntimeError("no bounded hosted presence authorization")
    WORK.mkdir(parents=True, exist_ok=False)
    RECEIPTS.mkdir(parents=True, exist_ok=False)
    probe("python-version", [sys.executable, "-I", "-B", "--version"])
    distributions = []
    debs = WORK / "debs"
    debs.mkdir()
    prefix = WORK / "prefix"
    prefix.mkdir()
    apt = json.loads((HERE / "apt_manifest.json").read_text())
    for name, record in apt["packages"].items():
        path = debs / (name + ".deb")
        download(record["url"], path, record["sha256"], record["bytes"])
        probe("unpack-" + name, ["dpkg-deb", "--extract", str(path), str(prefix)])
        distributions.append(dict(record, name=name, format="deb"))
    # Unpacking is installation into a private prefix, not dpkg system mutation.
    usr = prefix / "usr"
    # The Debian wrapper resolves its sibling binary for version-only invocation.
    # Setting VERILATOR_ROOT to share/ incorrectly redirects its binary lookup.
    if not (usr / "bin" / "verilator_bin").is_file():
        raise RuntimeError("fixed Verilator sibling binary is absent; STOP")
    os.environ.pop("VERILATOR_ROOT", None)
    os.environ["LD_LIBRARY_PATH"] = str(usr / "lib" / "x86_64-linux-gnu")
    make = probe("make-version", [str(usr / "bin" / "make"), "--version"])
    if "GNU Make 4.3" not in make:
        raise RuntimeError("GNU Make version mismatch")
    verilator = probe("verilator-version", [str(usr / "bin" / "verilator"), "--version"])
    if "Verilator 5.020" not in verilator:
        raise RuntimeError("Verilator version mismatch")
    cpp = probe("host-cpp-version", [str(usr / "bin" / "g++-13"), "--version"])
    if "13.2.0" not in cpp:
        raise RuntimeError("host C++ version mismatch")
    wheels = WORK / "wheels"
    wheels.mkdir()
    for record in json.loads((HERE / "wheel_manifest.json").read_text()):
        download(record["url"], wheels / record["filename"], record["sha256"], record["bytes"])
        distributions.append(dict(record, format="wheel"))
    venv = WORK / "venv"
    probe("python-venv", [sys.executable, "-I", "-B", "-m", "venv", str(venv)], 90)
    python = venv / "bin" / "python"
    probe("pip-install", [str(python), "-I", "-B", "-m", "pip", "install",
                         "--disable-pip-version-check", "--no-index", "--find-links", str(wheels),
                         "--only-binary=:all:", "--require-hashes", "--no-compile",
                         "-r", str(HERE / "requirements.lock")], 120)
    # Do not call `fusesoc` entrypoint wrappers or import the owner experiments.
    fuse = probe("fusesoc-version", [str(python), "-I", "-B", "-m", "fusesoc.main", "--version"])
    if fuse != "2.4.3":
        raise RuntimeError("FuseSoC version mismatch")
    packages = json.loads(probe("python-packages", [
        str(python), "-I", "-B", "-c",
        "import importlib.metadata,json; "
        "print(json.dumps({d.metadata['Name']:d.version for d in "
        "importlib.metadata.distributions()},sort_keys=True))",
    ]))
    if packages.get("edalize") != "0.6.0":
        raise RuntimeError("Edalize version mismatch")
    riscv = deps["riscv"]
    archive = WORK / "riscv.tar.gz"
    download(riscv["url"], archive, riscv["sha256"], riscv["bytes"])
    destination = WORK / "riscv"
    destination.mkdir()
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        if sum(m.size for m in members) + size(HERE / "_sources") > LIMIT:
            raise RuntimeError("expanded toolchain exceeds 5 GiB; STOP")
        tar.extractall(destination, filter="data")
    distributions.append(dict(riscv, name="xpack-riscv-none-elf-gcc", format="tar.gz"))
    roots = list(destination.iterdir())
    if len(roots) != 1:
        raise RuntimeError("unexpected fixed toolchain layout")
    gcc = roots[0] / "bin" / "riscv-none-elf-gcc"
    version = probe("riscv-version", [str(gcc), "--version"])
    if "14.2.0" not in version:
        raise RuntimeError("RISC-V GCC version mismatch")
    target = probe("riscv-target", [str(gcc), "-dumpmachine"])
    if target != riscv["target"]:
        raise RuntimeError("RISC-V target mismatch")
    multilibs = probe("riscv-multilib", [str(gcc), "-print-multi-lib"])
    flags = ["-march=rv32im_zicsr", "-mabi=ilp32"]
    multidir = probe("riscv-selected-multidir", [str(gcc), *flags, "-print-multi-directory"])
    selected_rows = [row.split(";", 1) for row in multilibs.splitlines()
                     if row.split(";", 1)[0] == multidir]
    if (len(selected_rows) != 1 or len(selected_rows[0]) != 2
            or "mabi=ilp32" not in selected_rows[0][1].split("@")
            or "@march=rv32" not in selected_rows[0][1]):
        raise RuntimeError("no explicit RV32/ilp32 library metadata selection; STOP, no default fallback")
    probe("riscv-target-options", [str(gcc), *flags, "-Q", "--help=target"])
    probe("riscv-sysroot", [str(gcc), "-print-sysroot"])
    libraries = {}
    for name in ("libm.a", "libc.a", "libgcc.a"):
        answer = probe("riscv-" + name, [str(gcc), *flags, "-print-file-name=" + name])
        path = pathlib.Path(answer)
        if not path.is_file() or not path.resolve().is_relative_to(roots[0].resolve()):
            raise RuntimeError(f"selected {name} absent or outside fixed toolchain; STOP")
        libraries[name] = {
            "selection": path.resolve().relative_to(roots[0]).as_posix(),
            "bytes": path.stat().st_size, "sha256": digest(path.read_bytes()),
            "qualification": "NOT_VERIFIED",
        }
    selected = {}
    for directory in (usr / "bin", roots[0] / "bin"):
        for name in ("make", "verilator", "verilator_bin", "g++-13", "riscv-none-elf-gcc"):
            path = directory / name
            if path.is_file():
                selected[name] = digest(path.read_bytes())
    selected["python"] = digest(pathlib.Path(sys.executable).read_bytes())
    selected["requirements.lock"] = digest((HERE / "requirements.lock").read_bytes())
    for name in ("libelf.so", "libsystemc.so", "libz.so"):
        path = usr / "lib" / "x86_64-linux-gnu" / name
        if not path.is_file():
            raise RuntimeError(f"fixed preparation library absent: {name}")
        selected[name] = digest(path.read_bytes())
    receipt = {
        "scope": "PREPARATION_ONLY", "presence_provenance": "PROBED",
        "attempt": gate, "distributions": distributions, "selected_executable_sha256": selected,
        "libraries": libraries, "selected_multidir": multidir,
        "selected_multilib_options": selected_rows[0][1],
        "host_runtime": "GitHub Ubuntu image shared libraries; NOT a hermetic qualified model",
        "hdl_binding": "NOT_VERIFIED", "abi": "NOT_VERIFIED", "isa_execution": "NOT_VERIFIED",
        "timing": "NOT_VERIFIED", "calibration": "NOT_VERIFIED", "ppa": "NOT_VERIFIED",
        "cpu_program_compile_run": "NOT_AUTHORIZED",
    }
    caps()
    (RECEIPTS / "presence.json").write_text(json.dumps(receipt, indent=2) + "\n")
    caps()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["PREPARATION_ONLY"], required=True)
    parser.parse_args()
    try:
        install_and_probe()
    except (OSError, RuntimeError, ValueError) as error:
        HERE.joinpath("_receipts").mkdir(exist_ok=True)
        failure = {"scope": "PREPARATION_ONLY", "presence_provenance": "BLOCKED",
                   "error": str(error), "cpu_program_compile_run": "NOT_AUTHORIZED"}
        (HERE / "_receipts" / "tool-failure.json").write_text(json.dumps(failure, indent=2) + "\n")
        raise SystemExit(str(error))
