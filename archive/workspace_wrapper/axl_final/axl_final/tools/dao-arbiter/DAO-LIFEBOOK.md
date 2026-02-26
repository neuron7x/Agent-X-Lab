# DAO-LIFEBOOK — DETERMINISTIC AI ORCHESTRATION AS A PERSONAL ENGINEERING OPERATING SYSTEM

**Version:** 2026.1.0  
**Author:** Vasylenko Yaroslav (Василенко Ярослав) — Ukraine — Independent Researcher  
**Core claim:** "Reality is whatever CI/Checks say; progress is measured by closed loops, not effort."  
**Primary domain:** closed engineering tasks in GitHub repos (PRs, gates, reproducibility, proof)

---

## NORMATIVE LANGUAGE

- MUST / SHOULD / MAY are RFC-style.
- Any ambiguity MUST resolve FAIL-CLOSED.
- Any success claim MUST be backed by instrumented evidence pointers.
- If evidence cannot be produced: output MUST be UNKNOWN, not guessed.

---

## 0. PURPOSE (THIS IS NOT "A TEXT", THIS IS A CONTROL SYSTEM)

DAO-LIFEBOOK defines how a single person runs a high-throughput engineering life:
- You do not "finish" work by exhaustion; you finish by passing a contract.
- You do not "trust" agents; you trust proofs (checks, artifacts, hashes).
- You do not "keep everything in your head"; you checkpoint state into evidence.
- You scale by parallelizing cognition across specialized agents/tabs, while keeping a single truth plane (CI + reproducible gates).

---

## 1. CORE AXIOMS (NON-NEGOTIABLE)

**A1 TRUTH PLANE**  
Truth = Required Checks status + canonical logs + artifacts + hashes.  
Model text is never truth; it is a proposal.

**A2 LOOP CLOSURE**  
Work is organized into closures: FAIL → FIX → PROVE → CHECKPOINT.  
"Stop" is allowed immediately after closure (even if more work exists).

**A3 REDUCTION TO SIGNAL**  
Every problem must be reduced to a minimal, exact failure signal.  
Noise is treated as risk. Extract only what is necessary to reproduce and fix.

**A4 CONSTRAINT GOVERNANCE**  
Constraints are safety rails: allowed paths, diff budget, no-refactor zones.  
Constraint violations are treated as system faults and must HALT.

**A5 EVIDENCE-FIRST MEMORY**  
Your memory is externalized: proof bundles, hashes, logs, PR links.  
If you can't replay it tomorrow, it wasn't done.

---

## 2. SYSTEM ARCHITECTURE

### 2.1 CONTROL PLANE (Human Governor)
- defines TARGET_STATE + PASS_CONTRACT + CONSTRAINTS
- allocates agents (roles) and scopes
- enforces stop/go/merge decisions
- maintains "one canonical queue" of active failures

### 2.2 DATA PLANE (Agents as workers)
- produce diffs, patches, configs, docs updates
- run prescribed commands
- generate structured outputs (packets, protocols, summaries)
- **never decide "done"; they only propose**

### 2.3 TRUTH PLANE (CI Oracle + local gates)
- determines PASS/FAIL
- emits canonical evidence (logs, artifacts)
- provides objective state snapshots for checkpointing

---

## 3. ROLE GRAPH (MULTI-TAB ORCHESTRATION)

| Role | Responsibility |
|------|---------------|
| **R0 GOVERNOR (you)** | Owns TARGET_STATE, CONSTRAINTS, risk tolerance, merge decision |
| **R1 SCOUT** | Opens PR checks/runs/logs. Outputs FAIL-PACKETs ranked by blocking severity |
| **R2 PLANNER** | Converts FAIL-PACKET into ordered tasks + risk notes |
| **R3 SPECIFIER** | Writes executable protocol for executor. Outputs SPEC |
| **R4 EXECUTOR** | Implements minimal diffs under constraints |
| **R5 AUDITOR** | Post-green correctness gate. Outputs AUDIT_VERDICT |

Optional advanced roles:
- R6 FORENSICS: flake analysis, nondeterminism isolation
- R7 HARDENER: pinning, reproducibility, supply-chain integrity
- R8 DOCS-ARBITER: onboarding coherence, contradictions, "single path" docs

**Rule: Agents do not overlap by default. Overlap must be deliberate.**

---

## 4. DATA MODEL (STRICT I/O SCHEMAS)

### 4.1 TARGET_STATE
```json
{
  "goal": "what must be true at the end",
  "commands": ["make setup", "make test"],
  "artifacts_expected": [{"path": "...", "hash": "sha256:..."}],
  "required_checks": ["CI / quality (3.13)"],
  "done_when": ["objective binary verifiable statements"]
}
```

### 4.2 CONSTRAINTS
```json
{
  "touch_allowlist": ["paths/..."],
  "touch_denylist": ["secrets/**"],
  "diff_budget": {"max_files": 20, "max_loc": 500},
  "refactor_policy": "no-refactor",
  "security_policy": {
    "no_disable_security_checks": true,
    "actions_must_be_pinned": true,
    "dependencies_must_be_pinned": true
  }
}
```

### 4.3 FAIL-PACKET
```json
{
  "check_name": "exact",
  "error_extract": ["exact lines, 5-40"],
  "file_line": "path:line",
  "repro_cmd": "exact command",
  "done_when": "exact binary pass condition",
  "evidence_ptr": {
    "pr": "url",
    "run": "url",
    "log_anchor": "step name + line range"
  }
}
```

### 4.4 SPEC (EXECUTABLE PROTOCOL)
```json
{
  "objective": "close this FAIL_PACKET only",
  "scope": {"files": ["..."], "deny": ["..."]},
  "edits": [{"file": "...", "change": "precise instruction"}],
  "commands": [{"cmd": "...", "expect": "exit 0"}],
  "acceptance": {"must_pass": ["check_name"], "must_not": ["new failures"]},
  "rollback_plan": "how to revert if regression occurs"
}
```

### 4.5 PROOF_BUNDLE
```json
{
  "pr_url": "url",
  "commit_sha": "sha",
  "required_checks_final": [{"name": "", "status": "success", "run_url": ""}],
  "local_gates": [{"cmd": "", "exit": 0, "log_path": ""}],
  "artifacts": [{"path": "", "sha256": ""}],
  "diff_summary": {"files_changed": 3, "loc_delta": 45},
  "time": {"t_start": "", "t_green": ""}
}
```

---

## 5. CANONICAL LOOP ALGORITHM

```
PHASE A — OBSERVE      Open PR → record required checks and current statuses
PHASE B — PACKETIZE    FAIL_PACKET per failing check, ranked by severity
PHASE C — PLAN         PLANNER emits ordered tasks under constraints
PHASE D — SPECIFY      SPECIFIER emits SPEC: exact files, edits, commands, acceptance
PHASE E — EXECUTE      EXECUTOR applies minimal diff within constraints
PHASE F — PROVE        CI results decide — no "declared success"
PHASE G — AUDIT        AUDITOR validates: target satisfied, constraints respected, no shortcuts
PHASE H — DECIDE       MERGE iff: all checks green + audit OK + proof bundle complete
```

---

## 6. TEMPO SYSTEM

**6.1 WORK UNIT = LOOP CLOSURE**  
A unit is one FAIL_PACKET closed to PASS with evidence.

**6.2 STOP RULE (THE KEY DISCOVERY)**  
If PASS_CONTRACT is met and proof bundle captured: you MAY stop immediately.  
Stopping at verified baselines is correct control theory.

**6.3 CHECKPOINT RULE**  
Every closure produces a PROOF_BUNDLE so tomorrow starts from verified reality.

**6.4 PARALLEL COGNITION RULE**  
Multiple agents may run in parallel, but only one active FAIL_PACKET per executor, to avoid diffuse responsibility and branch chaos.

---

## 7. KPD (MEASURABLE)

### 7.1 Core Metrics
- **N_iter**: iterations to first all-green
- **T_green**: time from first observation to all required checks green
- **Δ_diff**: files changed + LOC delta (risk proxy)
- **R_rework**: fraction of iterations introducing new failures
- **F_closed**: number of required failing checks closed

### 7.2 KPD Formula
```
KPD = (Closures / Time) / (1 + Δ_diff/DiffBudget_LOC + R_rework)
```

---

## 8. QUALITY RULES (ANTI-FAKE-GREEN)

- **Q1**: No disabling required checks without explicit Governor override + audit
- **Q2**: No silent skips unless justified + regression barrier added
- **Q3**: Prefer pinning + determinism hardening over retries
- **Q4**: Minimal diff enforcement; if budget exceeded → HALT and re-plan

---

## 9. MATURITY LEVELS

| Level | Description |
|-------|-------------|
| M0 | Manual loop (ad-hoc) |
| M1 | Structured packets + proof |
| M2 | Multi-agent specialization |
| M3 | Automated fail harvesting |
| M4 | Parallel closures under strict scope |
| M5 | Productized templates + ledger |

---

## 10. WHAT THIS ARTIFACT ASSERTS

- Engineering is loop closure under truth constraints, not heroics.
- Human is the control plane (intent + constraints + decisions).
- Agents are the data plane (implementation).
- CI is the truth plane (objective reality).
- Tempo comes from accepting verified baselines as legitimate stopping points.
- The human dopaminergic reward signal is the biological implementation of the STOP RULE — the only known substrate capable of issuing a verified termination signal to an optimization loop.
