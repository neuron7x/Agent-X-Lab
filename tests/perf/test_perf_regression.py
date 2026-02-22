from __future__ import annotations

from .run_perf_scenarios import generate_report

P95_LATENCY_THRESHOLDS_MS = {
    "backend.resolve_backend.reference": 5.0,
    "network.validate_backend.reference": 5.0,
    "cli.selftest": 2500.0,
}


def test_perf_regression_thresholds() -> None:
    report = generate_report()
    scenarios = {item["name"]: item for item in report["scenarios"]}

    for scenario_name, threshold_ms in sorted(P95_LATENCY_THRESHOLDS_MS.items()):
        assert scenario_name in scenarios
        assert float(scenarios[scenario_name]["p95_ms"]) <= threshold_ms
