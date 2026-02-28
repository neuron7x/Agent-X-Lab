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
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], text=True, stderr=subprocess.DEVNULL
        ).strip()
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
        query = urllib.parse.urlencode({"event": "workflow_dispatch", "branch": ref, "per_page": 20})
        payload = _request(repo, token, "GET", f"{endpoint}?{query}")
        runs = payload.get("workflow_runs", []) if isinstance(payload, dict) else []
        matches = [r for r in runs if isinstance(r, dict) and _iso_to_epoch(r.get("created_at")) >= start_epoch - 2]
        if matches:
            matches.sort(key=lambda r: _iso_to_epoch(r.get("created_at")))
            return matches[0]
        time.sleep(10)
    raise TriggerError("timeout waiting for ci-dispatch workflow run")


def _write_sha256_manifest(root: pathlib.Path) -> None:
    rows: list[str] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "sha256sum.txt"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(root).as_posix()}")
    (root / "sha256sum.txt").write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def _run_capture(command: list[str], out_path: pathlib.Path) -> None:
    proc = subprocess.run(command, text=True, capture_output=True, check=False)
    out_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    if proc.returncode != 0:
        raise TriggerError(f"command failed ({proc.returncode}): {' '.join(command)}")


def _build_patch_text() -> str:
    if subprocess.run(["git", "rev-parse", "--verify", "origin/main"], capture_output=True, text=True).returncode == 0:
        proc = subprocess.run(["git", "diff", "--no-color", "origin/main...HEAD"], capture_output=True, text=True)
        if proc.returncode == 0:
            return proc.stdout
    proc = subprocess.run(["git", "show", "--no-color", "HEAD"], capture_output=True, text=True)
    if proc.returncode == 0:
        return proc.stdout
    raise TriggerError("failed to build patch from origin/main...HEAD or git show HEAD")


def _capture_env(out_path: pathlib.Path) -> None:
    py = subprocess.run(["python", "--version"], text=True, capture_output=True, check=False)
    pip = subprocess.run(["python", "-m", "pip", "--version"], text=True, capture_output=True, check=False)
    out_path.write_text((py.stdout or "") + (py.stderr or "") + (pip.stdout or "") + (pip.stderr or ""), encoding="utf-8")
    if py.returncode != 0 or pip.returncode != 0:
        raise TriggerError("failed to capture python/pip env")


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

    commands = [
        f"python tools/ci/trigger_ci_dispatch.py --repo {args.repo} --pr {args.pr} --ref {args.ref}",
        f"POST /repos/{args.repo}/actions/workflows/{WORKFLOW_FILE}/dispatches (inputs: pr_number={args.pr}, dry_run=false)",
        f"GET /repos/{args.repo}/actions/workflows/{WORKFLOW_FILE}/runs?event=workflow_dispatch&branch={args.ref}&per_page=20",
        "python tools/verify_action_pinning.py --workflows .github/workflows",
        "python engine/tools/verify_workflow_hygiene.py --workflows .github/workflows",
        "python --version",
        "python -m pip --version",
        "git diff --no-color origin/main...HEAD (fallback: git show --no-color HEAD)",
    ]
    (proof_root / "commands.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")

    (outputs_dir / "dispatcher_run.txt").write_text(
        f"run_id={run_id}\nrun_url={run_url}\npr={args.pr}\nhead_sha={head_sha}\n",
        encoding="utf-8",
    )

    _run_capture(
        ["python", "tools/verify_action_pinning.py", "--workflows", ".github/workflows"],
        outputs_dir / "verify_action_pinning.txt",
    )
    _run_capture(
        ["python", "engine/tools/verify_workflow_hygiene.py", "--workflows", ".github/workflows"],
        outputs_dir / "verify_workflow_hygiene.txt",
    )
    _capture_env(outputs_dir / "env.txt")

    (patches_dir / "final.patch").write_text(_build_patch_text(), encoding="utf-8")

    _write_sha256_manifest(proof_root)
    print(run_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
