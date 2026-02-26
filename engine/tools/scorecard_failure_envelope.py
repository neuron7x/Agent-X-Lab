#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    p = Path("artifacts/security/scorecard-failure.sarif")
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ossf/scorecard-action",
                        "version": "v2.3.1",
                    }
                },
                "results": [
                    {
                        "level": "error",
                        "message": {
                            "text": "scorecard action failed before SARIF generation"
                        },
                        "properties": {
                            "status": "error",
                            "reason_code": "scorecard_action_failed_before_output",
                            "remediation": "inspect scorecard action logs and rerun after fixing the failing check",
                            "tool": {
                                "name": "ossf/scorecard-action",
                                "version": "v2.3.1",
                            },
                        },
                    }
                ],
            }
        ],
    }
    p.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    Path("artifacts/security/scorecard-results.sarif").write_text(
        p.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
