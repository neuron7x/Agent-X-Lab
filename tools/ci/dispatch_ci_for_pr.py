#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci.ci_contract import calculate_required, get_changed_files

API_ROOT = "https://api.github.com"
CONTRACT_VERSION = "task4.v2"


class DispatchError(RuntimeError):
    pass


def _iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_epoch(iso_value: str | None) -> float:
    if not iso_value or not isinstance(iso_value, str):
        return 0.0
    try:
        return dt.datetime.strptime(iso_value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        return 0.0


def _parse_bool_strict(value: str) -> bool:
    norm = value.strip().lower()
    if norm == "true":
        return True
    if norm == "false":
        return False
    raise DispatchError(f"invalid --dry-run value: {value}; expected true|false")


def _read_changed_files_file(path: pathlib.Path) -> list[str]:
    if not path.exists():
        raise DispatchError(f"changed-files-file does not exist: {path}")
    if not path.is_file():
        raise DispatchError(f"changed-files-file is not a file: {path}")
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(set(rows))


def _git_output(args: list[str]) -> str:
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _infer_local_head_ref() -> str:
    return _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "HEAD"


def _infer_local_head_sha() -> str:
    return _git_output(["git", "rev-parse", "HEAD"]) or ""


def _workflow_supports_dispatch(workflow_file: str) -> bool:
    workflow_path = REPO_ROOT / ".github" / "workflows" / workflow_file
    if not workflow_path.exists() or not workflow_path.is_file():
        return False
    data = workflow_path.read_text(encoding="utf-8")
    return bool(re.search(r"(?m)^\s*workflow_dispatch\s*:", data))


def _redact_token(text: str, token: str | None) -> str:
    redacted = text
    if token:
        redacted = redacted.replace(token, "[REDACTED_TOKEN]")
        if len(token) >= 8:
            redacted = redacted.replace(token[:8], "[REDACTED_TOKEN_PREFIX]")
            redacted = redacted.replace(token[-8:], "[REDACTED_TOKEN_SUFFIX]")
    return redacted


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
        body = json.dumps(payload, sort_keys=True).encode("utf-8") if payload is not None else None

        backoff = 1.0
        for attempt in range(1, 8):
            req = urllib.request.Request(url, headers=self.headers, method=method, data=body)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read().decode("utf-8")
                    self.trace.append(f"{method} {endpoint} -> {resp.status}")
                    return json.loads(data) if data else {}
            except urllib.error.HTTPError as exc:
                self.trace.append(f"{method} {endpoint} -> {exc.code}")
                if exc.code in (401, 403):
                    raise DispatchError(
                        f"GitHub API denied {method} {endpoint} ({exc.code}); token missing or insufficient permissions"
                    ) from exc
                if exc.code in (403, 429) and attempt < 7:
                    wait_s = _retry_wait(exc.headers, backoff)
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


def _resolve_run_for_workflow(
    client: GitHubClient,
    workflow_file: str,
    head_sha: str,
    start_epoch: float,
    deadline_epoch: float,
    poll_interval_seconds: int,
) -> dict | None:
    endpoint = f"actions/workflows/{workflow_file}/runs"
    query = urllib.parse.urlencode({"event": "workflow_dispatch", "per_page": 20})

    while time.time() < deadline_epoch:
        data = client.request("GET", f"{endpoint}?{query}")
        runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
        matches: list[dict] = []
        for run in runs:
            if not isinstance(run, dict):
                continue
            if run.get("head_sha") != head_sha:
                continue
            created_epoch = _to_epoch(run.get("created_at"))
            if created_epoch >= start_epoch - 2:
                matches.append(run)
        if matches:
            matches.sort(key=lambda item: _to_epoch(item.get("created_at")))
            return matches[0]
        time.sleep(poll_interval_seconds)
    return None


def _poll_run_completion(
    client: GitHubClient,
    run_id: int,
    deadline_epoch: float,
    poll_interval_seconds: int,
) -> dict | None:
    endpoint = f"actions/runs/{run_id}"
    while time.time() < deadline_epoch:
        data = client.request("GET", endpoint)
        if not isinstance(data, dict):
            return None
        if data.get("status") == "completed":
            return data
        time.sleep(poll_interval_seconds)
    return None


def _write_summary(evidence: dict) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    lines = [
        "## CI Dispatch Evidence",
        "",
        f"- Repo: `{evidence['repo']}`",
        f"- PR: `{evidence['pr_number']}`",
        f"- Head SHA: `{evidence['head_sha']}`",
        "",
        "| Workflow | Dispatch | Run | Status | Conclusion |",
        "|---|---|---|---|---|",
    ]
    by_wf = {item["workflow_file"]: item for item in evidence.get("resolved_runs", [])}
    for item in evidence.get("dispatched_workflows", []):
        run = by_wf.get(item["workflow_file"], {})
        run_url = run.get("html_url")
        run_text = f"[{run.get('run_id')}]({run_url})" if run_url else "-"
        lines.append(
            f"| `{item['workflow_file']}` | `{item['dispatch_status']}` | {run_text} | `{run.get('status', '-')}` | `{run.get('conclusion', '-')}` |"
        )
    if evidence.get("errors"):
        lines += ["", "### Errors"]
        lines.extend(f"- {err}" for err in evidence["errors"])
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_outputs(out_dir: pathlib.Path, evidence: dict, trace: list[str], changed_files: list[str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "changed_files.txt").write_text(
        "\n".join(changed_files) + ("\n" if changed_files else ""),
        encoding="utf-8",
    )
    (out_dir / "api_trace.log").write_text("\n".join(trace) + ("\n" if trace else ""), encoding="utf-8")
    (out_dir / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary(evidence)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch deterministic CI workflow set for a PR")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--dry-run", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--poll-interval-seconds", type=int, default=8)
    parser.add_argument("--changed-files-file")
    parser.add_argument("--head-ref")
    parser.add_argument("--head-sha")
    parser.add_argument("--repo")
    args = parser.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    trace: list[str] = []
    errors: list[str] = []
    changed_files: list[str] = []
    dispatched_workflows: list[dict] = []
    resolved_runs: list[dict] = []

    started_at = _iso_now()
    start_epoch = time.time()

    if args.timeout_seconds <= 0:
        raise DispatchError("--timeout-seconds must be > 0")
    if args.poll_interval_seconds <= 0:
        raise DispatchError("--poll-interval-seconds must be > 0")

    deadline_epoch = start_epoch + args.timeout_seconds

    dry_run = _parse_bool_strict(args.dry_run)
    offline_mode = bool(args.changed_files_file)

    repo = args.repo or os.environ.get("GITHUB_REPOSITORY") or "local/local"
    head_ref = args.head_ref or ""
    head_sha = args.head_sha or ""

    evidence = {
        "contract_version": CONTRACT_VERSION,
        "repo": repo,
        "base_repo": repo,
        "pr_number": args.pr,
        "head_ref": head_ref,
        "head_sha": head_sha,
        "started_at_utc": started_at,
        "run_started_at_utc": started_at,
        "dispatched_workflows": dispatched_workflows,
        "resolved_runs": resolved_runs,
        "errors": errors,
    }

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    try:
        if offline_mode:
            changed_files = _read_changed_files_file(pathlib.Path(args.changed_files_file or ""))
            evidence["head_ref"] = head_ref or _infer_local_head_ref()
            evidence["head_sha"] = head_sha or _infer_local_head_sha()
            workflow_map = calculate_required(changed_files)
            for workflow_file, reason in workflow_map.items():
                dispatched_workflows.append(
                    {
                        "workflow_file": workflow_file,
                        "reason": reason,
                        "dispatch_status": "SKIP_OFFLINE",
                        "dispatch_ref": evidence["head_ref"],
                    }
                )
            if not dry_run:
                errors.append("offline mode requires --dry-run true")
        else:
            if not token:
                raise DispatchError("missing token; set GITHUB_TOKEN or GH_TOKEN")
            client = GitHubClient(token, repo, trace)
            pr_data = client.request("GET", f"pulls/{args.pr}")
            if not isinstance(pr_data, dict):
                raise DispatchError("unexpected PR response payload")

            base_repo = ((pr_data.get("base") or {}).get("repo") or {}).get("full_name")
            head_repo = ((pr_data.get("head") or {}).get("repo") or {}).get("full_name")
            pr_head_ref = (pr_data.get("head") or {}).get("ref")
            pr_head_sha = (pr_data.get("head") or {}).get("sha")

            evidence["base_repo"] = str(base_repo or repo)
            evidence["head_ref"] = str(pr_head_ref or "")
            evidence["head_sha"] = str(pr_head_sha or "")

            if not base_repo or not head_repo or not pr_head_ref or not pr_head_sha:
                raise DispatchError("PR payload missing base/head repository metadata")
            if head_repo != base_repo:
                raise DispatchError(f"fork PRs are not allowed: base={base_repo} head={head_repo}")

            changed_files = get_changed_files(token, repo, args.pr)
            workflow_map = calculate_required(changed_files)

            for workflow_file, reason in workflow_map.items():
                dispatch_entry = {
                    "workflow_file": workflow_file,
                    "reason": reason,
                    "dispatch_status": "SKIP_DRY_RUN" if dry_run else "PENDING",
                    "dispatch_ref": pr_head_ref,
                }
                if not _workflow_supports_dispatch(workflow_file):
                    dispatch_entry["dispatch_status"] = "SKIP_UNSUPPORTED"
                    errors.append(
                        f"unsupported workflow target: {workflow_file} (missing workflow_dispatch or file not found)"
                    )
                    dispatched_workflows.append(dispatch_entry)
                    continue
                try:
                    if not dry_run:
                        client.request("POST", f"actions/workflows/{workflow_file}/dispatches", {"ref": pr_head_ref})
                        dispatch_entry["dispatch_status"] = "DISPATCHED"
                except Exception as exc:  # noqa: BLE001
                    dispatch_entry["dispatch_status"] = "DISPATCH_FAILED"
                    errors.append(_redact_token(f"dispatch failure for {workflow_file}: {exc}", token))
                dispatched_workflows.append(dispatch_entry)

            if not dry_run:
                for item in dispatched_workflows:
                    wf = item["workflow_file"]
                    if item["dispatch_status"] != "DISPATCHED":
                        continue

                    run = _resolve_run_for_workflow(
                        client=client,
                        workflow_file=wf,
                        head_sha=str(pr_head_sha),
                        start_epoch=start_epoch,
                        deadline_epoch=deadline_epoch,
                        poll_interval_seconds=args.poll_interval_seconds,
                    )
                    if run is None:
                        errors.append(
                            f"resolve timeout for workflow_file={wf} head_sha={pr_head_sha} started_at={started_at}"
                        )
                        continue

                    run_id = run.get("id")
                    if not isinstance(run_id, int):
                        errors.append(f"resolved run missing numeric id for workflow_file={wf}")
                        continue

                    completed = _poll_run_completion(
                        client,
                        run_id,
                        deadline_epoch,
                        args.poll_interval_seconds,
                    )
                    if completed is None:
                        errors.append(f"completion timeout for workflow_file={wf} run_id={run_id}")
                        status = run.get("status")
                        conclusion = run.get("conclusion")
                    else:
                        status = completed.get("status")
                        conclusion = completed.get("conclusion")

                    final_head_sha = (completed or run).get("head_sha")
                    if final_head_sha != pr_head_sha:
                        errors.append(
                            f"head_sha mismatch for workflow_file={wf} run_id={run_id}: expected={pr_head_sha} actual={final_head_sha}"
                        )

                    resolved_runs.append(
                        {
                            "workflow_file": wf,
                            "run_id": run_id,
                            "html_url": (completed or run).get("html_url"),
                            "head_sha": final_head_sha,
                            "status": status,
                            "conclusion": conclusion,
                            "created_at": (completed or run).get("created_at"),
                        }
                    )

                dispatched_count = sum(1 for item in dispatched_workflows if item["dispatch_status"] == "DISPATCHED")
                if len(resolved_runs) < dispatched_count:
                    errors.append(
                        f"resolved run count mismatch: dispatched={dispatched_count} resolved={len(resolved_runs)}"
                    )

    except Exception as exc:  # noqa: BLE001
        errors.append(_redact_token(str(exc), token))

    _write_outputs(out_dir, evidence, trace, changed_files)

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
