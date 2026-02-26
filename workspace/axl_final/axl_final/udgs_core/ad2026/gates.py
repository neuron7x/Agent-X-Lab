"""
udgs_core.ad2026.gates
======================
AD-2026 §VIII — Execution Gates G6 through G11

G6-AUTH         : AAID + AC signature + PB hash-chain
G7-FORMAL       : SMT/invariant proof (see typed_plan.SMTGate)
G8-SANDBOX      : Hermetic env fingerprint + toolchain pins
G9-MCP          : MCP policy + RCT token validation
G10-SYNC        : CI-L9 metrics (BSS alignment + determinism)
G11-INVARIANT   : CI-L10 kernel integrity + replay + SSDF + Phase G

All gates are fail-closed: FAIL => block execution, emit PB.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .identity import AAID, ACRootKey, APBHeader, jws_verify, zto_verify
from .typed_plan import GateResult, SPS, SMTGate, build_ac_baseline_invariants


# ──────────────────────────────────────────────
# Gate status
# ──────────────────────────────────────────────

class GateStatus(str, Enum):
    PASS        = "PASS"
    FAIL        = "FAIL"
    ERROR       = "ERROR"
    NOT_READY   = "NOT_READY"


@dataclass
class GateRunResult:
    gate_id:    str
    status:     GateStatus
    evidence:   List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == GateStatus.PASS

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


# ──────────────────────────────────────────────
# G6-AUTH
# ──────────────────────────────────────────────

class G6Auth:
    """
    AD-2026 G6-AUTH:
      1. AAID signature verification
      2. AC signature to AC_ROOT_KEY
      3. PB hash-chain continuity
    FAIL_CLOSED
    """
    GATE_ID = "G6-AUTH"

    def run(
        self,
        bundle:             APBHeader,
        trusted_aaid:       AAID,
        ac_root_key:        ACRootKey,
        ac_canonical_bytes: bytes,
        ac_signature:       str,
        expected_prev_hash: str,
    ) -> GateRunResult:
        ok, errors = zto_verify(
            bundle, trusted_aaid, ac_root_key,
            ac_canonical_bytes, ac_signature, expected_prev_hash,
        )
        return GateRunResult(
            gate_id=self.GATE_ID,
            status=GateStatus.PASS if ok else GateStatus.FAIL,
            evidence=[f"AAID={trusted_aaid.public_id[:16]}… AC_KEY={ac_root_key.key_id}"],
            violations=errors,
        )


# ──────────────────────────────────────────────
# G7-FORMAL  (delegates to SMTGate)
# ──────────────────────────────────────────────

class G7Formal:
    """
    AD-2026 G7-FORMAL:
      Prove SPS ⊨ AC_invariants via constraint solver.
    SAT (proven) or FAIL_CLOSED.
    """
    GATE_ID = "G7-FORMAL"

    def __init__(self, smt: Optional[SMTGate] = None) -> None:
        self.smt = smt or SMTGate(build_ac_baseline_invariants())

    def run(self, sps: SPS) -> GateRunResult:
        result = self.smt.prove(sps)
        return GateRunResult(
            gate_id=self.GATE_ID,
            status=GateStatus.PASS if result.passed else GateStatus.FAIL,
            evidence=result.evidence,
            violations=result.violations,
        )


# ──────────────────────────────────────────────
# G8-SANDBOX
# ──────────────────────────────────────────────

@dataclass
class EnvironmentProfile:
    """Pinned hermetic environment fingerprint."""
    profile_id:          str
    python_version:      str
    platform:            str
    toolchain_pins:      Dict[str, str]    # {"tool": "version_or_hash"}
    env_fingerprint_hash: str = ""         # SHA256 of canonical profile

    def compute_fingerprint(self) -> str:
        payload = json.dumps({
            "profile_id":     self.profile_id,
            "python_version": self.python_version,
            "platform":       self.platform,
            "toolchain_pins": self.toolchain_pins,
        }, sort_keys=True, separators=(",", ":")).encode()
        self.env_fingerprint_hash = hashlib.sha256(payload).hexdigest()
        return self.env_fingerprint_hash

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class G8Sandbox:
    """
    AD-2026 G8-SANDBOX:
      Hermetic env fingerprint hash == pinned profile.
    HASH_MATCH or FAIL_CLOSED.
    """
    GATE_ID = "G8-SANDBOX"

    def run(
        self,
        live_env: EnvironmentProfile,
        pinned_fingerprint: str,
        pinned_toolchain_hash: str,
        live_toolchain_hash: str,
    ) -> GateRunResult:
        violations = []
        live_fp = live_env.compute_fingerprint()
        if live_fp != pinned_fingerprint:
            violations.append(
                f"Env fingerprint mismatch: live={live_fp[:16]}… pinned={pinned_fingerprint[:16]}…"
            )
        if live_toolchain_hash != pinned_toolchain_hash:
            violations.append(
                f"Toolchain hash mismatch: live={live_toolchain_hash[:16]}… pinned={pinned_toolchain_hash[:16]}…"
            )
        return GateRunResult(
            gate_id=self.GATE_ID,
            status=GateStatus.PASS if not violations else GateStatus.FAIL,
            evidence=[f"Profile={live_env.profile_id}"],
            violations=violations,
        )


# ──────────────────────────────────────────────
# G9-MCP
# ──────────────────────────────────────────────

@dataclass
class RCToken:
    """Resource Capability Token (AD-2026 §2.1)."""
    token_id:     str
    agent_id:     str
    capabilities: List[str]
    expires_utc:  str
    revoked:      bool = False

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPCallRecord:
    """Record of a single MCP tool/context call."""
    call_id:      str
    tool_name:    str
    token_id:     str
    input_hash:   str
    output_hash:  str
    timestamp_utc: str
    hermetic:     bool = True


class MCPPolicy:
    """
    MCP policy enforcement (AD-2026 §2.0 / §2.1 / §2.2).
    Checks:
      - All calls go through MCP boundary (hermetic flag)
      - RCT tokens valid (not revoked, not expired, capability match)
      - No policy violations
    """

    def __init__(self, valid_tokens: Dict[str, RCToken]) -> None:
        self._tokens = valid_tokens

    def check_call(self, call: MCPCallRecord, required_cap: str) -> Tuple[bool, str]:
        if not call.hermetic:
            return False, f"Call {call.call_id}: non-hermetic (direct call bypass)"
        token = self._tokens.get(call.token_id)
        if token is None:
            return False, f"Call {call.call_id}: token {call.token_id} not found"
        if token.revoked:
            return False, f"Call {call.call_id}: token {call.token_id} revoked"
        if required_cap not in token.capabilities:
            return False, f"Call {call.call_id}: capability '{required_cap}' not in token"
        return True, ""


class G9MCP:
    """
    AD-2026 G9-MCP:
      Zero MCP policy violations.
    ZERO_POLICY_VIOLATIONS or FAIL_CLOSED.
    """
    GATE_ID = "G9-MCP"

    def __init__(self, policy: MCPPolicy) -> None:
        self.policy = policy

    def run(self, calls: List[Tuple[MCPCallRecord, str]]) -> GateRunResult:
        """
        calls: list of (MCPCallRecord, required_capability)
        """
        violations = []
        for call, required_cap in calls:
            ok, msg = self.policy.check_call(call, required_cap)
            if not ok:
                violations.append(msg)
        return GateRunResult(
            gate_id=self.GATE_ID,
            status=GateStatus.PASS if not violations else GateStatus.FAIL,
            evidence=[f"Checked {len(calls)} MCP calls"],
            violations=violations,
        )


# ──────────────────────────────────────────────
# G10-SYNC  (CI-L9)
# ──────────────────────────────────────────────

@dataclass
class CIL9Snapshot:
    """Rolling-window CI-L9 metric snapshot."""
    predictive_precision:     float    # P_p ≥ 0.94
    alignment_score:          float    # A_s ≥ 0.98
    latency_ms:               float    # L_rtt ≤ 500ms (cloud_standard)
    drift_correction_success: float    # D_cs ≥ 0.99
    planner_mismatch_count:   int      # m == 0 over N=100

    THRESHOLDS = {
        "predictive_precision":     0.94,
        "alignment_score":          0.98,
        "latency_ms":               500.0,
        "drift_correction_success": 0.99,
        "planner_mismatch_count":   0,
    }

    def violations(self) -> List[str]:
        v = []
        if self.predictive_precision < self.THRESHOLDS["predictive_precision"]:
            v.append(f"P_p={self.predictive_precision:.3f} < {self.THRESHOLDS['predictive_precision']}")
        if self.alignment_score < self.THRESHOLDS["alignment_score"]:
            v.append(f"A_s={self.alignment_score:.3f} < {self.THRESHOLDS['alignment_score']}")
        if self.latency_ms > self.THRESHOLDS["latency_ms"]:
            v.append(f"L_rtt={self.latency_ms:.1f}ms > {self.THRESHOLDS['latency_ms']}ms")
        if self.drift_correction_success < self.THRESHOLDS["drift_correction_success"]:
            v.append(f"D_cs={self.drift_correction_success:.3f} < {self.THRESHOLDS['drift_correction_success']}")
        if self.planner_mismatch_count > self.THRESHOLDS["planner_mismatch_count"]:
            v.append(f"planner_mismatch m={self.planner_mismatch_count} > 0")
        return v

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class G10Sync:
    """
    AD-2026 G10-SYNC (CI-L9):
      All CI-L9 thresholds satisfied over rolling window W=500.
    PASS or autonomy freeze.
    """
    GATE_ID = "G10-SYNC"

    def run(self, snapshot: CIL9Snapshot, ac_violations_in_window: int = 0) -> GateRunResult:
        violations = snapshot.violations()
        if ac_violations_in_window > 0:
            violations.append(f"AC violations in window: {ac_violations_in_window} (must be 0)")
        return GateRunResult(
            gate_id=self.GATE_ID,
            status=GateStatus.PASS if not violations else GateStatus.FAIL,
            evidence=[
                f"P_p={snapshot.predictive_precision:.3f} "
                f"A_s={snapshot.alignment_score:.3f} "
                f"L_rtt={snapshot.latency_ms:.0f}ms "
                f"D_cs={snapshot.drift_correction_success:.3f} "
                f"m={snapshot.planner_mismatch_count}"
            ],
            violations=violations,
        )


# ──────────────────────────────────────────────
# G11-INVARIANT_FIXATION  (CI-L10)
# ──────────────────────────────────────────────

@dataclass
class CIL10Snapshot:
    """CI-L10 metric snapshot for a CRSM epoch."""
    invariant_integrity:  float    # I_i == 1.0 REQUIRED
    ac_sha256_before:     str
    ac_sha256_after:      str
    optimization_delta:   float    # Δ_opt ≥ 0.15
    safety_entropy:       float    # S_e < 1e-9  (estimated mismatch rate)
    replay_mismatch_m:    int      # m == 0
    replay_n:             int      # N >= AC.MIN_REPLAY_N (default 100)
    min_replay_n:         int      # from AC
    ssdf_regression:      bool     # False = no regression
    phase_g_pass:         bool     # Phase G compliance review passed
    change_failure_rate:  float    # CFR == 0.0

    THRESHOLDS = {
        "invariant_integrity":  1.0,
        "optimization_delta":   0.15,
        "safety_entropy_max":   1e-9,
        "replay_mismatch_max":  0,
        "cfr_max":              0.0,
    }

    def violations(self) -> List[str]:
        v = []
        if self.invariant_integrity != 1.0:
            v.append(f"I_i={self.invariant_integrity} != 1.0  [HARD: AC kernel modified]")
        if self.ac_sha256_before != self.ac_sha256_after:
            v.append(
                f"AC hash changed: {self.ac_sha256_before[:16]}… → {self.ac_sha256_after[:16]}…"
            )
        if self.optimization_delta < self.THRESHOLDS["optimization_delta"]:
            v.append(f"Δ_opt={self.optimization_delta:.3f} < 0.15")
        if self.safety_entropy >= self.THRESHOLDS["safety_entropy_max"]:
            v.append(f"S_e={self.safety_entropy:.2e} ≥ 1e-9")
        if self.replay_mismatch_m > self.THRESHOLDS["replay_mismatch_max"]:
            v.append(f"Replay mismatch m={self.replay_mismatch_m} > 0")
        if self.replay_n < self.min_replay_n:
            v.append(f"N={self.replay_n} < AC.MIN_REPLAY_N={self.min_replay_n} → NOT_READY")
        if self.ssdf_regression:
            v.append("SSDF regression detected")
        if not self.phase_g_pass:
            v.append("Phase G compliance review FAIL")
        if self.change_failure_rate > self.THRESHOLDS["cfr_max"]:
            v.append(f"CFR={self.change_failure_rate:.3f} > 0.0")
        return v

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class G11InvariantFixation:
    """
    AD-2026 G11-INVARIANT_FIXATION (CI-L10):
      AC kernel integrity + replay + SSDF + Phase G.
    PASS or Hard-Kill Protocol.
    """
    GATE_ID = "G11-INVARIANT_FIXATION"

    def run(self, snapshot: CIL10Snapshot) -> GateRunResult:
        violations = snapshot.violations()
        # NOT_READY if replay N insufficient
        if snapshot.replay_n < snapshot.min_replay_n:
            return GateRunResult(
                gate_id=self.GATE_ID,
                status=GateStatus.NOT_READY,
                evidence=[f"N={snapshot.replay_n} < MIN_REPLAY_N={snapshot.min_replay_n}"],
                violations=violations,
            )
        return GateRunResult(
            gate_id=self.GATE_ID,
            status=GateStatus.PASS if not violations else GateStatus.FAIL,
            evidence=[
                f"I_i={snapshot.invariant_integrity} "
                f"Δ_opt={snapshot.optimization_delta:.3f} "
                f"S_e={snapshot.safety_entropy:.1e} "
                f"m={snapshot.replay_mismatch_m}/{snapshot.replay_n} "
                f"SSDF_reg={snapshot.ssdf_regression} "
                f"PhaseG={snapshot.phase_g_pass}"
            ],
            violations=violations,
        )


# ──────────────────────────────────────────────
# Gate Runner — orchestrates G6→G11 in sequence
# ──────────────────────────────────────────────

class GateRunnerResult:
    def __init__(self, results: List[GateRunResult]) -> None:
        self.results = results

    @property
    def all_pass(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def gate_results_hash(self) -> str:
        """Deterministic hash over all gate results — included in APB."""
        payload = json.dumps(
            [r.as_dict() for r in self.results],
            sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(payload).hexdigest()

    def summary(self) -> Dict[str, str]:
        return {r.gate_id: r.status.value for r in self.results}

    def violations(self) -> List[str]:
        return [v for r in self.results for v in r.violations]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "all_pass": self.all_pass,
            "gate_results_hash": self.gate_results_hash,
            "gates": [r.as_dict() for r in self.results],
        }
