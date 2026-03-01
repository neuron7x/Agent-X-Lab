# RIS System Object Spec

RIS (Repository Intelligence Stack) provides deterministic repository graph synthesis and contract evaluation.

## Interfaces
- `python -m exoneural_governor repo-model` generates `repo_model.json` and `architecture_contract.jsonl`.
- `python -m exoneural_governor contract-eval` generates hermetic evaluator bundle under `--out`.

## Determinism model
- Canonical JSON uses sorted keys and compact separators for hashing/comparisons.
- Centrality ordering uses deterministic tie-break by `(score desc, id asc)`.
- Semantic determinism compares fingerprints/counts/agent sets/edge multiset/core ranking + contract row count.

## Invariants
- Strict repo-model: zero `unknowns.dangling_edges` and zero `unknowns.parse_failures`.
- Contract rows are 1:1 with agents.
- Strict policy fails on policy-level violations.
- Strict-no-write forbids changes outside `--out`.

## Failure model
- Gate status: `PASS`, `WARNING`, `FAIL`.
- Strict mode escalates policy warnings to failures.
- Repository fingerprint drift fails strict mode.

## Artifact bundle format
- `report.json`: gate outcomes, warnings/failures.
- `env.json` + `env.sha256`: deterministic environment stamp.
- `commands.log` + `NNN_*.json`: executed command evidence and output hashes.
- `repo_model.run1.json`, `repo_model.run2.json`: determinism evidence.
- `hashes.json`: SHA-256 for all bundle files.
