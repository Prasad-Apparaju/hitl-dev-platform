# Multi-Repo Workspace: Test Plan (slice 0)

> Status: **draft v1 (2026-09-30)**. Conformance for LC-1 to LC-7 against the LLD
> [`03-lld.md`](03-lld.md). The host is a fake `run` function fed canned `gh` responses, so every
> case runs in CI; the fail-closed cases are asserted by feeding the fake the wrong thing.

## 0. What must be impossible

| ID | Input | Required outcome |
|---|---|---|
| **NEG-1** | a `docs` partner whose record says `status: planning` and whose issue has no approval comment and no merged PR | `need docs-approved` exit 2, verdict names the partner |
| **NEG-2** | the record unreadable (404) and the issue comments unreadable (403) | exit 3, the read that failed named; never 0 |
| **NEG-3** | a `provider` with a merged PR and a `Deployed to staging` comment, asked for `--env prod` | exit 2 |
| **NEG-4** | a `provider` with a `Deployed to prod` comment and no merged PR | exit 2 |
| **NEG-5** | a `code` partner with an open PR | `need code-merged` exit 2 |
| **NEG-6** | `role: upstream`; `repo: docs`; `change_id: DOCS` (no digits) | exit 2 `MALFORMED` before any host read (the fake records zero calls) |
| **NEG-7** | `fetch org/docs@main:docs/x.md` | refused, exit 2, no host read |
| **NEG-8** | an approval comment whose first line is `Gate Approved` in prose, not the marker | not approved |
| **NEG-9** | `gh` not installed | exit 3 with the install hint |

## 1. Checker

- **CHK-1** record `implementation-approved` alone approves; a `Ready for Development` comment alone approves; a `Gate Approved` comment alone approves; a merged PR alone approves.
- **CHK-2** `state` lists every partner with status, approved, merged, deployed environments and backlink; a partner whose record links back is `backlink=yes`, one that does not is `backlink=no`.
- **CHK-3** no `linked_changes`: every `need` prints `no linked changes`, exit 0, zero host reads.
- **CHK-4** a change with two `docs` partners, one approved: exit 2 naming the other.
- **CHK-5** `provider-deployed --env prod` with a merged PR and `Deployed to prod` and `Deployed to staging` comments: exit 0.
- **CHK-6** the branch is found by `issue/<n>-` prefix among many branches; absent branch means record `none` and the comments decide.
- **CHK-7** `fetch` with a valid reference writes the decoded body under `.hitl/linked/<owner>/<repo>/<commit>/<path>` and prints the path; a second call overwrites.
- **CHK-8** `issue-repo epic` prints `-R org/docs` from the config; `slice` prints `-R org/svc`; with no config prints nothing.
- **CHK-9** `link-sub` posts the child's database id to the epic's sub-issues; when the API refuses it comments on the epic and exits 0.
- **CHK-10** every exit path leaves no traceback (hostile JSON from the fake, empty bodies, a record that is a list).

## 2. The traceability gate

- **GATE-1** with no change file or no `docs` partner, `check_change.py` behaves as before (its existing tests unchanged).
- **GATE-2** manifest-domain files changed, no local packet, a `docs` partner whose PR files include `docs/decisions/issue-40.yaml`: the packet is fetched by ref and validated; the check passes and names the partner.
- **GATE-3** API files changed, no local LLD, the partner's PR files include an LLD path: `lld-adr-update` passes naming the partner.
- **GATE-4** the partner's PR files have no packet: the check fails as before, with the partner named as searched.
- **GATE-5** the host read fails: the check fails, never passes.

## 3. Prefix and filing

- **PFX-1** `start-change` forms the id from the config prefix (wiring: the skill reads `change_id_prefix` and writes `${PREFIX}-${N}`); `gen_change.py --stub SCM-12 ...` yields `issue:12` where it derives the number; `hitl_branch_reconcile` matches `issue/12-x` to `SCM-12`.
- **PFX-2** `pulse.py` with `change_id_prefix: SCM` at the top level and none under `team_pulse` finds `SCM-12` refs.
- **FIL-1** every skill that files issues (the wiring test's list minus onboarding) passes `issue-repo` to `gh issue create`.

## 4. Wiring

- **WIRE-1** `dev-tdd`, `dev-apply-change`, `ops-deploy`, `dev-conclude`, `dev-retro` name `ci/linked/linked.py` with the `$ROOT/shared/ci/linked/linked.py` fallback; the three refusal skills carry the exit-3 wording.
- **WIRE-2** the schema lists `linked_changes` with the four roles and `fold_before_partners`.
- **WIRE-3** `workflows.yaml` and the catalog are unchanged.
- **WIRE-4** `ci/linked` is in the synced set, the hash manifest, `init-project.sh`, the brownfield copy block, `dev-update`'s lists and the plugin build.
- **WIRE-5** `.hitl/linked/` is in the onboarding `.gitignore` block.

## 5. Acceptance (the issue's five items) and where each is proven

| Item | Proven by |
|---|---|
| declare linked changes; single-repo unchanged | CHK-3, GATE-1, WIRE-2, the full suite |
| no design pass while docs partner unapproved | NEG-1, NEG-2, NEG-8, CHK-1, CHK-4, WIRE-1 |
| no deploy before provider deployed | NEG-3, NEG-4, CHK-5, WIRE-1 |
| LLD from another repo by pinned reference | NEG-7, CHK-7, WIRE-1 |
| prefix per repo in breadcrumb, Team Pulse, retro | PFX-1, PFX-2, the retro section |

## 6. Validation review

One clean-context reviewer, the five acceptance items as the checklist, the suites run, the fake-host
cases re-run by hand against a scratch repository on the real host where `gh` allows (this repository
and the plugin repository as the two partners), one page.
