# TENSOR_KERNEL_SPEC

Trigger evidence:
- `outputs/tensor_kernel_mode.txt` includes marker hits in repository content (notably `engine/exoneural_governor/network.py`).

## Determinism requirements
1. Set deterministic seeds in all torch/jax/tf entrypoints before model execution.
2. For PyTorch, enforce deterministic algorithms (`torch.use_deterministic_algorithms(True)`) where available.
3. Ban nondeterministic atomic reductions in production paths unless explicitly justified and tested.
4. Require fixed random seeds in tests and benchmark harnesses.

## dtype/layout/stride contracts
1. Explicitly assert input dtypes at model boundaries.
2. Normalize memory layout (`contiguous`) before kernel-sensitive operations.
3. Reject implicit up/down-casts in hot path without profiler evidence.

## Kernel guardrails
1. No dynamic-shape kernel dispatch without shape guards and fallback paths.
2. No silent fallback from compiled kernels to eager mode without logging.
3. Introduce kernel-selection test matrix for representative tensor shapes.

## Profiling plan (local tools only)
1. If `torch.profiler` available: capture deterministic trace on fixed seed + fixed input set.
2. If CUDA tools available locally: run `nsys profile` against bounded benchmark harness.
3. Save trace hashes and compare across runs for drift detection.
