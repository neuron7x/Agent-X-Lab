# GHTPO Evidence

| Gate | Result | Command |
|---|---|---|
| G00 | PASS | `python - <<'Y'
import yaml,glob
for p in glob.glob('.github/workflows/*.yml'): yaml.safe_load(open(p))
print('ok')
Y` |
| G01 | PASS | `for f in .github/workflows/*.yml; do grep -q '^permissions:' "$f" || exit 1; done` |
| G02 | FAIL | `! rg -n 'uses:\s*(gitleaks|reviewdog)/[^@]+@v?[0-9]+' .github/workflows` |
| G03 | PASS | `for f in .github/workflows/*.yml; do grep -q '^concurrency:' "$f" || exit 1; done` |
| G04 | PASS | `for f in .github/workflows/*.yml; do grep -q 'timeout-minutes:' "$f" || exit 1; done` |
| G05 | PASS | `rg -n 'cache: pip|cache-dependency-path' .github/workflows/ci.yml` |
| G06 | PASS | `rg -n 'status-check|needs:' .github/workflows/ci.yml` |
| G07 | PASS | `ruff check .` |
| G08 | PASS | `ruff format --check .` |
| G09 | PASS | `mypy .` |
| G11 | PASS | `python -m pip check` |
| G13 | PASS | `test -f .github/dependabot.yml` |
| G14 | PASS | `test -f SECURITY.md` |
| G15 | PASS | `test -f .github/CODEOWNERS` |
| G16 | PASS | `test -f .github/pull_request_template.md` |
| G17 | PASS | `ls .github/ISSUE_TEMPLATE/*.yml >/dev/null` |
| G18 | PASS | `rg -n badge README.md` |
| G19 | PASS | `rg -n '^ci:' Makefile` |
| G20 | FAIL | `git status --short` |
