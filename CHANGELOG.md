# Changelog

All notable changes to the HITL plugin are documented here.

---

## [2.9.0] — 2026-09-02

Two features, both about the same complaint: HITL asked for too much on small changes, and never
told you what to run.

### Added

**Right-sizing (#97).** Someone added one environment variable to a shell script and HITL ran
eleven steps over three and a half hours. Nothing malfunctioned; the process was specified that
way. The cause was the order things happened in: the plan was fixed at intake, from the words in
the issue, before any code was read. `FIRECRAWL_API_KEY` in a title reads like a security change.
The code said a file in no area, with no callers.

So impact analysis stops being step 3 of the plan and becomes **the thing that produces the plan**.
It always runs, it cannot be skipped, and there is no plan yet to put it in. It writes what the
change reaches to `.hitl/impact/<change-id>.yaml`, with the provenance of each finding, so an
answer read from a hand-written manifest field is never presented as if it came from the code.

The tier is then proposed **from those findings** and confirmed by a person. Two options follow:

- **fast track** — the steps this change's own facts call for
- **full scale** — everything that applies to a change of this shape

Both are sized by rules on all 38 catalog steps, and every rule reads what the *change* touches,
never what its *area* has. That distinction is the whole feature: rules keyed to an area's
paperwork answer the same for every change to it, so a one-line fix in well-documented code would
draw the longest plan in the system and documenting an area would tax every future change to it.

Measured on the shipped catalog: a one-line API fix behind a flag draws 12 steps of 34, against 23
for full scale. A cross-domain change touching a published interface with a data migration draws 22,
against 31.

**This is not a new mechanism.** It replaces the pre-selection logic inside First Pass Step 4b,
which already presented steps with reasons filled in, took one confirmation for the whole set, and
put the confirming person's name on every record. The ledger, the validator and the actor rule are
unchanged.

**First Pass is no longer opt-in.** Every change is shown a proposal; full scale is the answer set
where nothing is dropped. The one feature built for this problem used to require knowing it existed.

**A fourth disposition, `not_applicable`.** The rules excluding a step is a different fact from a
person declining it. Without the distinction, a fast track recorded a named human as declining
twenty-odd steps they never looked at, and the closing retrospective read that list back as what was
left out and why. `RULE_OVER_FLOOR` (non-waivable) stops a rule retiring a load-bearing step: those
are dropped by a named person accepting the risk, or not at all.

**What you can run, at every step (#100).** The statusline now says it:

```
HITL ▸ GH-97 ▸ Build ▸ RED [T2]  → /hitl:dev-tdd
```

The catalog has declared a command for every step all along. It was dropped in derivation, dropped
again when the change file was written, and never shown. Each hop passed its own checks while the
path was dead end to end. Steps with nothing to run say so rather than inventing a command. Every
step also closes by saying what comes next and how to start it.

### Fixed

- **`impact` left the development workflow** and the retrospective joined it, so the plan is 34
  steps either way. Locked floors are 5 at tier 1, 6 at tier 2, 10 at tier 3.
- **One catalog resolver.** Three tools resolved it three ways and only one matched the layout an
  onboarded product repo has, so the generator failed outright and the validator silently loaded an
  empty catalog and called every skip unknown.
- **Security review, CVE audit and pentest are still unreachable** (#102, open). They are `cond:`
  steps resolved by machinery the plugin does not ship, so a tier-3 change to authentication draws
  none of them, and `pentest` is marked floor while never appearing in a plan.

### Known limits

- The two-option choice applies to `development` only. Platform is a one-time readiness checklist
  with its own waiver machinery and no per-step criticality; the other six workflows have no sizing
  rules and say so rather than offering two identical lists.
- The sizing rules will be wrong at first. The closing retrospective is what corrects them.

## [2.8.0] — 2026-08-18

Adversarial review was the one part of HITL that had never been reviewed. Three reports from real
use, plus what checking them turned up, add up to this release. **If you run
`/hitl:dev-adversarial-review`, this changes how it behaves.**

### Fixed

- **The reviewers' reports were not reaching anyone.** The skill told you to give each reviewer a
  name; naming turns a task that returns into an addressable peer that goes idle, so the report is
  written and never handed back. On one change, ten reviewers produced full reports — 13,000 to
  25,000 characters each — and not one was delivered. They were recovered by hand out of log files.

  Verified here rather than assumed: two agents, identical prompts, one named. The unnamed one
  returned its answer in 1.9 seconds. The named one delivered nothing, never appeared in the
  subagent list, and answered a direct question with an idle signal carrying no content.

  Reviewers now write their report to `.hitl/reviews/incoming/<lens>-round<N>.md` and the skill
  reads the file. **A missing report is UNKNOWN, never "the reviewer failed"** — reading a
  transcript to find out is a race, and losing it wrote a false record claiming a reviewer had
  never synthesized anything. It had; the file was mid-flush.

- **Marking a finding fixed required no evidence at all.** Accepting a risk has always needed a
  name against it. Claiming you had eliminated one needed nothing: a CRITICAL marked `fixed` with
  an empty `resolved_by`, or a fabricated commit id, passed the gate clean and printed *"adversarial
  review present, fresh, and cleared."*

  The record now carries `verified_by` for the reproduction re-run and what it printed. It is a
  field to fill in, not a rule (see the note below). A commit id says where a fix went, not that it
  worked — every false closure in the reports behind this carried a real commit id.

- **The gate read one reviewer's findings per round.** It picked the first record whose verdict was
  adverse — or the last one if they all said ship — and inspected only that one. A second
  reviewer's unresolved CRITICAL shipped unseen. Two reviewers per round is the whole design, and
  half of them were not being read. Found while writing a test for something else.

- **A second reviewer on the same question was invisible.** Duplicate detection compared raw lens
  strings, so filing one as `consequence-2` slipped past it. Names now resolve to a catalog id
  first.

### Added

- **Findings are put to you before anything is fixed.** A finding can be real, reproducible, and
  still not this change's problem — and deciding that is scope, which is yours. CRITICAL and HIGH
  come to you one at a time in plain English (what breaks, what it costs, the recommendation);
  MEDIUM and LOW are summarised. You answer fix, accept, or defer. It does not block, and anything
  you have not answered stays open.

  This is what makes `accepted_by` reachable. The gate has always required it and nothing ever
  asked anyone for a name, which left *fix everything* as the only answer an agent could give — and
  that is what turned reviews into a loop.

- **A lens catalog.** Thirteen named lenses with a base pair that depends on what you just
  finished: `fitness` after design, `correctness` after code, `upgrade` at release, `consequence`
  always. Then conditional ones the change earns — `security`, `data`, `scalability`,
  `operability`, `compatibility`, `bypass`, `interfaces`, `user`, `cost`.

  The plan goes into the offer that already exists rather than a second prompt. You pick where to
  look, never what will be found, and a lens you drop is named in the record's `scope`.

  `user` and `upgrade` are in the catalog because of what they caught here: 2.7.1 exists because a
  round finally looked at the upgrade path, and the feedback panel found in ordinary use what four
  adversarial rounds and an external model had missed. Neither was a documented lens.

- **Two rounds, then it asks.** Not a cap — this framework's own 2.7.x work ran to round 15 and
  round 15 found something — but round three is a decision someone makes, not a continuation. The
  gate also flags a finding that appears in consecutive rounds: two rounds blocked by one
  underlying decision is a scope question, not another fix.

- **Two distinct lenses at release is now written down as the practice**, with the catalog to pick
  the second from. Enforcing it in the gate was attempted and cut; see below.

### Changed

- **HITL stops talking like a compiler.** It interrupts you mid-edit and then reports its internal
  state in capitals: *"HITL CONTEXT MISMATCH: branch 'main' does not match active change GH-58. All
  edits are blocked until the context is realigned."* Nobody has a context mismatch. Nobody
  realigns anything. Several messages offered no way forward at all.

  All 46 of them, across five hooks — including the four inside the deploy gate's Python
  block, which a first pass missed — now say the same thing the way a colleague would and end
  with what to do next:

  ```
  🔒 Nothing is tracked for this branch yet, so edits are paused.

  Tell me what you are working on — an issue number, or just describe it — and I will set it up.
  ```

  Same gates, same exit codes, same enforcement. Icons are a small set marking state — 🔒 paused,
  🧭 where you are, ⚠️ irreversible, ✅ done — extending the existing `✓ ✗ ● ◐ ○ ·` vocabulary
  rather than decorating. They stay out of the breadcrumb and statusline, which are width-sensitive.
  They never celebrate: a 🎉 on a skipped review congratulates someone for lowering the bar.
  `/hitl:dev-preferences` accepts *"plain text, no icons"*, which governs what Claude writes; the
  hooks carry their icons as literal characters and read no configuration. Either way the sentence
  carries the warning and the glyph only makes it findable.

- **The portal had not moved since v2.1.1** while the plugin shipped to 2.7.1, so it advertised none
  of First Pass, the compound-agentic surface, the agentic intake, or the release gate. It also
  turned out the catalog page silently dropped the `release` workflow: its generator uses a
  hand-maintained allowlist, and a workflow missing from it never rendered — on a page whose own
  copy says it cannot drift. That is a build failure now. The generator was also overwriting the
  page's navigation on every deploy, so the live catalog had been missing its "Getting started" and
  GitHub links since they were added.

### Note for existing projects

Run `/hitl:dev-update`. **Two things changed in how review records are read, and a record that
relied on either may now block where it did not before.** Both are holes this release closes, so the
new blocks are correct — but know them before you upgrade mid-release:

- **Every record in a round is read.** Findings used to be taken from one record per round: the
  first adverse one, or the last if they all said ship. Whichever record the gate happened not to
  pick was not examined at all. Anything wrong in a sibling record — an unresolved finding, an
  acceptance with no signer, a malformed severity, a `findings:` that is not a list — was invisible
  and is now reported.
- **Lens names resolve to a catalog id.** `consequence-2` is `consequence`, `destructiveness` is
  `consequence`. A second reviewer filed under a numbered variant read as a distinct lens before;
  it now reads as the same lens twice and `DUPLICATE_ROUND` says so.

Deliberately not a list of error codes: the codes you see depend on what was already wrong in the
record that was never being read, and an earlier draft of this note twice gave a count that turned
out to be incomplete.

Nothing else changed. A single-record round, a finding closed with a bare commit id, and a legacy
lens name all validate exactly as they did on 2.7.1.
### On three checks that are not in this release

This release was going to add three rules to the release gate: a release must be reviewed through at
least two distinct lenses; a CRITICAL or HIGH marked `fixed` must record how that was verified; and
an open CRITICAL or HIGH must survive later rounds until something resolves it. All three are good
rules. None shipped.

Four rounds of independent review found CRITICAL defects in all three, repeatedly, and each round's
fixes produced the next round's findings. The rule kept after round 3 as "the part that survived
review" had in fact failed the only round it was ever exposed to. Earlier drafts of this note tried
to summarise that as a count, and to claim every finding in the release sat inside these three
rules. Both were wrong — some of what those rounds found is in code that ships and is fixed above —
and the attempt is dropped rather than corrected a third time.

The root cause is structural rather than a run of bugs. This validator judges **one** review round.
All three rules require reasoning about a **sequence** of rounds — what an earlier round found,
whether a later one really closed it, whether a resolution is trustworthy. Round 3 put it exactly:
adding a round makes the gate weaker, because every integrity rule reads only the newest one.
Bolting that on at the end of a release was the wrong place to discover it. The redesign is #92.

All three survive as written practice rather than as rules: pick a second lens from the catalog,
fill in `verified_by` when you close a finding, and read the earlier rounds — the trail is kept for
that reason. Nothing reads `verified_by`; it is there so the next round can. What is not here is
enforcement that was wrong more often than the thing it enforced.

---

## [2.7.1] — 2026-08-16

Round 15 reviewed the upgrade path against 2.7.0 and cleared it, then found a class of defect one
level down. `CLAUDE_PLUGIN_ROOT` is not in the Bash tool environment, and eight shipped code blocks
built paths from it anyway.

### Fixed

- **`dev-update` Step 4.5 crashed on every plugin-onboarded project.** It resolved the workflow
  catalog from `${CLAUDE_PLUGIN_ROOT:-.}` and fell back to a path that exists only in the HITL
  platform repo, so it never found the catalog a product repo actually has. Nothing was lost —
  the catalog is unchanged between 2.6.5 and 2.7.0, and it failed loudly — but it would have
  mattered the first release that changes a workflow.
- **Step 3b's validator refresh was a silent no-op**, so projects kept old snapshots and never
  received checks that had shipped since.
- **Six more blocks** across `dev-start-change`, `dev-validate`, `dev-apply-change` and
  `dev-adversarial-review` had the same fallback, silently unresolvable.
- **The guard for this exact class had two holes and both were occupied**: it required braces, so
  the unbraced form slipped through, and it treated `${CLAUDE_PLUGIN_ROOT:-X}` as a resolution when
  it is a default. It now catches every form and ignores comments.
- **`getting-started.md` said "53 HITL commands, you need four of them"** above a six-row table,
  with 56 shipping. The count guard now checks the prose, not only the arithmetic under the table.

### Note

Nothing in 2.7.0 is unsafe. Run `/hitl:dev-update` when convenient.

---

## [2.7.0] — 2026-08-16

### Added

**Two commands for how HITL talks, and how you write to other people.**

- **`/hitl:dev-preferences`** — tune how HITL talks to you in this project: length, whether it
  narrates its process, how it opens a disagreement. Four questions, adjustable any time, `off` to
  pause and `reset` to remove. Say *"default mode"* to drop it for one session without touching the
  file. Settings live in a marked block in the project's `CLAUDE.md`, which is committed — so the
  block records who set it, says so before writing, and tells a teammate whose settings are in
  force and how to change them.
- **`/hitl:dev-draft-for <person>`** — draft a PR comment, issue update or status note for a
  specific person, using a stored profile under `.hitl/people/`. Drafts only; it never sends, and
  never in the same turn it wrote. Profiles are gitignored by default, record who wrote them and
  whether the subject knows they exist, and both are disclosed on every draft.

**A preference shapes form, never substance.** Length, ordering, how much reasoning you show are
negotiable. A risk, a cost, an uncertainty, or a decision that is the reader's to make is not. That
rule is stated wherever someone acts on a profile, and it is pinned by hash so it cannot drift
quietly. Asked to store *"no risk warnings"*, HITL records the tone and declines that one clause.

### Fixed

- **`dev-update` Step 4.8 installed nothing.** It read a plugin root set in an earlier Bash call,
  which does not persist, and reported a benign-sounding "not in this build — skipping" while the
  update announced success. Steps 4.7 and 4.8 now resolve the root themselves.
- **The build deleted that fix.** `build.sh` prefixed `$ROOT/shared/...` and then collapsed the
  `$ROOT/` away, shipping a path that expands to `/shared/...`. It now protects any `$VAR/shared/`,
  which also repairs the brownfield observability survey's template copy.
- **`shared/personas.md` was never shipped**, though both commands open by reading it.
- **`generate-docs` pointed at a template path that does not exist** in the installed plugin, and
  had no rule against overwriting a `CLAUDE.md` that already exists.
- **Step 4.6 said "kept your manifest-waivers.yaml"** even when it had just created one.

### Note for existing projects

Run `/hitl:dev-update`. It adds the `.hitl/people/` ignore rule and refreshes the `CLAUDE.md` block,
which is what tells a session these commands exist.

---

## [2.6.5] — 2026-08-14

**If you are on 2.6.4, update before running `/hitl:dev-update` again.** It could leave your change file unusable.

### Fixed

- **The upgrade could destroy your change file, and tell you nothing was wrong.** If your `.hitl/current-change.yaml` wrote its steps in the indented block style rather than on single lines, the migration rewrote none of them, appended every step again at the wrong indentation, and produced a file that is not valid YAML — while its summary table reported all of your steps as kept, and its one warning said the lines *had* been updated. Applying it left the file unreadable: the First Pass check then blocks every pull request with `MALFORMED`, the session gate cannot read your position, and there is no way out but editing the file by hand.

  The migration now parses its own output before writing anything, refuses outright on a file shape it cannot rewrite, and says plainly when it has not updated something. Nothing is written unless it is valid.

- **The upgrade deleted steps your team had added to its own workflow.** Any step whose key HITL does not recognise was dropped from the proposal — leaving your comment about it stranded above the gap — despite the documentation promising that nothing you add is silently dropped. Those steps are now carried through untouched and listed by name so you can see them.

- **`/hitl:dev-update` told you to delete `.claude/settings.json` and rebuild it from a template.** That template is a whole file, not a merge: your permissions, environment, MCP wiring, and every hook that is not HITL's would have gone with it. Any project that sets its own status line triggered this on the first upgrade. It now backs the file up and changes only the specific keys that are wrong, showing you the diff first.

- **`.hitl/statusline.sh` was deleted whether or not it was yours.** If you keep your own script at that path and it is not committed, it was gone with no way back. It is now removed only when git is tracking it — otherwise you are told about it and it is left alone.

- **The upgrade's summary said "keep" for statuses it had just changed.** When a change file had more than one step marked current, the repair rewrote the others and reported every one as unchanged — the same misreading that let a corrupted position get confirmed past in 2.6.1. Changed statuses are now marked.

- **`owner:` was documented as a valid way to name who owns a skip, and rejected by the check.** Accepted now.

- **The release gate could report a review as both present and missing in the same run**, if the record file was named differently from the change. It now identifies records by their contents rather than their filename.

### Changed

- **Skipping the release review now requires a linked waiver, not just a name.** The framework's own rule is that a skip is not a waiver: a required step that maps to a fail-closed check needs someone to have signed for the exception. The release review was the one such step the rule did not cover. Skipping it at 2am is still possible — doing it with nobody signing for it is not.

### On the release workflow added in 2.6.4

Two independent reviews of it, from the perspectives that had condemned it earlier, found nothing further. That is the first clean result it has had, and the reason this release exists is that the same reviews found the problems above in the upgrade path instead — which had not been looked at.

---

## [2.6.4] — 2026-08-14

Four fixes for problems found in real upgrades of a live project, and a new release workflow that is **not yet proven** — read the note at the end before relying on it.

### Fixed

- **The `CLAUDE.md` section 2.6.0 introduced has never actually installed.** Its template path was built with the plugin root doubled, so it resolved nowhere — and the step reported that as *"No HITL block template in this plugin build"*, which reads like a legitimate absence rather than a broken path. Every upgrade since 2.6.0 has silently skipped it. If you upgraded and never saw the section appear, this is why. Run `/hitl:dev-update` again and it will install.

- **`/hitl:dev-update` could move your change back to an earlier step and un-skip work you had deliberately skipped.** When a change file tracked its position only in the `current_step` block — the older format the migration exists to serve — the "repair" picked the first step that was not marked done, which matched *skipped* steps too. On a real project it moved a change from step 18 back to step 2 and reopened a step the team had recorded a decision about. It now trusts the position the file already recorded, and never resumes on a step you skipped. The per-step table also labelled such a change `keep`, as though the value came from your file; a changed status now reads `~ repair`.

- **The same migration silently dropped steps your team had added.** Its step-matching expression never matched anything the current generator writes, so a project-authored step could vanish from the proposal and trailing comments were lost — both of which the migration explicitly promises to preserve. Statuses survived by another path, which is why this looked cosmetic.

- **`statusLine` was written as a string**, which Claude Code rejects, so upgraded projects showed a settings warning in every session — and a hand-correction was overwritten on the next update.

### Added — new, and not yet proven

A **`release` workflow** for publishing a version to users: twelve steps, with an independent adversarial review required before publishing, and a validator that binds a review record to the exact code being shipped. Two optional review offers now appear in the development workflow at the end of Design and Build; both are the lightest class of step and declining one is recorded like any other skip.

**Please treat this as new.** It has been through three rounds of independent review, each of which found real defects that have been fixed — but no round has yet come back clean, and one lens of the final round did not complete. What is unverified is whether the gate protects as thoroughly as it claims, not whether it is safe to have installed: for a project that does not use the release workflow, this adds two optional steps to the breadcrumb and one file under `ci/`. Nothing here changes how an existing change is executed.

### Changed

A skip that names who is accountable is now accepted whether or not the change is running First Pass, in both validators and the docs — previously an honest decline outside First Pass failed CI, and the failure message advised setting `first_pass: true`, which would have recorded something untrue. Accepting the record does not relax what is checked: such a change is now put through the full ruleset rather than exempted from it. Verified across 1,500 generated change files: nothing that passed before fails now.

---

## [2.6.3] — 2026-08-14

> **⚠ If you are an assistant running `/hitl:dev-update` right now, read this before continuing.**
>
> The `dev-update` steps loaded in your context came from the version you are updating **from**. If that was **2.6.2**, its Step 4.6 contains a "Remove dev-repo test suites" loop that deletes files by **filename alone**. That loop is unsafe: it will delete a file the team wrote themselves if the name happens to match, with no way to recover it.
>
> **Do not run the Step 4.6 removal loop from the steps in your context.** Instead, read the newly installed skill and follow **its** Step 4.6:
>
> ```bash
> python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(os.path.join(i['installPath'],'skills/dev-update/SKILL.md')) for i in d.get('plugins',{}).get('hitl@hitl',[])]" | head -1
> ```
>
> The installed version's block is content-gated and cannot delete a file it did not ship. The rest of the update is unaffected — continue normally afterwards.

Two defects in 2.6.2's own fix, both found by independent adversarial review and both reproduced before being acted on. **If you are on 2.6.2, update.**

### Fixed

- **The cleanup could delete a file your team wrote, with no way to get it back.** 2.6.2 removed previously-synced HITL tests by matching the filename, and the release notes said your own tests were safe. They were not. A team writing tests for the shipped validator `check_skips.py` names theirs `test_check_skips.py` — pytest convention, and 2.6.2 invited exactly that by removing the shipped ones. Untracked, such a file was deleted and reported as a successful cleanup.

  Removal now requires the file to be **tracked in your repo** *and* to **match, byte for byte, a version HITL actually shipped** (a manifest of all 17 versions of all 13 files, generated from the plugin's history). A file with a matching name but different content is **reported and kept** — if you edited a HITL test, the edit is yours. The same rule also stops the cleanup following a symlinked directory outside your repo, reaching into a submodule, or deleting the real suite when run inside a HITL fork.

- **The remedy 2.6.2 recommended never ran.** Its notes said to run `/hitl:dev-update`. That did nothing, on any run: the command executes the skill loaded when it started — the *old* one, with no cleanup — and on a second run it stopped at "already on the latest version" before reaching the repair. So the cleanup only fired on the release *after* the one that shipped it.

  `dev-update` now continues past "already current" into the re-sync steps, which reconcile your repo rather than the plugin and are the whole reason to run it again. It also **re-reads its own newly installed copy** after updating, so a fix delivered inside `dev-update` runs on the update that delivers it.

- **A copy path the first fix missed.** `ci/manifest-drift` was copied wholesale, shipping its test file *and* the onboarding machine's compiled `__pycache__` into your repo — which had no bytecode rule in its generated `.gitignore`. Both fixed.

- **`conftest.py` evaded every filter.** pytest imports it at collection, so a platform-only one breaks a consumer exactly as a test file does. Now excluded everywhere tests are.

- **The build never pruned.** A file deleted from the source survived in the packaged plugin from an earlier build — which is how the 2.6.2 test suites kept shipping after the filter existed. The build now fails outright on any test, `conftest.py`, or bytecode under `shared/`.

### Changed

- **The guards that were supposed to prevent this could not fail.** Reverting the fix while leaving a comment that mentioned it kept all six green: one checked for a string that a comment satisfies, and two built their test fixture with a *reimplementation* of the copy logic rather than running the shipped script. They now execute the real code and inspect what lands on disk. The same reversion fails seven of them.

---

## [2.6.2] — 2026-08-14

### Fixed

**Onboarded projects received test suites that could not run there, and they failed the moment anyone ran `pytest`.** The CI-validator sync copied `*.py` wholesale, which dragged each validator's own development test suite into the product repo. Those tests resolve paths that exist only in the HITL platform repo, so a freshly synced project got 3 collection errors under `ci/first-pass/` and 68 failures across `ci/manifest-agentic/` and `tools/manifest-agentic/` — before the team had written anything. Reported as plugin issue #29, and blocking a merge in a downstream project.

The validators themselves were always fine. It is their tests that were never portable, and one of them never could be: it reads the change-file generator out of `start-change/SKILL.md`, a file no product repo has or should have. These exercise HITL's internals, so they now stay with HITL's source.

- **Onboarding ships validators without their tests.** Three bare `cp <dir>/*.py` copies are replaced by a filtered copy.
- **`/hitl:dev-update` removes the test files earlier versions already installed.** Fixing the sync forward does nothing for a project that already has the files, and those are the projects that are blocked. Removal is by exact shipped filename, never a `test_*.py` glob, so tests your team wrote in those directories are left alone.
- **The plugin build never pruned.** Files removed from the source stayed in the packaged plugin from earlier builds, which is how these kept shipping after the filter existed. Cleared.

**If your project has these files, run `/hitl:dev-update` — it cleans them up.**

### Why it lasted

Nothing asserted what the sync actually delivers. Six guard tests now do: the copy sites cannot use a bare `*.py` glob, the cleanup list must cover every test file living in a synced directory, and a repo assembled the way onboarding assembles one must both collect cleanly and still run its validator.

---

## [2.6.1] — 2026-08-14

### Fixed

**A finished change could block every edit in a repo, with advice nobody could follow.** The standard GitHub flow deletes a branch on merge. If the change file outlived the change — which it does whenever the workflow stops short of step 30, as real changes often do — `check-hitl-context.sh` saw the branch mismatch and refused every guarded edit with:

```
HITL CONTEXT MISMATCH: branch 'main' does not match active change GH-58.
  • Run /hitl:dev-switch-context to reload context for this branch.
```

There is no switching to a branch that no longer exists. To anyone who did not know the history, HITL simply looked broken. Found on HITL's own repo, where a change merged weeks earlier would have blocked the next session outright.

A **concluded** change is now distinguished from a **context mismatch**: when the change's `expected_branch` has neither a local branch nor a remote-tracking ref, the hook reports that the change looks complete and names the real remedy — retire it, then start the next one. It still exits 2, so the gate is as closed as it was; only the diagnosis and the advice changed.

The detection is deliberately conservative. **Both** refs must be absent before a change is called concluded, so a branch that has merely not been fetched still counts as present — wrongly declaring a live change finished would push someone into re-intake and lose their step progress.

Five tests, run as real processes against real git repos, since the defect was in how the shell hooks read git state.

### Known gap

`status` is documented as an enum whose `merged` value deactivates a change, and it is set to `planning` at creation — but **nothing transitions it**. Retirement at step 30 only fires if the workflow is walked that far. This release makes the resulting failure self-explaining rather than silent; it does not add an automatic driver, which needs a merge-time trigger.

---

## [2.6.0] — 2026-08-14

A user told us: *"I am not aware of it initially and in later only I learned that there is a HITL plugin I suppose to use."* This release is the answer, and it turned out not to be a documentation gap. HITL already shipped a usage guide, a command directory and a session-start banner. Nothing in a project ever **said** HITL was in use.

### Added

- **A developer's guide** — `docs/getting-started.md`, shipped as `shared/getting-started.md` so Claude can read it to someone in-session without a browser. It is for the person dropped into a project that already uses HITL, not the person adopting it, and it walks one change end to end. It opens by saying you don't have to remember any of it: start work normally, and Claude takes you through intake. Of the 53 commands, it names the four you need.
- **A managed `CLAUDE.md` section.** `CLAUDE.md` is the only thing that can tell a developer this project uses HITL **when they haven't installed the plugin** — no hook runs and no skill exists, so nothing else in the repo speaks. Onboarding now maintains a marker-delimited block that never overwrites the team's file: it creates, appends, refreshes, or stays silent if current. A truncated `HITL:BEGIN` leaves the file untouched rather than swallowing everything after it.
- **`dev-update` Step 4.8** installs that block into already-onboarded projects, so existing repos get it on upgrade rather than only new ones. **Run `/hitl:dev-update` to pick this up.**

### Fixed

- **The `CLAUDE.md` template told Claude to run `/hitl:apply-change`** — a command that does not exist. It's `dev-apply-change`. Referenced twice, in the file Claude reads every session.
- **The template never mentioned `/hitl:dev-start-change`**, the front door for every change.
- **Onboarding skipped `CLAUDE.md` entirely whenever one already existed** — which is every real project. This is the root cause of the complaint above.
- **The intake banner spoke only to Claude.** "you MUST take the user through change intake" is an instruction to the model; a human saw a wall of imperatives about the agent. It now also tells Claude to explain HITL, in its own words, to a user who seems unfamiliar.
- **The template claimed a "31-step workflow."** It is 32.
- **`docs/quick-start.md` taught the obsolete fork-and-clone-the-platform flow** and never mentioned `claude plugin install`, while `docs/README.md` pointed newcomers to it *first*.
- **The README had no row for the most common case** a developer is actually in — "I've been asked to work on a project that already uses HITL." Every row addressed the person adopting HITL. That row is now first.
- **`/hitl:help` never mentioned the guide**, despite being where people land when lost.
- A broken README anchor (`#quick-start--existing-project`) that never matched its heading.

### Removed

- **`ai/shared/templates/settings-template.json`.** Its own first line said "Copy this to `.claude/settings.json` in your project root." Anyone who did got a hook that doesn't exist (`check-lld-exists.sh`) and **none** of the enforcement hooks — a project with zero HITL enforcement. It was never shipped and nothing referenced it. Its one real asset, the measured permission findings, moved to `ci/first-pass/migrate_project.py` beside the `ALLOW`/`DENY` they govern.

### Note

Nothing here changes how a change is executed. If you're on 2.5.0 and your projects are already onboarded, `/hitl:dev-update` gets you the `CLAUDE.md` block and the guide.

---

## [2.5.0] — 2026-08-13

First Pass shipped in 2.4.0 as requirements, a validator and a skill body. This release is what happened when six people actually used it. Three of the complaints that started it — "HITL is overkill for a bug fix", "it keeps asking permission for reads I already approved", "it makes me read too much" — each traced to a mechanism that was specified but never wired.

### Fixed

- **The driver never set `first_pass`.** Every mechanism gated on that flag — the skip ledger, brief mode, the permission policy — was unreachable in a real run. The Step 6 generator now emits it, along with `skips[]` and the tier attribution.
- **Step 6 clobbered the skip ledger it had just written.** The change file was moved into place unconditionally, so a generator that failed still overwrote good state with a truncated file. The write is now guarded on exit status and a non-empty temp file, and refuses to publish otherwise.
- **`starter` dispositions never certified.** The generator emitted `artifact_path` where the validator reads `starter_artifact`, so every starter step failed the gate. The e2e test that should have caught it only covered `skip`.
- **A false tier claim shipped in five files.** The docs said tier ≤1 demotes impact, packet, arch_review, qa_verify and rollout from `floor` to `standard`. Those five are `crit_by_tier: {3: floor}` — the demotion is 3→2, and 2→1 moves only `integration_verify`. Corrected in all five places, with three tests that pin the real matrix so the claim can't drift again.
- **Resurfacing dropped narrowed scopes.** A recorded skip whose scope shrank was never written back, because the roll-up only persisted when something was *added*. Path overlap is now compared segment-wise, so `src/app` no longer matches `src/application`.
- **Preflight skipped its own check on an empty file list.** `--changed-files` with no entries is falsey, not absent, so the guard read it as "no filter given" and passed everything.

### Added

- **Brief mode.** `first_pass: true` selects a directive that trims step output to what the reader has to act on. The intake dump — the single largest source of "too much reading" — collapses to a phase summary with the detail available on request.
- **A reduced-friction permission policy (CR-15).** A `PreToolUse` hook that emits `allow` for reads already covered by the change's declared scope. It only ever emits `allow` and never `deny`, so it can widen what proceeds without becoming a new way to block.
- **A real light path for tier 1.** Previously the tier was recorded and then largely ignored. Step 3b confirms it, records who set it and why (`tier_set_by` / `tier_reason`), and the light path is now materially shorter rather than nominally so.
- **Artifact retirement at step 29.** Promotion clears per-change working files while protecting `skip-ledger.yaml`, so `.hitl/` stops accumulating handoff and review-request scratch on `main`.
- **An adversarial stance for the five reviewer agents.** Each now opens with "try to refute, not to confirm". Reviewers that set out to confirm a design find it confirmed.
- **`ci/wiring/test_wiring.py`** — 34 tests over reachability, consistency and completeness. Every defect above is a wiring defect: a mechanism that exists, a mechanism that's referenced, and nothing connecting them. Unit tests could not see that class, because each end passed on its own.
- **`ci/first-pass/migrate_project.py`** — migrates an existing project's permission block and audits its change file, failing loud on an unmergeable block rather than guessing.

### Changed

- **The permission allowlist template shrank to one entry.** Measured against a live session: output redirection (`>`, `>>`) rides along on any match, including an exact entry with no wildcard, so *every* allowlist entry grants "write this command's stdout anywhere". `&&` and each pipe segment are checked, so those aren't the risk. The template now carries what's defensible plus the residual channels it does not close.
- **CR-1 amended** to permit a tier-gated batch decline, and roll-up append extended to the remaining four routes.
- **`.hitl/` is committed again**, with the scratch ignored: `*.tmp`, `*.migrated`, `first-pass-choices.json`, `backups/`. The prior rule ignored the whole directory, which discarded the handoff record the next step reads.
- **`init-project.sh` emitted pre-#14 hook wrappers** that `dev-update` could not detect, so affected projects were never offered the migration. Existing projects are reached by `dev-update`.

### Note for existing projects

Run `/hitl:dev-update`. Projects onboarded before this release carry the old hook wrappers and the wide permission block; the update detects and migrates both.

---

## [2.4.8] — 2026-08-08

### Fixed

**The reference guard shipped in 2.4.7 was porous — a second independent audit broke it with fixtures.** The user-facing defect it was written for stayed fixed, but the check meant to stop it recurring was measuring the wrong thing. Rewritten around path resolution:

- **`../` substring counting replaced with real resolution against the packaged tree.** Counting was wrong in both directions: `foo/../bar.md` climbs nowhere yet counted 1, `a/../../../b.md` climbs two yet counted 3, and a two-level escape into `docs/` — which the build never packages — passed clean. Worse, the threshold could not be right for both trees at once, because a skill sits one level deep once built and one *or two* in source. The rule is now "does the resolved target stay inside `ai/`", which is the actual question, since `ai/` is what the build packages.
- **Existence is checked for any local target, file or directory.** Gating it behind `endswith(".md")` was half of why the original defect was invisible — it pointed at a directory. A directory link that merely doesn't exist used to sail through untouched.
- **Reference-style links (`[label]: path`) are now checked.** The inline-only pattern never saw them, so an escape written that way was silently exempt.
- **Link titles and angle brackets are parsed.** `[x](file.md "Title")` and `[x](<spaced name.md>)` previously failed the `.md` test on the raw string and were skipped entirely.
- **Fence tracking records the opening delimiter length.** A naive boolean toggle turned inside-out on nested fences: a ```` fence containing an odd number of ``` fences leaked emitted-template links back out as hard failures — exactly the false positive 2.4.7 added fence-stripping to prevent. An unterminated fence is now a hard error rather than silently blanking the rest of the file, which had re-created the "silently skipped" failure mode from a different direction.
- **Findings report the line of the offending link.** Every reference finding used to report the frontmatter boundary, so a bad link on line 480 of a 497-line skill was reported at line 6. A check whose whole purpose is to point at one link could not locate it.

Twelve regression tests cover each case, including the legitimate `../../shared/` hop and the emitted-template link that must stay silent. **Five fail against 2.4.7's linter.**

---

## [2.4.7] — 2026-08-08

### Fixed

**A worked-example link was broken in every installed plugin.** `dev-start-change` pointed at `[docs/examples/first-pass/](../../../docs/examples/first-pass/)`. Three levels up from `skills/dev-start-change/` lands above the plugin root, and the build ships no `docs/` — so the link resolved in the source repo and pointed at nothing for every user. It now links to the file on GitHub. Found by an independent audit of the 2.4.6 release.

**`skill-lint` could not have caught it — three ways.** All fixed:

- **Unresolvable references were silently skipped.** `if not ref.is_file(): continue` meant the depth and table-of-contents checks only ever ran on links that already resolved, so a dangling reference passed a clean 53/53 run. Missing targets are now a hard failure.
- **The `.md` filter ran before everything else.** The broken link pointed at a *directory*, so `endswith(".md")` skipped it outright — the filter, not the rule, is what let it through. Path escaping is now checked first, for any local link, because escaping is a property of the path rather than of the file type it names.
- **No check existed for links that escape the skill directory.** This is the class the source tree cannot reveal: the target sits right there during development and disappears at packaging time. Anything climbing more than two levels now fails, with the fix named in the message.

The reference scan also now ignores fenced code blocks. A link inside a fence is usually content the skill *emits* — `architect/review-existing` writes an HLD index template containing `[Deployment View](deployment-view.md)`, correct in the user's docs directory and meaningless relative to the skill. Resolving those reported a defect that did not exist, and "fixing" it would have corrupted the emitted template.

**`commands/` is now linted.** Claude Code merged custom commands into skills, and the plugin's five command files do not set `disable-model-invocation` — which makes them the model-invocable surface, the descriptions Claude actually chooses between. Globbing `SKILL.md` alone left exactly that surface unaudited. Frontmatter and description are advisory rather than hard gates there, matching the Claude Code reference ("All fields are optional. Only `description` is recommended"), and `docs/examples/` is excluded as the sample project it is. `dev-check-implementation` and `ops-monitor-canary` gained explicit when-to-use triggers.

**Version-pinned narrative removed from `dev-update`'s body**, per the standard's guidance against time-sensitive content: the step described what was true "until 2.4.5" rather than what the step does.

---

## [2.4.6] — 2026-08-08

### Fixed

**Skill authoring brought into line with Anthropic's documented Agent Skill rules.** Audited all 53 shipped skills against the [skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices). Most were already compliant — names, description lengths, third-person voice, forward-slash paths, one-level-deep references and reserved-word rules all passed untouched. Three real defects:

- **`dev-start-brownfield` exceeded the 500-line body limit** (521). The observability survey — a self-contained sub-procedure with its own tables — moved to `observability-survey.md`, referenced one level deep from `SKILL.md` per the progressive-disclosure pattern. Body is now 461 lines.
- **Two reference files over 100 lines had no table of contents** (`roi-estimation.md`, `workflow-steps.md`). The rule exists so a partial read still reveals a file's full scope; both now open with one.
- **The `generate-docs` command copy under `.claude/` had no frontmatter at all**, so it failed the frontmatter gate.

**`hitl:agentic-intake`'s description rewritten for discovery.** It is one of only two skills Claude may auto-select (the other 51 are `disable-model-invocation: true`), so its description is what decides whether it is ever chosen. It opened with internal jargon — "the right-sizing front door to the compound-agentic surface (FR-28)" — and buried the trigger in the last clause. It now leads with what it does, then names the triggering situations in terms a request would actually contain (multi-agent systems, tool-using agents, orchestrator/worker graphs, agent-to-agent calls).

**`skill-lint`'s table-of-contents check was too permissive.** It accepted any `## ` heading in a reference file's first 15 lines as a table of contents, so a file that merely *started with a section* passed while giving a previewing reader nothing. It now requires an actual contents list. That is why the two files above were never flagged.

With these, `skill-lint` reports **54/54 passing, 0 failures, 0 warnings** — it had been failing on `main`.

**Note on portability:** HITL's skills use `argument-hint` and `disable-model-invocation`, which are Claude Code-only fields. They are correct for a Claude Code plugin, but uploading these skills to claude.ai or the Skills API would fail with `Unexpected key(s) in SKILL.md frontmatter`, which allows only `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`. Distribution stays Claude-Code-only unless that changes.

---

## [2.4.5] — 2026-08-08

### Fixed

**YAML comments no longer change hook behaviour (plugin issues #25, #23 item 3).** `hitl_scalar()` returned the whole remainder of a line, comments included. Three of its call sites are load-bearing *comparisons*, not display, so annotating a field — the natural thing to write — silently changed what the hooks did:

- **`status: merged   # PR #42 merged 2026-08-07` never deactivated the change.** It stayed nominally active forever; because it was also merged its branch was gone, so it then failed branch reconciliation on *every* subsequent branch — a permanent mismatch banner plus `check-hitl-context.sh` blocking source edits, pointing at `/hitl:dev-switch-context`, which cannot fix a change that is already finished.
- **`expected_branch: "issue/100-x"   # created …` reconciled as `mismatch` on the correct branch** — the false positive of exactly the check issue #12 added.
- `tier` / `change_id` comments rendered verbatim into the status line.

Both helpers now share one awk cleaner (`_HITL_AWK_CLEAN`); the ordering is load-bearing and documented at the definition — **comment first, then quotes**, because stripping quotes first leaves the closing quote stranded once a comment follows it. A `#` inside a quoted value is preserved (YAML treats `#` as a comment only when preceded by whitespace). Note `hitl_workflow_field()` was cited in the report as already correct; it was not — it stripped quotes before comments too, and is fixed here as well. 16 regression tests in `ci/hooks/test_steps_scalar.py`, 7 of which fail against 2.4.4.

**The status line exited 1 on the common path (issue #23 item 2).** Both trailing segment prints are short-circuit `&&` tests, so with no platform segment — a normal project — the last test was the script's exit status and it exited 1 having printed a correct line. A host may read that as failure and suppress the line, and a project wrapper that `exec`s the script adopts the status too. Now ends with an explicit `exit 0`.

**`dev-update` checked that `statusLine` existed, not what it pointed at (issue #23 item 1).** A repo onboarded before the `.hitl/hooks/` layout carries a pre-plugin `.hitl/statusline.sh` that hardcodes the 32-step development flow. `grep "statusLine"` matched it happily, so the stale script survived every upgrade and rendered `Step 3/32` for a 6-step `docs` change — while `welcome.sh` rendered the same change correctly, leaving the human and the model reading two disagreeing status lines. Step 4 now asserts the *target* (`hooks/statusline-hitl.sh`) and deletes a legacy `.hitl/statusline.sh` during re-sync.

**`dev-start-migration` never installed the First Pass validator (issue #27).** It was the only onboarding entry point without the install block, so migration-onboarded projects had no `ci/first-pass/`, no `.github/workflows/first-pass-check.yml`, and therefore **no enforcement of the skip ledger** — skips could be recorded on every change with nothing to certify them. The block now matches `dev-start-brownfield`. Separately, `dev-start-change` Step 4b resolved the validator by a repo-relative path with no fallback, so its absence read as *"First Pass is unavailable on this project"* rather than *"the tooling was never installed"*; it now falls back to the plugin's own copy and says plainly what to run.

**The change-context schema and its worked example were never shipped (issue #28).** Three skills instruct the model to write `.hitl/current-change.yaml` "using the schema at `docs/changes/change-context.schema.yaml`", but `build.sh` packages `ai/` only — `docs/` never reaches an installed project, so the reference dangled everywhere the plugin was actually used. Both files moved to `ai/shared/templates/`, which the build already syncs, and now ship as `shared/templates/change-context.schema.yaml` and `GH-000-example.yaml`. All five references updated (the issue named three). The typed, load-bearing fields are now called out at the point of writing: `first_pass` must be a literal boolean, `status` is an enum whose `merged` value deactivates the change, `expected_branch` is matched exactly.

**The semgrep SQL-injection rules missed implicitly-concatenated f-strings (issue #45).** `.semgrep/security/sql-injection.yaml` matched `f"..."`, `f"""..."""`, `"..." + x` and `"...".format(...)`, but not `execute(f"..." "...")` or `execute("..." f"...")` — the shape you get writing long SQL across lines without trailing-space bugs, which formatters produce. The same hole existed in `no-fstring-in-sqlalchemy-text`. The failure mode is worse than a missed finding: a team fixes every flagged site, sees `semgrep --error` return 0, and concludes a file is clean while the interpolation is still there. Found via `dilipkpoluru/PSR-Works#382`, where a migration containing three f-string `op.execute()` calls reported two — the unreported one being a destructive `DELETE`. Both rules gain the two implicit-concatenation patterns, with a seven-shape regression fixture under `ci/semgrep/` asserting in both directions (every interpolated form flagged, every plain literal not). Four of the twelve assertions fail against the previous rule.

**Five of seven convention rules were scoped to one repo's directory layout (issue #46).** `pydantic-validation`, `tenant-isolation`, `retry-wrapper` and both `subclass-contracts` rules pinned `paths.include` to `V2/app/**` — a single product repo's structure. `init-project.sh` copies `.semgrep/` into every onboarded project, so in any repo not using that layout those rules matched no files and always passed: the gate reported green because the rules never ran. A scan of this repo ran 2 of 7 rules.

The scoping is gone. Rules whose patterns are self-limiting (`class X(MutatingTool)`, an HTTP client bound by `metavariable-regex`, a route decorator plus a `Request` parameter) need no directory filter at all. `qdrant-must-filter-brand-id` did need one — bare `$CLIENT.search(...)` also matches `re.search(...)` — so the receiver is now constrained by name instead of by folder, which is layout-independent and more precise.

Removing the scope exposed a second defect underneath it: **`controller-must-use-pydantic-models` could never fire at all.** Its `pattern-not` (`$BODY: $MODEL`) also bound the very parameter the positive pattern looks for (`req: Request`), cancelling every match. Path scoping had hidden it — a rule that never runs is never noticed for also never matching. `$MODEL` is now constrained so a handler can legitimately take both a `Request` and a validated body.

All seven rules now run, each covered by a fixture asserting both directions. A guard test parses `paths:` and fails if any rule is ever scoped to a project-specific path again.

**The rules are now generic, not one customer's conventions.** Unscoping them exposed a deeper problem: three encoded a *specific* stack that HITL never documented and most customers do not use — Qdrant with a `brand_id` tenant key, a helper named `retry_external_call` with clients named `httpx_client`, and a `MutatingTool` base class. (`qdrant` appears in zero HITL docs; `MutatingTool` appears only under `docs/examples/`.) While path-scoped they were merely inert; once unscoped they would have fired wrongly in any repo with a different stack. Each now keys on something that generalizes:

- **`qdrant-must-filter-brand-id` → `vector-search-must-be-tenant-scoped`.** Covers Qdrant, Pinecone, Weaviate, Chroma, Milvus, pgvector and generic vector-store/embedding-store receivers across `search` / `query` / `similarity_search`, and requires *any* filter (`query_filter` / `filter` / `where` / `filters`) rather than one named tenant column. Which key you scope by is your business; that the query is scoped at all is the convention.
- **`external-calls-must-use-retry-wrapper` → `external-calls-must-be-retried`.** Keys on the HTTP *library* (`requests`, `httpx`, `aiohttp`, `urllib`) instead of a project's variable names, and accepts any retry-shaped decorator or wrapper — tenacity, backoff, or your own. Downgraded to `LOW` confidence to match its advisory nature.
- **`controller-must-use-pydantic-models` → `request-body-must-be-validated`** (file renamed `pydantic-validation.yaml` → `input-validation.yaml`). The old rule required a FastAPI route decorator plus a parameter annotated `Request`, and named pydantic as though it were the only validator — so it said nothing about Flask, Django or aiohttp. It now matches the *shape* the message always described: a raw body flowing directly into a call. Covers `await request.json()` (FastAPI/Starlette/aiohttp), `request.get_json()` (Flask), `request.POST` / `.body` (Django) and `.data` / `.form` (DRF), and treats a validator as compliant by callee name — pydantic, marshmallow, DRF serializers or a project's own `validate_*` all satisfy it.
- **`mutating-tool-must-*` → `side-effecting-tool-must-*`.** Matches any base class ending in `MutatingTool` / `SideEffectingTool` / `WritingTool`, so a project is covered whatever it calls its own base, while a `ReadOnlyTool` never matches. The convention is now documented in `docs/patterns/idempotency-keys.md` — which the rules already cited despite that doc never mentioning the class name.

`idempotency_key` stays an `ERROR`: it is HITL-canonical, appearing in the manifest schema (`idempotency_key`, `side_effect_key`, `side_effecting`) and in the pattern doc's checklist. `_describe_plan` is now a `WARNING`, because "PLAN mode" appears nowhere in HITL's schema or patterns — it is a convention, not a contract, and was previously blocking as if it were one.

A second guard test fails if any shipped rule names one customer's identifiers again.

**Rules can be opted out of.** Installing every absent rule on update would resurrect one a team deliberately deleted, every time. Both the onboarding installer and `dev-update` Step 4.7 honour `.semgrep/.hitl-optout` — one path per line, `#` comments allowed — so a single-tenant project can drop the vector-store rule and have it stay dropped.

**Semgrep rules were never shipped to plugin-installed projects, and never updated after onboarding (issue #47).** `build.sh` did not package `.semgrep/` and no onboarding skill installed it — only `tools/scripts/init-project.sh`, which copies from a `hitl-dev-platform` checkout. A plugin-onboarded repo therefore had **no rules at all**, and `/hitl:dev-check-conventions` failed outright with `unable to find a config; path .semgrep does not exist` (exit 7). Nothing re-synced them either, so even where rules existed a fix like #45 above never arrived.

- The build now ships them as `shared/semgrep/`, alongside an `install.sh` the three onboarding skills invoke.
- **Onboarding installs only what is absent.** A product repo's `.semgrep/` is co-owned — teams add their own rules and tune the shipped ones — so onboarding never overwrites.
- **`dev-update` Step 4.7 re-syncs**, treating the three cases differently: a rule the repo lacks is installed; an unmodified rule is refreshed silently; a **locally modified** rule is shown as a unified diff and requires explicit confirmation before it is overwritten. Rules the project added itself are never touched and never reported as drift. This is the lesson of the 2.4.4 Step 4.5 fix applied before the damage, not after.

**Branch slugs no longer end in a hyphen (issue #26).** The slug snippet piped `cut -c1-50` *after* the `sed` that trims leading/trailing hyphens, so the `cut` re-introduced the trailing hyphen the `sed` had just removed and every issue title over 50 characters produced `issue/N-…-`. `cut` now runs before `sed`, in both `dev-start-change` and `dev-apply-change` (the report named one).

---

## [2.4.4] — 2026-08-03

### Fixed

**`dev-update` change-file migration no longer destroys project-authored content (issue #22).** Step 4.5 regenerated the entire `workflow:` block from the catalog, silently dropping data the catalog cannot represent — on the exact path a user hits when upgrading. The printed table showed every step as `keep`, so the loss was invisible unless you diffed the `.migrated` file by hand.

- **Per-step `owner:` (and any other user-added field) is preserved.** The generator emitted only `n, key, label, status`; it now rewrites each step *line in place* and carries every non-core key across by `key`. `phase`/`substep` are refreshed from the catalog (they were being dropped too).
- **In-block comments survive.** Trailing per-step comments and standalone comment blocks — including out-of-catalog steps recorded there (e.g. tier-3 security gates the catalog can't hold) — are left byte-for-byte. The migration is now line-level surgical, not a whole-block replace.
- **Duplicate `current` is repaired.** The single-`current` guard only fired when *no* step was current; two `current` steps now resolve to one (linear-progress).
- **No-op short-circuit.** When the catalog is unchanged the `workflow:` block is left byte-for-byte intact and only the version stamps move.
- **The actual unified diff is printed** at the confirmation prompt, so any change is visible before you apply.
- The version-probe blocks used a bare `except:` that caught the `sys.exit(0)` success path (`SystemExit`) and printed a spurious `NOT_FOUND` after the correct version — now `except Exception:`.

Verified by reproducing every loss on a multi-owner tier-3 fixture, then confirming the fixed generator (extracted verbatim from the skill) preserves all of it, the migrated file parses, and the real breadcrumb parser reads it.

---

## [2.4.3] — 2026-07-27

### Fixed

**First Pass — closes a Codex adversarial review (2 CRITICAL + 6 HIGH + 2 MED + 1 LOW).** An independent clean-context review found gaps the four Fable rounds missed, chiefly in *plan completeness* and the *onboarding copy flows*:

- **Completeness bypass (CRITICAL):** deleting a load-bearing step (a `floor` step at tier, or `no_omit`) from the plan entirely — rather than marking it skipped — left no record to inspect and passed clean. Now `INCOMPLETE_PLAN` (non-waivable): every floor/no_omit catalog step must be present in the plan.
- **`first_pass` type (CRITICAL):** a falsey non-boolean (`[]`, `0`, `""`) disabled all enforcement. Now type-strict — a present-but-non-bool value is `MALFORMED` and still enforces; only literal `false`/absent is back-compat clean.
- Missing/null step status now blocks (`INVALID_STATUS`); an unmarked starter artifact now blocks (`STARTER_MARK` is non-waivable) and the CI gate runs on every PR so an artifact-only edit can't bypass it.
- `derive.py verify` now catches a *deleted* crit/no_omit/crit_by_tier field (was only compared when present); the permission classifier fails safe on malformed inputs (a string `scope_paths`, a null read path); resurfacing redacts hyphenated blame variants and no longer crashes on malformed roll-up entries.
- Onboarding is convergent: `init-project.sh` no longer lets a stale `ci/first-pass` dir suppress the install, and the `dev-update` re-sync stages copied files even when an optional path is absent.

Hardened across five clean-context adversarial passes (four Fable + one Codex); each finding fixed by mutation and regression-tested.

---

## [2.4.2] — 2026-07-27

### Added

**CI-validator install gap closed for existing repos + the compound-agentic validator.**

- **`/hitl:dev-update` now re-syncs the copied-in CI validators.** On plugin upgrade it refreshes the repo's CI tool code (plugin-owned) and **installs** validators added after the repo was onboarded — so a repo onboarded before 2.4.x retroactively gets `ci/first-pass/` (validator + co-located catalog + CI gate) without re-onboarding. Repo-owned files (waivers, the change ledger, customized workflows) are preserved.
- **Compound-agentic validator (#10) is now auto-installed.** `dev-start-from-prd`, `dev-start-brownfield`, `init-project.sh`, and the `dev-update` re-sync copy `ci/manifest-agentic/` (the fail-closed system-manifest validator) + `tools/manifest-agentic/` into a product repo — closing the same install gap First Pass had. `pm-design-feature`'s repo-relative validator call now works out of the box. Self-contained; the repo's own `manifest-waivers.yaml` is preserved (a fresh repo gets the empty `waivers: []` template).

---

## [2.4.1] — 2026-07-27

### Added

**First Pass — onboarding auto-copy.** The First Pass validator now installs into a product repo automatically, closing the "ships to `shared/` but nothing copies it in" gap. `/hitl:dev-start-from-prd`, `/hitl:dev-start-brownfield`, and `tools/scripts/init-project.sh` now copy `ci/first-pass/` (the fail-closed validator), its criticality **catalog** co-located as `ci/first-pass/workflows.yaml` (the CI-trusted source), and the `.github/workflows/first-pass-check.yml` gate into the repo. `check_skips.py` resolves the co-located catalog automatically (no `--workflows` needed), so a First Pass PR is enforced in CI end-to-end. Verified by running the validator from a simulated onboarded repo (clean → exit 0, unauthorized floor skip → exit 2).

---

## [2.4.0] — 2026-07-27

### Added

**First Pass (EPIC #FR-29).** A right-sized, **thin-whole-first, skip-with-record** way to run any workflow, for teams (PMs especially) who want to ship a basic version fast and iterate. It is a mode *overlay* on the existing 31-step workflow (not a new workflow), extending the tier system — it leverages HITL's "think holistically, implement incrementally" philosophy: a thin pass through the whole, then deepen.

- **Criticality on every step.** Each `development` step carries a tier-resolved `crit` (`ceremony | standard | floor`) in the workflow catalog, with `crit_by_tier` and `no_omit`. After HITL determines the plan, the team answers a single disposition **menu** (one pass, brief mode) per step: *do-now / starter / defer / decline*, constrained by criticality (`floor` → risk-accept only; TDD RED/GREEN → `no_omit`, starter-only).
- **Never silent, floor protected.** Every skip is recorded (`{step, crit, actor, reason, ts, disposition}`) in a `skips[]` ledger + a project roll-up, in neutral language. The fail-closed validator `ci/first-pass/check_skips.py` blocks a silent skip, an unauthorized floor skip (needs the accountable role's `ack_by`, and a linked waiver for a hard-gate step — a skip ≠ a waiver), or a TDD omission — all non-waivable. Hardened across **4 clean-context adversarial rounds (converged)**.
- **Give a starter, not a gap.** For an artifact-producing step, First Pass offers an *honest-minimal* starter marked `needs-enhancement` — e.g. the acceptance-criteria starter is simply *"a working version of the system exists and runs"* — never a fabricated full artifact.
- **The record has teeth.** Deferred steps seed fast-follow tickets; recorded skips resurface politely (escalating by criticality, never blaming) at the follow-up, the next change touching the same area, and incident review.
- **Breadcrumb + friction.** The trail shows the shape at a glance (`⊘` skipped, `◐` starter, distinct from open `·`); routine in-scope reads/edits proceed without permission prompts while critical/irreversible/outward actions still prompt (never "bypass all safety").
- Generalizes the FR-28 Advisor skip pattern to the whole workflow; reuses tiers, #10 waivers, and the issue model. Requirements: `docs/01-product/first-pass/requirements.md`; design: `docs/design/first-pass/`; worked example: `docs/examples/first-pass/`; product-repo CI template: `ci/workflows/first-pass-check.yml`.

---

## [2.3.0] — 2026-07-24

### Added

**Agentic Design Advisor (EPIC #35, FR-28).** A PM-lane front door for the compound-agentic surface: `hitl:agentic-intake` elicits an agentic system's shape and risks, recommends a right-sized set of controls (a recommendation report, not 8 commands), records the decisions, renders an evolving system map, and hands off a **neutral** design handoff — then a human authors the `system-manifest.yaml` from it, which `ci/manifest-agentic` (#10) validates.

- **The load-bearing boundary:** the Advisor **authors no manifest field** (not even `kind`). It recommends and records; #10 needs no input from it and validates the human-authored manifest independently. The neutral handoff is certified against the entire #10 field vocabulary before hand-off (`handoff_authors_no_manifest_field`), and every emitted channel is scalar-coerced so no nested manifest fragment can ride through.
- **`tools/agentic-advisor/`** — `compose.py` (relevance → report sections + a recommended floor from safety factors, no Tier input), `records.py` (canonical state, neutral handoff, decision record, rerun reconcile with typo-surfacing warnings), `render_map.py` (terminal + Mermaid), `askwhen.py` (a small AST-restricted safe evaluator for catalog predicates — no arbitrary code).
- **`ai/shared/agentic/catalog.yaml`** — the 16-lens curated elicitation data.
- **Proportionate, fail-safe, deterministic:** the floor is advice (a skip is recorded, never a #10 waiver); a partial/malformed state never crashes the intake; the same scenario yields the identical report. Hardened across four adversarial review rounds.

## [2.2.0] — 2026-07-24

### Added

**Compound-agentic system delivery surface (EPIC #10, FR-26).** HITL now governs products built as a **graph
of deterministic services + simple/deep agents** with sync, async, and event edges — not just single agents.
Everything is additive and per-check activated: a legacy or deterministic manifest validates unchanged and
needs no new registry (proven by test, not asserted).

- **Manifest schema extensions** (`system-manifest.schema.yaml`): a top-level `interactions` edge model (the
  element identity is `id`, so parallel edges between the same pair are representable), `orchestration`,
  `segments`, `sagas`, and an `observability` block; `DomainEntry` gains `kind`/`kind_rationale`/`identity`/
  `uses`/`memory`/`lifecycle`/`deep_agent`/`evals`. `interaction_matrix`/`depends_on`/`events_*` become
  generated projections when `interactions` is present.
- **17 fail-closed validators** (`ci/manifest-agentic/check_manifest_agentic.py`), each activating only on its
  own data. A **schema gate** runs first — an unknown enum value or unknown field is a non-waivable blocker, so
  a typo can never silently switch a governance check off (fail-*closed*, not fail-open). Then: graph integrity
  (topology, references, classification, scope grammar); trust + privilege
  (per-leg determinism boundary, necessary-and-sufficient capability check with over/under/ceiling,
  non-human authorization, policy resolution); reliability + state (async idempotency/DLQ, memory ⇄ uses
  reconciliation, durable lifecycle, deep-agent structure, declared-saga well-formedness, a
  compensation-gap **advisory**); and the **observability floor gate** + per-agent-plus-e2e eval coverage.
  A general `manifest-waivers.yaml` lets a human record a tier-appropriate exception for any blocker — never
  a silent skip; `unparseable`/`unknown_field`/`schema_invalid` and `system:`/`registry:` loci are
  non-waivable.
- **Generated posture views** (`tools/manifest-agentic/generate_views.py`): topology (Mermaid), privilege,
  tool matrix, observability, projections, and the eval index — deterministic, with a `--check`
  regenerate-and-diff so a view can never drift from the manifest.
- **Baseline eval generator** (`tools/manifest-agentic/gen_baseline_evals.py`, CR-20): seeds a `baseline_only`
  eval spec per agent + e2e segment (from `owning_fr`, facade failure modes, privilege boundary), merge-by-id
  preserving human-edited cases — HITL seeds, humans approve.
- **Design-flow integration:** `pm-design-feature` and `ai/codex/AGENTS.md` gain the gate→probe→route rule
  (agentic surface → topology probe → the compound track) and the compound-agentic authoring checklist.
- **Docs + worked example:** `docs/patterns/compound-agentic-systems.md` and a validator-clean reference
  system at `docs/examples/compound-agentic/` (manifest + registries + eval specs + generated views).

Conformance: 43 per-rule validator cases + generator/schema suites, all green; the worked showcase passes the
full validator end-to-end at Tier 2. **Governs-not-runtime:** HITL ships the schema, validators, generators,
and posture views — no runtime, broker, durable-execution engine, dashboard, or eval runner. Heavier items
(universal eval coverage, the saga required-when model, delegated per-interaction authority, sync-reliability
declarations, and eval-adapter *execution*/result ingestion) are a scoped follow-on (#42).

---

## [2.1.1] — 2026-07-13

### Fixed

**`delivery_ready` is no longer a deploy-gate bypass** (Codex round-6 non-blocking note,
now closed). `check-platform-ready.sh` previously honored `delivery_ready: true` before
any schema or canonical validation, so a hand-flipped flag in an otherwise invalid
register released a Tier 2+ production deploy. The gate now re-derives readiness from
the items and waivers themselves: the flag is the recorded outcome, never a release
mechanism. A register whose flag says true but whose items show open gaps, missing
canonical items, or schema violations blocks — and the output names the contradiction.
Honest registers are unaffected (flag true with all items verified/waived still passes).
Regression suite grown to 60 cases (`ci/hooks/test_check_platform_ready.py`).

---

## [2.1.0] — 2026-07-13

### Added

**Platform-bootstrap workflow (issue #21).** HITL now codifies the bridge from "onboarded"
to "ready for customer delivery" — previously untracked prose (greenfield), display-only
survey verdicts (brownfield), and simply absent (migration's back half). New pieces:

- **`platform` workflow** in the catalog (Survey → Verify → Deliver → Operate → Ready,
  17 steps; the Parity and Cutover phases apply only to migrations via `cond: migration`).
  Long-lived and per-project: progress lives in the readiness register, never in
  `.hitl/current-change.yaml` — roadmap items are ordinary HITL changes.
- **Platform readiness register** (`docs/04-operations/platform-readiness.yaml`, template
  shipped): machine-readable layer D/E/F items with required evidence, recorded waivers
  (owner + revisit + tier_limit), and a derived `delivery_ready` flag.
- **`/hitl:ops-plan-platform`** (new skill): derives the register from the entry artifacts
  (brownfield onboarding verdicts / PRD NFRs + HLD deployment view / migration source
  analysis), generates the roadmap as GitHub issues, renders status, and verifies the
  four-pillar Definition of Ready.
- **Hard production-deploy gate** (`hooks/check-platform-ready.sh`, run by
  `/hitl:ops-deploy` pre-flight): Tier 2+ production deploys are blocked while the project
  is not delivery-ready, unless every open item (`gap` or `accepted_gap`) carries an
  adequate, unlapsed waiver. Staging and canary are never gated. The gate **fails closed**
  when it cannot positively validate the register: no PyYAML-capable interpreter,
  unparseable YAML, a register with zero items, an item with an unknown status, a
  `verified` item without evidence, an incomplete waiver (owner + valid ISO revisit +
  integer tier_limit + reason are all required), a missing or duplicate item id (ids are
  the waiver join key), an invalid `project_kind` or `schema_version`, a register missing
  any canonical item (D1-F3, plus P1-C3 on migrations — truncated registers block), `na`
  on a canonical readiness item (waivers are the escape hatch, `na` is not), a migration
  register with Parity/Cutover items left `na`, a canonical item filed under the wrong
  layer, duplicate waiver entries for one item, or any unexpected error (hardened across
  five independent validation rounds that found fail-open paths). Environment strings are whitespace-trimmed before
  matching. Regression suite: `ci/hooks/test_check_platform_ready.py`.
- **Statusline platform chip**: shows open-gap count while the project is not
  delivery-ready; disappears permanently once it is.
- **Entry-point wiring**: brownfield steps 5-6 now persist their pipeline/observability
  verdicts to the register (previously conversation-only); `start-from-prd` gains a tracked
  step 5 (generate platform roadmap) replacing its untracked closing prose checklist;
  migration seeds the register with the Parity/Cutover layers and its completion criterion
  now includes legacy sunset — ported code with the legacy still running is not a finished
  migration.

Design package: `docs/design/platform-bootstrap/` (decisions D1-D6 locked 2026-07-11).
PRD: FR-25.

## [2.0.1] — 2026-07-11

### Fixed

**Intake gate: absolute paths never matched the bootstrap exemption, and out-of-project files
were wrongly blocked (issue #20).** `check-hitl-context.sh` classified paths after only stripping
a leading `./`, but Claude Code sends `tool_input.file_path` as an absolute path. Consequences:
the `.hitl/`/`.claude/` bootstrap exemption never fired (so intake itself could be blocked, the
exact chicken-and-egg it exists to prevent), and files outside the project (scratchpads under
`/tmp`, user-level config) were gated as if they were project source. Affected paths are now
normalized against the project root (`$CLAUDE_PROJECT_DIR`, falling back to the hook's working
directory): absolute paths inside the project are rewritten relative, symlinks are resolved on
both sides before the containment check, and paths outside the project are ignored — HITL
governs this project's files only. Regression suite: `ci/hooks/test_check_hitl_context.py`.
Also shipped on `release/1.x` as 1.0.31.

## [2.0.0] — 2026-07-10

Major version: the workflow model is a different mental model. Existing 1.x projects keep working (the change-file schema change is additive), but the identity, breadcrumb, and taxonomy are new, so it ships as a major. 1.x continues on `release/1.x` for critical fixes.

### Changed

**Numberless workflow model.** Steps are identified by a stable `key` + name + phase, never by global position. The runtime `workflows.yaml` is derived from a single numberless catalog (`tools/workflow-catalog/`), and the breadcrumb is a phase ribbon with no global `Step N / total` counter. Taxonomy is three tiers: 6 workflows, 6 profiles, 5 tags.

### Added

**Docs-only workflow (#19).** A documentation-only change gets its own 6-step spine (issue → scope → draft → domain-routed review → reconcile → merge) instead of owing the full delivery trail or bypassing HITL. Mixed docs+code changes stay on the delivery spine.

**Stale-change-file gate (#19).** A change marked `status: merged` is treated as inactive, so a concluded change file no longer satisfies the session gate for the next change.

**Manifest drift checker shipped (#16).** `ci/manifest-drift/check_manifest_drift.py` is now shipped under `shared/ci/`, copied into product repos at onboarding, and derives its scan roots from the manifest (no hardcoded `app/ src/`).

**Brownfield PRD initialization (#18).** Brownfield onboarding initializes the PRD shell (personas + format), the entry PM skills establish it on first run, and read-only PM/QA skills report "no requirements yet" instead of failing when the PRD is empty.

---

## [1.0.30] — 2026-06-21

### Fixed

**Breadcrumb now renders block-style YAML steps (issue #15).** `hooks/_steps.sh` only parsed
single-line flow maps (`- { n: 1, … }`); a change file written with block-style `workflow.steps`
(equally valid YAML, and easily produced by anything that edits the file) parsed to zero steps,
so the breadcrumb showed `Step ? / N` with no trail. The parser now handles **both** styles.
Also: the renderers tolerate **unquoted** `name:`/`phase:`; a workflow block that yields no steps
now shows the "run `/hitl:dev-update`" hint instead of a silent `?`; and the `unverifiable` branch
marker is no longer shown (it was permanent noise on long-lived non-`issue/*` branches).

**Hooks no longer silently no-op on Windows (issue #14).** The hook wrappers and several hooks
hard-coded `python3`, which on Windows is the Microsoft Store stub (on PATH but runs nothing) —
so plugin discovery returned empty and **every gate silently did nothing**. All Python callers
(wrapper template, the hooks, and the `dev-start-change` / `dev-update` generators) now probe
`python3 → python → py` with an `import sys` smoke test that rejects the stub, and force UTF-8
stdout (`PYTHONUTF8=1`) so breadcrumb glyphs don't crash on Windows' cp1252 default.

---

## [1.0.29] — 2026-06-17

### Fixed

**`/hitl:dev-update` change-file migration no longer mangles `current-change.yaml`.** The 1.0.28
migration (Step 4.5) round-tripped the whole file through `yaml.safe_dump`, which (1) **stripped
every inline comment** — destroying hand-written annotations like `# CORRECTED` / `# MISSED in
first draft` on the impact analysis — and (2) wrote the steps as multi-line **block** maps, which
the breadcrumb parser (`hooks/_steps.sh`) can't read, producing a "step trail unavailable" error.

The migration is now **surgical**: it replaces only the `workflow:` block (as single-line flow
maps) and upserts the version stamps, leaving every other line — and all comments — byte-for-byte
intact. The file is never round-tripped through a YAML dumper. Reported by a user upgrading the
Cerrtus consolidation to 1.0.28.

---

## [1.0.28] — 2026-06-16

### Added

**`/hitl:dev-start-change` — the enforced front door for starting a change.** Pick a GitHub
issue, have HITL classify the right workflow (development / brownfield / migration / prd) from
the issue, see the full step plan, and get a seeded-and-pushed `.hitl/current-change.yaml` — then
it routes into the matching workflow. A new `SessionStart` gate (`hitl-gate.sh`) plus a per-prompt
directive insist on this before any work happens, and `check-hitl-context.sh` now hard-blocks all
edits (not just source) until a change is active for the branch — so you can't drift into a
session without choosing a workflow. (`.hitl/` and `.claude/` paths stay writable so intake and
onboarding can bootstrap.)

**Self-describing, workflow-aware `current-change.yaml` (schema v2).** The change file now carries
its own workflow definition — an embedded `workflow` block with each step's stable `key`, label,
and status. The breadcrumb renderers read this block via a single shared parser
(`hooks/_steps.sh`), so the welcome banner and the status line can never again disagree on step
count or labels.

**Branch ↔ change mismatch warnings (issue #12).** A new `expected_branch` field plus a soft
"unverifiable"/hard "mismatch" marker in the breadcrumb and a hard edit-block when a committed
`current-change.yaml` has been inherited onto the wrong branch.

### Fixed

**Empty / drifting step trail (issue #10).** The status line previously matched the workflow phase
with a hardcoded `case` that real changes (`phase: "Design"`/`"Build"`) never hit, leaving an empty
trail; the banner used a separate hardcoded 32-step list. Both hardcoded models are gone — there is
now one canonical catalog (`ai/shared/workflows.yaml`: development 31 steps + 19a, brownfield 11,
migration 9, prd 4) that drives everything.

### Changed

**`/hitl:dev-update` migrates the change file.** On upgrade it remaps the embedded workflow by
stable `key` (preserving done/current across renumbering — e.g. the brownfield 8→11 growth),
shows a diff, and requires confirmation. The start-skills and `dev-apply-change` now seed the v2
block; `dev-apply-change`'s phase inconsistency was corrected.

---

## [1.0.27] — 2026-06-16

### Changed

**`/hitl:architect-review-existing` Phase 4a: architect now chooses which baseline ADRs to fill in.**

Previously Phase 4a decided for the architect which stubs to complete and blocked progression until specific ones were accepted. The new approach presents all 8 baseline ADRs in a single table with their gating requirements, then asks the architect which to complete now. For each selected ADR, Claude pre-fills every field derivable from the Phase 1 and Phase 2 findings and asks only for the fields that cannot be inferred from code (RTO/RPO targets, compliance scope, reviewer names, PR size policy, etc.). Deferred stubs are listed at the end with their gates so the team knows what to follow up on.

ADR numbering for new project-specific decisions (Phase 4b) corrected to start from ADR-0009.

### Upgrade guide — 1.0.26 → 1.0.27

```bash
/hitl:dev-update
```

---

## [1.0.26] — 2026-06-16

### Added

**Baseline ADR set completed: ADR-0006, 0007, and 0008.**

All three are picked up automatically by the `adr-000*.md` glob in Step 0 of every setup flow — no manual copy needed.

- **ADR-0006 (Branching and PR strategy)**: branching model, branch naming convention, PR size expectations, required reviewers by change tier, merge strategy, and branch protection rules. Gates: first PR merged via the HITL workflow.

- **ADR-0007 (Security baseline)**: secret management approach, dependency vulnerability scanning tool, SAST configuration, security review gates (when `/hitl:review-security` and `/hitl:ops-pentest` are mandatory), and compliance scope. Gates: first Tier 2 production deploy.

- **ADR-0008 (Data backup and recovery)**: RTO/RPO targets, backup approach per data store, tested restore procedure, verification cadence, and the pre-deploy backup gate used by `/hitl:ops-backup-database`. Gates: first production data write.

`/hitl:architect-review-existing` Phase 4a now lists all 8 baseline stubs with their gates, and groups the "ask architect" prompt by priority: stubs that block the first Tier 2 change vs stubs that block the first Tier 2 production deploy.

**Complete baseline ADR set:**

| ADR | Topic | Type | Gates |
|---|---|---|---|
| 0001 | HITL adoption | Pre-filled | — |
| 0002 | Documentation-first | Pre-filled | — |
| 0003 | Test strategy | Stub | First Tier 2 change |
| 0004 | Change tier policy | Stub | First Tier 2 change |
| 0005 | Observability strategy | Stub | First Tier 2 prod deploy |
| 0006 | Branching and PR strategy | Stub | First PR |
| 0007 | Security baseline | Stub | First Tier 2 prod deploy |
| 0008 | Data backup and recovery | Stub | First prod data write |

### Upgrade guide — 1.0.25 → 1.0.26

```bash
/hitl:dev-update
```

Existing projects: re-run `/hitl:architect-review-existing` — Phase 4a will copy ADR-0006, 0007, and 0008 stubs and prompt the architect to fill them in.

---

## [1.0.25] — 2026-06-16

### Added

**Observability setup added to all three onboarding flows. New ADR-0005 baseline stub.**

- **New `adr-0005-observability-strategy.md` stub**: covers application observability (logging, metrics, tracing, error tracking, dashboards, alerting, on-call routing) and agentic observability (session logs, token cost registry). Automatically copied to every project during Step 0 setup via the existing `adr-000*.md` glob.

- **Brownfield** (`/hitl:dev-start-brownfield`) — new Step 6 surveys existing observability infrastructure, seeds the token cost registry from the plugin template, fills in ADR-0005 with the architect, and flags gaps by severity (no logging = 🔴, no alerting = 🟡). Old Steps 6–10 shift to Steps 7–11.

- **PRD** (`/hitl:dev-start-from-prd`) — Step 4 handoff now includes observability provisioning as item 3: set up app observability stack and token cost registry before first deploy.

- **Migration** (`/hitl:dev-start-migration`) — Step 9 handoff now gates first production slice on observability infrastructure being in place for the target system.

- **`/hitl:architect-review-existing`** — Phase 2 adds Decision 9 (Observability as-built): extracts logging format, metrics tooling, tracing, error tracking, and on-call routing. Phase 4a adds ADR-0005 to the baseline stubs table; all three stubs (ADR-0003, 0004, 0005) must be accepted before the first Tier 2 production deploy.

### Upgrade guide — 1.0.24 → 1.0.25

```bash
/hitl:dev-update
```

Existing brownfield projects: re-run `/hitl:architect-review-existing` — Phase 4a will copy the missing ADR-0005 stub and ask the architect to fill it in. Then run Step 6 of `/hitl:dev-start-brownfield` as a standalone observability check.

---

## [1.0.24] — 2026-06-16

### Added

**Build and deployment pipeline verification added to all three setup flows.**

- **Brownfield** (`/hitl:dev-start-brownfield`) — new Step 5 verifies the existing pipeline: identifies the CI system (GitHub Actions, Jenkins, GitLab CI, CircleCI, Buildkite), runs a build check, confirms a staging deploy job exists. Offers to scaffold a starter pipeline if missing or broken. Old Steps 5–9 shift to Steps 6–10.

- **PRD** (`/hitl:dev-start-from-prd`) — Step 4 handoff now includes a pipeline setup item: after architect design is approved, provision CI/CD from the deployment view HLD and verify a commit reaches staging before any code is written.

- **Migration** (`/hitl:dev-start-migration`) — Step 9 handoff now includes an explicit pipeline gate between architect design approval and the first development slice: provision CI/CD for the target repo with build, test, and deploy-to-staging jobs; no production cutover step without a manual approval gate.

### Upgrade guide — 1.0.23 → 1.0.24

```bash
/hitl:dev-update
```

Existing brownfield projects: Step 5 is now the pipeline verification step. If you have already completed brownfield setup, run the Step 5 pipeline check as a standalone verification before your next change.

---

## [1.0.23] — 2026-06-16

### Added

**Deployment view staleness detection.**
Two automatic detection points prevent the deployment view HLD from drifting out of sync with infrastructure:

1. **Edit-time hook** (`check-domain-boundary.sh`): fires automatically whenever an IaC file is edited (Dockerfile, docker-compose, k8s/, helm/, terraform/, serverless.yml, .github/workflows/, infra/). If `docs/02-design/technical/hld/deployment-view.md` exists, a warning is emitted noting the view may be stale and pointing to the file or `/hitl:architect-review-existing` Phase 4c to regenerate.

2. **Post-apply step** (`/hitl:ops-apply-iac` Step 6): after every successful IaC apply, compares what changed against the deployment view and updates affected sections in place — services table, external dependencies, environments, CI/CD pipeline diagram. Skips silently if only config tuning or version bumps occurred with no topology change.

### Upgrade guide — 1.0.22 → 1.0.23

```bash
/hitl:dev-update
```

---

## [1.0.22] — 2026-06-16

### Added

**Deployment view HLD generated during brownfield architect review.**
`/hitl:architect-review-existing` Phase 4c now reads the infrastructure files already surveyed in Phase 1b (Dockerfile, docker-compose.yml, k8s/, terraform/, serverless.yml, CI/CD configs) and generates `docs/02-design/technical/hld/deployment-view.md`. The document covers environments, a Mermaid infrastructure diagram, services/containers table, external dependencies, and CI/CD pipeline. If no IaC files are found, the step is skipped and flagged as a Phase 5 concern. Phase 6 handoff now reports whether the deployment view was generated.

### Upgrade guide — 1.0.21 → 1.0.22

```bash
/hitl:dev-update
```

For existing brownfield projects: re-run `/hitl:architect-review-existing`. Phase 4c will generate the deployment view from your existing IaC files.

---

## [1.0.21] — 2026-06-16

### Fixed

**Baseline ADR stubs not delivered in brownfield onboarding (`/hitl:dev-start-brownfield`).**
Two bugs allowed the architect to reach `/hitl:architect-review-existing` without the 4 baseline ADR stubs:

1. **Step 0 all-or-nothing skip.** When `.hitl/hooks/` already existed (interrupted setup, re-run, manual wiring), the entire Step 0 was skipped including the ADR stub copy. Restructured: hook wiring (sub-steps 1–3) is still skipped when hooks exist, but gitignore and ADR stub sub-steps (4–5) always run.

2. **`architect-review-existing` never mentioned the stubs.** Added Phase 4a before any new ADRs are created: lists the 4 expected baseline stubs, copies any that are missing, and explicitly asks the architect to fill in ADR-0003 (test strategy) and ADR-0004 (change tier policy) before proceeding to ADR-0005+. These two stubs are pre-created but need architect input — they gate the first Tier 2 change.

### Upgrade guide — 1.0.20 → 1.0.21

```bash
/hitl:dev-update
```

For existing brownfield projects missing the stubs: re-run `/hitl:architect-review-existing`. Phase 4a will detect and copy the missing files.

---

## [1.0.20] — 2026-06-16

### Added

**Comprehensive usage guide (`shared/usage-guide.md`).**
Distributed with the plugin. Covers all six team scenarios with start commands, step-by-step flows, human gates, and what each path produces:

1. New project from a PRD
2. Existing codebase (brownfield onboarding)
3. Migration (source → target system replacement)
4. Enhancement (day-to-day 32-step workflow)
5. Bug fix (Tier 1 abbreviated path)
6. Incident response (P0 fix-first, P1 abbreviated)

Includes role-specific command tables for PM, Architect, QA, and Ops, plus context-switching guidance and a full quick-reference table.

### Upgrade guide — 1.0.19 → 1.0.20

```bash
/hitl:dev-update
```

No project changes needed. The usage guide is available at `${CLAUDE_PLUGIN_ROOT}/shared/usage-guide.md` after updating.

---

## [1.0.19] — 2026-06-16

### Fixed

**Plugin update cache-bust (`/hitl:dev-update`).**
`claude plugin marketplace update` can silently skip an update when `plugin-catalog-cache.json` holds a stale `marketplace_sha`. The update skill now detects a no-op (version unchanged after update) and automatically deletes the catalog cache file, then retries. If the version still doesn't change after the cache bust, the user is genuinely on the latest.

**`reinstall.sh` busts catalog cache and removes stale local marketplace entries.**
Added two pre-install steps: delete `plugin-catalog-cache.json` (forces fresh fetch) and remove any `known_marketplaces.json` entries for hitl marketplaces pointing at local/tmp paths (left over from dev installs). These stale entries prevented the GitHub-based marketplace from being the authoritative source.

### Upgrade guide — 1.0.18 → 1.0.19

```bash
/hitl:dev-update
```

If the update appears to be a no-op, the skill now handles it automatically. No manual steps needed.

---

## [1.0.18] — 2026-06-16

### Added

**Per-issue feature branches with context isolation.**
`/hitl:dev-apply-change` now creates an `issue/{N}-{slug}` branch before writing `.hitl/current-change.yaml` and commits the file immediately to anchor it to the branch. Each issue gets its own isolated YAML state automatically through git.

**Three-layer context conflict detection.**
Switching between issues in the same Claude Code session previously risked carrying stale context from the prior issue. Three defences now prevent this:

1. `check-hitl-context.sh` (PreToolUse hook) — blocks source code edits if the current branch's issue number doesn't match the YAML's `change_id`. Exit code 2 stops the tool call.
2. `welcome.sh` (UserPromptSubmit hook) — injects a visible `⚠️ HITL CONTEXT MISMATCH` warning into the model context on every prompt when branch and YAML diverge, even before any edit is attempted.
3. `/hitl:dev-switch-context` (new skill) — explicit context reload: stashes uncommitted work, checks out the target branch, reads `current-change.yaml`, reloads the GitHub issue + HLD + LLD from disk, and outputs a context-reset block instructing the model to discard all prior conversation context.

**Statusline breadcrumbs for all setup paths.**
Previously only `Migration Setup` and `Development` phases showed breadcrumbs. Three new phases added:

| Phase | Steps | Breadcrumb labels |
|---|---|---|
| `PRD Setup` | 4 | CLAUDE.md · Manifest · Issue · Handoff |
| `Brownfield Setup` | 9 | MapCode · CLAUDE.md · Manifest · ArchRvw · Docs · Registries · Graphify · Issue · Handoff |
| `Migration Review` | 5 | Context · Evaluate · MigReview · Brief · Handoff |

All three start skills (`dev-start-from-prd`, `dev-start-brownfield`, `dev-start-migration`) now write `.hitl/current-change.yaml` at Step 1 and update `current_step` at each subsequent step.

**Migration: source code is read-only.**
The migration skill now explicitly states that the source codebase is being *replaced*, not extended. A mandatory block is appended to the project's `CLAUDE.md` during setup: source code is reference only; all target behaviors must be implemented from scratch using the behavioral inventory as the only bridge.

**Workflow docs distributed with plugin.**
`shared/workflow-prd.md`, `shared/workflow-brownfield.md`, and `shared/workflow-migration.md` are now bundled with the plugin. `build.sh` auto-syncs these on every build.

### Fixed

**Graphify install gate removed from setup skills.**
`/hitl:dev-start-from-prd` and `/hitl:dev-start-brownfield` previously blocked setup with a machine-level install step (`uv tool install graphifyy`). The gate is removed; per-project commands (`graphify .`, `graphify hook install`) are retained as conditional steps that run only if Graphify is already installed.

**Stale command names swept.**
`/hitl:start-brownfield`, `/hitl:start-migration`, `/hitl:start-prd`, and `/hitl:ops-log-incident` replaced with current names across all skills and templates.

**Release logic corrected.**
`build.sh` previously set `marketplace.json source.commit` to the HEAD *before* the build commit, meaning installations always resolved to the prior version. A new `release.sh` script fixes the ordering: build → commit → pin SHA → create `hitl--vX.Y.Z` tag → commit marketplace update.

**Adoption guide updated.**
`docs/playbook/adoption-guide.md` referenced the deprecated `generate-docs reverse-engineer` sprint. Updated to reflect the current `/hitl:dev-start-brownfield` flow with `architect-review-existing` producing real ADRs.

### Upgrade guide — 1.0.17 → 1.0.18

```bash
/hitl:dev-update
```

No migration needed for existing projects. New behaviour is additive — branches are created on next `/hitl:dev-apply-change` run. If you have an existing `.hitl/current-change.yaml` on `main`, it will continue to work; breadcrumbs and context checks activate on the next change.

---

## [1.0.17] — 2026-06-15

### Added

**Migration flow: source codebase analysis (`/hitl:dev-start-migration` Step 5).**

The migration flow previously had no step that read the existing source code. The behavioral inventory produced by vendor runbooks or verbal description alone missed behaviors that are only visible in the actual code. This fills that gap.

**New Step 5 — Analyze source codebase:**

| Source location | What happens |
|---|---|
| Local path (same or sibling repo) | Reads top-level structure and key files; extracts APIs, domain behaviors, data contracts, integration points, auth rules, background jobs |
| Remote-only or inaccessible | User describes behavior verbally; entries marked `confidence: low` |

Output: `docs/00-migration/source-behavioral-inventory.md` — a table-structured inventory of every BI-NNN item that the target system must implement. This file is the objective definition of "migration complete."

**`/hitl:dev-review-external-docs` updated (Phase 1b + migration brief):**

- New Phase 1b reads `source-behavioral-inventory.md` before evaluating external docs. If absent, the skill warns and asks whether to proceed without it.
- Migration brief template now includes a **behavior coverage matrix** — one row per BI ID, with fields for target slice and status (`Not started / In progress / Complete / Descoped`). Each migration slice must declare which BI IDs it covers in its GitHub issue.

**Migration is complete when** every BI entry in the inventory has status `Complete` or `Descoped` in the coverage matrix. `Descoped` requires an explicit architect decision.

**Migration flow step renumbering:** old Steps 5–8 became Steps 6–9. Statusline updated to 9 steps, with new `SrcAnal` label at position 5.

### Upgrade guide — 1.0.16 → 1.0.17

```bash
/hitl:dev-update
```

Existing migration projects: run `/hitl:dev-start-migration` Step 5 manually to generate the behavioral inventory from your source codebase, then rerun `/hitl:dev-review-external-docs` to add the coverage matrix to your migration brief.

---

## [1.0.16] — 2026-06-15

### Added

**New skill: `/hitl:architect-review-existing` — reconstruct and document architecture decisions in an existing codebase.**

Fills the gap in the brownfield onboarding flow: the system manifest captures domain boundaries, but nothing captured *why* the existing technology choices were made or what constraints they impose. This skill reads the codebase and interviews the architect to produce real ADRs (not generic stubs) before incremental work begins.

**Six-phase flow:**

| Phase | What happens |
|---|---|
| 1 — Landscape | Reads system manifest + key technology indicator files; produces a Tech Stack Summary |
| 2 — Extract decisions | Identifies concrete decisions across 8 categories: service architecture, data, auth, API style, cross-domain communication, deployment, test strategy as-built, non-obvious patterns |
| 3 — Interview | Asks architect which decisions were deliberate vs inherited, confirms rationale, surfaces constraints and regrets |
| 4 — Document ADRs | Creates real ADRs (ADR-0005+) for significant decisions — status Accepted or Under review; never fabricates rationale |
| 5 — Surface concerns | Categorizes concerns as blocking HITL compliance (🔴), address in first changes (🟡), or worth noting (🟢) |
| 6 — Handoff | Produces summary of ADRs created, key constraints, and pre-conditions for first Tier 2 change |

**Brownfield flow updated:** New Step 4 added between system manifest generation (Step 3) and priority component documentation (now Step 5). Steps 4–8 renumbered to 5–9. Architect must confirm ADRs before proceeding to Step 5.

### Upgrade guide — 1.0.15 → 1.0.16

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

---

## [1.0.15] — 2026-06-14

### Fixed

**Persistent HITL breadcrumb via `statusLine` (fixes #7, #8).**

The `UserPromptSubmit` `welcome.sh` banner was routed into Claude's model context as `<system-reminder>` — not visible to the user. The fix adds a `statusLine` command to `.claude/settings.json` that Claude Code renders persistently in the UI status bar, showing the active change, phase, step number, and a windowed step trail:

```
HITL: Development · Step 14/31: GREEN [FR-42 · T2]
     ✓11.RED ✓12.TstRvw ✓13.VfyRED ▶14.GREEN ·15.VfyGRN ·16.Refact ·17.Conv …
```

Changes:
- `ai/claude/hooks/statusline-hitl.sh` — moved from `ai/claude/` (was never distributed by build.sh) into `hooks/` so it is now synced to the plugin; YAML path fixed from relative `$(dirname $0)/../` to `$CLAUDE_PROJECT_DIR` anchor
- `init-project.sh` and Step 0 of all three start skills — `statusLine` key added to `.claude/settings.json` template; `statusline-hitl` added to the hook wrapper generation loop
- `/hitl:dev-update` Step 4 — now checks for `statusLine` in `.claude/settings.json` and regenerates if absent

**Mermaid diagram constraints (fixes #9).**

Generated HLD/LLD diagrams broke GitHub rendering in two ways: nested generics in `classDiagram` (`~~` double-close from Java types like `ResponseEntity<Page<Order>>`) and literal `\n` in flowchart node labels. Both patterns now have:

1. **Template guardrails** — `hld-template.md` and `lld-component-template.md` have inline `<!-- Mermaid rules -->` comments that the architect skills read during generation
2. **`/hitl:dev-validate` checks** — two new checks added alongside the existing `<br/>` check:
   - `grep -n '~~' <file>` — catches nested generics before they reach GitHub
   - `grep -n '\\n' <file>` — catches literal `\n` in node labels

### Upgrade guide — 1.0.14 → 1.0.15

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Then run `/hitl:dev-update` in each project to add the `statusLine` to `.claude/settings.json` and regenerate hook wrappers. Restart Claude Code after.

---

## [1.0.14] — 2026-06-14

### Added

**New skill: `/hitl:help` — command discovery.**

Describe what you're trying to do and get a recommendation, or run it with no argument for the full command directory grouped by role.

```
/hitl:help                          # full directory — all commands by role
/hitl:help I want to enhance a feature that already exists
/hitl:help how do I start a TDD cycle
/hitl:help the code doesn't match the design doc
```

Covers all 40+ commands across dev, architect, QA, PM, and ops. Always gives a best guess — never says "I'm not sure" without recommending something.

### Upgrade guide — 1.0.13 → 1.0.14

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

---

## [1.0.13] — 2026-06-14

### Added

**New skill: `/hitl:pm-enhance-feature` — structured enhancement workflow for any existing feature.**

Works for product capabilities, PRD requirements, skills, agents, services, or any named component. Fills the gap between `/hitl:pm-update-requirement` (assumes you already know what to change) and `/hitl:pm-add-feature` (for new features from scratch).

**Five-phase flow:**

| Phase | What happens |
|---|---|
| 1 — Discover | Finds all artifacts related to the feature: PRD requirement, HLD/LLD, SKILL.md/AGENT.md, source paths from the system manifest, open GitHub issues |
| 2 — Explain | Summarizes current behavior in plain business language (no code, no YAML) — confirms the PM is looking at the right thing |
| 3 — Interview | Asks about the gap, affected users, impact, desired outcome, what must stay unchanged, constraints |
| 4 — Draft | Produces a structured enhancement request with problem statement, proposed changes, acceptance criteria, and explicit out-of-scope list |
| 5 — Record | Updates the PRD, creates a GitHub issue, and tells the PM what happens next (tier assessment → design → dev) |

Supports rigorous / moderate / light challenge modes. Never drafts the requirement until Phase 3 is complete. Never accepts unmeasurable acceptance criteria ("make it better", "improve it") without pushing for specifics.

### Upgrade guide — 1.0.12 → 1.0.13

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

---

## [1.0.12] — 2026-06-14

### Added

**Default ADR stubs written to `docs/02-design/technical/adrs/` during project setup.**

Every new HITL project now gets four starter ADRs that document the foundational decisions teams always need to make. They are created by both `init-project.sh` and Step 0 of all three start skills (`/hitl:dev-start-from-prd`, `/hitl:dev-start-brownfield`, `/hitl:dev-start-migration`). Existing files are never overwritten — safe to run on projects that already have ADRs.

| File | Status at creation | Purpose |
|---|---|---|
| `adr-0001-hitl-adoption.md` | Accepted (pre-filled) | Why the team adopted HITL; rationale, alternatives, ROI tracking |
| `adr-0002-documentation-first.md` | Accepted (pre-filled) | Decision to write HLD/LLD before code; consequences, exceptions |
| `adr-0003-test-strategy.md` | Draft (fill before first Tier 2 change) | Test framework, coverage gate, mocking policy, CI gates |
| `adr-0004-change-tier-policy.md` | Draft (fill at project kickoff) | Project-specific Tier 0–4 definitions; Tier 3 high-risk list |

ADR-0001 and ADR-0002 include pre-filled rationale that applies to any HITL project. ADR-0003 and ADR-0004 are stubs with prompts — the team fills them in at kickoff.

### Upgrade guide — 1.0.11 → 1.0.12

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

For existing projects, copy the ADR stubs manually:

```bash
mkdir -p docs/02-design/technical/adrs
PLUGIN_ROOT=$(python3 -c "
import json,os,sys
try:
  d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
  for inst in d.get('plugins',{}).get('hitl@hitl',[]):
    p=inst.get('installPath','')
    if os.path.isfile(os.path.join(p,'.claude-plugin/plugin.json')):
      print(p);sys.exit(0)
except:pass
" 2>/dev/null)
for f in "$PLUGIN_ROOT/shared/templates"/adr-000*.md; do
  dest="docs/02-design/technical/adrs/$(basename "$f")"
  [[ -f "$dest" ]] || cp "$f" "$dest"
done
```

---

## [1.0.11] — 2026-06-13

### Fixed

**Session logs no longer end up in the product repo's git history.**

`write-session-summary.sh` writes to `docs/session-logs/` inside the project directory. Nothing previously added that path to `.gitignore`, so session logs were silently committed on the next `git add`.

**Three-layer fix:**

1. **Step 0 of all start skills** now adds `docs/session-logs/` to `.gitignore` as part of initial project setup — same step that wires hooks and creates `.claude/settings.json`.

2. **`init-project.sh`** adds the `.gitignore` entry when creating the docs directory structure.

3. **`write-session-summary.sh` hook** adds the entry as a safety net on every session end — idempotent, only adds if missing. Covers existing projects that were set up before this fix without requiring a manual step.

**For existing projects with session logs already committed:**

```bash
# Remove from tracking (keeps the files on disk)
git rm -r --cached docs/session-logs/

# Commit the removal
git commit -m "chore: untrack HITL session logs"
```

The `.gitignore` entry will be added automatically on the next session end by the updated hook.

### Upgrade guide — 1.0.10 → 1.0.11

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. The safety-net fix in `write-session-summary.sh` activates on the next session end — no other action needed for existing projects.

---

## [1.0.10] — 2026-06-13

### Added

**New skill: `/hitl:dev-validate` — iterative validation loop.**

Runs a check → fix → re-check loop until every artifact from the session passes. Never exits until all checks pass (or explicitly marks items as unresolvable with a reason).

**What it validates by artifact type:**

| Type | Checks |
|---|---|
| Source code | Test suite (no regressions), coverage gate, linter, happy-path run |
| Tests | Execute without error, behavior-named, no unexplained skips |
| Docs (`.md`) | File paths exist, commands execute, no `{{placeholder}}`, no `<br/>` in Mermaid, index updated, cross-refs live |
| YAML / JSON | Parses, no placeholders, required fields present |
| Scripts / hooks | Executes, execute bit set, shebang present, `.hitl/` guard in hooks |
| Skill / agent files | Frontmatter valid, command names exist in `plugin.json`, paths exist, no placeholders |

**The loop:**
1. Inventory all files produced/modified
2. Run all applicable checks — log each PASS / FAIL
3. Fix every FAIL
4. Re-check — repeat from step 3 until zero failures
5. Report: what was checked, what was fixed, what (if anything) is genuinely unresolvable

**`CLAUDE.md.template` updated.** The Testing section is now a Validation Gate that directs Claude to run `/hitl:dev-validate` before reporting done on any task. Applies to all 40 skills universally.

### Upgrade guide — 1.0.9 → 1.0.10

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. No project-level changes needed — the new skill and updated CLAUDE.md template are available immediately after restart.

**Existing projects:** The CLAUDE.md template update only applies to new projects initialized after this release. To apply it to an existing project, add this section to your `CLAUDE.md`:

```markdown
## Validation (Mandatory — no exceptions)

After completing any task, run `/hitl:dev-validate` before reporting done.
```

---

## [1.0.9] — 2026-06-13

### Fixed

**Hooks no longer fail with "No such file or directory" on current Claude Code.**

Two bugs caused all six hooks to fail immediately after `plugin install` on any machine where Claude Code's working directory was not the project root:

**Bug 1 — Wrong plugin discovery schema (issue #6).**
All plugin path discovery code read `~/.claude/settings.json["plugins"]`, but current Claude Code stores installed plugin records in `~/.claude/plugins/installed_plugins.json` with a different schema. The hook wrappers generated by Step 0 could not find the plugin and silently exited — hooks never ran.

Fixed everywhere discovery runs:
- Detection snippet in Step 0 of all three start skills (`dev-start-from-prd`, `dev-start-brownfield`, `dev-start-migration`)
- Wrapper template written by Step 0
- Wrapper generation in `tools/scripts/init-project.sh`

New discovery order: `installed_plugins.json` first (current Claude Code v2 schema), fallback to `settings.json["plugins"]` (legacy).

**Bug 2 — Relative hook paths in `.claude/settings.json` (issue #7).**
Hook commands were written as `bash .hitl/hooks/welcome.sh` — a path relative to whatever Claude Code's working directory happened to be. Claude Code does not guarantee the cwd is the project root when invoking hooks. All six hooks failed with "No such file or directory" when Claude Code launched from a subdirectory or from a path other than the project root.

Fixed by using `$CLAUDE_PROJECT_DIR` (the env var Claude Code provides to hook commands) as an anchor:
```json
{ "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/hooks/welcome.sh\"" }
```

Fixed in `.claude/settings.json` templates in all three start skills and `init-project.sh`.

**`/hitl:dev-update` Step 4 detection updated.**
The stale-wrapper check was `grep "claude/settings.json"` — this now incorrectly marks the new wrappers as stale. Updated to `grep "installed_plugins.json"`: absence means the wrapper predates the v2 discovery fix and should be recreated. Step 4 also now checks and recreates `.claude/settings.json` if `CLAUDE_PROJECT_DIR` is absent.

### Upgrade guide — 1.0.8 → 1.0.9

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code.

**Existing projects — update hook wiring:** Run `/hitl:dev-update` from inside the project. Step 4 detects stale wrappers and settings.json and recreates them automatically.

Or do it manually:
```bash
rm -rf .hitl/hooks/ .claude/settings.json
```
Then re-run `/hitl:dev-start-from-prd` (or brownfield/migration) — Step 0 recreates both.

---

## [1.0.8] — 2026-06-11

### Added

**All skills now exit immediately in projects that haven't adopted HITL.**

Every skill except the three start skills and `/hitl:dev-update` now checks for `.hitl/` at the start. If the directory is absent, the skill outputs a setup prompt and stops — nothing else happens:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

This covers all 37 non-setup skills: `dev-practices`, `dev-tdd`, `dev-apply-change`, `dev-check-conventions`, `dev-generate-docs`, `dev-conclude`, `dev-impact-brief`, `dev-review-lld-adherence`, `dev-review-security`, `ta-approve`, all `architect-*`, `pm-*`, `qa-*`, `ops-*`, and `migrate-review-external-docs`.

**Known limitation (tracked):** `/hitl:*` commands appear in Claude Code's command palette in every project because Claude Code does not yet support per-project plugin skill visibility. The guard above is the mitigation — commands are visible but safe to invoke anywhere. A feature request has been filed with Anthropic to add project-scoped skill loading.

**README: opt-in model, opt-out instructions, and clean removal guide added to both repos.**

- "What happens when you install" — explains what is global (commands in palette) vs per-project (hooks, banner)
- "Opting a project out" — delete `.hitl/hooks/` and `.claude/settings.json`
- "Removing the plugin entirely" — `claude plugin uninstall hitl@hitl` + project cleanup

### Upgrade guide — 1.0.7 → 1.0.8

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. No project-level changes needed.

---

## [1.0.7] — 2026-06-11

### Fixed

**Plugin hooks no longer activate in projects that never opted into HITL.**

`hooks/hooks.json` was shipped in the plugin and auto-loaded by Claude Code, registering all hooks at user/global scope. This meant every project on the machine — including those with no `.hitl/` directory — had the HITL hooks firing. The immediate impact: `check-hitl-context.sh` exits 2 (blocking all `Edit`/`Write` tool calls) in any repo where `.hitl/current-change.yaml` is absent, even if that repo has nothing to do with HITL.

**Two changes:**

1. **`hooks/hooks.json` deleted.** The project-level hook wiring (`.hitl/hooks/` + `.claude/settings.json`, created by Step 0 of any start skill) is the correct mechanism and is unaffected. The global registration file is gone.

2. **All 6 hook scripts now guard on `.hitl/` presence.** As a safety net for any user who has plugin-level hooks wired in their user settings from an older install, every script now exits 0 immediately if `.hitl/` does not exist in the current working directory:
   ```bash
   [[ -d ".hitl" ]] || exit 0  # not a HITL project — skip silently
   ```
   This covers: `welcome.sh`, `check-hitl-context.sh`, `check-domain-boundary.sh`, `rebuild-graph.sh`, `sync-step-to-issue.sh`, `write-session-summary.sh`.

### Upgrade guide — 1.0.6 → 1.0.7

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. No project-level changes needed — the fix is entirely in the plugin.

---

## [1.0.6] — 2026-06-10

### Fixed

**`/hitl:dev-update` now correctly detects the installed version and upgrades the plugin.**

Three bugs prevented the update skill from working on current Claude Code:

1. **Version always showed `NOT_FOUND`.** The detection script read from `~/.claude/settings.json`, but Claude Code stores installed plugin records in `~/.claude/plugins/installed_plugins.json`. Fixed: reads `installed_plugins.json` first, falls back to scanning `settings.json` for the plugin path.

2. **`claude plugin install` is a no-op when already installed.** Step 2 was using the install command, which prints "already installed" and does nothing. Fixed: now uses `claude plugin marketplace update hitl` (refreshes the cached manifest) followed by `claude plugin update hitl@hitl` (installs the new version).

3. **`CHANGELOG.md` was not present in the installed plugin.** Step 3 tries to show the changelog from the plugin directory, but the file was never copied there. Fixed: `build.sh` now copies `CHANGELOG.md` from the source repo on every build. Step 3 falls back to the source repo URL if the file is missing.

### Upgrade guide — 1.0.5 → 1.0.6

Since `/hitl:dev-update` was broken in 1.0.5, upgrade manually this once:

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Restart Claude Code. After this, `/hitl:dev-update` will work correctly for all future upgrades.

---

## [1.0.5] — 2026-06-10

### Fixed

**Hook wrappers now survive plugin updates — "HITL_PLATFORM_ROOT is not set" error eliminated.**

The wrappers written by Step 0 used `${HITL_PLUGIN_ROOT:-<path>}` to locate the plugin. That env var was never set by Claude Code, and the fallback path was hardcoded to whatever version was current at setup time. After a `plugin install` bump (e.g. `1.0.4` → `1.0.5`), the versioned path changed and every hook silently failed or printed "is not set".

Wrappers are now fully dynamic: each one runs a short Python snippet at call time to read `~/.claude/settings.json` and discover the current plugin path. No env var, no hardcoded path — survives version bumps and reinstalls on any platform (macOS, Linux, WSL).

Old pattern (broken after update):
```bash
exec bash "${HITL_PLUGIN_ROOT:-/path/to/hitl/1.0.4}/hooks/welcome.sh" "$@"
```

New pattern (dynamic, version-agnostic):
```bash
PLUGIN_ROOT=$(python3 -c "
import json,os,sys
cfg=os.path.expanduser('~/.claude/settings.json')
try:
  data=json.load(open(cfg))
  for p in data.get('plugins',[]):
    path=p if isinstance(p,str) else p.get('path','')
    if os.path.isfile(os.path.join(path,'.claude-plugin/plugin.json')):
      print(path);sys.exit(0)
except:pass
" 2>/dev/null)
[[ -z "$PLUGIN_ROOT" ]] && exit 0
exec bash "$PLUGIN_ROOT/hooks/welcome.sh" "$@"
```

**Step 0 plugin detection now checks the installed plugin path, not the source repo path.**

The check that detects whether the HITL plugin is installed was looking for `ai/claude/plugin/plugin.json` — a path that only exists in the source repo. The installed plugin has `.claude-plugin/plugin.json`. Fixed in all three start skills and the update skill.

**Step 0 hook delegate path corrected.**

The wrappers generated by Step 0 were calling `ai/claude/hooks/<name>.sh` (source repo layout). The installed plugin has hooks at `hooks/<name>.sh`. Fixed.

**`/hitl:dev-start-from-prd` — command renamed from `start-prd`.**

`start-prd` could be misread as "start production". The command is renamed to `/hitl:dev-start-from-prd` — "start a project from a PRD document". No functional change.

**`/hitl:dev-update` Step 4 now detects and recreates stale wrappers.**

If `.hitl/hooks/` exists but the wrappers use an old path pattern (env var or hardcoded path), Step 4 now deletes the stale wrappers and recreates them with the dynamic discovery template. Detection check: `grep "claude/settings.json" .hitl/hooks/welcome.sh`.

### Added

**README: prerequisites table, Graphify billing note, troubleshooting section (both repos).**

- Prerequisites table: lists `bash`, `python3`, `PyYAML`, `git`, `gh`, and `graphify` with what fails silently if each is absent.
- Graphify billing note: subscription users must pass `--backend claude-cli` for the initial build. The background rebuild hook (`rebuild-graph.sh`) never calls an LLM and is always free.
- Troubleshooting section: SSH host-key fix for machines where `claude plugin install` fails with "No ED25519 host key is known for github.com".

**Documentation screenshots corrected — SVG diagrams now show correct `dev-` prefixed command names.**

| File | What changed |
|---|---|
| `docs/images/developer-commands.svg` | 6 commands updated: `generate-docs`, `tdd`, `apply-change`, `check-conventions`, `impact-brief`, `conclude` → all now show `dev-` prefix |
| `docs/images/tdd-flow.svg` | `/hitl:tdd` → `/hitl:dev-tdd` in two places |
| `docs/images/welcome-banner.svg` | `dev-start-prd` → `dev-start-from-prd` |

### Upgrade guide — 1.0.4 → 1.0.5

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code.

**Existing projects — update hook wrappers:** After restarting, run `/hitl:dev-update` from inside your project. Step 4 will detect the stale wrappers and recreate them automatically.

Or do it manually: delete `.hitl/hooks/` and re-run `/hitl:dev-start-from-prd` (or brownfield/migration). Step 0 will recreate the wrappers with the new dynamic pattern and skip all other setup steps.

---

## [1.0.4] — 2026-06-09

### Fixed

**`/hitl:ta-approve` — Technical Advisor role now published correctly.**

- `ta-approve` was missing from `plugin.json`, so it was not included in the plugin.
- When it was accidentally added by a prior build, it had the wrong name (`dev-ta-approve`) because the build script was applying the `dev-` prefix intended for developer skills.
- Fixed: `ta-approve` is now a special case in the build script and maps to `/hitl:ta-approve` — its own role prefix, distinct from `dev-`, `architect-`, `pm-`, `qa-`, and `ops-`.

**Stale `dev-ta-approve` removed.** The wrongly-named duplicate is deleted from the plugin.

**All internal command cross-references corrected.** Skill files (dev-practices, architect skills, qa skills, ops skills, ta-approve itself) referenced developer commands without the `dev-` prefix. All corrected:

| Was | Now |
|---|---|
| `/hitl:tdd` (in cross-references) | `/hitl:dev-tdd` |
| `/hitl:apply-change` (in cross-references) | `/hitl:dev-apply-change` |
| `/hitl:generate-docs` (in cross-references) | `/hitl:dev-generate-docs` |
| `/hitl:check-conventions` (in cross-references) | `/hitl:dev-check-conventions` |
| `/hitl:impact-brief` (in cross-references) | `/hitl:dev-impact-brief` |
| `/hitl:review-lld-adherence` (in cross-references) | `/hitl:dev-review-lld-adherence` |

**README By Role table updated:** Added Technical Advisor row. Added missing developer skills (`dev-review-lld-adherence`, `dev-review-security`) to Developer row.

### Upgrade guide — 1.0.3 → 1.0.4

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code.

---

## [1.0.3] — 2026-06-09

### Fixed

**Command names now match the actual plugin commands.**

The published plugin prefixes all flat developer skills with `dev-` (e.g. `/hitl:dev-start-from-prd`, `/hitl:dev-update`). All documentation and scripts now use the correct names. Previously the README, CHANGELOG, and reinstall script showed names without the prefix, which caused "command not found" confusion.

Corrected names:

| Was (wrong) | Now (correct) |
|---|---|
| `/hitl:dev-start-from-prd` | `/hitl:dev-start-from-prd` |
| `/hitl:start-brownfield` | `/hitl:dev-start-brownfield` |
| `/hitl:start-migration` | `/hitl:dev-start-migration` |
| `/hitl:update` | `/hitl:dev-update` |
| `/hitl:apply-change` | `/hitl:dev-apply-change` |
| `/hitl:check-conventions` | `/hitl:dev-check-conventions` |
| `/hitl:impact-brief` | `/hitl:dev-impact-brief` |
| `/hitl:tdd` | `/hitl:dev-tdd` |
| `/hitl:generate-docs` | `/hitl:dev-generate-docs` |
| `/hitl:conclude` | `/hitl:dev-conclude` |

### Upgrade guide — 1.0.2 → 1.0.3

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code. No other action needed — this is a documentation-only fix.

---

## [1.0.2] — 2026-06-09

### Added

**`/hitl:dev-update` skill** — update the plugin from inside Claude Code without touching a terminal.

Running `/hitl:dev-update` will:
1. Locate the plugin installation from `~/.claude/settings.json`
2. Re-run the plugin install command to fetch the latest release
3. Show the version change and a summary of what was updated
4. Re-wire `.hitl/hooks/` if they are missing or point to the wrong path
5. Prompt you to restart Claude Code

### Fixed

**README corrections:**

- Install and update instructions now clearly separated — install once with the marketplace commands, update thereafter with `/hitl:update`. Explicit note added not to re-run install commands to update.
- Install table corrected to list all available commands (phantom `architect-review-design`, `architect-verify-traceability`, `ops-review-release`, `ops-monitor-canary` removed)
- Removed two phantom Architect commands that were listed but never existed: `/hitl:architect-review-design`, `/hitl:architect-verify-traceability`
- Removed two phantom Ops commands: `/hitl:ops-review-release`, `/hitl:ops-monitor-canary`. Replaced with actual ops commands.

### Upgrade guide — 1.0.1 → 1.0.2

Run the plugin install command to update:

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code. From now on, just run `/hitl:dev-update` whenever you want to upgrade.

---

## [1.0.1] — 2026-06-09

### Fixed

**Hook wiring now works for plugin users without cloning the repo.**

Previously, hooks were defined in `plugin.json` and ran from the plugin directory. This caused two failures:
- Scripts could not find `.hitl/current-change.yaml` (which lives in the user's project, not the plugin)
- On machines where the plugin path differed from the path baked into `.claude/settings.json`, every hook fired a "No such file or directory" error

**Windows / WSL compatibility fixes** — hook scripts now work correctly when Claude Code runs inside WSL on Windows.

- `welcome.sh`, `sync-step-to-issue.sh`: replaced hardcoded `/tmp/` paths with `${TMPDIR:-${TMP:-/tmp}}`, which resolves correctly on macOS, Linux, WSL, and Git Bash
- `write-session-summary.sh`: replaced `echo -e` with `printf` — portable across all shells including those on Windows

### What changed

| File | Change |
|---|---|
| `ai/claude/plugin/plugin.json` | Removed `"hooks"` entry — plugin-level hooks are the wrong mechanism |
| `ai/claude/start-from-prd/SKILL.md` | Added Step 0: auto-wires `.hitl/hooks/` and `.claude/settings.json` |
| `ai/claude/start-brownfield/SKILL.md` | Added Step 0: same hook wiring |
| `ai/claude/start-migration/SKILL.md` | Added Step 0: same hook wiring |
| `.claude/settings.json` | Removed hardcoded `/Users/Prasad_1/…` path prefix from all hook commands |
| `ai/claude/hooks/welcome.sh` | Replaced `/tmp` hardcode with `${TMPDIR:-${TMP:-/tmp}}` |
| `ai/claude/hooks/sync-step-to-issue.sh` | Same `/tmp` fix |
| `ai/claude/hooks/write-session-summary.sh` | Replaced `echo -e` with portable `printf` |

### How hooks now work

Each start skill (`/hitl:dev-start-from-prd`, `/hitl:dev-start-brownfield`, `/hitl:dev-start-migration`) includes a **Step 0** that runs once per project:

1. Discovers the plugin installation path from `~/.claude/settings.json`
2. Creates `.hitl/hooks/*.sh` wrapper scripts in the user's project — each wrapper delegates to the real script in the plugin via `${HITL_PLATFORM_ROOT:-<discovered-path>}`
3. Creates `.claude/settings.json` in the user's project pointing to those wrappers

This is the same pattern `init-project.sh` used, now delivered automatically through the plugin.

---

## Upgrade guide — 1.0.0 → 1.0.1

### Everyone

Run the plugin install command to update:

```bash
claude plugin marketplace add pappar/hitl-claude-plugin
claude plugin install hitl@hitl
```

Restart Claude Code so the updated `plugin.json` is reloaded.

### New projects (not yet initialized)

No further action needed. Run your start skill as normal — Step 0 will wire the hooks automatically.

### Existing projects (already running the HITL workflow)

Your project does not have `.hitl/hooks/` wrappers yet. Create them now by running the appropriate start skill — it is **idempotent** and will skip any setup that is already in place:

```
/hitl:dev-start-from-prd
```
or
```
/hitl:dev-start-brownfield
```
or
```
/hitl:dev-start-migration
```

Step 0 will detect that `.hitl/hooks/` is missing, wire everything up, and prompt you to restart Claude Code. After the restart, hooks will fire correctly on every edit.

### Windows / WSL users

No special steps required beyond the above. The `/tmp` path fix and `printf` fix are included in this release and work automatically.

---

## [1.0.0] — initial release
