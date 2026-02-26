# Threat Model (Skeleton)

## Trust boundaries
- Browser/UI boundary
- Worker/BFF boundary
- GitHub API boundary
- Storage boundary

## Identity model (placeholder)
- To be completed in a follow-up PR with principal types, trust assumptions, and authorization mapping.

## Secrets policy
- `VITE_*` variables must never contain secrets.
- Secrets must not be committed to tracked files.
