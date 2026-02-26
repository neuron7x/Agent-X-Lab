from __future__ import annotations

from pathlib import Path

from tools.verify_protocol_consistency import verify


def test_unknown_deficits_fail_and_are_reported_in_missing(tmp_path: Path) -> None:
    protocol = tmp_path / "protocol.yaml"
    protocol.write_text(
        """
deficits:
  - id: D1
protocol_plan:
  - step_id: S1
    fixes: [D1, D_UNKNOWN]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = verify(protocol)

    assert result["pass"] is False
    assert result["duplicate_deficits"] == []
    assert result["orphan_steps"] == []
    assert result["missing_deficits"] == ["D_UNKNOWN"]
