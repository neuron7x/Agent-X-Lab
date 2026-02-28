# 08 Security Gates

Security gate workflows:
- `Workflow Hygiene` (includes static action pin audit + API-based pinned-SHA validation).
- `CodeQL Analysis`.
- `Dependency Review`.
- `Secret Scan (Gitleaks)`.

Branch-protection policy uses `CI Supercheck` to enforce these checks contextually and fail closed.
