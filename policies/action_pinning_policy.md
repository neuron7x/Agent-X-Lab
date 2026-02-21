# Action pinning policy

- All remote GitHub Actions in `.github/workflows/*.yml` MUST be pinned to full 40-hex commit SHAs.
- Local actions (`./...`) are allowed and are exempt from SHA pinning.
- Tags (`@v*`), branches, and short SHAs are forbidden for remote actions.
