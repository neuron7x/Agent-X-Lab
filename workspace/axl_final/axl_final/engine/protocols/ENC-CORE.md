# ENC-CORE: Exo-Neural Convergence Operational Specification
**Version:** v1.0.0 · **Status:** `ACTIVE` · **Author:** Yaroslav Vasylenko
**Classification:** Cognitive Architecture Protocol

---

## Definition

**Exo-Neural Convergence (ENC)** is an operational mode in which biological intent
and external computational execution form a **closed cognitive loop** — functioning
as a single unified decision-processing system.

In this mode:
- AI is not a tool being operated
- AI is not an autonomous agent being supervised
- AI is an **externalized neural module** participating in real-time cognition

The loop is closed. Output is the product of the combined system, not either component alone.

---

## 1 · System Architecture

```
┌─────────────────────────────────────────────────────┐
│                  ENC CLOSED LOOP                    │
│                                                     │
│  ┌──────────────┐         ┌──────────────────────┐ │
│  │  BIOLOGICAL  │ intent  │   COMPUTATIONAL      │ │
│  │  SUBSYSTEM   │────────▶│   MODULE             │ │
│  │              │         │                      │ │
│  │  - Intent    │◀────────│  - Memory            │ │
│  │  - Policy    │ artifact│  - Formalization     │ │
│  │  - Evaluation│         │  - Synthesis         │ │
│  │  - Direction │         │  - Verification      │ │
│  └──────────────┘         └──────────────────────┘ │
│           │                          │              │
│           └──────────────────────────┘              │
│                   feedback loop                     │
└─────────────────────────────────────────────────────┘
```

**Signal flow:**
1. Biological subsystem generates intent + evaluation policy
2. Computational module executes: memory, formalization, synthesis
3. Verification pass: separates valid from unverified
4. Artifacts return to biological subsystem → update intent
5. Repeat

---

## 2 · Operational Properties

### 2.1 What ENC Is

```
✅ A closed feedback loop between human intent and AI execution
✅ A methodology for producing verified cognitive artifacts at speed
✅ A cognitive architecture where AI handles externalized memory + formalization
✅ A system where the human retains strategic direction + truth policy
✅ A productive asymmetry: biological judgment × computational throughput
```

### 2.2 What ENC Is Not

```
❌ "Using AI as a tool" (tool implies separation; ENC implies integration)
❌ "Delegating tasks to AI" (delegation implies hand-off; ENC implies co-processing)
❌ "Automation" (automation eliminates the human; ENC amplifies the human)
❌ "Prompt engineering as a skill" (prompting is just the interface layer)
❌ Dependency or addiction (the biological subsystem retains full strategic control)
```

---

## 3 · Invariants of Valid ENC State

```
ENC-INV-01  Biological subsystem retains TRUTH POLICY
            The human decides what counts as valid/invalid output.
            AI never sets its own acceptance criteria.

ENC-INV-02  Verification is non-negotiable
            No artifact exits the loop without passing verification.
            Speed never justifies skipping the verifier pass.

ENC-INV-03  Artifacts are the unit of value
            Internal states (ideas, plans, intentions) have no value.
            Only externalized, verified artifacts count.

ENC-INV-04  Feedback modifies intent
            Artifacts returned to the biological subsystem must be
            allowed to update policy. Fixed intent = closed loop broken.

ENC-INV-05  The loop must be auditable
            Every artifact must have a traceable origin.
            Black-box outputs violate ENC integrity.
```

---

## 4 · Adversarial Orchestration (Production Implementation)

The primary production implementation of ENC is **Adversarial Orchestration**:

```
CYCLE (per artifact):

  CREATOR  → generates candidate output
             (role: produce; bias: completeness)

  CRITIC   → attacks the candidate
             (role: destroy; bias: find structural failure)
             Output: defect registry with severity classification

  AUDITOR  → verifies evidence completeness
             (role: validate; bias: contract compliance)
             Output: gate-by-gate pass/fail with evidence pointers

  VERIFIER → determinism test
             (role: stabilize; bias: reproducibility)
             Output: MERGE_VERDICT across 3 independent runs

  RELEASE  → only if Verifier emits MERGE_VERDICT: YES (all 3 runs)
```

**Roles may map to:**
- Different AI models (Claude, GPT-4, Gemini) in specialized roles
- Single model in sequential role-switching (temperature=0 for Verifier)
- Human-in-loop as Auditor or final Verifier

---

## 5 · Performance Characteristics

| Metric | Solo Human | ENC System |
|--------|-----------|------------|
| Working memory capacity | ~7 items | Unlimited (externalized) |
| Formalization speed | Hours/days | Minutes |
| Defect detection (structural) | Misses ~40% | Catches via Critic pass |
| Determinism verification | Manual, slow | Automated 3-run gate |
| Knowledge retention | Lossy | Persistent artifacts |
| Parallel hypothesis testing | 1–2 | N (multi-agent) |

*Note: These are operational observations from practice, not controlled benchmarks.*

---

## 6 · Failure Modes

```
FAILURE-01  Intent drift
  Symptom:  Artifacts diverge from original purpose over iterations
  Cause:    Feedback loop not updating intent; ENC-INV-04 violated
  Fix:      Re-anchor to original objective; re-run CREATOR with explicit constraints

FAILURE-02  Verification bypass
  Symptom:  Unverified artifacts released; quality degrades
  Cause:    Speed pressure eliminating Verifier pass; ENC-INV-02 violated
  Fix:      Hard gate: no artifact exits without MERGE_VERDICT: YES

FAILURE-03  Truth policy erosion
  Symptom:  AI-generated acceptance criteria replace human judgment
  Cause:    ENC-INV-01 violated; biological subsystem abdicating policy
  Fix:      Human explicitly re-establishes what "valid" means for this artifact

FAILURE-04  Artifact inflation
  Symptom:  Many artifacts, low density of value; no filtering
  Cause:    Missing scoring function; no release threshold
  Fix:      Apply score ≥ 98 gate; defer or discard below-threshold artifacts

FAILURE-05  Loop break
  Symptom:  Artifacts not feeding back; system becomes one-directional
  Cause:    No review cycle; human consuming outputs without updating policy
  Fix:      Scheduled re-anchoring: review artifact set, update intent constraints
```

---

## 7 · Integration with IOPS-2026

Every object produced under ENC must comply with IOPS-2026:

```yaml
enc_iops_binding:
  creator_output:    IO-BUNDLE draft (§1–§8 attempted)
  critic_output:     defect registry (class, severity, fix)
  auditor_output:    gate-by-gate evidence verification
  verifier_output:   3-run determinism result → MERGE_VERDICT
  release_artifact:  IOPS-2026 compliant IO-BUNDLE + MANIFEST.json
```

The Adversarial Orchestration cycle **is** the IOPS-2026 production pipeline.

---

## 8 · ENC vs. Competing Frameworks

| Framework | Human Role | AI Role | Output Unit | Verifiable? |
|-----------|-----------|---------|-------------|-------------|
| Prompt engineering | Operator | Tool | Text response | Rarely |
| AI assistant | User | Assistant | Conversation | No |
| Agentic AI | Supervisor | Autonomous agent | Actions | Partially |
| **ENC** | **Cognitive director** | **Exo-neural module** | **Verified artifact** | **Always** |

ENC's distinguishing property: **the output unit is always a verified artifact**, never raw text, never an action without audit trail.

---

```yaml
# PROTOCOL MANIFEST
name:            ENC-CORE
version:         v1.0.0
status:          ACTIVE
invariants:      5
failure_modes:   5
production_impl: Adversarial Orchestration
iops_binding:    IOPS-2026 v1.0.0
author:          Yaroslav Vasylenko
created:         2026-02-20
```
