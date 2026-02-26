# AXL Unified One-Project Workspace — QA8

This workspace packages **AXL-UI** (repository root) together with the **Agent-X-Lab Engine** (`engine/`) in a single auditable integration artifact.

The UI remains a monochrome, instrument-style control surface. It does **not** import engine code directly. Instead, it reads engine state through the GitHub API at runtime (for example `VR.json` and `artifacts/agent/*`). This preserves a clean boundary between presentation and execution logic.

## Grade: QA8_AUTONOMOUS_AUDIT_SELF_HEALING

The system has been promoted from QA7 (statically hardened anchors) to QA8 (continuously self-healing).

In QA8 mode the system:
- Runs a continuous watch daemon that scans component hashes against the QA7 baseline on a configurable interval.
- Detects any drift in the SHA-256 tree hash of each tracked component.
- Automatically regenerates `SYSTEM_OBJECT.json` when it diverges from the source tree (HEALED).
- Emits a STRICT_JSON FAIL_PACKET and enters ALERT mode when source-level drift is detected.
- Transitions to HALT (fail-closed) when the PROVE gate of the deterministic cycle cannot be satisfied.

## QA8 Upgrade Rule

> Any change that weakens the fail-closed contract, removes drift detection, or bypasses the PROVE gate requires explicit review and a new iteration checkpoint.

## Layout

- `/` — **AXL-UI** (interface source of truth)
- `engine/` — **Agent-X-Lab Engine** (contracts, artifacts, `VR.json`, docs, `Makefile`, `pyproject.toml`)
- `releases/` — frozen UI snapshots (`v1.0`, `v1.2`, `v1.3`)
- `qa8_state/` — live QA8 status, heal event log, QA7 baseline snapshot

## UI quick commands (run from repository root)

```bash
npm ci --no-audit --no-fund
npm run test
npm run build
```

## Engine quick commands

```bash
cd engine
# Follow engine README/Makefile. Typical patterns:
# python -m pip install -e .
# make <target>
```

## Integration rule (hard boundary)

- UI code must not import from `engine/`.
- Engine artifacts are consumed as runtime data through GitHub API reads.
- Any change that weakens this boundary requires explicit review and proof.
