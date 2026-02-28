# TASK_REGISTER

Mode: STANDARD

| Pri | ID | Goal | Files | Minimal change size | Done criteria | Risk | Impact (0-100) | Proof command |
|---|---|---|---|---|---|---|---:|---|
| P0 | T-001 | Fix missing local action description metadata | `.github/actions/pin-pip/action.yml` | 1-3 LOC | `python - <<PY (workflow blocker scan)` no `action_missing_description` | Low | 82 | `python tools/verify_workflow_hygiene.py --workflows .github/workflows` |
| P0 | T-002 | Refactor SC2129 append block in python-verify workflow | `.github/workflows/python-verify.yml` | 6-12 LOC | `workflow_blockers.json` no sc2129 for python-verify | Low | 76 | `python - <<PY (workflow blocker scan)` |
| P0 | T-003 | Refactor SC2129 append block in engine-drift-guard workflow | `.github/workflows/engine-drift-guard.yml` | 8-15 LOC | `workflow_blockers.json` no sc2129 for engine-drift-guard | Low | 74 | `python - <<PY (workflow blocker scan)` |
| P0 | T-004 | Harden determinism around datetime.now callsites | `engine/exoneural_governor/util.py` | 10-20 LOC | two-run hash stable for outputs using injected clock | Medium | 84 | `python -m pytest -q engine/tests -k time` |
| P0 | T-005 | Constrain secret scanner output path to artifact root | `engine/tools/secret_scan_gate.py` | 8-20 LOC | `--out /tmp/x` fails closed, default path passes | Low | 79 | `python -m pytest -q engine/tests/test_secret_scan_gate.py` |
| P1 | T-006 | Add unit tests for action pinning edge cases | `engine/tests/test_verify_action_pinning.py` | 40-80 LOC | new tests pass and cover invalid refs | Low | 68 | `python -m pytest -q engine/tests -k action_pinning` |
| P1 | T-007 | Add deterministic workflow blocker checker to CI | `.github/workflows/workflow-hygiene.yml, tools/*` | 20-50 LOC | checker output artifact uploaded and gate required | Medium | 70 | `python - <<PY (workflow blocker scan)` |
| P1 | T-008 | Codify invariant manifest JSON for machine checks | `tools/ci + build_proof templates` | 40-90 LOC | manifest validates >=20 invariants | Medium | 64 | `python -m pytest -q engine/tests -k invariant` |
| P2 | T-009 | Refactor highest complexity function validate_packet | `udgs_core/strict_json.py` | 40-120 LOC | complexity reduced >=20% with behavior parity tests | Medium | 72 | `python -m pytest -q udgs_core/tests/test_udgs_core.py -k validate_packet` |
| P2 | T-010 | Refactor workflow hygiene main into pure helpers | `engine/tools/verify_workflow_hygiene.py` | 30-80 LOC | same CLI output + lower complexity | Low | 60 | `python tools/verify_workflow_hygiene.py --workflows .github/workflows` |
| P2 | T-011 | Refactor validate_arsenal main control flow | `engine/scripts/validate_arsenal.py` | 40-120 LOC | no output diff on sample inputs | Medium | 58 | `python engine/scripts/validate_arsenal.py --help` |
| P2 | T-012 | Split release build orchestration function | `engine/exoneural_governor/release.py` | 40-100 LOC | unit tests green and complexity down | Medium | 56 | `python -m pytest -q engine/tests -k release` |
| P2 | T-013 | Reduce nested regex scanning overhead | `engine/tools/secret_scan_gate.py` | 20-50 LOC | benchmark <=70% current CPU for same corpus | Low | 54 | `python -m pytest -q engine/tests/test_secret_scan_gate.py` |
| P2 | T-014 | Reduce pyproject parsing churn in tooling scripts | `tools/prod_spec/*.py` | 20-60 LOC | same artifact hashes for deterministic inputs | Medium | 52 | `python tools/prod_spec/generate_formal_artifacts.py --help` |
| P2 | T-015 | Add complexity budget gate for top-20 functions | `tools/ci/complexity_gate.py` | .github/workflows/*.yml | 40-90 LOC | CI fails if threshold exceeded | Medium | `63` |
| P2 | T-016 | Normalize unused import cleanup across hotspots | `engine/**,udgs_core/**` | 30-120 LOC | ruff F401 count reduced with no behavior change | Low | 50 | `ruff check --select F .` |
| P3 | T-017 | Generate SVG from ARCH_DAG.dot in docs pipeline | `docs/**,tools/**` | 20-40 LOC | deterministic graph render artifact present | Low | 35 | `dot -Tsvg build_proof/.../ARCH_DAG.dot` |
| P3 | T-018 | Add mode matrix runner wrapper for FAST/STANDARD/DEEP | `scripts/hcap_runner.sh` | 40-80 LOC | three modes produce distinct evidence dirs | Low | 40 | `bash scripts/hcap_runner.sh --mode FAST` |
