# Deployment runbook (dao-arbiter)

This runbook assumes you have:
- Git
- (optional) GitHub CLI (`gh`)
- Pandoc + XeLaTeX (for DOCX→PDF)

## 1) Convert preprint DOCX → PDF

```bash
pandoc DAO_Dopaminergic_Arbiter_Preprint_Vasylenko_2026.docx   -o Vasylenko_DAO_Arbiter_2026.pdf   --pdf-engine=xelatex   -V mainfont="DejaVu Serif"   -V sansfont="DejaVu Sans"   -V monofont="DejaVu Sans Mono"
```

## 2) Create GitHub account (if needed)

- Sign up on GitHub.
- Enable 2FA.
- Create an SSH key (recommended) and add it to GitHub.

## 3) Create the public repository

### Option A — GitHub CLI (recommended)

If you want a single command that creates the repo and pushes the current directory:

```bash
gh auth login
gh repo create dao-arbiter --public --source=. --remote=origin --push
```

### Option B — Web UI
Create a new public repository named `dao-arbiter`, **without** initializing with a README (to avoid merge friction).

## 4) Push this repo (manual)

From the `dao-arbiter/` folder:

### If this folder already contains `.git/` (this bundle does)
Just set the remote and push:

```bash
OWNER="$(gh api user -q .login)"
git remote add origin "git@github.com:${OWNER}/dao-arbiter.git"
git push -u origin main
```

### If this folder does NOT contain `.git/`
Initialize and push:

```bash
git init
git add .
git commit -m "feat: initial commit of DAO-LIFEBOOK and Dopaminergic Arbiter Preprint"
git branch -M main

OWNER="$(gh api user -q .login)"
git remote add origin "git@github.com:${OWNER}/dao-arbiter.git"
git push -u origin main
```

## 5) Validate (local smoke checks)

```bash
git status
ls -lah
sha256sum README.md DAO-LIFEBOOK.md FAIL_PACKET.json PROOF_BUNDLE.json Vasylenko_DAO_Arbiter_2026.pdf
```

## 6) PASS_CONTRACT closure checklist

See `spec/PASS_CONTRACT_template.md`.
