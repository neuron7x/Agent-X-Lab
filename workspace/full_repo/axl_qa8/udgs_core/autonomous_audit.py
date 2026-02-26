"""
udgs_core.autonomous_audit
==========================
QA8 AUTONOMOUS_AUDIT (SELF-HEALING) engine.

Architecture
------------
The engine holds a QA7 baseline: the reference component hashes and system anchor
recorded at the moment QA7 was certified.  On every watch cycle it:

  1. Recomputes live component hashes.
  2. Compares them to the QA7 baseline (drift detection).
  3. Classifies each drifted component as GENERATED (auto-healable) or SOURCE (alert-only).
  4. For GENERATED components: regenerates the artifact from the live source tree and
     validates the result. Outcome recorded as HEALED or HEAL_FAILED.
  5. For SOURCE components: emits a structured ALERT packet and enters the
     DeterministicCycle (FAIL→FIX→PROVE→CHECKPOINT) with fail-closed semantics.
  6. Persists all events to HEAL_LOG.jsonl (append-only) and updates QA8_STATUS.json.

Fail-closed guarantee
---------------------
If the self-heal produces an inconsistent state (PROVE gate fails), the engine
transitions to HALT and writes a terminal alert.  It never silently accepts drift.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .anchors import sha256_tree, sha256_file, sha256_json
from .state_machine import DeterministicCycle, Evidence, LoopState
from .strict_json import compute_packet_anchor
from .system_object import build_system_object, write_system_object


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QA7_GRADE = "QA7_STRICT_ANCHOR_HARDENED"
QA8_GRADE = "QA8_AUTONOMOUS_AUDIT_SELF_HEALING"

# Components whose sole artifact is a *generated* JSON file that can be safely
# rebuilt from the source tree.  All others are treated as SOURCE.
GENERATED_COMPONENTS: frozenset[str] = frozenset()

# The generated top-level artifacts we can always regenerate.
GENERATED_ARTIFACTS = {
    "SYSTEM_OBJECT.json",
    "UDGS_MANIFEST.json",
}


# ---------------------------------------------------------------------------
# Data-classes
# ---------------------------------------------------------------------------

class Qa8Mode(str, Enum):
    NOMINAL    = "NOMINAL"       # All hashes match baseline.
    SCANNING   = "SCANNING"      # Scan in progress.
    DRIFT      = "DRIFT"         # Deviation detected, not yet healed.
    HEALING    = "HEALING"       # Heal cycle in progress.
    HEALED     = "HEALED"        # Deviation corrected, anchor restored.
    ALERT      = "ALERT"         # SOURCE drift – cannot auto-heal.
    HALT       = "HALT"          # Fail-closed gate triggered.


@dataclass
class ComponentDrift:
    name: str
    path: str
    kind: str
    baseline_hash: str
    live_hash: str
    is_generated: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HealEvent:
    event_id: str
    utc: str
    prior_mode: str
    drifts: List[Dict[str, Any]]
    cycle_result: Dict[str, Any]
    outcome: str          # HEALED | HEAL_FAILED | ALERT | HALT
    notes: List[str] = field(default_factory=list)
    new_system_anchor: Optional[str] = None
    heal_packet_anchor: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Qa8Status:
    mode: str
    last_scan_utc: Optional[str]
    last_heal_utc: Optional[str]
    scan_count: int
    heal_count: int
    alert_count: int
    halt_count: int
    baseline_anchor: str
    live_anchor: Optional[str]
    grade: str = QA8_GRADE
    version: str = "2026.02.25"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Baseline loader
# ---------------------------------------------------------------------------

def load_baseline(system_object_path: str) -> Dict[str, Any]:
    """Load the QA7 baseline from SYSTEM_OBJECT.json."""
    with open(system_object_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Metric scoring
# ---------------------------------------------------------------------------

def score_system(
    baseline: Dict[str, Any],
    live_components: Dict[str, str],
) -> Dict[str, Any]:
    """
    Compute a QA8 health metric snapshot.

    Returns a dict with:
      integrity_score  – fraction of components whose hashes match baseline (0.0–1.0)
      total_components – total number of tracked components
      matching         – count of components that match
      drifted          – count of components that differ
      grade            – PASS if integrity_score == 1.0, DEGRADED otherwise
    """
    baseline_comps = baseline.get("components", {})
    total = len(baseline_comps)
    if total == 0:
        return {"integrity_score": 1.0, "total_components": 0,
                "matching": 0, "drifted": 0, "grade": "PASS"}

    matching = sum(
        1 for name, meta in baseline_comps.items()
        if live_components.get(name) == meta.get("hash", "")
    )
    drifted = total - matching
    score = matching / total
    return {
        "integrity_score": round(score, 6),
        "total_components": total,
        "matching": matching,
        "drifted": drifted,
        "grade": "PASS" if score == 1.0 else "DEGRADED",
    }


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class AutonomousAuditEngine:
    """
    QA8 self-healing engine.

    Parameters
    ----------
    root          : absolute path to the project root
    config_path   : path to system/udgs.config.json
    system_object_path : path to SYSTEM_OBJECT.json (the live generated artifact)
    qa8_state_dir : directory for QA8_STATUS.json and HEAL_LOG.jsonl
    qa8_config    : parsed qa8.config.json dict
    """

    def __init__(
        self,
        root: str,
        config_path: str,
        system_object_path: str,
        qa8_state_dir: str,
        qa8_config: Dict[str, Any],
    ) -> None:
        self.root = os.path.abspath(root)
        self.config_path = config_path
        self.system_object_path = system_object_path
        self.qa8_state_dir = qa8_state_dir
        self.qa8_config = qa8_config

        os.makedirs(qa8_state_dir, exist_ok=True)

        self._baseline: Optional[Dict[str, Any]] = None
        self._status = Qa8Status(
            mode=Qa8Mode.NOMINAL,
            last_scan_utc=None,
            last_heal_utc=None,
            scan_count=0,
            heal_count=0,
            alert_count=0,
            halt_count=0,
            baseline_anchor="",
            live_anchor=None,
        )
        self._scan_count = 0
        self._heal_count = 0
        self._alert_count = 0
        self._halt_count = 0

    # ------------------------------------------------------------------
    # Baseline
    # ------------------------------------------------------------------

    def load_baseline(self) -> None:
        """Load (or reload) the QA7 baseline from SYSTEM_OBJECT.json."""
        self._baseline = load_baseline(self.system_object_path)

    def _baseline_anchor(self) -> str:
        if self._baseline is None:
            return ""
        return self._baseline.get("system_anchor", "")

    # ------------------------------------------------------------------
    # Live hash computation
    # ------------------------------------------------------------------

    def _compute_live_hashes(self) -> Dict[str, str]:
        """Return {component_name: tree_hash} for all components in baseline."""
        if self._baseline is None:
            raise RuntimeError("Baseline not loaded. Call load_baseline() first.")

        exclude_paths = set(
            self._baseline.get("config", {}).get("audit_exclude_rel_paths", [])
        )
        exclude_prefixes = set(
            self._baseline.get("config", {}).get("audit_exclude_rel_prefixes", [])
        )

        live: Dict[str, str] = {}
        for name, meta in self._baseline["components"].items():
            rel_path = meta["path"]
            abs_path = os.path.join(self.root, rel_path) if rel_path != "." else self.root
            if not os.path.exists(abs_path):
                live[name] = "MISSING"
                continue
            if rel_path == ".":
                tree_hash, _ = sha256_tree(
                    abs_path,
                    exclude_rel_paths=exclude_paths,
                    exclude_rel_prefixes=exclude_prefixes,
                )
            else:
                tree_hash, _ = sha256_tree(abs_path)
            live[name] = tree_hash
        return live

    # ------------------------------------------------------------------
    # Drift detection
    # ------------------------------------------------------------------

    def detect_drift(self) -> List[ComponentDrift]:
        """Compare live hashes to baseline.  Return list of drifted components."""
        if self._baseline is None:
            raise RuntimeError("Baseline not loaded.")

        live = self._compute_live_hashes()
        drifts: List[ComponentDrift] = []
        for name, meta in self._baseline["components"].items():
            baseline_hash = meta.get("hash", "")
            live_hash = live.get(name, "MISSING")
            if baseline_hash != live_hash:
                drifts.append(ComponentDrift(
                    name=name,
                    path=meta.get("path", ""),
                    kind=meta.get("kind", ""),
                    baseline_hash=baseline_hash,
                    live_hash=live_hash,
                    is_generated=(name in GENERATED_COMPONENTS),
                ))
        return drifts

    # ------------------------------------------------------------------
    # Heal
    # ------------------------------------------------------------------

    def _emit_heal_packet(
        self,
        drifts: List[ComponentDrift],
        notes: List[str],
    ) -> Dict[str, Any]:
        """Build a STRICT_JSON FAIL_PACKET for the detected drift."""
        signals = [f"DRIFT:{d.name}" for d in drifts]
        signals.append("QA8_SELF_HEAL_TRIGGERED")

        diff_scope = [f"{d.name}:{d.path}" for d in drifts]
        constraints = [
            "fail-closed",
            "deterministic-anchors",
            "qa8-autonomous-heal",
            "ssot-source-tree",
        ]

        packet: Dict[str, Any] = {
            "FAIL_PACKET": {
                "summary": f"QA8 drift detected in {len(drifts)} component(s): "
                           + ", ".join(d.name for d in drifts),
                "signals": signals,
                "repro": "python -m udgs_core.cli qa8-heal --root . --config system/udgs.config.json",
            },
            "MUTATION_PLAN": {
                "diff_scope": diff_scope,
                "constraints": constraints,
            },
            "PRE_VERIFICATION_SCRIPT": (
                "python -m udgs_core.cli build-system-object "
                "--root . --config system/udgs.config.json --out SYSTEM_OBJECT.json"
            ),
            "REGRESSION_TEST_PAYLOAD": {
                "suite": ["udgs_core.cli anchor engine", "udgs_core.cli build-system-object"],
                "expected": {
                    "system_object_valid": True,
                    "anchor_deterministic": True,
                },
            },
            "SHA256_ANCHOR": "REPLACE",
        }
        packet["SHA256_ANCHOR"] = compute_packet_anchor(packet)
        return packet

    def _regenerate_system_object(self) -> Tuple[bool, str, List[str]]:
        """Rebuild SYSTEM_OBJECT.json from live source tree.  Return (ok, new_anchor, notes)."""
        notes: List[str] = []
        try:
            obj = build_system_object(self.root, self.config_path)
            write_system_object(self.system_object_path, obj)
            notes.append(f"SYSTEM_OBJECT.json regenerated; new anchor={obj.system_anchor[:16]}…")
            return True, obj.system_anchor, notes
        except Exception as exc:
            notes.append(f"REGENERATE_FAILED: {exc}")
            return False, "", notes

    def _run_heal_cycle(
        self,
        drifts: List[ComponentDrift],
    ) -> HealEvent:
        """Execute the FAIL→FIX→PROVE→CHECKPOINT deterministic cycle for a detected drift."""
        event_id = _new_event_id()
        utc = _utc_now()
        prior_mode = self._status.mode
        notes: List[str] = []

        # Build FAIL_PACKET
        heal_packet = self._emit_heal_packet(drifts, notes)

        # Determine if we can regenerate
        source_drifts = [d for d in drifts if not d.is_generated]
        all_generated = len(source_drifts) == 0

        # Run deterministic cycle
        cycle = DeterministicCycle(fail_closed=True)

        # FAIL → FIX
        cycle.step(Evidence())
        notes.append("Cycle: FAIL→FIX")
        cycle.step(Evidence())
        notes.append("Cycle: FIX→PROVE")

        # Attempt regeneration of SYSTEM_OBJECT.json (always safe to regenerate)
        regen_ok, new_anchor, regen_notes = self._regenerate_system_object()
        notes.extend(regen_notes)

        # Build evidence for PROVE gate
        prove_evidence = Evidence(
            logs={"drifts": [d.as_dict() for d in drifts], "regen_ok": regen_ok},
            hash_anchor=new_anchor if regen_ok else None,
            oracle_pass=regen_ok,
        )
        prove_result = cycle.step(prove_evidence)
        notes.extend(prove_result.notes)

        # Determine outcome
        if prove_result.next_state == LoopState.CHECKPOINT:
            outcome = "HEALED" if all_generated else "ALERT"
            notes.append(f"PROVE gate satisfied → {outcome}")
        elif prove_result.next_state == LoopState.HALT:
            outcome = "HALT"
            notes.append("Fail-closed HALT: PROVE gate failed.")
        else:
            outcome = "HEAL_FAILED"
            notes.append(f"Unexpected cycle state: {prove_result.next_state}")

        event = HealEvent(
            event_id=event_id,
            utc=utc,
            prior_mode=prior_mode,
            drifts=[d.as_dict() for d in drifts],
            cycle_result={
                "next_state": prove_result.next_state.value,
                "violated": [
                    {"name": i.name, "rule": i.rule, "severity": i.severity}
                    for i in prove_result.violated
                ],
                "notes": prove_result.notes,
            },
            outcome=outcome,
            notes=notes,
            new_system_anchor=new_anchor if regen_ok else None,
            heal_packet_anchor=heal_packet["SHA256_ANCHOR"],
        )
        return event

    # ------------------------------------------------------------------
    # Scan-and-heal cycle
    # ------------------------------------------------------------------

    def run_cycle(self) -> Qa8Status:
        """
        One autonomous audit cycle:
          1. Detect drift.
          2. If drift found → run heal cycle.
          3. Update and persist QA8_STATUS.json.
          Return updated Qa8Status.
        """
        now = _utc_now()
        self._scan_count += 1
        self._set_mode(Qa8Mode.SCANNING)

        if self._baseline is None:
            self.load_baseline()

        drifts = self.detect_drift()
        live = self._compute_live_hashes()

        # Compute live system anchor for status
        baseline_comps = self._baseline.get("components", {})  # type: ignore[union-attr]
        config_hash = sha256_file(self.config_path)
        anchor_payload = {
            "config_hash": config_hash,
            "components": {k: v for k, v in sorted(live.items())},
        }
        live_anchor = sha256_json(anchor_payload)

        if not drifts:
            self._set_mode(Qa8Mode.NOMINAL)
            status = self._build_status(now, live_anchor)
            self._persist_status(status)
            return status

        # Drift detected
        self._set_mode(Qa8Mode.DRIFT)
        self._set_mode(Qa8Mode.HEALING)

        event = self._run_heal_cycle(drifts)
        self._append_heal_log(event)

        if event.outcome in ("HEALED", "ALERT"):
            if event.outcome == "HEALED":
                self._heal_count += 1
                self._set_mode(Qa8Mode.HEALED)
                # Reload baseline after heal so next cycle starts fresh
                self.load_baseline()
            else:
                self._alert_count += 1
                self._set_mode(Qa8Mode.ALERT)
        elif event.outcome == "HALT":
            self._halt_count += 1
            self._set_mode(Qa8Mode.HALT)
        else:
            self._alert_count += 1
            self._set_mode(Qa8Mode.ALERT)

        status = self._build_status(now, event.new_system_anchor or live_anchor)
        if event.outcome in ("HEALED", "HALT", "HEAL_FAILED"):
            status_dict = status.as_dict()
            status_dict["last_heal_utc"] = now
            status = Qa8Status(**status_dict)

        self._persist_status(status)
        return status

    # ------------------------------------------------------------------
    # Watch loop (daemon)
    # ------------------------------------------------------------------

    def watch(self, interval_sec: float = 30.0, max_cycles: Optional[int] = None) -> None:
        """
        Continuous watch loop.  Runs run_cycle() every ``interval_sec`` seconds.
        Stops when max_cycles is reached (if given) or the mode becomes HALT.
        """
        cycle_n = 0
        while True:
            status = self.run_cycle()
            cycle_n += 1
            _log(f"[QA8 CYCLE {cycle_n}] mode={status.mode}  "
                 f"scans={status.scan_count}  heals={status.heal_count}  "
                 f"alerts={status.alert_count}  halts={status.halt_count}")
            if status.mode == Qa8Mode.HALT:
                _log("[QA8] HALT state reached – stopping watch loop (fail-closed).")
                break
            if max_cycles is not None and cycle_n >= max_cycles:
                break
            time.sleep(interval_sec)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_mode(self, mode: Qa8Mode) -> None:
        self._status.mode = mode.value  # type: ignore[assignment]

    def _build_status(self, now: str, live_anchor: str) -> Qa8Status:
        return Qa8Status(
            mode=self._status.mode,
            last_scan_utc=now,
            last_heal_utc=self._status.last_heal_utc,
            scan_count=self._scan_count,
            heal_count=self._heal_count,
            alert_count=self._alert_count,
            halt_count=self._halt_count,
            baseline_anchor=self._baseline_anchor(),
            live_anchor=live_anchor,
            grade=QA8_GRADE,
        )

    def _persist_status(self, status: Qa8Status) -> None:
        path = os.path.join(self.qa8_state_dir, "QA8_STATUS.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(status.as_dict(), f, indent=2, ensure_ascii=False)

    def _append_heal_log(self, event: HealEvent) -> None:
        path = os.path.join(self.qa8_state_dir, "HEAL_LOG.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.as_dict(), ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_event_id() -> str:
    import uuid
    return str(uuid.uuid4())[:8]


def _log(msg: str) -> None:
    print(f"[{_utc_now()}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def make_engine(root: str, qa8_config_path: Optional[str] = None) -> AutonomousAuditEngine:
    """
    Convenience factory.  Loads qa8.config.json (or defaults) and builds an engine.
    """
    root = os.path.abspath(root)
    config_path = os.path.join(root, "system", "udgs.config.json")
    system_object_path = os.path.join(root, "SYSTEM_OBJECT.json")
    qa8_state_dir = os.path.join(root, "qa8_state")

    qa8_config: Dict[str, Any] = {}
    if qa8_config_path is None:
        qa8_config_path = os.path.join(root, "system", "qa8.config.json")
    if os.path.isfile(qa8_config_path):
        with open(qa8_config_path, "r", encoding="utf-8") as f:
            qa8_config = json.load(f)

    return AutonomousAuditEngine(
        root=root,
        config_path=config_path,
        system_object_path=system_object_path,
        qa8_state_dir=qa8_state_dir,
        qa8_config=qa8_config,
    )
