#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

API_ROOT = "https://api.github.com"
WORKFLOW_FILE = "ci-dispatch.yml"


class TriggerError(RuntimeError):
    pass


def _repo_from_remote() -> str | None:
    try:
        remote = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None

    if remote.startswith("git@github.com:"):
        slug = remote.split(":", 1)[1]
    elif "github.com/" in remote:
        slug = remote.split("github.com/", 1)[1]
    else:
        return None
    if slug.endswith(".git"):
        slug = slug[:-4]
    return slug.strip("/") or None


def _request(repo: str, token: str, method: str, endpoint: str, payload: dict | None = None) -> object:
    url = f"{API_ROOT}/repos/{repo}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "axl-trigger-ci-dispatch",
    }
    body = json.dumps(payload).encode("utf-8") if payload is not None else None

    backoff = 1
    for attempt in range(1, 8):
        req = urllib.request.Request(url, headers=headers, method=method, data=body)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data) if data else {}
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise TriggerError(f"GitHub API denied {method} {endpoint} ({exc.code})") from exc
            if exc.code in (403, 429) and attempt < 7:
                retry_after = exc.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait_s = max(1, int(retry_after))
                else:
                    reset = exc.headers.get("X-RateLimit-Reset")
                    wait_s = max(1, int(reset) - int(time.time())) if reset and reset.isdigit() else backoff
                time.sleep(wait_s)
                backoff *= 2
                continue
            raise TriggerError(f"GitHub API error {exc.code} for {method} {endpoint}") from exc


def _iso_to_epoch(text: str | None) -> float:
    if not text:
        return 0.0
    return dt.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


def _find_dispatch_run(repo: str, token: str, ref: str, start_epoch: float) -> dict:
    deadline = time.time() + 600
    endpoint = f"actions/workflows/{WORKFLOW_FILE}/runs"
    while time.time() < deadline:
        query = urllib.parse.urlencode({"event": "workflow_dispatch", "branch": ref, "per_page": 10})
        payload = _request(repo, token, "GET", f"{endpoint}?{query}")
        runs = payload.get("workflow_runs", []) if isinstance(payload, dict) else []
        for run in runs:
            if not isinstance(run, dict):
                continue
            if _iso_to_epoch(run.get("created_at")) >= start_epoch - 2:
                return run
        time.sleep(10)
    raise TriggerError("timeout waiting for ci-dispatch workflow run")


def _write_sha256_manifest(root: pathlib.Path) -> None:
    rows: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "sha256sum.txt"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(root).as_posix()}")
    (root / "sha256sum.txt").write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Trigger CI dispatch workflow and create build_proof bundle")
    parser.add_argument("--repo", default=_repo_from_remote())
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--ref", default="main")
    args = parser.parse_args()

    if not args.repo:
        raise SystemExit("ERROR: --repo required (or configure origin remote)")

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("ERROR: missing token; set GH_TOKEN or GITHUB_TOKEN")

    start_epoch = time.time()
    _request(
        args.repo,
        token,
        "POST",
        f"actions/workflows/{WORKFLOW_FILE}/dispatches",
        {"ref": args.ref, "inputs": {"pr_number": str(args.pr), "dry_run": "false"}},
    )

    run = _find_dispatch_run(args.repo, token, args.ref, start_epoch)
    run_id = str(run.get("id"))
    run_url = str(run.get("html_url"))

    pr_data = _request(args.repo, token, "GET", f"pulls/{args.pr}")
    head_sha = ((pr_data.get("head") or {}).get("sha")) if isinstance(pr_data, dict) else ""

    proof_root = pathlib.Path("build_proof") / f"task4_ci_dispatch_{run_id}"
    outputs_dir = proof_root / "outputs"
    patches_dir = proof_root / "patches"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    patches_dir.mkdir(parents=True, exist_ok=True)

    (outputs_dir / "dispatcher_run.txt").write_text(
        f"run_id={run_id}\nrun_url={run_url}\npr={args.pr}\nhead_sha={head_sha}\n",
        encoding="utf-8",
    )

    patch_text = subprocess.check_output(["git", "diff", "--", "."], text=True)
    (patches_dir / "final.patch").write_text(patch_text, encoding="utf-8")

    _write_sha256_manifest(proof_root)
    print(run_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
