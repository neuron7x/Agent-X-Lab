from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

from .anchors import sha256_file, sha256_tree
from .state_machine import DeterministicCycle, Evidence
from .strict_json import compute_packet_anchor, load_and_validate
from .system_object import build_system_object, write_system_object
from .autonomous_audit import make_engine, Qa8Mode, QA8_GRADE
from .ad2026.runtime import AD2026Runtime


def cmd_anchor(args: argparse.Namespace) -> int:
    if os.path.isdir(args.path):
        tree_hash, _ = sha256_tree(args.path)
        print(tree_hash)
        return 0
    if os.path.isfile(args.path):
        print(sha256_file(args.path))
        return 0
    print(f"Path not found: {args.path}", file=sys.stderr)
    return 2


def cmd_validate_packet(args: argparse.Namespace) -> int:
    ok, _obj, errs = load_and_validate(args.packet)
    if ok:
        print("OK")
        return 0
    for e in errs:
        print(f"{e.path}: {e.message}", file=sys.stderr)
    return 1


def cmd_loop(args: argparse.Namespace) -> int:
    cycle = DeterministicCycle(fail_closed=True)
    evidence: Dict[str, Any] = {}

    if args.evidence_json:
        with open(args.evidence_json, "r", encoding="utf-8") as f:
            evidence = json.load(f)

    ev = Evidence(
        logs=evidence.get("logs"),
        hash_anchor=evidence.get("hash_anchor"),
        oracle_pass=evidence.get("oracle_pass"),
    )

    # step through to PROVE and evaluate, unless user wants single step
    steps = 1 if args.single_step else 3
    result = None
    for _ in range(steps):
        result = cycle.step(ev)

    assert result is not None
    out = {
        "next_state": result.next_state.value,
        "violated": [{"name": i.name, "rule": i.rule, "severity": i.severity} for i in result.violated],
        "notes": result.notes,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["next_state"] != "HALT" else 1



def cmd_packet_anchor(args: argparse.Namespace) -> int:
    with open(args.packet, "r", encoding="utf-8") as f:
        obj = json.load(f)
    print(compute_packet_anchor(obj))
    return 0


def cmd_build_system_object(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    config_path = os.path.abspath(args.config)
    obj = build_system_object(root, config_path)
    write_system_object(args.out, obj)
    print(obj.system_anchor)
    return 0


def cmd_qa8_watch(args: argparse.Namespace) -> int:
    engine = make_engine(args.root, args.qa8_config)
    engine.load_baseline()
    interval = float(args.interval)
    max_cycles = int(args.max_cycles) if args.max_cycles else None
    print(f"[QA8] Starting autonomous audit watch — interval={interval}s  grade={QA8_GRADE}", flush=True)
    engine.watch(interval_sec=interval, max_cycles=max_cycles)
    return 0


def cmd_qa8_heal(args: argparse.Namespace) -> int:
    engine = make_engine(args.root, args.qa8_config)
    engine.load_baseline()
    status = engine.run_cycle()
    print(json.dumps(status.as_dict(), indent=2, ensure_ascii=False))
    return 0 if status.mode not in (Qa8Mode.HALT, Qa8Mode.ALERT) else 1


def cmd_qa8_status(args: argparse.Namespace) -> int:
    root = os.path.abspath(args.root)
    status_path = os.path.join(root, "qa8_state", "QA8_STATUS.json")
    if not os.path.isfile(status_path):
        print(json.dumps({"error": "QA8_STATUS.json not found. Run qa8-heal first."}))
        return 1
    with open(status_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_ad2026_init(args: argparse.Namespace) -> int:
    """Bootstrap AD-2026 runtime, run T0-T7 checklist, write status."""
    root = os.path.abspath(args.root)
    runtime = AD2026Runtime.bootstrap(root=root, agent_id=args.agent_id)
    telemetry = runtime.run_telemetry_checklist()
    status = runtime.status()
    print(json.dumps({
        "ad2026_status": status,
        "telemetry": {k: v["status"] for k, v in telemetry["checks"].items()},
        "execution_ready": telemetry["execution_ready"],
        "autonomy_status": telemetry["autonomy_status"],
    }, indent=2, ensure_ascii=False))
    return 0 if telemetry["execution_ready"] else 1


def cmd_ad2026_status(args: argparse.Namespace) -> int:
    """Print AD2026_STATUS.json."""
    root = os.path.abspath(args.root)
    status_path = os.path.join(root, "ad2026_state", "AD2026_STATUS.json")
    if not os.path.exists(status_path):
        print(json.dumps({"error": "AD2026_STATUS.json not found. Run ad2026-init first."}))
        return 1
    with open(status_path) as f:
        print(f.read())
    return 0


def cmd_ad2026_gate_run(args: argparse.Namespace) -> int:
    """Run full G6-G11 gate pipeline on a minimal SPS."""
    import uuid
    from .ad2026.typed_plan import SPS, TypedAction, ActionType
    root = os.path.abspath(args.root)
    runtime = AD2026Runtime.bootstrap(root=root, agent_id=args.agent_id)
    runtime.run_telemetry_checklist()

    sps = SPS(sps_id=f"GATE-RUN-{uuid.uuid4().hex[:8]}", agent_id=args.agent_id, utc="")
    import datetime as _dt
    sps.utc = _dt.datetime.now(tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sps.add(TypedAction(
        action_id="GR-001",
        action_type=ActionType.CHECKPOINT,
        preconditions=["ad2026_gate_run"],
        postconditions=["checkpoint_complete"],
        invariants_touched=["DETERMINISM-01"],
        rollback_action_id="NOOP",
        evidence_refs=["§REF:LOG#gate-run-smoke#" + "0"*64],
    ))
    sps.add(TypedAction(
        action_id="GR-002",
        action_type=ActionType.EMIT_PB,
        preconditions=["checkpoint_complete"],
        postconditions=["pb_emitted"],
        invariants_touched=[],
        rollback_action_id="NOOP",
    ))

    result = runtime.execute_sps(sps)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["execution_allowed"] else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="udgs")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("anchor", help="Compute SHA-256 anchor for file or directory")
    pa.add_argument("path")
    pa.set_defaults(fn=cmd_anchor)

    pv = sub.add_parser("validate-packet", help="Validate STRICT_JSON FAIL_PACKET bundle")
    pv.add_argument("packet")
    pv.set_defaults(fn=cmd_validate_packet)

    pp = sub.add_parser("packet-anchor", help="Compute deterministic SHA256_ANCHOR for a STRICT_JSON packet")
    pp.add_argument("packet")
    pp.set_defaults(fn=cmd_packet_anchor)

    pl = sub.add_parser("loop", help="Run deterministic loop gates (fail-closed)")
    pl.add_argument("--evidence-json", default=None, help="JSON with keys: logs, hash_anchor, oracle_pass")
    pl.add_argument("--single-step", action="store_true")
    pl.set_defaults(fn=cmd_loop)

    ps = sub.add_parser("build-system-object", help="Build SYSTEM_OBJECT.json from config + file anchors")
    ps.add_argument("--root", default=".")
    ps.add_argument("--config", default="system/udgs.config.json")
    ps.add_argument("--out", default="SYSTEM_OBJECT.json")
    ps.set_defaults(fn=cmd_build_system_object)

    # QA8 commands
    pw = sub.add_parser("qa8-watch", help="Start QA8 autonomous audit watch daemon")
    pw.add_argument("--root", default=".")
    pw.add_argument("--qa8-config", default=None)
    pw.add_argument("--interval", default=30, help="Watch interval in seconds (default: 30)")
    pw.add_argument("--max-cycles", default=None, help="Stop after N cycles (default: infinite)")
    pw.set_defaults(fn=cmd_qa8_watch)

    ph = sub.add_parser("qa8-heal", help="Run one QA8 autonomous audit + heal cycle")
    ph.add_argument("--root", default=".")
    ph.add_argument("--qa8-config", default=None)
    ph.set_defaults(fn=cmd_qa8_heal)

    pqs = sub.add_parser("qa8-status", help="Print current QA8_STATUS.json")
    pqs.add_argument("--root", default=".")
    pqs.set_defaults(fn=cmd_qa8_status)

    # AD-2026 commands
    pai = sub.add_parser("ad2026-init", help="Bootstrap AD-2026 runtime and run T0-T7 checklist")
    pai.add_argument("--root", default=".")
    pai.add_argument("--agent-id", default="AXL-AGENT-01")
    pai.set_defaults(fn=cmd_ad2026_init)

    pas = sub.add_parser("ad2026-status", help="Print AD2026_STATUS.json")
    pas.add_argument("--root", default=".")
    pas.set_defaults(fn=cmd_ad2026_status)

    pag = sub.add_parser("ad2026-gate-run", help="Run G6-G11 gate pipeline smoke test")
    pag.add_argument("--root", default=".")
    pag.add_argument("--agent-id", default="AXL-AGENT-01")
    pag.set_defaults(fn=cmd_ad2026_gate_run)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
