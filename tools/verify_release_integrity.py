#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REQUIRED_FILES = [
    "checksums.txt",
    "provenance-predicate.json",
    "provenance.intoto.jsonl",
    "sbom.cyclonedx.json",
    "sbom.spdx.json",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, default=Path("artifacts/release"))
    args = parser.parse_args()

    release_dir = args.release_dir
    errors: list[str] = []

    if not release_dir.is_dir():
        print(f"FAIL: missing release directory: {release_dir}")
        return 1

    for name in REQUIRED_FILES:
        if not (release_dir / name).is_file():
            errors.append(f"missing_required_file:{name}")

    bundles = sorted(release_dir.glob("*.tar.gz"))
    if len(bundles) != 1:
        errors.append(f"expected_single_bundle:found={len(bundles)}")

    sig_files = sorted(release_dir.glob("*.tar.gz.sig"))
    if len(sig_files) != 1:
        errors.append(f"expected_single_signature:found={len(sig_files)}")

    if not errors and bundles:
        checksums = {}
        for line in (release_dir / "checksums.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                errors.append(f"invalid_checksum_line:{line}")
                continue
            checksums[Path(parts[1].lstrip("* " )).name] = parts[0]

        bundle_name = bundles[0].name
        expected_digest = checksums.get(bundle_name)
        if expected_digest is None:
            errors.append(f"missing_checksum_for_bundle:{bundle_name}")
        else:
            actual_digest = _sha256(bundles[0])
            if actual_digest != expected_digest:
                errors.append(
                    f"bundle_checksum_mismatch:expected={expected_digest}:actual={actual_digest}"
                )

    if (release_dir / "sbom.cyclonedx.json").is_file():
        cyclonedx = _load_json(release_dir / "sbom.cyclonedx.json")
        if not isinstance(cyclonedx, dict) or cyclonedx.get("bomFormat") != "CycloneDX":
            errors.append("invalid_cyclonedx_sbom")

    if (release_dir / "sbom.spdx.json").is_file():
        spdx = _load_json(release_dir / "sbom.spdx.json")
        if not isinstance(spdx, dict) or "spdxVersion" not in spdx:
            errors.append("invalid_spdx_sbom")

    if (release_dir / "provenance-predicate.json").is_file():
        predicate = _load_json(release_dir / "provenance-predicate.json")
        if not isinstance(predicate, dict) or "buildDefinition" not in predicate:
            errors.append("invalid_slsa_predicate")

    if (release_dir / "provenance.intoto.jsonl").is_file():
        provenance = _load_json(release_dir / "provenance.intoto.jsonl")
        if not isinstance(provenance, dict) or provenance.get("_type") != "https://in-toto.io/Statement/v1":
            errors.append("invalid_in_toto_statement")

    if errors:
        print("FAIL: release integrity verification failed")
        print("\n".join(sorted(errors)))
        return 1

    print("PASS: release integrity verification succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
