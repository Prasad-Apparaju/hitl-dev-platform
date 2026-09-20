# Branch Context: Requirements

> **What** HITL must do when work that belongs to no active change starts while the working tree is
> on another change's branch: notice at the command that would write, move the work to main (a
> switch when the tree is clean, a sibling worktree when it is not), offer the way back, and let the
> few writes that legitimately belong to no change (shaping an issue, the PRD, the backlog) happen on
> main without an active change. Product one-liner: **FR-34** in the [PRD](../prd.md) backlog table
> (§5.7); ticket [#136](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/136), status Backlog. The **how** (the context check, the worktree layout, the gate allowance, the return path)
> is a design package at `docs/design/branch-context/`, not started. Status: **draft v1
> (2026-09-20)**. Related: FR-33 single developer mode (a solo developer hops tasks constantly),
> FR-30 multi-repo workspace (already leans on sibling worktrees), `/hitl:dev-switch-context`,
> intake Step 1 (do not clobber an active change), the pre-tool-use gate.

## 1. Problem

A change lives on its own branch with its own change file, and the gate keeps source edits on that
branch tied to that change. Nothing keeps *other* work off it. Shaping a new issue while on the
branch for issue 123 is harmless until one step later, when the PM skill writes the new requirement
into the PRD and the design skill writes design docs: those land on 123's branch, ship with 123 or
disappear when its branch is deleted after merge. The person did nothing wrong. They asked HITL for
a new task while standing where their last task left them, which is where everyone stands.

What exists today and why it is not enough:

| Mechanism | What it does | Gap |
|---|---|---|
| Intake Step 1 | Refuses to start a second change on a branch that already has one | Only intake; the PM skills do not check |
| `/hitl:dev-switch-context` | Stashes, checks out another **issue** branch, reloads context | Never goes to main; never restores the stash it made |
| The gate, layer 1 | With no active change on the branch, blocks **all** edits except `.hitl/` and `.claude/` | On main there is no active change, so the PRD write this feature needs is blocked too |
| The gate, layer 2 | Blocks edits when branch and change file disagree | Says nothing when branch and change agree but the work is someone else's |

**Delivery surface.** A shared context check invoked by the PM skills, intake and the switch command;
a gate allowance for a named set of no-change paths; a return path. No new workflow, no UI.

## 2. Users

| User | What they need |
|---|---|
| **Developer** | To say "new task" from wherever they are and have the new work land on main, with what they were doing kept intact and one step from resuming |
| **PM** | To add or change a requirement without knowing or caring what branch the developer's tree is on |
| **Architect** | Design docs for a new issue on a branch cut from main, never on another change's branch |
| **HITL maintainer** | One rule, one check, reused by every skill that writes outside a change |

## 3. Scope

**In scope.** The PM skills that write to the repo (`pm-add-feature`, `pm-report-bug`,
`pm-design-feature`, `pm-update-requirement` and the like), `dev-start-change`,
`dev-switch-context`, the pre-tool-use gate's no-change allowance, and a return path.

**Out of scope.** Detecting that a *conversation* has drifted to another topic. Any change to what
a change's branch may contain once the work is the change's. Multi-repo layouts (FR-30 owns the
worktree layout across repositories; this feature must fit it, not define it).

**Slices.**

| Slice | Delivers | Requirements |
|---|---|---|
| 1 The rule and the check | The context check at the writing commands; the three options; the gate allowance | BC-1 to BC-4 |
| 2 The way back | Stash restore and worktree return; the switch command learns main | BC-5, BC-6 |
| 3 The nudge | A soft prompt when an edit request names a different issue | BC-7 |

## 4. Goals

1. A PRD or design write for a new issue never lands on another change's branch.
2. The person loses nothing: uncommitted work on the change branch is kept and restored by one
   command, and a dirty tree is never stashed when a worktree would do.
3. Creating an issue alone never forces a branch move.
4. No new prompts on the normal path: a developer on main, or on the branch of the change they are
   working, sees nothing new.

## 5. Requirements

Requirement IDs are `BC-<n>`.

| ID | Requirement | Priority | Slice |
|---|---|---|---|
| **BC-1** | **The rule: writes that belong to no active change happen on main.** "Main" means the repository's default branch, or a branch cut from it for the new work. A write belongs to the active change when the change file on the current branch is active and the write is part of that change's plan. Everything else, the PRD, the backlog table, a new issue's design docs, is no-change work and goes to main. Creating or editing a GitHub issue is not a write to the repo and is never gated by branch. | Must | 1 |
| **BC-2** | **The check runs at the command, not on the conversation.** Before its first repo write, each PM skill, intake, and any "new task" entry point runs one shared context check: is there an active change on this branch, and is this write part of it? If the tree is on main or the write belongs to the active change, nothing is said. HITL does not classify chat topics; a wrong guess that moves someone off their branch mid-thought is the interruption this feature exists to prevent. | Must | 1 |
| **BC-3** | **One question, three answers, a default that never loses work.** When the check fires, HITL asks once: *(a) park this change and go to main*, *(b) open a sibling worktree on main for the new work and leave this tree untouched*, *(c) this belongs to the current change after all*. The recommended default is (b) when the working tree is dirty and (a) when it is clean, with one line saying why. (a) commits nothing on the person's behalf: it stashes with a named message, checks out main, pulls, and records the stash and the branch it came from in a local file so BC-5 can find them. | Must | 1 |
| **BC-4** | **The gate allows no-change writes on main to a named set of paths.** With no active change on the default branch, the gate permits writes to the PRD, the product requirements folder, the backlog and the `.hitl/` bootstrap paths it already allows, and nothing else. Source and design paths stay blocked until a change is active. The set is declared in one place the gate and the skills both read, so adding a path is one edit. On a branch that is not the default branch, layer 1 is unchanged. | Must | 1 |
| **BC-5** | **The way back is one command.** After the no-change work is done, HITL offers "back to #N?" For a parked change that means checkout of the recorded branch and `git stash pop` of the recorded stash, reporting a conflict rather than resolving it silently. For a worktree it means naming the original tree's path and, if the worktree was created for this one task, offering to remove it once its work is committed or discarded. `/hitl:dev-switch-context` gains `main` as a target and restores a stash it made when returning to a branch it left. | Must | 2 |
| **BC-6** | **Worktrees are first class in HITL state.** Every skill and hook resolves the repository root from git, never from the current directory, so a sibling worktree gets its own `.hitl/` state and never reads or writes the original tree's. A worktree on main carries no change file and is subject to BC-4. The layout must fit the sibling-worktree convention FR-30 already uses. | Must | 2 |
| **BC-7** | **A soft nudge when the ask names a different issue.** When a request to edit files names an issue number that is not the active change's, HITL says so in one line and offers the BC-3 question, but proceeds if the person says it is the same work. This is the only heuristic trigger, it is off the normal path, and it is a Should because a wrong nudge costs one line and a wrong silence costs a misplaced write. | Should | 3 |
| **BC-8** | **Records stay minimal.** Parking, returning and worktree creation write nothing to the change file and post nothing to any issue. The only durable trace is the local park record BC-3 keeps for BC-5, which is deleted on return. | Must | 1 |

## 6. Constraints

- **No topic detection.** The trigger is a command that is about to write, plus BC-7's explicit
  issue-number mention. Nothing reads the conversation for drift.
- **Never commit on the person's behalf.** Parking stashes; it does not commit. A commit is the
  person's decision.
- **The gate stays fail-closed.** BC-4 widens what main allows with no active change to a declared
  list and nothing more. A write outside that list on main is still blocked, and nothing on a change
  branch changes.
- **One check, shared.** The context check is one shared step every writing skill invokes, wired
  the way Step 6b of intake wires its scripts, so the wiring suite can assert each skill calls it.
- **Plain English.** Everything said to the person follows `ai/shared/plain-english.md`.

## 7. Non-goals

- Guessing from chat that the person has changed subject.
- Auto-switching without the BC-3 question. The person always chooses.
- Managing more than one active change per tree. One tree, one change, is unchanged.
- Cleaning up worktrees the person made themselves.

## 8. Success measures

| Measure | Target |
|---|---|
| PRD or design writes that land on another change's branch | zero, checked by a wiring test that runs the PM skill's write path with an active change on a non-default branch |
| Work lost when parking | zero: every park has a named stash and a record, every return pops it or reports the conflict |
| New prompts on the normal path (main, or the active change's own branch) | zero |
| Time from "new task" to the PRD write landing on main | one question and one confirmation, no manual git |

## 9. Version

| Version | Date | Change |
|---|---|---|
| draft v1 | 2026-09-20 | First draft from the discussion on 2026-09-20. Three forks settled as defaults: command-triggered with one soft nudge (BC-2, BC-7); worktree when dirty, switch when clean (BC-3); issue creation alone never needs main (BC-1). Not reviewed. |

## 10. References

- `ai/claude/switch-context/SKILL.md` (stash and checkout today; no main target, no restore)
- `ai/claude/start-change/SKILL.md` Step 1 (do not clobber an active change)
- `ai/claude/hooks/check-hitl-context.sh` (gate layers; layer 1 blocks all edits with no active change)
- `ai/claude/pm/add-feature/SKILL.md` step 7 (the PRD write this feature must route to main)
- `docs/01-product/single-developer-mode/requirements.md` (FR-33)
- `docs/01-product/prd.md` §5.7 (FR-30 multi-repo workspace, sibling worktrees)

## 11. Review history

None yet.
