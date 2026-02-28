# 08 Security Gates

Required security-facing checks:
- `CodeQL Analysis` (`.github/workflows/codeql-analysis.yml`)
- `Dependency Review` (`.github/workflows/dependency-review.yml`)
- `Secret Scan (Gitleaks)` (`.github/workflows/secret-scan.yml`)
- `Action Pin Audit` (`.github/workflows/action-pin-audit.yml`)
- `Workflow Hygiene` (`.github/workflows/workflow-hygiene.yml`)

Evidence for CI calibration is stored under `build_proof/ci_calibration/`.
