# Branch Protection Setup

This guide explains how to configure GitHub branch protection so the **Traceability Check** is required before merging to `main`.

## Steps

### 1. Open branch protection settings

Navigate to:

```
Repository → Settings → Branches → Branch protection rules → Add rule
```

In the "Branch name pattern" field, enter `main`.

### 2. Require status checks

Check **"Require status checks to pass before merging"**.

In the search box that appears, type `traceability` and select the **traceability** job from `ci/traceability-check.yml`.  This blocks any PR from merging until the preflight script exits with code 0.

Also select **convention-check** jobs (`semgrep`, `manifest-drift`, `mermaid-check`) if you want those enforced too.

### 3. Require pull request reviews

Check **"Require pull request reviews before merging"**.

Set "Required number of approvals" to **1** (or higher for critical repos).  This ensures at least one human reviews every change.

### 4. Require linear history (optional)

Check **"Require linear history"**.

This prevents merge commits and forces rebase or squash merges, keeping `git log` clean and making `git bisect` reliable.  Recommended but not mandatory.

### 5. Additional recommended settings

- **"Restrict who can push to matching branches"** -- limit direct pushes to admins only.  All changes flow through PRs.
- **"Require conversation resolution before merging"** -- ensures all review comments are addressed.
- **"Do not allow bypassing the above settings"** -- prevents even admins from force-merging without checks.

### 6. Save

Click **"Create"** (or **"Save changes"** if editing an existing rule).

## Verification

After saving, open a test PR against `main`.  You should see the **traceability** status check listed as "Required" in the merge box.  The PR cannot be merged until it reports success.

## Manifest Drift Checks by Team Maturity

Teams can progressively tighten manifest drift enforcement as they mature:

| Stage | Flags | What blocks CI |
|---|---|---|
| Early adoption | `--strict` | Unlisted files |
| Maturing | `--strict --fail-cross-domain-imports` | Unlisted files + cross-domain imports |
| Mature | `--strict --fail-cross-domain-imports --fail-missing-facade` | All categories |

Update the `manifest-drift` step in your CI workflow to add the appropriate flags for your team's stage.

## Summary of enabled protections

| Setting | Purpose |
|---------|---------|
| Required status checks: `traceability` | Enforces issue linking, decision packets, LLD/ADR updates, test-registry, rollout plans |
| Required status checks: `semgrep`, `manifest-drift`, `mermaid-check` | Enforces coding conventions and doc standards |
| Pull request reviews (1+) | Human review gate |
| Linear history | Clean commit graph |
| No bypass | Admins cannot skip checks |
