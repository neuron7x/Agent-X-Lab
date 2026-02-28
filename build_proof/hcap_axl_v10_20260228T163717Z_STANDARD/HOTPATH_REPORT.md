# HOTPATH_REPORT

Mode: STANDARD

## Measured profile summary

- Evidence hash (pytest durations): `7f217d7dbbb6c83dffabe20080f61dc7b0b2efdd6ad5a91779d7fe3647faf94a`

- 76.25s call     engine/tests/test_vr_provenance_id.py::test_no_git_with_distinct_build_ids_are_unique
- 9.28s call     udgs_core/tests/test_udgs_core.py::TestCLI::test_qa8_heal_nominal
- 6.47s call     udgs_core/tests/test_udgs_core.py::TestCLI::test_build_system_object_deterministic
- 3.25s call     udgs_core/tests/test_udgs_core.py::TestCLI::test_build_system_object
- 1.59s call     engine/tests/test_repo_invariants.py::test_sg_vr_accepts_config_after_subcommand
- 1.25s call     engine/tests/test_stack.py::test_vr_and_release
- 0.84s call     engine/tests/test_readme_contract.py::test_generate_titan9_proof_bundle
- 0.66s call     engine/tests/test_nongit_runner.py::test_nongit_runner_executes_pytest_command
- 0.57s call     engine/tests/test_doctor.py::test_doctor_passes_in_ci_env
- 0.48s call     engine/tests/test_witness.py::test_witness_writes_report_and_signature
- 0.46s call     engine/tests/test_repo_invariants.py::test_validate_arsenal_strict_passes
- 0.42s call     engine/tests/test_repo_invariants.py::test_sg_release_accepts_config_after_subcommand
- 0.35s call     engine/tests/test_repo_invariants.py::test_object_eval_harnesses_pass
- 0.33s call     engine/tests/test_readme_contract.py::test_readme_contract_fails_when_quickstart_not_make_only_stable
- 0.32s call     engine/tests/test_repo_invariants.py::test_sg_config_selftest_passes
- 0.31s call     engine/tests/test_run_gate.py::test_run_gate_default_evidence_path_stable_across_cwds
- 0.28s call     engine/tests/test_repo_invariants.py::test_schema_validate_passes
- 0.26s call     engine/tests/test_readme_contract.py::test_readme_contract_passes
- 0.24s call     engine/tests/test_rebuild_catalog_index.py::test_rebuild_catalog_index_preserves_generated_utc
- 0.20s call     engine/tests/test_workflow_guards.py::test_verify_workflow_hygiene_autodetects_repo_root_from_subdir

## Hotpath-backed optimization candidates

- DAG size: nodes=291 edges=1466 (hash `1dfd296c6aefb8a46aa23741d17fc79025fe0d52aa53d173ec8953af2062582b`).
- Candidate: cache expensive provenance-id setup used by `engine/tests/test_vr_provenance_id.py::test_no_git_with_distinct_build_ids_are_unique`.
- Candidate: split CLI integration-heavy tests into smoke+deep markers to keep deterministic quick gate under 60s.
- Candidate: for high-CC functions in `outputs/entropy_metrics.json`, extract pure validators and benchmark before/after.

## Mode gates

- STANDARD mode profiling executed with pytest durations.

## Memory/coalescing

Triggered by dependency/content markers in `outputs/memory_mode.txt`.
- Introduce preallocation and batch transforms in tensor-adjacent paths.
- Replace repeated append-based list growth with bounded comprehensions/generators in hot loops.
- Add microbench harness with fixed-seed inputs and hash-stable outputs.
