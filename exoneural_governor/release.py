from __future__ import annotations

import json
import zipfile
from pathlib import Path

from .config import Config
from .manifest import write_manifest
from .util import ensure_dir, utc_now_iso


INCLUDE_DEFAULT = [
    "catalog",
    "docs",
    "configs",
    "vendor/scpe-cimqa-2026.3.0",
    "README.md",
    "SECURITY.redaction.yml",
    "requirements.lock",
    "pyproject.toml",
    "VR.json",
    ".github",
]


def build_release(
    cfg: Config, *, vr_path: Path | None = None, output_dir: Path | None = None
) -> dict:
    repo_root = cfg.repo_root.resolve()
    ts = utc_now_iso().replace(":", "").replace("Z", "Z")
    release_dir = (
        output_dir if output_dir is not None else (repo_root / "artifacts" / "release")
    )
    if not release_dir.is_absolute():
        release_dir = repo_root / release_dir
    ensure_dir(release_dir)

    vr_path = vr_path if vr_path is not None else (repo_root / "VR.json")
    if not vr_path.is_absolute():
        vr_path = repo_root / vr_path
    evidence_root_path: Path | None = None
    evidence_files_included = 0
    if vr_path.exists():
        vr = json.loads(vr_path.read_text(encoding="utf-8"))
        evidence_root = vr.get("evidence_root")
        if evidence_root:
            candidate = Path(str(evidence_root))
            evidence_root_path = (
                candidate.resolve()
                if candidate.is_absolute()
                else (repo_root / candidate).resolve()
            )
            if not evidence_root_path.is_relative_to(repo_root):
                raise ValueError(
                    "E_EVIDENCE_ROOT_OUTSIDE_REPO: evidence_root must be within repo_root"
                )
    zip_name = f"{cfg.artifact_name}-{ts}.zip"
    zip_path = release_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for item in INCLUDE_DEFAULT:
            src = repo_root / item
            if src.is_dir():
                for p in sorted(
                    [x for x in src.rglob("*") if x.is_file()],
                    key=lambda x: x.as_posix(),
                ):
                    z.write(p, arcname=p.relative_to(repo_root).as_posix())
            elif src.is_file():
                z.write(src, arcname=src.relative_to(repo_root).as_posix())

        if evidence_root_path is not None:
            epath = evidence_root_path
            if epath.exists() and epath.is_dir():
                for p in sorted(
                    [x for x in epath.rglob("*") if x.is_file()],
                    key=lambda x: x.as_posix(),
                ):
                    if not p.resolve().is_relative_to(
                        epath
                    ) or not p.resolve().is_relative_to(repo_root):
                        raise ValueError(
                            "E_EVIDENCE_PATH_OUTSIDE_REPO: evidence file escaped allowed roots"
                        )
                    # include under evidence/ to keep release small and explicit
                    z.write(p, arcname=("evidence/" + p.relative_to(epath).as_posix()))
                    evidence_files_included += 1

    write_manifest(release_dir, release_dir / "MANIFEST.release.json")
    report = {
        "utc": utc_now_iso(),
        "zip_path": str(zip_path.relative_to(repo_root)),
        "manifest_path": str(
            (release_dir / "MANIFEST.release.json").relative_to(repo_root)
        ),
        "included": INCLUDE_DEFAULT,
        "evidence_included": evidence_files_included > 0,
    }
    (release_dir / "release.report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
