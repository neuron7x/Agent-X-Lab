from __future__ import annotations

import json
from pathlib import Path

from exoneural_governor.catalog import validate_catalog
from exoneural_governor.config import load_config
from exoneural_governor.vr import run_vr
from exoneural_governor.release import build_release


def test_catalog_ok():
    repo_root = Path(__file__).resolve().parents[1]
    rep = validate_catalog(repo_root)
    assert rep["ok"], rep


def test_vr_and_release(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    cfg = load_config(repo_root / "configs" / "sg.config.json")
    vr = run_vr(cfg, write_back=False)
    assert vr["status"] in ("RUN", "CALIBRATION_REQUIRED")
    rel = build_release(cfg)
    assert (repo_root / rel["zip_path"]).exists()
