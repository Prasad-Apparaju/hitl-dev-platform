# What's new in HITL: recent features

Covers releases 2.2.0 through 2.12.0. Newest first. Each entry says what the feature is, and what
you actually get out of it.

To pick all of this up on an existing project, run `/hitl:dev-update` once.

---

## 1. Plain English, and short, is the standard

HITL 2.12.0

One rule for everything HITL says or writes, `shared/plain-english.md`: no em dashes, none of the
filler a model reaches for, numbers in a table, and a document as long as what it has to say. A
section with nothing to say reads "None."

**What you get:** generated documents with a ceiling. An executive summary is three sentences, an
HLD two pages of prose, an LLD one page per component, an ADR one page, and an impact brief,
retrospective or review report one page. Going over is allowed when the content needs it, said in
one line at the top. Every prompt banner points at the rule, `/hitl:dev-preferences` defaults the
tone to it, and a lint checks the text that reaches people: hook messages, the lines skills say to
you, the templates. Around three hundred shipped lines were reworded to pass it.

---

## 2. The adversarial review became a verification review

`/hitl:dev-verification-review`, HITL 2.11.0

Same independent reviewer in a clean context, different brief. Instead of "assume this is broken
and find how", the reviewer gets a checklist built from the requirement, the work's own claims and
the lens questions, runs what can be run, and returns one page.

**What you get:** a table of checks with the command and result for each, then at most five ranked
points in three classes: stops it working, worth deciding, minor. "It is right" is a real answer.
The attacking output was unusable in practice; the constrained brief found more real defects in
fewer lines, so the constraints stayed and the attack went.

**Nothing to migrate:** the step keys did not change, so no change file, skip record or waiver
needs editing. The old command remains for one release and tells you where it went. The release
gate reads both record shapes.

---

## 3. Security steps a plan can actually reach

HITL 2.10.0

The security design review, CVE audit and penetration test were dropped on the way to the runtime,
so a tier-3 change to authentication drew none of them, and the pentest was a floor step that never
appeared in a plan.

**What you get:** the three are lettered substeps now, activated per change by a lockfile change, a
data migration, or you answering yes to one intake question: does this touch auth, secrets,
personal or payment data. Inactive, the sizer records them not applicable with the reason. Silence
is not a no: the gate blocks a step marked not applicable when the record never answers the
question.

Also in 2.10.0: the change-file audit in `dev-update` fails closed on an unreadable file, validator
copies in your repo are synced with a diff and a question rather than blind-copied, and the step
docs number the steps the way the runtime does.

---

## 4. Right-sizing: the code decides the plan

HITL 2.9.0

Someone added one environment variable to a shell script and HITL ran eleven steps over three and
a half hours. The plan was fixed at intake from the words in the issue, before any code was read.

**What you get:** impact analysis stops being a step in the plan and becomes the thing that
produces it. It always runs, reads what the change reaches, writes the findings with their
provenance to `.hitl/impact/<change-id>.yaml`, and proposes a tier from them. You confirm the tier
and pick one of two options: Fast Track, the steps this change's own facts call for, or Full
Scale, everything that applies to a change of this shape. Every rule reads what the change touches,
never what its area has, so documenting an area does not tax every future change to it.

**What it replaces:** the step-by-step menu from 2.4.0 (item 12). The light path is no longer
opt-in; every change sees a proposal. A fourth disposition, `not_applicable`, separates "the rules excluded it"
from "a person declined it", so the retrospective stops reading twenty declined steps nobody looked
at. A rule cannot retire a load-bearing step; a named person can.

---

## 5. What to run, at every step

HITL 2.9.0

The catalog has declared commands all along. They were dropped in derivation, dropped again when
the change file was written, and never shown.

**What you get:** the statusline names the command for the current step, and every step closes by
saying what comes next and how to start it. Steps with nothing to run say so rather than inventing
one.

---

## 6. Review findings reach you, and you decide

HITL 2.8.0

Reviewer reports were being written and never handed back. On one change, ten reviewers produced
full reports and not one was delivered.

**What you get:** reports land as files the skill reads, and a missing report is unknown, never
"the reviewer failed". CRITICAL and HIGH findings come to you one at a time in plain English: what
breaks, what it costs, the recommendation. You answer fix, accept, or defer. That is what makes an
accepted risk recordable; before, "fix everything" was the only answer an agent could give, and
reviews became a loop. A catalog of thirteen lenses picks where a review looks. Two rounds, then
round three is a decision someone makes. The gate reads every reviewer in a round, not one, and a
name filed as `consequence-2` no longer hides a duplicate.

---

## 7. HITL stops talking like a compiler

HITL 2.8.0

The hooks used to interrupt you mid-edit and report internal state in capitals. Nobody has a
context mismatch. Nobody realigns anything.

**What you get:** all 46 gate messages across five hooks say what happened the way a colleague
would and end with what to do next. Same gates, same exit codes. A small set of icons marks state
and never celebrates. The portal also caught up with the plugin in this release; it had not moved
since 2.1.1.

---

## 8. Tell HITL how to talk to you

`/hitl:dev-preferences` — HITL 2.7.0

Four questions about how you want HITL to communicate in this project: how long the answers are,
whether it narrates what it's doing, how it opens a disagreement. Adjustable any time, `off` to
pause, `reset` to remove.

**What you get:** the assistant stops writing essays when you wanted three lines, and stops
writing three lines when you wanted the reasoning. Say "default mode" to drop it for one session
without touching the file. The settings live in a marked block in the project's `CLAUDE.md`, so
your teammates get the same behaviour and can see who set it and how to change it.

**The limit that makes it safe:** a preference shapes *form*, never *substance*. Length, ordering
and how much reasoning is shown are yours to set. A risk, a cost, an uncertainty, or a decision
that is yours to make will be stated regardless. Ask it to store "no risk warnings" and it records
the tone and politely declines that one clause.

---

## 9. Draft a message for a specific person

`/hitl:dev-draft-for <person>` — HITL 2.7.0

Writes a PR comment, issue update or status note aimed at one named person, using a short profile
you store under `.hitl/people/`.

**What you get:** the same update, pitched for the reader. A blunt reviewer gets the blunt version;
someone who wants context first gets context first. You stop rewriting the same status note three
ways.

**The guardrails:** it drafts, it never sends, and it never sends in the same turn it wrote.
Profiles are gitignored by default, they record who wrote them and whether the person knows the
profile exists, and both facts are disclosed on every draft.

---

## 10. A workflow for shipping a release

The `release` workflow — HITL 2.6.4, tightened in 2.6.5

Twelve steps for publishing a version to your users, with an independent adversarial review
required before you publish and a validator that ties the review record to the exact code being
shipped.

**What you get:** releases stop being a thing one person does from memory at 11pm. The review can't
be satisfied by a review of some earlier state of the code, because the record is bound to what
you're actually shipping. Skipping the review is still possible, but as of 2.6.5 it needs a signed
waiver, not just a name. Two optional review offers also appear at the end of Design and Build in
the normal development workflow; declining either is recorded like any other skip.

---

## 11. Your project says out loud that it uses HITL

Managed `CLAUDE.md` section + `docs/getting-started.md` — HITL 2.6.0

A user told us: *"I wasn't aware of it initially, and only later did I learn there's a HITL plugin
I'm supposed to use."* Nothing in a project ever said so. Now onboarding maintains a marked block
in `CLAUDE.md`, and there's a guide written for the person dropped into an existing project.

**What you get:** a new joiner finds out on day one instead of week three, including when they
haven't installed the plugin (in that case `CLAUDE.md` is the only thing in the repo that can tell
them). The guide walks one change end to end and opens by saying you don't have to memorise any of
it: start work normally and Claude takes you through intake. Of 56 commands, it names the four you
need. The block never overwrites your file; it creates, appends, refreshes, or stays quiet.

---

## 12. The skip record: ship a thin whole version, on the record

HITL 2.4.0, actually wired in 2.5.0

In 2.4.0 this was a mode you turned on at the start of a change, then called First Pass. HITL
proposed the plan, then you answered one menu: for each step, do it now / write an honest-minimal
starter / defer / decline. Since 2.9.0 the plan is sized for you (item 4) and this menu is how you
lighten it further; the record below is how Fast Track keeps what it left out.

**What you get:** a materially shorter path to something running, without pretending the skipped
work doesn't exist. Every lightened step is written to a ledger with who, why and when, deferrals
seed follow-up tickets, and skips resurface later (at the follow-up, at the next change touching
the same area, at incident review) in neutral language that never assigns blame.

**What you can't skip:** load-bearing steps for the change's tier need the accountable person's
acknowledgement and, where the step maps to a hard gate, a linked waiver. The TDD red/green cycle
can be thinned but never dropped. A fail-closed CI check enforces all of it.

**Note on 2.4.0 vs 2.5.0:** 2.4.0 shipped the requirements, the validator and the skill. It turned
out the driver never set the flag those mechanisms read, so in a real run most of them were
unreachable. 2.5.0 connected them, and added a test suite for that whole class of defect. If you
tried the light path on 2.4.x and it felt like nothing happened, that's why.

---

## 13. Brief mode

HITL 2.5.0

When intake leaves any step out (Fast Track, since 2.9.0), step output is trimmed to what you
actually have to act on. The intake dump,
the single biggest source of "this makes me read too much", collapses to a phase summary.

**What you get:** less to read per step, and the detail is still there if you ask for it.

---

## 14. Fewer permission prompts for reads you already approved

HITL 2.5.0

A hook that auto-approves reads already covered by the scope your change declared.

**What you get:** you stop clicking approve on files you explicitly put in scope two minutes
earlier. The hook can only ever say *allow*, never *deny*, so it can widen what proceeds and can
never turn into a new way to block you. Alongside it, the permission template shipped with
onboarding was cut back to what's genuinely defensible, after we measured that shell redirection
rides along on any allowlist entry.

---

## 15. Reviewers that try to prove you wrong

HITL 2.5.0, replaced in 2.11.0

All five reviewer agents (PM, architect, QA, ops, spec conformance) opened with an instruction to
refute rather than confirm. A reviewer that sets out to confirm a design finds it confirmed, every
time, which is worth nothing.

**Where it went:** the refute line is gone as of 2.11.0. The agents now open with "Verify, do not
confirm" and are told a result is the command and what it printed. Item 2 has the reasoning.

---

## 16. A front door for designing agentic systems

`hitl:agentic-intake` — HITL 2.3.0

One conversation that asks about the shape and risks of the agentic system you're building, then
recommends a right-sized set of controls, records your decisions, draws the system map, and hands
off a design handoff.

**What you get:** a recommendation report instead of eight commands you'd have to know existed. It
scales down: a small system doesn't get the governance a fleet of tool-using agents needs. Rerun it
as the design changes and it reconciles with what you decided last time rather than starting over.
The same answers always produce the same report.

**The boundary that matters:** the intake writes no field of your system manifest, not one. A human
authors the manifest; the validator in item 17 checks it independently. That keeps the check honest
rather than grading its own homework.

---

## 17. HITL governs systems, not just services

Compound-agentic delivery surface — HITL 2.2.0

The system manifest can now describe a product built as a graph of deterministic services and
agents, with sync, async and event edges between them, and 17 validators check it in CI.

**What you get:** the questions everybody forgets get asked automatically, at review time, in code.
Does this agent have more privilege than it needs? Does the async edge have idempotency and a dead
letter queue? Is there an eval for each agent and for the end-to-end path? Does the observability
floor hold? You also get generated views (topology diagram, privilege table, tool matrix) that
can't drift from the manifest, because CI regenerates and diffs them.

**Additive:** an existing or purely deterministic manifest validates unchanged and needs no new
registry. Each check activates only when the data it inspects is present. Unknown fields and typos
are blockers rather than silent skips, so a typo can't quietly switch a governance check off. Any
blocker can be waived by a human with a recorded reason; a few can't be waived at all.

---

## Also landed, if you're wondering where these went

- **Validators install themselves** (2.4.1, 2.4.2). Onboarding and `/hitl:dev-update` now copy the
  CI validators into your repo and install ones that were added after you onboarded. A repo
  onboarded a year ago retroactively gets checks shipped since, without re-onboarding. Your own
  files (waivers, ledgers, customised workflows) are preserved.
- **Platform-bootstrap workflow** (2.1.0). Tracks the gap between "onboarded" and "ready to deliver
  to a customer": a readiness register with evidence and waivers, a roadmap generated as issues, a
  status chip in the statusline, and a hard gate that blocks a tier 2+ production deploy while a
  gap is open and unwaived. Staging and canary are never gated.

## And a note on the point releases

2.4.3 through 2.4.8, 2.6.1 through 2.6.3, 2.7.1, 2.9.1 and 2.10.1 are fixes, not features, and
most of them came from independent reviews or from people using this for real. If you're on
anything older than 2.12.0, update: 2.9.0 shipped a retrospective step that failed for everyone who
installed the plugin, 2.6.4 could corrupt a change file on upgrade, and 2.6.2 had a cleanup step
that could delete a test file your team wrote.
