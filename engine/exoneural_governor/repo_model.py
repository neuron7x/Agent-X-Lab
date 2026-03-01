from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shlex
import subprocess
from collections import deque
from pathlib import Path
from typing import Any

import networkx as nx
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
        or rel.startswith("engine/tools/")
    ):
        if path.name == "__init__.py" and not (
            rel.startswith("scripts/")
            or rel.startswith("engine/scripts/")
        ):
            return Kind.OTHER
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

    for sub in (
        repo_root / "scripts",
        repo_root / "tools",
        repo_root / "engine" / "scripts",
        repo_root / "engine" / "tools",
        repo_root / "engine" / "exoneural_governor",
        repo_root / "tools" / "dao-arbiter" / "dao_lifebook",
    ):
        for p in _iter_files(sub):
            if p.suffix == ".py" and p.name == "__init__.py":
                if _rel(repo_root, p).startswith("engine/tools/"):
                    continue
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


def _safe_load_yaml(repo_root: Path, path: Path, parse_failures: list[str]) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        parse_failures.append(_rel(repo_root, path))
        return None


def _iter_steps(data: Any) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if isinstance(data, dict):
        if isinstance(data.get("steps"), list):
            for step in data["steps"]:
                if isinstance(step, dict):
                    steps.append(step)
        for value in data.values():
            steps.extend(_iter_steps(value))
    elif isinstance(data, list):
        for item in data:
            steps.extend(_iter_steps(item))
    return steps


def _normalize_local_action_ref(
    repo_root: Path, src_file: Path, uses_value: str
) -> Path | None:
    ref = uses_value.strip()
    if "@" in ref:
        ref = ref.split("@", 1)[0]

    candidates: list[Path] = []
    if ref.startswith("./"):
        candidates.append((repo_root / ref).resolve())
        candidates.append((src_file.parent / ref).resolve())
    elif ref.startswith(".github/"):
        candidates.append((repo_root / ref).resolve())
    elif "/.github/actions/" in ref:
        suffix = ref.split("/.github/actions/", 1)[1]
        candidates.append((repo_root / ".github" / "actions" / suffix).resolve())
    else:
        candidates.append((repo_root / ref).resolve())

    for candidate in candidates:
        if candidate.is_dir():
            for name in ("action.yml", "action.yaml"):
                action_file = candidate / name
                if action_file.exists() and action_file.is_file():
                    return action_file
        if candidate.is_file() and candidate.name in {"action.yml", "action.yaml"}:
            return candidate
    return None


def _normalize_local_workflow_ref(
    repo_root: Path, src_file: Path, uses_value: str
) -> Path | None:
    ref = uses_value.strip()
    if "@" in ref:
        ref = ref.split("@", 1)[0]

    candidates: list[Path] = []
    if ref.startswith("./"):
        candidates.append((repo_root / ref).resolve())
        candidates.append((src_file.parent / ref).resolve())
    elif ref.startswith(".github/"):
        candidates.append((repo_root / ref).resolve())
    else:
        candidates.append((repo_root / ref).resolve())

    for candidate in candidates:
        if (
            candidate.is_file()
            and candidate.suffix in {".yml", ".yaml"}
            and _rel(repo_root, candidate).startswith(".github/workflows/")
        ):
            return candidate
    return None


def _normalize_script_ref(
    repo_root: Path,
    token: str,
    base_dir: Path | None = None,
    source_file: Path | None = None,
) -> Path | None:
    if not token:
        return None
    normalized = token.strip().strip('"\'`')
    if normalized.startswith("$"):
        return None

    if normalized.startswith("./"):
        base = (base_dir or repo_root).resolve()
        candidate = (base / normalized).resolve()
        if not candidate.exists() and source_file is not None:
            candidate = (source_file.parent / normalized).resolve()
    else:
        candidate = (repo_root / normalized).resolve()

    if candidate.exists() and candidate.is_file() and candidate.suffix in SCRIPT_SUFFIXES:
        return candidate
    return None


def _extract_run_paths(
    repo_root: Path,
    source_file: Path,
    run_value: str,
    base_dir: Path | None = None,
) -> list[Path]:
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
            target = _normalize_script_ref(
                repo_root,
                tokens[1],
                base_dir=base_dir,
                source_file=source_file,
            )
            if target:
                found.add(target)

        for token in tokens:
            if token.startswith("./scripts/") or token.startswith("scripts/"):
                target = _normalize_script_ref(
                    repo_root,
                    token,
                    base_dir=base_dir,
                    source_file=source_file,
                )
                if target:
                    found.add(target)
            elif any(token.endswith(ext) for ext in SCRIPT_SUFFIXES):
                target = _normalize_script_ref(
                    repo_root,
                    token,
                    base_dir=base_dir,
                    source_file=source_file,
                )
                if target:
                    found.add(target)
    return sorted(found)


def _extract_makefile_run_edges(repo_root: Path, makefile: Path) -> list[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if not line.startswith("\t"):
            continue
        for path in _extract_run_paths(repo_root, makefile, line, base_dir=repo_root):
            edges.add((_rel(repo_root, makefile), _rel(repo_root, path), "RUNS_SCRIPT"))
    return sorted(edges)


def _resolve_relative_import(
    current_file: Path,
    module: str | None,
    level: int,
    name: str,
) -> Path | None:
    base_dir = current_file.parent
    parent = base_dir
    for _ in range(max(0, level - 1)):
        parent = parent.parent

    module_parts = [part for part in (module.split(".") if module else []) if part]
    name_parts = [part for part in name.split(".") if part]

    if module_parts or name_parts:
        candidate = parent.joinpath(*(module_parts + name_parts))
        py_candidate = candidate.with_suffix(".py")
        if py_candidate.exists() and py_candidate.is_file():
            return py_candidate
    return None


def _resolve_same_root_absolute_import(
    root_dir: Path,
    module_name: str,
) -> Path | None:
    parts = [part for part in module_name.split(".") if part]
    if not parts:
        return None
    candidate = root_dir.joinpath(*parts).with_suffix(".py")
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def _extract_python_import_edges(
    repo_root: Path,
    bounded_paths: set[str],
) -> list[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    bounded_files = sorted(repo_root / rel for rel in bounded_paths)

    group_roots = [
        repo_root / "tools" / "dao-arbiter" / "dao_lifebook",
        repo_root / "engine" / "exoneural_governor",
    ]

    for src_file in bounded_files:
        if src_file.suffix != ".py" or not src_file.exists():
            continue
        src_rel = _rel(repo_root, src_file)

        root_dir: Path | None = None
        for grp in group_roots:
            try:
                src_file.relative_to(grp)
                root_dir = grp
                break
            except ValueError:
                continue
        if root_dir is None:
            continue

        try:
            tree = ast.parse(src_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                level = int(node.level or 0)
                module = node.module
                for alias in node.names:
                    alias_name = alias.name
                    dst_file: Path | None = None
                    if level > 0:
                        dst_file = _resolve_relative_import(
                            src_file,
                            module,
                            level,
                            alias_name,
                        )
                        if dst_file is None and module:
                            dst_file = _resolve_relative_import(
                                src_file,
                                module,
                                level,
                                "",
                            )
                    elif module:
                        full = module if alias_name == "*" else f"{module}.{alias_name}"
                        dst_file = _resolve_same_root_absolute_import(root_dir, full)
                        if dst_file is None:
                            dst_file = _resolve_same_root_absolute_import(root_dir, module)
                    elif alias_name != "*":
                        dst_file = _resolve_same_root_absolute_import(root_dir, alias_name)

                    if dst_file is None or not dst_file.exists():
                        continue
                    dst_rel = _rel(repo_root, dst_file)
                    if dst_rel == src_rel or dst_rel not in bounded_paths:
                        continue
                    edges.add((src_rel, dst_rel, "IMPORTS_PY"))

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    dst_file = _resolve_same_root_absolute_import(root_dir, alias.name)
                    if dst_file is None or not dst_file.exists():
                        continue
                    dst_rel = _rel(repo_root, dst_file)
                    if dst_rel == src_rel or dst_rel not in bounded_paths:
                        continue
                    edges.add((src_rel, dst_rel, "IMPORTS_PY"))

    return sorted(edges)


def extract_wiring_edges(
    repo_root: Path, agents: list[dict[str, Any]]
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    known_paths = {agent["path"] for agent in agents}
    parse_failures: list[str] = []
    dangling_edges: list[dict[str, str]] = []
    edge_rows: set[tuple[str, str, str]] = set()

    workflow_dir = repo_root / ".github" / "workflows"
    action_dir = repo_root / ".github" / "actions"
    workflow_files = sorted(workflow_dir.glob("**/*.yml")) + sorted(
        workflow_dir.glob("**/*.yaml")
    )
    action_files = sorted(action_dir.glob("**/action.yml")) + sorted(
        action_dir.glob("**/action.yaml")
    )

    for workflow in workflow_files:
        data = _safe_load_yaml(repo_root, workflow, parse_failures)
        if not isinstance(data, dict):
            continue

        source_path = _rel(repo_root, workflow)

        jobs = data.get("jobs", {})
        if isinstance(jobs, dict):
            for _, job_data in sorted(jobs.items()):
                if not isinstance(job_data, dict):
                    continue
                uses_value = job_data.get("uses")
                if isinstance(uses_value, str):
                    target = _normalize_local_workflow_ref(repo_root, workflow, uses_value)
                    if target is not None:
                        edge_rows.add(
                            (
                                source_path,
                                _rel(repo_root, target),
                                "USES_REUSABLE_WORKFLOW",
                            )
                        )

        for step in _iter_steps(data):
            uses = step.get("uses")
            if isinstance(uses, str):
                target = _normalize_local_action_ref(repo_root, workflow, uses)
                if target is not None:
                    edge_rows.add(
                        (source_path, _rel(repo_root, target), "USES_LOCAL_ACTION")
                    )

            run_value = step.get("run")
            if isinstance(run_value, str):
                base_dir = repo_root
                working_dir = step.get("working-directory")
                if isinstance(working_dir, str) and working_dir.strip():
                    base_dir = (repo_root / working_dir.strip()).resolve()
                for script_path in _extract_run_paths(
                    repo_root,
                    workflow,
                    run_value,
                    base_dir=base_dir,
                ):
                    edge_rows.add((source_path, _rel(repo_root, script_path), "RUNS_SCRIPT"))

    for action in action_files:
        data = _safe_load_yaml(repo_root, action, parse_failures)
        if not isinstance(data, dict):
            continue

        source_path = _rel(repo_root, action)
        runs = data.get("runs", {})
        steps = runs.get("steps", []) if isinstance(runs, dict) else []
        if not isinstance(steps, list):
            steps = []

        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if isinstance(uses, str):
                target = _normalize_local_action_ref(repo_root, action, uses)
                if target is not None:
                    edge_rows.add(
                        (
                            source_path,
                            _rel(repo_root, target),
                            "USES_ACTION_IN_ACTION",
                        )
                    )

            run_value = step.get("run")
            if isinstance(run_value, str):
                base_dir = repo_root
                working_dir = step.get("working-directory")
                if isinstance(working_dir, str) and working_dir.strip():
                    base_dir = (repo_root / working_dir.strip()).resolve()
                for script_path in _extract_run_paths(
                    repo_root,
                    action,
                    run_value,
                    base_dir=base_dir,
                ):
                    edge_rows.add((source_path, _rel(repo_root, script_path), "RUNS_SCRIPT"))

    makefile = repo_root / "Makefile"
    if makefile.exists():
        edge_rows.update(_extract_makefile_run_edges(repo_root, makefile))

    bounded_import_paths = {
        path
        for path in known_paths
        if path.startswith("tools/dao-arbiter/dao_lifebook/")
        or path.startswith("engine/exoneural_governor/")
    }
    edge_rows.update(_extract_python_import_edges(repo_root, bounded_import_paths))

    resolved_edges: list[dict[str, str]] = []
    for src_path, dst_path, edge_type in sorted(edge_rows, key=lambda x: (x[0], x[1], x[2])):
        dst_exists = (repo_root / dst_path).exists()
        if src_path in known_paths and dst_path in known_paths:
            resolved_edges.append(
                {
                    "from_id": _sha12(src_path),
                    "to_id": _sha12(dst_path),
                    "edge_type": edge_type,
                    "from_path": src_path,
                    "to_path": dst_path,
                }
            )
        elif dst_exists:
            dangling_edges.append(
                {
                    "from_path": src_path,
                    "to_path": dst_path,
                    "edge_type": edge_type,
                }
            )

    return resolved_edges, {
        "parse_failures": sorted(set(parse_failures)),
        "dangling_edges": sorted(
            dangling_edges,
            key=lambda item: (item["from_path"], item["to_path"], item["edge_type"]),
        ),
    }


def _build_graph(
    nodes: list[str], edges: list[tuple[str, str]]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
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
    for node in sorted(out_adj):
        out_adj[node] = sorted(set(out_adj[node]))
        in_adj[node] = sorted(set(in_adj[node]))
    return out_adj, in_adj


def pagerank(
    nodes: list[str],
    edges: list[tuple[str, str]],
    damping: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-10,
) -> dict[str, float]:
    ordered = sorted(set(nodes))
    if not ordered:
        return {}
    out_adj, in_adj = _build_graph(ordered, edges)
    n = len(ordered)
    ranks = {node: 1.0 / n for node in ordered}

    for _ in range(max_iter):
        dangling = sum(ranks[node] for node in ordered if not out_adj[node])
        new_ranks: dict[str, float] = {}
        delta = 0.0
        for node in ordered:
            value = (1.0 - damping) / n
            value += damping * dangling / n
            for src in in_adj[node]:
                value += damping * (ranks[src] / len(out_adj[src]))
            new_ranks[node] = value
            delta += abs(value - ranks[node])
        ranks = new_ranks
        if delta <= tol:
            break

    total = sum(ranks.values())
    if total > 0:
        ranks = {node: value / total for node, value in ranks.items()}
    return ranks


def betweenness_centrality_brandes(
    nodes: list[str], edges: list[tuple[str, str]]
) -> dict[str, float]:
    ordered = sorted(set(nodes))
    out_adj, _ = _build_graph(ordered, edges)
    bc = {node: 0.0 for node in ordered}

    for source in ordered:
        stack: list[str] = []
        pred: dict[str, list[str]] = {node: [] for node in ordered}
        sigma = {node: 0.0 for node in ordered}
        dist = {node: -1 for node in ordered}
        sigma[source] = 1.0
        dist[source] = 0

        q: deque[str] = deque([source])
        while q:
            vertex = q.popleft()
            stack.append(vertex)
            for nxt in out_adj[vertex]:
                if dist[nxt] < 0:
                    q.append(nxt)
                    dist[nxt] = dist[vertex] + 1
                if dist[nxt] == dist[vertex] + 1:
                    sigma[nxt] += sigma[vertex]
                    pred[nxt].append(vertex)

        delta = {node: 0.0 for node in ordered}
        while stack:
            node = stack.pop()
            for parent in sorted(pred[node]):
                if sigma[node] > 0:
                    delta[parent] += (sigma[parent] / sigma[node]) * (1.0 + delta[node])
            if node != source:
                bc[node] += delta[node]

    n = len(ordered)
    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for node in ordered:
            bc[node] *= scale
    else:
        for node in ordered:
            bc[node] = 0.0
    return bc




def strongly_connected_components(
    nodes: list[str], edges: list[tuple[str, str]]
) -> list[tuple[str, ...]]:
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(set(nodes)))
    graph.add_edges_from(sorted(set(edges)))
    components = [tuple(sorted(component)) for component in nx.strongly_connected_components(graph)]
    return sorted(components)


def _repo_fingerprint(repo_root: Path, scan_paths: list[str]) -> str:
    code, out = _run_git(["rev-parse", "HEAD"], repo_root)
    if code == 0 and out:
        return out

    sha = hashlib.sha256()
    for rel in sorted(scan_paths):
        path = repo_root / rel
        if not path.exists() or not path.is_file():
            continue

        file_hash = None
        git_code, git_out = _run_git(["hash-object", rel], repo_root)
        if git_code == 0 and git_out:
            file_hash = git_out
        else:
            stat = path.stat()
            file_hash = f"{stat.st_mtime_ns}:{stat.st_size}"

        sha.update(rel.encode("utf-8"))
        sha.update(b"\n")
        sha.update(file_hash.encode("utf-8"))
        sha.update(b"\n")
    return sha.hexdigest()


def generate_repo_model(repo_root: Path) -> dict[str, Any]:
    agents = discover_agents(repo_root)
    edges, unknowns = extract_wiring_edges(repo_root, agents)

    all_agents = sorted(agents, key=lambda agent: agent["agent_id"])
    node_ids = sorted(agent["agent_id"] for agent in all_agents)
    directed = [(edge["from_id"], edge["to_id"]) for edge in edges]

    pr = pagerank(node_ids, directed)
    bc = betweenness_centrality_brandes(node_ids, directed)
    max_pr = max(pr.values()) if pr else 0.0
    max_bc = max(bc.values()) if bc else 0.0

    degree: dict[str, int] = {node: 0 for node in node_ids}
    for src, dst in directed:
        degree[src] += 1
        degree[dst] += 1
    nonzero_nodes = sum(1 for value in degree.values() if value > 0)
    k = max(5, min(25, round(0.08 * nonzero_nodes))) if nonzero_nodes else 5

    by_id = {agent["agent_id"]: agent for agent in all_agents}
    ranked: list[dict[str, Any]] = []
    for node in node_ids:
        pr_norm = (pr.get(node, 0.0) / max_pr) if max_pr > 0 else 0.0
        bc_norm = (bc.get(node, 0.0) / max_bc) if max_bc > 0 else 0.0
        core_score = 0.6 * pr_norm + 0.4 * bc_norm
        ranked.append(
            {
                "agent_id": node,
                "path": by_id[node]["path"],
                "kind": by_id[node]["kind"],
                "pr": pr.get(node, 0.0),
                "bc": bc.get(node, 0.0),
                "pr_norm": pr_norm,
                "bc_norm": bc_norm,
                "core_score": core_score,
            }
        )

    ranked.sort(
        key=lambda row: (
            -row["core_score"],
            -row["pr_norm"],
            -row["bc_norm"],
            row["agent_id"],
        )
    )
    core_candidates = [
        {
            "agent_id": row["agent_id"],
            "path": row["path"],
            "kind": row["kind"],
            "pr": row["pr"],
            "bc": row["bc"],
            "core_score": row["core_score"],
            "rank": idx,
        }
        for idx, row in enumerate(ranked[:k], start=1)
    ]

    sccs = strongly_connected_components(node_ids, directed)
    cycle_events = [
        {"type": "ARCHITECTURAL_CYCLE_DETECTED", "agent_ids": list(component)}
        for component in sccs
        if len(component) > 1
    ]
    unknown_events = sorted(
        cycle_events, key=lambda event: tuple(event.get("agent_ids", []))
    )

    unknowns_payload = dict(unknowns)
    unknowns_payload["events"] = unknown_events

    return {
        "repo_root": repo_root.as_posix(),
        "repo_fingerprint": _repo_fingerprint(
            repo_root, [agent["path"] for agent in all_agents]
        ),
        "agents": all_agents,
        "agents_count": len(all_agents),
        "wiring": {
            "edges": edges,
            "edges_count": len(edges),
        },
        "centrality": {
            "pagerank": {node: pr[node] for node in sorted(pr)},
            "betweenness": {node: bc[node] for node in sorted(bc)},
        },
        "core_candidates": core_candidates,
        "core_candidates_count": len(core_candidates),
        "metadata": {
            "core_candidates": core_candidates,
        },
        "unknowns": unknowns_payload,
    }


def write_repo_model(out_path: Path, model: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo-model")
    parser.add_argument("--out", default="engine/artifacts/repo_model/repo_model.json")
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args(argv)

    repo_root = discover_repo_root(Path.cwd())
    out_arg = Path(args.out)
    out_path = out_arg if out_arg.is_absolute() else (repo_root / out_arg)
    model = generate_repo_model(repo_root)
    write_repo_model(out_path, model)

    if args.stdout:
        print(json.dumps(model, indent=2, sort_keys=True))
    else:
        print(f"WROTE:{out_path.relative_to(repo_root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
