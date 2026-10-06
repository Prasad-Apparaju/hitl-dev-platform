# Validator re-sync: the Step 4.6 protocol

Read from Step 4.6 of `dev-update`. The rules the migrator applies to the copied-in CI tools, and why HITL's own test suites are removed from a product repo rather than fixed. No commands here: the step's own fence runs the migrator and the cleanup.

## Why the repo carries copies

Some validators run via project-relative paths from `ci/workflows/*.yml`, where the plugin is not present. So the repo carries its own copy of the plugin's `ci/` and `tools/` directories, installed at onboarding. On upgrade the copies are refreshed, and tools added after the repo was onboarded are installed.

## The per-file protocol

The copies are co-owned. A repo that fixed a validator bug ahead of upstream is a co-owner, and a blind copy would revert that fix on every run, including runs with no version change. So the migrator decides per file:

| Case | Action |
|---|---|
| Shipped file the repo does **not** have | install it |
| Shipped file, byte-identical | leave alone, say nothing |
| Shipped file the repo has, byte-identical to an **older release** | update it; an older version is not an edit |
| Shipped file the repo has **modified** | show the diff, **keep the repo's**, and ask |
| File the repo added itself | never touched, never reported |
| File listed in that directory's `.hitl-optout` | never installed — a deliberate removal stays removed |
| `first-pass-check.yml`, `manifest-waivers.yaml`, `data-layer-check.yml`, `data-layer-waivers.yaml` | installed once if absent, then the repo's outright |

## Why stale test suites are removed, not fixed

Earlier versions synced HITL's own test suites into product repos. They test HITL's internals against the platform's source layout: one of them extracts a generator from `start-change/SKILL.md`, a file no product repo has or should have, so they cannot be made to pass outside the platform repo. They fail on collection and block the consumer's CI. CI in a product repo runs the **validators**; the validators' tests belong with the validators' source.

Removal is gated, because a filename is not evidence of authorship. A team writing tests for the shipped validator `check_skips.py` names theirs `test_check_skips.py` by pytest convention, and this very step, by removing the shipped tests, invites them to. Deleting on name alone destroys that file with no recovery path when it is untracked. So a file is removed only when it is **both** tracked in this repo **and** hashes to a version HITL shipped (the manifest at `shared/ci/retired-tests.sha256`, matched on hash and basename, so content shipped as file A can never delete a file at path B). Anything else is reported and kept. In the HITL platform repo itself these tests are the real suite and are never touched.

Staging afterwards is per existing path only: a single `git add` over an absent optional path errors on the whole pathspec and, with `|| true`, would silently stage nothing.

## When a file differs

Stop and ask per file, with the question in Step 4.6, using the command the migrator printed. Only an explicit yes for that file runs the printed `--overwrite <path>`. Never overwrite a file nobody said yes to, and never resolve a difference by deleting the repo's copy. Keeping the repo's version means it misses the upstream fix; say so.
