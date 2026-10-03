# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""Complete paginated API history and separate immutable authorization epochs."""

from __future__ import annotations

import json
import re

FIELDS = {"id", "head_sha", "display_title", "event", "run_attempt", "status", "conclusion"}


def parse_history(text: str) -> list[dict[str, object]]:
    decoder, pages = json.JSONDecoder(), []
    while text.strip():
        page, end = decoder.raw_decode(text.lstrip())
        pages.append(page)
        text = text.lstrip()[end:]
    if not pages:
        raise ValueError("empty API history, not an empty attempt journal")
    records, counts = [], []
    for page in pages:
        if not isinstance(page, dict) or set(page) != {"total_count", "runs"} or (
            type(page["total_count"]) is not int or page["total_count"] < 1
            or not isinstance(page["runs"], list) or not page["runs"]
        ):
            raise ValueError("malformed/error API history page")
        counts.append(page["total_count"])
        for item in page["runs"]:
            if not isinstance(item, dict) or set(item) != FIELDS or (
                type(item["id"]) is not int or item["id"] <= 0
                or type(item["run_attempt"]) is not int or item["run_attempt"] < 1
                or not isinstance(item["head_sha"], str)
                or not re.fullmatch(r"[0-9a-f]{40}", item["head_sha"])
                or not isinstance(item["display_title"], str)
                or not isinstance(item["event"], str) or not isinstance(item["status"], str)
                or item["conclusion"] is not None and not isinstance(item["conclusion"], str)
            ):
                raise ValueError("malformed API run identity")
            records.append(item)
    if any(count != counts[0] for count in counts) or len(records) != counts[0]:
        raise ValueError("incomplete or concurrently changing paginated API history")
    if len({item["id"] for item in records}) != len(records):
        raise ValueError("duplicate run across history pages")
    return records


def qualify_history(
    records: list[dict[str, object]], authorization: dict[str, object], legacy_identity: str,
    current_id: str, source_sha: str, mode: str, preparation_attempt: int, preparation_run: str,
) -> list[dict[str, object]]:
    if any(item["run_attempt"] != 1 for item in records):
        raise ValueError("workflow rerun is unauthorized")
    def epoch(identity: str) -> list[dict[str, object]]:
        result = [item for item in records if item["event"] == "workflow_dispatch"
                  and item["display_title"].endswith(" " + identity)]
        for item in result:
            if item["run_attempt"] != 1:
                raise ValueError("epoch run_attempt > 1 is unauthorized")
            match = re.fullmatch(r"RVFI next-PC (prepare|pair) p([0-4]) " + re.escape(identity),
                                 item["display_title"])
            if not match or match[1] == "prepare" and match[2] == "0" or (
                match and match[1] == "pair" and match[2] != "0"
            ):
                raise ValueError("malformed authorized dispatch title")
        return result

    if "closed_epochs" in authorization:
        if [item["identity"] for item in authorization["closed_epochs"]] != [
            legacy_identity, "WLHsu0827-2026-10-03-rvfi-nextpc-recovery-1"
        ]:
            raise ValueError("closed authorization epochs omitted or changed")
        for closed in authorization["closed_epochs"]:
            actual = epoch(closed["identity"])
            expected = closed["runs"]
            if len(actual) != len(expected):
                raise ValueError("closed epoch dispatch count changed")
            for frozen in expected:
                found = [item for item in actual if item["id"] == frozen["id"]]
                title = f"RVFI next-PC {frozen['mode']} p{frozen['preparation_attempt']} {closed['identity']}"
                if len(found) != 1 or found[0]["display_title"] != title or (
                    found[0]["head_sha"] != frozen["head_sha"]
                    or found[0]["conclusion"] != frozen["conclusion"] or found[0]["status"] != "completed"
                ):
                    raise ValueError("closed epoch immutable run identity changed")
    else:
        old = epoch(legacy_identity)
        if len(old) != 2 or any(" pair " in item["display_title"] for item in old) or (
            sorted(item["display_title"].split()[3] for item in old) != ["p1", "p2"]
        ):
            raise ValueError("original exhausted epoch history changed")
    authorized = epoch(authorization["identity"])
    prepares = [item for item in authorized if " prepare " in item["display_title"]]
    pairs = [item for item in authorized if " pair " in item["display_title"]]
    if len(prepares) > authorization["max_preparations"] or len(pairs) > authorization["max_pairs"]:
        raise ValueError("authorization attempt budget exhausted")
    current = [item for item in authorized if str(item["id"]) == current_id]
    if len(current) != 1 or current[0]["head_sha"] != source_sha:
        raise ValueError("current dispatch missing/duplicated or source mismatch")
    if current[0]["display_title"] != (
        f"RVFI next-PC {mode} p{preparation_attempt} {authorization['identity']}"
    ):
        raise ValueError("current dispatch/input mode or counter mismatch")
    sequence = sorted(int(item["display_title"].split()[3][1:]) for item in prepares)
    if sequence != list(range(1, len(prepares) + 1)):
        raise ValueError("preparation counter duplicated/skipped/reset")
    if mode == "prepare":
        if pairs or preparation_attempt != len(prepares) or not 1 <= len(prepares) <= 4:
            raise ValueError("invalid recovery preparation sequence")
    else:
        previous = [item for item in prepares if str(item["id"]) == preparation_run]
        if len(previous) != 1 or previous[0]["conclusion"] != "success" or (
            previous[0]["head_sha"] != source_sha or len(pairs) != 1 or preparation_attempt != 0
        ):
            raise ValueError("pair requires successful same-source preparation and unique pair dispatch")
    return authorized
