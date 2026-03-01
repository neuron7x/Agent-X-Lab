from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._exec import ExecResult, pip_cmd, python_module_cmd
from .blame import git_available, in_git_repo
from .repo_model import betweenness_centrality_brandes, pagerank

EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_ERROR = 3


@dataclass
class GateResult:
    gate_id: str
    status: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.gate_id, "status": self.status, "details": self.details}


@dataclass
class EvalContext:
    repo_root: Path
    strict: bool
    json_mode: bool
    out_dir: Path | None
    no_write: bool
    commands: list[ExecResult] = field(default_factory=list)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bounded(items: list[str], n: int = 200) -> dict[str, Any]:
    ordered = sorted(set(items))
    return {"count": len(ordered), "items": ordered[:n]}


def _run_cmd(ctx: EvalContext, name: str, cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> ExecResult:
    from ._exec import run_command

    rec = run_command(name=name, command=cmd, cwd=(cwd or ctx.repo_root), env=env)
    ctx.commands.append(rec)
    return rec


def discover_repo_root(cwd: Path) -> Path:
    from ._exec import run_command

    proc = run_command("repo_root", ["git", "rev-parse", "--show-toplevel"], cwd)
    if proc.returncode != 0:
        raise RuntimeError("unable to discover repo root via git rev-parse")
    return Path(proc.stdout.strip()).resolve()


def validate_repo_model_schema(model: dict[str, Any]) -> tuple[bool, str]:
    required = ["repo_root", "repo_fingerprint", "agents", "edges", "core_candidates", "counts", "unknowns"]
    for key in required:
        if key not in model:
            return False, f"missing key: {key}"
    if not isinstance(model["counts"], dict) or not isinstance(model["counts"].get("core_candidates_count"), int):
        return False, "missing counts.core_candidates_count"
    return True, "ok"


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _gate_put(gates: dict[str, GateResult], gate_id: str, status: str, details: dict[str, Any]) -> None:
    gates[gate_id] = GateResult(gate_id=gate_id, status=status, details=details)


def _collect_versions(ctx: EvalContext) -> tuple[dict[str, Any], bool]:
    import sys

    py = _run_cmd(ctx, "python_version", [sys.executable, "-V"])
    pip = _run_cmd(ctx, "pip_version", pip_cmd("-V"))
    node = _run_cmd(ctx, "node_version", ["node", "-v"])
    npm = _run_cmd(ctx, "npm_version", ["npm", "-v"])
    git = _run_cmd(ctx, "git_version", ["git", "--version"])
    versions = {
        "sys.executable": sys.executable,
        "python_version": (py.stdout or py.stderr).strip() or None,
        "pip_version": (pip.stdout or pip.stderr).strip() or None,
        "node_version": (node.stdout or node.stderr).strip() or None,
        "npm_version": (npm.stdout or npm.stderr).strip() or None,
        "git_version": (git.stdout or git.stderr).strip() or None,
        "os.name": os.name,
        "sys.platform": sys.platform,
    }
    ok = all(versions.get(k) for k in ("sys.executable", "python_version", "pip_version", "node_version", "npm_version", "git_version"))
    return versions, ok


def _git_snapshot(ctx: EvalContext) -> dict[str, Any]:
    status = _run_cmd(ctx, "git_status_porcelain", ["git", "status", "--porcelain=v1", "--untracked-files=all"])
    untracked = _run_cmd(ctx, "git_untracked", ["git", "ls-files", "--others", "--exclude-standard"])
    return {
        "porcelain_text": status.stdout,
        "porcelain_lines": [ln for ln in status.stdout.splitlines() if ln.strip()],
        "untracked_lines": [ln for ln in untracked.stdout.splitlines() if ln.strip()],
    }


def _repo_fingerprint(ctx: EvalContext, label: str) -> str:
    head = _run_cmd(ctx, f"git_head_{label}", ["git", "rev-parse", "HEAD"])
    tree = _run_cmd(ctx, f"git_tree_{label}", ["git", "ls-tree", "-r", "HEAD"])
    status = _run_cmd(ctx, f"git_status_{label}", ["git", "status", "--porcelain=v1", "--untracked-files=no"])
    return _sha256_text(_canonical_json({"head": head.stdout.strip(), "tree": tree.stdout.splitlines(), "porcelain": status.stdout.splitlines()}))


def _porcelain_path(line: str) -> str:
    payload = line[3:] if len(line) > 3 else line
    if " -> " in payload:
        return payload.split(" -> ", 1)[1].strip()
    return payload.strip()


def _is_allowed_path(path: str, out_rel: str | None, repo_root: Path, out_dir: Path | None) -> bool:
    if not out_rel or out_dir is None:
        return False
    candidate = (repo_root / path).resolve()
    out_resolved = out_dir.resolve()
    try:
        candidate.relative_to(out_resolved)
        return True
    except ValueError:
        return False


def _strict_no_write_diff(before: dict[str, Any], after: dict[str, Any], out_rel: str | None, repo_root: Path, out_dir: Path | None) -> dict[str, Any]:
    before_lines = set(before["porcelain_lines"])
    after_lines = set(after["porcelain_lines"])
    added_lines = sorted(after_lines - before_lines)
    removed_lines = sorted(before_lines - after_lines)

    outside_added = sorted([ln for ln in added_lines if not _is_allowed_path(_porcelain_path(ln), out_rel, repo_root, out_dir)])
    outside_removed = sorted([ln for ln in removed_lines if not _is_allowed_path(_porcelain_path(ln), out_rel, repo_root, out_dir)])

    before_untracked = set(before["untracked_lines"])
    after_untracked = set(after["untracked_lines"])
    new_untracked = sorted(after_untracked - before_untracked)
    outside_new_untracked = sorted([p for p in new_untracked if not _is_allowed_path(p, out_rel, repo_root, out_dir)])

    return {
        "outside_porcelain_added": outside_added,
        "outside_porcelain_removed": outside_removed,
        "outside_new_untracked": outside_new_untracked,
    }


def _semantic_signature(model: dict[str, Any], contract_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "counts": model.get("counts", {}),
        "agent_ids": sorted(a.get("agent_id") for a in model.get("agents", []) if isinstance(a, dict) and isinstance(a.get("agent_id"), str)),
        "edges": sorted((e.get("from_id"), e.get("to_id"), e.get("edge_type")) for e in model.get("edges", []) if isinstance(e, dict)),
        "core_ranked": sorted((c.get("agent_id"), c.get("rank")) for c in model.get("core_candidates", []) if isinstance(c, dict)),
        "contract_row_count": len(contract_rows),
    }


def evaluate_contracts(strict: bool, out_path: Path | None, json_mode: bool, no_write: bool = True, repo_root: Path | None = None, engine_root: Path | None = None) -> tuple[int, dict[str, Any]]:
    repo_root = (repo_root.resolve() if repo_root else discover_repo_root(Path.cwd()))
    out_dir = out_path.resolve() if out_path else None
    ctx = EvalContext(repo_root=repo_root, strict=strict, json_mode=json_mode, out_dir=out_dir, no_write=no_write)
    engine_root = engine_root.resolve() if engine_root else (repo_root / "engine")
    gates: dict[str, GateResult] = {}
    warnings: list[dict[str, str]] = []

    if not git_available():
        return EXIT_ERROR, {
            "state": "ERROR",
            "exit_code": EXIT_ERROR,
            "gates": [],
            "failures": [{"gate": "INTERNAL", "reason": "git unavailable"}],
            "warnings": [],
            "artifacts": {"dir": None, "files": []},
        }

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
    temp_root = (out_dir / "_tmp") if out_dir else Path(tempfile.gettempdir()) / "ris_contract_eval_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)

    hermetic_env = {
        "PYTHONPATH": ".",
        "XDG_CACHE_HOME": str(temp_root / "xdg_cache"),
        "PIP_CACHE_DIR": str(temp_root / "pip_cache"),
        "PYTHONPYCACHEPREFIX": str(temp_root / "pycache"),
        "npm_config_cache": str(temp_root / "npm_cache"),
    }
    for key in ("XDG_CACHE_HOME", "PIP_CACHE_DIR", "PYTHONPYCACHEPREFIX", "npm_config_cache"):
        Path(hermetic_env[key]).mkdir(parents=True, exist_ok=True)

    before = _git_snapshot(ctx)
    fp_start = _repo_fingerprint(ctx, "start")
    out_rel = _safe_rel(out_dir, repo_root) if out_dir else None

    versions, versions_ok = _collect_versions(ctx)
    _gate_put(gates, "GATE_A01_ENVIRONMENT_STAMP", "PASS" if versions_ok else "FAIL", {"versions": versions})

    env_stamp = {"versions": versions, "strict": strict, "no_write": no_write, "repo_root": repo_root.as_posix()}
    if out_dir:
        env_text = _canonical_json(env_stamp)
        (out_dir / "env.json").write_text(env_text + "\n", encoding="utf-8")
        (out_dir / "env.sha256").write_text(_sha256_text(env_text) + "\n", encoding="utf-8")
    _gate_put(gates, "GATE_A03_DETERMINISTIC_ENV_STAMP", "PASS", {"sha256": _sha256_text(_canonical_json(env_stamp))})

    run_artifacts: list[tuple[Path, Path]] = []
    with tempfile.TemporaryDirectory(prefix="repo_model_run1_", dir=temp_root) as run1_tmp, tempfile.TemporaryDirectory(prefix="repo_model_run2_", dir=temp_root) as run2_tmp:
        run_artifacts = [
            (Path(run1_tmp) / "repo_model.json", Path(run1_tmp) / "architecture_contract.jsonl"),
            (Path(run2_tmp) / "repo_model.json", Path(run2_tmp) / "architecture_contract.jsonl"),
        ]

        repo_model_ok = True
        for model_path, contract_path in run_artifacts:
            rec = _run_cmd(
                ctx,
                f"repo_model_{model_path.parent.name}",
                python_module_cmd("exoneural_governor", "repo-model", "--out", str(model_path), "--contract-out", str(contract_path)),
                cwd=engine_root,
                env=hermetic_env,
            )
            if rec.returncode != 0:
                repo_model_ok = False
                break

        if not repo_model_ok:
            _gate_put(gates, "GATE_A02_STRICT_NO_WRITE", "FAIL", {"reason": "repo-model execution failed"})
            _gate_put(gates, "GATE_A06_DETERMINISM_SIGNATURE", "FAIL", {"reason": "repo-model execution failed"})
        else:
            m1, c1 = run_artifacts[0]
            m2, c2 = run_artifacts[1]
            model1 = json.loads(m1.read_text(encoding="utf-8"))
            model2 = json.loads(m2.read_text(encoding="utf-8"))
            contract_rows1 = [json.loads(ln) for ln in c1.read_text(encoding="utf-8").splitlines() if ln.strip()]
            contract_rows2 = [json.loads(ln) for ln in c2.read_text(encoding="utf-8").splitlines() if ln.strip()]

            sig1 = _semantic_signature(model1, contract_rows1)
            sig2 = _semantic_signature(model2, contract_rows2)
            sig1_text = _canonical_json(sig1)
            sig2_text = _canonical_json(sig2)
            det_ok = sig1_text == sig2_text

            if out_dir:
                shutil.copy2(m1, out_dir / "repo_model.run1.json")
                shutil.copy2(m2, out_dir / "repo_model.run2.json")
                (out_dir / "signature.run1.json").write_text(sig1_text + "\n", encoding="utf-8")
                (out_dir / "signature.run2.json").write_text(sig2_text + "\n", encoding="utf-8")

            _gate_put(
                gates,
                "GATE_A06_DETERMINISM_SIGNATURE",
                "PASS" if det_ok else "FAIL",
                {
                    "semantic_equal": det_ok,
                    "signature_run1_sha256": _sha256_text(sig1_text),
                    "signature_run2_sha256": _sha256_text(sig2_text),
                    "signature_run1": sig1,
                    "signature_run2": sig2,
                },
            )

            ok_schema, reason = validate_repo_model_schema(model1)
            dangling = model1.get("unknowns", {}).get("dangling_edges", [])
            parse_failures = model1.get("unknowns", {}).get("parse_failures", [])

            comp_status = "PASS"
            if strict and (dangling or parse_failures):
                comp_status = "FAIL"
            elif dangling or parse_failures:
                warnings.append({"code": "DISCOVERY_INCOMPLETE", "message": f"dangling={len(dangling)} parse_failures={len(parse_failures)}"})
            _gate_put(gates, "GATE_B01_AGENT_DISCOVERY_COMPLETENESS", comp_status, {"dangling_edges": len(dangling), "parse_failures": len(parse_failures)})

            dep_edges = [e for e in model1.get("edges", []) if isinstance(e, dict) and e.get("edge_type") in {"IMPORTS_PY", "IMPORTS_JS", "INCLUDES"}]
            _gate_put(gates, "GATE_B02_EDGE_TYPE_COVERAGE_MIN_IMPORTS", "PASS" if len(dep_edges) >= 1 else "FAIL", {"edge_count": len(dep_edges), "minimum": 1})

            agents = [a for a in model1.get("agents", []) if isinstance(a, dict)]
            _gate_put(gates, "GATE_C01_ARCHITECTURE_CONTRACT_JSONL", "PASS" if len(contract_rows1) == len(agents) else "FAIL", {"agents": len(agents), "rows": len(contract_rows1)})

            name_required = {"CLI_SCRIPT", "GITHUB_WORKFLOW", "GITHUB_COMPOSITE_ACTION", "MAKEFILE"}
            missing_names = sorted([str(a.get("path")) for a in agents if a.get("kind") in name_required and not str(a.get("name") or "").strip()])
            _gate_put(gates, "GATE_C02_NAME_RECONSTRUCTION_NON_NULL", "PASS" if not missing_names else "FAIL", {"missing": _bounded(missing_names)})

            iface_fail: list[str] = []
            for a in agents:
                p = a.get("path")
                if not isinstance(p, str):
                    continue
                fp = repo_root / p
                if not fp.exists() or not fp.is_file():
                    continue
                text = fp.read_text(encoding="utf-8", errors="replace")
                inputs = a.get("interface", {}).get("inputs", []) if isinstance(a.get("interface"), dict) else []
                has_parser = fp.suffix in {".py", ".js", ".mjs", ".ts", ".sh", ".bash"} and (
                    "argparse.ArgumentParser(" in text or "@click.option(" in text or "yargs" in text
                )
                if has_parser and not inputs:
                    iface_fail.append(p)
            _gate_put(gates, "GATE_C03_ZERO_SHOT_INTERFACE_EXTRACTION_MINIMUM", "PASS" if not iface_fail else "FAIL", {"missing_inputs": _bounded(iface_fail)})

            policy_fail = bool(strict and (dangling or parse_failures))
            _gate_put(gates, "GATE_D01_POLICY_TIERS_ENFORCED", "FAIL" if policy_fail else "PASS", {"strict": strict})

            fixtures_present = all(
                (repo_root / p).exists()
                for p in [
                    "engine/tests/fixtures/repo_model_fixture_a",
                    "engine/tests/fixtures/repo_model_fixture_b",
                    "engine/tests/fixtures/repo_model_fixture_c",
                    "engine/tests/fixtures/repo_model_fixture_d",
                ]
            )
            _gate_put(gates, "GATE_D02_REGRESSION_FIXTURES_GOLDEN", "PASS" if fixtures_present else "FAIL", {"fixtures_present": fixtures_present})

            ids = sorted([a.get("agent_id") for a in agents if isinstance(a.get("agent_id"), str)])
            edges = [
                (e.get("from_id"), e.get("to_id"))
                for e in model1.get("edges", [])
                if isinstance(e, dict) and isinstance(e.get("from_id"), str) and isinstance(e.get("to_id"), str)
            ]
            pr1 = pagerank(ids, edges)
            bc1 = betweenness_centrality_brandes(ids, edges)
            ids2 = ids + [f"iso_{i}" for i in range(8)]
            pr2 = pagerank(ids2, edges)
            bc2 = betweenness_centrality_brandes(ids2, edges)
            top1 = [k for k, _ in sorted(((k, 0.6 * pr1.get(k, 0.0) + 0.4 * bc1.get(k, 0.0)) for k in ids), key=lambda x: (-x[1], x[0]))[:5]]
            top2 = [k for k, _ in sorted(((k, 0.6 * pr2.get(k, 0.0) + 0.4 * bc2.get(k, 0.0)) for k in ids), key=lambda x: (-x[1], x[0]))[:5]]
            _gate_put(gates, "GATE_E01_CENTRALITY_STABILITY_SANITY", "PASS" if top1 == top2 else "FAIL", {"top5_before": top1, "top5_after": top2})

            blame_missing = [r.get("path") for r in contract_rows1 if r.get("core_rank") is not None and (not isinstance(r.get("blame"), dict) or not r["blame"].get("top_author"))]
            can_git = git_available() and in_git_repo(repo_root)
            _gate_put(
                gates,
                "GATE_E02_BUS_FACTOR_MINIMUM",
                "FAIL" if strict and can_git and blame_missing else "PASS",
                {"git_available": can_git, "missing_blame": _bounded([str(x) for x in blame_missing if isinstance(x, str)]), "schema_ok": ok_schema, "schema_reason": reason},
            )

    fp_end = _repo_fingerprint(ctx, "end")
    if fp_start != fp_end:
        if strict:
            _gate_put(gates, "GATE_A04_REPO_FINGERPRINT_RESCAN", "FAIL", {"start": fp_start, "end": fp_end})
        else:
            warnings.append({"code": "FINGERPRINT_CHANGED", "message": "repository fingerprint changed during evaluation"})
            _gate_put(gates, "GATE_A04_REPO_FINGERPRINT_RESCAN", "WARNING", {"start": fp_start, "end": fp_end})
    else:
        _gate_put(gates, "GATE_A04_REPO_FINGERPRINT_RESCAN", "PASS", {"start": fp_start, "end": fp_end})

    after = _git_snapshot(ctx)
    diff = _strict_no_write_diff(before, after, out_rel, repo_root, out_dir)
    outside_changes = bool(diff["outside_porcelain_added"] or diff["outside_porcelain_removed"] or diff["outside_new_untracked"])
    _gate_put(gates, "GATE_A05_OUTSIDE_OUT_WRITE_CHECK", "FAIL" if (no_write and outside_changes) else "PASS", diff)
    _gate_put(gates, "GATE_A02_STRICT_NO_WRITE", "PASS" if (not no_write or not outside_changes) else "FAIL", {"enabled": no_write, "out_dir": out_dir.as_posix() if out_dir else None})

    ordered_gates = [gates[k].as_dict() for k in sorted(gates)]
    failures = [{"gate": g["id"], "reason": "gate failed"} for g in ordered_gates if g["status"] == "FAIL"]
    state = "PASS" if not failures else "FAIL"
    exit_code = EXIT_PASS if state == "PASS" else EXIT_FAIL

    report = {
        "state": state,
        "exit_code": exit_code,
        "repo_root": repo_root.as_posix(),
        "gates": ordered_gates,
        "failures": failures,
        "warnings": warnings,
        "artifacts": {"dir": out_dir.as_posix() if out_dir else None, "files": sorted([p.name for p in out_dir.iterdir()]) if out_dir else []},
    }

    if out_dir:
        from ._exec import write_command_artifacts

        write_command_artifacts(out_dir, ctx.commands)
        (out_dir / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        hashes = {p.relative_to(out_dir).as_posix(): _sha256_file(p) for p in sorted(out_dir.rglob("*")) if p.is_file() and p.name != "hashes.json"}
        (out_dir / "hashes.json").write_text(json.dumps(hashes, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        report["artifacts"]["files"] = sorted([p.name for p in out_dir.iterdir()])

    return exit_code, report


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contract-eval")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--allow-write", action="store_true")
    group.add_argument("--strict-no-write", action="store_true")
    args = parser.parse_args(argv)
    out_dir = Path(args.out).resolve() if args.out else None
    no_write = True if args.strict_no_write else (not args.allow_write)
    code, report = evaluate_contracts(strict=args.strict, out_path=out_dir, json_mode=args.json, no_write=no_write)
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"CONTRACT_EVAL:{report['state']}")
    return code


if __name__ == "__main__":
    raise SystemExit(cli())
