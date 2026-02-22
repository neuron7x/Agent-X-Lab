from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .catalog import validate_catalog
from .config import load_config
from .inventory import inventory
from .release import build_release
from .util import (
    MetricsEmitter,
    ensure_dir,
    generate_request_id,
    get_request_id,
    log_event,
    set_request_id,
    setup_json_logger,
)
from .vr import run_vr

_LOG = setup_json_logger("exoneural_governor.cli")


def _default_config_path() -> Path:
    # Prefer repo-local default config
    return Path("configs/sg.config.json")


def _normalize_global_flags(argv: list[str]) -> list[str]:
    """Allow global flags after subcommand for compatibility.

    `argparse` only accepts global args before subcommand. We normalize
    `sg vr --config X ...` into `sg --config X vr ...` deterministically.
    """
    if not argv:
        return argv

    out = list(argv)
    for flag in ("--config", "--metrics-out", "--request-id"):
        if flag in out:
            i = out.index(flag)
            if i + 1 < len(out):
                val = out[i + 1]
                del out[i : i + 2]
                out = [flag, val, *out]
    return out


def cmd_inventory(cfg_path: Path) -> int:
    cfg = load_config(cfg_path)
    out_dir = cfg.repo_root / "artifacts" / "reports" / "inventory"
    ensure_dir(out_dir)
    inv = inventory(cfg.repo_root, out_dir)
    print(json.dumps(inv, indent=2, sort_keys=True))
    return 0


def cmd_validate(cfg_path: Path) -> int:
    cfg = load_config(cfg_path)
    rep = validate_catalog(cfg.repo_root)
    print(json.dumps(rep, indent=2, sort_keys=True))
    return 0 if rep.get("ok") else 2


def cmd_vr(cfg_path: Path, out_path: Path, write_back: bool) -> int:
    cfg = load_config(cfg_path)
    vr = run_vr(cfg, write_back=False)
    if write_back:
        target = out_path if out_path.is_absolute() else (cfg.repo_root / out_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(vr, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(vr, indent=2, sort_keys=True))
    return 0 if vr.get("status") == "RUN" else 3


def cmd_release(cfg_path: Path, vr_path: Path, output_dir: Path) -> int:
    cfg = load_config(cfg_path)
    rep = build_release(cfg, vr_path=vr_path, output_dir=output_dir)
    print(json.dumps(rep, indent=2, sort_keys=True))
    return 0


def cmd_selftest(cfg_path: Path) -> int:
    cfg = load_config(cfg_path)
    rep = validate_catalog(cfg.repo_root)
    if not rep.get("ok"):
        print(json.dumps(rep, indent=2, sort_keys=True))
        return 2
    return 0


def _run_command_with_observability(
    *,
    command_name: str,
    fn,
    metrics: MetricsEmitter,
) -> int:
    started = time.perf_counter()
    log_event(_LOG, "cli.command.start", command=command_name)
    try:
        rc = fn()
    except Exception as exc:
        latency_ms = (time.perf_counter() - started) * 1000.0
        log_event(
            _LOG,
            "cli.command.error",
            command=command_name,
            error=str(exc),
            gate_outcome="error",
            latency_ms=round(latency_ms, 3),
        )
        metrics.emit(
            metric="sg.command",
            status="error",
            latency_ms=latency_ms,
            gate_outcome="error",
            error=type(exc).__name__,
        )
        raise

    latency_ms = (time.perf_counter() - started) * 1000.0
    gate_outcome = "success" if rc == 0 else "failure"
    status = "success" if rc == 0 else "error"
    log_event(
        _LOG,
        "cli.command.finish",
        command=command_name,
        gate_outcome=gate_outcome,
        latency_ms=round(latency_ms, 3),
        status=status,
    )
    metrics.emit(
        metric="sg.command",
        status=status,
        latency_ms=latency_ms,
        gate_outcome=gate_outcome,
        error=(None if rc == 0 else f"exit_code={rc}"),
    )
    return rc


def main(argv: list[str] | None = None) -> None:
    argv = _normalize_global_flags(argv or sys.argv[1:])
    p = argparse.ArgumentParser(
        prog="sg", description="AgentX Lab governor CLI (deterministic)."
    )
    p.add_argument(
        "--config", default=str(_default_config_path()), help="Path to sg.config.json"
    )
    p.add_argument(
        "--metrics-out",
        default="artifacts/observability/metrics.jsonl",
        help="Path to JSONL metrics file emitter output.",
    )
    p.add_argument(
        "--request-id",
        default=None,
        help="Correlation/request identifier for all structured logs and metrics.",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inventory", help="Collect deterministic repo inventory.")
    sub.add_parser(
        "validate-catalog",
        help="Fail-closed catalog integrity check (sha256 + indexing).",
    )

    vrp = sub.add_parser("vr", help="Run VR calibration and produce evidence bundle.")
    vrp.add_argument("--out", default="VR.json", help="Path to VR output JSON.")
    vrp.add_argument(
        "--no-write", action="store_true", help="Do not write VR.json back to repo."
    )

    rel = sub.add_parser(
        "release",
        help="Build release zip (includes latest VR evidence when available).",
    )
    rel.add_argument("--vr", default="VR.json", help="Path to VR.json to include.")
    rel.add_argument(
        "--output",
        default="artifacts/release",
        help="Directory for release bundle outputs.",
    )
    sub.add_parser("selftest", help="Lightweight CI self-test (catalog validation).")

    args = p.parse_args(argv)
    cfg_path = Path(args.config)

    req_id = args.request_id or generate_request_id()
    set_request_id(req_id)
    metrics = MetricsEmitter(Path(args.metrics_out))
    log_event(_LOG, "cli.request.context", request_id=get_request_id(), command=args.cmd)

    if args.cmd == "inventory":
        rc = _run_command_with_observability(
            command_name=args.cmd,
            fn=lambda: cmd_inventory(cfg_path),
            metrics=metrics,
        )
    elif args.cmd == "validate-catalog":
        rc = _run_command_with_observability(
            command_name=args.cmd,
            fn=lambda: cmd_validate(cfg_path),
            metrics=metrics,
        )
    elif args.cmd == "vr":
        rc = _run_command_with_observability(
            command_name=args.cmd,
            fn=lambda: cmd_vr(cfg_path, out_path=Path(args.out), write_back=(not args.no_write)),
            metrics=metrics,
        )
    elif args.cmd == "release":
        rc = _run_command_with_observability(
            command_name=args.cmd,
            fn=lambda: cmd_release(
                cfg_path,
                vr_path=Path(args.vr),
                output_dir=Path(args.output),
            ),
            metrics=metrics,
        )
    elif args.cmd == "selftest":
        rc = _run_command_with_observability(
            command_name=args.cmd,
            fn=lambda: cmd_selftest(cfg_path),
            metrics=metrics,
        )
    else:
        raise RuntimeError("unreachable")

    raise SystemExit(rc)


if __name__ == "__main__":
    main()
