#!/usr/bin/env python3
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

EXIT_OK = 0
EXIT_PYTHON = 10
EXIT_GIT = 11
EXIT_INSTALLER = 12
EXIT_OS = 13
EXIT_MAKE = 14

SUPPORTED_SYSTEMS = {"Linux", "Darwin"}


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str
    exit_code: int = EXIT_OK


def _python_check() -> CheckResult:
    if sys.version_info < (3, 10):
        return CheckResult(
            ok=False,
            message=(
                f"python.version=FAIL expected>=3.10 actual={sys.version_info.major}.{sys.version_info.minor}"
            ),
            exit_code=EXIT_PYTHON,
        )
    return CheckResult(
        ok=True,
        message=(
            f"python.version=PASS actual={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
    )


def _git_check() -> CheckResult:
    if shutil.which("git") is None:
        return CheckResult(
            ok=False,
            message="git.binary=FAIL missing",
            exit_code=EXIT_GIT,
        )
    proc = subprocess.run(
        ["git", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return CheckResult(
            ok=False,
            message=f"git.version=FAIL rc={proc.returncode}",
            exit_code=EXIT_GIT,
        )
    return CheckResult(ok=True, message=f"git.version=PASS {proc.stdout.strip()}")


def _installer_check() -> CheckResult:
    pip_proc = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    uv_path = shutil.which("uv")

    if pip_proc.returncode != 0:
        return CheckResult(
            ok=False,
            message="installer=FAIL python -m pip unavailable",
            exit_code=EXIT_INSTALLER,
        )

    parts: list[str] = []
    parts.append(f"pip=PASS {pip_proc.stdout.strip()}")

    if uv_path is None:
        parts.append("uv=MISS")
    else:
        uv_proc = subprocess.run(
            [uv_path, "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
        if uv_proc.returncode == 0:
            parts.append(f"uv=PASS {uv_proc.stdout.strip()}")
        else:
            parts.append(f"uv=FAIL rc={uv_proc.returncode}")

    return CheckResult(ok=True, message="installer=PASS " + " ; ".join(parts))


def _make_check() -> CheckResult:
    make_path = shutil.which("make")
    if make_path is None:
        return CheckResult(
            ok=False,
            message="make.binary=FAIL missing",
            exit_code=EXIT_MAKE,
        )
    return CheckResult(ok=True, message=f"make.binary=PASS {make_path}")


def _os_check() -> CheckResult:
    system = platform.system()
    if system not in SUPPORTED_SYSTEMS:
        return CheckResult(
            ok=False,
            message=f"os=FAIL unsupported={system}",
            exit_code=EXIT_OS,
        )
    return CheckResult(ok=True, message=f"os=PASS {system}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    checks = [
        _python_check(),
        _git_check(),
        _installer_check(),
        _make_check(),
        _os_check(),
    ]
    for check in checks:
        if not args.quiet:
            print(check.message)
        if not check.ok:
            return check.exit_code
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
