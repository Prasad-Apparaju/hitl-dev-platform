# Deployment Gates

How to enforce risk-based gates before code reaches production. Complements the [Rollout Strategy](rollout-strategy.md) which covers what happens after deploy.

---

## Gates by Risk Level

| Risk | PR Gate | Deploy Gate | Approval |
|---|---|---|---|
| **Low** | Standard PR review | Auto-deploy on merge | None |
| **Medium** | PR review + `rollout-approved` label | Deploy workflow checks for label | None |
| **High** | PR review + `rollout-approved` label | GitHub Environment with required reviewers | Manual approval in Actions |
| **Critical** | PR review + `rollout-approved` label | Separate deploy PR reviewed by tech advisor | Manual approval + deploy PR merge |

---

## GitHub Actions Implementation

### Sample: Deploy with Risk-Based Gates

See [`ci/deploy-with-gates.yml.example`](../../ci/deploy-with-gates.yml.example) for a complete workflow. The key patterns:

#### Checking for the `rollout-approved` label

```yaml
- name: Check rollout-approved label
  if: needs.determine-risk.outputs.risk != 'low'
  run: |
    LABELS=$(gh pr list --search "${{ github.sha }}" --json labels --jq '.[0].labels[].name')
    if ! echo "$LABELS" | grep -q "rollout-approved"; then
      echo "::error::PR must have 'rollout-approved' label for medium+ risk deploys"
      exit 1
    fi
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Manual approval via GitHub Environments

```yaml
deploy-high:
  needs: [determine-risk, gate-check]
  if: needs.determine-risk.outputs.risk == 'high' || needs.determine-risk.outputs.risk == 'critical'
  runs-on: ubuntu-latest
  environment: production  # requires reviewers configured in repo settings
  steps:
    - name: Deploy
      run: ./scripts/deploy.sh
```

To configure the `production` environment: **Settings > Environments > production > Required reviewers** and add the people who should approve high/critical deploys.

#### Reading risk level from a decision packet

The deploy workflow looks for a `docs/decisions/issue-NNN.yaml` decision packet in the PR's changed files. It reads `rollout.risk` as the canonical field (falling back to the legacy `risk_level` top-level key):

```yaml
- name: Determine risk level
  id: risk
  run: |
    PACKET=$(git diff --name-only HEAD~1 HEAD | grep "docs/decisions/issue-.*\.yaml" | head -1)

    if [ -n "$PACKET" ] && [ -f "$PACKET" ]; then
      # Prefer rollout.risk (canonical); fall back to top-level risk_level
      RISK=$(python3 -c "
    import yaml, sys
    data = yaml.safe_load(open('$PACKET'))
    rollout = data.get('rollout') or {}
    risk = rollout.get('risk') or data.get('risk_level') or ''
    print(risk)
    " 2>/dev/null)
      echo "Found decision packet: $PACKET — risk=$RISK"
    fi

    if [ -z "$RISK" ]; then
      echo "::warning::Could not determine risk level — defaulting to manual approval"
      echo "risk=high" >> "$GITHUB_OUTPUT"
    else
      echo "risk=$RISK" >> "$GITHUB_OUTPUT"
    fi
```

If no decision packet exists or the risk field is missing, the workflow defaults to **high** (requires manual approval). This is intentional: unknown risk should not bypass gates silently.

---

## Other CI/CD Systems

The same concepts apply regardless of platform:

### GitLab CI

- Use `rules:` with `if: '$CI_MERGE_REQUEST_LABELS =~ /rollout-approved/'` to gate deploy jobs
- Use `when: manual` for high/critical risk to require a click in the pipeline UI
- Use protected environments for reviewer requirements

### CircleCI

- Use `requires:` with an `approval` job type for manual gates
- Check labels via the GitHub API in a script step before deploying
- Use contexts with restricted access for production deploy credentials

### General Pattern

```
1. PR merges to main
2. CI reads risk level (from decision packet, PR label, or default)
3. Low  → deploy immediately
4. Medium → check for approval label → deploy
5. High → check for approval label → wait for manual approval → deploy
6. Critical → check for approval label → wait for manual approval
              → verify separate deploy PR exists and is approved → deploy
```

---

## Rollback Procedure

When a deploy goes wrong, pick the fastest safe option:

### Option 1: Revert the Merge Commit

```bash
git revert <merge-commit-sha> --mainline 1
# Create PR for the revert, merge immediately (low risk — it's a revert)
```

Best when: the issue is in the code itself and you need to undo the change entirely.

### Option 2: Disable the Feature Flag

If the change was behind a feature flag, flip it off. No deploy needed.

Best when: the code is fine but the feature has unexpected behavior in production.

### Option 3: Re-deploy Previous Version

If your deploy system supports pinning to a specific commit or image tag:

```bash
./scripts/deploy.sh --version <previous-tag>
```

Best when: the revert is complicated (e.g., migration already ran) and you need to buy time.

### After Rollback

1. **Incident registry entry within 48 hours** — record what happened, root cause, and what would have caught it earlier
2. **Update canary criteria** — if the issue should have been caught by monitoring, add the metric
3. **Update the decision packet** — note the incident for future risk assessment of this domain

---

## Quick Reference

```
Low risk    → merge and ship
Medium risk → add 'rollout-approved' label, then merge
High risk   → add label, merge, approve in GitHub Actions UI
Critical    → add label, create deploy PR, get tech advisor review,
              approve in Actions UI, merge deploy PR
```
