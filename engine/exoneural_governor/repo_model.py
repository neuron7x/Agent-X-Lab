from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shlex
import subprocess
from collections import Counter, deque
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .blame import blame_for_path, git_available, in_git_repo

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
    "artifacts",
    "build_proof",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
    "coverage",
    "htmlcov",
}

SCRIPT_SUFFIXES = {".py", ".mjs", ".js", ".ts", ".sh", ".bash"}
YAML_SUFFIXES = {".yml", ".yaml"}
EXECUTABLES = {"python", "python3", "node", "bash", "sh"}
MAX_AGENT_INPUTS = 200
MAX_INVOCATION_EXAMPLES = 20
MAX_GIT_LOG_LINES = 2000
MAX_SCAN_TEXT_SIZE = 1024 * 1024
MAX_DOC_SIZE = 256 * 1024
TOKEN_MAP = {
    "a11y": "Accessibility",
    "e2e": "E2E",
    "ci": "CI",
    "vr": "VR",
    "prod": "Prod",
    "spec": "Spec",
    "dao": "DAO",
    "jws": "JWS",
    "ed25519": "Ed25519",
}


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
    proc = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout.strip()


def discover_repo_root(cwd: Path | None = None) -> Path:
    start = (cwd or Path.cwd()).resolve()
    code, out = _run_git(["rev-parse", "--show-toplevel"], start)
    if code == 0 and out:
        return Path(out).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "engine").exists() and (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not discover repository root")


def _rel(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _is_ignored(rel_parts: tuple[str, ...]) -> bool:
    return any(part in IGNORED_DIRS for part in rel_parts)


def _iter_files(base: Path, size_cap: int | None = None) -> list[Path]:
    out: list[Path] = []
    if not base.exists():
        return out
    for p in base.rglob("*"):
        if p.is_dir():
            continue
        if _is_ignored(p.relative_to(base).parts):
            continue
        if size_cap is not None:
            try:
                if p.stat().st_size > size_cap:
                    continue
            except OSError:
                continue
        out.append(p)
    return sorted(set(out))


def _kind_for_path(repo_root: Path, path: Path) -> str:
    rel = _rel(repo_root, path)
    if rel.startswith(".github/workflows/") and path.suffix in YAML_SUFFIXES:
        return Kind.GITHUB_WORKFLOW
    if rel.startswith(".github/actions/") and path.name in {"action.yml", "action.yaml"}:
        return Kind.GITHUB_COMPOSITE_ACTION
    if rel == "Makefile":
        return Kind.MAKEFILE
    if rel.startswith("engine/tools/") and path.suffix == ".py" and path.name != "__init__.py":
        return Kind.CLI_SCRIPT
    if path.suffix in SCRIPT_SUFFIXES and (
        rel.startswith("scripts/")
        or rel.startswith("tools/")
        or rel.startswith("engine/scripts/")
        or rel.startswith("engine/tools/")
        or rel.startswith("engine/exoneural_governor/")
    ):
        return Kind.CLI_SCRIPT
    if path.suffix.lower() == ".md" and (
        rel.startswith("docs/prompts/") or rel.startswith("docs/") or "runbook" in path.name.lower()
    ):
        return Kind.RUNBOOK_DOC
    return Kind.OTHER


def _derive_name(path: Path) -> str | None:
    base = re.sub(r"[_\-.]+", " ", path.stem)
    tokens = [tok for tok in base.split() if tok]
    if not tokens:
        return None
    out: list[str] = []
    for tok in tokens:
        mapped = TOKEN_MAP.get(tok.lower())
        out.append(mapped if mapped is not None else tok.title())
    derived = " ".join(out).strip()
    return derived or None


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _first_md_header(text: str) -> tuple[str, int] | None:
    for i, line in enumerate(text.splitlines(), start=1):
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return (m.group(1).strip()[:120], i)
    return None


def _python_docstring_header(text: str) -> tuple[str, int] | None:
    try:
        tree = ast.parse(text)
    except Exception:
        return None
    if not tree.body or not isinstance(tree.body[0], ast.Expr):
        return None
    val = tree.body[0].value
    if not isinstance(val, ast.Constant) or not isinstance(val.value, str):
        return None
    for line in val.value.splitlines():
        s = line.strip()
        if s:
            return (s[:120], tree.body[0].lineno)
    return None


def _comment_header(path: Path, text: str) -> tuple[str, int] | None:
    lines = text.splitlines()
    in_block = False
    for i, line in enumerate(lines, start=1):
        s = line.strip()
        if not s:
            continue
        if path.suffix in {".js", ".mjs", ".ts"}:
            if s.startswith("//"):
                return (s[2:].strip()[:120], i)
            if s.startswith("/*"):
                c = s[2:]
                c = c.split("*/", 1)[0].strip("* ")
                if c:
                    return (c[:120], i)
                in_block = True
                continue
            if in_block:
                c = s.split("*/", 1)[0].strip("* ")
                if c:
                    return (c[:120], i)
                if "*/" in s:
                    in_block = False
                continue
        if path.suffix in {".sh", ".bash"} and s.startswith("#"):
            return (s[1:].strip()[:120], i)
        break
    return None


def _safe_load_yaml(repo_root: Path, path: Path, parse_failures: list[str]) -> Any:
    try:
        return yaml.safe_load(_read_text(path))
    except Exception:
        parse_failures.append(_rel(repo_root, path))
        return None


def _yaml_on(data: dict[str, Any]) -> Any:
    on_value = data.get("on")
    if on_value is not None:
        return on_value
    # yaml 1.1 converts key 'on' to True with safe_load
    return data.get(True)


def _name_for_path(repo_root: Path, path: Path, parse_failures: list[str]) -> tuple[str | None, str, dict[str, Any] | None]:
    rel = _rel(repo_root, path)
    text = _read_text(path)
    if path.suffix in YAML_SUFFIXES:
        data = _safe_load_yaml(repo_root, path, parse_failures)
        if isinstance(data, dict):
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip(), "DECLARED", {"path": rel, "line": 1, "excerpt": name.strip()[:120]}
    if path.suffix.lower() == ".md":
        hdr = _first_md_header(text)
        if hdr:
            return hdr[0], "HEADER", {"path": rel, "line": hdr[1], "excerpt": hdr[0]}
    if path.suffix == ".py":
        hdr = _python_docstring_header(text)
        if hdr:
            return hdr[0], "HEADER", {"path": rel, "line": hdr[1], "excerpt": hdr[0]}
    if path.suffix in {".js", ".mjs", ".ts", ".sh", ".bash"}:
        hdr = _comment_header(path, text)
        if hdr:
            return hdr[0], "HEADER", {"path": rel, "line": hdr[1], "excerpt": hdr[0]}
    derived = _derive_name(path)
    if derived:
        return derived, "DERIVED", None
    return None, "MISSING", None


DEFAULT_INCLUDE_GLOBS = [
    ".github/workflows/*",
    ".github/actions/**",
    "Makefile",
    "scripts/**",
    "tools/**",
    "engine/scripts/**",
    "engine/tools/**/*.py",
    "engine/exoneural_governor/**/*.py",
    "docs/**/*.md",
]

DEFAULT_EXCLUDE_GLOBS = ["**/__init__.py"]




def _canon_rel(rel: str) -> str:
    r = rel.replace("\\", "/")
    while r.startswith("./"):
        r = r[2:]
    return r


def _match(rel: str, pat: str) -> bool:
    rel2 = _canon_rel(rel)
    pat2 = pat.replace("\\", "/")
    return PurePosixPath(rel2).match(pat2)


def _match_any(rel: str, patterns: list[str]) -> bool:
    return any(_match(rel, p) for p in patterns)

def discover_agents(repo_root: Path, include_globs: list[str] | None = None, exclude_globs: list[str] | None = None) -> list[dict[str, Any]]:
    paths: set[Path] = set()
    paths.update(_iter_files(repo_root / ".github" / "workflows"))
    paths.update(_iter_files(repo_root / ".github" / "actions"))

    mf = repo_root / "Makefile"
    if mf.exists():
        paths.add(mf)

    # manual loop to apply dir-specific constraints deterministically
    for p in _iter_files(repo_root / "scripts") + _iter_files(repo_root / "tools") + _iter_files(repo_root / "engine" / "scripts") + _iter_files(repo_root / "engine" / "exoneural_governor") + _iter_files(repo_root / "tools" / "dao-arbiter" / "dao_lifebook"):
        if p.suffix in SCRIPT_SUFFIXES:
            paths.add(p)

    for p in _iter_files(repo_root / "engine" / "tools"):
        if p.suffix == ".py" and p.name != "__init__.py":
            paths.add(p)

    for p in _iter_files(repo_root / "docs", size_cap=MAX_DOC_SIZE):
        if p.suffix.lower() == ".md":
            paths.add(p)

    include_globs = include_globs if include_globs is not None else []
    exclude_globs = exclude_globs if exclude_globs is not None else DEFAULT_EXCLUDE_GLOBS

    agents: list[dict[str, Any]] = []
    parse_failures: list[str] = []
    for p in sorted(paths):
        rel = _rel(repo_root, p)
        if include_globs and not _match_any(rel, include_globs):
            continue
        if exclude_globs and _match_any(rel, exclude_globs):
            continue
        name, source, evidence = _name_for_path(repo_root, p, parse_failures)
        row: dict[str, Any] = {
            "agent_id": _sha12(rel),
            "path": rel,
            "kind": _kind_for_path(repo_root, p),
            "name": name,
            "name_source": source,
            "interface": {"inputs": [], "outputs": [], "invocation": []},
            "depends_on_paths": [],
            "invocation_examples": [],
            "subkind": "OTHER",
            "evolution": {
                "commit_count": None,
                "authors": [],
                "top_author": None,
                "top_author_share": None,
                "last_commit": None,
                "last_date": None,
            },
        }
        if evidence is not None:
            row["name_evidence"] = evidence
        agents.append(row)
    return sorted(agents, key=lambda a: a["agent_id"])


def _iter_steps(data: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(data, dict):
        steps = data.get("steps")
        if isinstance(steps, list):
            out.extend([s for s in steps if isinstance(s, dict)])
        for v in data.values():
            out.extend(_iter_steps(v))
    elif isinstance(data, list):
        for v in data:
            out.extend(_iter_steps(v))
    return out


def _normalize_local_action_ref(repo_root: Path, src_file: Path, uses: str) -> Path | None:
    ref = uses.strip().split("@", 1)[0]
    candidates: list[Path] = []
    if ref.startswith("./"):
        candidates.extend([(repo_root / ref).resolve(), (src_file.parent / ref).resolve()])
    elif ref.startswith(".github/"):
        candidates.append((repo_root / ref).resolve())
    elif "/.github/actions/" in ref:
        suffix = ref.split("/.github/actions/", 1)[1]
        candidates.append((repo_root / ".github" / "actions" / suffix).resolve())
    else:
        candidates.append((repo_root / ref).resolve())
    for c in candidates:
        if c.is_dir():
            for n in ("action.yml", "action.yaml"):
                p = c / n
                if p.exists():
                    return p
        if c.is_file() and c.name in {"action.yml", "action.yaml"}:
            return c
    return None


def _normalize_local_workflow_ref(repo_root: Path, src_file: Path, uses: str) -> Path | None:
    ref = uses.strip().split("@", 1)[0]
    candidates = []
    if ref.startswith("./"):
        candidates.extend([(repo_root / ref).resolve(), (src_file.parent / ref).resolve()])
    else:
        candidates.append((repo_root / ref).resolve())
    for c in candidates:
        if c.is_file() and c.suffix in YAML_SUFFIXES and _rel(repo_root, c).startswith(".github/workflows/"):
            return c
    return None


def _normalize_script_ref(repo_root: Path, token: str, base_dir: Path | None, src: Path | None) -> Path | None:
    norm = token.strip().strip("\"'`")
    if not norm or norm.startswith("$"):
        return None
    cand = ((base_dir or repo_root) / norm).resolve() if norm.startswith("./") else (repo_root / norm).resolve()
    if (not cand.exists()) and src is not None and norm.startswith("./"):
        cand = (src.parent / norm).resolve()
    if cand.exists() and cand.is_file() and cand.suffix in SCRIPT_SUFFIXES:
        return cand
    return None


def _extract_run_paths(repo_root: Path, src_file: Path, run_value: str, base_dir: Path | None = None) -> list[Path]:
    found: set[Path] = set()
    for raw in run_value.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            toks = shlex.split(line)
        except ValueError:
            toks = line.split()
        if not toks:
            continue
        if toks[0] in EXECUTABLES and len(toks) > 1:
            p = _normalize_script_ref(repo_root, toks[1], base_dir, src_file)
            if p:
                found.add(p)
        for t in toks:
            if t.endswith(tuple(SCRIPT_SUFFIXES)) or t.startswith("scripts/") or t.startswith("./scripts/"):
                p = _normalize_script_ref(repo_root, t, base_dir, src_file)
                if p:
                    found.add(p)
    return sorted(found)


def _value_literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _extract_python_interface(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = _read_text(path)
    try:
        tree = ast.parse(text)
    except Exception:
        return [], []
    inputs: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            flags: list[str] = []
            for a in node.args:
                val = _value_literal(a)
                if isinstance(val, str) and val.startswith("-"):
                    flags.append(val)
            if not flags:
                continue
            long_flags = [f for f in flags if f.startswith("--")]
            name = (long_flags[0] if long_flags else flags[0]).lstrip("-")
            default = None
            required = None
            help_text = None
            type_name = None
            for kw in node.keywords:
                if kw.arg == "default":
                    v = _value_literal(kw.value)
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        default = str(v) if v is not None else None
                elif kw.arg == "required":
                    v = _value_literal(kw.value)
                    required = bool(v) if isinstance(v, bool) else None
                elif kw.arg == "help":
                    v = _value_literal(kw.value)
                    help_text = v if isinstance(v, str) else None
                elif kw.arg == "type":
                    if isinstance(kw.value, ast.Name) and kw.value.id in {"str", "int", "float", "Path"}:
                        type_name = kw.value.id
                    else:
                        v = _value_literal(kw.value)
                        type_name = v if isinstance(v, str) else None
            inputs.append({"name": name, "flags": sorted(set(flags)), "required": required, "default": default, "type": type_name, "help": help_text, "source": "python:argparse"})

        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and isinstance(dec.func.value, ast.Name):
                    base = dec.func.value.id
                    if base == "click" and dec.func.attr in {"option", "argument"}:
                        vals = [_value_literal(a) for a in dec.args]
                        flags = sorted([v for v in vals if isinstance(v, str) and v.startswith("-")])
                        longf = [f for f in flags if f.startswith("--")]
                        name = (longf[0] if longf else (flags[0] if flags else (vals[0] if vals and isinstance(vals[0], str) else "arg"))).lstrip("-")
                        inputs.append({"name": name, "flags": flags, "required": None, "default": None, "type": None, "help": None, "source": "python:click"})
            for default in node.args.defaults:
                if isinstance(default, ast.Call) and isinstance(default.func, ast.Attribute) and isinstance(default.func.value, ast.Name) and default.func.value.id == "typer" and default.func.attr == "Option":
                    flags = [v for v in (_value_literal(a) for a in default.args) if isinstance(v, str) and v.startswith("-")]
                    if flags:
                        longf = [f for f in flags if f.startswith("--")]
                        name = (longf[0] if longf else flags[0]).lstrip("-")
                        inputs.append({"name": name, "flags": sorted(set(flags)), "required": None, "default": None, "type": None, "help": None, "source": "python:typer"})

    inputs = sorted(inputs, key=lambda x: (x["name"], x["flags"][0] if x["flags"] else ""))[:MAX_AGENT_INPUTS]
    outputs: list[dict[str, Any]] = []
    for row in inputs:
        n = row["name"].lower()
        d = (row.get("default") or "")
        if n in {"out", "output", "dest", "report", "json"} or "/" in d or d.endswith((".json", ".txt", ".log")):
            outputs.append({"name": row["name"], "path_hint": row.get("default"), "source": row["source"]})
    return inputs, sorted(outputs, key=lambda x: x["name"])


def _extract_node_interface(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = _read_text(path)
    inputs: list[dict[str, Any]] = []
    for m in re.finditer(r"yargs\.option\((['\"])([^'\"]+)\1", text):
        nm = m.group(2)
        inputs.append({"name": nm, "flags": [f"--{nm}"], "required": None, "default": None, "type": None, "help": None, "source": "node:yargs"})
    for m in re.finditer(r"\.positional\((['\"])([^'\"]+)\1", text):
        nm = m.group(2)
        inputs.append({"name": nm, "flags": [], "required": None, "default": None, "type": None, "help": None, "source": "node:yargs"})
    for m in re.finditer(r"\.(requiredOption|option)\((['\"])([^'\"]+)\2", text):
        spec = m.group(3)
        flags = [p.strip() for p in spec.split(",") if p.strip().startswith("-")]
        longf = [f for f in flags if f.startswith("--")]
        name = (longf[0] if longf else (flags[0] if flags else spec)).lstrip("-")
        inputs.append({"name": name, "flags": flags, "required": True if m.group(1) == "requiredOption" else None, "default": None, "type": None, "help": None, "source": "node:commander"})
    inputs = sorted(inputs, key=lambda x: (x["name"], x["flags"][0] if x["flags"] else ""))[:MAX_AGENT_INPUTS]
    outputs = [{"name": r["name"], "path_hint": None, "source": r["source"]} for r in inputs if r["name"].lower() in {"out", "output", "report", "json"}]
    return inputs, sorted(outputs, key=lambda x: x["name"])


def _extract_shell_interface(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = _read_text(path)
    m = re.search(r"getopts\s+['\"]([^'\"]+)['\"]", text)
    if not m:
        return [], []
    spec = m.group(1)
    inputs = []
    for ch in spec:
        if ch == ":":
            continue
        inputs.append({"name": ch, "flags": [f"-{ch}"], "required": None, "default": None, "type": None, "help": None, "source": "sh:getopts"})
    return sorted(inputs, key=lambda x: x["name"])[:MAX_AGENT_INPUTS], []


def _extract_yaml_interface(kind: str, path: Path, data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    inputs: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    invocation: list[dict[str, Any]] = []

    def add_input_map(src: str, d: Any) -> None:
        if isinstance(d, dict):
            for k in sorted(d):
                v = d[k] if isinstance(d[k], dict) else {}
                inputs.append({
                    "name": k,
                    "flags": [],
                    "required": v.get("required") if isinstance(v.get("required"), bool) else None,
                    "default": str(v.get("default")) if v.get("default") is not None else None,
                    "type": str(v.get("type")) if v.get("type") is not None else None,
                    "help": v.get("description") if isinstance(v.get("description"), str) else None,
                    "source": src,
                })

    if kind == Kind.GITHUB_WORKFLOW:
        on = _yaml_on(data)
        if isinstance(on, dict):
            wd = on.get("workflow_dispatch")
            wc = on.get("workflow_call")
            if wd is not None:
                invocation.append({"pattern": "workflow_dispatch", "source": "yaml:on"})
                if isinstance(wd, dict):
                    add_input_map("yaml:on.workflow_dispatch.inputs", wd.get("inputs"))
            if wc is not None:
                invocation.append({"pattern": "workflow_call", "source": "yaml:on"})
                if isinstance(wc, dict):
                    add_input_map("yaml:on.workflow_call.inputs", wc.get("inputs"))
                    outs = wc.get("outputs")
                    if isinstance(outs, dict):
                        for k in sorted(outs):
                            outputs.append({"name": k, "path_hint": None, "source": "yaml:on.workflow_call.outputs"})
        jobs = data.get("jobs")
        if isinstance(jobs, dict):
            for _, job in sorted(jobs.items()):
                if isinstance(job, dict) and isinstance(job.get("outputs"), dict):
                    for k in sorted(job["outputs"]):
                        outputs.append({"name": k, "path_hint": None, "source": "yaml:jobs.outputs"})

    if kind == Kind.GITHUB_COMPOSITE_ACTION:
        add_input_map("action.yml:inputs", data.get("inputs"))
        outs = data.get("outputs")
        if isinstance(outs, dict):
            for k in sorted(outs):
                outputs.append({"name": k, "path_hint": None, "source": "action.yml:outputs"})
        invocation.append({"pattern": f"uses: {_rel(discover_repo_root(path.parent), path.parent)}@<ref>", "source": "action.yml"})

    return {
        "inputs": sorted(inputs, key=lambda x: (x["name"], x["flags"][0] if x["flags"] else ""))[:MAX_AGENT_INPUTS],
        "outputs": sorted(outputs, key=lambda x: x["name"]),
        "invocation": sorted(invocation, key=lambda x: (x["pattern"], x["source"])),
    }


def _python_module_name(rel: str) -> str | None:
    if not rel.startswith("engine/exoneural_governor/") or not rel.endswith(".py"):
        return None
    mod = rel[len("engine/") : -3].replace("/", ".")
    if mod.endswith(".__init__"):
        return mod[: -len(".__init__")]
    return mod


def _resolve_py_import(repo_root: Path, src: Path, module: str | None, level: int, alias_name: str | None) -> Path | None:
    if level > 0:
        base = src.parent
        for _ in range(max(0, level - 1)):
            base = base.parent
        parts = []
        if module:
            parts.extend([p for p in module.split(".") if p])
        if alias_name and alias_name != "*":
            parts.extend([p for p in alias_name.split(".") if p])
        cand = base.joinpath(*parts) if parts else base
        for p in [cand.with_suffix(".py"), cand / "__init__.py"]:
            if p.exists() and p.is_file() and repo_root in p.resolve().parents:
                return p
        return None

    if module:
        parts = [p for p in module.split(".") if p]
        cand = repo_root.joinpath(*parts)
        for p in [cand.with_suffix(".py"), cand / "__init__.py"]:
            if p.exists() and p.is_file():
                return p
        if alias_name and alias_name != "*":
            parts2 = parts + [alias_name]
            cand2 = repo_root.joinpath(*parts2)
            for p in [cand2.with_suffix(".py"), cand2 / "__init__.py"]:
                if p.exists() and p.is_file():
                    return p
    elif alias_name and alias_name != "*":
        cand = repo_root.joinpath(*alias_name.split("."))
        for p in [cand.with_suffix(".py"), cand / "__init__.py"]:
            if p.exists() and p.is_file():
                return p
    return None




def _resolve_relative_import_for_graph(current_file: Path, module: str | None, level: int, name: str) -> Path | None:
    base_dir = current_file.parent
    parent = base_dir
    for _ in range(max(0, level - 1)):
        parent = parent.parent
    module_parts = [part for part in (module.split(".") if module else []) if part]
    name_parts = [part for part in name.split(".") if part]
    candidate = parent.joinpath(*(module_parts + name_parts)) if (module_parts or name_parts) else parent
    for path in (candidate.with_suffix('.py'), candidate / '__init__.py'):
        if path.exists() and path.is_file():
            return path
    return None


def _resolve_same_root_absolute_import_for_graph(root_dir: Path, module_name: str) -> Path | None:
    parts = [part for part in module_name.split('.') if part]
    if not parts:
        return None
    candidate = root_dir.joinpath(*parts)
    for path in (candidate.with_suffix('.py'), candidate / '__init__.py'):
        if path.exists() and path.is_file():
            return path
    return None


def _extract_python_import_edges_for_graph(repo_root: Path, bounded_paths: set[str], parse_failures: list[str] | None = None) -> list[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    parse_failures = parse_failures if parse_failures is not None else []
    bounded_files = sorted(repo_root / rel for rel in bounded_paths)
    group_roots = [
        repo_root / 'tools' / 'dao-arbiter' / 'dao_lifebook',
        repo_root / 'engine' / 'exoneural_governor',
        repo_root / 'engine' / 'tools',
    ]
    for src_file in bounded_files:
        if src_file.suffix != '.py' or not src_file.exists():
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
            tree = ast.parse(_read_text(src_file))
        except SyntaxError:
            parse_failures.append(_canon_rel(src_rel))
            continue
        except Exception:
            parse_failures.append(_canon_rel(src_rel))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                level = int(node.level or 0)
                module = node.module
                for alias in node.names:
                    alias_name = alias.name
                    dst_file: Path | None = None
                    if level > 0:
                        dst_file = _resolve_relative_import_for_graph(src_file, module, level, alias_name)
                        if dst_file is None and module:
                            dst_file = _resolve_relative_import_for_graph(src_file, module, level, '')
                    elif module:
                        full = module if alias_name == '*' else f"{module}.{alias_name}"
                        dst_file = _resolve_same_root_absolute_import_for_graph(root_dir, full)
                        if dst_file is None:
                            dst_file = _resolve_same_root_absolute_import_for_graph(root_dir, module)
                    elif alias_name != '*':
                        dst_file = _resolve_same_root_absolute_import_for_graph(root_dir, alias_name)
                    if dst_file is None or not dst_file.exists():
                        continue
                    dst_rel = _rel(repo_root, dst_file)
                    if dst_rel == src_rel or dst_rel not in bounded_paths:
                        continue
                    edges.add((src_rel, dst_rel, 'IMPORTS_PY'))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    dst_file = _resolve_same_root_absolute_import_for_graph(root_dir, alias.name)
                    if dst_file is None or not dst_file.exists():
                        continue
                    dst_rel = _rel(repo_root, dst_file)
                    if dst_rel == src_rel or dst_rel not in bounded_paths:
                        continue
                    edges.add((src_rel, dst_rel, 'IMPORTS_PY'))
    return sorted(edges)


def _extract_js_import_edges_for_graph(repo_root: Path, bounded_paths: set[str]) -> list[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    for rel in sorted(bounded_paths):
        if Path(rel).suffix not in {".js", ".mjs", ".ts", ".tsx", ".jsx"}:
            continue
        src_file = repo_root / rel
        if not src_file.exists():
            continue
        text = _read_text(src_file)
        specs = [m.group(1) for m in re.finditer(r"import\s+[^\n]*?from\s+['\"]([^'\"]+)['\"]", text)]
        specs.extend([m.group(1) for m in re.finditer(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)", text)])
        for spec in sorted(specs):
            if not spec.startswith(("./", "../")):
                continue
            dst_file = _resolve_js_local(src_file.parent, spec)
            if dst_file is None or not dst_file.exists():
                continue
            dst_rel = _rel(repo_root, dst_file)
            if dst_rel == rel or dst_rel not in bounded_paths:
                continue
            edges.add((rel, dst_rel, "IMPORTS_JS"))
    return sorted(edges)


def _extract_include_edges_for_graph(repo_root: Path, bounded_paths: set[str]) -> list[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    for rel in sorted(bounded_paths):
        src_file = repo_root / rel
        if not src_file.exists():
            continue
        text = _read_text(src_file)
        if src_file.suffix.lower() in {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}:
            for m in re.finditer(r'^\s*#include\s+"([^"]+)"', text, flags=re.MULTILINE):
                dst_file = (src_file.parent / m.group(1).strip()).resolve()
                if not dst_file.exists() or not dst_file.is_file():
                    continue
                dst_rel = _rel(repo_root, dst_file)
                if dst_rel == rel or dst_rel not in bounded_paths:
                    continue
                edges.add((rel, dst_rel, "INCLUDES"))
        if src_file.name == "Makefile" or src_file.suffix in {".mk", ".make"}:
            for m in re.finditer(r"^\s*include\s+(.+)$", text, flags=re.MULTILINE):
                spec = m.group(1).strip().split()[0]
                dst_file = (src_file.parent / spec).resolve()
                if not dst_file.exists() or not dst_file.is_file():
                    continue
                dst_rel = _rel(repo_root, dst_file)
                if dst_rel == rel or dst_rel not in bounded_paths:
                    continue
                edges.add((rel, dst_rel, "INCLUDES"))
    return sorted(edges)
def _resolve_js_local(base: Path, spec: str) -> Path | None:
    cand = (base / spec).resolve()
    candidates = [cand, *[cand.with_suffix(ext) for ext in [".js", ".mjs", ".ts"]], cand / "index.js", cand / "index.mjs", cand / "index.ts"]
    for p in candidates:
        if p.exists() and p.is_file():
            return p
    return None


def _extract_python_dep_paths(repo_root: Path, rel: str, unknowns: dict[str, Any]) -> list[str]:
    path = repo_root / rel
    try:
        tree = ast.parse(_read_text(path))
    except Exception:
        return []
    deps: set[str] = set()
    fails: list[dict[str, str]] = unknowns.setdefault("import_resolution_failures", [])
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                target = _resolve_py_import(repo_root, path, node.module, int(node.level or 0), alias.name)
                spec = ("." * int(node.level or 0)) + ((node.module + ".") if node.module else "") + alias.name
                if target is None and (int(node.level or 0) > 0 or (node.module and (node.module.startswith(".") is False))):
                    fails.append({"from_path": rel, "spec": spec})
                elif target is not None:
                    deps.add(_rel(repo_root, target))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                target = _resolve_py_import(repo_root, path, alias.name, 0, None)
                if target is None:
                    fails.append({"from_path": rel, "spec": alias.name})
                else:
                    deps.add(_rel(repo_root, target))
    deps.discard(rel)
    return sorted(deps)


def _extract_js_dep_paths(repo_root: Path, rel: str, unknowns: dict[str, Any]) -> list[str]:
    path = repo_root / rel
    text = _read_text(path)
    deps: set[str] = set()
    fails: list[dict[str, str]] = unknowns.setdefault("import_resolution_failures", [])
    specs = [m.group(1) for m in re.finditer(r"import\s+[^\n]*?from\s+['\"]([^'\"]+)['\"]", text)]
    specs.extend([m.group(1) for m in re.finditer(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)", text)])
    for spec in sorted(specs):
        if not spec.startswith(("./", "../")):
            continue
        target = _resolve_js_local(path.parent, spec)
        if target is None:
            fails.append({"from_path": rel, "spec": spec})
        else:
            deps.add(_rel(repo_root, target))
    deps.discard(rel)
    return sorted(deps)


def _extract_wiring_edges(repo_root: Path, agents: list[dict[str, Any]]) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, set[str]]]:
    known = {a["path"] for a in agents}
    edges: set[tuple[str, str, str]] = set()
    parse_failures: list[str] = []
    dangling: list[dict[str, str]] = []
    depends: dict[str, set[str]] = {p: set() for p in known}

    workflows = sorted([repo_root / p for p in known if p.startswith(".github/workflows/") and Path(p).suffix in YAML_SUFFIXES])
    actions = sorted([repo_root / p for p in known if p.startswith(".github/actions/") and Path(p).name in {"action.yml", "action.yaml"}])

    for wf in workflows:
        data = _safe_load_yaml(repo_root, wf, parse_failures)
        if not isinstance(data, dict):
            continue
        src = _rel(repo_root, wf)
        jobs = data.get("jobs")
        if isinstance(jobs, dict):
            for _, job in sorted(jobs.items()):
                if not isinstance(job, dict):
                    continue
                uses = job.get("uses")
                if isinstance(uses, str):
                    target = _normalize_local_workflow_ref(repo_root, wf, uses)
                    if target is not None:
                        dst = _rel(repo_root, target)
                        edges.add((src, dst, "USES_REUSABLE_WORKFLOW"))
                        depends[src].add(dst)
                steps = job.get("steps") if isinstance(job.get("steps"), list) else []
                for step in steps:
                    if not isinstance(step, dict):
                        continue
                    uses = step.get("uses")
                    if isinstance(uses, str):
                        target = _normalize_local_action_ref(repo_root, wf, uses)
                        if target is not None:
                            dst = _rel(repo_root, target)
                            edges.add((src, dst, "USES_LOCAL_ACTION"))
                            depends[src].add(dst)
                    run = step.get("run")
                    if isinstance(run, str):
                        base = repo_root
                        wd = step.get("working-directory")
                        if isinstance(wd, str) and wd.strip():
                            base = (repo_root / wd.strip()).resolve()
                        for sp in _extract_run_paths(repo_root, wf, run, base):
                            dst = _rel(repo_root, sp)
                            edges.add((src, dst, "RUNS_SCRIPT"))
                            depends[src].add(dst)

    for action in actions:
        data = _safe_load_yaml(repo_root, action, parse_failures)
        if not isinstance(data, dict):
            continue
        src = _rel(repo_root, action)
        runs = data.get("runs") if isinstance(data.get("runs"), dict) else {}
        steps = runs.get("steps") if isinstance(runs.get("steps"), list) else []
        for step in steps:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if isinstance(uses, str):
                target = _normalize_local_action_ref(repo_root, action, uses)
                if target is not None:
                    dst = _rel(repo_root, target)
                    edges.add((src, dst, "USES_ACTION_IN_ACTION"))
                    depends[src].add(dst)
            run = step.get("run")
            if isinstance(run, str):
                for sp in _extract_run_paths(repo_root, action, run, repo_root):
                    dst = _rel(repo_root, sp)
                    edges.add((src, dst, "RUNS_SCRIPT"))
                    depends[src].add(dst)

    mf = repo_root / "Makefile"
    if mf.exists():
        src = _rel(repo_root, mf)
        for line in _read_text(mf).splitlines():
            if line.startswith("\t"):
                for sp in _extract_run_paths(repo_root, mf, line, repo_root):
                    dst = _rel(repo_root, sp)
                    edges.add((src, dst, "RUNS_SCRIPT"))
                    depends[src].add(dst)

    bounded_import_paths = {
        path
        for path in known
        if path.startswith("tools/dao-arbiter/dao_lifebook/")
        or path.startswith("engine/exoneural_governor/")
        or path.startswith("engine/tools/")
    }
    py_parse_failures: list[str] = []
    for src, dst, et in _extract_python_import_edges_for_graph(repo_root, bounded_import_paths, parse_failures=py_parse_failures):
        edges.add((src, dst, et))
        depends.setdefault(src, set()).add(dst)
    for src, dst, et in _extract_js_import_edges_for_graph(repo_root, bounded_import_paths):
        edges.add((src, dst, et))
        depends.setdefault(src, set()).add(dst)
    for src, dst, et in _extract_include_edges_for_graph(repo_root, bounded_import_paths):
        edges.add((src, dst, et))
        depends.setdefault(src, set()).add(dst)

    resolved: list[dict[str, str]] = []
    for s, d, t in sorted(edges, key=lambda x: (x[0], x[1], x[2])):
        if s in known and d in known:
            resolved.append({"from_id": _sha12(s), "to_id": _sha12(d), "edge_type": t, "from_path": s, "to_path": d})
        else:
            dangling.append({"from_path": s, "to_path": d, "edge_type": t})

    return resolved, {
        "parse_failures": sorted(set([_canon_rel(x) for x in parse_failures + py_parse_failures])),
        "dangling_edges": sorted(dangling, key=lambda x: (x["from_path"], x["to_path"], x["edge_type"])),
        "import_resolution_failures": [],
    }, depends


def _build_graph(nodes: list[str], edges: list[tuple[str, str]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    out = {n: [] for n in nodes}
    inn = {n: [] for n in nodes}
    for s, d in sorted(set(edges)):
        if s not in out:
            out[s] = []
            inn[s] = []
        if d not in out:
            out[d] = []
            inn[d] = []
        out[s].append(d)
        inn[d].append(s)
    for n in sorted(out):
        out[n] = sorted(set(out[n]))
        inn[n] = sorted(set(inn[n]))
    return out, inn


def pagerank(nodes: list[str], edges: list[tuple[str, str]], damping: float = 0.85, max_iter: int = 100, tol: float = 1e-10) -> dict[str, float]:
    ordered = sorted(set(nodes))
    if not ordered:
        return {}
    out, inn = _build_graph(ordered, edges)
    n = len(ordered)
    ranks = {k: 1.0 / n for k in ordered}
    for _ in range(max_iter):
        dangling = sum(ranks[k] for k in ordered if not out[k])
        new: dict[str, float] = {}
        delta = 0.0
        for node in ordered:
            v = (1.0 - damping) / n + damping * dangling / n
            for src in inn[node]:
                v += damping * (ranks[src] / len(out[src]))
            new[node] = v
            delta += abs(v - ranks[node])
        ranks = new
        if delta <= tol:
            break
    total = sum(ranks.values())
    return {k: (v / total if total else 0.0) for k, v in sorted(ranks.items())}


def betweenness_centrality_brandes(nodes: list[str], edges: list[tuple[str, str]]) -> dict[str, float]:
    ordered = sorted(set(nodes))
    out, _ = _build_graph(ordered, edges)
    bc = {n: 0.0 for n in ordered}
    for source in ordered:
        stack: list[str] = []
        pred = {n: [] for n in ordered}
        sigma = {n: 0.0 for n in ordered}
        dist = {n: -1 for n in ordered}
        sigma[source] = 1.0
        dist[source] = 0
        q: deque[str] = deque([source])
        while q:
            v = q.popleft()
            stack.append(v)
            for w in out[v]:
                if dist[w] < 0:
                    q.append(w)
                    dist[w] = dist[v] + 1
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = {n: 0.0 for n in ordered}
        while stack:
            w = stack.pop()
            for v in sorted(pred[w]):
                if sigma[w] > 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != source:
                bc[w] += delta[w]
    n = len(ordered)
    scale = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 0.0
    return {k: bc[k] * scale for k in ordered}


def strongly_connected_components(nodes: list[str], edges: list[tuple[str, str]]) -> list[tuple[str, ...]]:
    out, _ = _build_graph(sorted(set(nodes)), edges)
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    idx: dict[str, int] = {}
    low: dict[str, int] = {}
    result: list[tuple[str, ...]] = []

    def sc(v: str) -> None:
        nonlocal index
        idx[v] = index
        low[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        for w in out[v]:
            if w not in idx:
                sc(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            result.append(tuple(sorted(comp)))

    for n in sorted(out):
        if n not in idx:
            sc(n)
    return sorted(result)


def _repo_fingerprint(repo_root: Path, exclude_rel: set[str]) -> str:
    code, out = _run_git(["rev-parse", "HEAD"], repo_root)
    if code == 0 and out:
        return out
    sha = hashlib.sha256()
    for p in sorted(_iter_files(repo_root)):
        rel = _rel(repo_root, p)
        if rel in exclude_rel:
            continue
        sha.update(rel.encode())
        sha.update(b"\n")
        st = p.stat()
        sha.update(f"{st.st_size}:{st.st_mtime_ns}".encode())
        sha.update(b"\n")
    return sha.hexdigest()


def _compute_evolution(repo_root: Path, rel: str, unknowns: dict[str, Any]) -> dict[str, Any]:
    code, _ = _run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    if code != 0:
        unknowns["git_unavailable"] = True
        return {"commit_count": None, "authors": [], "top_author": None, "top_author_share": None, "last_commit": None, "last_date": None}
    rc, out = _run_git(["log", "--follow", "--format=%H|%an|%ad", "--date=iso-strict", "--", rel], repo_root)
    if rc != 0:
        return {"commit_count": 0, "authors": [], "top_author": None, "top_author_share": 0.0, "last_commit": None, "last_date": None}
    lines = out.splitlines()
    if len(lines) > MAX_GIT_LOG_LINES:
        unknowns.setdefault("evolution_truncated_paths", []).append(rel)
        lines = lines[:MAX_GIT_LOG_LINES]
    commits = 0
    ctr: Counter[str] = Counter()
    last_commit = None
    last_date = None
    for i, line in enumerate(lines):
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        sha, author, date = parts
        commits += 1
        ctr[author] += 1
        if i == 0:
            last_commit = sha
            last_date = date
    top3 = sorted(ctr.items(), key=lambda x: (-x[1], x[0]))[:3]
    authors = [{"name": n, "count": c, "share": round(c / commits, 6) if commits else 0.0} for n, c in top3]
    top_author = authors[0]["name"] if authors else None
    top_share = authors[0]["share"] if authors else 0.0
    return {"commit_count": commits, "authors": authors, "top_author": top_author, "top_author_share": round(float(top_share), 6), "last_commit": last_commit, "last_date": last_date}


def _iter_scan_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for p in _iter_files(repo_root):
        rel = _rel(repo_root, p)
        if p.stat().st_size <= MAX_SCAN_TEXT_SIZE and p.suffix.lower() in {".py", ".md", ".yml", ".yaml", ".json", ".js", ".mjs", ".ts", ".sh", ".bash", ".txt", ""}:
            files.append(p)
        elif rel.endswith("Makefile") and p.stat().st_size <= MAX_SCAN_TEXT_SIZE:
            files.append(p)
    return sorted(files)




def _core_candidate_eligible(path: str) -> bool:
    rel = _canon_rel(path)
    return not rel.startswith("engine/exoneural_governor/_")

def _classify_subkind(agent: dict[str, Any], out_edges: dict[str, int]) -> str:
    rel = agent["path"].lower()
    tok = rel.replace("/", " ")
    has_outputs = bool(agent["interface"]["outputs"])
    if agent["kind"] in {Kind.GITHUB_WORKFLOW, Kind.GITHUB_COMPOSITE_ACTION, Kind.MAKEFILE} or out_edges.get(agent["path"], 0) > 0 or re.search(r"dispatch|trigger|orchestr|runner|pipeline", tok):
        return "ORCHESTRATOR"
    if re.search(r"verify|validate|check|audit|lint|test|scan|gate", tok):
        return "VALIDATOR"
    if re.search(r"generate|build|rebuild|sign|make|render|convert|ensure|compile|bundle", tok):
        return "TRANSFORMER"
    if has_outputs and out_edges.get(agent["path"], 0) == 0 and re.search(r"report|manifest|artifact|evidence", tok):
        return "DATA_SINK"
    return "OTHER"


def _populate_interfaces_and_deps(repo_root: Path, agents: list[dict[str, Any]], unknowns: dict[str, Any], depends_from_edges: dict[str, set[str]]) -> None:
    by_path = {a["path"]: a for a in agents}
    for agent in agents:
        rel = agent["path"]
        path = repo_root / rel
        kind = agent["kind"]
        iface = {"inputs": [], "outputs": [], "invocation": []}
        if path.suffix in YAML_SUFFIXES:
            data = _safe_load_yaml(repo_root, path, unknowns.setdefault("parse_failures", []))
            if isinstance(data, dict):
                iface = _extract_yaml_interface(kind, path, data)
        elif path.suffix == ".py":
            ins, outs = _extract_python_interface(path)
            iface = {"inputs": ins, "outputs": outs, "invocation": []}
            module = _python_module_name(rel)
            if module:
                iface["invocation"].append({"pattern": f"python -m {module}", "source": "python:module"})
        elif path.suffix in {".js", ".mjs", ".ts"}:
            ins, outs = _extract_node_interface(path)
            iface = {"inputs": ins, "outputs": outs, "invocation": []}
        elif path.suffix in {".sh", ".bash"}:
            ins, outs = _extract_shell_interface(path)
            iface = {"inputs": ins, "outputs": outs, "invocation": []}
        agent["interface"] = iface

        deps = set(depends_from_edges.get(rel, set()))
        if path.suffix == ".py":
            deps.update(_extract_python_dep_paths(repo_root, rel, unknowns))
        if path.suffix in {".js", ".mjs", ".ts"}:
            deps.update(_extract_js_dep_paths(repo_root, rel, unknowns))
        deps.discard(rel)
        agent["depends_on_paths"] = sorted(d for d in deps if d in by_path)


def _populate_invocation_examples(repo_root: Path, agents: list[dict[str, Any]]) -> None:
    scan_files = _iter_scan_files(repo_root)
    hits: dict[str, list[dict[str, Any]]] = {a["path"]: [] for a in agents}
    patterns: dict[str, list[re.Pattern[str]]] = {}
    for a in agents:
        rel = a["path"]
        pats = [re.compile(re.escape(rel))]
        if a["kind"] in {Kind.GITHUB_WORKFLOW, Kind.GITHUB_COMPOSITE_ACTION}:
            bare = rel[2:] if rel.startswith("./") else rel
            pats.append(re.compile(rf"uses:\s*(?:\./)?{re.escape(bare)}(?:@[^\s]+)?"))
        mod = _python_module_name(rel)
        if mod:
            pats.append(re.compile(rf"python\s+-m\s+{re.escape(mod)}\b"))
        patterns[rel] = pats

    for f in scan_files:
        src = _rel(repo_root, f)
        text = _read_text(f)
        for ln, line in enumerate(text.splitlines(), start=1):
            for rel, pats in patterns.items():
                if len(hits[rel]) >= MAX_INVOCATION_EXAMPLES:
                    continue
                if any(p.search(line) for p in pats):
                    hits[rel].append({"source_path": src, "line": ln, "excerpt": line.strip()[:160]})
    for a in agents:
        a["invocation_examples"] = hits[a["path"]][:MAX_INVOCATION_EXAMPLES]


def _build_model_once(repo_root: Path, out_path: Path, contract_path: Path, include_globs: list[str] | None = None, exclude_globs: list[str] | None = None) -> dict[str, Any]:
    agents = discover_agents(repo_root, include_globs=include_globs, exclude_globs=exclude_globs)
    edges, unknowns, depends_from_edges = _extract_wiring_edges(repo_root, agents)
    _populate_interfaces_and_deps(repo_root, agents, unknowns, depends_from_edges)
    _populate_invocation_examples(repo_root, agents)
    for a in agents:
        a["evolution"] = _compute_evolution(repo_root, a["path"], unknowns)

    out_edge_count: Counter[str] = Counter([e["from_path"] for e in edges])
    for a in agents:
        a["subkind"] = _classify_subkind(a, out_edge_count)

    node_ids = sorted(a["agent_id"] for a in agents)
    directed = [(e["from_id"], e["to_id"]) for e in edges]

    degree = {nid: 0 for nid in node_ids}
    for s, d in directed:
        degree[s] += 1
        degree[d] += 1

    active_nodes = sorted([nid for nid, deg in degree.items() if deg > 0])
    active_edges = [(s, d) for s, d in directed if s in degree and d in degree and degree[s] > 0 and degree[d] > 0]

    pr_active = pagerank(active_nodes, active_edges) if active_nodes else {}
    bc_active = betweenness_centrality_brandes(active_nodes, active_edges) if active_nodes else {}
    pr = {nid: pr_active.get(nid, 0.0) for nid in node_ids}
    bc = {nid: bc_active.get(nid, 0.0) for nid in node_ids}
    max_pr = max(pr.values()) if pr else 0.0
    max_bc = max(bc.values()) if bc else 0.0
    nonzero = sum(1 for v in degree.values() if v > 0)
    k = max(5, min(25, round(0.08 * nonzero))) if nonzero else 5

    by_id = {a["agent_id"]: a for a in agents}
    ranked: list[dict[str, Any]] = []
    candidate_nodes = [nid for nid in node_ids if _core_candidate_eligible(by_id[nid]["path"])]
    for nid in candidate_nodes:
        pr_norm = pr.get(nid, 0.0) / max_pr if max_pr else 0.0
        bc_norm = bc.get(nid, 0.0) / max_bc if max_bc else 0.0
        ranked.append({"agent_id": nid, "path": by_id[nid]["path"], "kind": by_id[nid]["kind"], "pr": pr.get(nid, 0.0), "bc": bc.get(nid, 0.0), "pr_norm": pr_norm, "bc_norm": bc_norm, "core_score": 0.6 * pr_norm + 0.4 * bc_norm})
    ranked.sort(key=lambda r: (-r["core_score"], -r["pr_norm"], -r["bc_norm"], r["agent_id"]))

    core_candidates = [{"agent_id": r["agent_id"], "path": r["path"], "kind": r["kind"], "pr": r["pr"], "bc": r["bc"], "core_score": r["core_score"], "rank": i} for i, r in enumerate(ranked[:k], start=1)]
    if git_available() and in_git_repo(repo_root):
        for row in core_candidates:
            row["blame"] = blame_for_path(repo_root, row["path"])
    sccs = strongly_connected_components(node_ids, directed)
    events = [{"type": "ARCHITECTURAL_CYCLE_DETECTED", "agent_ids": list(comp)} for comp in sccs if len(comp) > 1]
    unknowns["events"] = sorted(events, key=lambda e: tuple(e["agent_ids"]))

    exclude = {x for x in (_rel_if_within(repo_root, out_path), _rel_if_within(repo_root, contract_path)) if x is not None}
    return {
        "repo_root": repo_root.as_posix(),
        "repo_fingerprint": _repo_fingerprint(repo_root, exclude),
        "agents": sorted(agents, key=lambda a: a["agent_id"]),
        "edges": edges,
        "core_candidates": core_candidates,
        "counts": {
            "agents_count": len(agents),
            "edges_count": len(edges),
            "core_candidates_count": len(core_candidates),
        },
        "agents_count": len(agents),
        "wiring": {"edges": edges, "edges_count": len(edges)},
        "centrality": {"pagerank": {k: pr[k] for k in sorted(pr)}, "betweenness": {k: bc[k] for k in sorted(bc)}},
        "core_candidates_count": len(core_candidates),
        "metadata": {"core_candidates": core_candidates},
        "unknowns": unknowns,
    }



def _rel_if_within(repo_root: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return None

def generate_repo_model(repo_root: Path, out_path: Path | None = None, contract_out: Path | None = None, include_globs: list[str] | None = None, exclude_globs: list[str] | None = None) -> dict[str, Any]:
    out_path = out_path or (repo_root / "engine/artifacts/repo_model/repo_model.json")
    contract_out = contract_out or (repo_root / "engine/artifacts/repo_model/architecture_contract.jsonl")
    exclude = {x for x in (_rel_if_within(repo_root, out_path), _rel_if_within(repo_root, contract_out)) if x is not None}
    start_fp = _repo_fingerprint(repo_root, exclude)
    model = _build_model_once(repo_root, out_path, contract_out, include_globs=include_globs, exclude_globs=exclude_globs)
    end_fp = _repo_fingerprint(repo_root, exclude)
    rescans = 0
    if start_fp != end_fp:
        rescans = 1
        model = _build_model_once(repo_root, out_path, contract_out, include_globs=include_globs, exclude_globs=exclude_globs)
        end_fp = _repo_fingerprint(repo_root, exclude)
    stable = start_fp == end_fp
    model["scan"] = {
        "scan_start_fingerprint": start_fp,
        "scan_end_fingerprint": end_fp,
        "rescans": rescans,
        "fingerprint_stable": stable,
    }
    if not stable:
        model.setdefault("unknowns", {})["fingerprint_changed"] = True
    return model


def write_repo_model(out_path: Path, model: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _subdomain_tags(path: str, limit: int = 8) -> list[str]:
    p = path.replace("\\", "/").lstrip("./")
    segs = [s for s in p.split("/") if s]
    raw: list[str] = []
    for seg in segs:
        base = seg.rsplit(".", 1)[0]
        parts = [x for x in base.split("-") if x]
        raw.extend(parts)
        if len(raw) >= limit * 2:
            break
    stable_unique = list(dict.fromkeys(raw))
    return stable_unique[:limit]


def write_architecture_contract(out_path: Path, model: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    repo_root = Path(str(model.get("repo_root", ""))).resolve() if model.get("repo_root") else None
    can_blame = bool(repo_root and repo_root.exists() and git_available() and in_git_repo(repo_root))
    core_rank = {c.get("agent_id"): c.get("rank") for c in model.get("core_candidates", []) if isinstance(c, dict)}
    edge_index: dict[str, dict[str, int]] = {}
    for e in model.get("edges", []):
        if not isinstance(e, dict):
            continue
        src = e.get("from_id")
        et = e.get("edge_type")
        if not isinstance(src, str) or not isinstance(et, str):
            continue
        edge_index.setdefault(src, {})
        edge_index[src][et] = edge_index[src].get(et, 0) + 1

    rows = []
    for a in sorted(model.get("agents", []), key=lambda x: x["agent_id"]):
        inputs = a.get("interface", {}).get("inputs", [])
        outputs = a.get("interface", {}).get("outputs", [])
        invocation_examples = a.get("invocation_examples", [])
        # NOTE(repo-infra): deterministic fallback fields are required by contract-eval gates.
        blame = None
        if can_blame and repo_root is not None and core_rank.get(a["agent_id"]) is not None:
            blame = blame_for_path(repo_root, a["path"])
        rows.append({
            "agent_id": a["agent_id"],
            "path": a["path"],
            "kind": a["kind"],
            "subkind": a.get("subkind"),
            "name": a.get("name"),
            "inputs": inputs if isinstance(inputs, list) else [],
            "outputs": outputs if isinstance(outputs, list) else [],
            "depends_on_paths": a.get("depends_on_paths", []),
            "invocation_examples": invocation_examples if isinstance(invocation_examples, list) else [],
            "provides": sorted({o.get("name") for o in outputs if isinstance(o, dict) and isinstance(o.get("name"), str)}),
            "subdomain_tags": _subdomain_tags(str(a.get("path", ""))),
            "edges_summary": edge_index.get(a["agent_id"], {}),
            "core_rank": core_rank.get(a["agent_id"]),
            "blame": blame,
        })
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


# How to run (deterministic local commands):
#   PYTHONPATH=. python -m exoneural_governor repo-model --out engine/artifacts/repo_model/repo_model.json
#   PYTHONPATH=. python -m exoneural_governor contract-eval --out engine/artifacts/contract_eval

def cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="repo-model")
    p.add_argument("--out", default="engine/artifacts/repo_model/repo_model.json")
    p.add_argument("--contract-out", default="engine/artifacts/repo_model/architecture_contract.jsonl")
    p.add_argument("--no-contract", action="store_true")
    p.add_argument("--stdout", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--include-glob", action="append", default=[])
    p.add_argument("--exclude-glob", action="append", default=[])
    args = p.parse_args(argv)

    repo_root = discover_repo_root(Path.cwd())
    out_path = Path(args.out)
    out_path = out_path if out_path.is_absolute() else repo_root / out_path
    contract_out = Path(args.contract_out)
    contract_out = contract_out if contract_out.is_absolute() else repo_root / contract_out

    model = generate_repo_model(
        repo_root,
        out_path=out_path,
        contract_out=contract_out,
        include_globs=(args.include_glob or None),
        exclude_globs=(args.exclude_glob or None),
    )
    write_repo_model(out_path, model)
    if not args.no_contract:
        write_architecture_contract(contract_out, model)

    if args.stdout:
        print(json.dumps(model, indent=2, sort_keys=True))
    else:
        try:
            shown = out_path.relative_to(repo_root).as_posix()
        except ValueError:
            shown = out_path.as_posix()
        print(f"WROTE:{shown}")

    if args.strict and (model.get("unknowns", {}).get("dangling_edges") or model.get("unknowns", {}).get("parse_failures")):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
