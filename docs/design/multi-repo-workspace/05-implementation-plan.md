# Multi-Repo Workspace (EPIC #105): Implementation Plan

> Status: **draft v1 (2026-09-30)**. Slice 0 (linked changes) planned in detail from
> [requirements v1.1](../../01-product/multi-repo-workspace/requirements.md) and the issue's
> 2026-10-01 comment; slices 1 to 3 outlined in the HLD §6. Slice 0 is a minor release: it adds one
> optional list to the change record and changes no required field, hook or catalog step.

## 1. What slice 0 rides on (verified in the repo)

| Mechanism | Where | Used for |
|---|---|---|
| `status: implementation-approved` | `.hitl/current-change.yaml`, set by `ta-approve`; the `tdd` refusal rule reads it | the partner's approval signal |
| Issue markers | `hooks/sync-step-to-issue.sh` (`**HITL progress**`), `ta-approve` (`## ✅ Gate Approved`, `## ✅ Ready for Development`), `ops/deploy` (`## 🚀 Deployed to <env>`) | the host-visible fallbacks |
| Trailing digits as the issue number | `gen_change.py:246`, `_steps.sh hitl_branch_reconcile`, `skipped_line.py`, `pulse.py refs_in` | a prefix other than GH already works |
| `gh api` contents by ref, sub-issues | probed 2026-09-30 on this repository | the record read and the epic link |
| `check_change.py` | `ci/preflight/`, run by `ci/workflows/traceability-check.yml` | the gate that gains the partner source |
| Validator install and update | brownfield Step 3, `init-project.sh`, `migrate_project.py` sync sets, the hash manifest | shipping `ci/linked/` |

## 2. Phases

| Phase | Deliverable | Depends | Requirements | Key tests |
|---|---|---|---|---|
| **A** | Schema: `linked_changes` and `fold_before_partners` in `change-context.schema.yaml`; config keys documented in `shared/linked-changes.md` | design | LC-1, LC-5, LC-6 | WIRE-2 |
| **B** | `ci/linked/linked.py` with `state`, `need`, `fetch`, `issue-repo`, `link-sub`; tests with a fake host | A | LC-2, LC-3, LC-4, LC-6, LC-7 | NEG-1 to NEG-9, CHK-1 to CHK-10 |
| **C** | `check_change.py` partner source; `pulse.py` prefix fallback | B | LC-2, LC-5 | GATE-1 to GATE-5, PFX-2 |
| **D** | Skill edits: `start-change` (prefix, partner question, issue repo, sub-issue link), `tdd`, `apply-change`, `review-lld-adherence`, `ops-deploy`, `conclude`, `retro`, the three filing skills, `issue-hygiene.md`, `workflow-steps.md`; user doc `docs/linked-changes.md` | B | LC-2 to LC-7 | WIRE-1, FIL-1, PFX-1, skill lint |
| **E** | Integration: copy blocks, sync sets, hash manifest, retired tests, `dev-update` lists, `.gitignore` entry, plugin build, help, usage guide, CHANGELOG | D | all | WIRE-4, WIRE-5, full suite |
| **F** | Validation review on the real host (this repository and the plugin repository as partners), then release as a minor on 2.x | E | all | the five acceptance items |

## 3. Decisions

| ADR | Decision |
|---|---|
| 1 | one record per repository, linked, no shared record |
| 2 | partner state from the host in a fixed order; unreadable is exit 3, never a pass |
| 3 | checks in the skills that already refuse plus the traceability gate; no new hook |
| 4 | references by commit, never by branch; the copy under `.hitl/linked/` is a cache |
| 5 | prefix as a repository setting; trailing digits stay the issue number |
| 6 | issue repositories as config; the sub-issue link is best effort |
| 7 | a docs change folds when its last code partner merged; earlier is recorded |

## 4. Review history

| Round | Date | Lens | Verdict | Applied |
|---|---|---|---|---|
