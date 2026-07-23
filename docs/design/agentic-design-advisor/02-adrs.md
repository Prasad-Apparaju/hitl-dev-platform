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

## ADR-A5: The commands recommend + record + hand off — they do NOT author the manifest (re-scoped 2026-07-23)

**Status:** Accepted, **rewritten 2026-07-23 (v4).** Prior versions had the commands **author the manifest**
#10 validates (v1: via a fictional seed; v3.3: via a canonical-state writer + `floor ≡ activation`). Round 8
showed that seam could only be validated by the real validator, and the product owner named the root cause:
**auto-authoring the manifest puts the PM front door into design/implementation — the line HITL must hold,
and it makes the gate audit HITL's own output.** So auto-authoring is removed.

**Context.** #10 owns the schema, validators, and generators. The Advisor is a PM-lane elicitor/recommender.
The question: should the Advisor *author* the design artifact (the manifest) that #10 gates, or *recommend*
it and hand off to a human?

**Decision.** The commands **elicit + recommend + record** — each produces a recommendation and a
decision-record entry, and contributes TODO notes to a **manifest skeleton**. **No command authors a
validated manifest field.** A **human authors** the real manifest in the design phase; **#10 validates** the
human-authored manifest. The Advisor holds the requirements/design boundary and requires **no** change to
#10, which activates purely from human-authored content and ships independently.
The **observability + PM eval-console** hard requirement (2026-07-22) survives cleanly: the Advisor
**recommends** it, and #10's **`check_observability`** **enforces** it on the human-authored manifest.

**Alternatives and their cost.**
- *Advisor auto-authors the manifest (v1–v3.3).* Cost: puts the PM front door into design/implementation
  (the line HITL exists to hold); makes the gate audit HITL's own output; and — proven across rounds 4–8 —
  is only validatable by building the real validator, so it never converges on paper.
- *Advisor validates/generates too.* Cost: two implementations of #10's rules that drift.

**Consequences.** (+) The Advisor stays in the PM/elicitation lane; #10 has one source of truth (the
human-authored manifest) and ships independently; the entire failing auto-authoring surface (writer,
`floor ≡ activation`, ownership/author-complete) disappears. (−) A human must author the manifest from the
handoff — but that is HITL's normal, and better, pattern (scaffold + author + gate).

---

## ADR-A6: The floor is a Tier + risk RECOMMENDATION (advice); #10 is the gate (re-scoped 2026-07-23)

**Status:** Accepted, **rewritten 2026-07-23 (v4).** Rounds 5–8 made the floor a *pure function of #10's
activation* so the Advisor could author a matching manifest — an equivalence that had to be *proven* and
kept failing (a copy that drifts, unowned checks, a spike that couldn't validate it). With auto-authoring
removed (ADR-A5), the floor no longer needs to equal #10's activation at all: **the Advisor recommends, #10
enforces.**

**Context.** The Advisor should tell a team which controls it shouldn't skip — but it is not the gate, and
it must not re-implement or predict #10.

**Decision.** The floor is the **Advisor's recommended set of mandatory controls**, a deterministic function
of the existing **Tier (0–3) + risk factors** (`side_effects`, `data`, `autonomy`, `stakes`, `scale`) —
expert judgment, not a mirror of #10. **Tier scales the recommended depth** (observability report vs console,
etc.), not membership. The recommendation is **advice**: a team may skip a recommended control, but the
Advisor **records the skip** (owner + reason) and surfaces it — never silent. The **actual hard
block-or-waive** happens **downstream at #10** (its validators + HITL's tier/waiver process, FR-25) on the
**human-authored** manifest. So "can't be skipped silently" holds by *recording*; "hard-blocked until … or
waived" holds *at #10*. No equivalence to prove, no activation to import.

**Alternatives and their cost.**
- *Floor ≡ #10 activation (v3.3).* Cost: only meaningful if the Advisor authors the manifest (removed); an
  equivalence that must be proven and drifts every round.
- *An absolutely non-waivable floor.* Cost: no human escape hatch — inconsistent with FR-25.
- *Prose triggers, no vocabulary.* Cost: two people compute different floors; not auditable.

**Consequences.** (+) Reproducible, auditable, reuses Tier, no equivalence to prove, no second copy of #10.
(−) The floor is advice; the real enforcement is #10 at design time — which is correct, because #10 is the
gate and the Advisor is the front door.

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
| ADR-A5 | A5 | Commands **recommend + record + hand off** — they do **not** author the manifest (re-scope 2026-07-23); a human authors it, #10 validates; observability is **recommended** (Advisor) + **enforced** (#10 `check_observability`) |
| ADR-A6 | A6 | Floor is a **Tier + risk recommendation** (advice, not a gate); a skip is **recorded**; the hard block-or-waive is **downstream at #10** on the human-authored manifest; Tier scales recommended depth |
| ADR-A7 | A7 | Record the build-vs-buy decision + portability diligence; a human carries it — provision nothing, auto-hand-off to nothing |
| ADR-A8 | A8 | Evolving map = terminal-first generated view; **core = inline text + Mermaid; rich HTML + combined live mode deferred** (M8); regen per step; no live server |
| ADR-A9 | A9 | Intake integrates into `pm-design-feature`/`AGENTS.md` — precede for compound, skip for simple, never replace |
