# 09 Branch Protection

## Required checks are check-run names

GitHub branch protection evaluates check-run names. Workflow names and job names combine into check-runs (commonly `Workflow / Job` in UI presentation).

## Deterministic discovery method (no guesswork)

For a PR head commit SHA:

1. Open PR → **Checks** tab and copy exact displayed names.
2. API method (recommended for automation):

```bash
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>/commits/<sha>/check-runs?per_page=100"
```

3. Parse `check_runs[].name` values and use exact names if manually configuring required checks.

## Recommended policy

Require only **`CI Supercheck`** in branch protection.

Rationale:
- Prevents deadlocks and path-filter mismatches.
- Enforces context-aware required checks inside one deterministic fail-closed gate.
- Keeps branch-protection configuration stable while workflows/jobs evolve.
