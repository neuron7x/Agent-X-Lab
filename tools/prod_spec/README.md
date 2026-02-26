# PROD_SPEC_V2.1 — Artifact Tooling

This folder contains deterministic, offline-capable tooling to generate the **mandatory** artifacts required by `engine/scripts/check_prod_spec_gates.py`.

## One-shot (local)

```bash
# 0) (Optional) Build frontend for *this* snapshot
# npm ci && npm run build

# 1) Deterministic AC.package + build reproducibility artifacts
python tools/prod_spec/generate_build_artifacts.py --root .

# 2) AC signing (Ed25519 JWS)
# Production: set AC_SIGNING_SEED_B64URL or AC_SIGNING_SEED_HEX (32 bytes seed)
# DEV: allow ephemeral key (NOT for production)
python tools/prod_spec/sign_ac_package.py --allow-ephemeral

# 3) Formal + finality artifacts
python tools/prod_spec/generate_formal_artifacts.py

# 4) Runtime replay harness
python tools/prod_spec/run_replay_harness.py

# 5) Gate check
python engine/scripts/check_prod_spec_gates.py \
  --ac artifacts/AC_VERSION.json \
  --pb-dir ad2026_state/pb/ \
  --ssdf artifacts/SSDF.map \
  --artifacts-dir artifacts/ \
  --out artifacts/gate_check.report.json
```

## Remaining human gate

`G5/ARB.decision.memo` is intentionally enforced as a **human approval** artifact.

To clear G5:
1) ARB reviews the exact release candidate (AC.package sha256 + gate report).
2) Update `artifacts/ARB.decision.memo`:
   - `decision = "APPROVED"`
   - `approval.approved = true`
   - `approval.approved_at` set (UTC)
   - keep SoD: author ≠ approver ≠ auditor

Only after that should a production deploy proceed.
