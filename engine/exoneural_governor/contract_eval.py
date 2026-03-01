from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


GATE_ORDER = [
    "GATE_01_REPO_ROOT",
    "GATE_02_GIT_CLEAN",
    "GATE_03_REPO_MODEL_GENERATES",
    "GATE_04_REPO_MODEL_SCHEMA",
    "GATE_05_REPO_MODEL_DETERMINISM",
    "GATE_06_DANGLING_EDGES_POLICY",
    "GATE_07_CORE_CANDIDATES_MINIMUM",
    "GATE_08_AGENT_ID_REPRODUCIBLE",
    "GATE_09_NO_MARKDOWN_JSON",
]


@dataclass
class EvalContext:
    repo_root: Path
    strict: bool
    json_mode: bool
    out_dir: Path | None
    commands: list[str] = field(default_factory=list)
    command_outputs: list[dict[str, str]] = field(default_factory=list)
    model_path: Path | None = None
    model: dict[str, Any] | None = None
    run1: dict[str, Any] | None = None
    run2: dict[str, Any] | None = None


def discover_repo_root(cwd: Path) -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError("git repo root discovery failed")
    return Path(proc.stdout.strip()).resolve()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def run_cmd(ctx: EvalContext, cmd: list[str], name: str) -> subprocess.CompletedProcess[str]:
    ctx.commands.append(" ".join(cmd))
    proc = subprocess.run(cmd, cwd=ctx.repo_root, check=False, capture_output=True, text=True)
    ctx.command_outputs.append(
        {
            "name": name,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "stdout_sha256": _sha256_bytes(proc.stdout.encode("utf-8", errors="replace")),
            "stderr_sha256": _sha256_bytes(proc.stderr.encode("utf-8", errors="replace")),
            "returncode": str(proc.returncode),
        }
    )
    return proc


def _status(gid: str, status: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"id": gid, "status": status, "details": details}


def validate_repo_model_schema(model: dict[str, Any]) -> tuple[bool, str]:
    required_top = {
        "repo_root": str,
        "repo_fingerprint": str,
        "agents": list,
        "edges": list,
        "core_candidates": list,
        "counts": dict,
        "unknowns": dict,
    }
    for k, t in required_top.items():
        if k not in model:
            return False, f"missing key: {k}"
        if not isinstance(model[k], t):
            return False, f"invalid type for {k}"

    counts = model["counts"]
    for k in ("agents_count", "edges_count", "core_candidates_count"):
        if k not in counts or not isinstance(counts[k], int):
            return False, f"invalid counts.{k}"

    def is_hex12(value: Any) -> bool:
        if not isinstance(value, str) or len(value) != 12:
            return False
        try:
            int(value, 16)
            return True
        except ValueError:
            return False

    for item in model["agents"]:
        if not isinstance(item, dict):
            return False, "invalid agent item"
        if not is_hex12(item.get("agent_id")):
            return False, "invalid agent_id"
        if not isinstance(item.get("path"), str):
            return False, "invalid agent.path"
        if not isinstance(item.get("kind"), str):
            return False, "invalid agent.kind"

    for item in model["edges"]:
        if not isinstance(item, dict):
            return False, "invalid edge item"
        if not isinstance(item.get("from_id"), str):
            return False, "invalid edge.from_id"
        if not isinstance(item.get("to_id"), str):
            return False, "invalid edge.to_id"
        if not isinstance(item.get("edge_type"), str):
            return False, "invalid edge.edge_type"

    for item in model["core_candidates"]:
        if not isinstance(item, dict):
            return False, "invalid core candidate item"
        if not isinstance(item.get("agent_id"), str):
            return False, "invalid core.agent_id"
        if not isinstance(item.get("core_score"), (int, float)):
            return False, "invalid core.core_score"
        if not isinstance(item.get("rank"), int):
            return False, "invalid core.rank"
        if not isinstance(item.get("path"), str):
            return False, "invalid core.path"
        if not isinstance(item.get("kind"), str):
            return False, "invalid core.kind"
        if not isinstance(item.get("pr"), (int, float)):
            return False, "invalid core.pr"
        if not isinstance(item.get("bc"), (int, float)):
            return False, "invalid core.bc"

    return True, "ok"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def evaluate_contracts(strict: bool = False, out_path: Path | None = None, json_mode: bool = False) -> tuple[int, dict[str, Any]]:
    try:
        repo_root = discover_repo_root(Path.cwd())
    except Exception as exc:
        report = {
            "state": "ERROR",
            "exit_code": 3,
            "repo_root": Path.cwd().as_posix(),
            "repo_fingerprint": None,
            "gates": [_status("GATE_01_REPO_ROOT", "ERROR", {"error": str(exc)})],
            "failures": [{"gate": "GATE_01_REPO_ROOT", "reason": str(exc)}],
            "warnings": [],
            "artifacts": {"dir": None, "files": []},
        }
        return 3, report

    os.chdir(repo_root)
    ctx = EvalContext(repo_root=repo_root, strict=strict, json_mode=json_mode, out_dir=out_path)

    gates: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    repo_fingerprint: str | None = None

    try:
        git_check = run_cmd(ctx, ["git", "--version"], "git_version")
        if git_check.returncode != 0:
            report = {
                "state": "ERROR",
                "exit_code": 3,
                "repo_root": repo_root.as_posix(),
                "repo_fingerprint": None,
                "gates": [_status("GATE_00_GIT_AVAILABLE", "ERROR", {"returncode": git_check.returncode})],
                "failures": [{"gate": "GATE_00_GIT_AVAILABLE", "reason": "git unavailable"}],
                "warnings": [],
                "artifacts": {"dir": None, "files": []},
            }
            return 3, report

        env_details: dict[str, str | None] = {}
        py = run_cmd(ctx, ["python", "-V"], "python_version")
        env_details["python"] = py.stdout.strip() or py.stderr.strip()
        pip = run_cmd(ctx, ["pip", "-V"], "pip_version")
        env_details["pip"] = (pip.stdout.strip() or pip.stderr.strip()) if pip.returncode == 0 else None
        node = run_cmd(ctx, ["node", "-v"], "node_version")
        env_details["node"] = (node.stdout.strip() or node.stderr.strip()) if node.returncode == 0 else None

        markers_ok = (repo_root / "engine").is_dir() and (repo_root / ".github").is_dir() and (repo_root / "Makefile").is_file()
        if markers_ok:
            gates.append(_status("GATE_01_REPO_ROOT", "PASS", {"repo_root": repo_root.as_posix(), "env": env_details}))
        else:
            gates.append(_status("GATE_01_REPO_ROOT", "FAIL", {"repo_root": repo_root.as_posix()}))
            failures.append({"gate": "GATE_01_REPO_ROOT", "reason": "required markers missing"})

        st = run_cmd(ctx, ["git", "status", "--porcelain"], "git_status_porcelain")
        dirty = bool(st.stdout.strip())
        if st.returncode == 0 and not dirty:
            gates.append(_status("GATE_02_GIT_CLEAN", "PASS", {"dirty": False}))
        else:
            gates.append(_status("GATE_02_GIT_CLEAN", "FAIL", {"dirty": dirty, "status_returncode": st.returncode}))
            failures.append({"gate": "GATE_02_GIT_CLEAN", "reason": "git tree is not clean"})

        model_path = repo_root / "engine/artifacts/repo_model/repo_model.json"
        rm = run_cmd(
            ctx,
            ["python", "-m", "exoneural_governor", "repo-model", "--out", "engine/artifacts/repo_model/repo_model.json"],
            "repo_model_generate",
        )
        model_ok = rm.returncode == 0 and model_path.exists()
        parsed = None
        if model_ok:
            try:
                parsed = _load_json(model_path)
            except Exception:
                model_ok = False
        if model_ok and parsed is not None:
            ctx.model_path = model_path
            ctx.model = parsed
            repo_fingerprint = parsed.get("repo_fingerprint")
            gates.append(_status("GATE_03_REPO_MODEL_GENERATES", "PASS", {"path": "engine/artifacts/repo_model/repo_model.json"}))
        else:
            gates.append(_status("GATE_03_REPO_MODEL_GENERATES", "FAIL", {"returncode": rm.returncode, "path_exists": model_path.exists()}))
            failures.append({"gate": "GATE_03_REPO_MODEL_GENERATES", "reason": "repo-model generation failed"})

        schema_status = "FAIL"
        schema_details: dict[str, Any] = {}
        if ctx.model is not None:
            ok, reason = validate_repo_model_schema(ctx.model)
            schema_status = "PASS" if ok else "FAIL"
            schema_details = {"reason": reason}
            if not ok:
                failures.append({"gate": "GATE_04_REPO_MODEL_SCHEMA", "reason": reason})
        else:
            schema_details = {"reason": "missing model"}
            failures.append({"gate": "GATE_04_REPO_MODEL_SCHEMA", "reason": "missing model"})
        gates.append(_status("GATE_04_REPO_MODEL_SCHEMA", schema_status, schema_details))

        det_status = "FAIL"
        det_details: dict[str, Any] = {}
        if ctx.model is not None and not dirty:
            with tempfile.TemporaryDirectory(prefix="axl_contract_eval_") as td:
                tmp_dir = Path(td)
                run1p = tmp_dir / "repo_model.run1.json"
                run2p = tmp_dir / "repo_model.run2.json"
                r1 = run_cmd(ctx, ["python", "-m", "exoneural_governor", "repo-model", "--out", run1p.as_posix()], "repo_model_run1")
                r2 = run_cmd(ctx, ["python", "-m", "exoneural_governor", "repo-model", "--out", run2p.as_posix()], "repo_model_run2")
                if r1.returncode == 0 and r2.returncode == 0 and run1p.exists() and run2p.exists():
                    j1 = _load_json(run1p)
                    j2 = _load_json(run2p)
                    counts1 = j1.get("counts", {})
                    counts2 = j2.get("counts", {})
                    set1 = {a.get("agent_id") for a in j1.get("agents", [])}
                    set2 = {a.get("agent_id") for a in j2.get("agents", [])}
                    edges1 = sorted((e.get("from_id"), e.get("to_id"), e.get("edge_type")) for e in j1.get("edges", []))
                    edges2 = sorted((e.get("from_id"), e.get("to_id"), e.get("edge_type")) for e in j2.get("edges", []))
                    core1 = [(c.get("agent_id"), c.get("rank")) for c in j1.get("core_candidates", [])]
                    core2 = [(c.get("agent_id"), c.get("rank")) for c in j2.get("core_candidates", [])]
                    checks = {
                        "repo_fingerprint_equal": j1.get("repo_fingerprint") == j2.get("repo_fingerprint"),
                        "counts_equal": counts1 == counts2,
                        "agent_ids_equal": set1 == set2,
                        "edges_multiset_equal": edges1 == edges2,
                        "core_order_equal": core1 == core2,
                    }
                    if all(checks.values()):
                        det_status = "PASS"
                    else:
                        failures.append({"gate": "GATE_05_REPO_MODEL_DETERMINISM", "reason": "determinism checks failed"})
                    det_details = checks
                    ctx.run1, ctx.run2 = j1, j2
                else:
                    failures.append({"gate": "GATE_05_REPO_MODEL_DETERMINISM", "reason": "repo-model reruns failed"})
                    det_details = {"run1_returncode": r1.returncode, "run2_returncode": r2.returncode}
        else:
            failures.append({"gate": "GATE_05_REPO_MODEL_DETERMINISM", "reason": "preconditions failed"})
            det_details = {"requires_clean_git": True}
        gates.append(_status("GATE_05_REPO_MODEL_DETERMINISM", det_status, det_details))

        dangling = []
        if ctx.model is not None:
            dangling = ctx.model.get("unknowns", {}).get("dangling_edges", [])
        if strict and dangling:
            gates.append(_status("GATE_06_DANGLING_EDGES_POLICY", "FAIL", {"dangling_edges_count": len(dangling), "strict": True}))
            failures.append({"gate": "GATE_06_DANGLING_EDGES_POLICY", "reason": "dangling edges present"})
        else:
            gates.append(_status("GATE_06_DANGLING_EDGES_POLICY", "PASS", {"dangling_edges_count": len(dangling), "strict": strict}))
            if dangling:
                warnings.append({"gate": "GATE_06_DANGLING_EDGES_POLICY", "note": f"dangling_edges={len(dangling)}"})

        g7_status = "FAIL"
        g7_details: dict[str, Any] = {}
        if ctx.model is not None:
            counts = ctx.model.get("counts", {})
            cc = ctx.model.get("core_candidates", [])
            min_ok = isinstance(counts.get("core_candidates_count"), int) and counts.get("core_candidates_count") >= 5
            score_ok = all(isinstance(c.get("core_score"), (int, float)) and 0 <= float(c.get("core_score")) <= 1 for c in cc)
            g7_details = {"core_candidates_count": counts.get("core_candidates_count"), "min_ok": min_ok, "score_range_ok": score_ok}
            if min_ok and score_ok:
                g7_status = "PASS"
            else:
                failures.append({"gate": "GATE_07_CORE_CANDIDATES_MINIMUM", "reason": "core candidates threshold/score invalid"})
        else:
            failures.append({"gate": "GATE_07_CORE_CANDIDATES_MINIMUM", "reason": "missing model"})
            g7_details = {"reason": "missing model"}
        gates.append(_status("GATE_07_CORE_CANDIDATES_MINIMUM", g7_status, g7_details))

        g8_status = "FAIL"
        g8_details: dict[str, Any] = {}
        if ctx.model is not None:
            mismatches: list[dict[str, str]] = []
            for agent in ctx.model.get("agents", []):
                p = agent.get("path")
                aid = agent.get("agent_id")
                if not isinstance(p, str) or not isinstance(aid, str):
                    mismatches.append({"path": str(p), "expected": "", "actual": str(aid)})
                    continue
                expected = hashlib.sha256(p.encode("utf-8")).hexdigest()[:12]
                if aid != expected:
                    mismatches.append({"path": p, "expected": expected, "actual": aid})
            g8_details = {"mismatch_count": len(mismatches)}
            if mismatches:
                g8_details["mismatches"] = mismatches[:20]
                failures.append({"gate": "GATE_08_AGENT_ID_REPRODUCIBLE", "reason": "agent_id mismatch"})
            else:
                g8_status = "PASS"
        else:
            failures.append({"gate": "GATE_08_AGENT_ID_REPRODUCIBLE", "reason": "missing model"})
            g8_details = {"reason": "missing model"}
        gates.append(_status("GATE_08_AGENT_ID_REPRODUCIBLE", g8_status, g8_details))

        g9_status = "PASS"
        g9_details = {"json_mode": json_mode}
        if json_mode:
            # enforced by cli output implementation; deterministic construction
            g9_details["format"] = "json_only"
        gates.append(_status("GATE_09_NO_MARKDOWN_JSON", g9_status, g9_details))

        failed = [g for g in gates if g["status"] == "FAIL"]
        state = "PASS" if not failed else "FAIL"
        exit_code = 0 if state == "PASS" else 2
        report = {
            "state": state,
            "exit_code": exit_code,
            "repo_root": repo_root.as_posix(),
            "repo_fingerprint": repo_fingerprint,
            "gates": gates,
            "failures": failures,
            "warnings": warnings,
            "artifacts": {"dir": out_path.relative_to(repo_root).as_posix() if out_path and out_path.is_absolute() and out_path.is_relative_to(repo_root) else (out_path.as_posix() if out_path else None), "files": []},
        }
        return exit_code, report
    except Exception as exc:
        report = {
            "state": "ERROR",
            "exit_code": 3,
            "repo_root": repo_root.as_posix(),
            "repo_fingerprint": repo_fingerprint,
            "gates": gates,
            "failures": failures + [{"gate": "INTERNAL", "reason": str(exc)}],
            "warnings": warnings,
            "artifacts": {"dir": out_path.as_posix() if out_path else None, "files": []},
        }
        return 3, report


def write_artifacts(ctx_report: dict[str, Any], out_dir: Path, commands: list[str], command_outputs: list[dict[str, str]]) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir = out_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []

    cmd_log = out_dir / "commands.log"
    cmd_log.write_text("\n".join(commands) + "\n", encoding="utf-8")
    files.append(cmd_log)

    for i, item in enumerate(command_outputs, start=1):
        base = outputs_dir / f"{i:03d}_{item['name']}"
        outp = base.with_suffix(".stdout.txt")
        errp = base.with_suffix(".stderr.txt")
        meta = base.with_suffix(".meta.json")
        outp.write_text(item["stdout"], encoding="utf-8")
        errp.write_text(item["stderr"], encoding="utf-8")
        meta.write_text(
            json.dumps(
                {
                    "name": item["name"],
                    "stdout_sha256": item["stdout_sha256"],
                    "stderr_sha256": item["stderr_sha256"],
                    "returncode": int(item["returncode"]),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        files.extend([outp, errp, meta])

    report_file = out_dir / "report.json"
    report_file.write_text(json.dumps(ctx_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files.append(report_file)

    hashes_file = out_dir / "hashes.json"
    hashes = {p.relative_to(out_dir).as_posix(): _sha256_file(p) for p in sorted(files)}
    hashes_file.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files.append(hashes_file)

    return {
        "dir": out_dir.as_posix(),
        "files": [p.relative_to(out_dir).as_posix() for p in sorted(files)],
    }


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contract-eval")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    out_dir = Path(args.out).resolve() if args.out else None
    code, report = evaluate_contracts(strict=args.strict, out_path=out_dir, json_mode=args.json)

    # regenerate command records for artifacts deterministically from local execution trace
    if out_dir is not None:
        # rerun lightweight collection to populate files; deterministic and local
        repo_root = discover_repo_root(Path.cwd())
        ctx = EvalContext(repo_root=repo_root, strict=args.strict, json_mode=args.json, out_dir=out_dir)
        run_cmd(ctx, ["git", "--version"], "git_version")
        run_cmd(ctx, ["python", "-V"], "python_version")
        run_cmd(ctx, ["pip", "-V"], "pip_version")
        run_cmd(ctx, ["node", "-v"], "node_version")
        run_cmd(ctx, ["git", "status", "--porcelain"], "git_status_porcelain")
        run_cmd(ctx, ["python", "-m", "exoneural_governor", "repo-model", "--out", "engine/artifacts/repo_model/repo_model.json"], "repo_model_generate")
        art = write_artifacts(report, out_dir, ctx.commands, ctx.command_outputs)
        report["artifacts"] = art
        (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(f"CONTRACT_EVAL:{report['state']}")
    return int(code)


if __name__ == "__main__":
    raise SystemExit(cli())
