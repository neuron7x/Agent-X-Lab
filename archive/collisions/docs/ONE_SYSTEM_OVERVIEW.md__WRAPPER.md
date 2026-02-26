# AXL One System — Product/System Design Overview

## Goal
Unify **code + artifacts + release evidence + control-plane policy** into one coherent system **without mutating** or “breaking” any existing module.

## What this pack gives you
- **Full repo** preserved as-is (dev & implementation reality)
- **Promoted release evidence** preserved as-is (what passed gate-check)
- **Final minimal build** preserved as-is (deployable dist)
- **Control Plane lock** (hash-bound pointers to canonical CP inputs)
- **Integration map** (explicit composition, no implicit coupling)

## How to operate
### 1) Treat Control Plane as authority
- `cp/AXL_CP_LOCK.json` binds the canonical CP inputs by SHA256.
- `cp/AXL_INTEGRATION_MAP.yaml` is the integration “wiring diagram”.

### 2) Evidence-first release verification
From the promoted bundle:
- `release/promoted_bundle_2026-02-26/artifacts/` contains gate evidence.
- `release/promoted_bundle_2026-02-26/engine/scripts/check_prod_spec_gates.py` is the verifier.

### 3) Build & deploy paths
- **Build from source**: `workspace/full_repo/axl_qa8/` (React/Vite)
- **Deploy dist**: `workspace/axl_final/axl_final/dist/` (or `workspace/full_repo/axl_qa8/dist/`)

## Non-breaking integration rules (hard)
- Never overwrite any snapshot.
- New integration logic lives only in `cp/` + `docs/`.
- Any future “unification” should be implemented as **adapters** + **schemas**, not rewrites.

## Next hardening (recommended)
- Add JSON Schemas for every gate artifact in CP.
- Make the gate checker execute policy from `gate_assertions.yaml` instead of duplicating logic.
- Enforce crypto verification for G6 (existence != validity).
