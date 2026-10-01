# Multi-Repo Workspace: Low-Level Design (slice 0, linked changes)

> Status: **draft v1 (2026-09-30)**. Implements HLD [`01-design.md`](01-design.md) and ADRs
> [`02-adrs.md`](02-adrs.md) for LC-1 to LC-7.

## 1. Scope

The record addition (§2), the checker's contract (§3), pinned references (§4), the skill and gate
edits (§5), the config keys and the filing rule (§6), lints (§7).

## 2. The record: `linked_changes` (LC-1, ADR-1)

Added to `ai/shared/templates/change-context.schema.yaml` as an optional top-level list. The awk
breadcrumb parser reads only the `workflow` block, so the list is invisible to it.

```yaml
linked_changes:                       # optional; absent on every single-repo change
  - repo: org/docs                    # owner/name on the host
    change_id: GH-40                  # the partner's change id as its own repo writes it
    role: docs                        # docs | provider | consumer | code
    issue: 40                         # optional; default: the digits at the end of change_id
fold_before_partners:                 # optional; written by conclude when a docs change folds early (LC-7)
  by: "pm@team"
  at: 2026-09-30T12:00:00Z
  reason: "the consumer slipped a quarter; the PRD must describe what ships this week"
```

Roles are from the declaring change's point of view: `docs` holds this change's design; `provider`
must ship before this change; `consumer` ships after it; `code` implements this docs change. A role
outside the four, a `repo` not of the form `owner/name`, or a `change_id` with no digits is
`MALFORMED` and the checker exits 2 before any host read.

## 3. The checker: `ci/linked/linked.py` (LC-2, LC-3, LC-7, ADR-2)

Standard library plus PyYAML; every host read goes through one `run(cmd) -> (code, stdout)` function
that wraps `gh`, injectable for tests. Exit codes: 0 satisfied, 2 not satisfied or malformed, 3 the
host could not be read (and which read). Nothing is cached between runs.

### 3.1 Reading one partner

| Fact | Read | Fallback |
|---|---|---|
| issue number | `issue` field, else trailing digits of `change_id` | none; no digits is MALFORMED |
| branch | `gh api repos/R/branches?per_page=100` filtered to `issue/<n>-*` (first match) | none |
| record | `gh api repos/R/contents/.hitl/current-change.yaml?ref=<branch>` (base64 body), `status` and `linked_changes` | unreadable: record `none`, continue with comments |
| issue state and comments | `gh api repos/R/issues/<n>` and `gh api repos/R/issues/<n>/comments --paginate` | unreadable: exit 3 |
| PRs | `gh api "repos/R/pulls?state=all&head=<owner>:<branch>"` plus `search/issues?q=repo:R+is:pr+<change_id>` and `...+<n>`; a search hit counts only when its head ref starts with `issue/<n>-` (read from `repos/R/pulls/<number>`, kept after the branch is deleted) or its title or body carries the change id or `#<n>` as a whole word | unreadable: exit 3 |
| approved | record `status: implementation-approved`, else a comment whose first line is `## ✅ Ready for Development` or starts with `## ✅ Gate Approved`, else a merged PR | |
| merged | any PR with `merged_at` set | |
| deployed | every environment named by a comment whose first line starts with `## 🚀 Deployed to ` | |

### 3.2 Subcommands

```
linked.py state   [--change .hitl/current-change.yaml] [--json]
linked.py need    docs-approved | provider-deployed --env <env> | code-merged  [--change ...]
linked.py fetch   owner/repo@<commit>:<path>  [--out-dir .hitl/linked]
linked.py issue-repo  epic | slice | bug | followup   [--config .hitl/config.yaml]
linked.py link-sub  owner/repo#<epic> owner/repo#<child>
```

`state` prints one line per partner: `role change_id repo status=<record or none> approved=yes|no
merged=yes|no deployed=[envs]` and, when the partner's record is readable, whether it links back
(`backlink=yes|no`). `need` prints the same lines for the partners it inspected and one verdict line
naming what is waited on. With no `linked_changes` every `need` prints `no linked changes` and exits 0.

`fetch` refuses a reference whose middle part is not 7 to 40 hex characters (a branch), writes the
decoded body to `<out-dir>/<owner>/<repo>/<commit>/<path>`, and prints that path. `issue-repo` prints
`-R <repo>` when the config names one for the kind (`epic` reads `issues.epics`; `slice`, `bug` and
`followup` read `issues.slices`) and nothing otherwise. `link-sub` resolves the child's database id
(`gh api repos/R/issues/<m> --jq .id`) and posts it to `repos/E/issues/<epic>/sub_issues`; on any
refusal it comments on the epic (`Slice: R#<m>`) and exits 0.

## 4. Pinned references (LC-4, ADR-4)

Grammar: `^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@([0-9a-f]{7,40}):(.+)$`. Accepted by `dev-tdd` (the
LLD argument), `dev-apply-change` (the HLD/LLD source artifact), `dev-review-lld-adherence` (the
manifest's `lld:` value), and by the manifest template as a documented alternative to a local path.
Each skill runs `fetch`, reads the printed path, and writes the reference, not the path, into the
record (`source_artifacts.lld`) and into anything it cites. `.hitl/linked/` is added to `.gitignore`
by onboarding beside `.hitl/people/`.

## 5. Where the checks run (LC-2, LC-3, LC-7, ADR-3)

| Skill or gate | Edit |
|---|---|
| `dev-tdd` | a fourth refusal rule before the LLD rule: with a `docs` partner, run `need docs-approved`; on exit 2 stop with the checker's verdict line; on exit 3 stop and say the host could not be read |
| `dev-apply-change` Step 2 | the same rule; and the LLD path may be a pinned reference |
| `dev-review-lld-adherence` Step 1 | an `lld:` value that is a pinned reference is fetched first |
| `ops-deploy` Step 1 | with a `provider` partner, run `need provider-deployed --env <target>`; on exit 2 or 3 stop before Step 2 |
| `dev-conclude` fold | with a `code` partner, run `need code-merged`; on exit 2 ask "fold now anyway?"; a yes writes `fold_before_partners` |
| `dev-retro` | a "Linked changes" section from `state` |
| `check_change.py` | reads `.hitl/current-change.yaml` when present; with a `docs` partner, `check_decision_packet` also searches the partner's merged or open PR files (`gh api repos/R/pulls/<n>/files`) for `docs/decisions/issue-<n>*.yaml` and fetches each by ref to validate; `check_lld_adr_for_api` passes when the partner's PR files include an LLD or ADR path; the result message names the partner. A host read that fails is a failed check, never a pass |

## 6. Config keys and the filing rule (LC-5, LC-6, ADR-5, ADR-6)

```yaml
# .hitl/config.yaml
repo: org/service-scm            # default: gh repo view --json nameWithOwner
change_id_prefix: SCM            # default GH; start-change forms <prefix>-<issue>
issues:
  epics: org/docs                # where pm-add-feature files an epic; default: this repo
  slices: org/service-scm        # where start-change, pm-report-bug, qa-report-defect and conclude file; default: this repo
```

`start-change` Step 6 reads the prefix with one Python line and writes `CHANGE_ID="${PREFIX}-${N}"`.
`shared/issue-hygiene.md` gains section 4, "Which repository", and every filing skill passes
`$(python3 "$LINKED" issue-repo <kind>)` to `gh issue create`. Team Pulse's `change_id_prefix`
defaults to the top-level key.

## 7. Lints and wiring tests

- `test_wiring.py`: every skill that runs `need` names `ci/linked/linked.py` and its shared fallback;
  `dev-tdd`, `dev-apply-change` and `ops-deploy` carry the exit-3 wording; the filing skills pass
  `issue-repo`; the catalog is unchanged; the schema lists `linked_changes` with the four roles.
- `test_shipped_tools_are_self_contained.py`: `ci/linked` in the synced set; its test file in the
  removal list and retired-tests.
- Skill lint: every edited skill stays under the cap.
