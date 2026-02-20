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


def main(argv: list[str] | None = None) -> None:
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
    else:
        raise RuntimeError("unreachable")

    raise SystemExit(rc)


if __name__ == "__main__":
    main()
