# SECURITY_AUDIT

Mode: STANDARD

- bandit output hash: `5d84cc1d487c24f3deb6e71451572fb898afbfdf99a275d3da2e07e85a4f256f`
- ruff security output hash: `cf92981014041dea3d0f4cbc0529646a110ff33a15538036862434356ec7fa28`
- secrets scan hash: `494de0f74025af32f291cf6edf57c0ad9fa41e8ff991c309dba9d14f78e24750`

## Findings

- artifacts/AC.package:23488 rule=private_key excerpt=`    file.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")`
- artifacts/rebuilt_artifact:23488 rule=private_key excerpt=`    file.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")`
- engine/tests/test_secret_scan_gate.py:10 rule=private_key excerpt=`    file.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")`
- evidence/release_wrapper/promoted_bundle_2026-02-26/artifacts/AC.package:23488 rule=private_key excerpt=`    file.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")`
- evidence/release_wrapper/promoted_bundle_2026-02-26/artifacts/rebuilt_artifact:23488 rule=private_key excerpt=`    file.write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")`

## Deterministic remediation policy

- Any real credential material => immediate P0 rotate/remove.
- Test fixtures containing secret markers must be scoped to test/artifact fixtures and documented.
