# Agentic Design Advisor: Architecture Decisions

> ADRs for decisions **A1–A9** from [`01-design.md`](01-design.md) §10. Each records the forces, the
> decision, the **alternatives with their concrete cost**, and the consequences. **v3** — reshaped around
> commands + composed workflow (v2), then revised after two review rounds (A8 map; A9 surface-selection
> integration; A5 declared-artifact exception; A6 floor waiver). Status: **accepted, pending review**.

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
evals). #10's **existing, unmodified** per-check activation then runs exactly the checks whose data is
present. The Advisor **configures by authoring the manifest**; it does not pass #10 a validator list and
requires **no change to #10**. **Honest exception:** two obligations have **no #10 target today** — the
**kill-switch** (`agentic-reliability`) and all of **`agentic-observability`** (#10's CR-9 is deferred to
#15). These produce **declared design artifacts** in the decision record (recorded, human-reviewed), *not*
manifest fields #10 validates; when #15 lands, observability's artifact gains a real #10 check. They are
stated as declared artifacts rather than as a manifest→#10 mapping that doesn't hold (the round-2 review
caught the v2 over-claim).

**Alternatives and their cost.**
- *A seed with an active-validator set (v1).* Cost: describes a mechanism #10 can't consume; the field is
  decorative and the "only relevant validators run" claim is unbacked (architect Blocker 1).
- *Claim kill-switch/observability author #10 fields anyway (v2).* Cost: two of six mandatory commands map
  to #10 fields/checks that don't exist — the same fiction as the seed, recurring per-command (round-2 F1).
- *The Advisor validates/generates too.* Cost: two implementations of the same rules that drift — the
  double-source problem.

**Consequences.** (+) One source of truth; truly additive (no #10 change); the "configures, doesn't
duplicate" property is demonstrable against #10's real activation model, and the two exceptions are honest.
(−) Kill-switch and observability are human-reviewed, not machine-validated, until their targets exist
(observability with #15); the Advisor must author the rest correctly for #10 to react — covered by the
manifest-authoring tests (test plan §6).

---

## ADR-A6: The floor is a deterministic function of Tier + risk; the ladder offers deferrable rungs

**Status:** Accepted (this **refines** the v1 decision, which introduced an L0–L4 "ladder" as a scale
alongside HITL's Tier 0–3 without reconciling them — the architect review's orthogonal-machinery catch,
and prose triggers that two implementers would compute differently).

**Context.** The floor (the controls that can't be skipped) must be **auditable** — reproducible for a
given declared risk — and must **reuse HITL's existing Tier model** (requirements §6: no new orthogonal
machinery). v1's L0–L4 rungs were a second scale with prose triggers and no precedence rule.

**Decision.** The floor is a **deterministic function of the existing Tier (0–3) plus an enumerated set of
agentic risk factors** (stakes, side_effects, data, autonomy, scale). Each floor rule fires monotonically;
if several apply, the command is mandatory (union). Commands above the floor are **offered as deferrable
rungs** — the "add now or defer" ladder is a *human-facing narrative over the same Tier+risk axis*, not a
competing scale. **The floor is non-silently-droppable but waivable:** a floor command cannot be dropped
silently (below the floor without a waiver is a blocker), but it **can** be dropped via an **explicit,
tier-appropriate waiver** recorded in the decision record (owner, reason, tier-limit, revisit) — HITL's
own hard-gate precedent (FR-25: "hard-blocked until … *or waived*") and consistent with "humans decide"
(ADV-9). **Determinism is scoped to the computation given declared factors**, not to whether two people
declare the same scenario identically (a softer property the categorical vocabulary mitigates).

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
regenerated from the accumulating scenario record **at each meaningful step**, and rendered **terminal-first
in three ways from one source**: (a) a terminal-native inline text map re-printed at each milestone (the
live view, no browser); (b) a Markdown + Mermaid map in the decision record, IDE/GitHub-previewable and
auto-updating on file change; (c) an optional rich interactive HTML rendering. On an **artifact-capable
surface** (c) runs as a **combined "chat + live map"** mode — the intake re-publishes the map artifact to
the same URL each step, so the discussion and the evolving map sit side-by-side. Two constraints keep it
in-lane: the artifact is a **live view, not an input** (sandboxed, can't post answers back — the
conversation stays the input), and it is the **rich tier only** (terminal-text is the universal baseline).
All renderings share one **node-type visual vocabulary** (agent/service/datastore/external/store + message
+ gate; ASCII equivalents in the terminal), so a component's kind reads at a glance. HITL **writes files
and publishes/prints**; live refresh is the surface's, not a server HITL runs.

**Alternatives and their cost.**
- *A hosted live dashboard.* Cost: crosses governs-not-runtime (a runtime service HITL would host), and
  forces a browser on terminal users.
- *HTML-only.* Cost: forces a browser context-switch on the terminal-first majority — friction that defeats
  the "picture it while you discuss it" purpose.
- *A final diagram only (not evolving).* Cost: loses the "watch it take shape / see what's left out as you
  choose" value that is the whole point.

**Consequences.** (+) Terminal users see the map evolve inline with no browser; IDE users get a live Mermaid
preview for free; the rich HTML is there when wanted; all from one deterministic regenerate, so the map
never drifts from the design. (−) Three renderings to generate and keep consistent — mitigated by one data
source and a shared template.

---

## ADR-A9: The intake integrates into the existing intake — precede for compound, skip for simple, never replace

**Status:** Accepted (added after round-2; the architect review found ADV-13's required integration into
`pm-design-feature`/`AGENTS.md` had *no design* — a Must-priority sequencing gap, not deferrable to LLD).

**Context.** ADV-13 requires the Advisor to select the delivery surface and route into the compound-agentic
workflow, integrating with `pm-design-feature` and `ai/codex/AGENTS.md`. The open question the review named
is architectural: does the Advisor **gate, precede, or replace** the existing single-agent intake?

**Decision.** The Advisor is the **compound-agentic branch of the existing intake**, not a replacement.
`pm-design-feature`'s existing "what is the delivery surface?" step gains a branch: once the elicited system
has **≥2 components and ≥1 inter-component edge**, it **hands off to `hitl:agentic-intake`**; a
single-component product stays on the existing single-agent path unchanged. `ai/codex/AGENTS.md` gains a
matching routing rule so the Codex design path follows the composed workflow for compound systems. The
trigger is evaluated from the intake's own elicited component/edge count — no new detector. So: **precede
for compound, skip for simple, never gate or replace** the deterministic flow.

**Alternatives and their cost.**
- *No integration design (v2).* Cost: a Must requirement with no mechanism; an implementer must invent the
  sequencing — the round-2 blocker.
- *The Advisor replaces `pm-design-feature`.* Cost: breaks the existing single-agent and deterministic
  flows; a far larger, unnecessary change.
- *A separate detector tool.* Cost: net-new machinery to decide "is this compound?" when the intake already
  elicits the component/edge count.

**Consequences.** (+) A concrete, minimal integration: one branch in `pm-design-feature`, one rule in
`AGENTS.md`, reusing the intake's own elicitation. Simple products are untouched. (−) Two existing
artifacts (`pm-design-feature`, `AGENTS.md`) get a small, tracked change — enumerated in the LLD's file
list.

---

## Decision index

| ADR | Decision | One-line |
|---|---|---|
| ADR-A1 | A1 | Advisor = a set of harness-run commands (not a monolith, not an app) |
| ADR-A2 | A2 | Catalog = curated, versioned data; curated refresh, not live lookup |
| ADR-A3 | A3 | Recommend, never decide; human confirms; record chosen/rejected |
| ADR-A4 | A4 | HITL composes a proportionate workflow; run only what's relevant |
| ADR-A5 | A5 | Commands author the manifest; #10 reacts — no seed, no #10 change; **exception**: kill-switch/observability are declared artifacts (no #10 target yet) |
| ADR-A6 | A6 | Floor = deterministic fn of Tier + risk; **non-silently-droppable but waivable** (FR-25 precedent); ladder offers rungs |
| ADR-A7 | A7 | Record the build-vs-buy decision + portability diligence; a human carries it — provision nothing, auto-hand-off to nothing |
| ADR-A8 | A8 | Evolving map = terminal-first generated view (inline text + Mermaid + optional HTML); regen per step; no live server |
| ADR-A9 | A9 | Intake integrates into `pm-design-feature`/`AGENTS.md` — precede for compound, skip for simple, never replace |
