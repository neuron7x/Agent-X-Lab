# Error Codes

## Documented deterministic errors

- `E_BACKEND_TORCH_MISSING`
  - Meaning: accelerated backend requested but torch is unavailable.
  - Message: `E_BACKEND_TORCH_MISSING: accelerated backend requires torch. Fix: install torch or use backend='reference'.`
  - Fix: install torch or set `backend='reference'`.
- `E_NO_GIT_NO_BUILD_ID`
  - Meaning: git commit is unavailable and BUILD_ID was not provided.
  - Message: `E_NO_GIT_NO_BUILD_ID: git commit unavailable; set BUILD_ID for deterministic provenance id.`
  - Fix: set `BUILD_ID` in CI or provide git metadata.

README links to this file as the SSOT for user-facing deterministic error codes.
