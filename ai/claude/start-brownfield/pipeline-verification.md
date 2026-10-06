# Pipeline verification (brownfield Step 5)

The full procedure for Step 5 of `/hitl:dev-start-brownfield`. Read this file and perform every part of it, then return to `SKILL.md` Step 6.

The deployment view generated in Step 4 (Phase 4c of `/hitl:architect-review-existing`) describes the CI/CD pipeline. This step confirms it actually works before feature development begins.

**1. Identify the CI/CD system:**

Check which CI/CD configuration files exist:

| File | System |
|---|---|
| `.github/workflows/*.yml` | GitHub Actions |
| `Jenkinsfile` | Jenkins |
| `.gitlab-ci.yml` | GitLab CI |
| `.circleci/config.yml` | CircleCI |
| `.buildkite/pipeline.yml` | Buildkite |

If none found: skip to "Pipeline missing" below.

**2. Verify the build:**

Run the project's build command (infer from the tech stack confirmed in Step 2 — `npm run build`, `mvn package`, `go build ./...`, `./gradlew build`, etc.).

- ✅ Build passes → continue
- 🔴 Build fails → record the error and say: "Build is broken — fix this before feature work begins. Run `/hitl:ops-build` for a structured diagnosis."

**3. Verify the deployment path:**

Check whether the CI/CD config includes:
- A job that deploys to at least one non-production environment (staging, dev, test)
- A job or manual gate for production deploy

The 31-step workflow (`/hitl:dev-practices`) gates every PR on a passing staging deploy — if no staging job exists, that gate cannot function.

- ✅ Staging deploy job exists → proceed
- 🟡 No staging deploy job → note it: "The HITL staging gate will need a manual workaround until a staging deploy job is added."
- 🔴 No deploy jobs at all → treat same as pipeline missing below

**Pipeline missing or broken:**

If no CI/CD config exists, or the build fails and cannot be quickly fixed, say:

> "No working build pipeline found. This is a 🔴 concern: the 31-step workflow requires a passing build and a staging deploy path before a PR can be closed. Options:
> - Scaffold a CI/CD config now: describe your hosting target (GitHub Actions → AWS/GCP/Azure/Railway/Fly.io) and I'll generate a starter pipeline
> - Set it up manually and re-run this step when ready
> - Proceed and accept that the build and deploy steps of the 31-step workflow will need manual execution until the pipeline exists"

If they want a scaffold, generate a minimal CI/CD config (build → test → deploy-to-staging) using the tech stack from Step 2 and the deployment target from the deployment view. Do not include a production deploy job without an explicit approval gate.

**Persist the verdicts (required):** copy `"$PLUGIN_ROOT/shared/templates/platform-readiness-template.yaml"`
to `docs/04-operations/platform-readiness.yaml` if missing, set `project_kind: brownfield`,
and record this step's verdicts there: `E1` (build reproducible), `E3` (staging deploy from
CI), `D1` (suites run in CI and can fail) — evidence rules are in the template header. The
register feeds `/hitl:ops-plan-platform` (Step 11) and the production-deploy gate; a verdict
not written here does not exist.
