"""Fail-closed original ceiling and one separately authorized tool-only slot."""

import argparse
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lock_tools import check_exact_requirements

LEGACY_STEP = "Reserve bounded hosted presence attempt"
EXTENSION_STEP = "Reserve tool-only extension slot 1"
LABEL = "stock-profile-tool-only-extension-1"


def check_extension_identities():
    approval_path = HERE / "tool_extension_approval.json"
    approval = json.loads(approval_path.read_bytes())
    if (approval["slot"] != "tool-only-extension-1"
            or approval["scope"] != "PREPARATION_ONLY"
            or approval["additional_presence_attempts"] != 1
            or approval["original_attempt_limit"] != 2
            or approval["cpu_program_hdl_compile_run"] != "NOT_AUTHORIZED"
            or approval["accepted_baseline_head"] != "3af2c0433d1c91c46cecc37ad470f74aed757eca"
            or approval["label"] != LABEL
            or (approval["job_minutes"], approval["workers"],
                approval["source_artifact_increment_bytes"],
                approval["aggregate_selected_publication_bytes"])
            != (20, 1, 5 * 1024**3, 16 * 1024**2)
            or set(approval["canonical_lf_git_file_sha256"])
            != {"source_manifest.json", "config.json", "dependencies.json",
                "requirements.lock", "wheel_manifest.json", "apt_manifest.json"}):
        raise RuntimeError("invalid extension approval; STOP")
    for name, expected in approval["canonical_lf_git_file_sha256"].items():
        data = (HERE / name).read_bytes().replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError(f"accepted immutable identity changed: {name}; STOP")
    wheels = json.loads((HERE / "wheel_manifest.json").read_bytes())
    check_exact_requirements(wheels)
    expected_lock = ["# CPython 3.12 / Ubuntu 24.04 amd64; wheels only, no source builds."]
    expected_lock.extend(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}"
                         for r in wheels)
    if (HERE / "requirements.lock").read_text().splitlines() != expected_lock:
        raise RuntimeError("wheel/requirements lock mismatch; STOP")
    return hashlib.sha256(approval_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def reservation(mode, run_attempt, prior_legacy, prior_extension):
    if run_attempt != 1:
        raise RuntimeError("reruns cannot reserve or install tools; STOP")
    if mode == "original":
        if prior_legacy >= 2 or prior_extension:
            raise RuntimeError("original two-attempt ceiling exhausted; STOP")
        return prior_legacy + 1
    if mode != "extension-1" or prior_legacy != 2 or prior_extension != 0:
        raise RuntimeError("unique extension slot unavailable or history mismatch; STOP")
    return 1


def started_reservations(jobs):
    counts = {LEGACY_STEP: 0, EXTENSION_STEP: 0}
    for job in jobs:
        for step in job.get("steps", []):
            if (step["name"] in counts and step.get("started_at") is not None
                    and step.get("conclusion") != "skipped"):
                counts[step["name"]] += 1
    return counts


def api(path):
    request = urllib.request.Request(
        "https://api.github.com/repos/WLHsu0827/ibex-fetch-error-observability/" + path,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def run_gate(slot):
    if os.environ.get("GITHUB_REPOSITORY") != "WLHsu0827/ibex-fetch-error-observability":
        raise SystemExit("owner repository mismatch; STOP")
    event = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    branch = event.get("pull_request", {}).get("head", {}).get("ref")
    if branch is None:
        branch = os.environ["GITHUB_REF_NAME"]
    if branch != "wlhsu0827-stock-workload-preparation":
        raise SystemExit("independent owner preparation branch required; STOP")
    if (slot == "extension-1"
            and (os.environ.get("GITHUB_EVENT_NAME") != "pull_request"
                 or event.get("action") != "labeled"
                 or event.get("label", {}).get("name") != LABEL
                 or event.get("number") != 4
                 or event["pull_request"]["head"]["repo"]["full_name"]
                 != os.environ["GITHUB_REPOSITORY"])):
        raise SystemExit("extension requires the explicit owner PR4 label event; STOP")
    run_id = int(os.environ["GITHUB_RUN_ID"])
    attempt = int(os.environ["GITHUB_RUN_ATTEMPT"])
    current = api(f"actions/runs/{run_id}")
    runs = api(f"actions/workflows/{current['workflow_id']}/runs?per_page=100&branch={branch}")
    if runs["total_count"] > 100:
        raise SystemExit("attempt history exceeds bounded query; STOP")
    prior = {LEGACY_STEP: 0, EXTENSION_STEP: 0}
    for run in runs["workflow_runs"]:
        for number in range(1, run["run_attempt"] + 1):
            if run["id"] == run_id and number == attempt:
                continue
            jobs = api(f"actions/runs/{run['id']}/attempts/{number}/jobs?per_page=100")
            if jobs["total_count"] > 100:
                raise SystemExit("job history exceeds bounded query; STOP")
            counts = started_reservations(jobs["jobs"])
            for name in prior:
                prior[name] += counts[name]
    receipt = {"prior_original_reservations": prior[LEGACY_STEP],
               "prior_extension_reservations": prior[EXTENSION_STEP],
               "slot": slot, "authorized": False,
               "original_maximum": 2, "extension_maximum": 1,
               "run_id": run_id, "run_attempt": attempt,
               "code_head": event.get("pull_request", {}).get("head", {}).get("sha",
                                                                           os.environ["GITHUB_SHA"]),
               "scope": "PREPARATION_ONLY"}
    path = HERE / "_receipts" / "tool-attempt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        receipt["reserved_attempt"] = reservation(slot, attempt, prior[LEGACY_STEP],
                                                  prior[EXTENSION_STEP])
        if slot == "extension-1":
            receipt["approval_sha256"] = check_extension_identities()
        receipt["authorized"] = True
    except (RuntimeError, ValueError, OSError) as error:
        receipt["error"] = str(error)
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        raise SystemExit(str(error))
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    with pathlib.Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write("authorized=true\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", choices=("original", "extension-1"), default="original")
    run_gate(parser.parse_args().slot)
