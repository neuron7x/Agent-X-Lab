# udgs_core CHANGELOG

All notable changes to the `udgs_core` package are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [QA8] 2026-02-25 — Autonomous Audit (Self-Healing)

### Added
- `udgs_core/autonomous_audit.py` — `AutonomousAuditEngine` class with:
  - `detect_drift()` — SHA-256 tree hash comparison against QA7 baseline.
  - `run_cycle()` — Single scan-and-heal cycle with full FAIL→FIX→PROVE→CHECKPOINT gate.
  - `watch()` — Continuous daemon with configurable interval and `max_cycles` termination.
  - `score_system()` — Integrity metric (0.0–1.0) with PASS/DEGRADED grade.
  - `HEAL_LOG.jsonl` — Append-only structured event log.
  - `QA8_STATUS.json` — Live status with mode, counters, anchors.
- `system/qa8.config.json` — Runtime configuration for QA8 watch daemon.
- `udgs_core/tests/test_udgs_core.py` — Formal Python test suite (70 tests) covering all modules.
- CLI commands: `qa8-heal`, `qa8-watch`, `qa8-status`.
- `build_proof/ITERATION_CYCLE_02_QA8_AUTONOMOUS_AUDIT.md` — Iteration checkpoint.

### Fixed
- **CRITICAL**: `dao_lifebook_adapter.proof_bundle_to_udgs_packet()` generated
  `REGRESSION_TEST_PAYLOAD` without the required `suite` and `expected` keys,
  causing every produced packet to fail STRICT_JSON validation.
  — Fixed by adding `suite: [...]` and `expected: {...}` to the regression payload.

### Changed
- `system/udgs.config.json` — Added `qa8` block, `grade: QA8_…`, `promoted_from`,
  and `qa8_state/` to `audit_exclude_rel_prefixes`.
- `build_proof/scripts/check_ui_contract.py` — Added QA8 marker and config checks.
- `system/PRE_VERIFICATION_SCRIPT.sh` — Added `udgs_core/tests/` pytest step
  and `qa8-heal` NOMINAL verification step.
- `README.md` and `UNIFIED_SYSTEM.md` — Updated to QA8, added mode table and upgrade rule.
- Language quality cycle count: 7 → 8.

### Promoted from
`QA7_STRICT_ANCHOR_HARDENED` (2026-02-23)
— QA7 system anchor preserved in `system/qa8.config.json → promoted_from.system_anchor`.

---

## [QA7] 2026-02-23 — Strict Anchor Hardening

### Added
- Deterministic `SYSTEM_OBJECT.json` with SHA-256 component tree hashes.
- `UDGS_MANIFEST.json` with consistency_checks for all components.
- `DeterministicCycle` (FAIL→FIX→PROVE→CHECKPOINT) with fail-closed HALT gate.
- STRICT_JSON packet validation with self-referential `SHA256_ANCHOR`.
- DAO-Arbiter adapter (`dao_lifebook_adapter.py`).
- Language quality refinement: 7 cycles (UA/EN, docs, scripts).
- Determinism proof: two independent build runs produce identical system anchor.

---

## [v1.0] Initial — AXL+UDGS Unified System Object

- `udgs_core.anchors` — `sha256_tree`, `sha256_file`, `sha256_json`, `sha256_bytes`.
- `udgs_core.state_machine` — `DeterministicCycle`, `LoopState`, `Evidence`.
- `udgs_core.strict_json` — STRICT_JSON packet validation contract.
- `udgs_core.system_object` — `build_system_object`, `write_system_object`.
- `udgs_core.cli` — CLI entry-point with `anchor`, `validate-packet`, `loop`,
  `packet-anchor`, `build-system-object` commands.
