# Branch Protection: Main No-Fly Zone

Configure this exactly in GitHub UI:

1. Go to **Settings → Branches → Add branch protection rule**.
2. Set **Branch name pattern** to `main`.
3. Enable:
   - ✅ **Require a pull request before merging**
   - ✅ **Require approvals**: set to **1** (or **2** if your team policy requires)
   - ✅ **Require review from Code Owners**
   - ✅ **Dismiss stale pull request approvals when new commits are pushed**
   - ✅ **Require conversation resolution before merging**
   - ✅ **Require status checks to pass before merging**
     - Select **only**: `PR Gate / PR Gate`
   - ✅ **Require linear history**
   - ✅ **Include administrators**
   - ✅ **Restrict deletions**
   - ✅ **Block force pushes**

Optional but recommended:

4. Enable **Merge Queue** and require `PR Gate / PR Gate` for `merge_group`.

## Required Check Name

Use this exact check in Branch Protection:

- `PR Gate / PR Gate`

## Important

After merging this workflow to default branch, run one PR through CI once so GitHub records `PR Gate / PR Gate` in the selectable required checks list.

## Security & analysis prerequisite

Enable **Dependency Graph** in repository settings: **Settings → Security & analysis → Dependency graph**.
