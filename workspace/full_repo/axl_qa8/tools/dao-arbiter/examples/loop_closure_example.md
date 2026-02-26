# Loop-closure example (realistic DAO cycle)

This walkthrough demonstrates a *real* DAO loop where the **truth plane** (CI/local verifier) blocks closure until the proof is updated.

## Scenario

You edit `README.md` (control-plane documentation), but forget to update `examples/PROOF_BUNDLE.example.json`, which contains SHA-256 hashes for key artifacts. The truth-plane check fails with a hash mismatch.

---

## 1) FAIL — capture as FAIL_PACKET

**Observed failing check:** `verify_repo`  
**Local reproduction:**
```bash
pip install jsonschema
python scripts/verify_repo.py
```

**Typical failure extract (verbatim):**
```
ERROR: hash mismatch for README.md
  expected: <...>
  got:      <...>
```

A minimal FAIL_PACKET (see also `examples/FAIL_PACKET.example.json`):

```json
{
  "check_name": "verify_repo",
  "error_extract": "ERROR: hash mismatch for README.md\n  expected: <...>\n  got:      <...>",
  "repro_cmd": "pip install jsonschema && python scripts/verify_repo.py",
  "done_when": "scripts/verify_repo.py exits with code 0 and prints OK",
  "evidence_ptr": "https://example.org/ci/run/12345"
}
```

---

## 2) FIX — update proof bundle hashes

Recompute the README hash and update the proof bundle example.

Example command to compute a SHA-256 (Linux/macOS):
```bash
python -c "import hashlib;print(hashlib.sha256(open('README.md','rb').read()).hexdigest())"
```

Then update:
- `examples/PROOF_BUNDLE.example.json.artifact_hashes['README.md']`

---

## 3) PROVE — re-run truth-plane checks

```bash
python scripts/verify_repo.py
```

Expected:
```
OK: schemas valid; proof bundle artifact hashes match.
```

---

## 4) CHECKPOINT — record closure

Create a commit referencing the closure:
```bash
git add README.md examples/PROOF_BUNDLE.example.json
git commit -m "chore: close loop (update proof bundle hashes)"
```

Optionally, mint a real PROOF_BUNDLE for the commit (instead of an example) and attach the CI run URL as immutable evidence.

---

## Why this matters

The loop demonstrates a key invariant:

> If the artifact changes, the proof must change too — and CI should enforce that relationship.
