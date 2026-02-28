#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci.ci_contract import calculate_required, get_changed_files

API_ROOT = "https://api.github.com"


class DispatchError(RuntimeError):
    pass


def _iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_bool(value: str) -> bool:
    norm = (value or "").strip().lower()
    if norm in {"1", "true", "yes", "y"}:
        return True
    if norm in {"0", "false", "no", "n", ""}:
        return False
    raise DispatchError(f"invalid bool value: {value}")


class GitHubClient:
    def __init__(self, token: str, repo: str, trace: list[str]):
        self.repo = repo
        self.trace = trace
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "axl-ci-dispatcher",
        }

    def request(self, method: str, endpoint: str, payload: dict | None = None) -> object:
        url = f"{API_ROOT}/repos/{self.repo}/{endpoint.lstrip('/')}"
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        backoff = 1.0
        for attempt in range(1, 8):
            req = urllib.request.Request(url, headers=self.headers, method=method, data=body)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read().decode("utf-8")
                    self.trace.append(f"{method} {endpoint} -> {resp.status}")
                    if not data:
                        return {}
                    return json.loads(data)
            except urllib.error.HTTPError as exc:
                self.trace.append(f"{method} {endpoint} -> {exc.code}")
                if exc.code in (401, 403):
                    raise DispatchError(f"GitHub API denied {method} {endpoint} ({exc.code}); token missing or insufficient permissions") from exc
                if exc.code in (429,) and attempt < 7:
                    wait_s = _retry_wait(exc.headers, backoff)
                    time.sleep(wait_s)
                    backoff *= 2
                    continue
                if exc.code == 403 and attempt < 7:
                    wait_s = _retry_wait(exc.headers, backoff)
                    if wait_s > 0:
                        time.sleep(wait_s)
                        backoff *= 2
                        continue
                raise DispatchError(f"GitHub API error {exc.code} for {method} {endpoint}") from exc
            except urllib.error.URLError as exc:
                self.trace.append(f"{method} {endpoint} -> URLERROR")
                if attempt == 7:
                    raise DispatchError(f"network error for {method} {endpoint}: {exc.reason}") from exc
                time.sleep(backoff)
                backoff *= 2
        raise DispatchError(f"request exhausted retries: {method} {endpoint}")


def _retry_wait(headers, fallback: float) -> int:
    retry_after = headers.get("Retry-After") if headers else None
    if retry_after and retry_after.isdigit():
        return max(1, int(retry_after))
    reset = headers.get("X-RateLimit-Reset") if headers else None
    if reset and reset.isdigit():
        return max(1, int(reset) - int(time.time()))
    return max(1, int(fallback))


def _find_run_for_workflow(client: GitHubClient, workflow_file: str, branch: str, head_sha: str, start_epoch: float, deadline_epoch: float) -> dict:
    endpoint = f"actions/workflows/{workflow_file}/runs"
    while time.time() < deadline_epoch:
        query = urllib.parse.urlencode({"event": "workflow_dispatch", "branch": branch, "per_page": 10})
        data = client.request("GET", f"{endpoint}?{query}")
        runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
        for run in runs:
            if not isinstance(run, dict):
                continue
            created_at = run.get("created_at")
            created_epoch = 0.0
            if isinstance(created_at, str):
                try:
                    created_epoch = dt.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
                except ValueError:
                    created_epoch = 0.0
            if run.get("head_sha") == head_sha and created_epoch >= start_epoch - 2:
                return run
        time.sleep(10)
    raise DispatchError(f"timeout waiting for workflow run: {workflow_file}")


def _write_summary(evidence: dict) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## CI Dispatch Evidence",
        "",
        f"- PR: `{evidence['pr_number']}`",
        f"- Head SHA: `{evidence['head_sha']}`",
        "",
        "| Workflow | Dispatch | Run | Conclusion |",
        "|---|---|---|---|",
    ]
    resolved_by_wf = {entry["workflow_file"]: entry for entry in evidence.get("resolved_runs", [])}
    for item in evidence.get("dispatched_workflows", []):
        workflow = item["workflow_file"]
        run = resolved_by_wf.get(workflow, {})
        url = run.get("html_url")
        run_text = f"[{run.get('run_id')}]({url})" if url else "-"
        lines.append(f"| `{workflow}` | `{item['dispatch_status']}` | {run_text} | `{run.get('conclusion', '-')}` |")
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch deterministic CI workflow set for a PR")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--dry-run", default="false")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    trace: list[str] = []
    errors: list[str] = []

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("ERROR: missing token; set GITHUB_TOKEN or GH_TOKEN")

    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("ERROR: GITHUB_REPOSITORY is required")

    started_at = _iso_now()
    start_epoch = time.time()
    deadline = start_epoch + 900

    evidence = {
        "base_repo": repo,
        "pr_number": args.pr,
        "head_ref": "",
        "head_sha": "",
        "run_started_at_utc": started_at,
        "dispatched_workflows": [],
        "resolved_runs": [],
        "errors": errors,
    }

    try:
        client = GitHubClient(token, repo, trace)
        pr_data = client.request("GET", f"pulls/{args.pr}")
        if not isinstance(pr_data, dict):
            raise DispatchError("unexpected PR response payload")

        base_repo = ((pr_data.get("base") or {}).get("repo") or {}).get("full_name")
        head_repo = ((pr_data.get("head") or {}).get("repo") or {}).get("full_name")
        head_ref = (pr_data.get("head") or {}).get("ref")
        head_sha = (pr_data.get("head") or {}).get("sha")

        evidence["base_repo"] = str(base_repo or repo)
        evidence["head_ref"] = str(head_ref or "")
        evidence["head_sha"] = str(head_sha or "")

        if not base_repo or not head_repo or not head_ref or not head_sha:
            raise DispatchError("PR payload missing base/head repository metadata")
        if head_repo != base_repo:
            raise DispatchError(f"fork PRs are not allowed: base={base_repo} head={head_repo}")

        changed_files = get_changed_files(token, repo, args.pr)
        (out_dir / "changed_files.txt").write_text("\n".join(changed_files) + ("\n" if changed_files else ""), encoding="utf-8")

        workflow_map = calculate_required(changed_files)
        dry_run = _parse_bool(args.dry_run)

        for workflow_file, reason in workflow_map.items():
            status = "SKIP_DRY_RUN"
            if not dry_run:
                client.request("POST", f"actions/workflows/{workflow_file}/dispatches", {"ref": head_ref})
                status = "DISPATCHED"
            evidence["dispatched_workflows"].append(
                {
                    "workflow_file": workflow_file,
                    "reason": reason,
                    "dispatch_status": status,
                }
            )

        if not dry_run:
            for item in evidence["dispatched_workflows"]:
                wf = item["workflow_file"]
                run = _find_run_for_workflow(client, wf, str(head_ref), str(head_sha), start_epoch, deadline)
                evidence["resolved_runs"].append(
                    {
                        "workflow_file": wf,
                        "run_id": run.get("id"),
                        "html_url": run.get("html_url"),
                        "head_sha": run.get("head_sha"),
                        "status": run.get("status"),
                        "conclusion": run.get("conclusion"),
                    }
                )

    except Exception as exc:  # noqa: BLE001
        message = str(exc).replace(token, "[REDACTED_TOKEN]")
        errors.append(message)

    (out_dir / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "api_trace.log").write_text("\n".join(trace) + ("\n" if trace else ""), encoding="utf-8")
    _write_summary(evidence)

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
