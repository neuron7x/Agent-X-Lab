#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List

API_ROOT = "https://api.github.com"


def _github_get_json(token: str, url: str) -> object:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "axl-ci-contract",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    backoff = 1.0
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429) and attempt < 5:
                retry_after = exc.headers.get("Retry-After")
                reset = exc.headers.get("X-RateLimit-Reset")
                if retry_after and retry_after.isdigit():
                    wait_s = max(1, int(retry_after))
                elif reset and reset.isdigit():
                    wait_s = max(1, int(reset) - int(time.time()))
                else:
                    wait_s = int(backoff)
                    backoff *= 2
                time.sleep(wait_s)
                continue
            raise


def get_changed_files(token: str, repo: str, pr_number: int) -> List[str]:
    files: list[str] = []
    page = 1
    while True:
        endpoint = f"{API_ROOT}/repos/{repo}/pulls/{pr_number}/files"
        query = urllib.parse.urlencode({"per_page": 100, "page": page})
        data = _github_get_json(token, f"{endpoint}?{query}")
        if not isinstance(data, list):
            raise RuntimeError("unexpected pulls/files API response")
        if not data:
            break
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("filename"), str):
                files.append(item["filename"])
        if len(data) < 100:
            break
        page += 1
    return sorted(set(files))


def calculate_required(paths: List[str]) -> Dict[str, str]:
    if paths and all(p.startswith("docs/") or p.startswith("build_proof/") or p.endswith(".md") for p in paths):
        return {}

    required: dict[str, str] = {}

    def add(workflow: str, reason: str) -> None:
        required[workflow] = reason

    def any_path(predicate) -> bool:
        return any(predicate(path) for path in paths)

    if any_path(lambda p: p.startswith(".github/")):
        add("workflow-hygiene.yml", "workflow_changes")
        add("action-pin-audit.yml", "workflow_changes")

    if any_path(lambda p: p.startswith("engine/")):
        add("engine-drift-guard.yml", "engine_changes")
        add("python-verify.yml", "engine_changes")

    ui_config_suffixes = (
        "config.ts",
        "config.js",
        "vite.config.ts",
        "playwright.config.ts",
        "tsconfig.json",
        "package.json",
        "package-lock.json",
    )
    if any_path(
        lambda p: p.startswith(("src/", "workers/", "e2e/", "scripts/"))
        or p.endswith(ui_config_suffixes)
    ):
        add("ui-verify.yml", "ui_changes")

    if any_path(lambda p: p.startswith("e2e/") or "playwright" in p.lower()):
        add("ui-e2e.yml", "ui_e2e_relevant")

    if any_path(lambda p: p.startswith(("src/", "workers/"))):
        add("ui-perf.yml", "ui_perf_relevant")

    return dict(sorted(required.items(), key=lambda item: item[0]))
