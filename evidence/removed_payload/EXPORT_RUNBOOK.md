# Removed Payload Export Runbook

This runbook describes deterministic recovery of removed payload from git history.

## Preconditions
- Use the commit immediately before this hygiene change (`BASE_SHA`).
- Set deterministic environment:

```bash
export PYTHONHASHSEED=0 LC_ALL=C LANG=C TZ=UTC GIT_PAGER=cat PAGER=cat PYTHONDONTWRITEBYTECODE=1
```

## 1) Export removed trees

```bash
git archive --format=tar --output removed_payload.tar BASE_SHA archive artifacts/proof_bundle control-plane engine/.github/workflows
```

## 2) Extract

```bash
mkdir -p recovered_payload
tar -xf removed_payload.tar -C recovered_payload
```

## 3) Verify cryptographic manifest

```bash
python3 - <<'PY'
import json,hashlib
from pathlib import Path
m=json.loads(Path('evidence/removed_payload/REMOVAL_MANIFEST.json').read_text(encoding='utf-8'))
root=Path('recovered_payload')
for e in m['removed_files']:
    p=root/e['path']
    data=p.read_bytes()
    h=hashlib.sha256(data).hexdigest()
    assert h==e['sha256'], f'mismatch: {e["path"]}'
print('manifest verification passed')
PY
```
