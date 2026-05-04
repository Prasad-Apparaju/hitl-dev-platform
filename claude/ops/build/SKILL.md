---
name: ops-build
description: Build the application from a specified branch, verify CI pipeline output and artifact integrity, and record build readiness in the HITL context file before deployment.
argument-hint: "[branch name or PR number]"
disable-model-invocation: true
---

# Build from Branch

Build the application from a specified branch and confirm the artifact is ready for deployment.

**Input:** $ARGUMENTS (branch name or PR number)

---

## Step 1 — Verify branch state

1. Run `git fetch origin` and confirm the branch exists
2. Check branch is rebased or merged with the target base (main/release) — flag any divergence
3. Read the CI configuration (`Dockerfile`, `Makefile`, `.github/workflows/`, or equivalent) to understand the build pipeline
4. Identify which domains this branch touches — prefer a graph query:
   ```
   /graphify query "domains affected by branch: <branch-name>"
   /graphify query "components changed in: <list of modified files>"
   ```
   Fall back to reading `docs/system-manifest.yaml` directly and matching modified files to domain paths. Record the affected domains — they determine which smoke checks apply in Step 3.
5. Check recent CI runs for this branch: `gh run list --branch <branch>` — note the last run status

If the last CI run failed, present the failure reason and stop: "Build is blocked — address CI failures before deployment."

---

## Step 2 — Trigger or verify the build

**If CI is available:**
1. Confirm the latest commit on the branch has a passing CI run: `gh run view <run-id>`
2. If no passing run exists, trigger one via `gh workflow run` or instruct the operator to push a triggering commit
3. Report the artifact location from CI output (Docker image tag, S3 path, release asset URL, etc.)

**If building locally:**
1. Run the build command from the CI config (e.g., `docker build`, `npm run build`, `make dist`)
2. Capture and display the build output
3. Record the artifact reference (image digest, build hash, or output path)

---

## Step 3 — Verify artifact integrity

1. Confirm the artifact exists at the expected location
2. Verify the image digest or checksum matches what CI produced — do not proceed with a stale artifact
3. Determine smoke check scope from the affected domains identified in Step 1 — prefer a graph query:
   ```
   /graphify query "health endpoints and smoke checks for domain: <domain-name>"
   /graphify query "integration test entry points for: <domain-name>"
   ```
   Fall back to reading the CI config and `docs/system-manifest.yaml` for known health endpoints if the graph is unavailable.
4. Run the applicable smoke checks (e.g., `docker run --rm <image> --health-check`, `curl /health`)
5. If any smoke check fails, stop and report the failure — do not proceed to deployment

---

## Step 4 — Record build readiness

Update `.hitl/current-change.yaml` under a `build` key:

```yaml
build:
  branch: <branch-name>
  artifact: <image-tag-or-artifact-path>
  digest: <checksum-or-image-digest>
  ci_run: <CI run URL>
  smoke_check: passed
  status: ready
```

Report: "Build verified. Artifact: `<artifact>`. Ready to deploy with `/ops:deploy`."

---

## Important Rules

- Never proceed with an artifact whose digest cannot be verified against CI output
- If CI is the build source, the artifact reference must come from CI — not from a local build unless CI is unavailable
- Record the `build.artifact` reference before handoff — the deploy skill reads it from the HITL context
- A passing CI run on a different commit does not count — verify it is the same commit being deployed
