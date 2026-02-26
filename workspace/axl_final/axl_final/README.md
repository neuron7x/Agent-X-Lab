# AXL + UDGS Unified Product (Single System Object) — QA8

This package is a **single synchronized workspace** that combines runtime UI behavior, execution tooling, and deterministic governance into one auditable system object.

## What is included

1. **AXL-UI** (`/`) — the runtime interface that reads project state through the GitHub API.
2. **AXL Engine** (`engine/`) — the exoneural governor, contracts, artifacts, and validation assets.
3. **DAO-Arbiter SDK** (`tools/dao-arbiter/`) — a deterministic loop engine and related research assets.
4. **E-legacy snapshot** (`sources/legacy/E-legacy_snapshot/`) — preserved for audit parity only (not an active SSOT).
5. **UDGS Core** (`udgs_core/`) — a stdlib-only integration layer for deterministic anchors, strict packet validation, system-object generation, and **QA8 autonomous self-healing**.

## Grade

`QA8_AUTONOMOUS_AUDIT_SELF_HEALING` — promoted from `QA7_STRICT_ANCHOR_HARDENED` (2026.02.23).

The system is no longer only statically anchored.  It actively monitors its own component hashes, detects deviations, and auto-restores generated artifacts within one heal cycle.

## Primary use case

Use this workspace when you need to:

- validate changes against a fail-closed protocol,
- build a deterministic `SYSTEM_OBJECT.json`,
- keep a cryptographic audit trail for integration steps,
- preserve a single source of truth across UI + engine + embedded SDKs,
- **run autonomous continuous audit with self-healing** (QA8 mode).

## Quick audit commands

```bash
# Build SYSTEM_OBJECT.json and print the deterministic system anchor.
python -m udgs_core.cli build-system-object --root . --config system/udgs.config.json --out SYSTEM_OBJECT.json

# Validate a STRICT_JSON packet (fail-closed contract).
python -m udgs_core.cli validate-packet system/examples/packet.example.json

# Derive the deterministic self-anchor used by SHA256_ANCHOR.
python -m udgs_core.cli packet-anchor system/examples/packet.example.json

# Compute a deterministic SHA-256 anchor for any file or directory.
python -m udgs_core.cli anchor engine
```

## QA8 autonomous audit commands

```bash
# Run one scan+heal cycle and print QA8_STATUS.json.
python -m udgs_core.cli qa8-heal --root .

# Start continuous watch daemon (default: 30-second interval).
python -m udgs_core.cli qa8-watch --root . --interval 30

# Print current live QA8 status.
python -m udgs_core.cli qa8-status --root .
```

### QA8 Modes

| Mode | Meaning |
|------|---------|
| `NOMINAL` | All component hashes match QA7 baseline. |
| `SCANNING` | Scan cycle in progress. |
| `DRIFT` | Hash deviation detected, heal pending. |
| `HEALING` | Deterministic FAIL→FIX→PROVE→CHECKPOINT cycle running. |
| `HEALED` | Generated artifact restored; anchors reconciled. |
| `ALERT` | Source-level drift; auto-heal not possible; FAIL_PACKET emitted. |
| `HALT` | Fail-closed gate triggered; manual intervention required. |

## Workspace layout (high level)

- `/` — AXL-UI
- `engine/` — AXL Engine
- `system/` — PROTOCOL_13/DEGC, unified config, and `qa8.config.json`
- `udgs_core/` — system-object builder, strict packet validator, deterministic loop gate, **autonomous_audit (QA8)**
- `tools/` — embedded SDKs (DAO-Arbiter active, E-legacy snapshot archived under `sources/legacy/`)
- `sources/` — original input ZIP files for audit and reproducibility
- `build_proof/` — local verification scripts, static checks, and proof summaries
- `qa8_state/` — live QA8 status, heal log, QA7 baseline snapshot *(excluded from component hashes)*

## Language quality refinement

This build includes a documented **8-cycle language-quality refinement pass** over user-facing and operator-facing text surfaces (docs, protocol wording, scripts, and UI localization strings). See `build_proof/LANGUAGE_QUALITY_REPORT.md`.
