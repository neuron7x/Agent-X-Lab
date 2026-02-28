#!/usr/bin/env python3
"""Generate architecture_contract.jsonl from a System Object JSON.

The output is line-delimited JSON where each line is a strict I/O contract
("promise") for one module/component declared in SYSTEM_OBJECT.json.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def io_contract_by_kind(kind: str) -> Dict[str, Any]:
    """Deterministic hardware-style I/O promises by component kind."""
    contracts: Dict[str, Dict[str, Any]] = {
        "ui": {
            "inputs": [
                "BFF JSON responses",
                "User interaction events",
                "Runtime configuration (VITE_AXL_API_BASE)",
            ],
            "outputs": [
                "Deterministic UI states",
                "Dispatch requests to BFF",
                "No direct api.github.com network traffic",
            ],
            "acceptance_checks": [
                "Build succeeds (npm run build)",
                "UI test suite passes",
                "Fail-closed rate-limit state rendered",
            ],
        },
        "engine": {
            "inputs": [
                "STRICT_JSON packets",
                "System anchor and manifest metadata",
                "Policy and gate configuration",
            ],
            "outputs": [
                "Deterministic gate decisions (G6-G11)",
                "Immutable execution evidence",
                "Append-only execution logs",
            ],
            "acceptance_checks": [
                "Core python tests pass",
                "Replay remains deterministic",
                "Fail-closed on invariant violations",
            ],
        },
        "sdk": {
            "inputs": [
                "Proof bundles and gate outcomes",
                "Role/task orchestration intents",
            ],
            "outputs": [
                "Arbiter decisions",
                "Structured evidence ledgers",
            ],
            "acceptance_checks": [
                "DAO lifebook tests pass",
                "No contract role overlap violations",
            ],
        },
        "legacy": {
            "inputs": [
                "Legacy model/config payloads",
                "Historical evidence references",
            ],
            "outputs": [
                "Backward-compatible snapshots",
                "Legacy-compatible metrics and constraints",
            ],
            "acceptance_checks": [
                "Legacy tests pass",
                "Compatibility surface remains stable",
            ],
        },
        "docs": {
            "inputs": [
                "System protocol and deployment specifications",
                "Security and release policy updates",
            ],
            "outputs": [
                "Normative contracts for operators",
                "Traceable implementation obligations",
            ],
            "acceptance_checks": [
                "Referenced files exist",
                "Contract docs remain internally consistent",
            ],
        },
    }

    default_contract = {
        "inputs": ["Declared module dependencies"],
        "outputs": ["Declared module artifacts"],
        "acceptance_checks": ["Contract completeness check"],
    }
    return contracts.get(kind, default_contract)


def make_rows(system_object: Dict[str, Any], input_file: str) -> List[Dict[str, Any]]:
    config = system_object.get("config", {})
    components = system_object.get("components", {})
    system_anchor = system_object.get("system_anchor", "")

    rows: List[Dict[str, Any]] = []
    for component_id in sorted(components.keys()):
        component = components[component_id]
        kind = str(component.get("kind", "unknown"))
        io_contract = io_contract_by_kind(kind)
        row = {
            "record_type": "architecture_contract",
            "contract_version": "1.0.0",
            "generated_at": now_utc(),
            "source": input_file,
            "system_name": config.get("name"),
            "system_version": config.get("version"),
            "system_anchor": system_anchor,
            "module_id": component_id,
            "module_name": component.get("name"),
            "module_kind": kind,
            "module_path": component.get("path"),
            "module_hash": component.get("hash"),
            "fail_closed": bool(config.get("fail_closed", False)),
            "oracle_required": bool(config.get("oracle_required", False)),
            "promise": {
                "input_contract": io_contract["inputs"],
                "output_contract": io_contract["outputs"],
                "acceptance_checks": io_contract["acceptance_checks"],
                "precision_level": "Welinder-Hardware-Style",
            },
        }
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(REPO_ROOT), help="Repository root")
    ap.add_argument(
        "--input",
        default="SYSTEM_OBJECT.json",
        help="Input System Object JSON path (relative to --root)",
    )
    ap.add_argument(
        "--output",
        default="artifacts/architecture_contract.jsonl",
        help="Output JSONL path (relative to --root)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    input_path = (root / args.input).resolve()
    output_path = (root / args.output).resolve()

    if not input_path.exists():
        print(f"ERROR: input not found: {input_path}")
        return 2

    system_object = load_json(input_path)
    rows = make_rows(system_object, input_path.relative_to(root).as_posix())
    write_jsonl(output_path, rows)

    print("OK")
    print(f"input: {input_path.relative_to(root).as_posix()}")
    print(f"output: {output_path.relative_to(root).as_posix()}")
    print(f"rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
