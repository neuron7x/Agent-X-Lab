"""
DAO-LIFEBOOK — Evidence & Checkpointing (Axiom A5).

Your memory is externalized: proof bundles, hashes, logs, PR links.
If you can't replay it tomorrow, it wasn't done.
"""

from __future__ import annotations

import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import (
    ArtifactRef,
    CheckResult,
    DiffSummary,
    LocalGateResult,
    LoopState,
    Phase,
    ProofBundle,
    TimeSpan,
)

logger = logging.getLogger("dao.evidence")

_DEFAULT_STORE = Path.home() / ".dao_lifebook" / "evidence"


class ProofAssembler:
    """
    Builds a ProofBundle from loop state and CI results.

    The bundle is immutable once assembled — it's an evidence record.
    """

    __slots__ = ()

    @staticmethod
    def assemble(
        *,
        pr_url: str,
        commit_sha: str,
        check_results: list[CheckResult],
        diff_summary: DiffSummary,
        t_start: datetime,
        t_green: datetime | None = None,
        local_gates: list[LocalGateResult] | None = None,
        artifacts: list[ArtifactRef] | None = None,
    ) -> ProofBundle:
        """Assemble a proof bundle from raw evidence."""
        return ProofBundle(
            pr_url=pr_url,
            commit_sha=commit_sha,
            required_checks_final=check_results,
            local_gates=local_gates or [],
            artifacts=artifacts or [],
            diff_summary=diff_summary,
            time=TimeSpan(
                t_start=t_start,
                t_green=t_green,
            ),
        )

    @staticmethod
    def validate(bundle: ProofBundle) -> list[str]:
        """
        Validate bundle completeness.
        Returns list of issues (empty = valid).
        """
        issues: list[str] = []

        if not bundle.pr_url:
            issues.append("Missing PR URL")
        if not bundle.commit_sha:
            issues.append("Missing commit SHA")
        if not bundle.required_checks_final:
            issues.append("No check results recorded")
        if not bundle.all_green:
            non_green = [
                c.name for c in bundle.required_checks_final
                if not c.status.is_green
            ]
            issues.append(f"Non-green checks: {non_green}")
        if bundle.time.t_green is None:
            issues.append("t_green not recorded (no proven completion)")

        return issues


class CheckpointStore:
    """
    Persistent checkpoint storage for proof bundles and loop states.

    Directory layout:
      <store_root>/
        bundles/
          <sha256>.json          — serialized ProofBundle
        states/
          <pr_number>_<iter>.json — serialized LoopState snapshot
        ledger.jsonl              — append-only proof hash log
    """

    __slots__ = ("_root",)

    def __init__(self, root: Path | str | None = None) -> None:
        self._root = Path(root) if root else _DEFAULT_STORE
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / "bundles").mkdir(exist_ok=True)
        (self._root / "states").mkdir(exist_ok=True)

    # ── Proof Bundles ─────────────────────────────────────────────────────

    def save_bundle(self, bundle: ProofBundle) -> str:
        """
        Persist a proof bundle. Returns its integrity hash.

        Idempotent: same bundle content → same hash → same file.
        """
        h = bundle.integrity_hash()
        path = self._root / "bundles" / f"{h}.json"
        if not path.exists():
            path.write_text(
                bundle.model_dump_json(indent=2),
                encoding="utf-8",
            )
            self._append_ledger(h, bundle.pr_url, bundle.commit_sha)
            logger.info("Bundle saved: %s", h[:12])
        return h

    def load_bundle(self, hash_prefix: str) -> ProofBundle | None:
        """Load a bundle by full or prefix hash."""
        bundle_dir = self._root / "bundles"
        for p in bundle_dir.glob(f"{hash_prefix}*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            return ProofBundle.model_validate(data)
        return None

    def list_bundles(self, limit: int = 50) -> list[dict[str, str]]:
        """List recent bundles from the ledger."""
        ledger_path = self._root / "ledger.jsonl"
        if not ledger_path.exists():
            return []
        lines = ledger_path.read_text(encoding="utf-8").strip().split("\n")
        entries: list[dict[str, str]] = []
        for line in reversed(lines[-limit:]):
            if line.strip():
                entries.append(json.loads(line))
        return entries

    # ── Loop State Snapshots ──────────────────────────────────────────────

    def save_state(self, state: LoopState, label: str = "") -> Path:
        """
        Snapshot current loop state to disk.

        Label defaults to phase + iteration.
        """
        if not label:
            label = f"{state.phase.value}_{state.iteration:04d}"
        path = self._root / "states" / f"{label}.json"
        path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )
        logger.info("State snapshot: %s", path.name)
        return path

    def load_state(self, label: str) -> LoopState | None:
        path = self._root / "states" / f"{label}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return LoopState.model_validate(data)

    def list_states(self) -> list[str]:
        state_dir = self._root / "states"
        return sorted(p.stem for p in state_dir.glob("*.json"))

    # ── Ledger (append-only) ──────────────────────────────────────────────

    def _append_ledger(self, h: str, pr_url: str, sha: str) -> None:
        ledger_path = self._root / "ledger.jsonl"
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "hash": h,
            "pr": pr_url,
            "sha": sha,
        }
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    # ── Artifact integrity ────────────────────────────────────────────────

    @staticmethod
    def verify_artifact(ref: ArtifactRef) -> bool:
        """Verify an artifact's SHA-256 matches the file on disk."""
        path = Path(ref.path)
        if not path.exists():
            return False
        if not ref.sha256:
            return True  # no hash to verify
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        return actual == ref.sha256

    def verify_bundle_artifacts(self, bundle: ProofBundle) -> list[str]:
        """Returns list of failed artifact verifications."""
        failures: list[str] = []
        for art in bundle.artifacts:
            if not self.verify_artifact(art):
                failures.append(f"Artifact mismatch or missing: {art.path}")
        return failures
