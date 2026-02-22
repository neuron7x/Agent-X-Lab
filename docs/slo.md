# Production SLO / KPI thresholds

All thresholds are deterministic guardrails for the `exoneural_governor` critical path.

## Latency SLO (p95)

- `backend.resolve_backend("reference")`: **<= 5 ms**
- `network.validate_backend("reference")`: **<= 5 ms**
- `sg --config configs/sg.config.json selftest`: **<= 2500 ms**

## Error-rate SLO

- Critical-path scenarios above: **0% unexpected failures** in regression runs.
- Expected fail-closed paths (malformed command, timeout propagation, dependency failure propagation): **100% deterministic failure behavior**.

## Throughput KPI

- CLI self-test scenario minimum throughput: **>= 0.4 runs/sec** (equivalent to p95 <= 2500 ms).

## Evidence and artifact locations

- Current run: `artifacts/reports/perf/latest.json`
- Release trend: `artifacts/reports/perf/trend.json`

## Enforcement

- Local regression gate: `pytest -q tests/perf/test_perf_regression.py`
- CI regression gate (scheduled/manual): `.github/workflows/perf-regression.yml`
