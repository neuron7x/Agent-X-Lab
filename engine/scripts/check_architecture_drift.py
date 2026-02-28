#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


def load_contract(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def extract_sccs(model: dict[str, Any]) -> set[tuple[str, ...]]:
    unknowns = model.get("unknowns", {})
    if isinstance(unknowns, list):
        events = unknowns
    elif isinstance(unknowns, dict):
        events = unknowns.get("events", [])
    else:
        events = []

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


def extract_core_top_k(model: dict[str, Any], k: int = 5) -> set[str]:
    candidates = model.get("metadata", {}).get("core_candidates")
    if not isinstance(candidates, list):
        candidates = model.get("core_candidates", [])
    out: set[str] = set()
    for row in candidates[:k]:
        if isinstance(row, dict) and isinstance(row.get("agent_id"), str):
            out.add(row["agent_id"])
    return out


def render_cycles(cycles: set[tuple[str, ...]]) -> list[str]:
    return [f"- `{' -> '.join(cycle)}`" for cycle in sorted(cycles)]


def maybe_post_pr_comment(report_path: Path) -> None:
    token = os.getenv("GITHUB_TOKEN")
    api = os.getenv("GITHUB_API_URL")
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_num = os.getenv("PR_NUMBER")
    if not all([token, api, repo, pr_num]):
        return

    import urllib.request

    body = report_path.read_text(encoding="utf-8")
    payload = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(
        f"{api}/repos/{repo}/issues/{pr_num}/comments",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            pass
    except Exception as exc:
        print(f"[WARN] Unable to post PR comment: {exc}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--override", type=str, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    has_override = args.override.lower() == "true"
    base_model = load_contract(args.base)
    head_model = load_contract(args.head)

    fatal_modes: list[str] = []
    evidence_log: list[str] = ["# 🛡️ Architecture Drift Report", ""]

    base_sccs = extract_sccs(base_model)
    head_sccs = extract_sccs(head_model)
    new_sccs = head_sccs - base_sccs
    resolved_sccs = base_sccs - head_sccs

    if new_sccs:
        fatal_modes.append("NEW_CYCLIC_DEPENDENCY")
        evidence_log.append("## ❌ Fatal: Topological Cycles Introduced")
        evidence_log.extend(render_cycles(new_sccs))
    else:
        evidence_log.append("## ✅ SCC Boundary")
        evidence_log.append("- No new cyclic dependencies detected.")

    if resolved_sccs:
        evidence_log.append("## ✅ Optimization: Topological Cycles Resolved")
        evidence_log.extend(render_cycles(resolved_sccs))

    base_core = extract_core_top_k(base_model)
    head_core = extract_core_top_k(head_model)
    displaced_core = sorted(base_core - head_core)
    incoming_core = sorted(head_core - base_core)

    evidence_log.append("## 🧠 Core Transition (Top-5)")
    evidence_log.append(f"- Base: `{sorted(base_core)}`")
    evidence_log.append(f"- Head: `{sorted(head_core)}`")
    if incoming_core:
        evidence_log.append(f"- Incoming: `{incoming_core}`")

    if displaced_core:
        if has_override:
            evidence_log.append("- ⚠️ Override authorized (`architecture-override`).")
            evidence_log.append(f"- Displaced: `{displaced_core}`")
        else:
            fatal_modes.append("UNAUTHORIZED_CORE_DEGRADATION")
            evidence_log.append("## ❌ Fatal: Core Agent Displaced")
            evidence_log.append(f"- Missing from Top-5: `{displaced_core}`")
            evidence_log.append(
                "- *Action Required:* Restore core placement or apply `architecture-override` label."
            )
    else:
        evidence_log.append("- No core degradation detected.")

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

    maybe_post_pr_comment(args.report)

    if fatal_modes:
        print("[FATAL] Architecture Drift Guard failed.", file=sys.stderr)
        for mode in fatal_modes:
            print(f"  - {mode}", file=sys.stderr)
        sys.exit(1)

    print("[PASS] Architecture Drift Guard passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
