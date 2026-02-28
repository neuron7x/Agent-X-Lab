# CI Tools

## action_pin_audit.py

Deterministic workflow action pin scanner.

```bash
python3 tools/ci/action_pin_audit.py --fail
```

Rules:
- scans `.github/workflows/*.yml`
- validates `uses: owner/repo@ref`
- requires full 40-hex SHA refs
- sorted output, non-zero exit on violation with `--fail`
