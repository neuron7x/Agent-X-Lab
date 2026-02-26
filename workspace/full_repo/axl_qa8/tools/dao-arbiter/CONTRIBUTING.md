# Contributing

This repository is designed around loop-closure discipline:

`FAIL → FIX → PROVE → CHECKPOINT`

## Ground rules

- **Truth source:** CI/required checks are the reality oracle.
- **No “hand-wavy done”:** Every change must define an objective *done-when* condition.
- **Evidence-first:** Provide reproducible commands and artifacts.

## Workflow

1. **Capture a failure**
   - Create a `FAIL_PACKET` instance (see `FAIL_PACKET.json` and `examples/FAIL_PACKET.example.json`).
   - Minimum fields:
     - `check_name`
     - `error_extract` (exact lines; no paraphrase)
     - `repro_cmd`
     - `done_when` (binary pass condition)
     - `evidence_ptr` (link to CI run, log, or artifact)

2. **Implement the fix**
   - Keep the patch minimal and reviewable.
   - Prefer deterministic changes; avoid non-reproducible steps.

3. **Prove**
   - Produce a `PROOF_BUNDLE` instance (see `PROOF_BUNDLE.json` and `examples/PROOF_BUNDLE.example.json`).
   - Include:
     - real `commit_sha`
     - required checks status
     - artifact hashes (`sha256`)
     - timestamp of the first fully-green state

4. **Checkpoint**
   - Open a PR with:
     - the FAIL_PACKET (or link to it)
     - the PROOF_BUNDLE (or link to it)
     - a concise explanation of what changed and why

## PR checklist

- [ ] CI required checks are green
- [ ] Repro steps are included and work
- [ ] Schema examples remain valid JSON
- [ ] No placeholders / dummy SHAs / broken links
- [ ] Changes are minimal, auditable, and reversible if needed

## Security / safety notes

If your change touches external communications drafts (endorsement, safety outreach), keep claims factual and avoid unverifiable statements. Use the repository PDF and public links as the only sources unless explicitly validated.
