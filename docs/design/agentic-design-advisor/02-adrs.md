# Agentic Design Advisor: Architecture Decisions

> ADRs for decisions **A1–A9** from [`01-design.md`](01-design.md) §10. Each records the forces, the
> decision, the **alternatives with their concrete cost**, and the consequences. **v3.3** — reshaped around
> commands + composed workflow (v2), revised after pm/architect rounds (v3), then **core-scope-locked** after
> the round-4 objectives review ([`../agentic-core-scope.md`](../agentic-core-scope.md)): **A6** floor now
> obligation-first (`floor ⊆ composed`, B3); **A8** map core = terminal+Mermaid, HTML/live-combined deferred
> (M8). Status: **accepted, core-lock applied, pending Codex re-review (round 7)**.

---

## ADR-A1: The Advisor is a set of harness-run commands — not a separate app, not a monolith

**Context.** The Advisor asks expert questions and produces design artifacts at design time. HITL's
mechanisms already run *inside* the harness (skills, hooks, reviewer agents). The work spans many distinct
concerns (classification, boundary, privilege, reliability, observability, deployment), and different
people want to run different pieces at different times.

**Decision.** Ship the Advisor as a **set of runnable commands** (`hitl:agentic-*`), each doing one expert
concern and each **independently invocable by anyone**. A thorough `hitl:agentic-intake` command runs first
and **composes** the rest into a workflow (ADR-A4). The harness runs the conversation; HITL supplies the
catalog, the composition rules, and the gates.

**Alternatives and their cost.**
- *One monolithic intake skill.* Cost: can't run `agentic-privilege` alone against an existing design; the
  whole thing is all-or-nothing; harder to test, extend, or right-size.
- *A standalone questionnaire app.* Cost: a separate runtime (crosses governs-not-runtime), outside the
  design flow, can't author the manifest.

**Consequences.** (+) Anyone can run any piece; the commands compose into a right-sized workflow; each is
independently testable. (−) The command boundaries and their compose order must be defined (§2/§4) and
kept coherent — the composition step (ADR-A4) is what holds them together.

---

## ADR-A2: The question/option catalog is curated, versioned data — a curated refresh, not a live lookup

**Context.** The expertise (questions, option menus, answer→consequence mapping) must be reviewable,
refreshable, and testable. The field moves monthly; expertise baked into skill prose goes stale silently
(the #8 problem).

**Decision.** The catalog is a **versioned data artifact** (`ai/shared/agentic/catalog.yaml`), each entry
declaring its concern, trigger, options, guidance, recommendation rule, and machine-checkable
`consequence`. Staleness is handled by a **curated human refresh** (a catalog bump), prompted on a Tier-3
change — **not** a live external lookup, which would cross document-driven / governs-not-runtime.

**Alternatives and their cost.**
- *Questions hardcoded in skill prose.* Cost: not diffable as knowledge, not lintable (orphan questions),
  updates require editing skills — the staleness #8 exists to prevent.
- *A live external "scan for newer capabilities" call.* Cost: a runtime network dependency in a
  design-time, document-driven tool; non-reproducible; crosses the boundary.

**Consequences.** (+) Expertise is reviewable data; a lint can prove every question has a consequence
(ADV-4); refresh is an auditable human act. (−) The catalog is a curation burden (shared with #8),
mitigated by keeping it small and concern-organized.

---

## ADR-A3: Recommend, never decide — output is a proposal the human confirms

**Context.** "AI proposes, humans decide" is a HITL invariant. The commands make consequential calls
(component kinds, the floor, deployment). The AI's instinct is to pick the fanciest option.

**Decision.** Each command **recommends** the simplest option that fits (with rejected alternatives and
their cost) and **records** the decision; the human confirms, and an override is recorded with its reason.
No choice is applied silently.

**Alternatives and their cost.**
- *Auto-apply the "best" option.* Cost: the over-engineering bias wins, the human loses the decision and
  the learning, and the record no longer reflects a human judgment (fails governance evidence).
- *Ask only when unsure.* Cost: the AI is most confident exactly when it is wrong.

**Consequences.** (+) Human authority preserved; every material choice is an auditable, human-confirmed
decision. (−) More confirmation points — mitigated by composition (A4), so only relevant decisions surface.

---

## ADR-A4: HITL composes a proportionate workflow from the intake

**Context.** A fixed questionnaire / fixed command list that runs everything for everyone is the
over-governance failure this feature exists to prevent. Depth must follow risk.

**Decision.** After the intake understands the scenario, HITL **composes the workflow** — includes a
command only if the scenario has data for its lens, marks it mandatory (floor) or offered (rung), and
orders it by dependency. Composition is deterministic given the answers; a re-run reproduces the workflow.

**Alternatives and their cost.**
- *Always run every command.* Cost: drowns low-risk teams, gets routed around — the anti-over-engineering
  tool recreating over-engineering.
- *Free-form "let the AI decide what to run".* Cost: non-reproducible, no coverage guarantee, no record.

**Consequences.** (+) Light for light changes, thorough for heavy ones; runs reproduce; depth is
proportionate (see the worked example, HLD §9). (−) The relevance predicates and floor rules are logic to
author and test (test plan §4).

---

## ADR-A5: The commands author the manifest; #10's existing activation reacts — configure, don't feed, don't duplicate

**Status:** Accepted (this **replaces** the v1 decision, which claimed the Advisor feeds #10 an
"active-validator set" via a seed — a contract #10 was never built to receive, caught by the architect
review).

**Context.** #10 owns the schema, validators, and generators. The Advisor must not re-implement them, and
the two must have one source of truth. v1 invented a `.hitl/agentic-profile.yaml` seed whose
"active-validator set" #10 would read. Checked against #10's actual LLD, activation is **per-check
predicates over manifest content** — there is no external activation input, so the seed field was inert.

**Decision.** The commands **author real manifest fields** (kinds, trust legs, `uses`, lifecycle gates,
evals, the `observability` block). #10's per-check activation then runs exactly the checks whose data is
present. The Advisor **configures by authoring the manifest**; it does not pass #10 a validator list.
**Honest exception (now one):** the **kill-switch** (`agentic-reliability`) has **no #10 target today** —
no `kill_switch` check exists — so it produces a **declared design artifact** in the decision record
(recorded, human-reviewed). **`agentic-observability` is no longer an exception:** per the **2026-07-22 hard
directive** (a PM eval-console + live traces is required), #10 gained **`check_observability`** (a floor
gate on the `observability` block) via its own CR-9 elevation, and the Advisor authors that real field. So
the "author, don't modify #10" premise holds — #10 changed for its *own* requirement (CR-9), not at the
Advisor's behest.

**Alternatives and their cost.**
- *A seed with an active-validator set (v1).* Cost: describes a mechanism #10 can't consume; the field is
  decorative and the "only relevant validators run" claim is unbacked (architect Blocker 1).
- *Claim kill-switch/observability author #10 fields anyway (v2).* Cost: two of six mandatory commands map
  to #10 fields/checks that don't exist — the same fiction as the seed, recurring per-command (round-2 F1).
- *The Advisor validates/generates too.* Cost: two implementations of the same rules that drift — the
  double-source problem.

**Consequences.** (+) One source of truth; the "configures, doesn't duplicate" property is demonstrable
against #10's real activation model; observability is now **machine-validated** (a #10 floor gate), and the
one remaining exception (kill-switch) is honest. (−) The kill-switch stays human-reviewed until it gains a
#10 target; the Advisor must author the rest correctly for #10 to react — covered by the manifest-authoring
tests (test plan §6).

---

## ADR-A6: The floor is DERIVED from #10's activation; Tier scales depth; the ladder offers deferrable rungs

**Status:** Accepted; **rewritten round-5 (B1).** The earlier decision made the floor a function of *Tier +
risk gates* (e.g. "privilege floor at Tier ≥ 2"). Round-4/round-5 showed this **contradicted #10**, whose
per-check activation fires on manifest *content* — so a control the old floor treated as a deferrable rung
(privilege/evals/boundary at low tier) would be *mandated* by #10 and hard-fail when the team deferred it.
The floor is now a **pure function of #10's activation predicates**: a command is floor iff a #10 check it
owns will activate. **Tier no longer decides membership — it scales the required depth within a floor
control.** (This still refines the v1 L0–L4 "ladder" that was a second scale with no precedence rule.)

**Context.** The floor (the controls that can't be skipped) must be **auditable** — reproducible for a
given declared risk — and must **reuse HITL's existing Tier model** (requirements §6: no new orthogonal
machinery). v1's L0–L4 rungs were a second scale with prose triggers and no precedence rule.

**Decision.** The floor is **`{ command : a #10 check it owns activates on the scenario-implied manifest }`**
plus two non-#10 obligations (human gate on irreversible, kill-switch on supervised+side-effecting). The
Advisor **imports #10's activation predicates** (`ci/manifest-agentic/activation.py`) rather than copying
them — there is nothing to drift — and the `OWNERSHIP-COMPLETE` lint asserts every blocking #10 check is
owned by some command (round-7 B1). The workflow is `floor ∪ rungs`, so `floor ⊆ workflow` by construction
(the `FLOOR-SUBSET` lint guards it). **Tier + risk factors set the required *depth*** within a floor control
(e.g. observability = report vs console, M3), not
whether it is floor. Commands above the floor are
**offered as deferrable rungs** — the "add now or **defer**" ladder is a *human-facing narrative over the
same Tier+risk axis*, not a competing scale (note: rung **defer** ≠ floor **waiver**, round-4 m3). **The
floor is non-silently-droppable but waivable:** a floor command cannot be dropped silently (below the floor
without a waiver is a blocker), but it **can** be dropped via an **explicit, tier-appropriate waiver**
recorded in the decision record (owner, reason, tier-limit, revisit) — HITL's own hard-gate precedent
(FR-25: "hard-blocked until … *or waived*") and consistent with "humans decide" (ADV-9). **Determinism is
scoped to the computation given declared factors**, not to whether two people declare the same scenario
identically (a softer property the categorical vocabulary mitigates).

**Alternatives and their cost.**
- *A separate L0–L4 scale (v1).* Cost: two governance axes with an undefined relationship — confusing and
  self-violating (the feature adds the orthogonal machinery it warns against).
- *An absolutely non-waivable floor (v2).* Cost: the one hard block in HITL with no escape hatch —
  inconsistent with FR-25's precedent and in tension with ADV-9's "everything overridable" (round-2 PM
  finding); a signed human override with a recorded rationale is more honest than a wall.
- *Prose triggers, no vocabulary.* Cost: two implementers compute different floors; not auditable.

**Consequences.** (+) The floor is reproducible, auditable, reuses Tier, has teeth (no silent drop) *and*
a human escape hatch (recorded waiver) — matching HITL's established gating pattern. (−) The risk-factor
vocabulary, the floor rules, and the waiver schema are a small, safety-critical set that must be reviewed
as carefully as any guardrail (LLD).

---

## ADR-A7: The Advisor records the build-vs-buy decision; a human carries it — it provisions nothing

**Status:** Accepted (this **replaces** the v1 decision, which claimed an automated handoff of a
"deployment direction" to the platform/ops track — a receiver the architect review found does not exist).

**Context.** "Build all the agent infrastructure from scratch" is the biggest deployment over-engineering
trap, and teams make it by default. A right-sizing front door must surface it. But provisioning and vendor
choice are runtime/ops (governs-not-runtime), and platform-bootstrap has no intake for a deployment
direction.

**Decision.** `hitl:agentic-deploy` surfaces the decision, recommends **managed unless there is a specific
reason to build**, and **records** it in the decision record. On a managed recommendation it also
**surfaces the lock-in trade-off** and requires the three portability-diligence answers — **governance**
(neutral vs vendor-owned), **packaging** (portable across clouds without a rewrite), **state** (memory
exportable) — so the managed default is an eyes-open choice rather than a reflex (the industry-convergence
analysis, requirements §11). It then **prompts a human to carry the recorded decision into the platform/ops
track** (FR-25). There is **no automated handoff**, **no schema change to platform-bootstrap**, and **no
provisioning**.

**Alternatives and their cost.**
- *An automated seed→platform-bootstrap handoff (v1).* Cost: names a receiver that doesn't exist; requires
  retrofitting a shipped feature this package never scoped (architect Blocker 2).
- *Leave deployment out entirely.* Cost: the costliest infra trap goes unquestioned; teams build from
  scratch by default.
- *The Advisor provisions / picks the vendor.* Cost: crosses governs-not-runtime, vendor lock-in,
  cloud-specific modules to maintain (violates CR-10).

**Consequences.** (+) The costliest infra decision is surfaced, defaulted toward proportionate, and
recorded — while HITL stays out of provisioning, lock-in, and modifying a shipped feature. (−) The handoff
is a human step, not a machine one; if a machine handoff is wanted later it is a *separately scoped* FR-25
change, not assumed here.

---

## ADR-A8: The evolving map is a terminal-first generated view — HITL writes/prints, runs no live server

**Context.** People can picture what an agent *does* but not the *system*; an evolving map that shows the
composed topology and what's included/excluded makes the design — and the right-sizing — legible. But HITL
is used mostly in the **terminal**, and it is governs-not-runtime, so the map must not require a browser or
a hosted live dashboard.

**Decision.** The map is a **generated view** (the same category as the command-map/posture views),
regenerated from the accumulating scenario record **at each meaningful step**. **Core (v1) renders
terminal-first in two ways from one source (round-4 M8):** (a) a terminal-native inline text map re-printed
at each milestone (the live view, no browser); (b) a Markdown + Mermaid map in the decision record,
IDE/GitHub-previewable and auto-updating on file change. **Deferred enhancement:** (c) a rich interactive
HTML rendering, and — on an **artifact-capable surface** — a **combined "chat + live map"** mode that
re-publishes the map artifact to the same URL each step (the discussion and the evolving map side-by-side).
The combined mode is deferred because a **Should** feature should not carry a live re-publish loop and a
host API into v1; it has a defined host API in the follow-on. Two constraints govern the deferred mode: the
artifact is a **live view, not an input** (sandboxed, can't post answers back), and it is the **rich tier
only** (terminal-text is the universal baseline). All renderings share one **node-type visual vocabulary**
(agent/service/datastore/external/store + message + gate; ASCII equivalents in the terminal). HITL **writes
files and publishes/prints**; live refresh is the surface's, not a server HITL runs.

**Alternatives and their cost.**
- *A hosted live dashboard.* Cost: crosses governs-not-runtime (a runtime service HITL would host), and
  forces a browser on terminal users.
- *HTML-only.* Cost: forces a browser context-switch on the terminal-first majority — friction that defeats
  the "picture it while you discuss it" purpose.
- *A final diagram only (not evolving).* Cost: loses the "watch it take shape / see what's left out as you
  choose" value that is the whole point.

**Consequences.** (+) Terminal users see the map evolve inline with no browser; IDE users get a live Mermaid
preview for free (the rich HTML/live mode is a deferred follow-on, M8); all from one deterministic
regenerate, so the map never drifts from the design. (−) Two core renderings to keep consistent — mitigated
by one data source and a shared template.

---

## ADR-A9: The intake integrates into the existing intake — precede for compound, skip for simple, never replace

**Status:** Accepted; **rewritten round-5 (M1)** to a single, non-circular selector sequence — the earlier
text said the trigger came from "the intake's own elicited count," which both created a circularity
(needing the intake to decide whether to run the intake) and lacked an `agentic` gate.

**Context.** ADV-13 requires the Advisor to select the delivery surface and route into the compound-agentic
workflow, integrating with `pm-design-feature` and `ai/codex/AGENTS.md`, without (a) circularity and (b)
misrouting a non-agentic multi-component system into the compound intake.

**Decision — one selector, evaluated before any full intake (HLD §3.1):**
1. **`agentic` gate:** `pm-design-feature`'s existing "what is the delivery surface?" answer. Not agentic ⇒
   the deterministic/single flow runs unchanged and nothing below fires.
2. **topology probe** (agentic only): two questions — component count; does any component call/hand-off/
   message another?
3. **route:** ≥2 components and ≥1 edge ⇒ hand off to `hitl:agentic-intake` (compound branch); else the
   single-agent path. The full intake does **not** re-select the surface (the duplicate selector is
   removed, LLD §3); it only elicits the full detail on the compound branch. `ai/codex/AGENTS.md` gets the
   identical gate→probe→route rule.

**Alternatives and their cost.**
- *Select after the full intake (the old text).* Cost: circular — you must run the agentic intake to decide
  whether to run it (round-4 B2); and with no `agentic` gate a 2-service deterministic app misroutes to the
  compound intake (round-5 M1).
- *The Advisor replaces `pm-design-feature`.* Cost: breaks the existing single-agent/deterministic flows.
- *A separate detector tool.* Cost: net-new machinery when the surface question + a two-question probe suffice.

**Consequences.** (+) One cheap, non-circular selector; non-agentic and single-agent products are untouched;
the full intake runs only where it applies. (−) `pm-design-feature` and `AGENTS.md` each get a small tracked
change (the gate→probe→route rule), enumerated in the LLD file list.

---

## Decision index

| ADR | Decision | One-line |
|---|---|---|
| ADR-A1 | A1 | Advisor = a set of harness-run commands (not a monolith, not an app) |
| ADR-A2 | A2 | Catalog = curated, versioned data; curated refresh, not live lookup |
| ADR-A3 | A3 | Recommend, never decide; human confirms; record chosen/rejected |
| ADR-A4 | A4 | HITL composes a proportionate workflow; run only what's relevant |
| ADR-A5 | A5 | Commands author the manifest; #10 reacts — no seed; observability authors the #10-gated `observability` block (hard directive); **only** the kill-switch remains a declared artifact (no #10 target yet) |
| ADR-A6 | A6 | Floor is **DERIVED from #10's imported activation** (floor ≡ activation, complete ownership; round-7 B1); **Tier scales depth, not membership**; `floor ⊆ workflow`; **waivable via #10's real per-check waiver store** (round-6 B3); rungs are **deferrable** (defer ≠ waiver) |
| ADR-A7 | A7 | Record the build-vs-buy decision + portability diligence; a human carries it — provision nothing, auto-hand-off to nothing |
| ADR-A8 | A8 | Evolving map = terminal-first generated view; **core = inline text + Mermaid; rich HTML + combined live mode deferred** (M8); regen per step; no live server |
| ADR-A9 | A9 | Intake integrates into `pm-design-feature`/`AGENTS.md` — precede for compound, skip for simple, never replace |
