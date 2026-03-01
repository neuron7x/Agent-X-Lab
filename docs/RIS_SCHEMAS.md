# RIS Schemas

## repo_model.json (high level)
- `repo_root: string`
- `repo_fingerprint: string`
- `agents: Agent[]`
- `edges: Edge[]`
- `core_candidates: CoreCandidate[]`
- `counts: {agents_count:int, edges_count:int, core_candidates_count:int}`
- `unknowns: object`

## architecture_contract.jsonl row
- `agent_id, path, kind, subkind, name`
- `inputs[], outputs[]`
- `invocation_examples[]`
- `depends_on_paths[]`
- `provides[]`
- `subdomain_tags[]`
- `core_rank`
- `blame{top_author,top_share,authors_topN[]}`

## contract-eval report.json
- `state: PASS|FAIL|ERROR`
- `exit_code: int`
- `gates[]: {id,status,details}`
- `failures[]`
- `warnings[]`
- `artifacts{dir,files[]}`

## env.json
- `versions{python,pip,node,npm,git,...}`
- `strict: bool`
- `no_write: bool`
- `repo_root: string`
