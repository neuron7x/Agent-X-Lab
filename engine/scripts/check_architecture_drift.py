#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPORT_MARKER = "<!-- architecture-drift-report -->"




def default_contract() -> dict[str, Any]:
    return {
        "wiring": {"edges": []},
        "metadata": {"core_candidates": []},
        "unknowns": {"events": [], "dangling_edges": []},
    }


def ensure_contract_file(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_contract()), encoding="utf-8")

def load_contract(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_contract(model: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(model.get("wiring"), dict):
        errors.append(f"{label}: missing object 'wiring'")
    elif not isinstance(model["wiring"].get("edges", []), list):
        errors.append(f"{label}: 'wiring.edges' must be a list")

    unknowns = model.get("unknowns")
    if not isinstance(unknowns, dict):
        errors.append(f"{label}: missing object 'unknowns'")
    else:
        if "events" in unknowns and not isinstance(unknowns.get("events"), list):
            errors.append(f"{label}: 'unknowns.events' must be a list")
        if "dangling_edges" in unknowns and not isinstance(
            unknowns.get("dangling_edges"), list
        ):
            errors.append(f"{label}: 'unknowns.dangling_edges' must be a list")

    core_candidates = model.get("metadata", {}).get("core_candidates")
    if core_candidates is None:
        core_candidates = model.get("core_candidates")
    if not isinstance(core_candidates, list):
        errors.append(f"{label}: missing list 'metadata.core_candidates' or 'core_candidates'")

    return errors


def extract_sccs(model: dict[str, Any]) -> set[tuple[str, ...]]:
    unknowns = model.get("unknowns", {})
    events = unknowns.get("events", []) if isinstance(unknowns, dict) else []

    out: set[tuple[str, ...]] = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("type") != "ARCHITECTURAL_CYCLE_DETECTED":
            continue
        ids = event.get("agent_ids", [])
        if isinstance(ids, list) and len(ids) > 1:
            out.add(tuple(sorted(str(item) for item in ids)))
    return out


def extract_core_candidates(model: dict[str, Any]) -> list[str]:
    candidates = model.get("metadata", {}).get("core_candidates")
    if not isinstance(candidates, list):
        candidates = model.get("core_candidates", [])

    out: list[str] = []
    for row in candidates:
        if isinstance(row, dict) and isinstance(row.get("agent_id"), str):
            out.append(row["agent_id"])
    return out


def top_k_core(model: dict[str, Any], k: int | None) -> set[str]:
    candidates = extract_core_candidates(model)
    if k is None:
        inferred = model.get("core_candidates_count")
        if isinstance(inferred, int) and inferred > 0:
            k = min(25, inferred)
        else:
            k = min(25, max(5, len(candidates))) if candidates else 5
    return set(candidates[:k])


def extract_dangling_edges(model: dict[str, Any]) -> set[tuple[str, str, str]]:
    unknowns = model.get("unknowns", {})
    rows = unknowns.get("dangling_edges", []) if isinstance(unknowns, dict) else []
    out: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        src = row.get("from_path")
        dst = row.get("to_path")
        et = row.get("edge_type")
        if isinstance(src, str) and isinstance(dst, str) and isinstance(et, str):
            out.add((src, dst, et))
    return out


def _github_request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else None


def upsert_pr_comment(report_text: str) -> None:
    token = os.getenv("GITHUB_TOKEN")
    api = os.getenv("GITHUB_API_URL")
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_num = os.getenv("PR_NUMBER")
    if not all([token, api, repo, pr_num]):
        return

    issue_comments_url = f"{api}/repos/{repo}/issues/{pr_num}/comments"
    try:
        comments = _github_request("GET", issue_comments_url, token)
        body = f"{REPORT_MARKER}\n{report_text}"
        existing = None
        if isinstance(comments, list):
            for comment in comments:
                if isinstance(comment, dict) and REPORT_MARKER in str(comment.get("body", "")):
                    existing = comment
                    break

        if existing and isinstance(existing.get("id"), int):
            _github_request(
                "PATCH",
                f"{api}/repos/{repo}/issues/comments/{existing['id']}",
                token,
                payload={"body": body},
            )
        else:
            _github_request("POST", issue_comments_url, token, payload={"body": body})
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        print(f"[WARN] Unable to upsert PR comment: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--core-k", type=int, default=5)
    parser.add_argument("--override", action="store_true")
    args = parser.parse_args()

    ensure_contract_file(args.base)
    ensure_contract_file(args.head)

    base_model = load_contract(args.base)
    head_model = load_contract(args.head)

    fatal_modes: list[str] = []
    evidence_log: list[str] = [REPORT_MARKER, "# 🛡️ Architecture Drift Report", ""]

    schema_errors = validate_contract(base_model, "base") + validate_contract(head_model, "head")
    if schema_errors:
        fatal_modes.append("INVALID_CONTRACT_SCHEMA")
        evidence_log.append("## ❌ Fatal: Contract Schema Validation Failed")
        for err in schema_errors:
            evidence_log.append(f"- {err}")

    base_sccs = extract_sccs(base_model)
    head_sccs = extract_sccs(head_model)
    new_sccs = head_sccs - base_sccs
    resolved_sccs = base_sccs - head_sccs

    if new_sccs:
        fatal_modes.append("NEW_CYCLIC_DEPENDENCY")
        evidence_log.append("## ❌ Fatal: Topological Cycles Introduced")
        for cycle in sorted(new_sccs):
            evidence_log.append(f"- `{' -> '.join(cycle)}`")
    else:
        evidence_log.append("## ✅ SCC Boundary")
        evidence_log.append("- No new cyclic dependencies detected.")

    if resolved_sccs:
        evidence_log.append("## ✅ Optimization: Topological Cycles Resolved")
        for cycle in sorted(resolved_sccs):
            evidence_log.append(f"- `{' -> '.join(cycle)}`")

    base_core = top_k_core(base_model, args.core_k)
    head_core = top_k_core(head_model, args.core_k)
    displaced_core = sorted(base_core - head_core)

    evidence_log.append(f"## 🧠 Core Transition (Top-{args.core_k})")
    evidence_log.append(f"- Base: `{sorted(base_core)}`")
    evidence_log.append(f"- Head: `{sorted(head_core)}`")

    if displaced_core:
        if args.override:
            evidence_log.append("- ⚠️ Override authorized (`architecture-override`).")
            evidence_log.append(f"- Displaced: `{displaced_core}`")
        else:
            fatal_modes.append("UNAUTHORIZED_CORE_DEGRADATION")
            evidence_log.append("## ❌ Fatal: Core Agent Displaced")
            evidence_log.append(f"- Missing from Top-k: `{displaced_core}`")
    else:
        evidence_log.append("- No core degradation detected.")

    base_dangling = extract_dangling_edges(base_model)
    head_dangling = extract_dangling_edges(head_model)
    new_dangling = head_dangling - base_dangling
    if new_dangling:
        if args.override:
            evidence_log.append("## ⚠️ Warning: New Dangling Edges (Override Authorized)")
        else:
            evidence_log.append("## ❌ Fatal: New Dangling Edges Detected")
            fatal_modes.append("NEW_DANGLING_EDGES")
        for src, dst, edge_type in sorted(new_dangling):
            evidence_log.append(f"- `{src} --[{edge_type}]--> {dst}`")

    base_edges = len(base_model.get("wiring", {}).get("edges", []))
    head_edges = len(head_model.get("wiring", {}).get("edges", []))
    edge_delta = head_edges - base_edges
    evidence_log.append("## 📊 Telemetry")
    evidence_log.append(f"- **Edges (Base):** {base_edges}")
    evidence_log.append(f"- **Edges (Head):** {head_edges} ({'+' if edge_delta > 0 else ''}{edge_delta})")

    report = "\n".join(evidence_log) + "\n"
    args.report.write_text(report, encoding="utf-8")
    with args.summary.open("a", encoding="utf-8") as fh:
        fh.write(report)

    upsert_pr_comment(report)

    if fatal_modes:
        print("[FATAL] Architecture Drift Guard failed.", file=sys.stderr)
        for mode in fatal_modes:
            print(f"  - {mode}", file=sys.stderr)
        sys.exit(1)

    print("[PASS] Architecture Drift Guard passed.")


if __name__ == "__main__":
    main()
