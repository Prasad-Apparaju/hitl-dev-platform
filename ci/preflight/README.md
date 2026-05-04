# Preflight Traceability Check

`check_change.py` verifies that a code change has the required supporting artifacts before code generation or PR merge.

## What it checks

| Check | Trigger | Requirement |
|-------|---------|-------------|
| **linked-issue** | Any source file (`.py`, `.ts`, `.js`, etc.) changed | `--issue <number>` must be supplied; verified via `gh issue view` if the CLI is available |
| **decision-packet** | Files in a `system-manifest.yaml` domain changed | A decision packet exists at `docs/decisions/issue-*.yaml` |
| **lld-adr-update** | API/controller/router files changed | At least one LLD or ADR doc is also modified in the changeset |
| **test-registry** | Test/spec files changed | `test-registry.yaml` is also modified in the changeset |
| **rollout-plan** | IaC/deployment files (Terraform, Helm, k8s, etc.) changed | A rollout plan exists in a decision packet or as a changed file |

Each check outputs **PASS** or **FAIL** with a message.  Exit code is `0` when all pass, `1` when any fail.

## Running manually

```bash
# Basic — auto-detects changed files via git diff against origin/main
python ci/preflight/check_change.py --issue 42

# Explicit file list (useful outside a git context)
python ci/preflight/check_change.py --issue 42 --changed-files src/api/users.py docs/lld/users.md

# Custom base ref
python ci/preflight/check_change.py --issue 42 --base-ref origin/develop

# Strict mode — domain mismatches in decision packets become errors (exit 1)
python ci/preflight/check_change.py --issue 42 --strict
```

### Prerequisites

- Python 3.10+
- `pyyaml` (`pip install pyyaml`) — needed for manifest-domain and rollout-plan checks
- `gh` CLI - optional for local non-strict runs; required for strict issue verification in CI

## How Claude uses it

During the `/workflows:apply-change` workflow, Claude runs this script **before generating any code**.  The typical invocation:

```
python ci/preflight/check_change.py --issue <ISSUE_NUMBER>
```

If any check fails, Claude must resolve the gap (create a decision packet, update LLD, etc.) before proceeding to code changes.

## How CI uses it

The `ci/traceability-check.yml` GitHub Actions workflow runs the same script on every pull request.  It:

1. Checks out the repo with full history (`fetch-depth: 0`).
2. Computes changed files via `git diff --name-only origin/$BASE_REF...HEAD`.
3. Runs `python ci/preflight/check_change.py --strict --changed-files <files>`.

The job fails the PR status check if any traceability rule is violated, blocking merge until the issue is fixed.
