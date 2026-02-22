# Release Checklist

## 1) Release Gates (must pass)

- [ ] `make check`
- [ ] `pytest -q`
- [ ] `python tools/release_guard.py --mode release --version <pyproject-version>`
- [ ] CI status checks are green on default branch

## 2) Security Checks

- [ ] `python tools/secret_scan_gate.py --repo-root . --config SECURITY.redaction.yml`
- [ ] `python tools/pip_audit_gate.py --requirements requirements.lock --allowlist policies/pip_audit_allowlist.json`
- [ ] `.github/workflows/security.yml` latest run is successful

## 3) Proof Artifacts

- [ ] `artifacts/proof/**` generated and archived by CI
- [ ] `artifacts/reports/**` uploaded in CI artifacts
- [ ] Release manifest generated (`artifacts/release/MANIFEST.release.json`)
- [ ] `artifacts/release/release.report.json` present for the release build

## 4) Documentation and Notes

- [ ] `pyproject.toml` version is bumped intentionally
- [ ] `CHANGELOG.md` has entry for the target version
- [ ] `docs/release-notes.md` has section for the target version
- [ ] PR description includes release impact summary

## 5) Sign-off

- [ ] Engineering owner approval
- [ ] Security owner approval (for Security section changes)
- [ ] Final release operator sign-off in workflow dispatch inputs / run summary
