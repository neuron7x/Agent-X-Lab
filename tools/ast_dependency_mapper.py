#!/usr/bin/env python3
"""Deep architecture extraction via strict AST + repository evidence.

Usage:
  python3 tools/ast_dependency_mapper.py /workspace/Agent-X-Lab > architecture_contract.jsonl

All operational logs are emitted to STDERR.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EXCLUDED_TOP_LEVEL = {".git", "node_modules", "build_proof", "evidence", "archive", "dist"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def git_tracked_files(repo_root: Path) -> list[str]:
    code, out, _ = run_cmd(["git", "ls-files", "-z"], repo_root)
    if code != 0:
        return []
    return [p for p in out.split("\x00") if p]


def compute_repo_fingerprint(repo_root: Path) -> str:
    sha = hashlib.sha256()
    for rel in sorted(git_tracked_files(repo_root)):
        path = repo_root / rel
        if not path.is_file():
            continue
        sha.update(rel.encode("utf-8"))
        sha.update(b"\x00")
        sha.update(path.read_bytes())
        sha.update(b"\x00")
    return sha.hexdigest()


def discover_python_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for p in repo_root.rglob("*.py"):
        rel_parts = p.relative_to(repo_root).parts
        if rel_parts and rel_parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        files.append(p)
    return sorted(files)


def is_identifier(part: str) -> bool:
    return part.isidentifier()


def build_module_index(repo_root: Path, py_files: list[Path]) -> tuple[dict[str, set[str]], dict[str, str]]:
    index: dict[str, set[str]] = defaultdict(set)
    primary_module_for_file: dict[str, str] = {}

    for path in py_files:
        rel = path.relative_to(repo_root).as_posix()
        parts = list(path.relative_to(repo_root).with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            module_parts = parts[:-1]
            if module_parts:
                primary_module_for_file[rel] = ".".join([p for p in module_parts if is_identifier(p)])
        else:
            valid = [p for p in parts if is_identifier(p)]
            if valid:
                primary_module_for_file[rel] = ".".join(valid)

        for i in range(len(parts)):
            suffix = parts[i:]
            if not suffix:
                continue
            if suffix[-1] == "__init__":
                suffix = suffix[:-1]
            if not suffix or not all(is_identifier(p) for p in suffix):
                continue
            mod = ".".join(suffix)
            index[mod].add(rel)

    return index, primary_module_for_file


def parse_file(path: Path) -> tuple[ast.AST | None, str | None]:
    try:
        src = path.read_text(encoding="utf-8")
        return ast.parse(src), None
    except SyntaxError as e:
        return None, str(e)


def module_package(rel: str) -> str:
    p = Path(rel)
    dirs = list(p.parent.parts)
    suffix: list[str] = []
    for part in reversed(dirs):
        if is_identifier(part):
            suffix.append(part)
        elif suffix:
            break
    suffix = list(reversed(suffix))
    if p.name == "__init__.py":
        return ".".join(suffix)
    return ".".join(suffix)


def resolve_module_candidate(module_name: str, module_index: dict[str, set[str]]) -> str | None:
    candidates = module_index.get(module_name, set())
    if len(candidates) == 1:
        return next(iter(candidates))
    return None


def extract_import_edges(
    tree: ast.AST,
    rel: str,
    module_index: dict[str, set[str]],
    primary_module_for_file: dict[str, str],
) -> tuple[list[str], list[str]]:
    imports: set[str] = set()
    edges: set[str] = set()
    package = module_package(rel)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                m = alias.name
                imports.add(m)
                target = resolve_module_candidate(m, module_index)
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
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "add_argument":
                args = [literal(a) for a in node.args if isinstance(literal(a), str)]
                required = None
                default = None
                for kw in node.keywords:
                    if kw.arg == "required":
                        required = bool(literal(kw.value))
                    if kw.arg == "default":
                        default = literal(kw.value)
                if args:
                    inputs.append(
                        {
                            "source": "argparse",
                            "flags": args,
                            "required": required,
                            "default": default,
                        }
                    )
        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name):
                if node.value.value.id == "sys" and node.value.attr == "argv":
                    inputs.append({"source": "sys.argv"})

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if isinstance(dec.func.value, ast.Name) and dec.func.value.id == "click":
                        if dec.func.attr in {"option", "argument"}:
                            args = [literal(a) for a in dec.args if isinstance(literal(a), str)]
                            default = None
                            required = None
                            for kw in dec.keywords:
                                if kw.arg == "default":
                                    default = literal(kw.value)
                                if kw.arg == "required":
                                    required = bool(literal(kw.value))
                            inputs.append(
                                {
                                    "source": f"click.{dec.func.attr}",
                                    "flags": args,
                                    "required": required,
                                    "default": default,
                                }
                            )
    dedup = []
    seen = set()
    for item in inputs:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return dedup


def reconstruct_name(rel: str, tree: ast.AST) -> str:
    doc = ast.get_docstring(tree) or ""
    if doc.strip():
        return doc.strip().splitlines()[0][:120]
    return Path(rel).stem.replace("_", " ").strip().title()


def classify_role(rel: str, imports: list[str], interface_inputs: list[dict[str, Any]]) -> str:
    name = Path(rel).name.lower()
    import_blob = " ".join(imports).lower()
    if interface_inputs or "argparse" in import_blob or "click" in import_blob:
        return "ORCHESTRATOR"
    if "test" in rel.lower() or name.startswith("test_") or "unittest" in import_blob or "pytest" in import_blob:
        return "VALIDATOR"
    if any(k in name for k in ["evidence", "ledger", "report", "artifact"]):
        return "EVIDENCE_COLLECTOR"
    if any(k in name for k in ["model", "types", "schema", "store", "dao"]):
        return "DATA_SINK"
    return "TRANSFORMER"


def blame_stats(repo_root: Path, rel: str) -> dict[str, Any]:
    code, out, _ = run_cmd(["git", "blame", "--line-porcelain", "--", rel], repo_root)
    if code != 0:
        return {"bus_factor": 0, "primary_maintainer": None, "line_ownership": {}}
    counts: Counter[str] = Counter()
    for line in out.splitlines():
        if line.startswith("author "):
            counts[line[len("author ") :].strip()] += 1
    primary = counts.most_common(1)[0][0] if counts else None
    return {
        "bus_factor": len(counts),
        "primary_maintainer": primary,
        "line_ownership": dict(sorted(counts.items())),
    }


def find_invocations(repo_root: Path, rel: str) -> list[str]:
    fname = Path(rel).name
    code, out, _ = run_cmd(["rg", "-n", "--fixed-strings", fname, str(repo_root)], repo_root)
    if code not in (0, 1):
        return []
    hits: list[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        normalized = line.replace(str(repo_root) + "/", "")
        first = normalized.split(":", 1)[0].split("/", 1)[0]
        if first in EXCLUDED_TOP_LEVEL:
            continue
        hits.append(normalized)
    return hits[:50]


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
        new_ranks = {}
        sink_sum = sum(ranks[node] for node in nodes if not out_map[node])
        for node in nodes:
            score = (1.0 - d) / n
            score += d * sink_sum / n
            for src in in_map[node]:
                score += d * (ranks[src] / len(out_map[src]))
            new_ranks[node] = score
        ranks = new_ranks
    return ranks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", nargs="?", default=".")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    log(f"[phase] repo_root={repo_root}")

    fp_before = compute_repo_fingerprint(repo_root)
    py_files = discover_python_files(repo_root)
    log(f"[phase1] python_files={len(py_files)}")

    module_index, primary_mod = build_module_index(repo_root, py_files)

    agents: list[dict[str, Any]] = []
    edges: set[tuple[str, str]] = set()
    unknowns: list[dict[str, Any]] = []

    for path in py_files:
        rel = path.relative_to(repo_root).as_posix()
        tree, err = parse_file(path)
        if err:
            log(json.dumps({"state": "BLOCKED", "file": rel, "error": err}, ensure_ascii=False))
            continue

        imports, depends_on_paths = extract_import_edges(tree, rel, module_index, primary_mod)
        interface_inputs = extract_interface_inputs(tree)
        role = classify_role(rel, imports, interface_inputs)
        name = reconstruct_name(rel, tree)
        invocations = find_invocations(repo_root, rel)
        evolution = blame_stats(repo_root, rel)

        for dep in depends_on_paths:
            edges.add((rel, dep))

        agents.append(
            {
                "agent_id": rel,
                "agent_path": rel,
                "name": name,
                "role": role,
                "imports": imports,
                "depends_on_paths": depends_on_paths,
                "interface": {
                    "inputs": interface_inputs,
                    "invocation": invocations,
                },
                "evolution": evolution,
            }
        )

    agent_ids = {a["agent_id"] for a in agents}
    verified_edges: list[tuple[str, str]] = []
    for src, dst in sorted(edges):
        if src in agent_ids and dst in agent_ids:
            verified_edges.append((src, dst))
        else:
            unknowns.append(
                {
                    "type": "CRITICAL_LINK_ERROR",
                    "from": src,
                    "to": dst,
                }
            )

    pr = pagerank(sorted(agent_ids), verified_edges)
    core_candidates = [
        {"agent_id": k, "score": round(v, 12)}
        for k, v in sorted(pr.items(), key=lambda x: (-x[1], x[0]))
    ]

    fp_after = compute_repo_fingerprint(repo_root)
    fingerprint_match = fp_before == fp_after
    if not fingerprint_match:
        log("[phase3] fingerprint mismatch -> RE-SCAN")
        return 3

    out_rows: list[dict[str, Any]] = []
    out_rows.append(
        {
            "type": "METADATA",
            "centrality_algorithm": "PageRank",
            "fingerprint_match": fingerprint_match,
            "repo_fingerprint": fp_after,
            "core_candidates": core_candidates,
            "unknowns": unknowns,
        }
    )

    edge_map: dict[str, list[str]] = defaultdict(list)
    for src, dst in verified_edges:
        edge_map[src].append(dst)

    for agent in sorted(agents, key=lambda x: x["agent_id"]):
        out_rows.append(
            {
                "type": "AGENT_CONTRACT",
                "agent_id": agent["agent_id"],
                "name": agent["name"],
                "role": agent["role"],
                "interface": agent["interface"],
                "depends_on_paths": agent["depends_on_paths"],
                "verified_edges": edge_map.get(agent["agent_id"], []),
                "evolution": agent["evolution"],
            }
        )

    out_rows.append(
        {
            "type": "EVIDENCE_LEDGER",
            "cmdlog_refs": [
                "git ls-files -z",
                "git blame --line-porcelain <path>",
                "rg -n --fixed-strings <filename> <repo_root>",
            ],
        }
    )

    for row in out_rows:
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
