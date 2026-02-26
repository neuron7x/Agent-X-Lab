# PROTOCOL_13/DEGC — Deterministic External-Governed Convergence (Fail-Closed)

**Purpose:** Convert LLM-assisted work from open-ended conversation into a deterministic, externally verified engineering loop.  
**Truth source:** `TRUTH_PLANE` (CI/CD, logs, checks, reproducible outputs).  
**Termination authority:** `CONTROL_PLANE` (human governor only).  
**Default failure mode:** fail-closed — missing evidence, ambiguity, or contradiction ⇒ **HALT**.

## Topology (planes)

- **CONTROL_PLANE** — human governor (sole authority for termination and merge decisions)
- **DATA_PLANE** — executor agent (produces diffs, packets, scripts, and candidate state transitions)
- **TRUTH_PLANE** — external oracle (CI/CD, tests, build gates, security checks)

## Canonical convergence cycle

`FAIL → FIX → PROVE → CHECKPOINT`

Each `CHECKPOINT` is an auditable snapshot. The loop is restart-safe and designed to minimize entropy accumulation across iterations.

## STRICT_JSON packet contract (single packet, no top-level extras)

Required top-level keys:

- `FAIL_PACKET` (`object`) — externally observed failure evidence (logs, failed checks, reproduction hints)
- `MUTATION_PLAN` (`object`) — minimal diff plan, file targets, invariants, and constraints
- `PRE_VERIFICATION_SCRIPT` (`string`) — deterministic local verification script
- `REGRESSION_TEST_PAYLOAD` (`object`) — regression suite definition and expected outcomes
- `SHA256_ANCHOR` (`string`) — cryptographic audit anchor (64-char lowercase SHA-256, self-anchor over canonical packet payload excluding `SHA256_ANCHOR`)


### Nested fail-closed minimums (packet internals)

- `FAIL_PACKET` must include non-empty: `summary`, `signals[]`, `repro`
- `MUTATION_PLAN` must include non-empty arrays: `diff_scope[]`, `constraints[]`
- `REGRESSION_TEST_PAYLOAD` must include non-empty: `suite[]`, `expected`
- `SHA256_ANCHOR` must match the canonical self-anchor derived from the packet payload with `SHA256_ANCHOR` omitted

Canonicalization for self-anchor:
- JSON UTF-8
- sorted keys
- compact separators `(',', ':')`
- payload = top-level packet without `SHA256_ANCHOR`

## Fail-closed invariants

1. **No silent failures.** All error states must surface explicitly.
2. **No oracle → no truth.** CI/CD remains the only truth contour for PASS/FAIL.
3. **Missing evidence ⇒ HALT.**
4. **Anchor mismatch ⇒ HALT.** Packet hash drift is a hard failure.
5. **Minimal diffs.** No dependency additions unless explicitly allowed.
6. **Type integrity.** Do not weaken types or suppress checks.
7. **AXL-UI polling invariants.**
   - GitHub rate limit reached ⇒ state becomes `RATE_LIMITED`
   - polling stops until reset time
   - reset countdown is visible
   - indicator animation runs only in `POLLING`

## Reference tooling (offline)

- Build `SYSTEM_OBJECT.json` and print the system anchor:
  - `python -m udgs_core.cli build-system-object --root . --config system/udgs.config.json --out SYSTEM_OBJECT.json`
- Validate a STRICT_JSON packet:
  - `python -m udgs_core.cli validate-packet <packet.json>`
- Compute deterministic packet self-anchor (used for `SHA256_ANCHOR`):
  - `python -m udgs_core.cli packet-anchor <packet.json>`
- Compute anchors:
  - `python -m udgs_core.cli anchor <path>`
- Evaluate fail-closed loop gate:
  - `python -m udgs_core.cli loop --evidence-json <evidence.json>`
