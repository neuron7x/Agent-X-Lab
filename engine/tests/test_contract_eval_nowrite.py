from __future__ import annotations

import json
from pathlib import Path

from exoneural_governor import contract_eval
from exoneural_governor._exec import ExecResult


def _minimal_model(repo_root: Path) -> dict:
    return {
        "repo_root": repo_root.as_posix(),
        "repo_fingerprint": "fp",
        "agents": [{"agent_id": "a1", "path": "engine/tools/x.py", "kind": "CLI_SCRIPT", "name": "x", "interface": {"inputs": []}}],
        "edges": [],
        "core_candidates": [{"agent_id": "a1", "rank": 1}],
        "counts": {"agents_count": 1, "edges_count": 0, "core_candidates_count": 1},
        "unknowns": {"dangling_edges": [], "parse_failures": []},
    }


def test_strict_no_write_detects_outside_out(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "engine").mkdir(parents=True)
    out_dir = tmp_path / "out"

    calls = {"status": 0}

    def fake_discover(_: Path) -> Path:
        return repo_root

    def fake_run(ctx, name, cmd, cwd=None, env=None):
        if name == "git_status_porcelain":
            calls["status"] += 1
            text = "?? outside.txt\n" if calls["status"] >= 2 else ""
            rec = ExecResult(name=name, command=cmd, returncode=0, stdout=text, stderr="")
        elif name == "git_untracked":
            text = "outside.txt\n" if calls["status"] >= 2 else ""
            rec = ExecResult(name=name, command=cmd, returncode=0, stdout=text, stderr="")
        elif name.startswith("git_head") or name.startswith("git_status_"):
            rec = ExecResult(name=name, command=cmd, returncode=0, stdout="abc\n", stderr="")
        elif name in {"python_version", "pip_version", "node_version", "npm_version", "git_version"}:
            rec = ExecResult(name=name, command=cmd, returncode=0, stdout="ok\n", stderr="")
        elif name.startswith("repo_model_"):
            out_idx = cmd.index("--out")
            contract_idx = cmd.index("--contract-out")
            model_path = Path(cmd[out_idx + 1])
            contract_path = Path(cmd[contract_idx + 1])
            model_path.parent.mkdir(parents=True, exist_ok=True)
            contract_path.parent.mkdir(parents=True, exist_ok=True)
            model_path.write_text(json.dumps(_minimal_model(repo_root)), encoding="utf-8")
            contract_path.write_text(json.dumps({"agent_id": "a1", "core_rank": 1, "blame": {"top_author": "a"}}) + "\n", encoding="utf-8")
            (repo_root / "outside.txt").write_text("x", encoding="utf-8")
            rec = ExecResult(name=name, command=cmd, returncode=0, stdout="", stderr="")
        else:
            rec = ExecResult(name=name, command=cmd, returncode=0, stdout="", stderr="")
        ctx.commands.append(rec)
        return rec

    monkeypatch.setattr(contract_eval, "discover_repo_root", fake_discover)
    monkeypatch.setattr(contract_eval, "_run_cmd", fake_run)
    monkeypatch.setattr(contract_eval, "git_available", lambda: True)
    monkeypatch.setattr(contract_eval, "in_git_repo", lambda _: True)

    code, report = contract_eval.evaluate_contracts(strict=True, out_path=out_dir, json_mode=True, no_write=True)
    assert code == 2
    g = {x["id"]: x for x in report["gates"]}
    assert g["GATE_A05_OUTSIDE_OUT_WRITE_CHECK"]["status"] == "FAIL"
    assert g["GATE_A02_STRICT_NO_WRITE"]["status"] == "FAIL"
    assert g["GATE_A05_OUTSIDE_OUT_WRITE_CHECK"]["details"]["outside_new_untracked"] == ["outside.txt"]
