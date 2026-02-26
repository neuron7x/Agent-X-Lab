# MULTI-AGENT VALIDATION
**Version:** v1.0.0 · **Status:** `ACTIVE` · **Author:** Yaroslav Vasylenko  
**Protocol:** IOPS-2026 · **Layer:** Architecture  
**Created:** 2026-02-20

---

## What This Is

A **mechanized validation architecture** for coordinating 5–20 agents (or role-states)
so that the final artifact is **evidence-bound, fail-closed, and reproducible**.

This document defines:
- Coordination patterns (topologies)
- Deterministic convergence rules
- Evidence requirements per phase
- Failure modes and hard-stops

---

## 1 · Core Principle: Evidence-Weighted Convergence

Convergence is not consensus. Convergence happens when:
1. The **Verifier** can reproduce the claimed outputs.
2. The **Auditor** finds no invariant violations.
3. The **Critic** cannot produce a stronger counterexample within bounded cycles.

If any step yields UNKNOWN ⇒ FAIL (IOPS INV-04).

---

## 2 · Standard Roles (extendable)

Baseline roles (see ADVERSARIAL-ORCHESTRATION):
- Creator (constructs artifact)
- Critic (attacks/weakness-finds)
- Auditor (policy + invariants)
- Verifier (reproducibility + proofs)

Additional roles (optional):
- Integrator: stitches modules, normalizes interfaces, reduces duplication
- Red-Teamer: prompt injection + security adversary
- Benchmarker: runs baselines and measures deltas
- Librarian: maintains SSOT and manifests
- Release Engineer: packaging, tags, compatibility, rollback

---

## 3 · Coordination Topologies

### 3.1 Single-stream (4 roles)
Creator → Critic → Auditor → Verifier
- Use when artifact scope is small and contracts are stable.

### 3.2 Two-stream (spec + implementation)
Spec Stream: Creator/ Critic/ Auditor/ Verifier operate on spec documents.  
Impl Stream: Builder/ Tester/ Security/ Verifier operate on code and CI.

Outputs merge only when both streams pass their gates.

### 3.3 Star (Integrator hub)
Multiple specialized agents produce modules; Integrator merges into SSOT.
Verifier independently replays the integrated result.

Use when you have many objects or heterogeneous stacks.

### 3.4 Tournament (N critics)
1 Creator produces candidate.
N Critics produce disjoint attack sets.
Auditor consolidates findings.
Creator patches.
Verifier replays.

Use when injection risk is high or correctness stakes are high.

---

## 4 · Deterministic Iteration Protocol

Hard limits:
- Max cycles: 5 (default)
- Max blockers per cycle: 20
- Max unresolved UNKNOWN: 0

Cycle:
1. Creator outputs artifact + proof plan.
2. Critics output counterexamples (each must include a minimal reproducer).
3. Auditor outputs gate matrix with PASS/FAIL and citations to repro steps.
4. Creator applies minimal diffs.
5. Verifier runs repro; emits proof bundle index.

Stop conditions:
- PASS: all gates PASS and Verifier reproduces evidence.
- FAIL: any invariant violation or any unresolved UNKNOWN after cycle 5.

---

## 5 · Evidence Requirements (mechanized)

Every claim must map to:
- command (exact)
- environment (OS, Python, tool versions)
- key output excerpt
- artifact path
- sha256 checksum

Recommended evidence bundle structure:
`artifacts/evidence/<date>/<run-id>/(ENV.txt|COMMANDS.txt|OUTPUTS/|REPORTS/|MANIFEST.json)`

---

## 6 · Common Failure Modes and Fixes

- **False confidence**: Verifier does not replay commands → fix: forbid unverifiable claims.
- **Scope creep**: Creator expands objectives → fix: Integrator enforces “one PR one objective”.
- **Gate dilution**: “temporary” disables become permanent → fix: Auditor blocks merges without explicit justification and rollback.
- **Consensus drift**: roles disagree on SSOT → fix: Librarian maintains a single manifest and checksums.

---

## 7 · Minimal Implementation Guidance

For repositories, implement:
- `scripts/validate_arsenal.py` (schema + checksums)
- per-object `eval/run_harness.py` (DG gates)
- CI workflow that runs validation and eval on every PR

