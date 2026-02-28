from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
from collections import deque
from pathlib import Path
from typing import Any

import yaml

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "out",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "vendor",
}

SCRIPT_SUFFIXES = {".py", ".mjs", ".js", ".ts", ".sh", ".bash"}
EXECUTABLES = {"python", "python3", "node", "bash", "sh"}


class Kind:
    GITHUB_WORKFLOW = "GITHUB_WORKFLOW"
    GITHUB_COMPOSITE_ACTION = "GITHUB_COMPOSITE_ACTION"
    CLI_SCRIPT = "CLI_SCRIPT"
    RUNBOOK_DOC = "RUNBOOK_DOC"
    MAKEFILE = "MAKEFILE"
    OTHER = "OTHER"


def _sha12(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _run_git(args: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    return proc.returncode, proc.stdout.strip()


def discover_repo_root(cwd: Path | None = None) -> Path:
    start = (cwd or Path.cwd()).resolve()
    code, out = _run_git(["rev-parse", "--show-toplevel"], start)
    if code == 0 and out:
        return Path(out).resolve()

    for candidate in [start, *start.parents]:
        has_git = (candidate / ".git").exists()
        has_markers = (candidate / "engine" / "pyproject.toml").exists() and (
            candidate / ".github"
        ).exists()
        if has_git or has_markers:
            return candidate
    raise RuntimeError("Could not discover repository root")


def _iter_files(base: Path) -> list[Path]:
    out: list[Path] = []
    if not base.exists():
        return out
    for path in base.rglob("*"):
        if path.is_dir():
            continue
        rel_parts = path.relative_to(base).parts
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        out.append(path)
    return sorted(out)


def _rel(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _kind_for_path(repo_root: Path, path: Path) -> str:
    rel = _rel(repo_root, path)
    if rel.startswith(".github/workflows/") and path.suffix in {".yml", ".yaml"}:
        return Kind.GITHUB_WORKFLOW
    if rel.startswith(".github/actions/") and path.name in {"action.yml", "action.yaml"}:
        return Kind.GITHUB_COMPOSITE_ACTION
    if rel == "Makefile":
        return Kind.MAKEFILE
    if path.suffix in SCRIPT_SUFFIXES and (
        rel.startswith("scripts/")
        or rel.startswith("tools/")
        or rel.startswith("engine/scripts/")
    ):
        return Kind.CLI_SCRIPT
    if path.suffix.lower() == ".md" and "runbook" in path.name.lower():
        return Kind.RUNBOOK_DOC
    return Kind.OTHER


def discover_agents(repo_root: Path) -> list[dict[str, Any]]:
    paths: set[Path] = set()
    paths.update(_iter_files(repo_root / ".github" / "workflows"))
    paths.update(_iter_files(repo_root / ".github" / "actions"))

    makefile = repo_root / "Makefile"
    if makefile.exists():
        paths.add(makefile)

    for sub in (repo_root / "scripts", repo_root / "tools", repo_root / "engine" / "scripts"):
        for p in _iter_files(sub):
            if p.suffix in SCRIPT_SUFFIXES:
                paths.add(p)

    agents: list[dict[str, Any]] = []
    for path in sorted(paths):
        rel = _rel(repo_root, path)
        agents.append(
            {
                "agent_id": _sha12(rel),
                "path": rel,
                "kind": _kind_for_path(repo_root, path),
                "name": None,
            }
        )
    return agents


def _safe_load_yaml(path: Path, parse_failures: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        parse_failures.append(path.as_posix())
        return None


def _iter_steps(data: Any) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if isinstance(data.get("steps"), list):
            for s in data["steps"]:
                if isinstance(s, dict):
                    steps.append(s)
        for v in data.values():
            steps.extend(_iter_steps(v))
    elif isinstance(data, list):
        for item in data:
            steps.extend(_iter_steps(item))
    return steps


def _resolve_local_action_target(repo_root: Path, source_file: Path, uses_value: str) -> Path | None:
    text = uses_value.strip()
    if "@" in text:
        text = text.split("@", 1)[0]

    candidate: Path | None = None
    if text.startswith("./"):
        candidate = (source_file.parent / text).resolve()
    elif text.startswith(".github/"):
        candidate = (repo_root / text).resolve()
    elif "/.github/actions/" in text:
        suffix = text.split("/.github/actions/", 1)[1]
        candidate = (repo_root / ".github" / "actions" / suffix).resolve()

    if candidate is None:
        return None
    if candidate.is_dir():
        for name in ("action.yml", "action.yaml"):
            f = candidate / name
            if f.exists():
                return f
        return None
    if candidate.exists():
        return candidate
    return None


def _resolve_script_candidate(repo_root: Path, source_file: Path, token: str) -> Path | None:
    if not token:
        return None
    token = token.strip().strip('"\'`')
    if token.startswith("$"):
        return None

    if token.startswith("./"):
        candidate = (source_file.parent / token).resolve()
    else:
        candidate = (repo_root / token).resolve()
    if candidate.exists() and candidate.is_file() and candidate.suffix in SCRIPT_SUFFIXES:
        return candidate
    return None


def _extract_run_paths(repo_root: Path, source_file: Path, run_value: str) -> list[Path]:
    found: set[Path] = set()
    for raw_line in run_value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = line.split()
        if not tokens:
            continue

        if tokens[0] in EXECUTABLES and len(tokens) > 1:
            target = _resolve_script_candidate(repo_root, source_file, tokens[1])
            if target:
                found.add(target)

        for token in tokens:
            if token.startswith("./scripts/") or token.startswith("scripts/"):
                target = _resolve_script_candidate(repo_root, source_file, token)
                if target:
                    found.add(target)
            elif any(token.endswith(ext) for ext in SCRIPT_SUFFIXES):
                target = _resolve_script_candidate(repo_root, source_file, token)
                if target:
                    found.add(target)
    return sorted(found)


def _extract_makefile_run_edges(repo_root: Path, makefile: Path) -> list[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if not line.startswith("\t"):
            continue
        for path in _extract_run_paths(repo_root, makefile, line):
            edges.add((_rel(repo_root, makefile), _rel(repo_root, path), "RUNS_SCRIPT"))
    return sorted(edges)


def extract_wiring_edges(repo_root: Path, agents: list[dict[str, Any]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    agent_paths = {a["path"] for a in agents}
    parse_failures: list[str] = []
    edge_rows: set[tuple[str, str, str]] = set()

    workflow_files = sorted((repo_root / ".github" / "workflows").glob("**/*.yml")) + sorted(
        (repo_root / ".github" / "workflows").glob("**/*.yaml")
    )
    action_files = sorted((repo_root / ".github" / "actions").glob("**/action.yml")) + sorted(
        (repo_root / ".github" / "actions").glob("**/action.yaml")
    )

    # A + C on workflows
    for wf in workflow_files:
        data = _safe_load_yaml(wf, parse_failures)
        if not isinstance(data, dict):
            continue
        src = _rel(repo_root, wf)
        for step in _iter_steps(data):
            uses = step.get("uses")
            if isinstance(uses, str):
                target = _resolve_local_action_target(repo_root, wf, uses)
                if target is not None:
                    dst = _rel(repo_root, target)
                    edge_rows.add((src, dst, "USES_LOCAL_ACTION"))
            run_value = step.get("run")
            if isinstance(run_value, str):
                for script_path in _extract_run_paths(repo_root, wf, run_value):
                    edge_rows.add((src, _rel(repo_root, script_path), "RUNS_SCRIPT"))

    # B + C on composite actions
    for action in action_files:
        data = _safe_load_yaml(action, parse_failures)
        if not isinstance(data, dict):
            continue
        src = _rel(repo_root, action)
        runs = data.get("runs", {})
        steps = runs.get("steps", []) if isinstance(runs, dict) else []
        if not isinstance(steps, list):
            steps = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if isinstance(uses, str):
                target = _resolve_local_action_target(repo_root, action, uses)
                if target is not None:
                    edge_rows.add((src, _rel(repo_root, target), "USES_ACTION_IN_ACTION"))
            run_value = step.get("run")
            if isinstance(run_value, str):
                for script_path in _extract_run_paths(repo_root, action, run_value):
                    edge_rows.add((src, _rel(repo_root, script_path), "RUNS_SCRIPT"))

    # D optional
    makefile = repo_root / "Makefile"
    if makefile.exists():
        edge_rows.update(_extract_makefile_run_edges(repo_root, makefile))

    # add referenced paths as nodes if discovered by extraction but missing from initial list
    for _, dst, _ in list(edge_rows):
        if dst not in agent_paths:
            agent_paths.add(dst)

    edges = [
        {
            "from_id": _sha12(src),
            "to_id": _sha12(dst),
            "edge_type": edge_type,
            "from_path": src,
            "to_path": dst,
        }
        for src, dst, edge_type in sorted(edge_rows, key=lambda x: (x[0], x[1], x[2]))
    ]
    return edges, {"parse_failures": sorted(set(parse_failures))}


def _build_graph(nodes: list[str], edges: list[tuple[str, str]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    out_adj = {n: [] for n in nodes}
    in_adj = {n: [] for n in nodes}
    for src, dst in sorted(set(edges)):
        if src not in out_adj:
            out_adj[src] = []
            in_adj[src] = []
        if dst not in out_adj:
            out_adj[dst] = []
            in_adj[dst] = []
        out_adj[src].append(dst)
        in_adj[dst].append(src)
    for n in sorted(out_adj):
        out_adj[n] = sorted(set(out_adj[n]))
        in_adj[n] = sorted(set(in_adj[n]))
    return out_adj, in_adj


def pagerank(nodes: list[str], edges: list[tuple[str, str]], damping: float = 0.85, max_iter: int = 100, tol: float = 1e-10) -> dict[str, float]:
    ordered = sorted(set(nodes))
    if not ordered:
        return {}
    out_adj, in_adj = _build_graph(ordered, edges)
    n = len(ordered)
    ranks = {node: 1.0 / n for node in ordered}

    for _ in range(max_iter):
        dangling = sum(ranks[node] for node in ordered if not out_adj[node])
        new_ranks: dict[str, float] = {}
        diff = 0.0
        for node in ordered:
            value = (1.0 - damping) / n
            value += damping * dangling / n
            for src in in_adj[node]:
                value += damping * (ranks[src] / len(out_adj[src]))
            new_ranks[node] = value
            diff += abs(value - ranks[node])
        ranks = new_ranks
        if diff <= tol:
            break

    total = sum(ranks.values())
    if total > 0:
        ranks = {k: v / total for k, v in ranks.items()}
    return ranks


def betweenness_centrality_brandes(nodes: list[str], edges: list[tuple[str, str]]) -> dict[str, float]:
    ordered = sorted(set(nodes))
    out_adj, _ = _build_graph(ordered, edges)
    bc = {v: 0.0 for v in ordered}

    for s in ordered:
        stack: list[str] = []
        pred: dict[str, list[str]] = {w: [] for w in ordered}
        sigma = {w: 0.0 for w in ordered}
        dist = {w: -1 for w in ordered}
        sigma[s] = 1.0
        dist[s] = 0

        q: deque[str] = deque([s])
        while q:
            v = q.popleft()
            stack.append(v)
            for w in out_adj[v]:
                if dist[w] < 0:
                    q.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        delta = {w: 0.0 for w in ordered}
        while stack:
            w = stack.pop()
            for v in sorted(pred[w]):
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                bc[w] += delta[w]

    n = len(ordered)
    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for node in ordered:
            bc[node] *= scale
    else:
        for node in ordered:
            bc[node] = 0.0
    return bc


def _repo_fingerprint(repo_root: Path, scan_paths: list[str]) -> str:
    code, out = _run_git(["rev-parse", "HEAD"], repo_root)
    if code == 0 and out:
        return out
    sha = hashlib.sha256()
    for rel in sorted(scan_paths):
        path = repo_root / rel
        if not path.exists() or not path.is_file():
            continue
        file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        sha.update(rel.encode("utf-8"))
        sha.update(b"\n")
        sha.update(file_sha.encode("utf-8"))
        sha.update(b"\n")
    return sha.hexdigest()


def generate_repo_model(repo_root: Path) -> dict[str, Any]:
    agents = discover_agents(repo_root)
    edges, unknowns = extract_wiring_edges(repo_root, agents)

    by_path = {a["path"]: a for a in agents}
    for edge in edges:
        for rel in (edge["from_path"], edge["to_path"]):
            if rel not in by_path:
                p = repo_root / rel
                by_path[rel] = {
                    "agent_id": _sha12(rel),
                    "path": rel,
                    "kind": _kind_for_path(repo_root, p),
                    "name": None,
                }

    all_agents = sorted(by_path.values(), key=lambda a: a["agent_id"])
    node_ids = sorted(a["agent_id"] for a in all_agents)
    directed = [(e["from_id"], e["to_id"]) for e in edges]

    pr = pagerank(node_ids, directed)
    bc = betweenness_centrality_brandes(node_ids, directed)
    max_pr = max(pr.values()) if pr else 0.0
    max_bc = max(bc.values()) if bc else 0.0

    deg: dict[str, int] = {node: 0 for node in node_ids}
    for src, dst in directed:
        deg[src] += 1
        deg[dst] += 1
    n_nonzero = sum(1 for v in deg.values() if v > 0)
    k = max(5, min(25, round(0.08 * n_nonzero))) if n_nonzero else 5

    ranked: list[dict[str, Any]] = []
    path_by_id = {a["agent_id"]: a["path"] for a in all_agents}
    kind_by_id = {a["agent_id"]: a["kind"] for a in all_agents}
    for node in node_ids:
        pr_norm = (pr.get(node, 0.0) / max_pr) if max_pr > 0 else 0.0
        bc_norm = (bc.get(node, 0.0) / max_bc) if max_bc > 0 else 0.0
        score = 0.6 * pr_norm + 0.4 * bc_norm
        ranked.append(
            {
                "agent_id": node,
                "path": path_by_id[node],
                "kind": kind_by_id[node],
                "pr": pr.get(node, 0.0),
                "bc": bc.get(node, 0.0),
                "pr_norm": pr_norm,
                "bc_norm": bc_norm,
                "core_score": score,
            }
        )

    ranked.sort(
        key=lambda r: (
            -r["core_score"],
            -r["pr_norm"],
            -r["bc_norm"],
            r["agent_id"],
        )
    )
    core_candidates = []
    for idx, row in enumerate(ranked[:k], start=1):
        core_candidates.append(
            {
                "agent_id": row["agent_id"],
                "path": row["path"],
                "kind": row["kind"],
                "pr": row["pr"],
                "bc": row["bc"],
                "core_score": row["core_score"],
                "rank": idx,
            }
        )

    scan_paths = [a["path"] for a in all_agents]
    return {
        "repo_root": repo_root.as_posix(),
        "repo_fingerprint": _repo_fingerprint(repo_root, scan_paths),
        "agents": all_agents,
        "agents_count": len(all_agents),
        "wiring": {"edges": edges, "edges_count": len(edges)},
        "centrality": {
            "pagerank": {k: pr[k] for k in sorted(pr)},
            "betweenness": {k: bc[k] for k in sorted(bc)},
        },
        "core_candidates": core_candidates,
        "core_candidates_count": len(core_candidates),
        "unknowns": unknowns,
    }


def write_repo_model(out_path: Path, model: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo-model")
    parser.add_argument("--out", default="engine/artifacts/repo_model/repo_model.json")
    args = parser.parse_args(argv)

    repo_root = discover_repo_root(Path.cwd())
    model = generate_repo_model(repo_root)
    write_repo_model(Path(args.out), model)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
