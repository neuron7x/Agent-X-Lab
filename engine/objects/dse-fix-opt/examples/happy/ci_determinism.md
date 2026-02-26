# Happy-path example — CI determinism fix (illustrative)

## Input (user → agent)
Goal: Pin Python toolchain deterministically; eliminate pip drift; keep minimal diffs.

Repo facts:
- Python 3.12 in CI
- `pip install -U pip` used without pin
- No evidence bundle directory

## Expected output shape (agent → user)
- INVENTORY_JSON: includes CI workflows, python version, current pip state, unknowns
- PR_PLAN: PR1 pins pip and adds proof bundle logging
- PR1_PATCH: updates workflow YAML to:
  - define `PIP_VERSION` once
  - install `pip==<pinned>`
  - log `python -m pip --version` immediately after pin
- PROOF_BUNDLE_INDEX: paths + sha256 for:
  - ENV.txt
  - workflow run logs or captured command outputs
- MERGE_VERDICT: YES (if all gates pass) else NO with <=5 blockers
