"""Reserve at most two presence attempts for this owner PR; never dump API data."""

import json
import os
import pathlib
import urllib.request


def api(path):
    request = urllib.request.Request(
        "https://api.github.com/repos/WLHsu0827/ibex-fetch-error-observability/" + path,
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


if __name__ == "__main__":
    if os.environ.get("GITHUB_REPOSITORY") != "WLHsu0827/ibex-fetch-error-observability":
        raise SystemExit("owner repository mismatch; STOP")
    event = json.loads(pathlib.Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    branch = event.get("pull_request", {}).get("head", {}).get("ref")
    if branch is None:
        branch = os.environ["GITHUB_REF_NAME"]
    if branch != "wlhsu0827-stock-workload-preparation":
        raise SystemExit("independent owner preparation branch required; STOP")
    run_id = int(os.environ["GITHUB_RUN_ID"])
    attempt = int(os.environ["GITHUB_RUN_ATTEMPT"])
    current = api(f"actions/runs/{run_id}")
    runs = api(f"actions/workflows/{current['workflow_id']}/runs?per_page=100&branch={branch}")
    if runs["total_count"] > 100:
        raise SystemExit("attempt history exceeds bounded query; STOP")
    prior = 0
    for run in runs["workflow_runs"]:
        for number in range(1, run["run_attempt"] + 1):
            if run["id"] == run_id and number == attempt:
                continue
            jobs = api(f"actions/runs/{run['id']}/attempts/{number}/jobs?per_page=100")
            if jobs["total_count"] > 100:
                raise SystemExit("job history exceeds bounded query; STOP")
            for job in jobs["jobs"]:
                prior += sum(step["name"] == "Reserve bounded hosted presence attempt"
                             and step.get("started_at") is not None
                             and step.get("conclusion") != "skipped"
                             for step in job.get("steps", []))
    if prior >= 2:
        raise SystemExit("two hosted tool-install/provenance attempts exhausted; STOP")
    receipt = {"prior_started_attempts": prior, "reserved_attempt": prior + 1,
               "maximum": 2, "run_id": run_id, "run_attempt": attempt,
               "code_head": event.get("pull_request", {}).get("head", {}).get("sha",
                                                                           os.environ["GITHUB_SHA"]),
               "scope": "PREPARATION_ONLY"}
    path = pathlib.Path("stock_profile") / "_receipts" / "tool-attempt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))
