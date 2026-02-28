from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

sys.setrecursionlimit(max(5000, sys.getrecursionlimit()))

EXCLUDED_TOP_LEVEL = {".git", "node_modules", "build_proof", "evidence", "archive", "dist", ".venv"}
TEXT_SCAN_GLOBS = ["*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.toml", "*.ini", "*.cfg", "*.sh", "Makefile"]
RUN_SCRIPT_RE = re.compile(r"(?:^|\s)(?:python(?:3)?|node|bash|sh)\s+([./\w\-]+\.(?:py|js|sh))")


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    edge_type: str


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        log(f"[WARN] Binary not found: {cmd[0]} - {e}")
        return 127, "", str(e)
    return proc.returncode, proc.stdout, proc.stderr


def discover_python_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for p in repo_root.rglob("*.py"):
        rel_parts = p.relative_to(repo_root).parts
        if rel_parts and rel_parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        files.append(p)
    return sorted(files)


def build_module_index(repo_root: Path, py_files: list[Path]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for path in py_files:
        rel = path.relative_to(repo_root).as_posix()
        parts = list(path.relative_to(repo_root).with_suffix("").parts)
        for i in range(len(parts)):
            suffix = parts[i:]
            if suffix and suffix[-1] == "__init__":
                suffix = suffix[:-1]
            if suffix and all(part.isidentifier() for part in suffix):
                index[".".join(suffix)].add(rel)
    return index


def module_package(rel: str) -> str:
    p = Path(rel)
    suffix: list[str] = []
    for part in reversed(p.parent.parts):
        if part.isidentifier():
            suffix.append(part)
        elif suffix:
            break
    return ".".join(reversed(suffix))


def resolve_module_candidate(module_name: str, module_index: dict[str, set[str]]) -> str | None:
    candidates = module_index.get(module_name, set())
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def parse_file(path: Path) -> tuple[ast.AST | None, str | None]:
    try:
        src = path.read_text(encoding="utf-8")
        return ast.parse(src), None
    except (SyntaxError, RecursionError) as e:
        return None, str(e)


def extract_import_edges(tree: ast.AST, rel: str, module_index: dict[str, set[str]]) -> tuple[list[str], list[str]]:
    imports: set[str] = set()
    edges: set[str] = set()
    package = module_package(rel)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
                target = resolve_module_candidate(alias.name, module_index)
                if target and target != rel:
                    edges.add(target)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level > 0:
                pkg_parts = package.split(".") if package else []
                cut = max(0, len(pkg_parts) - (node.level - 1))
                prefix = ".".join(pkg_parts[:cut])
                abs_base = f"{prefix}.{base}".strip(".") if base else prefix
            else:
                abs_base = base
            if abs_base:
                imports.add(abs_base)
                target = resolve_module_candidate(abs_base, module_index)
                if target and target != rel:
                    edges.add(target)
            for alias in node.names:
                if alias.name == "*":
                    continue
                composed = f"{abs_base}.{alias.name}".strip(".") if abs_base else alias.name
                imports.add(composed)
                target = resolve_module_candidate(composed, module_index)
                if target and target != rel:
                    edges.add(target)

    return sorted(imports), sorted(edges)


def literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    return None


def extract_interface_inputs(tree: ast.AST) -> list[dict[str, Any]]:
    inputs: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            args = [literal(a) for a in node.args if isinstance(literal(a), str)]
            required: bool | None = None
            default: Any = None
            for kw in node.keywords:
                if kw.arg == "required":
                    required = bool(literal(kw.value))
                if kw.arg == "default":
                    default = literal(kw.value)
            if args:
                inputs.append({"source": "argparse", "flags": args, "required": required, "default": default})
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
            if node.value.value.id == "sys" and node.value.attr == "argv":
                inputs.append({"source": "sys.argv"})

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                func_id: str | None = None
                if isinstance(dec.func, ast.Name):
                    func_id = dec.func.id
                elif isinstance(dec.func, ast.Attribute) and isinstance(dec.func.value, ast.Name) and dec.func.value.id == "click":
                    func_id = dec.func.attr
                if func_id not in {"option", "argument"}:
                    continue
                args = [literal(a) for a in dec.args if isinstance(literal(a), str)]
                default: Any = None
                required: bool | None = None
                for kw in dec.keywords:
                    if kw.arg == "default":
                        default = literal(kw.value)
                    if kw.arg == "required":
                        required = bool(literal(kw.value))
                inputs.append({"source": f"click.{func_id}", "flags": args, "required": required, "default": default})

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in inputs:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def classify_role(rel: str, imports: list[str], interface_inputs: list[dict[str, Any]]) -> str:
    name = Path(rel).name.lower()
    import_blob = " ".join(imports).lower()
    if rel.endswith((".yml", ".yaml")):
        return "ORCHESTRATOR"
    if interface_inputs or "argparse" in import_blob or "click" in import_blob or "typer" in import_blob:
        return "ORCHESTRATOR"
    if "test" in rel.lower() or name.startswith("test_") or "pytest" in import_blob:
        return "VALIDATOR"
    if any(k in name for k in ["evidence", "ledger", "report", "artifact"]):
        return "EVIDENCE_COLLECTOR"
    if any(k in name for k in ["model", "types", "schema", "store", "dao"]):
        return "DATA_SINK"
    return "TRANSFORMER"


def batch_git_ownership(repo_root: Path) -> dict[str, dict[str, Any]]:
    code, out, _ = run_cmd(["git", "log", "--pretty=format:%H|%an|%ad", "--name-only", "--date=short"], repo_root)
    if code != 0:
        return {}
    ownership: dict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    current_author: str | None = None
    for line in out.splitlines():
        if not line.strip():
            continue
        if "|" in line and len(line.split("|")) >= 3:
            _, author, _ = line.split("|", 2)
            current_author = author.strip()
            continue
        if current_author and line.endswith(".py"):
            ownership[line.strip()][current_author] += 1

    result: dict[str, dict[str, Any]] = {}
    for rel, counter in ownership.items():
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        result[rel] = {
            "bus_factor": len(counter),
            "primary_maintainer": items[0][0] if items else None,
            "line_ownership": {k: v for k, v in sorted(counter.items())},
        }
    return result


def build_invocation_index_rg(repo_root: Path, entrypoints: list[str]) -> dict[str, list[str]]:
    if not entrypoints:
        return {}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as patt:
        patt_path = Path(patt.name)
        for ep in sorted(set(entrypoints)):
            patt.write(re.escape(ep) + "\n")
    cmd = ["rg", "--json", "-n", "-f", str(patt_path), str(repo_root)]
    code, out, _ = run_cmd(cmd, repo_root)
    patt_path.unlink(missing_ok=True)
    if code not in (0, 1):
        return {}
    index: dict[str, list[str]] = defaultdict(list)
    tracked = set(entrypoints)
    for row in out.splitlines():
        if not row.strip():
            continue
        try:
            payload = json.loads(row)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "match":
            continue
        data = payload.get("data", {})
        path_text = data.get("path", {}).get("text", "")
        rel = path_text.replace(str(repo_root) + "/", "")
        top = rel.split("/", 1)[0] if rel else ""
        if top in EXCLUDED_TOP_LEVEL:
            continue
        lineno = data.get("line_number", 0)
        line = data.get("lines", {}).get("text", "").strip()
        for ep in tracked:
            if ep in line:
                index[ep].append(f"{rel}:{lineno}:{line}")
    for ep in list(index.keys()):
        index[ep] = index[ep][:50]
    return index


def extract_run_script_targets(run_value: str) -> list[str]:
    targets: list[str] = []
    for line in run_value.splitlines():
        m = RUN_SCRIPT_RE.search(line)
        if m:
            targets.append(m.group(1))
    return targets


def iter_step_dicts(node: Any) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if isinstance(node.get("steps"), list):
            for s in node["steps"]:
                if isinstance(s, dict):
                    steps.append(s)
        for v in node.values():
            steps.extend(iter_step_dicts(v))
    elif isinstance(node, list):
        for item in node:
            steps.extend(iter_step_dicts(item))
    return steps


def parse_yaml_file(path: Path) -> Any:
    if yaml is None:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def polyglot_edges(repo_root: Path) -> tuple[set[str], set[Edge]]:
    agents: set[str] = set()
    edges: set[Edge] = set()
    patterns = [repo_root / ".github/workflows", repo_root / ".github/actions"]
    yml_files: list[Path] = []
    for base in patterns:
        if not base.exists():
            continue
        yml_files.extend(list(base.rglob("*.yml")))
        yml_files.extend(list(base.rglob("*.yaml")))

    for yml in sorted(set(yml_files)):
        rel = yml.relative_to(repo_root).as_posix()
        agents.add(rel)
        parsed = parse_yaml_file(yml)
        if not parsed:
            continue
        for step in iter_step_dicts(parsed):
            uses = step.get("uses")
            if isinstance(uses, str):
                if uses.startswith("./"):
                    target = (repo_root / uses).resolve()
                    action_yml = target / "action.yml"
                    if action_yml.exists():
                        tgt_rel = action_yml.relative_to(repo_root).as_posix()
                        agents.add(tgt_rel)
                        edge_type = "USES_LOCAL_ACTION" if "/workflows/" in rel else "USES_ACTION_IN_ACTION"
                        edges.add(Edge(rel, tgt_rel, edge_type))
                elif uses.startswith(".github/actions/"):
                    action_yml = (repo_root / uses / "action.yml").resolve()
                    if action_yml.exists():
                        tgt_rel = action_yml.relative_to(repo_root).as_posix()
                        agents.add(tgt_rel)
                        edges.add(Edge(rel, tgt_rel, "USES_LOCAL_ACTION"))
            run = step.get("run")
            if isinstance(run, str):
                for target in extract_run_script_targets(run):
                    t = (yml.parent / target).resolve() if target.startswith("./") else (repo_root / target).resolve()
                    if t.exists():
                        tgt_rel = t.relative_to(repo_root).as_posix()
                        agents.add(tgt_rel)
                        edges.add(Edge(rel, tgt_rel, "RUNS_SCRIPT"))

    return agents, edges


def pagerank(nodes: list[str], edges: list[tuple[str, str]], d: float = 0.85, iterations: int = 50) -> dict[str, float]:
    if not nodes:
        return {}
    n = len(nodes)
    ranks = {node: 1.0 / n for node in nodes}
    out_map: dict[str, set[str]] = defaultdict(set)
    in_map: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        out_map[a].add(b)
        in_map[b].add(a)
    for _ in range(iterations):
        new_ranks: dict[str, float] = {}
        sink_sum = sum(ranks[node] for node in nodes if not out_map[node])
        for node in nodes:
            score = (1.0 - d) / n + d * sink_sum / n
            for src in in_map[node]:
                score += d * (ranks[src] / len(out_map[src]))
            new_ranks[node] = score
        ranks = new_ranks
    return ranks


def betweenness_centrality_brandes(nodes: list[str], edges: list[tuple[str, str]]) -> dict[str, float]:
    g: dict[str, list[str]] = {n: [] for n in nodes}
    for u, v in edges:
        g.setdefault(u, []).append(v)
        g.setdefault(v, [])

    bc: dict[str, float] = {v: 0.0 for v in g}
    for s in g:
        stack: list[str] = []
        pred: dict[str, list[str]] = {w: [] for w in g}
        sigma: dict[str, float] = {w: 0.0 for w in g}
        dist: dict[str, int] = {w: -1 for w in g}
        sigma[s] = 1.0
        dist[s] = 0
        q: deque[str] = deque([s])
        while q:
            v = q.popleft()
            stack.append(v)
            for w in g[v]:
                if dist[w] < 0:
                    q.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta: dict[str, float] = {w: 0.0 for w in g}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                bc[w] += delta[w]
    return bc


def tarjan_scc(nodes: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    graph: dict[str, list[str]] = {n: [] for n in nodes}
    for u, v in edges:
        graph.setdefault(u, []).append(v)
        graph.setdefault(v, [])

    index = 0
    stack: list[str] = []
    onstack: set[str] = set()
    idx: dict[str, int] = {}
    low: dict[str, int] = {}
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        idx[v] = index
        low[v] = index
        index += 1
        stack.append(v)
        onstack.add(v)

        for w in graph[v]:
            if w not in idx:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in onstack:
                low[v] = min(low[v], idx[w])

        if low[v] == idx[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                onstack.remove(w)
                comp.append(w)
                if w == v:
                    break
            sccs.append(sorted(comp))

    for n in sorted(graph):
        if n not in idx:
            strongconnect(n)
    return sccs


def compute_repo_fingerprint(repo_root: Path) -> str:
    code, out, _ = run_cmd(["git", "ls-files", "-z"], repo_root)
    sha = hashlib.sha256()
    if code != 0:
        return sha.hexdigest()
    for rel in sorted([p for p in out.split("\x00") if p]):
        path = repo_root / rel
        if path.is_file():
            sha.update(rel.encode("utf-8"))
            sha.update(b"\x00")
            sha.update(path.read_bytes())
            sha.update(b"\x00")
    return sha.hexdigest()


def generate_repo_model(repo_root: Path) -> dict[str, Any]:
    fp_before = compute_repo_fingerprint(repo_root)
    py_files = discover_python_files(repo_root)
    module_index = build_module_index(repo_root, py_files)
    owners = batch_git_ownership(repo_root)
    invocations = build_invocation_index_rg(repo_root, [p.name for p in py_files])

    agents: list[dict[str, Any]] = []
    agent_ids: set[str] = set()
    edges: set[Edge] = set()
    unknowns: list[dict[str, Any]] = []

    for path in py_files:
        rel = path.relative_to(repo_root).as_posix()
        tree, err = parse_file(path)
        if err or tree is None:
            unknowns.append({"type": "BLOCKED_AST_PARSE", "agent_id": rel, "error": err})
            continue
        imports, deps = extract_import_edges(tree, rel, module_index)
        iface = extract_interface_inputs(tree)
        name = (ast.get_docstring(tree) or "").strip().splitlines()[0] if ast.get_docstring(tree) else path.stem.replace("_", " ").title()
        agent = {
            "agent_id": rel,
            "name": name,
            "role": classify_role(rel, imports, iface),
            "interface": {"inputs": iface, "invocation": invocations.get(path.name, [])},
            "depends_on_paths": deps,
            "imports": imports,
            "evolution": owners.get(rel, {"bus_factor": 0, "primary_maintainer": None, "line_ownership": {}}),
        }
        agents.append(agent)
        agent_ids.add(rel)
        for dep in deps:
            edges.add(Edge(rel, dep, "IMPORTS"))

    extra_agents, poly_edges = polyglot_edges(repo_root)
    for aid in sorted(extra_agents):
        if aid in agent_ids:
            continue
        agents.append({"agent_id": aid, "name": Path(aid).name, "role": "ORCHESTRATOR", "interface": {"inputs": [], "invocation": []}, "depends_on_paths": [], "imports": [], "evolution": {"bus_factor": 0, "primary_maintainer": None, "line_ownership": {}}})
        agent_ids.add(aid)
    edges.update(poly_edges)

    verified_edges: list[dict[str, str]] = []
    for e in sorted(edges, key=lambda x: (x.source, x.target, x.edge_type)):
        if e.source in agent_ids and e.target in agent_ids:
            verified_edges.append({"from": e.source, "to": e.target, "type": e.edge_type})
        else:
            unknowns.append({"type": "CRITICAL_LINK_ERROR", "from": e.source, "to": e.target, "edge_type": e.edge_type})

    simple_edges = [(e["from"], e["to"]) for e in verified_edges]
    nodes = sorted(agent_ids)
    pr = pagerank(nodes, simple_edges)
    bc = betweenness_centrality_brandes(nodes, simple_edges)
    max_pr = max(pr.values()) if pr else 1.0
    max_bc = max(bc.values()) if bc else 1.0
    max_pr = max_pr if max_pr > 0 else 1.0
    max_bc = max_bc if max_bc > 0 else 1.0

    core_candidates: list[dict[str, Any]] = []
    for n in nodes:
        pr_norm = pr.get(n, 0.0) / max_pr
        bc_norm = bc.get(n, 0.0) / max_bc
        core_score = 0.6 * pr_norm + 0.4 * bc_norm
        core_candidates.append({"agent_id": n, "core_score": round(core_score, 12), "pr_norm": round(pr_norm, 12), "bc_norm": round(bc_norm, 12)})
    core_candidates.sort(key=lambda x: (-x["core_score"], -x["pr_norm"], -x["bc_norm"], x["agent_id"]))

    for comp in tarjan_scc(nodes, simple_edges):
        if len(comp) > 1:
            unknowns.append({"type": "ARCHITECTURAL_CYCLE_DETECTED", "nodes": comp})
            log(f"[WARN] Cycle detected: {' -> '.join(comp)}")

    fp_after = compute_repo_fingerprint(repo_root)
    if fp_before != fp_after:
        raise RuntimeError("RE-SCAN: fingerprint mismatch")

    return {
        "type": "REPO_MODEL",
        "metadata": {
            "centrality_algorithm": "PageRank+Brandes",
            "fingerprint_match": fp_before == fp_after,
            "repo_fingerprint": fp_after,
            "core_candidates": core_candidates,
        },
        "agents": sorted(agents, key=lambda a: a["agent_id"]),
        "wiring": {"edges": verified_edges, "core_candidates": core_candidates[:20]},
        "unknowns": unknowns,
    }


def cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo-model")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", default="engine/artifacts/repo_model/repo_model.json")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (repo_root / out_path).resolve()

    model = generate_repo_model(repo_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_ref = out_path.as_posix()
    try:
        output_ref = out_path.relative_to(repo_root).as_posix()
    except ValueError:
        output_ref = out_path.as_posix()
    print(json.dumps({"status": "OK", "output": output_ref}, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(cli())


if __name__ == "__main__":
    main()
