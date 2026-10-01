# Multi-Repo Workspace: Architecture Decision Records (slice 0)

> Status: **proposed, v1 (2026-09-30)**. HLD: [`01-design.md`](01-design.md); LLD: [`03-lld.md`](03-lld.md).

---

## ADR-1: One record per repository, linked; not one record for all

**Context.** Design fork 1 asked where the change record lives when a change spans repositories.

**Decision.** Each repository keeps its own record on its own branch, as today. A record names its
partners in an optional `linked_changes` list. No shared record, no second file, no schema change to
a required field.

**Alternatives.** One record in the docs repository that every code repository reads (a scoped
contributor cannot write it, and every hook would need a second root). A record in both repositories
with one authoritative copy (two copies drift; the hooks would need to know which is which).

**Consequences.** (+) Single-repository projects are untouched; every hook still reads one file.
(+) A partner's state is read from the host, which is the access boundary the requirement set.
(−) The link is declared twice, once from each side; the `state` subcommand shows both directions
so a one-sided link is visible.

---

## ADR-2: A partner's state comes from the host, read in a fixed order, and unreadable is never a pass

**Decision.** `linked.py` reads a `docs` partner's approval from its record on its branch through the
contents API (`status: implementation-approved`), then from its issue comments (`## ✅ Ready for
Development`, `## ✅ Gate Approved`), then from a merged PR. A `provider` is shipped when a PR for the
change is merged and a `## 🚀 Deployed to <env>` comment names the environment. Any read the host
refuses or that times out is exit 3, with the reason; a check never passes on silence.

**Alternatives.** Read the partner's checkout on disk (assumes access and a local layout). A webhook
or a status API of HITL's own (a runtime; out of scope).

**Consequences.** (+) Works for a contributor who has read on the docs repository and nothing on the
provider's code: issues and PR metadata are what the host shows them. (−) The markers are prose
HITL already posts; a repository that disables the comment hooks loses the fallback and the record
read must succeed.

---

## ADR-3: The checks live in the skills that already refuse, plus the traceability gate; no new hook

**Decision.** `dev-tdd` and `dev-apply-change` run `need docs-approved` next to their existing
refusal rules; `ops-deploy` runs `need provider-deployed` in its pre-deployment checks;
`check_change.py` looks for the packet and the LLD in a `docs` partner's PR when one is declared.

**Alternatives.** A PreToolUse hook that blocks edits while a partner is unapproved (every edit would
call the host; and the hooks are the one surface the requirements say must stay root-local).

**Consequences.** (+) Three edits, one script, the existing wiring test shape. (−) A person who skips
the TDD step under First Pass skips the check too; the CI gate is the second line.

---

## ADR-4: A design in another repository is referenced by commit, never by branch, and the local copy is a cache

**Decision.** `owner/repo@<commit>:<path>`, fetched through the contents API into `.hitl/linked/`,
which onboarding ignores in git. A branch name in the reference is refused. Skills cite the reference,
not the cached path, in what they write.

**Alternatives.** Submodules (a workspace decision, slice 1). Copying the LLD into the code
repository (two copies of an approved design).

**Consequences.** (+) The approved design is pinned; a later edit in the docs repository does not
silently change what the code was built against. (−) A re-approved LLD needs the reference updated.

---

## ADR-5: The change-id prefix is a repository setting; the issue number stays the digits at the end

**Decision.** `change_id_prefix` in `.hitl/config.yaml`, default `GH`. `start-change` forms
`<prefix>-<issue number>`. Everything that derives the issue number from the id (the generator, the
branch reconcile, the skipped line, Team Pulse) already takes the trailing digits, so nothing else
changes. Team Pulse's own `team_pulse.change_id_prefix` falls back to the shared key.

**Consequences.** (+) `SCM-12` and `EMAIL-14` no longer collide in a shared docs tree. (−) The prefix
is not validated against the repository name; a wrong prefix is a readable mistake, not a broken one.

---

## ADR-6: Issue repositories are a config, and the sub-issue link is best effort

**Decision.** `issues.epics` and `issues.slices` in `.hitl/config.yaml`; `linked.py issue-repo <kind>`
prints the `-R` flag the filing skills pass. `start-change` links a new slice issue under its epic with
the sub-issues API when both numbers are known; a host that refuses the link gets a comment on the
epic naming the slice instead.

**Consequences.** (+) Epics stay in the docs repository with slices beside the code. (−) Sub-issues
are a GitHub feature; other hosts get the comment.

---

## ADR-7: A docs change folds when its last code partner has merged; folding earlier is recorded

**Decision.** `conclude` on a change with `code` partners runs `need code-merged`; when one is still
open it asks, and a yes writes `fold_before_partners: { by, at, reason }` into the record. The PRD
delta is never folded silently ahead of the running code.

**Alternatives.** Fold when the docs PR merges (the PRD then describes code that is not running).

**Consequences.** (+) The PRD stays true to what runs. (−) A long-running code partner holds the fold;
the recorded choice is the release valve.
