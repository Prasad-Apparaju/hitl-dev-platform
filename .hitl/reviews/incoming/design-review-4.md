# Design review 4 — right-sizing, progress-and-retro, and the command-surfacing commits

Five points, ranked. Checked by running: the wiring suite (231 pass), `derive.py verify` (clean),
and the statusline against a hand-built change file at step 2.

## 1. The command reaches the change file once and is dropped on every advance — this stops it working

The claim "the change file and the statusline" holds at creation and nowhere after. The statusline
reads `current_step.command` only. Every instruction in the repo for advancing the pointer writes
`current_step` as `{number, name, phase}`:

- `ai/claude/apply-change/SKILL.md:100` — the development driver. Its seeded `workflow.steps`
  example (lines 95–98) has no `command` column either, and line 91 tells the agent to carry
  `phase` verbatim from the catalog, not `command`.
- ~30 more templates in `start-brownfield/SKILL.md`, `start-migration/SKILL.md`,
  `start-from-prd/SKILL.md`, `start-brownfield/observability-survey.md`,
  `agents/spec-conformance-reviewer.md:23-24`.

I built a change file exactly as `apply-change` instructs (step 1 done, step 2 `red` current) and ran
the statusline. Output: `HITL ▸ GH-1 ▸ Build ▸ RED [T2]` — no `→ /hitl:dev-tdd`. `red` declares
`dev-tdd`; the empty case in `statusline-hitl.sh:73` renders nothing, silently. Same defect shape as
the one the commit message diagrams, one hop further along.

This also breaks the other half. `next-step.md` tells 22 skills to read the next step's `command`
from `workflow.steps` — and `apply-change`, which carries that contract at line 232, is the skill
whose own seed template omits the field.

The three new wiring tests do not catch it: two exercise the generator's first emission, the third
uses a hand-written fixture that has the field. Nothing tests an advanced file.

Everything else the commits claim is true. `derive.py verify` does compare `command`
(`derive.py:205`), the runtime carries 63 of 99 (34/34 development, 17/17 platform, 12/12 release,
0 for the five that declare none — the stated count is exact), and all 22 targets reference
`ai/shared/next-step.md`, both skills and `commands/`.

## 2. Right-sizing never says when the change file is created, and the workflow is chosen twice — worth deciding

Step 3's record is "referenced from the change file", and the reference is a blocking check. But the
change file is produced by `start-change/SKILL.md`'s step-6 generator, which today takes the tier and
emits the whole step list — both of which the design moves to after step 3. So the file either exists
before step 3 without a tier or a plan, or it is written twice. The doc does not say which, and the
generator refuses to emit a plan with no steps in it.

Related: step 3 answers "which workflow applies", but `start-change` already had to pick a workflow
to seed the file. That is the one thing in the flow decided twice.

## 3. Declining a progress update requires the publish that was declined — worth deciding

"It is never published on your behalf" and "the block then shows that it is deliberately stale" are
the same paragraph. The block is at the top of the issue body; marking it deliberately stale is an
edit to a shared issue that the person just refused. Either the decline is local-only (and the team
cannot tell a quiet change from a declined one, which is the stated purpose) or the guarantee has an
exception nobody named.

Also unresolved: "when the block was last refreshed" has no stated home. Nothing in the change file
or the block schema holds a refresh timestamp today, so the two-day trigger has nothing to read.

## 4. The two docs disagree about the retrospective and about the tier-3 floor — worth deciding

Progress-and-retro adds a catalog step and calls it "the one exception": always in, never falls out.
Right-sizing's §4 describes two predicates, no exceptions, and its §3 arithmetic (34→33, floor
ten→nine) predates the addition. Which doc governs the step count is unresolved.

The stronger version: right-sizing §5 says anything not floor-locked can be unticked. The
retrospective is not floor. So a person can untick the feedback loop, and the thing progress-and-retro
argues must never drop out drops out on a manual untick. Neither doc addresses it.

The floor counts: tier 1 (4) and tier 2 (5) check out against the catalog once `no_omit` on
`red`/`green` is counted. Tier 3 does not. Over the development workflow it is 9 today and 8 once
`impact` leaves — §3 says ten→nine and §4 says nine after. They contradict each other, and both are
one high.

## 5. The two walkthroughs come out right; one gap in the small one — minor

**A one-line fix in the best-documented area.** Impact analysis finds the area, finds the change
reaches nothing, `needed_now` fires for nothing, tier 1, four locked steps. This is the FIRECRAWL case
inverted correctly, and the "read the change's reach, never the area's paperwork" rule is what makes
the well-documented area not cost more. It works.

The gap: §2 says every definition-of-done line must name a criterion and a line with none "stops
progress before Build begins". No step in the 38-step spine writes acceptance criteria — they live in
the issue or the PRD, and a tier-1 fast track creates neither. So the flow has a hard block before
Build with nothing in the plan that produces the thing it blocks on, and no named owner. On the
lightest path that is a stall with no next command, which is the opposite of what #100 just shipped.

**A feature touching a published interface with three dependents.** Impact finds the dependents and
the interface, `needed_now` pulls integration and compatibility in, tier 3 locks nine, the PRD is
created because the workflow is a feature. Comes out sensible, no gap found.
