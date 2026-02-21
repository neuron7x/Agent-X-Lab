from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_verify_workflow_hygiene_passes() -> None:
    p = _run(["python", "tools/verify_workflow_hygiene.py"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_verify_action_pinning_passes() -> None:
    p = _run(["python", "tools/verify_action_pinning.py"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_scorecard_workflow_has_fail_closed_sarif_contract() -> None:
    workflow_path = REPO_ROOT / ".github/workflows/scorecard.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    steps = workflow["jobs"]["analysis"]["steps"]
    named_steps = {
        step.get("name"): step
        for step in steps
        if isinstance(step, dict) and step.get("name")
    }

    assert "Run Scorecard" in named_steps
    scorecard_step = named_steps["Run Scorecard"]
    assert scorecard_step.get("id") == "scorecard"
    assert scorecard_step.get("continue-on-error") is True
    assert scorecard_step.get("uses") == "ossf/scorecard-action@v2.3.1"
    assert scorecard_step.get("with", {}).get("results_format") == "sarif"
    assert scorecard_step.get("with", {}).get("results_file") == (
        "artifacts/security/scorecard-results.sarif"
    )

    assert "Write deterministic Scorecard failure envelope" in named_steps
    failure_step = named_steps["Write deterministic Scorecard failure envelope"]
    assert failure_step.get("if") == (
        "steps.scorecard.outcome != 'success' && !hashFiles('artifacts/security/scorecard-results.sarif')"
    )

    assert "Upload Scorecard SARIF to code scanning" in named_steps
    upload_cs = named_steps["Upload Scorecard SARIF to code scanning"]
    assert upload_cs.get("uses") == "github/codeql-action/upload-sarif@v3"
    assert upload_cs.get("with", {}).get("sarif_file") == (
        "artifacts/security/scorecard-results.sarif"
    )

    assert "Upload Scorecard SARIF artifact" in named_steps
    upload_artifact = named_steps["Upload Scorecard SARIF artifact"]
    assert upload_artifact.get("with", {}).get("if-no-files-found") == "error"
    assert "artifacts/security/scorecard-results.sarif" in upload_artifact.get(
        "with", {}
    ).get("path", "")

    assert "Enforce Scorecard success" in named_steps
