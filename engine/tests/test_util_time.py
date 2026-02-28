from __future__ import annotations

from datetime import datetime, timezone

from exoneural_governor.util import utc_now_iso


def test_utc_now_iso_uses_injected_clock() -> None:
    fixed = datetime(2026, 2, 28, 16, 0, 1, 987654, tzinfo=timezone.utc)
    assert utc_now_iso(now=fixed) == "2026-02-28T16:00:01Z"
