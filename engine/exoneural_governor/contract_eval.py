from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_ERROR = 3

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
class CommandRecord:
    name: str
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass
class EvalContext:
    repo_root: Path
    strict: bool
    json_mode: bool
    out_dir: Path | None
    commands: list[CommandRecord] = field(default_factory=list)
    model_path: Path | None = None
    model: dict[str, Any] | None = None


@dataclass
class GateResult:
    gate_id: str
    status: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.gate_id, "status": self.status, "details": self.details}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        loaded = json.load(fh)
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object in {path}")
    return loaded


def _run_cmd(ctx: EvalContext, name: str, cmd: list[str]) -> CommandRecord:
    proc = subprocess.run(
        cmd,
        cwd=ctx.repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    rec = CommandRecord(
        name=name,
        command=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
    ctx.commands.append(rec)
    return rec


def discover_repo_root(cwd: Path) -> Path:
    if shutil.which("git") is None:
        raise RuntimeError("git executable not found")
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("unable to discover repo root via git rev-parse")
    root = Path(proc.stdout.strip()).resolve()
    if not root.exists():
        raise RuntimeError("discovered repo root does not exist")
    return root


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
    for key, expected_type in required_top.items():
        if key not in model:
            return False, f"missing key: {key}"
        if not isinstance(model[key], expected_type):
            return False, f"invalid type for {key}"

    counts = model["counts"]
    for key in ("agents_count", "edges_count", "core_candidates_count"):
        if key not in counts:
            return False, f"missing counts.{key}"
        if not isinstance(counts[key], int):
            return False, f"invalid type for counts.{key}"

    def _is_hex12(value: Any) -> bool:
        if not isinstance(value, str) or len(value) != 12:
            return False
        try:
            int(value, 16)
        except ValueError:
            return False
        return True

    agents = model["agents"]
    for index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            return False, f"agents[{index}] is not object"
        if not _is_hex12(agent.get("agent_id")):
            return False, f"agents[{index}].agent_id invalid"
        if not isinstance(agent.get("path"), str):
            return False, f"agents[{index}].path invalid"
        if not isinstance(agent.get("kind"), str):
            return False, f"agents[{index}].kind invalid"

    edges = model["edges"]
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            return False, f"edges[{index}] is not object"
        if not isinstance(edge.get("from_id"), str):
            return False, f"edges[{index}].from_id invalid"
        if not isinstance(edge.get("to_id"), str):
            return False, f"edges[{index}].to_id invalid"
        if not isinstance(edge.get("edge_type"), str):
            return False, f"edges[{index}].edge_type invalid"

    candidates = model["core_candidates"]
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            return False, f"core_candidates[{index}] is not object"
        for key, typ in {
            "agent_id": str,
            "rank": int,
            "path": str,
            "kind": str,
        }.items():
            if not isinstance(candidate.get(key), typ):
                return False, f"core_candidates[{index}].{key} invalid"
        for key in ("core_score", "pr", "bc"):
            if not isinstance(candidate.get(key), (int, float)):
                return False, f"core_candidates[{index}].{key} invalid"

    return True, "ok"


def _gate_repo_root(ctx: EvalContext) -> GateResult:
    markers = {
        "engine": (ctx.repo_root / "engine").is_dir(),
        ".github": (ctx.repo_root / ".github").is_dir(),
        "Makefile": (ctx.repo_root / "Makefile").is_file(),
    }
    if all(markers.values()):
        return GateResult("GATE_01_REPO_ROOT", "PASS", {"markers": markers})
    return GateResult("GATE_01_REPO_ROOT", "FAIL", {"markers": markers})


def _gate_git_clean(ctx: EvalContext) -> GateResult:
    rec = _run_cmd(ctx, "git_status_porcelain", ["git", "status", "--porcelain"])
    dirty = bool(rec.stdout.strip())
    if rec.returncode == 0 and not dirty:
        return GateResult("GATE_02_GIT_CLEAN", "PASS", {"dirty": False})
    return GateResult(
        "GATE_02_GIT_CLEAN",
        "FAIL",
        {"dirty": dirty, "returncode": rec.returncode},
    )


def _repo_model_cmd(output_path: Path) -> list[str]:
    return [
        "python",
        "-m",
        "exoneural_governor",
        "repo-model",
        "--out",
        output_path.as_posix(),
        "--no-contract",
    ]


def _gate_repo_model_generates(ctx: EvalContext, artifacts_model_path: Path) -> GateResult:
    rec = _run_cmd(ctx, "repo_model_generate", _repo_model_cmd(artifacts_model_path))
    if rec.returncode != 0 or not artifacts_model_path.exists():
        return GateResult(
            "GATE_03_REPO_MODEL_GENERATES",
            "FAIL",
            {
                "returncode": rec.returncode,
                "output_exists": artifacts_model_path.exists(),
                "path": artifacts_model_path.as_posix(),
            },
        )
    try:
        model = _json_load(artifacts_model_path)
    except Exception as exc:
        return GateResult(
            "GATE_03_REPO_MODEL_GENERATES",
            "FAIL",
            {"reason": f"invalid_json: {exc}", "path": artifacts_model_path.as_posix()},
        )

    ctx.model_path = artifacts_model_path
    ctx.model = model
    return GateResult("GATE_03_REPO_MODEL_GENERATES", "PASS", {"path": artifacts_model_path.as_posix()})


def _gate_repo_model_schema(ctx: EvalContext) -> GateResult:
    if ctx.model is None:
        return GateResult("GATE_04_REPO_MODEL_SCHEMA", "FAIL", {"reason": "repo model missing"})
    ok, reason = validate_repo_model_schema(ctx.model)
    return GateResult("GATE_04_REPO_MODEL_SCHEMA", "PASS" if ok else "FAIL", {"reason": reason})


def _edge_counter(model: dict[str, Any]) -> Counter[tuple[str, str, str]]:
    return Counter((str(e.get("from_id")), str(e.get("to_id")), str(e.get("edge_type"))) for e in model.get("edges", []))


def _gate_repo_model_determinism(ctx: EvalContext, git_clean_passed: bool, run_dir: Path) -> GateResult:
    if not git_clean_passed:
        return GateResult("GATE_05_REPO_MODEL_DETERMINISM", "FAIL", {"reason": "requires clean git tree"})

    run1 = run_dir / "repo_model.run1.json"
    run2 = run_dir / "repo_model.run2.json"
    rec1 = _run_cmd(ctx, "repo_model_run1", _repo_model_cmd(run1))
    rec2 = _run_cmd(ctx, "repo_model_run2", _repo_model_cmd(run2))
    if rec1.returncode != 0 or rec2.returncode != 0:
        return GateResult(
            "GATE_05_REPO_MODEL_DETERMINISM",
            "FAIL",
            {"run1_returncode": rec1.returncode, "run2_returncode": rec2.returncode},
        )

    try:
        m1 = _json_load(run1)
        m2 = _json_load(run2)
    except Exception as exc:
        return GateResult("GATE_05_REPO_MODEL_DETERMINISM", "FAIL", {"reason": f"invalid_json: {exc}"})

    checks = {
        "repo_fingerprint_equal": m1.get("repo_fingerprint") == m2.get("repo_fingerprint"),
        "counts_equal": m1.get("counts") == m2.get("counts"),
        "agent_ids_equal": {a.get("agent_id") for a in m1.get("agents", [])} == {a.get("agent_id") for a in m2.get("agents", [])},
        "edges_multiset_equal": _edge_counter(m1) == _edge_counter(m2),
        "core_order_equal": [
            (c.get("agent_id"), c.get("rank")) for c in m1.get("core_candidates", [])
        ]
        == [
            (c.get("agent_id"), c.get("rank")) for c in m2.get("core_candidates", [])
        ],
    }

    if all(checks.values()):
        return GateResult("GATE_05_REPO_MODEL_DETERMINISM", "PASS", checks)
    return GateResult("GATE_05_REPO_MODEL_DETERMINISM", "FAIL", checks)


def _gate_dangling_edges_policy(ctx: EvalContext) -> tuple[GateResult, dict[str, str] | None]:
    if ctx.model is None:
        return GateResult("GATE_06_DANGLING_EDGES_POLICY", "FAIL", {"reason": "repo model missing"}), None

    dangling = ctx.model.get("unknowns", {}).get("dangling_edges", [])
    if not isinstance(dangling, list):
        return GateResult("GATE_06_DANGLING_EDGES_POLICY", "FAIL", {"reason": "unknowns.dangling_edges invalid"}), None

    if ctx.strict and dangling:
        return (
            GateResult(
                "GATE_06_DANGLING_EDGES_POLICY",
                "FAIL",
                {"dangling_edges_count": len(dangling), "strict": True},
            ),
            None,
        )

    warning = None
    if dangling:
        warning = {"gate": "GATE_06_DANGLING_EDGES_POLICY", "note": f"dangling_edges={len(dangling)}"}
    return (
        GateResult(
            "GATE_06_DANGLING_EDGES_POLICY",
            "PASS",
            {"dangling_edges_count": len(dangling), "strict": ctx.strict},
        ),
        warning,
    )


def _gate_core_candidates_minimum(ctx: EvalContext) -> GateResult:
    if ctx.model is None:
        return GateResult("GATE_07_CORE_CANDIDATES_MINIMUM", "FAIL", {"reason": "repo model missing"})

    counts = ctx.model.get("counts", {})
    candidates = ctx.model.get("core_candidates", [])
    count_ok = isinstance(counts.get("core_candidates_count"), int) and counts["core_candidates_count"] >= 5
    score_ok = all(
        isinstance(item.get("core_score"), (int, float)) and 0 <= float(item["core_score"]) <= 1 for item in candidates
    )
    status = "PASS" if count_ok and score_ok else "FAIL"
    return GateResult(
        "GATE_07_CORE_CANDIDATES_MINIMUM",
        status,
        {
            "core_candidates_count": counts.get("core_candidates_count"),
            "count_ok": count_ok,
            "score_ok": score_ok,
        },
    )


def _gate_agent_id_reproducible(ctx: EvalContext) -> GateResult:
    if ctx.model is None:
        return GateResult("GATE_08_AGENT_ID_REPRODUCIBLE", "FAIL", {"reason": "repo model missing"})

    mismatches: list[dict[str, str]] = []
    for agent in ctx.model.get("agents", []):
        path = agent.get("path")
        actual = agent.get("agent_id")
        if not isinstance(path, str) or not isinstance(actual, str):
            mismatches.append({"path": str(path), "expected": "", "actual": str(actual)})
            continue
        expected = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
        if expected != actual:
            mismatches.append({"path": path, "expected": expected, "actual": actual})

    status = "PASS" if not mismatches else "FAIL"
    details: dict[str, Any] = {"mismatch_count": len(mismatches)}
    if mismatches:
        details["mismatches"] = mismatches
    return GateResult("GATE_08_AGENT_ID_REPRODUCIBLE", status, details)


def _gate_no_markdown_json(json_mode: bool) -> GateResult:
    if not json_mode:
        return GateResult("GATE_09_NO_MARKDOWN_JSON", "PASS", {"json_mode": False})

    payload = json.dumps({"probe": True}, sort_keys=True)
    first = payload.lstrip()[:1]
    last = payload.rstrip()[-1:]
    has_fence = "```" in payload
    ok = first == "{" and last == "}" and not has_fence
    return GateResult(
        "GATE_09_NO_MARKDOWN_JSON",
        "PASS" if ok else "FAIL",
        {
            "json_mode": True,
            "starts_with": first,
            "ends_with": last,
            "has_code_fence": has_fence,
        },
    )


def _collect_env_fingerprints(ctx: EvalContext) -> dict[str, str | None]:
    py = _run_cmd(ctx, "python_version", ["python", "-V"])
    pip = _run_cmd(ctx, "pip_version", ["pip", "-V"])
    node = _run_cmd(ctx, "node_version", ["node", "-v"])
    return {
        "python": (py.stdout.strip() or py.stderr.strip() or None),
        "pip": (pip.stdout.strip() or pip.stderr.strip() or None) if pip.returncode == 0 else None,
        "node": (node.stdout.strip() or node.stderr.strip() or None) if node.returncode == 0 else None,
    }


def _build_report(
    *,
    state: str,
    exit_code: int,
    repo_root: Path,
    repo_fingerprint: str | None,
    gates: list[GateResult],
    failures: list[dict[str, str]],
    warnings: list[dict[str, str]],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "state": state,
        "exit_code": exit_code,
        "repo_root": repo_root.as_posix(),
        "repo_fingerprint": repo_fingerprint,
        "gates": [g.as_dict() for g in gates],
        "failures": failures,
        "warnings": warnings,
        "artifacts": artifacts,
    }


def write_artifacts(report: dict[str, Any], ctx: EvalContext) -> dict[str, Any]:
    if ctx.out_dir is None:
        return {"dir": None, "files": []}

    out_dir = ctx.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = out_dir / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []

    commands_log = out_dir / "commands.log"
    commands_log.write_text(
        "".join(" ".join(rec.command) + "\n" for rec in ctx.commands),
        encoding="utf-8",
    )
    files.append(commands_log)

    for index, rec in enumerate(ctx.commands, start=1):
        prefix = outputs / f"{index:03d}_{rec.name}"
        stdout_path = prefix.with_suffix(".stdout.txt")
        stderr_path = prefix.with_suffix(".stderr.txt")
        meta_path = prefix.with_suffix(".meta.json")
        stdout_path.write_text(rec.stdout, encoding="utf-8")
        stderr_path.write_text(rec.stderr, encoding="utf-8")
        meta_path.write_text(
            json.dumps(
                {
                    "name": rec.name,
                    "returncode": rec.returncode,
                    "stdout_sha256": _sha256_bytes(rec.stdout.encode("utf-8")),
                    "stderr_sha256": _sha256_bytes(rec.stderr.encode("utf-8")),
                },
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        files.extend([stdout_path, stderr_path, meta_path])

    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files.append(report_path)

    hashes = {path.relative_to(out_dir).as_posix(): _sha256_file(path) for path in sorted(files)}
    hashes_path = out_dir / "hashes.json"
    hashes_path.write_text(json.dumps(hashes, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    files.append(hashes_path)

    try:
        dir_value = out_dir.relative_to(ctx.repo_root).as_posix()
    except ValueError:
        dir_value = out_dir.as_posix()

    return {
        "dir": dir_value,
        "files": [path.relative_to(out_dir).as_posix() for path in sorted(files)],
    }


def evaluate_contracts(strict: bool = False, out_path: Path | None = None, json_mode: bool = False) -> tuple[int, dict[str, Any]]:
    try:
        repo_root = discover_repo_root(Path.cwd())
    except Exception as exc:
        fallback_root = Path.cwd().resolve()
        report = _build_report(
            state="ERROR",
            exit_code=EXIT_ERROR,
            repo_root=fallback_root,
            repo_fingerprint=None,
            gates=[GateResult("GATE_01_REPO_ROOT", "ERROR", {"reason": str(exc)})],
            failures=[{"gate": "GATE_01_REPO_ROOT", "reason": str(exc)}],
            warnings=[],
            artifacts={"dir": None, "files": []},
        )
        return EXIT_ERROR, report

    os.chdir(repo_root)
    ctx = EvalContext(repo_root=repo_root, strict=strict, json_mode=json_mode, out_dir=out_path)

    if shutil.which("git") is None:
        report = _build_report(
            state="ERROR",
            exit_code=EXIT_ERROR,
            repo_root=repo_root,
            repo_fingerprint=None,
            gates=[GateResult("GATE_01_REPO_ROOT", "ERROR", {"reason": "git unavailable"})],
            failures=[{"gate": "GATE_01_REPO_ROOT", "reason": "git unavailable"}],
            warnings=[],
            artifacts={"dir": None, "files": []},
        )
        return EXIT_ERROR, report

    gates: list[GateResult] = []
    failures: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    try:
        env = _collect_env_fingerprints(ctx)

        g1 = _gate_repo_root(ctx)
        g1.details["environment"] = env
        gates.append(g1)
        if g1.status == "FAIL":
            failures.append({"gate": g1.gate_id, "reason": "required repository markers missing"})

        g2 = _gate_git_clean(ctx)
        gates.append(g2)
        if g2.status == "FAIL":
            failures.append({"gate": g2.gate_id, "reason": "git tree is not clean"})

        model_base = ctx.repo_root / "engine" / "artifacts" / "repo_model"
        model_base.mkdir(parents=True, exist_ok=True)
        model_path = model_base / "repo_model.json"
        g3 = _gate_repo_model_generates(ctx, model_path)
        gates.append(g3)
        if g3.status == "FAIL":
            failures.append({"gate": g3.gate_id, "reason": "repo-model generation failed"})

        g4 = _gate_repo_model_schema(ctx)
        gates.append(g4)
        if g4.status == "FAIL":
            failures.append({"gate": g4.gate_id, "reason": str(g4.details.get("reason", "schema validation failed"))})

        tmp_dir = model_base / "_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        g5 = _gate_repo_model_determinism(ctx, g2.status == "PASS", tmp_dir)
        gates.append(g5)
        if g5.status == "FAIL":
            failures.append({"gate": g5.gate_id, "reason": "determinism checks failed"})

        g6, warning = _gate_dangling_edges_policy(ctx)
        gates.append(g6)
        if g6.status == "FAIL":
            failures.append({"gate": g6.gate_id, "reason": "dangling edges policy violation"})
        if warning is not None:
            warnings.append(warning)

        g7 = _gate_core_candidates_minimum(ctx)
        gates.append(g7)
        if g7.status == "FAIL":
            failures.append({"gate": g7.gate_id, "reason": "core candidate requirements failed"})

        g8 = _gate_agent_id_reproducible(ctx)
        gates.append(g8)
        if g8.status == "FAIL":
            failures.append({"gate": g8.gate_id, "reason": "agent_id reproducibility mismatch"})

        g9 = _gate_no_markdown_json(json_mode)
        gates.append(g9)
        if g9.status == "FAIL":
            failures.append({"gate": g9.gate_id, "reason": "json stdout formatting invalid"})

        state = "PASS" if all(g.status == "PASS" for g in gates) else "FAIL"
        exit_code = EXIT_PASS if state == "PASS" else EXIT_FAIL

        repo_fingerprint = None
        if ctx.model is not None:
            fingerprint = ctx.model.get("repo_fingerprint")
            repo_fingerprint = str(fingerprint) if fingerprint is not None else None

        report = _build_report(
            state=state,
            exit_code=exit_code,
            repo_root=repo_root,
            repo_fingerprint=repo_fingerprint,
            gates=gates,
            failures=failures,
            warnings=warnings,
            artifacts={"dir": None, "files": []},
        )

        artifacts = write_artifacts(report, ctx)
        report["artifacts"] = artifacts
        if ctx.out_dir is not None:
            (ctx.out_dir / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return exit_code, report
    except Exception as exc:
        report = _build_report(
            state="ERROR",
            exit_code=EXIT_ERROR,
            repo_root=repo_root,
            repo_fingerprint=None,
            gates=gates,
            failures=failures + [{"gate": "INTERNAL", "reason": str(exc)}],
            warnings=warnings,
            artifacts={"dir": None, "files": []},
        )
        artifacts = write_artifacts(report, ctx)
        report["artifacts"] = artifacts
        return EXIT_ERROR, report


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="contract-eval")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    out_dir = Path(args.out).resolve() if args.out else None
    exit_code, report = evaluate_contracts(strict=args.strict, out_path=out_dir, json_mode=args.json)

    if args.json:
        payload = json.dumps(report, sort_keys=True)
        print(payload)
    else:
        print(f"CONTRACT_EVAL:{report['state']}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(cli())
