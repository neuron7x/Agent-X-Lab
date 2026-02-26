# DAO-Arbiter: Deterministic AI Orchestration

**Author:** Vasylenko Yaroslav — Ukraine  
**Version:** 2026.1.0  
**Preprint:** [arXiv — pending] | `Vasylenko_DAO_Arbiter_2026.pdf`

> *Reality is whatever CI/Checks say; progress is measured by closed loops, not effort.*

---

## What this is

This repository contains both the **theoretical framework** and the **working Python implementation** of the Dopaminergic Arbiter Hypothesis: the claim that robust AI alignment requires a human as the sole verified arbiter of loop termination.

**Two components in one repo:**

| Component | Location | Purpose |
|-----------|----------|---------|
| Research preprint | `Vasylenko_DAO_Arbiter_2026.pdf` | Full academic paper |
| Python SDK | `dao_lifebook/` | Runnable implementation of the DAO model |
| Schemas | `spec/`, `examples/` | Formal FAIL_PACKET and PROOF_BUNDLE schemas |
| Outreach | `docs/` | arXiv, LessWrong, Anthropic submission drafts |

---

## Core Architecture

```
CONTROL PLANE  →  Human Governor
                  owns: TARGET_STATE, PASS_CONTRACT, CONSTRAINTS
                  sole authority on: "done"

DATA PLANE     →  AI Agents (narrow, scoped, no merge authority)
                  produce: diffs, proposals, packets

TRUTH PLANE    →  CI / External Verification Oracle
                  determines: PASS / FAIL only
```

## Canonical Loop

```
FAIL → FIX → PROVE → CHECKPOINT
```

Eight phases: OBSERVE → PACKETIZE → PLAN → SPECIFY → EXECUTE → PROVE → AUDIT → DECIDE

---

## Install (Python SDK)

```bash
pip install -e ".[dev]"
```

Requires Python ≥ 3.11.

## CLI Usage

```bash
# Observe PR checks (read-only)
export GITHUB_TOKEN=YOUR_GITHUB_TOKEN
dao observe owner/repo#123

# Extract FAIL_PACKETs
dao packetize owner/repo#123

# Run one canonical loop iteration
dao run owner/repo#123 --config dao_config.example.json

# View proof bundle ledger
dao ledger

# Verify a proof bundle
dao verify <hash_prefix>
```

## Run Tests

```bash
pytest dao_lifebook/tests.py -v
```

---

## Repository Structure

```
dao-arbiter/
├── dao_lifebook/          ← Python package (SDK)
│   ├── __init__.py
│   ├── models.py          ← Pydantic schemas (§4)
│   ├── engine.py          ← Canonical loop (§5)
│   ├── roles.py           ← Role graph R1–R5 (§3)
│   ├── truth_plane.py     ← CI Oracle + LocalGate (§2.3)
│   ├── constraints.py     ← Constraint enforcement (A4)
│   ├── evidence.py        ← Checkpointing (A5)
│   ├── metrics.py         ← KPD formula (§7)
│   ├── cli.py             ← CLI interface
│   └── tests.py           ← Full test suite
├── Vasylenko_DAO_Arbiter_2026.pdf   ← Preprint
├── preprint/
│   └── dopaminergic_arbiter_2026.pdf
├── spec/
│   └── PASS_CONTRACT_template.md
├── examples/
│   ├── FAIL_PACKET.example.json
│   ├── PROOF_BUNDLE.example.json
│   └── loop_closure_example.md
├── docs/
│   ├── SUBMISSION_METADATA.md
│   ├── ANTHROPIC_SAFETY_EMAIL.md
│   ├── LESSWRONG_POST.md
│   ├── OUTREACH_ENDORSEMENT_EMAIL.md
│   └── DEPLOYMENT.md
├── scripts/
│   └── verify_repo.py
├── dao_config.example.json
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── .github/workflows/ci.yml
```

---

## License

- **Research content** (preprint, docs, schemas): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Source code** (`dao_lifebook/`): MIT — see `LICENSE`
