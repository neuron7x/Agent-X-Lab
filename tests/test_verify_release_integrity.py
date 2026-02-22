from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)


def test_verify_release_integrity_passes_with_fixture() -> None:
    fixture = REPO_ROOT / "artifacts" / "release-test"
    fixture.mkdir(parents=True, exist_ok=True)

    bundle = fixture / "agentx-lab.tar.gz"
    bundle.write_bytes(b"fixture")
    digest = __import__("hashlib").sha256(b"fixture").hexdigest()

    (fixture / "checksums.txt").write_text(
        f"{digest}  {bundle.name}\n", encoding="utf-8"
    )
    (fixture / "agentx-lab.tar.gz.sig").write_text("sig\n", encoding="utf-8")
    (fixture / "sbom.cyclonedx.json").write_text(
        json.dumps({"bomFormat": "CycloneDX", "components": []}), encoding="utf-8"
    )
    (fixture / "sbom.spdx.json").write_text(
        json.dumps({"spdxVersion": "SPDX-2.3"}), encoding="utf-8"
    )
    (fixture / "provenance-predicate.json").write_text(
        json.dumps({"buildDefinition": {}}), encoding="utf-8"
    )
    (fixture / "provenance.intoto.jsonl").write_text(
        json.dumps({"_type": "https://in-toto.io/Statement/v1"}), encoding="utf-8"
    )

    p = _run(
        [
            "python",
            "tools/verify_release_integrity.py",
            "--release-dir",
            str(fixture),
        ]
    )

    assert p.returncode == 0, p.stdout + "\n" + p.stderr
