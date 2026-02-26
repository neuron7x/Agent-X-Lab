# ADVERSARIAL ORCHESTRATION
**Version:** v1.0.0 · **Status:** `ACTIVE` · **Author:** Yaroslav Vasylenko
**Protocol:** IOPS-2026 · **Layer:** Architecture

---

## What This Is

A **production methodology** for generating high-quality, verified cognitive artifacts
by coordinating multiple AI agents (or role-states) in an adversarial pipeline.

The core insight: **quality emerges from structured disagreement**, not consensus.
A Creator that is never challenged produces unchecked artifacts.
A Critic with no Creator produces nothing.
A Verifier with no Auditor produces false confidence.

All four roles are necessary. The pipeline is the system.

---

## 1 · Role Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  ADVERSARIAL ORCHESTRATION PIPELINE             │
│                                                                 │
│   INPUT                                                         │
│   (objective + constraints + context)                           │
│         │                                                       │
│         ▼                                                       │
│   ┌──────────┐                                                  │
│   │ CREATOR  │  Role: Generate candidate artifact               │
│   │          │  Bias: Completeness, coverage                    │
│   │ temp=0.7 │  Output: Draft IO-BUNDLE or system artifact      │
│   └────┬─────┘                                                  │
│        │ candidate                                              │
│        ▼                                                        │
│   ┌──────────┐                                                  │
│   │  CRITIC  │  Role: Find structural failures                  │
│   │          │  Bias: Adversarial; assume artifact is wrong     │
│   │ temp=0.3 │  Output: Defect registry (class + severity)      │
│   └────┬─────┘                                                  │
│        │ defect registry                                        │
│        ▼                                                        │
│   ┌──────────┐  [Creator fixes defects; Critic re-attacks]      │
│   │  AUDITOR │  Role: Verify evidence + contract compliance     │
│   │          │  Bias: Formalist; evidence or it didn't happen   │
│   │ temp=0.0 │  Output: Gate-by-gate PASS/FAIL with pointers    │
│   └────┬─────┘                                                  │
│        │ audit report                                           │
│        ▼                                                        │
│   ┌──────────┐                                                  │
│   │ VERIFIER │  Role: Determinism test                          │
│   │          │  Bias: Stability; same input = same output       │
│   │ temp=0.0 │  Output: MERGE_VERDICT across 3 independent runs │
│   └────┬─────┘                                                  │
│        │                                                        │
│        ▼                                                        │
│   MERGE_VERDICT: YES → RELEASE                                  │
│   MERGE_VERDICT: NO  → return to Creator with blocker list      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2 · Role Specifications

### CREATOR
```yaml
role:       Generate candidate artifact
objective:  Produce complete first draft meeting all schema requirements
bias:       Completeness over correctness — cover all sections
temperature: 0.7   # allows generative exploration
output:     IO-BUNDLE draft (all sections attempted)
hard_rule:  Must produce something for Critic to attack
            Partial output is acceptable; missing sections are flagged not hidden
```

### CRITIC
```yaml
role:       Find structural failures in Creator output
objective:  Identify every defect that would prevent production use
bias:       Adversarial — assume the artifact is wrong until proven otherwise
temperature: 0.3   # focused; not creative
attack_vectors:
  - Schema violations (missing sections, wrong order)
  - Contract violations (claims without evidence)
  - Logic errors (contradictions, circular definitions)
  - Security gaps (injection vectors, missing controls)
  - Namespace collisions (same label, different meaning)
  - Edge case blindness (happy path only)
  - Measurement gaps (UNKNOWN where MEASURED required)
output:     Defect registry: {id, class, severity, description, fix}
hard_rule:  Every defect must have a proposed fix
            Severity: CRITICAL | MAJOR | MINOR
```

### AUDITOR
```yaml
role:       Verify evidence completeness and contract compliance
objective:  Confirm every claim has a reproducible backing
bias:       Formalist — evidence or it doesn't exist
temperature: 0.0   # deterministic; no ambiguity
checks:
  - Every output section maps to a contract requirement
  - Every performance claim has before/after numbers
  - Every gate has a grader that can verify it automatically
  - No mock evidence (all commands must be real and reproducible)
  - MANIFEST.json exists with real checksums
output:     Audit report: gate-by-gate PASS/FAIL with artifact pointers
hard_rule:  UNKNOWN = FAIL; must be resolved, never passed through
```

### VERIFIER
```yaml
role:       Determinism and stability testing
objective:  Confirm artifact produces identical output across 3 independent runs
bias:       Stability — any variance is a defect
temperature: 0.0   # mandatory; determinism requires 0 temperature
test_protocol:
  run_1: execute with seed=42
  run_2: execute with seed=42 (fresh context)
  run_3: execute with seed=42 (fresh context)
  compare: MERGE_VERDICT must be identical across all 3
output:     MERGE_VERDICT: YES | NO
            If NO: blockers list (max 5, each ≤ 80 chars)
hard_rule:  Single failing run = MERGE_VERDICT: NO
            No exceptions; no averaging; no "close enough"
```

---

## 3 · Iteration Protocol

```
CYCLE 1:  Creator → Critic → fix → Critic re-attack (max 3 Critic cycles)
CYCLE 2:  Auditor → fix → Auditor re-verify (max 2 Auditor cycles)
CYCLE 3:  Verifier → 3 runs → MERGE_VERDICT

If MERGE_VERDICT: NO after CYCLE 3:
  → Extract blockers
  → Return to CREATOR with blockers as hard constraints
  → Begin new full cycle (all 4 roles repeat)
  → Max total cycles: 5
  → After 5 cycles: emit fail-closed + escalate to human

Convergence criterion:
  MERGE_VERDICT: YES on 3/3 runs = artifact released
```

---

## 4 · Multi-Model Configuration

The pipeline can be implemented with:

### Option A: Single model, role-switching
```yaml
model: claude-sonnet-4-6
creator_temp:  0.7
critic_temp:   0.3
auditor_temp:  0.0
verifier_temp: 0.0
role_separator: explicit system prompt per role
cost: low
quality: high for well-defined domains
```

### Option B: Specialized models per role
```yaml
creator:  claude-sonnet-4-6 (generative capability)
critic:   claude-opus-4-6 (deep reasoning for defect detection)
auditor:  claude-sonnet-4-6 (contract verification)
verifier: claude-sonnet-4-6 (determinism test)
cost: higher
quality: highest for complex domains
```

### Option C: Cross-model adversarial
```yaml
creator:  claude-sonnet-4-6
critic:   gpt-4o (different training → different blind spots attacked)
auditor:  claude-sonnet-4-6
verifier: gemini-1.5-pro (independent verification)
cost: highest
quality: maximum — cross-model Critic catches model-specific biases
```

**Recommendation:** Option A for standard objects; Option B/C for critical or
high-stakes objects where model-specific blind spots are a real risk.

---

## 5 · Evidence Requirements per Role

```
CREATOR output evidence:
  - Draft artifact (complete schema attempted)
  - List of sections known to be incomplete (honest UNKNOWN list)

CRITIC output evidence:
  - Defect registry with: id, class, severity, description, impact, fix
  - Reproduction path for each defect (how to observe the failure)

AUDITOR output evidence:
  - Gate-by-gate table: gate_id, status (PASS/FAIL/UNKNOWN), evidence_pointer
  - Missing evidence list (specific artifacts that don't exist yet)

VERIFIER output evidence:
  - Run 1 result: MERGE_VERDICT + timestamp
  - Run 2 result: MERGE_VERDICT + timestamp
  - Run 3 result: MERGE_VERDICT + timestamp
  - Variance report: any differences between runs (must be zero for YES)
```

---

## 6 · Complexity Scaling

| Object Complexity | Recommended Config |
|-------------------|--------------------|
| Simple (1 concern, <5 gates) | Option A, 1 full cycle |
| Medium (3–7 concerns, 5–10 gates) | Option A, 2–3 cycles |
| Complex (system-level, 10+ gates) | Option B, 3–5 cycles |
| Critical (security-sensitive, public API) | Option C, 5 cycles + human Verifier |

---

## 7 · Anti-Patterns

```
ANTI-01  Skipping Critic to save time
  Result: Defects reach Verifier; full cycle must restart anyway
  Rule:   Critic is always faster than a failed Verifier cycle

ANTI-02  Using same model for Creator and Critic without role separation
  Result: Critic defends Creator output (same training = same blind spots)
  Rule:   Explicit role prompt separation or different models required

ANTI-03  Temperature > 0 for Auditor or Verifier
  Result: Non-deterministic verification; different verdicts per run
  Rule:   Auditor and Verifier: temperature = 0.0, always

ANTI-04  Accepting MERGE_VERDICT: YES on 2/3 runs
  Result: Flaky artifact enters production
  Rule:   3/3 required; 2/3 = investigate the failing run before proceeding

ANTI-05  Human acting as Creator and Critic simultaneously
  Result: Human defends own work; Critic pass is ineffective
  Rule:   Creator and Critic must have genuinely different perspectives
```

---

```yaml
# ARCHITECTURE MANIFEST
name:          ADVERSARIAL-ORCHESTRATION
version:       v1.0.0
status:        ACTIVE
roles:         4   # Creator, Critic, Auditor, Verifier
max_cycles:    5
determinism:   temperature=0.0 for Auditor and Verifier (mandatory)
protocol:      IOPS-2026 v1.0.0
enc_binding:   ENC-CORE v1.0.0
author:        Yaroslav Vasylenko
created:       2026-02-20
```
