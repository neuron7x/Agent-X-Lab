from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exoneural_governor.redaction import redact_tree


def test_redact_tree_returns_changed_files_in_stable_lexicographic_order(tmp_path):
    root = tmp_path / "evidence"
    (root / "zeta").mkdir(parents=True)
    (root / "alpha").mkdir(parents=True)

    files_with_secret = [
        root / "zeta" / "b.log",
        root / "alpha" / "a.md",
        root / "alpha" / "c.TXT",
    ]
    ignored_file = root / "alpha" / "ignored.bin"

    for path in files_with_secret:
        path.write_text("token=SECRET\n", encoding="utf-8")
    ignored_file.write_text("token=SECRET\n", encoding="utf-8")

    expected = [
        str(path) for path in sorted(files_with_secret, key=lambda x: x.as_posix())
    ]

    first = redact_tree(root, ["SECRET"])

    for path in files_with_secret:
        path.write_text("token=SECRET\n", encoding="utf-8")

    second = redact_tree(root, ["SECRET"])

    assert first == expected
    assert second == expected
