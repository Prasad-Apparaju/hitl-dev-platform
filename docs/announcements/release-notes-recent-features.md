# What's new in HITL: the last 10 features

Covers releases 2.2.0 through 2.7.1. Newest first. Each entry says what the feature is, and what
you actually get out of it.

To pick all of this up on an existing project, run `/hitl:dev-update` once.

---

## 1. Tell HITL how to talk to you

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

## 2. Draft a message for a specific person

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

## 3. A workflow for shipping a release

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

## 4. Your project says out loud that it uses HITL

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

## 5. First Pass: ship a thin whole version, on the record

HITL 2.4.0, actually wired in 2.5.0

A mode you turn on at the start of any change. HITL proposes the plan, then you answer one menu:
for each step, do it now / write an honest-minimal starter / defer / decline. Then you build.

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
tried First Pass on 2.4.x and it felt like nothing happened, that's why.

---

## 6. Brief mode

HITL 2.5.0

With First Pass on, step output is trimmed to what you actually have to act on. The intake dump,
the single biggest source of "this makes me read too much", collapses to a phase summary.

**What you get:** less to read per step, and the detail is still there if you ask for it.

---

## 7. Fewer permission prompts for reads you already approved

HITL 2.5.0

A hook that auto-approves reads already covered by the scope your change declared.

**What you get:** you stop clicking approve on files you explicitly put in scope two minutes
earlier. The hook can only ever say *allow*, never *deny*, so it can widen what proceeds and can
never turn into a new way to block you. Alongside it, the permission template shipped with
onboarding was cut back to what's genuinely defensible, after we measured that shell redirection
rides along on any allowlist entry.

---

## 8. Reviewers that try to prove you wrong

HITL 2.5.0

All five reviewer agents (PM, architect, QA, ops, spec conformance) now open with an instruction to
refute rather than confirm.

**What you get:** reviews that find things. A reviewer that sets out to confirm a design finds it
confirmed, every time, which is worth nothing. This one line changed the character of the output
more than anything else in the release.

---

## 9. A front door for designing agentic systems

`hitl:agentic-intake` — HITL 2.3.0

One conversation that asks about the shape and risks of the agentic system you're building, then
recommends a right-sized set of controls, records your decisions, draws the system map, and hands
off a design handoff.

**What you get:** a recommendation report instead of eight commands you'd have to know existed. It
scales down: a small system doesn't get the governance a fleet of tool-using agents needs. Rerun it
as the design changes and it reconciles with what you decided last time rather than starting over.
The same answers always produce the same report.

**The boundary that matters:** the intake writes no field of your system manifest, not one. A human
authors the manifest; the validator in item 10 checks it independently. That keeps the check honest
rather than grading its own homework.

---

## 10. HITL governs systems, not just services

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

2.4.3 through 2.4.8, 2.6.1 through 2.6.3, and 2.7.1 are fixes, not features, and most of them came
from independent adversarial reviews or from people using this for real. If you're on
anything older than 2.7.1, update: 2.6.4 could corrupt a change file on upgrade, and 2.6.2 had a
cleanup step that could delete a test file your team wrote.
