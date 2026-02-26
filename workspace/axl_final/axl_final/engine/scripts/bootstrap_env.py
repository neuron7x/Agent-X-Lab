#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import sysconfig
from pathlib import Path

REQ_FILES = ["requirements.lock", "requirements-dev.txt"]
REQUIRED_IMPORTS = ["yaml", "jsonschema", "pytest", "mypy", "ruff"]


def run_install(req: str) -> int:
    return subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req]
    ).returncode


def add_base_site_packages() -> bool:
    base_prefix = Path(sys.base_prefix)
    purelib = Path(sysconfig.get_paths()["purelib"])  # venv site-packages
    base_pure = (
        base_prefix
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    if not base_pure.exists():
        return False
    purelib.mkdir(parents=True, exist_ok=True)
    (purelib / "_base_site_packages.pth").write_text(
        str(base_pure) + "\n", encoding="utf-8"
    )
    return True


def verify_imports() -> bool:
    mods = ",".join(REQUIRED_IMPORTS)
    code = "import " + mods
    return subprocess.run([sys.executable, "-c", code]).returncode == 0


def main() -> int:
    failures = [req for req in REQ_FILES if run_install(req) != 0]
    if not failures:
        return 0

    # Offline fallback for clean venv: link base interpreter site-packages and verify.
    if not add_base_site_packages():
        print(
            f"FAIL: pip install failed for {failures} and base site-packages not found."
        )
        return 1

    if not verify_imports():
        print(
            f"FAIL: pip install failed for {failures} and required modules unavailable after fallback."
        )
        return 1

    print(
        f"WARN: pip install failed for {failures}; using verified base site-packages fallback."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
