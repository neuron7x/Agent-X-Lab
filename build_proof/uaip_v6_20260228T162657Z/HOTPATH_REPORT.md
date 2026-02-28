# HOTPATH_REPORT

## Measurement sources
- `outputs/profile/pytest_udgs_core.txt` (test durations)
- `outputs/profile/cprofile_compileall.txt` (CPU cumulative frames)
- `outputs/profile/algorithmic_microbench.txt` (complexity micro-bench)

## Measured hot paths
1. `TestCLI::test_qa8_heal_nominal` = 9.09s.
2. `TestCLI::test_build_system_object_deterministic` = 6.57s.
3. `TestCLI::test_build_system_object` = 3.40s.
4. Compile walk spends most cumulative time in `compileall.compile_dir/compile_file` with filesystem stats dominating (`posix.stat`).

## Algorithmic pruning candidates

### Candidate A: repeated set construction in protocol consistency
- Site: `engine/tools/verify_protocol_consistency.py:37` currently computes `d not in set(deficit_ids)` inside comprehension.
- Complexity claim: current path is effectively O(|seen| * |deficit_ids|) due to repeated set creation; replacement is O(|seen|) using a precomputed set.
- Micro-benchmark evidence (`outputs/profile/algorithmic_microbench.txt`):
  - current: `14.583156s`
  - proposed: `0.003181s`
  - equality: `True`
- Correctness invariant: `unknown_deficits` contents unchanged for identical `deficit_ids` and `seen`.

### Candidate B: regex scan loop in secret scanning
- Site: `engine/tools/secret_scan_gate.py:57-60` loops line-by-line and pattern-by-pattern.
- Complexity claim: current is O(lines * patterns); replacement with a compiled union regex reduces constant factors and branch overhead while preserving detection semantics.
- Micro-benchmark evidence:
  - current: `0.041144s`
  - proposed: `0.007702s`
- Correctness invariant: each line flagged by any old pattern must be flagged by union regex.

### Candidate C: nested loop over action preconditions
- Site: `tools/prod_spec/generate_formal_artifacts.py:149-153` nested loops over actions and conditions.
- Complexity claim: O(total preconditions + postconditions), acceptable now; optimize only if action count grows (>10^5 conditions).
- Proposed optimization: keep as-is; add guardrail benchmark in CI to detect growth regression.

## Memory/coalescing
NOT_APPLICABLE for heavy numeric pipelines. Repo scan did not detect `torch`, `tensorflow`, `jax`, `triton`, `cupy`, or CUDA kernel sources in analyzed Python modules (`outputs/tensor_kernel_mode.txt`).
