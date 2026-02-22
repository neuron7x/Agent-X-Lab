from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Callable

from exoneural_governor.backend import resolve_backend
from exoneural_governor.network import validate_backend

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO_ROOT / "artifacts" / "reports" / "perf"
LATEST_REPORT_PATH = REPORT_DIR / "latest.json"
TREND_REPORT_PATH = REPORT_DIR / "trend.json"

WARMUP_RUNS = 5
MEASURED_RUNS = 50


def _measure(name: str, scenario: Callable[[], None]) -> dict[str, float | int | str]:
    for _ in range(WARMUP_RUNS):
        scenario()

    samples: list[float] = []
    for _ in range(MEASURED_RUNS):
        start = time.perf_counter()
        scenario()
        samples.append((time.perf_counter() - start) * 1000.0)

    samples.sort()
    p95_index = int(len(samples) * 0.95) - 1
    p95_index = max(0, p95_index)
    return {
        "name": name,
        "runs": MEASURED_RUNS,
        "p50_ms": round(samples[len(samples) // 2], 3),
        "p95_ms": round(samples[p95_index], 3),
        "max_ms": round(samples[-1], 3),
    }


def _cli_selftest_scenario() -> None:
    cmd = [
        "python",
        "-m",
        "exoneural_governor.cli",
        "--config",
        "configs/sg.config.json",
        "selftest",
    ]
    env = dict(os.environ)
    env.update(
        {
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
        }
    )
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"cli selftest failed rc={proc.returncode} stderr={proc.stderr.strip()}"
        )


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def generate_report() -> dict:
    scenarios = [
        _measure("backend.resolve_backend.reference", lambda: resolve_backend("reference")),
        _measure("network.validate_backend.reference", lambda: validate_backend("reference")),
        _measure("cli.selftest", _cli_selftest_scenario),
    ]

    report = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "release": os.environ.get("PERF_RELEASE", "dev"),
        "scenarios": sorted(scenarios, key=lambda item: str(item["name"])),
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    trend = _read_json(TREND_REPORT_PATH, default={"releases": []})
    releases = [r for r in trend.get("releases", []) if r.get("release") != report["release"]]
    releases.append({"release": report["release"], "scenarios": report["scenarios"]})
    trend_payload = {"releases": sorted(releases, key=lambda item: str(item["release"]))}
    TREND_REPORT_PATH.write_text(
        json.dumps(trend_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    print(json.dumps(generate_report(), indent=2, sort_keys=True))
