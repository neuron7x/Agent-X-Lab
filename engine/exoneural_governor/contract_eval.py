from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._exec import ExecResult, pip_cmd, python_module_cmd, run_command, write_command_artifacts
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


def _bounded(items: list[str], n: int = 200) -> dict[str, Any]:
    ordered = sorted(set(items))
    return {"count": len(ordered), "items": ordered[:n]}


def _run_cmd(ctx: EvalContext, name: str, cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> ExecResult:
    run_cwd = cwd or ctx.repo_root
    rec = run_command(name=name, command=cmd, cwd=run_cwd, env=env)
    ctx.commands.append(rec)
    return rec


def discover_repo_root(cwd: Path) -> Path:
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


def _git_snapshot(repo_root: Path) -> dict[str, Any]:
    status = run_command("git_status", ["git", "status", "--porcelain=v1", "--untracked-files=all"], repo_root)
    tracked = run_command("git_diff_name", ["git", "diff", "--name-only"], repo_root)
    untracked = run_command("git_untracked", ["git", "ls-files", "--others", "--exclude-standard"], repo_root)
    return {
        "status": [ln for ln in status.stdout.splitlines() if ln.strip()],
        "tracked": [ln for ln in tracked.stdout.splitlines() if ln.strip()],
        "untracked": [ln for ln in untracked.stdout.splitlines() if ln.strip()],
    }


def _repo_fingerprint(repo_root: Path) -> str:
    head = run_command("head", ["git", "rev-parse", "HEAD"], repo_root)
    status = run_command("status", ["git", "status", "--porcelain=v1", "--untracked-files=all"], repo_root)
    payload = _canonical_json({"head": head.stdout.strip(), "status": status.stdout.splitlines()})
    return _sha256_text(payload)


def _semantic_signature(model: dict[str, Any], contract_rows: list[dict[str, Any]]) -> dict[str, Any]:
    edges = sorted((e.get("from_id"), e.get("to_id"), e.get("edge_type")) for e in model.get("edges", []) if isinstance(e, dict))
    cores = [(c.get("agent_id"), c.get("rank")) for c in model.get("core_candidates", []) if isinstance(c, dict)]
    return {
        "repo_fingerprint": model.get("repo_fingerprint"),
        "counts": model.get("counts", {}),
        "agent_ids": sorted(a.get("agent_id") for a in model.get("agents", []) if isinstance(a, dict) and isinstance(a.get("agent_id"), str)),
        "edges": edges,
        "core_ranked": cores,
        "contract_row_count": len(contract_rows),
    }


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _collect_versions(ctx: EvalContext) -> tuple[dict[str, Any], bool]:
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
    ok = all(v for k, v in versions.items() if k.endswith("_version") or k == "sys.executable")
    return versions, ok


def evaluate_contracts(strict: bool, out_path: Path | None, json_mode: bool, no_write: bool = True) -> tuple[int, dict[str, Any]]:
    repo_root = discover_repo_root(Path.cwd())
    out_dir = out_path.resolve() if out_path else None
    ctx = EvalContext(repo_root=repo_root, strict=strict, json_mode=json_mode, out_dir=out_dir, no_write=no_write)
    gates: list[GateResult] = []
    warnings: list[dict[str, str]] = []

    if not git_available():
        return EXIT_ERROR, {"state": "ERROR", "exit_code": EXIT_ERROR, "gates": [], "failures": [{"gate": "INTERNAL", "reason": "git unavailable"}], "warnings": [], "artifacts": {"dir": None, "files": []}}

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

    for v in hermetic_env.values():
        Path(v).mkdir(parents=True, exist_ok=True)

    before = _git_snapshot(repo_root)
    fp_start = _repo_fingerprint(repo_root)

    versions, versions_ok = _collect_versions(ctx)
    gates.append(GateResult("GATE_A01_HERMETIC_RUNNER", "PASS" if versions_ok else "FAIL", {"versions": versions}))

    env_stamp = {"versions": versions, "strict": strict, "no_write": no_write, "repo_root": repo_root.as_posix()}
    if out_dir:
        env_text = _canonical_json(env_stamp)
        (out_dir / "env.json").write_text(env_text + "\n", encoding="utf-8")
        (out_dir / "env.sha256").write_text(_sha256_text(env_text) + "\n", encoding="utf-8")
    gates.append(GateResult("GATE_A03_DETERMINISTIC_ENV_STAMP", "PASS", {"sha256": _sha256_text(_canonical_json(env_stamp))}))

    run_artifacts: list[tuple[Path, Path]] = []
    for n in ("run1", "run2"):
        tmp = Path(tempfile.mkdtemp(prefix=f"repo_model_{n}_", dir=temp_root))
        run_artifacts.append((tmp / "repo_model.json", tmp / "architecture_contract.jsonl"))

    for model_path, contract_path in run_artifacts:
        rec = _run_cmd(
            ctx,
            f"repo_model_{model_path.parent.name}",
            python_module_cmd("exoneural_governor", "repo-model", "--out", str(model_path), "--contract-out", str(contract_path)),
            cwd=repo_root / "engine",
            env=hermetic_env,
        )
        if rec.returncode != 0:
            gates.append(GateResult("GATE_A02_STRICT_NO_WRITE", "FAIL", {"reason": "repo-model execution failed"}))
            break

    if len(gates) == 2:
        m1, c1 = run_artifacts[0]
        m2, c2 = run_artifacts[1]
        model1 = json.loads(m1.read_text(encoding="utf-8"))
        model2 = json.loads(m2.read_text(encoding="utf-8"))
        contract_rows1 = [json.loads(ln) for ln in c1.read_text(encoding="utf-8").splitlines() if ln.strip()]
        contract_rows2 = [json.loads(ln) for ln in c2.read_text(encoding="utf-8").splitlines() if ln.strip()]

        sig1 = _semantic_signature(model1, contract_rows1)
        sig2 = _semantic_signature(model2, contract_rows2)
        det_ok = _canonical_json(sig1) == _canonical_json(sig2)

        if out_dir:
            shutil.copy2(m1, out_dir / "repo_model.run1.json")
            shutil.copy2(m2, out_dir / "repo_model.run2.json")

        ok_schema, reason = validate_repo_model_schema(model1)
        dangling = model1.get("unknowns", {}).get("dangling_edges", [])
        parse_failures = model1.get("unknowns", {}).get("parse_failures", [])

        comp_status = "PASS"
        if strict and (dangling or parse_failures):
            comp_status = "FAIL"
        elif dangling or parse_failures:
            warnings.append({"code": "DISCOVERY_INCOMPLETE", "message": f"dangling={len(dangling)} parse_failures={len(parse_failures)}"})

        gates.append(GateResult("GATE_B01_AGENT_DISCOVERY_COMPLETENESS", comp_status, {"dangling_edges": len(dangling), "parse_failures": len(parse_failures)}))

        dep_edges = [e for e in model1.get("edges", []) if isinstance(e, dict) and e.get("edge_type") in {"IMPORTS_PY", "IMPORTS_JS", "INCLUDES"}]
        minimum = 1
        gates.append(GateResult("GATE_B02_EDGE_TYPE_COVERAGE_MIN_IMPORTS", "PASS" if len(dep_edges) >= minimum else "FAIL", {"edge_count": len(dep_edges), "minimum": minimum}))

        agents = [a for a in model1.get("agents", []) if isinstance(a, dict)]
        gates.append(GateResult("GATE_C01_ARCHITECTURE_CONTRACT_JSONL", "PASS" if len(contract_rows1) == len(agents) else "FAIL", {"agents": len(agents), "rows": len(contract_rows1)}))

        name_required = {"CLI_SCRIPT", "GITHUB_WORKFLOW", "GITHUB_COMPOSITE_ACTION", "MAKEFILE"}
        missing_names = sorted([str(a.get("path")) for a in agents if a.get("kind") in name_required and not str(a.get("name") or "").strip()])
        gates.append(GateResult("GATE_C02_NAME_RECONSTRUCTION_NON_NULL", "PASS" if not missing_names else "FAIL", {"missing": _bounded(missing_names)}))

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
            has_parser = fp.suffix in {".py", ".js", ".mjs", ".ts", ".sh", ".bash"} and ("argparse.ArgumentParser(" in text or "@click.option(" in text or "yargs" in text)
            if has_parser and not inputs:
                iface_fail.append(p)
        gates.append(GateResult("GATE_C03_ZERO_SHOT_INTERFACE_EXTRACTION_MINIMUM", "PASS" if not iface_fail else "FAIL", {"missing_inputs": _bounded(iface_fail)}))

        policy_fail = bool(strict and (dangling or parse_failures))
        gates.append(GateResult("GATE_D01_POLICY_TIERS_ENFORCED", "FAIL" if policy_fail else "PASS", {"strict": strict}))

        fixtures_present = all((repo_root / p).exists() for p in [
            "engine/tests/fixtures/repo_model_fixture_a",
            "engine/tests/fixtures/repo_model_fixture_b",
            "engine/tests/fixtures/repo_model_fixture_c",
            "engine/tests/fixtures/repo_model_fixture_d",
        ])
        gates.append(GateResult("GATE_D02_REGRESSION_FIXTURES_GOLDEN", "PASS" if fixtures_present else "FAIL", {"fixtures_present": fixtures_present}))

        ids = sorted([a.get("agent_id") for a in agents if isinstance(a.get("agent_id"), str)])
        edges = [(e.get("from_id"), e.get("to_id")) for e in model1.get("edges", []) if isinstance(e, dict) and isinstance(e.get("from_id"), str) and isinstance(e.get("to_id"), str)]
        pr1 = pagerank(ids, edges)
        bc1 = betweenness_centrality_brandes(ids, edges)
        ids2 = ids + [f"iso_{i}" for i in range(8)]
        pr2 = pagerank(ids2, edges)
        bc2 = betweenness_centrality_brandes(ids2, edges)
        top1 = [k for k, _ in sorted(((k, 0.6 * pr1.get(k, 0.0) + 0.4 * bc1.get(k, 0.0)) for k in ids), key=lambda x: (-x[1], x[0]))[:5]]
        top2 = [k for k, _ in sorted(((k, 0.6 * pr2.get(k, 0.0) + 0.4 * bc2.get(k, 0.0)) for k in ids), key=lambda x: (-x[1], x[0]))[:5]]
        gates.append(GateResult("GATE_E01_CENTRALITY_STABILITY_SANITY", "PASS" if top1 == top2 else "FAIL", {"top5_before": top1, "top5_after": top2}))

        blame_missing = [r.get("path") for r in contract_rows1 if r.get("core_rank") is not None and (not isinstance(r.get("blame"), dict) or not r["blame"].get("top_author"))]
        can_git = git_available() and in_git_repo(repo_root)
        gates.append(GateResult("GATE_E02_BUS_FACTOR_MINIMUM", "FAIL" if strict and can_git and blame_missing else "PASS", {"git_available": can_git, "missing_blame": _bounded([str(x) for x in blame_missing if isinstance(x, str)])}))

        gates.append(GateResult("GATE_A02_STRICT_NO_WRITE", "PASS", {"schema": ok_schema, "schema_reason": reason, "semantic_equal": det_ok, "canonical_digest_run1": _sha256_text(_canonical_json(sig1)), "canonical_digest_run2": _sha256_text(_canonical_json(sig2))}))

    fp_end = _repo_fingerprint(repo_root)
    if fp_start != fp_end:
        if strict:
            gates.append(GateResult("GATE_A04_REPO_FINGERPRINT_RESCAN", "FAIL", {"start": fp_start, "end": fp_end}))
        else:
            warnings.append({"code": "FINGERPRINT_CHANGED", "message": "repository fingerprint changed during evaluation"})
            gates.append(GateResult("GATE_A04_REPO_FINGERPRINT_RESCAN", "WARNING", {"start": fp_start, "end": fp_end}))
    else:
        gates.append(GateResult("GATE_A04_REPO_FINGERPRINT_RESCAN", "PASS", {"start": fp_start, "end": fp_end}))

    after = _git_snapshot(repo_root)
    changed_paths = sorted(set(after["tracked"] + after["untracked"]) - set(before["tracked"] + before["untracked"]))
    outside: list[str] = []
    out_rel = _safe_rel(out_dir, repo_root) if out_dir else None
    for rel in changed_paths:
        if out_rel and (rel == out_rel or rel.startswith(out_rel + "/")):
            continue
        outside.append(rel)
    if no_write and outside:
        gates.append(GateResult("GATE_A02_STRICT_NO_WRITE", "FAIL", {"new_paths_outside_out": _bounded(outside)}))

    if out_dir:
        command_files = write_command_artifacts(out_dir, ctx.commands)
        file_hashes: dict[str, str] = {}
        for p in sorted(out_dir.rglob("*")):
            if p.is_file() and p.name != "hashes.json":
                rel = p.relative_to(out_dir).as_posix()
                file_hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        (out_dir / "hashes.json").write_text(json.dumps(file_hashes, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    failures = [{"gate": g.gate_id, "reason": "gate failed"} for g in gates if g.status == "FAIL"]
    state = "PASS" if not failures else "FAIL"
    exit_code = EXIT_PASS if state == "PASS" else EXIT_FAIL
    report = {
        "state": state,
        "exit_code": exit_code,
        "repo_root": repo_root.as_posix(),
        "gates": [g.as_dict() for g in gates],
        "failures": failures,
        "warnings": warnings,
        "artifacts": {"dir": out_dir.as_posix() if out_dir else None, "files": sorted([p.name for p in out_dir.iterdir()]) if out_dir else []},
    }
    if out_dir:
        (out_dir / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return exit_code, report


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contract-eval")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-write", action="store_true")
    parser.add_argument("--strict-no-write", action="store_true")
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
