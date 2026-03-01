from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .inventory import inventory
from .catalog import validate_catalog
from .vr import run_vr
from .release import build_release
from .util import ensure_dir
from .repo_model import cli as repo_model_cli
from .contract_eval import cli as contract_eval_cli


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
    for flag in ("--config",):
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
    try:
        vr = run_vr(cfg, write_back=False)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 3
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


def main(argv: list[str] | None = None) -> None:
    """Deterministic command entrypoint for inventory/VR/release workflows."""
    argv = _normalize_global_flags(argv or sys.argv[1:])
    p = argparse.ArgumentParser(
        prog="sg", description="AgentX Lab governor CLI (deterministic)."
    )
    p.add_argument(
        "--config", default=str(_default_config_path()), help="Path to sg.config.json"
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

    rm = sub.add_parser("repo-model", help="Generate repository architecture model artifact.")
    rm.add_argument("--out", default="engine/artifacts/repo_model/repo_model.json", help="Output path for repository model JSON.")
    rm.add_argument("--contract-out", default="engine/artifacts/repo_model/architecture_contract.jsonl", help="Output path for architecture contract JSONL.")
    rm.add_argument("--no-contract", action="store_true", help="Disable architecture contract output.")
    rm.add_argument("--strict", action="store_true", help="Exit non-zero if dangling edges or parse failures are present.")
    rm.add_argument("--include-glob", action="append", default=[], help="Agent discovery include glob (repeatable).")
    rm.add_argument("--exclude-glob", action="append", default=[], help="Agent discovery exclude glob (repeatable).")
    rm.add_argument("--stdout", action="store_true", help="Print JSON model to stdout.")

    ce = sub.add_parser(
        "contract-eval",
        help="Run deterministic contract evaluator for repository infrastructure contracts.",
    )
    ce.add_argument("--strict", action="store_true", help="Fail on policy warnings.")
    ce.add_argument("--out", default=None, help="Artifact output directory.")
    ce.add_argument("--json", action="store_true", help="Emit strict JSON report to stdout.")
    ce.add_argument("--allow-write", action="store_true", help="Allow evaluator writes outside --out.")
    ce.add_argument("--strict-no-write", action="store_true", help="Enforce zero writes outside --out.")

    args = p.parse_args(argv)
    cfg_path = Path(args.config)

    if args.cmd == "inventory":
        rc = cmd_inventory(cfg_path)
    elif args.cmd == "validate-catalog":
        rc = cmd_validate(cfg_path)
    elif args.cmd == "vr":
        rc = cmd_vr(cfg_path, out_path=Path(args.out), write_back=(not args.no_write))
    elif args.cmd == "release":
        rc = cmd_release(
            cfg_path,
            vr_path=Path(args.vr),
            output_dir=Path(args.output),
        )
    elif args.cmd == "selftest":
        rc = cmd_selftest(cfg_path)
    elif args.cmd == "repo-model":
        rm_args = ["--out", str(args.out)]
        rm_args.extend(["--contract-out", str(args.contract_out)])
        if args.no_contract:
            rm_args.append("--no-contract")
        if args.strict:
            rm_args.append("--strict")
        for g in args.include_glob:
            rm_args.extend(["--include-glob", str(g)])
        for g in args.exclude_glob:
            rm_args.extend(["--exclude-glob", str(g)])
        if args.stdout:
            rm_args.append("--stdout")
        rc = repo_model_cli(rm_args)
    elif args.cmd == "contract-eval":
        ce_args: list[str] = []
        if args.strict:
            ce_args.append("--strict")
        if args.out is not None:
            ce_args.extend(["--out", str(args.out)])
        if args.json:
            ce_args.append("--json")
        if args.allow_write:
            ce_args.append("--allow-write")
        if args.strict_no_write:
            ce_args.append("--strict-no-write")
        rc = contract_eval_cli(ce_args)
    else:
        raise RuntimeError("unreachable")

    raise SystemExit(rc)


if __name__ == "__main__":
    main()
