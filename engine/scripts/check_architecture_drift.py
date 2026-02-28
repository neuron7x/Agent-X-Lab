#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_contract(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_sccs(model: dict[str, Any]) -> set[tuple[str, ...]]:
    return {
        tuple(sorted(item["agent_ids"]))
        for item in model.get("unknowns", [])
        if item.get("type") == "ARCHITECTURAL_CYCLE_DETECTED"
    }


def extract_core_top_k(model: dict[str, Any], k: int = 5) -> set[str]:
    candidates = model.get("metadata", {}).get("core_candidates", [])
    return {candidate["agent_id"] for candidate in candidates[:k]}


def render_report(
    base_model: dict[str, Any],
    head_model: dict[str, Any],
    has_override: bool,
) -> tuple[list[str], list[str]]:
    fatal_modes: list[str] = []
    report: list[str] = ["# 🛡️ Architecture Drift Report", ""]

    base_sccs = extract_sccs(base_model)
    head_sccs = extract_sccs(head_model)
    new_sccs = sorted(head_sccs - base_sccs)
    resolved_sccs = sorted(base_sccs - head_sccs)

    report.append("## SCC Delta")
    report.append(f"- Base SCC components (>1): **{len(base_sccs)}**")
    report.append(f"- Head SCC components (>1): **{len(head_sccs)}**")

    if new_sccs:
        fatal_modes.append("NEW_CYCLIC_DEPENDENCY")
        report.append("- ❌ New cycles introduced:")
        for cycle in new_sccs:
            report.append(f"  - `{' -> '.join(cycle)}`")
    else:
        report.append("- ✅ No new cycles introduced.")

    if resolved_sccs:
        report.append("- ✅ Cycles resolved:")
        for cycle in resolved_sccs:
            report.append(f"  - `{' -> '.join(cycle)}`")

    base_core = extract_core_top_k(base_model)
    head_core = extract_core_top_k(head_model)
    displaced_core = sorted(base_core - head_core)

    report.append("")
    report.append("## Core Top-5 Stability")
    report.append(f"- Base Top-5 IDs: `{sorted(base_core)}`")
    report.append(f"- Head Top-5 IDs: `{sorted(head_core)}`")

    if displaced_core:
        if has_override:
            report.append(f"- ⚠️ Displaced core IDs with override: `{displaced_core}`")
        else:
            fatal_modes.append("UNAUTHORIZED_CORE_DEGRADATION")
            report.append(f"- ❌ Displaced core IDs without override: `{displaced_core}`")
            report.append("- Action: restore topology weight or apply `architecture-override` label.")
    else:
        report.append("- ✅ No core displacement detected.")

    base_edges = len(base_model.get("wiring", {}).get("edges", []))
    head_edges = len(head_model.get("wiring", {}).get("edges", []))
    edge_delta = head_edges - base_edges
    report.append("")
    report.append("## Telemetry")
    report.append(f"- Edges (base): **{base_edges}**")
    report.append(f"- Edges (head): **{head_edges}** ({'+' if edge_delta > 0 else ''}{edge_delta})")
    report.append(f"- Override label active: **{has_override}**")

    status = "PASS" if not fatal_modes else "FATAL"
    report.append("")
    report.append(f"## Verdict: **{status}**")

    return fatal_modes, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--override", type=str, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=False)
    args = parser.parse_args()

    has_override = args.override.lower() == "true"
    base_model = load_contract(args.base)
    head_model = load_contract(args.head)

    fatal_modes, report = render_report(base_model, head_model, has_override)

    with args.summary.open("a", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")

    if args.report_out is not None:
        args.report_out.write_text("\n".join(report) + "\n", encoding="utf-8")

    if fatal_modes:
        print("[FATAL] Architecture drift guard failed.", file=sys.stderr)
        for mode in fatal_modes:
            print(f"  - {mode}", file=sys.stderr)
        sys.exit(1)

    print("[PASS] Architecture topology verified.")


if __name__ == "__main__":
    main()
