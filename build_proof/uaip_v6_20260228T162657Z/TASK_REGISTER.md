# TASK_REGISTER

## P0 (correctness / determinism / CI blockers)

### P0-1 Enforce deterministic runtime envelope in Python CI
- Goal: ensure compile/test steps run under fixed hash/locale/timezone.
- Minimal change set: `.github/workflows/python-verify.yml`.
- Done criteria + proof:
  - `python tools/verify_workflow_hygiene.py --workflows .github/workflows` passes.
  - `python -m pytest -q udgs_core/tests --durations=20` remains green.
- Risk: low (env var additions only).

### P0-2 Remove repeated `set(deficit_ids)` construction
- Goal: eliminate algorithmic blowup in protocol consistency verification.
- Minimal change set: `engine/tools/verify_protocol_consistency.py`.
- Done criteria + proof:
  - Run tool on representative protocol file; output unchanged.
  - Benchmark shows lower runtime (`outputs/profile/algorithmic_microbench.txt`).
- Risk: low (semantics-preserving refactor).

### P0-3 Restrict secret scan output path to artifact root
- Goal: prevent unintended writes outside repository artifact policy.
- Minimal change set: `engine/tools/secret_scan_gate.py`.
- Done criteria + proof:
  - command with `--out /tmp/x` fails closed.
  - default output path still succeeds.
- Risk: low-medium (could break custom consumers relying on external path).

## P1 (architecture boundaries/contracts)

### P1-1 Add invariant tests for action pinning parser
- Goal: lock parser behavior for `uses:` edge cases.
- Minimal change set: `engine/tests/test_verify_action_pinning.py` (new).
- Done criteria + proof: targeted pytest subset passes.
- Risk: low.

### P1-2 Harden workflow hygiene constraints
- Goal: enforce deterministic concurrency key and timeout max cap.
- Minimal change set: `engine/tools/verify_workflow_hygiene.py`, tests.
- Done criteria + proof: tool fails on synthetic violating workflow fixtures.
- Risk: medium (may require workflow updates).

### P1-3 Explicit oracle truth requirement in strict mode
- Goal: make PROVE gate require positive oracle when field is present.
- Minimal change set: `udgs_core/state_machine.py`, `udgs_core/tests/test_udgs_core.py`.
- Done criteria + proof: tests updated and passing.
- Risk: medium (behavioral tightening).

## P2 (optimization / entropy reduction)

### P2-1 Split `udgs_core.strict_json.validate_packet` into composable validators
- Goal: reduce cyclomatic complexity hotspot (43).
- Minimal change set: `udgs_core/strict_json.py`, tests.
- Done criteria + proof: complexity metric reduced; tests unchanged.
- Risk: medium.

### P2-2 Refactor `engine/scripts/validate_arsenal.py::main`
- Goal: reduce complexity (39) and improve readability.
- Minimal change set: `engine/scripts/validate_arsenal.py`.
- Done criteria + proof: tool output and exit codes unchanged.
- Risk: medium.

### P2-3 Refactor `engine/tools/verify_workflow_hygiene.py::main`
- Goal: complexity reduction (27) via extraction.
- Minimal change set: `engine/tools/verify_workflow_hygiene.py`, tests.
- Done criteria + proof: policy tool output unchanged.
- Risk: low.

### P2-4 Optimize secret scan pattern matching
- Goal: reduce scan runtime with union regex / early exits.
- Minimal change set: `engine/tools/secret_scan_gate.py`.
- Done criteria + proof: benchmark improvement and exact finding parity.
- Risk: low.

### P2-5 Add complexity budget check in CI
- Goal: block future entropy growth on top 20 functions.
- Minimal change set: new `tools/ci/complexity_gate.py`, workflow invocation.
- Done criteria + proof: CI fails when threshold exceeded.
- Risk: medium.
