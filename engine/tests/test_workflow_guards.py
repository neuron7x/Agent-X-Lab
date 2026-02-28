from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPO_ROOT if (REPO_ROOT / ".github/workflows").exists() else REPO_ROOT.parent


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_verify_workflow_hygiene_passes() -> None:
    p = _run(["python", "tools/verify_workflow_hygiene.py"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_verify_action_pinning_passes() -> None:
    p = _run(["python", "tools/verify_action_pinning.py"])
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_verify_action_pinning_scans_yaml_files(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()

    pinned = workflows_dir / "ok.yml"
    pinned.write_text(
        """
name: pinned
jobs:
  t:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@1234567890123456789012345678901234567890
""".strip()
        + "\n",
        encoding="utf-8",
    )

    unpinned_yaml = workflows_dir / "bad.yaml"
    unpinned_yaml.write_text(
        """
name: unpinned
jobs:
  t:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
""".strip()
        + "\n",
        encoding="utf-8",
    )

    p = _run(
        [
            "python",
            "tools/verify_action_pinning.py",
            "--workflows",
            str(workflows_dir),
        ]
    )

    assert p.returncode != 0
    assert "bad.yaml:t:step_0:actions/setup-python@v5" in p.stdout


def test_verify_action_pinning_reports_relative_workflow_path(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "workflows"
    nested_dir = workflows_dir / "nested"
    nested_dir.mkdir(parents=True)
    bad = nested_dir / "bad.yaml"
    bad.write_text(
        """
name: unpinned
jobs:
  t:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
""".strip()
        + "\n",
        encoding="utf-8",
    )

    p = _run(
        [
            "python",
            "tools/verify_action_pinning.py",
            "--workflows",
            str(workflows_dir),
        ]
    )

    assert p.returncode != 0
    assert "nested/bad.yaml:t:step_0:actions/setup-python@v5" in p.stdout


def test_verify_action_pinning_fails_closed_for_missing_workflows(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    p = _run([
        "python",
        "tools/verify_action_pinning.py",
        "--workflows",
        str(missing),
    ])
    assert p.returncode == 2
    assert "FAIL: workflows directory validation failed" in p.stdout


def test_verify_action_pinning_fails_closed_for_empty_workflows(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    p = _run([
        "python",
        "tools/verify_action_pinning.py",
        "--workflows",
        str(workflows_dir),
    ])
    assert p.returncode == 2
    assert "no workflow files found" in p.stdout


def test_verify_action_pinning_autodetects_repo_root_from_subdir(tmp_path: Path) -> None:
    nested_dir = REPO_ROOT / "tests"
    p = subprocess.run(
        ["python", str(REPO_ROOT / "tools" / "verify_action_pinning.py")],
        cwd=nested_dir,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr


def test_verify_workflow_hygiene_fails_closed_for_missing_workflows(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    p = _run([
        "python",
        "tools/verify_workflow_hygiene.py",
        "--workflows",
        str(missing),
    ])
    assert p.returncode == 2
    assert "FAIL: workflow hygiene validation setup failed" in p.stdout


def test_verify_workflow_hygiene_fails_closed_for_empty_workflows(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    p = _run([
        "python",
        "tools/verify_workflow_hygiene.py",
        "--workflows",
        str(workflows_dir),
    ])
    assert p.returncode == 2
    assert "no workflow files found" in p.stdout


def test_verify_workflow_hygiene_fails_closed_for_invalid_yaml(tmp_path: Path) -> None:
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    (workflows_dir / "bad.yml").write_text("jobs: [", encoding="utf-8")
    p = _run([
        "python",
        "tools/verify_workflow_hygiene.py",
        "--workflows",
        str(workflows_dir),
    ])
    assert p.returncode == 2
    assert "FAIL: invalid workflow YAML detected" in p.stdout

def test_verify_workflow_hygiene_autodetects_repo_root_from_subdir() -> None:
    nested_dir = REPO_ROOT / "tests"
    p = subprocess.run(
        ["python", str(REPO_ROOT / "tools" / "verify_workflow_hygiene.py")],
        cwd=nested_dir,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, p.stdout + "\n" + p.stderr

def test_scorecard_workflow_has_fail_closed_sarif_contract() -> None:
    workflow_path = WORKFLOW_ROOT / ".github/workflows/scorecard.yml"
    if not workflow_path.exists():
        assert (WORKFLOW_ROOT / ".github/workflows/ci-supercheck.yml").exists()
        return

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
    assert (
        scorecard_step.get("uses")
        == "ossf/scorecard-action@62b7fcb92755d80d6e46e3f6d2f13213dcd89f05"
    )
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
    assert (
        upload_cs.get("uses")
        == "github/codeql-action/upload-sarif@b8f6507f3f5d3b9332f3d3e6585f6f8eecc65c0a"
    )
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
