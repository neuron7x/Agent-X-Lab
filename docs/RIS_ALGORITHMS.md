# RIS Algorithms

## Discovery
1. Gather candidate paths from workflows/actions/Makefile/scripts/tools/engine surfaces/docs.
2. Apply include/exclude glob policy.
3. Classify kind and derive stable `agent_id=sha12(path)`.

## Edge extraction
- Workflow `uses`/`run` and Makefile command extraction.
- Python import graph: AST `Import`/`ImportFrom` mapped to local files.
- JS import graph: regex for `import ... from`, `require`, `export ... from` local specs.
- Include graph: C/C++ include, Makefile include, shell `source`.

## Centrality
- Compute PageRank and Brandes betweenness on directed wiring graph.
- Core score: `0.6*pr_norm + 0.4*bc_norm`.
- Stable rank sorting with deterministic tie-breaks.

## Contract extraction
- Reconstruct names from YAML `name`, doc headers, comments, stem fallback.
- Extract interfaces from argparse/click/yargs/getopts/workflow inputs.
- Collect invocation examples by static scan for path/module references.

## Blame aggregation
- `git blame --line-porcelain` per path.
- Optional ignore revisions via `.git-blame-ignore-revs`.
- Compute top author share and top-N distribution.

## Evaluator gates
- Hermetic runtime stamps tool versions.
- Strict-no-write compares before/after git snapshots.
- Determinism compares canonical semantic signatures across two runs.
- Fingerprint guard checks start/end stability.
