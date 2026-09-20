# Branch Context: Requirements

> **What this is.** When you start work that is not part of the change on your current branch, HITL
> should move that work to main and keep your current work safe. The clearest case: you are on the
> branch for one task and you ask for a new task. This is **FR-34** in the [PRD](../prd.md) backlog
> table (§5.7), ticket [#136](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/136),
> status Backlog. The design (how it is built) goes in `docs/design/branch-context/`, not started.
> Status: **draft v1 (2026-09-20)**, not reviewed. Related: FR-33 single developer mode, FR-30
> multi-repo workspace, the `/hitl:dev-switch-context` command, and the edit gate.

## 1. The problem

Every change has its own branch and its own change file. The gate makes sure code edits on that
branch belong to that change. Nothing stops other work from landing there.

Here is how it goes wrong. You finish a task on the branch for issue 123. You stay on that branch,
because that is where you are. You ask HITL for a new task. Creating the issue is fine. Then the PM
skill writes the new requirement into the PRD, and the design skill writes design docs. Those files
are now on 123's branch. They either ship with 123, or vanish when 123's branch is deleted after
merge. You did nothing wrong.

What HITL has today, and why it is not enough:

| What exists | What it does | What it misses |
|---|---|---|
| Intake, step 1 | Refuses to start a second change on a branch that already has one | Only intake checks. The PM skills do not. |
| The switch command | Saves your uncommitted work, moves you to another issue's branch, reloads context | It never goes to main. It never gives your saved work back. |
| The gate, first rule | On a branch with no active change, blocks every edit except HITL's own files | Main has no active change, so the PRD edit this feature needs is blocked too. |
| The gate, second rule | Blocks edits when the branch and the change file disagree | Says nothing when they agree but the work is for a different issue. |

**What we deliver.** One shared check that the writing commands call. A short list of files that may
be edited on main with no active change. A way back to where you were. No new workflow. No screen.

## 2. Who needs it

| Who | What they need |
|---|---|
| Developer | Say "new task" from wherever you are. The new work lands on main. Your current work is kept and one command away. |
| PM | Add or change a requirement without knowing which branch the developer's tree is on. |
| Architect | Design docs for a new issue on a branch cut from main, never on another change's branch. |
| HITL maintainer | One rule and one check, shared by every skill that writes outside a change. |

## 3. Scope

**In.** The PM skills that write files (add feature, report bug, design feature, update
requirement), the intake command, the switch command, the gate's rule for main, and the way back.

**Out.** Guessing from the conversation that you have changed subject. Any change to what a branch
may hold once the work belongs to that change. How worktrees are laid out across several repos,
which FR-30 owns.

**Slices.**

| Slice | What it delivers | Requirements |
|---|---|---|
| 1 The rule and the check | The check at the writing commands, the three choices, the gate rule for main | BC-1 to BC-4, BC-8 |
| 2 The way back | Restore saved work, return from a worktree, teach the switch command about main | BC-5, BC-6 |
| 3 The nudge | A one-line prompt when you name a different issue | BC-7 |

## 4. Goals

1. A PRD or design file for a new issue never lands on another change's branch.
2. You lose nothing. Uncommitted work is kept and comes back with one command.
3. Creating an issue never moves you off your branch.
4. Nothing new appears on the normal path. On main, or on the branch of the change you are working
   on, you see no new question.

## 5. Requirements

Requirement IDs are `BC-<n>`.

| ID | Requirement | Priority | Slice |
|---|---|---|---|
| **BC-1** | **Work that belongs to no change goes on main.** "Main" is the default branch, or a new branch cut from it. A file edit belongs to a change when the current branch has an active change and the edit is part of that change's plan. Everything else is no-change work: the PRD, the backlog table, a new issue's design docs. Creating or editing a GitHub issue is not a file edit. It never depends on the branch. | Must | 1 |
| **BC-2** | **The check runs when a command is about to write, never on the chat.** Each PM skill, the intake command, and any "new task" entry point runs the same check before its first file edit. The check asks two things: is there an active change on this branch, and is this edit part of it? If you are on main, or the edit belongs to the change, HITL says nothing. HITL does not read the conversation for a change of subject. A wrong guess that pulls you off your branch mid-thought is the interruption this feature exists to remove. | Must | 1 |
| **BC-3** | **One question, three answers, and no lost work.** When the check fires, HITL asks once. The answers: (a) park this change and go to main; (b) open a second working copy on main, next to this one, and leave this one alone; (c) this belongs to the current change after all. HITL recommends (b) when you have uncommitted edits and (a) when your tree is clean, and says why in one line. Parking never commits for you. It saves your edits with a named stash, moves to main, pulls, and writes the stash name and the branch to a small local file so BC-5 can find them. | Must | 1 |
| **BC-4** | **On main, the gate allows edits to a short, named list of files.** With no active change on the default branch, the gate lets you edit the PRD, the product requirements folder, the backlog, and HITL's own files. Nothing else. Code and design files stay blocked until a change is active. The list lives in one place that both the gate and the skills read, so adding a path is one edit. On any other branch the gate's first rule does not change. | Must | 1 |
| **BC-5** | **The way back is one command.** When the no-change work is done, HITL asks "back to #N?" For a parked change, HITL checks out the saved branch and restores the stash. If the stash conflicts, HITL says so and stops. It does not resolve the conflict for you. For a second working copy, HITL names the path of the first one and, if it made the copy for this one task, offers to remove the copy once its work is committed or thrown away. The switch command learns two things: main is a valid target, and it restores a stash it made when you return to that branch. | Must | 2 |
| **BC-6** | **A second working copy has its own HITL state.** Every skill and hook finds the repository root through git, never through the current folder. A second working copy then gets its own `.hitl/` folder and never reads or writes the first copy's. A second copy on main has no change file, so BC-4 applies to it. The layout must fit the side-by-side convention that FR-30 already uses. | Must | 2 |
| **BC-7** | **A one-line nudge when you name a different issue.** If you ask to edit files and name an issue number that is not the active change's, HITL says so in one line and offers the BC-3 question. If you say it is the same work, HITL goes on. This is the only guess HITL makes, it is off the normal path, and it is a Should: a wrong nudge costs one line, a wrong silence costs a misplaced file. | Should | 3 |
| **BC-8** | **Almost nothing is recorded.** Parking, returning, and making a second working copy write nothing to the change file and post nothing to any issue. The only trace is the small local file from BC-3, and it is deleted when you return. | Must | 1 |

## 6. Rules the design must keep

- HITL never guesses from the chat. The trigger is a command about to write, plus the issue number
  you typed in BC-7.
- HITL never commits for you. Parking saves your edits. Committing is your decision.
- The gate stays strict. BC-4 adds a short list of files that main allows with no active change,
  and nothing more. Any other file on main is still blocked. Change branches do not change.
- One check, shared. Every writing skill calls the same check, wired the way intake step 6b wires
  its scripts, so the wiring tests can prove each skill calls it.
- Everything HITL says here follows `ai/shared/plain-english.md`.

## 7. Not doing

- Guessing from the chat that you changed subject.
- Switching without asking. You always choose.
- More than one active change in one working copy.
- Cleaning up working copies you made yourself.

## 8. How we know it worked

| Measure | Target |
|---|---|
| PRD or design files that land on another change's branch | Zero. A wiring test runs the PM skill's write path with an active change on a non-default branch and checks where the file went. |
| Work lost when parking | Zero. Every park has a named stash and a record. Every return restores it or reports the conflict. |
| New questions on the normal path | Zero. |
| From "new task" to the PRD edit landing on main | One question and one confirmation. No git by hand. |

## 9. Version

| Version | Date | Change |
|---|---|---|
| draft v1 | 2026-09-20 | First draft from the discussion on 2026-09-20. Three open choices settled as defaults: command-triggered with one nudge (BC-2, BC-7); second working copy when you have edits, switch when you do not (BC-3); creating an issue never needs main (BC-1). Rewritten in plain English the same day. Not reviewed. |

## 10. Where to look

- `ai/claude/switch-context/SKILL.md`: saves and switches today; no main target, no restore
- `ai/claude/start-change/SKILL.md`, step 1: refuses to start a second change on a busy branch
- `ai/claude/hooks/check-hitl-context.sh`: the gate; its first rule blocks every edit with no active change
- `ai/claude/pm/add-feature/SKILL.md`, step 7: the PRD edit this feature must send to main
- `docs/01-product/single-developer-mode/requirements.md`: FR-33
- `docs/01-product/prd.md`, §5.7: FR-30 multi-repo workspace, side-by-side working copies

## 11. Review history

None yet.
