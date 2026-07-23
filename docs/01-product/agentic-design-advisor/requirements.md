# Agentic Design Advisor: Requirements

> **What** the surface must do, for the HITL enhancement that encodes agentic-systems expertise as
> **runnable commands** that ask the questions an expert asks, understand the whole scenario, and let HITL
> **compose the right-sized workflow** for the change. Product one-liner: **FR-28** in the
> [PRD](../prd.md). The **how** (command set, intake, workflow composition, floor computation) is the
> design package at [`docs/design/agentic-design-advisor/`](../../design/agentic-design-advisor/). Status:
> **draft, pending PM review**. Related: EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10)
> (compound-agentic surface — the commands produce its manifest inputs) and
> [#8](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/8) (best-practice-advisory — the Advisor
> is its agentic-domain instance). **Tracked as EPIC [#35](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/35)**
> (sub-issues [#36](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/36)–[#41](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/41):
> catalog · intake+integration · commands · composer+floor · map · CI/docs). **v3.2** — reshaped around
> **commands + composed workflow** (v2), revised after pm + architect rounds (v3), then **core-scope-locked**
> after the round-4 objectives review (map → terminal+Mermaid core, HTML/live deferred; non-circular routing;
> obligation-first floor; contract-authoring seam); see §12 and [`../../design/agentic-core-scope.md`](../../design/agentic-core-scope.md).

## 1. Problem

Teams adopting agentic workloads don't know which questions to ask. The expertise (where the determinism
boundary goes, when a step needs an agent vs a deterministic service, which actions need a human gate, how
to bound privilege, how you'll detect misbehavior, how you kill it fast) lives in a few specialists' heads.
Without it, teams land in one of two failure modes:

- **Under-govern:** ship an over-privileged agent, no human gate on an irreversible action, no way to
  detect or stop it — and take the incident.
- **Over-govern:** reach for the full ceremony on a two-agent internal tool, drown the team, and get
  routed around — governance that governs nothing.

**Evidence.** *Internal:* this is not hypothetical for HITL — the compound-agentic surface (#10) was itself
designed with mandatory machinery that **over-governed** (e.g. requiring sagas for flows that didn't need
them) until an independent review caught it — direct evidence that even experts mis-size without a
right-sizing discipline. *External:* the enterprise agent-platform landscape is converging on exactly the
concerns this Advisor elicits — an industry analysis of Amazon, Microsoft, and Google's platforms names
the questions enterprises must ask (did the agent complete the task, choose the right tools, **exceed its
authority**, what did it cost, **did quality regress after a model update**) and the portability/state/
governance diligence a team owes itself (see [`References`](#11-references)). Those are the Advisor's
lenses. *(This external evidence **supports the lens taxonomy** — that these are the right concerns — more
than it proves the design-time pain directly; the pain-rate substantiation is the #22 work below.)*
*Deferred:* outcome-quality substantiation (rate of agentic changes shipping under- or over-governed) is
**deferred to the metrics epic (#22)**, which will instrument it; this doc asserts no outcome numbers HITL
cannot yet measure — but it does carry a **baselined adoption metric** (§8) that is measurable today.

## 2. Users

| User | What they need |
|---|---|
| **Product Manager** | to be guided to a right-sized design without hiring an agentic-systems specialist |
| **Technical Advisor / Architect** | the expert questions asked and the material decisions surfaced, recorded with rationale |
| **Developer** | a clear, composed workflow of commands to run — no guessing which controls apply |
| **Ops** | the deployment (build-vs-buy) and operability decisions recorded, to carry into the platform track |

## 3. Scope

The **Agentic Design Advisor** is a set of HITL **commands**, run by the harness, that:

- are each **independently runnable** (anyone can invoke `hitl:agentic-privilege` on an existing design,
  or run the whole intake) — the work is decomposed into commands, not a monolith;
- start with a **thorough intake** that understands the *whole* scenario — the way HITL's deterministic
  design intake (`pm-design-feature`) does — asking the expert questions so critical things are not missed;
- let **HITL compose the right-sized workflow** after understanding the requirements: which commands this
  change needs, in what order — a two-component read-only flow gets a short workflow, a payments mesh gets
  a full one;
- set a **risk-appropriate floor** (the commands that cannot be skipped) and **offer the rungs above it**
  as deferrable (the adoption ladder — start minimal, add later);
- **recommend** the simplest option that fits (never silently decide) and **record** every material
  decision;
- **produce real artifacts** — manifest fields and design docs the compound-agentic surface (#10) and the
  human then act on.

It is the **front door** to the compound-agentic surface: the Advisor elicits and composes; #10 validates
and generates; the human decides.

## 4. Goals

1. **Encode the expertise as commands.** An expert's question set and material decisions, as runnable
   commands a non-expert invokes.
2. **Understand the whole scenario.** As thorough as the deterministic intake — miss nothing critical.
3. **Right-size by composing the workflow.** Match the commands run to the actual risk; nothing more.
4. **Set an honest floor, offer the rungs.** A calibrated minimum that can't be skipped, plus deferrable
   controls offered explicitly.
5. **Propose, don't decide.** Recommend with rationale; the human confirms or overrides; record both.
6. **Produce durable evidence** and real manifest/design artifacts the rest of HITL consumes.

## 5. Requirements

Requirement IDs are `ADV-<n>` (Advisor Requirement).

> **Absorbed from #10 (2026-07-21):** **CR-1** (surface selection / design-track routing) → **ADV-13**;
> **CR-19** (the capability menu) → **ADV-6 + ADV-11**. #10 now owns only representation, validation, and
> evidence.

| ID | Requirement | Priority |
|---|---|---|
| **ADV-1** | The Advisor is delivered as a **set of runnable commands** (`hitl:agentic-*`), each **independently invocable by anyone** and each doing one expert concern; it is **not** a monolithic skill. **Two tiers:** the **intake** (ADV-2) *elicits* the whole scenario across all lenses; the **per-concern commands** *own the decision and consequence* for their lens (ADV-4). The intake is an elicitor that hands off to the composed commands — not the monolith this requirement warns against. | Must |
| **ADV-2** | A **thorough intake command** (`hitl:agentic-intake`) understands the **whole scenario** the way the deterministic intake does, asking the expert questions across every lens so critical things are not missed. Lenses: component right-sizing (agent vs deterministic; simple vs deep; *do you need multiple agents at all*), the **determinism boundary**, **side effects / irreversibility**, **human gates**, **privilege / identity / trust** (incl. the lethal-trifecta check), **orchestration / topology** (sync/async, loops), **reliability / failure modes** (idempotency, retry, DLQ), **observability / detectability** (how misbehavior is seen in production; targets OpenTelemetry GenAI conventions; includes the **PM eval-console** — the PM-facing surface to run evals + review results/traces — a floor obligation per the 2026-07-22 hard directive, gated by #10's `check_observability`), **kill-switch / rollback** (how the system is stopped fast), **memory / state**, **PII / data classification**, **portability** (bind model/memory/tool providers as capabilities via config — do not embed a provider in agent logic; Twelve-Factor "attached resources"), **evaluation** (incl. model/prompt-version drift), **cost / amplification**, **deployment / build-vs-buy** (ADV-14), and **stakes / tier / compliance**. | Must |
| **ADV-3** | After the intake understands the requirements, **HITL composes the right-sized workflow** — the ordered set of `hitl:agentic-*` commands this change needs. The composition is **proportionate**: a change asks for and runs only the commands its risk and shape warrant (a lens with no relevant data contributes no command). | Must |
| **ADV-4** | **Every lens/question maps to a concrete consequence** — a component classification, a boundary obligation, a required gate, a **command in the composed workflow**, or a **floor** entry. A lens with no downstream effect is not shipped. | Must |
| **ADV-5** | The **floor is the set of controls #10 will enforce** — computed as a pure function of **#10's per-check activation predicates** (a command is floor iff a #10 check it owns activates on the manifest the scenario implies), so the Advisor floor can never disagree with #10 (round-5 B1). **Tier (0–3) + risk factors set the required *depth* within a floor control, not whether it is floor.** Two floor obligations have no #10 check and are added by rule (human gate, kill-switch). Commands with no firing #10 check are **offered as deferrable rungs** (memory when hinted; deploy when greenfield/platform-change/durable/requested). The floor reuses Tier for depth; it adds no competing governance axis. | Must |
| **ADV-6** | For each material decision with modern options (component kind, orchestration pattern, memory strategy, inter-agent protocol, async transport), the Advisor **presents the menu with when-to/when-not, recommends the simplest option that fits with rationale, and records chosen + rejected** (the capability menu / best-practice-advisory, #8). **The build-vs-buy / deployment decision is owned exclusively by ADV-14**, not by this generic menu — ADV-6 does not present a deployment menu. | Must |
| **ADV-7** | The Advisor produces **durable, reviewable artifacts**: a **decision record** (questions, answers, recommendations, chosen/rejected, floor, composed workflow) that regenerates cleanly on a re-run. | Must |
| **ADV-8** | The commands **produce real manifest fields and design artifacts**. The compound-agentic surface (#10) then activates **only the relevant validators from the manifest content it finds** (its existing per-check activation) — the Advisor **configures by producing the right manifest, it does not feed #10 a validator list**. No change to #10 is required. The command→manifest-field map (LLD §5.1) must cover **every core #10 check**, including the **contract step** (`agentic-topology`/`agentic-boundary`) that authors `facade_apis` **and** `interactions.authorization` — without these, #10's `check_references`/`check_authorization` have nothing to validate (round-4 B1). **Exception (honest):** **one** obligation has **no #10 target today** — the **kill-switch** (from `agentic-reliability`) produces a **declared design artifact** in the decision record (recorded, human-reviewed), *not* a manifest field #10 validates. **`agentic-observability` now authors a real #10 field** — the `observability` block gated by `check_observability` (a floor gate, per the 2026-07-22 hard directive that a PM eval-console + live traces is required); #10 gained that check via its own CR-9 elevation, the Advisor simply authors into it. Every other command authors manifest fields #10 already reacts to. | Must |
| **ADV-9** | The Advisor **recommends, never silently decides.** Every recommendation is confirmable and overridable by the human, and an override is recorded with its rationale. | Must |
| **ADV-10** | The intake is **role-aware**, reusing HITL's **actual roles** (`docs/playbook/roles.md`: PM, Technical Advisor, Architect, Developer, QA, Ops) — each command/lens is attributed to the role whose concern it is. (Reuse of the role *taxonomy*, applied to asking rather than reviewing, is validated in design.) | Should |
| **ADV-11** | The question/capability catalog is a **curated, human-refreshed** artifact (a curated catalog bump, **not** a live external lookup — that would cross document-driven / governs-not-runtime). It has a **named owner** and a **periodic refresh cadence** (independent of change events, so it cannot go stale indefinitely); additionally a Tier-3 agentic change prompts an **"is the catalog current?"** review step, and a stale-catalog finding is **recorded and surfaced** (not silently ignored). | Should |
| **ADV-12** | The floor is **auditable and non-silently-droppable.** The floor is a deterministic function of **#10's activation predicates** (ADV-5, round-5 B1) evaluated over the declared scenario, so the floor *computation* is reproducible and provably equals what #10 will enforce (the requirement does **not** claim two people describe the same scenario identically — elicitation uses categorical definitions to minimize that variance). A floor command **cannot be dropped silently**; dropping one requires an **explicit, recorded, tier-appropriate waiver** written to the enforcing check's own store (e.g. #10's eval waivers) — HITL's hard-gate precedent (PRD **FR-25**: "hard-blocked until … **or waived**"), consistent with "humans decide" (ADV-9). Below the floor *without* a waiver is a blocker. Above the floor, the team defers freely. | Must |
| **ADV-13** | The **intake selects the delivery surface and composes the compound-agentic workflow**. To avoid a routing circularity (you cannot know the surface before you know the shape), the intake **always begins with a short topology probe** — component count and whether any component calls another — and then routes: **≥2 components and ≥1 inter-component edge → compound surface**; otherwise the existing single-agent surface. One selector, no chicken-and-egg. The selection + composition integrate into **`pm-design-feature`** and **`ai/codex/AGENTS.md`**. *(Absorbed from #10 CR-1; round-4 B2.)* | Must |
| **ADV-14** | A **`hitl:agentic-deploy` command** surfaces the **build-vs-buy** decision: it elicits the drivers (durable-execution need, scale, ops capacity, compliance / data-residency, existing cloud, time-to-market), presents the menu (**from-scratch / managed platform / self-hosted OSS**) with implementations named only as **examples** (CR-10), **recommends** with a bias toward *managed unless there is a specific reason to build*, and **records** the decision. When it recommends **managed**, it **surfaces the lock-in trade-off** and requires the team to answer the three portability-diligence questions: **governance** (is the platform's control neutral or vendor-owned), **packaging** (can the same agent artifact run on another cloud without a rewrite), and **state** (can the agent's memory/state be exported) — so "buy" is chosen with eyes open, not by default. A **human carries the recorded decision into HITL's platform/ops track** (FR-25). The Advisor **does not** provision infrastructure, pick a vendor, ship a cloud module, or auto-hand-off. | Must |
| **ADV-15** | The front door generates an **evolving system map** — a **design-time** view (extends #10's generated topology view; **not** a runtime dashboard) that **regenerates incrementally as the intake proceeds** (a component named/typed, a boundary drawn, a gate added), from the accumulating scenario record — so as agents are added one at a time the map grows one node/annotation at a time. It shows the composed topology and a **getting / available / not-needed** breakdown, so the team can *picture the system* and *see the proportionality* — what is included, what is offered, and what is left out **and why**. It reads with a **consistent visual vocabulary per component type** (a datastore looks like a datastore, an agent like an agent, a message like a message). **Core (v1) is terminal-first — no browser required — rendered as terminal text + Markdown/Mermaid** (regenerated per intake step). A **rich HTML / live-artifact combined mode** (updating live alongside the discussion) is a **deferred enhancement** with a defined host API — not core (round-4 M8). It is design-time only (HITL does not run a live server). *(The specific renderings — terminal text, Mermaid, the deferred HTML/live mode, the icon vocabulary, and the no-live-server constraint — are **design**, HLD §9.7 / ADR-A8 / LLD §6.)* | Should |

## 6. Constraints

- **Governs, does not run.** The commands elicit, record, and produce design artifacts; they ship no
  runtime, dashboard, engine, or provisioning.
- **Reuse existing mechanisms.** Commands/skills, reviewer-role taxonomy, the capability menu (#8), the
  manifest + #10's per-check activation, **the existing Tier 0–3 model** (the floor reuses Tier — no new
  tier axis), the breadcrumb, and durable-artifact conventions. No new orthogonal machinery.
- **Proportionate to itself.** The composed workflow must be light for light changes; an over-heavy
  Advisor would defeat its purpose.
- **Document-driven.** Output is durable, reviewable artifacts — never a lost chat.
- **Additive.** The commands produce manifest content #10 already knows how to react to; #10 is unchanged.

## 7. Non-goals

- **Not a runtime** and not an autonomous decider — it recommends; humans decide (ADV-9).
- **Not the validators/design** — the commands feed #10; they do not re-implement its schema or checks.
- **Not a monolith and not a fixed questionnaire** — it is decomposed commands (ADV-1) whose workflow is
  composed to the change (ADV-3); a static form that asks everyone everything is the over-governance
  failure this feature prevents.
- **Not a provisioner** — on build-vs-buy it decides the *direction* and records it for a human to carry;
  it provisions nothing and auto-hands-off to nothing (ADV-14).
- **Not domain-specific** — it asks general agentic-systems questions; it encodes no vertical's nouns.

## 8. Success measures

### 8.1 Success metric (baselined today)

- **Adoption:** the share of **Tier-2+ agentic changes that run the Advisor before design**. Baseline
  **0** today (the feature does not exist). Target **≥ 80%** within **2 releases** of GA. *(A secondary
  count — composed workflows produced per month — tracks usage.)* Outcome-quality metrics (rate of agentic
  changes shipping under-/over-governed, before/after) require instrumentation and are **deferred to #22**;
  asserting an outcome baseline here would be dishonest.

### 8.2 Acceptance scenarios (pass/fail)

1. A PM **with no agentic-systems expertise** runs the intake and comes out with a right-sized **composed
   workflow**, a stated floor, and a decision record — without a specialist in the room.
2. A **low-stakes** two-agent read-only flow composes a **short workflow**; the saga, deep-memory, and
   reliability commands are **not** included. **Observability is included** (floor for any agentic system —
   the 2026-07-22 hard directive) but at **minimal depth** — a basic trace + a simple PM eval-console
   declaration, not a full OTel/rich-console build. *(Presence is non-negotiable; depth scales with tier —
   the proportionate reading of the hard requirement.)*
3. A **high-stakes** irreversible-action flow composes the **full workflow**, and its floor (declare +
   human gate + idempotency + detectability + kill-switch) **cannot be dropped silently** (ADV-12).
4. **Every recommendation** is recorded with a rationale and is overridable (ADV-6/ADV-9).
5. The commands **produce manifest fields** that make #10's per-check activation run exactly the relevant
   validators (ADV-8) — verified against a low- and a high-risk fixture; `agentic-observability` authors the
   `observability` block #10's **`check_observability` floor-gates** (hard directive); the **kill-switch**
   artifact is recorded as a **declared design artifact** (no #10 target yet), not silently omitted.
6. Rerunning the intake after a change reflects the change (durable, re-runnable), not a one-shot chat.
7. On **build-vs-buy**, a low-stakes small-scale flow is recommended a **managed platform**, a specific
   reason is required to override toward **build**, the decision is **recorded**, and a human is prompted
   to carry it to the platform track — nothing provisioned or auto-handed-off (ADV-14).
8. The floor **computation is deterministic** given the declared risk factors: two runs on the same
   *declared* factors compute the identical floor (ADV-12). *(Consistency of the human-declared factors
   themselves is a separate, softer property, mitigated by categorical definitions — design.)*
9. A team attempting to drop a floor command is **blocked** unless it records an **explicit,
   tier-appropriate waiver**; the waiver (owner, reason) lands in the decision record (ADV-12).
10. *(ADV-15, Should)* The evolving map renders **in the terminal with no browser** and updates as the
    intake proceeds. Being a Should, it does not hard-gate the implementation.

## 9. Version

Ships on the **2.x line**. Version slotting (relative to #10 / metrics #22) is a release-planning decision;
the Advisor may ship as part of, or ahead of, the compound-agentic surface since it is that surface's front
door.

## 10. Standards alignment (pointer)

The Advisor's lenses are aligned with where the industry's enterprise agent platforms are converging
(runtime, memory, tool gateway, identity, observability, governance), and with the named standards its
lenses reference (OpenTelemetry GenAI conventions for observability; Twelve-Factor "attached resources" for
portability; the Linux Foundation Agentic AI Foundation for neutral governance). *The full analysis and the
"HITL manifest = the design-time portable agent contract" rationale is **design** (HLD §12 / ADR-A5) and
the source is [`References`](#11-references) — not a requirement here.*

## 11. References

- Janakiram MSV, *Amazon, Microsoft, and Google are converging on the same enterprise agent architecture*,
  The New Stack, 2026-07-20 —
  <https://thenewstack.io/amazon-microsoft-and-google-are-converging-on-the-same-enterprise-agent-architecture/>
  (the runtime-layer convergence, the missing portable contract, and the governance / packaging / state
  diligence questions folded into ADV-14).

## 12. Review history

- **v1** drafted with #10's CR-1/CR-19 relocated in (requirements + HLD + ADRs + test plan).
- **pm + architect review (2026-07-21):** both returned NOT READY. Resolved in **v2**: the fictional
  seed→#10 and deployment→platform *contracts* removed (the commands produce the manifest; the deployment
  decision is recorded and human-carried, ADV-8/ADV-14); the floor made a **deterministic** function of
  **Tier + risk** with the ladder as offered rungs (no new axis, ADV-5); **observability** and
  **kill-switch** lenses added (ADV-2); the **command decomposition + composed workflow** model adopted
  (ADV-1/ADV-3); roles aligned to the real set (ADV-10); ADV-11 pinned to a curated refresh; problem
  evidence cited (#10 over-governance) with quantitative metrics deferred to #22; §8 reframed as
  acceptance scenarios. The HLD/ADRs/test-plan cascade from this doc.
- **v2.1 (2026-07-22):** folded in the industry-convergence article — external evidence (§1), the
  **portability / lock-in diligence** on the deploy lens (ADV-14), the **bind-capabilities-not-embed**
  portability facet (ADV-2), and standards alignment.
- **round-2 pm + architect review (2026-07-22):** both again NOT READY, but confirmed the two v1 blockers
  (seed→#10, deploy handoff) genuinely closed and the core sound. Resolved in **v3**: **floor is now
  non-silently-droppable + waivable** per FR-25 precedent (ADV-12); a **baselined adoption metric** added
  (§8.1); the **kill-switch/observability #10 gap** made honest (ADV-8 — declared artifacts, observability
  validator with #15); **ADV-6/ADV-14 deployment overlap** resolved; **ADV-1/ADV-2 two-tier split** stated;
  **ADV-12 determinism** scoped honestly to *declared* factors; **ADV-11** given an owner/cadence;
  **ADV-15** abstracted to WHAT (renderings → design); **§10 standards analysis** demoted to a pointer
  (taxonomy). Design-side fixes (ADV-13 integration mechanism, worked-example check list, composition +
  consequence tables, headers) cascade to the HLD/ADRs/test-plan.
- **round-4 objectives review + core scope lock (2026-07-22):** the joint #10+Advisor review returned
  REVISIONS REQUIRED (over-scope the central finding). Response: **lock a minimal sound core, defer the
  heavy/contested parts** ([`../../design/agentic-core-scope.md`](../../design/agentic-core-scope.md)).
  Requirements changes in **v3.2**: **ADV-13** routing made **non-circular** (topology probe first, B2);
  **ADV-14/ADV-15 reordered** (m2); **ADV-15** map trimmed to **terminal+Mermaid core**, HTML/live-combined
  mode **deferred** (M8); **ADV-8** now requires the command→field map to cover the **contract-authoring
  seam** (`facade_apis` + `authorization`, B1). Design-side fixes (obligation-first floor B3, scenario +
  consequence schema M3, canonical-state/merge M4, role-attribution-not-gating M9, `deferred`-vs-`waiver`
  terminology m3) cascade to the HLD/ADRs/LLD/test-plan. The eval scope that #10 enforces is narrowed to
  **per-agent + e2e** (universal coverage deferred) — the Advisor's evaluation lens is unchanged; it elicits,
  #10 enforces the narrowed floor.
- **hard directive — observability + PM eval-console (2026-07-22):** the user directed that a PM eval
  console + live traces is a **hard requirement** (model: *HITL enforces, the product builds*). CR-9/CR-16
  are elevated to the **floor**; `agentic-observability` becomes a **floor command** authoring the
  `observability` block #10's new **`check_observability` floor-gate** validates (ADV-8's honest exception
  shrinks to the kill-switch alone; ADV-2 observability lens now names the PM eval-console). **Presence is
  non-negotiable; depth scales with Tier** (the proportionate reading — acceptance scenario 2 updated). HITL
  ships the declaration + validator + gate; the product builds the running console/trace backend (#21
  reference), so O1 governs-not-runtime holds.
- **round-5 cold Codex review (2026-07-22):** REVISIONS REQUIRED (4 blockers + 8 majors). The core finding:
  the Advisor floor was hand-tuned with Tier gates that contradicted #10's content-based activation (the
  reconciling principle was asserted, not delivered). Fixed at the **mechanism** level in **v3.3**: the floor
  is now **derived from #10's activation predicates** (floor ≡ activation, `ACTIVATION-MIRROR` lint; ADV-5/12,
  B1); **Tier scales depth, not membership**; the canonical state is a **machine-readable YAML** holding the
  authored outputs, with the Markdown decision record generated from it (B4); the catalog `consequence` is
  reconciled to one option→list-of-tagged-unions shape (B4); routing gets an **`agentic` gate** before the
  probe and a single selector (M1, ADR-A9 rewritten); `agentic-deploy` composes only when
  greenfield/platform-change/durable/requested (M6). Exact `COMPOSE-LOW`/`COMPOSE-HIGH` fixtures replace the
  impossible ones (B2). #10-side (compound package): result-review + saga `parallel` + multi-owner baseline
  removed from core (→#42), observability gate made real + tier-scaled (M3), release re-scoped so core = 2.2.0
  (M4). Tracker bodies #12/#13/#15/#38/#41 rewritten (M7).
