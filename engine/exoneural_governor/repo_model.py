from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

IGNORE_DIRS = {
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

SCRIPT_EXTENSIONS = {".py", ".mjs", ".js", ".ts", ".sh", ".bash"}
RUN_PATTERN = re.compile(
    r"(?:^|\s)(?:python3?|node|bash|sh)\s+([./A-Za-z0-9_\-][A-Za-z0-9_./\-]*)"
)
DIRECT_PATH_PATTERN = re.compile(
    r"(?:^|\s)((?:\./)?scripts/[A-Za-z0-9_./\-]+\.(?:py|mjs|js|ts|sh|bash))"
)


class AgentKind:
    GITHUB_WORKFLOW = "GITHUB_WORKFLOW"
    GITHUB_COMPOSITE_ACTION = "GITHUB_COMPOSITE_ACTION"
    CLI_SCRIPT = "CLI_SCRIPT"
    RUNBOOK_DOC = "RUNBOOK_DOC"
    MAKEFILE = "MAKEFILE"
    OTHER = "OTHER"


def _repo_root_from_git(cwd: Path) -> Path | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, stderr=subprocess.DEVNULL
        )
        return Path(out.decode("utf-8").strip()).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def discover_repo_root(cwd: Path | None = None) -> Path:
    here = (cwd or Path.cwd()).resolve()
    from_git = _repo_root_from_git(here)
    if from_git is not None:
        return from_git
    current = here
    while True:
        has_git = (current / ".git").exists()
        has_markers = (current / "engine" / "pyproject.toml").exists() and (
            current / ".github"
        ).exists()
        if has_git or has_markers:
            return current
        if current.parent == current:
            raise RuntimeError("Unable to discover repository root")
        current = current.parent


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in sorted(dirnames) if d not in IGNORE_DIRS]
        base = Path(dirpath)
        for filename in sorted(filenames):
            files.append(base / filename)
    return files


def _rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _agent_id(rel_path: str) -> str:
    return hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:12]


def discover_agents(repo_root: Path) -> dict[str, dict[str, Any]]:
    agents: dict[str, dict[str, Any]] = {}

    def add(path: Path, kind: str) -> None:
        rel = _rel_posix(path, repo_root)
        aid = _agent_id(rel)
        agents[aid] = {
            "agent_id": aid,
            "path": rel,
            "kind": kind,
            "name": None,
        }

    wf_dir = repo_root / ".github" / "workflows"
    if wf_dir.exists():
        for p in sorted(wf_dir.glob("**/*.yml")):
            if p.is_file():
                add(p, AgentKind.GITHUB_WORKFLOW)

    actions_dir = repo_root / ".github" / "actions"
    if actions_dir.exists():
        for p in sorted(actions_dir.glob("**/action.yml")):
            if p.is_file():
                add(p, AgentKind.GITHUB_COMPOSITE_ACTION)

    makefile = repo_root / "Makefile"
    if makefile.exists() and makefile.is_file():
        add(makefile, AgentKind.MAKEFILE)

    for p in _iter_files(repo_root):
        rel = _rel_posix(p, repo_root)
        suffix = p.suffix.lower()
        if rel.startswith("scripts/") and suffix in {".mjs", ".ts", ".js", ".py", ".sh"}:
            add(p, AgentKind.CLI_SCRIPT)
        elif rel.startswith("tools/") and suffix == ".py" and p.name != "__init__.py":
            add(p, AgentKind.CLI_SCRIPT)
        elif rel.startswith("engine/scripts/") and suffix == ".py":
            add(p, AgentKind.CLI_SCRIPT)
    return dict(sorted(agents.items()))


def _safe_yaml_load(path: Path, parse_failures: list[str], repo_root: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        parse_failures.append(_rel_posix(path, repo_root))
        return {}


def _strip_ref_suffix(ref: str) -> str:
    text = ref.strip()
    if "@" in text:
        text = text.split("@", 1)[0]
    return text


def _resolve_local_ref_path(ref: str, src_file: Path, repo_root: Path) -> Path | None:
    text = _strip_ref_suffix(ref)
    candidates: list[Path] = []
    if text.startswith("./"):
        candidates.append((repo_root / text).resolve())
        candidates.append((src_file.parent / text).resolve())
    elif text.startswith(".github/"):
        candidates.append((repo_root / text).resolve())
    elif "/.github/actions/" in text:
        _, tail = text.split("/.github/actions/", 1)
        candidates.append((repo_root / ".github" / "actions" / tail).resolve())
    elif "/.github/workflows/" in text:
        _, tail = text.split("/.github/workflows/", 1)
        candidates.append((repo_root / ".github" / "workflows" / tail).resolve())
    else:
        return None

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _normalize_local_action_ref(ref: str, src_file: Path, repo_root: Path) -> Path | None:
    candidate = _resolve_local_ref_path(ref, src_file, repo_root)
    if candidate is None:
        return None
    if candidate.is_dir():
        action_file = candidate / "action.yml"
        return action_file if action_file.exists() else None
    if candidate.is_file() and candidate.name == "action.yml":
        return candidate
    if candidate.is_file():
        return candidate if candidate.suffix.lower() in {".yml", ".yaml"} else None
    action_file = candidate / "action.yml"
    return action_file if action_file.exists() else None


def _normalize_local_workflow_ref(ref: str, src_file: Path, repo_root: Path) -> Path | None:
    candidate = _resolve_local_ref_path(ref, src_file, repo_root)
    if candidate is None:
        return None
    if candidate.is_file() and candidate.suffix.lower() in {".yml", ".yaml"}:
        workflow_dir = (repo_root / ".github" / "workflows").resolve()
        try:
            candidate.relative_to(workflow_dir)
        except ValueError:
            return None
        return candidate
    return None


def _extract_run_script_refs(run_text: str) -> list[str]:
    refs: list[str] = []
    for pattern in (RUN_PATTERN, DIRECT_PATH_PATTERN):
        for match in pattern.finditer(run_text):
            refs.append(match.group(1))
    return refs


def _resolve_working_directory(step: dict[str, Any], repo_root: Path) -> Path:
    working_dir = step.get("working-directory")
    if not isinstance(working_dir, str) or not working_dir.strip():
        return repo_root
    path = Path(working_dir.strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _normalize_script_ref(
    ref: str,
    repo_root: Path,
    base_dir: Path | None = None,
) -> Path | None:
    path = ref.strip().strip("\"'")
    if not path:
        return None
    base = base_dir or repo_root
    candidate: Path
    if path.startswith("./"):
        candidate = (base / path).resolve()
    else:
        candidate = (repo_root / path).resolve()
    if not (candidate.exists() and candidate.is_file()):
        return None
    if candidate.suffix.lower() not in SCRIPT_EXTENSIONS:
        return None
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        return None
    return candidate


def _iter_workflow_steps(doc: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return []
    steps: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for job_data in jobs.values():
        if not isinstance(job_data, dict):
            continue
        job_steps = job_data.get("steps")
        if not isinstance(job_steps, list):
            continue
        for step in job_steps:
            if isinstance(step, dict):
                steps.append((job_data, step))
    return steps


def _iter_action_steps(doc: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    runs = doc.get("runs")
    if not isinstance(runs, dict):
        return []
    steps = runs.get("steps")
    if not isinstance(steps, list):
        return []
    return [(runs, step) for step in steps if isinstance(step, dict)]


def extract_edges(
    repo_root: Path,
    agents: dict[str, dict[str, Any]],
    parse_failures: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    path_to_id = {meta["path"]: aid for aid, meta in agents.items()}
    edge_set: set[tuple[str, str, str]] = set()
    dangling: set[tuple[str, str, str]] = set()

    def add_edge(src_path: str, dst_path: str, edge_type: str) -> None:
        src_id = path_to_id.get(src_path)
        dst_id = path_to_id.get(dst_path)
        if src_id is not None and dst_id is not None:
            edge_set.add((src_id, dst_id, edge_type))
            return
        if src_id is not None and dst_id is None and (repo_root / dst_path).exists():
            dangling.add((src_path, dst_path, edge_type))

    for meta in agents.values():
        kind = meta["kind"]
        rel_path = meta["path"]
        path = repo_root / rel_path
        if kind not in {
            AgentKind.GITHUB_WORKFLOW,
            AgentKind.GITHUB_COMPOSITE_ACTION,
            AgentKind.MAKEFILE,
        }:
            continue

        if kind == AgentKind.MAKEFILE:
            for line in path.read_text(encoding="utf-8").splitlines():
                for ref in _extract_run_script_refs(line):
                    resolved = _normalize_script_ref(ref, repo_root=repo_root, base_dir=repo_root)
                    if resolved is None:
                        continue
                    add_edge(rel_path, _rel_posix(resolved, repo_root), "RUNS_SCRIPT")
            continue

        doc = _safe_yaml_load(path, parse_failures, repo_root)
        if kind == AgentKind.GITHUB_WORKFLOW:
            jobs = doc.get("jobs")
            if isinstance(jobs, dict):
                for job_data in jobs.values():
                    if not isinstance(job_data, dict):
                        continue
                    job_uses = job_data.get("uses")
                    if isinstance(job_uses, str):
                        resolved_workflow = _normalize_local_workflow_ref(job_uses, path, repo_root)
                        if resolved_workflow is not None:
                            add_edge(
                                rel_path,
                                _rel_posix(resolved_workflow, repo_root),
                                "USES_REUSABLE_WORKFLOW",
                            )
            step_entries = _iter_workflow_steps(doc)
        else:
            step_entries = _iter_action_steps(doc)

        for parent, step in step_entries:
            uses = step.get("uses")
            if isinstance(uses, str):
                resolved_action = _normalize_local_action_ref(uses, path, repo_root)
                if resolved_action is not None:
                    add_edge(
                        rel_path,
                        _rel_posix(resolved_action, repo_root),
                        (
                            "USES_LOCAL_ACTION"
                            if kind == AgentKind.GITHUB_WORKFLOW
                            else "USES_ACTION_IN_ACTION"
                        ),
                    )

            run_text = step.get("run")
            if isinstance(run_text, str):
                base_dir = _resolve_working_directory(step, repo_root)
                if base_dir == repo_root:
                    base_dir = _resolve_working_directory(parent, repo_root)
                for ref in _extract_run_script_refs(run_text):
                    resolved = _normalize_script_ref(ref, repo_root=repo_root, base_dir=base_dir)
                    if resolved is None:
                        continue
                    add_edge(rel_path, _rel_posix(resolved, repo_root), "RUNS_SCRIPT")

    edges = [
        {"from_id": a, "to_id": b, "edge_type": t}
        for a, b, t in sorted(edge_set, key=lambda item: (item[0], item[1], item[2]))
    ]
    dangling_edges = [
        {"from_path": src, "to_path": dst, "edge_type": edge_type}
        for src, dst, edge_type in sorted(dangling, key=lambda item: (item[0], item[1], item[2]))
    ]
    return edges, dangling_edges


def compute_pagerank(
    node_ids: list[str],
    edges: list[tuple[str, str]],
    damping: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-10,
) -> dict[str, float]:
    sorted_nodes = sorted(node_ids)
    n = len(sorted_nodes)
    if n == 0:
        return {}
    out_neighbors: dict[str, list[str]] = {node: [] for node in sorted_nodes}
    incoming: dict[str, list[str]] = {node: [] for node in sorted_nodes}
    for src, dst in sorted(set(edges)):
        if src in out_neighbors and dst in incoming:
            out_neighbors[src].append(dst)
    for src in sorted_nodes:
        out_neighbors[src] = sorted(set(out_neighbors[src]))
        for dst in out_neighbors[src]:
            incoming[dst].append(src)

    rank = {node: 1.0 / n for node in sorted_nodes}
    base = (1.0 - damping) / n

    for _ in range(max_iter):
        dangling_sum = sum(rank[node] for node in sorted_nodes if not out_neighbors[node])
        new_rank: dict[str, float] = {}
        delta = 0.0
        for node in sorted_nodes:
            incoming_contrib = sum(rank[src] / len(out_neighbors[src]) for src in incoming[node])
            value = base + damping * (incoming_contrib + dangling_sum / n)
            new_rank[node] = value
            delta += abs(value - rank[node])
        rank = new_rank
        if delta < tol:
            break
    return rank


def compute_betweenness(node_ids: list[str], edges: list[tuple[str, str]]) -> dict[str, float]:
    nodes = sorted(node_ids)
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for src, dst in sorted(set(edges)):
        if src in adjacency and dst in adjacency:
            adjacency[src].append(dst)
    for node in nodes:
        adjacency[node] = sorted(set(adjacency[node]))

    cb = {node: 0.0 for node in nodes}
    for source in nodes:
        stack: list[str] = []
        predecessors: dict[str, list[str]] = {w: [] for w in nodes}
        sigma = {w: 0.0 for w in nodes}
        sigma[source] = 1.0
        distance = {w: -1 for w in nodes}
        distance[source] = 0
        queue: collections.deque[str] = collections.deque([source])

        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adjacency[v]:
                if distance[w] < 0:
                    queue.append(w)
                    distance[w] = distance[v] + 1
                if distance[w] == distance[v] + 1:
                    sigma[w] += sigma[v]
                    predecessors[w].append(v)

        delta = {w: 0.0 for w in nodes}
        while stack:
            w = stack.pop()
            if sigma[w] > 0:
                coeff = (1.0 + delta[w]) / sigma[w]
                for v in sorted(predecessors[w]):
                    delta[v] += sigma[v] * coeff
            if w != source:
                cb[w] += delta[w]

    n = len(nodes)
    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for node in nodes:
            cb[node] *= scale
    else:
        cb = {node: 0.0 for node in nodes}
    return cb


def _compute_core_candidates(
    agents: dict[str, dict[str, Any]], edges: list[dict[str, str]]
) -> list[dict[str, Any]]:
    node_ids = sorted(agents.keys())
    edge_pairs = [(edge["from_id"], edge["to_id"]) for edge in edges]
    pagerank = compute_pagerank(node_ids, edge_pairs)
    betweenness = compute_betweenness(node_ids, edge_pairs)

    max_pr = max(pagerank.values(), default=0.0)
    max_bc = max(betweenness.values(), default=0.0)

    in_deg = {nid: 0 for nid in node_ids}
    out_deg = {nid: 0 for nid in node_ids}
    for src, dst in edge_pairs:
        if src in out_deg:
            out_deg[src] += 1
        if dst in in_deg:
            in_deg[dst] += 1

    scored: list[dict[str, Any]] = []
    for nid in node_ids:
        pr = pagerank.get(nid, 0.0)
        bc = betweenness.get(nid, 0.0)
        pr_norm = (pr / max_pr) if max_pr > 0 else 0.0
        bc_norm = (bc / max_bc) if max_bc > 0 else 0.0
        core_score = (0.6 * pr_norm) + (0.4 * bc_norm)
        scored.append(
            {
                "agent_id": nid,
                "path": agents[nid]["path"],
                "kind": agents[nid]["kind"],
                "pr": pr,
                "bc": bc,
                "pr_norm": pr_norm,
                "bc_norm": bc_norm,
                "core_score": core_score,
                "degree": in_deg[nid] + out_deg[nid],
            }
        )

    active_nodes = sum(1 for nid in node_ids if (in_deg[nid] + out_deg[nid]) > 0)
    k = min(25, max(5, round(0.08 * active_nodes)))
    ordered = sorted(
        scored,
        key=lambda r: (-r["core_score"], -r["pr_norm"], -r["bc_norm"], r["agent_id"]),
    )

    candidates: list[dict[str, Any]] = []
    for i, row in enumerate(ordered[:k], start=1):
        candidates.append(
            {
                "agent_id": row["agent_id"],
                "path": row["path"],
                "kind": row["kind"],
                "pr": row["pr"],
                "bc": row["bc"],
                "core_score": row["core_score"],
                "rank": i,
            }
        )
    return candidates


def _repo_fingerprint(repo_root: Path, agents: dict[str, dict[str, Any]]) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, stderr=subprocess.DEVNULL
        )
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    parts: list[str] = []
    for aid in sorted(agents):
        rel = agents[aid]["path"]
        fpath = repo_root / rel
        try:
            digest = hashlib.sha256(fpath.read_bytes()).hexdigest()
        except OSError:
            digest = ""
        parts.append(f"{rel}\n{digest}\n")
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()


def build_repo_model(repo_root: Path) -> dict[str, Any]:
    agents = discover_agents(repo_root)
    parse_failures: list[str] = []
    edges, dangling_edges = extract_edges(repo_root, agents, parse_failures)
    core_candidates = _compute_core_candidates(agents, edges)
    return {
        "repo_root": repo_root.as_posix(),
        "repo_fingerprint": _repo_fingerprint(repo_root, agents),
        "agents": [agents[aid] for aid in sorted(agents)],
        "edges": edges,
        "core_candidates": core_candidates,
        "counts": {
            "agents_count": len(agents),
            "edges_count": len(edges),
            "core_candidates_count": len(core_candidates),
        },
        "unknowns": {
            "parse_failures": sorted(parse_failures),
            "dangling_edges": dangling_edges,
        },
    }


def write_repo_model_artifact(model: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cmd_repo_model(
    out: Path | None = None,
    cwd: Path | None = None,
    emit_stdout: bool = False,
) -> int:
    repo_root = discover_repo_root(cwd)
    output = out or (repo_root / "engine" / "artifacts" / "repo_model" / "repo_model.json")
    if not output.is_absolute():
        output = repo_root / output
    model = build_repo_model(repo_root)
    write_repo_model_artifact(model, output)
    if emit_stdout:
        print(json.dumps(model, indent=2, sort_keys=True))
    else:
        print(f"WROTE:{output.relative_to(repo_root).as_posix()}")
    return 0


def build_repo_model_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "repo-model",
        help="Build deterministic repository agent wiring model and centrality cores.",
    )
    parser.add_argument(
        "--out",
        default="engine/artifacts/repo_model/repo_model.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print JSON to stdout instead of one-line status output.",
    )
