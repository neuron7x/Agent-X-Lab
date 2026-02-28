# INVARIANT_MAP

## Determinism hazards

| Site | Hazard type | Minimal fix | Proof command |
|---|---|---|---|
| `engine/exoneural_governor/util.py:16` | Wall-clock dependency (`datetime.now`) | Thread optional `clock` callable through callsites; default UTC clock for runtime, fixed clock in tests. | `python - <<'PY' ... ast scan ... PY` (see `outputs/determinism_findings.json`) |
| `engine/tools/agent/run_and_log.py:97` | Wall-clock event timestamp | Allow `--ts-override` for replay mode; keep default for live mode. | same as above |
| `engine/tools/agent/run_and_log.py:61,82` | Monotonic duration varies run-to-run | Persist duration as integer ms bucket or gate comparisons with tolerance in consuming checks. | same as above |
| `engine/tools/secret_scan_gate.py:87-94` | Writes output path from CLI without root restriction | Enforce output under `artifacts/security/**` and reject external paths. | same as above |
| `engine/exoneural_governor/util.py:72-73` | File writes are side effects outside explicit artifact policy | Add explicit `artifact_root` parameter and path prefix assertion before writes. | same as above |
| `udgs_core/tests/test_udgs_core.py:20-22` | Path mutation from cwd-sensitive root inference | Replace with `Path(__file__).resolve()`-based absolute package root and no `sys.path` mutation in library tests. | same as above |

## Invariant table

| # | Invariant | Enforced where | Missing / gap | Minimal enforcement change + proof |
|---|---|---|---|---|
| 1 | Workflow actions must be SHA pinned | `engine/tools/verify_action_pinning.py` lines 50-57, 115-131 | No direct unit test for parser edge cases | Add tests for local/docker and invalid refs; prove with `python -m pytest -q engine/tests -k action_pinning`. |
| 2 | Workflow YAML must parse or fail closed | `engine/tools/verify_action_pinning.py` lines 103-123 | Parse errors not surfaced with file context in CI artifact | Save parse_errors JSON artifact on failure. |
| 3 | All workflows require `permissions` | `engine/tools/verify_workflow_hygiene.py` line 67 | No check for least-privilege values | Enforce denylist (`write-all`) in hygiene tool. |
| 4 | All workflows require `concurrency` | `engine/tools/verify_workflow_hygiene.py` line 69 | Does not validate deterministic key template | Require group contains `${{ github.ref }}` or `${{ github.sha }}`. |
| 5 | All jobs must have timeout | `engine/tools/verify_workflow_hygiene.py` lines 76-77 | No max timeout cap | Add cap (<=30 min) to bound hangs. |
| 6 | `pin-pip` action requires `PIP_VERSION` | `engine/tools/verify_workflow_hygiene.py` lines 83-91 | No semver format check | Validate strict `x.y.z` pattern. |
| 7 | Python verify must fail if no test contract | `.github/workflows/python-verify.yml` lines 33-51 | Drift risk if new package layout appears | Add explicit branch for monorepo package manifests. |
| 8 | Python verify must compile source before tests | `.github/workflows/python-verify.yml` lines 52-55 | compileall not run with deterministic env vars | Set `PYTHONHASHSEED=0 LC_ALL=C TZ=UTC` in job env. |
| 9 | Tests must exist or fail closed | `.github/workflows/python-verify.yml` lines 57-61 | file discovery uses `find` shell semantics only | Mirror rule in Python helper for portability. |
| 10 | Strict packet schema rejects extra keys | `udgs_core/strict_json.py` lines 96-100 | No schema snapshot test in CI | Add golden packet fixtures + snapshot check. |
| 11 | Packet anchor must match canonical hash | `udgs_core/strict_json.py` lines 134-143 | No fuzz tests for nested ordering permutations | Add property test for ordering invariance. |
| 12 | PROVE state requires logs and anchor (fail-closed) | `udgs_core/state_machine.py` lines 59-70 | Oracle tri-state (`None`) implicitly passes | Require explicit `oracle_pass is True` in strict mode. |
| 13 | HALT must be absorbing | `udgs_core/state_machine.py` lines 78-79 + tests | None identified | Keep existing tests; add mutation test to ensure no transition leakage. |
| 14 | Secret scan must fail when findings exist | `engine/tools/secret_scan_gate.py` lines 96-101 | Excludes only `tests/` and `artifacts/`; missing allowlist semantics | Add path/rule allowlist with expiry metadata. |

