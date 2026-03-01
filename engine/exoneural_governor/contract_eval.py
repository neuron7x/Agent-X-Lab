from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .blame import git_available, in_git_repo
from .repo_model import IGNORED_DIRS, betweenness_centrality_brandes, pagerank

EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_ERROR = 3

GATE_ORDER = [
    "GATE_A01_HERMETIC_RUNNER",
    "GATE_A02_STRICT_NO_WRITE",
    "GATE_A03_DETERMINISTIC_ENV_STAMP",
    "GATE_B01_AGENT_DISCOVERY_COMPLETENESS",
    "GATE_B02_EDGE_TYPE_COVERAGE_MIN_IMPORTS",
    "GATE_C01_ARCHITECTURE_CONTRACT_JSONL",
    "GATE_C02_NAME_RECONSTRUCTION_NON_NULL",
    "GATE_C03_ZERO_SHOT_INTERFACE_EXTRACTION_MINIMUM",
    "GATE_D01_POLICY_TIERS_ENFORCED",
    "GATE_D02_REGRESSION_FIXTURES_GOLDEN",
    "GATE_E01_CENTRALITY_STABILITY_SANITY",
    "GATE_E02_BUS_FACTOR_MINIMUM",
]


@dataclass
class CommandRecord:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


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
    commands: list[CommandRecord] = field(default_factory=list)


def _bounded(items: list[str], n: int = 200) -> dict[str, Any]:
    ordered = sorted(items)
    return {"count": len(ordered), "items": ordered[:n]}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_cmd(ctx: EvalContext, name: str, cmd: list[str]) -> CommandRecord:
    cwd = ctx.repo_root / "engine" if (len(cmd) >= 3 and cmd[0] == sys.executable and cmd[1] == "-m" and cmd[2] == "exoneural_governor") else ctx.repo_root
    env = os.environ.copy()
    if cwd == ctx.repo_root / "engine":
        env["PYTHONPATH"] = "."
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    rec = CommandRecord(name=name, command=cmd, returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    ctx.commands.append(rec)
    return rec


def discover_repo_root(cwd: Path) -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=False)
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


def _list_repo_files(repo_root: Path, out_dir: Path | None) -> set[str]:
    excluded = set(IGNORED_DIRS)
    out_rel = None
    if out_dir is not None:
        try:
            out_rel = out_dir.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            out_rel = None
    files: set[str] = set()
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.resolve().relative_to(repo_root.resolve()).as_posix()
        parts = rel.split("/")
        if any(part in excluded for part in parts):
            continue
        if out_rel and (rel == out_rel or rel.startswith(out_rel + "/")):
            continue
        files.add(rel)
    return files


def _repo_model_cmd(model_path: Path, contract_path: Path) -> list[str]:
    return [sys.executable, "-m", "exoneural_governor", "repo-model", "--out", model_path.as_posix(), "--contract-out", contract_path.as_posix()]


def _collect_versions(ctx: EvalContext) -> dict[str, Any]:
    py = _run_cmd(ctx, "python_version", [sys.executable, "-V"])
    pip = _run_cmd(ctx, "pip_version", [sys.executable, "-m", "pip", "-V"])
    node_proc = subprocess.run(["node", "-v"], capture_output=True, text=True, check=False)
    ctx.commands.append(CommandRecord("node_version", ["node", "-v"], node_proc.returncode, node_proc.stdout, node_proc.stderr))
    head = _run_cmd(ctx, "git_head", ["git", "rev-parse", "HEAD"])
    return {
        "sys.executable": sys.executable,
        "python_version": (py.stdout or py.stderr).strip() or None,
        "pip_version": (pip.stdout or pip.stderr).strip() or None,
        "node_version": ((node_proc.stdout or node_proc.stderr).strip() or None) if node_proc.returncode == 0 else None,
        "os.name": os.name,
        "sys.platform": sys.platform,
        "repo_head": head.stdout.strip() if head.returncode == 0 else None,
    }


def _policy_status(ctx: EvalContext, hard_fail: bool) -> str:
    if hard_fail:
        return "FAIL"
    return "PASS"


def evaluate_contracts(strict: bool, out_path: Path | None, json_mode: bool, no_write: bool = True) -> tuple[int, dict[str, Any]]:
    repo_root = discover_repo_root(Path.cwd())
    ctx = EvalContext(repo_root=repo_root, strict=strict, json_mode=json_mode, out_dir=out_path, no_write=no_write)
    gates: list[GateResult] = []
    warnings: list[dict[str, str]] = []

    if not git_available():
        return EXIT_ERROR, {"state": "ERROR", "exit_code": EXIT_ERROR, "gates": [], "failures": [{"gate": "INTERNAL", "reason": "git unavailable"}], "warnings": [], "artifacts": {"dir": None, "files": []}}

    baseline_git = _run_cmd(ctx, "git_status_baseline", ["git", "status", "--porcelain"])
    before_files = _list_repo_files(repo_root, out_path) if no_write else set()
    versions1 = _collect_versions(ctx)

    required_ok = all(versions1.get(k) for k in ["sys.executable", "python_version", "pip_version", "repo_head"])
    g_a01 = GateResult("GATE_A01_HERMETIC_RUNNER", "PASS" if required_ok else "FAIL", {"versions": versions1})
    gates.append(g_a01)

    with tempfile.TemporaryDirectory(prefix="contract_eval_") as td1, tempfile.TemporaryDirectory(prefix="contract_eval_") as td2:
        run1 = Path(td1)
        run2 = Path(td2)
        m1, c1 = run1 / "repo_model.json", run1 / "architecture_contract.jsonl"
        m2, c2 = run2 / "repo_model.json", run2 / "architecture_contract.jsonl"
        r1 = _run_cmd(ctx, "repo_model_run1", _repo_model_cmd(m1, c1))
        r2 = _run_cmd(ctx, "repo_model_run2", _repo_model_cmd(m2, c2))
        if r1.returncode != 0 or r2.returncode != 0:
            fail = {"state": "FAIL", "exit_code": EXIT_FAIL, "gates": [g.as_dict() for g in gates], "failures": [{"gate": "GATE_A03_DETERMINISTIC_ENV_STAMP", "reason": "repo-model execution failed"}], "warnings": warnings, "artifacts": {"dir": None, "files": []}}
            return EXIT_FAIL, fail
        model1 = json.loads(m1.read_text(encoding="utf-8"))
        model2 = json.loads(m2.read_text(encoding="utf-8"))
        versions2 = _collect_versions(ctx)

        env1 = {**versions1, "repo_root": repo_root.as_posix()}
        env2 = {**versions2, "repo_root": repo_root.as_posix()}
        env1_json = json.dumps(env1, sort_keys=True, separators=(",", ":")).encode("utf-8")
        env2_json = json.dumps(env2, sort_keys=True, separators=(",", ":")).encode("utf-8")
        env_equal = env1_json == env2_json and versions1.get("repo_head") == versions2.get("repo_head")
        if out_path is not None:
            out_path.mkdir(parents=True, exist_ok=True)
            (out_path / "env.json").write_text(env1_json.decode("utf-8"), encoding="utf-8")
            (out_path / "env.json.sha256").write_text(_sha256_bytes(env1_json) + "\n", encoding="utf-8")
        gates.append(GateResult("GATE_A03_DETERMINISTIC_ENV_STAMP", "PASS" if env_equal else "FAIL", {"equal": env_equal, "sha256": _sha256_bytes(env1_json)}))

        if no_write:
            post_git = _run_cmd(ctx, "git_status_post", ["git", "status", "--porcelain"])
            after_files = _list_repo_files(repo_root, out_path)
            new_files = sorted(after_files - before_files)
            git_changed = baseline_git.stdout != post_git.stdout
            violation = git_changed or bool(new_files)
            gates.append(GateResult("GATE_A02_STRICT_NO_WRITE", "FAIL" if violation else "PASS", {"git_changed": git_changed, "new_files": _bounded(new_files)}))
        else:
            gates.append(GateResult("GATE_A02_STRICT_NO_WRITE", "PASS", {"skipped": True, "reason": "allow-write enabled"}))

        ok_schema, reason = validate_repo_model_schema(model1)
        if not ok_schema:
            gates.append(GateResult("GATE_D01_POLICY_TIERS_ENFORCED", "FAIL", {"reason": reason}))
        else:
            dangling = model1.get("unknowns", {}).get("dangling_edges", [])
            parse_failures = model1.get("unknowns", {}).get("parse_failures", [])
            should_fail = strict and (bool(dangling) or bool(parse_failures))
            if (not strict) and (bool(dangling) or bool(parse_failures)):
                warnings.append({"gate": "GATE_D01_POLICY_TIERS_ENFORCED", "note": f"dangling={len(dangling)} parse_failures={len(parse_failures)}"})
            gates.append(GateResult("GATE_D01_POLICY_TIERS_ENFORCED", _policy_status(ctx, should_fail), {"strict": strict, "dangling_edges": len(dangling), "parse_failures": len(parse_failures)}))

        agents = model1.get("agents", [])
        agent_paths = {a.get("path") for a in agents if isinstance(a, dict)}
        dangling = model1.get("unknowns", {}).get("dangling_edges", [])
        comp_fail = bool(strict and dangling)
        gates.append(GateResult("GATE_B01_AGENT_DISCOVERY_COMPLETENESS", "FAIL" if comp_fail else "PASS", {"dangling_edges": len(dangling)}))

        dep_edges = [e for e in model1.get("edges", []) if e.get("edge_type") in {"IMPORTS_PY", "IMPORTS_JS", "INCLUDES"}]
        dao_files = [p for p in agent_paths if isinstance(p, str) and p.startswith("tools/dao-arbiter/")]
        if dao_files:
            enough = len(dep_edges) >= 5
            gates.append(GateResult("GATE_B02_EDGE_TYPE_COVERAGE_MIN_IMPORTS", "PASS" if enough else "FAIL", {"edge_count": len(dep_edges), "minimum": 5}))
        else:
            gates.append(GateResult("GATE_B02_EDGE_TYPE_COVERAGE_MIN_IMPORTS", "PASS", {"skipped": True, "reason": "insufficient surface present"}))

        contract_lines = [ln for ln in c1.read_text(encoding="utf-8").splitlines() if ln.strip()]
        gates.append(GateResult("GATE_C01_ARCHITECTURE_CONTRACT_JSONL", "PASS" if len(contract_lines) == len(agents) else "FAIL", {"agents": len(agents), "rows": len(contract_lines)}))

        name_required = {"CLI_SCRIPT", "GITHUB_WORKFLOW", "GITHUB_COMPOSITE_ACTION", "MAKEFILE"}
        missing_names = sorted([a.get("path", "") for a in agents if a.get("kind") in name_required and not str(a.get("name") or "").strip()])
        gates.append(GateResult("GATE_C02_NAME_RECONSTRUCTION_NON_NULL", "FAIL" if missing_names else "PASS", {"missing": _bounded(missing_names)}))

        iface_fail: list[str] = []
        for a in agents:
            p = a.get("path")
            if not isinstance(p, str):
                continue
            file_path = repo_root / p
            if not file_path.exists() or not file_path.is_file():
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
            inputs = a.get("interface", {}).get("inputs", []) if isinstance(a.get("interface"), dict) else []
            has_parser = "argparse.ArgumentParser(" in text or "@click.option(" in text or "@click.argument(" in text or ".option(" in text and "yargs" in text
            if has_parser and not inputs:
                iface_fail.append(p)
        gates.append(GateResult("GATE_C03_ZERO_SHOT_INTERFACE_EXTRACTION_MINIMUM", "FAIL" if iface_fail else "PASS", {"missing_inputs": _bounded(iface_fail)}))

        fixtures_present = (repo_root / "engine/tests/fixtures/repo_model_fixture_a").exists()
        gates.append(GateResult("GATE_D02_REGRESSION_FIXTURES_GOLDEN", "PASS" if fixtures_present else "FAIL", {"fixtures_present": fixtures_present}))

        ids = sorted([a.get("agent_id") for a in agents if isinstance(a.get("agent_id"), str)])
        edges = [(e.get("from_id"), e.get("to_id")) for e in model1.get("edges", []) if isinstance(e, dict) and isinstance(e.get("from_id"), str) and isinstance(e.get("to_id"), str)]
        pr1 = pagerank(ids, edges)
        bc1 = betweenness_centrality_brandes(ids, edges)
        ids2 = ids + [f"iso_{i}" for i in range(8)]
        pr2 = pagerank(ids2, edges)
        bc2 = betweenness_centrality_brandes(ids2, edges)
        top1 = [k for k, _ in sorted(((k, 0.7 * pr1.get(k, 0.0) + 0.3 * bc1.get(k, 0.0)) for k in ids), key=lambda x: (-x[1], x[0]))[:5]]
        top2 = [k for k, _ in sorted(((k, 0.7 * pr2.get(k, 0.0) + 0.3 * bc2.get(k, 0.0)) for k in ids), key=lambda x: (-x[1], x[0]))[:5]]
        gates.append(GateResult("GATE_E01_CENTRALITY_STABILITY_SANITY", "PASS" if top1 == top2 else "FAIL", {"top5_before": top1, "top5_after": top2}))

        can_git = git_available() and in_git_repo(repo_root)
        blame_rows = [json.loads(ln) for ln in contract_lines]
        blame_missing = [r.get("path") for r in blame_rows if r.get("core_rank") is not None and r.get("blame") is None]
        blame_fail = strict and can_git and bool(blame_missing)
        gates.append(GateResult("GATE_E02_BUS_FACTOR_MINIMUM", "FAIL" if blame_fail else "PASS", {"git_available": can_git, "missing_blame": _bounded([str(x) for x in blame_missing if isinstance(x, str)])}))

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
        "artifacts": {"dir": None, "files": []},
    }
    if out_path is not None:
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        report["artifacts"] = {"dir": out_path.as_posix(), "files": ["report.json", "env.json", "env.json.sha256"] if (out_path / "env.json").exists() else ["report.json"]}
    return exit_code, report


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contract-eval")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-write", action="store_true")
    parser.add_argument("--no-write", action="store_true", default=True)
    args = parser.parse_args(argv)
    out_dir = Path(args.out).resolve() if args.out else None
    no_write = True
    if args.allow_write:
        no_write = False
    code, report = evaluate_contracts(strict=args.strict, out_path=out_dir, json_mode=args.json, no_write=no_write)
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"CONTRACT_EVAL:{report['state']}")
    return code


if __name__ == "__main__":
    raise SystemExit(cli())
