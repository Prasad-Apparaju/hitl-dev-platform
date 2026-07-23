# Agentic Design Advisor: Requirements

> **What** the surface must do, for the HITL enhancement that encodes agentic-systems expertise as
> **runnable commands** that ask the questions an expert asks, understand the whole scenario, and let HITL
> **compose the right-sized workflow** for the change. Product one-liner: **FR-28** in the
> [PRD](../prd.md). The **how** (command set, intake, workflow composition, the recommended floor, the
> handoff) is the design package at [`docs/design/agentic-design-advisor/`](../../design/agentic-design-advisor/).
> Status: **draft, v4.1 — one intake + recommendation report; neutral `agentic-design-handoff.yaml` (no manifest fields)**. Related: EPIC
> [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10)
> (compound-agentic surface — a human authors its manifest; #10 validates; the Advisor hands off, it does
> not author) and
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

The **Agentic Design Advisor** is **one HITL intake command** (`hitl:agentic-intake`), run by the harness,
that:

- runs a **thorough intake** that understands the *whole* scenario — the way HITL's deterministic design
  intake (`pm-design-feature`) does — asking the expert questions across every lens so critical things are
  not missed;
- produces a **right-sized recommendation report** — only the lenses this change's risk and shape warrant
  appear as sections (a two-component read-only flow → a short report; a payments mesh → a full one). *(The
  per-concern lenses are report sections, not 8 separate commands — round-9 M9.)*
- **recommends a risk-appropriate floor** (the controls that shouldn't be skipped — advice, enforced
  downstream by #10) and **offers the rungs above it** as deferrable;
- **recommends** the simplest option that fits (never silently decides) and **records** every material
  decision (chosen/rejected + rationale; a **skip** of a recommended control is recorded, never silent);
- **hands off to the design track** — a durable **decision record / recommendation report** plus a neutral
  **`agentic-design-handoff.yaml`** (components + connections + `proposed_kind`s + recommendation IDs +
  target-path hints, **not** a manifest) that a **human authors into a real design**; the Advisor **authors
  no manifest field** (not even `kind`).

It is the **front door** to the compound-agentic surface, and it stays in the **PM/elicitation lane**: the
Advisor **elicits, recommends, records, and hands off**; a **human authors the design** (the manifest); #10
**validates** the human-authored manifest. This boundary is the point of the feature — HITL must **not**
become a tool that lets a PM produce design/implementation artifacts. The Advisor produces requirements-level
outputs (decisions, recommendations, a right-sized workflow) and a handoff; the *design* is authored by the
design role in the design phase and gated by #10. *(This is the 2026-07-23 re-scope: the earlier model, in
which the Advisor's commands auto-authored a complete #10-valid manifest, crossed that line and is removed —
see §12.)*

## 4. Goals

1. **Encode the expertise as commands.** An expert's question set and material decisions, as runnable
   commands a non-expert invokes.
2. **Understand the whole scenario.** As thorough as the deterministic intake — miss nothing critical.
3. **Right-size by composing the workflow.** Match the commands run to the actual risk; nothing more.
4. **Set an honest floor, offer the rungs.** A calibrated minimum that can't be skipped, plus deferrable
   controls offered explicitly.
5. **Propose, don't decide.** Recommend with rationale; the human confirms or overrides; record both.
6. **Produce durable evidence + a clean handoff** — a decision record and a design handoff (scenario +
   recommended controls + a manifest skeleton) that a human authors into the design; the Advisor authors no
   design artifact itself.

## 5. Requirements

Requirement IDs are `ADV-<n>` (Advisor Requirement).

> **Absorbed from #10 (2026-07-21):** **CR-1** (surface selection / design-track routing) → **ADV-13**;
> **CR-19** (the capability menu) → **ADV-6 + ADV-11**. #10 now owns only representation, validation, and
> evidence.

| ID | Requirement | Priority |
|---|---|---|
| **ADV-1** | The Advisor is **one intake command** (`hitl:agentic-intake`) that produces a **recommendation report** — not a set of 8 per-concern commands (round-9 M9: proportionate to a recommendation front door). The intake elicits the whole scenario across all lenses (ADV-2); each lens is a **section of the report** with its recommendation + rationale (ADV-4), reusing the already-elicited answers (no re-elicitation). A team may **re-run the intake focused on a single lens** to refresh one recommendation, but there is no separate `hitl:agentic-privilege`/etc. command to run. No lens authors a manifest field — the report is *advice* the design role acts on. | Must |
| **ADV-2** | A **thorough intake command** (`hitl:agentic-intake`) understands the **whole scenario** the way the deterministic intake does, asking the expert questions across every lens so critical things are not missed. Lenses: component right-sizing (agent vs deterministic; simple vs deep; *do you need multiple agents at all*), the **determinism boundary**, **side effects / irreversibility**, **human gates**, **privilege / identity / trust** (incl. the lethal-trifecta check), **orchestration / topology** (sync/async, loops), **reliability / failure modes** (idempotency, retry, DLQ), **observability / detectability** (how misbehavior is seen in production; targets OpenTelemetry GenAI conventions; includes the **PM eval-console** — the PM-facing surface to run evals + review results/traces. The Advisor **recommends** this control at the floor; **#10's `check_observability`** is what *enforces* it on the human-authored manifest at design time — 2026-07-22 hard directive), **kill-switch / rollback** (how the system is stopped fast), **memory / state**, **PII / data classification**, **portability** (bind model/memory/tool providers as capabilities via config — do not embed a provider in agent logic; Twelve-Factor "attached resources"), **evaluation** (incl. model/prompt-version drift), **cost / amplification**, **deployment / build-vs-buy** (ADV-14), and **stakes / tier / compliance**. | Must |
| **ADV-3** | After eliciting, the intake **composes a right-sized recommendation report** — only the lenses this change's risk and shape warrant appear (a lens with no relevant data contributes no section). Proportionality is *which lenses are in the report*, not how many commands run. | Must |
| **ADV-4** | **Every lens/question maps to a concrete consequence in the recommendation report** — a recommended component classification, a recommended boundary control, a recommended gate, a lens **section**, or a **floor** entry (a recommended-mandatory control). The consequence is a *recommendation the human acts on in design*, never an authored manifest field. A lens with no downstream effect is not shipped. | Must |
| **ADV-5** | The **floor is the Advisor's recommended set of mandatory controls** — a deterministic function of the declared risk factors, stated honestly (round-9 M2): **membership** is driven by the safety-relevant factors — *any agent* ⇒ classify/boundary/privilege/observability/evals; *irreversible side effects* ⇒ human gate; *supervised/autonomous + side effects* ⇒ kill-switch. **Tier + `data`/`stakes`/`scale` inform the recommended *depth*** of a floor control (e.g. observability report vs console), not membership — the doc does not claim a factor drives the floor unless the function uses it. It is **advice, not a gate**: the Advisor recommends and records; enforcement is **#10's validators at design time** on the human-authored manifest. Above the floor = offered rungs. The floor does **not** re-implement or predict #10's activation (removed). | Must |
| **ADV-6** | For each material decision with modern options (component kind, orchestration pattern, memory strategy, inter-agent protocol, async transport), the Advisor **presents the menu with when-to/when-not, recommends the simplest option that fits with rationale, and records chosen + rejected** (the capability menu / best-practice-advisory, #8). **The build-vs-buy / deployment decision is owned exclusively by ADV-14**, not by this generic menu — ADV-6 does not present a deployment menu. | Must |
| **ADV-7** | The Advisor produces **durable, reviewable artifacts**: a **decision record** (questions, answers, recommendations, chosen/rejected, floor, composed workflow) that regenerates cleanly on a re-run. | Must |
| **ADV-8** | The Advisor's output is a **recommendation + a handoff, not a design.** It produces (a) the **decision record / recommendation report** (ADV-7) and (b) a **neutral design-handoff file `agentic-design-handoff.yaml`** — explicitly **NOT** `system-manifest.yaml`. The handoff carries the elicited **components** and **connections**, a **`proposed_kind`** per component (a *recommendation*, not a `kind:` field), the recommended controls as **recommendation IDs**, and **target-path hints** (which manifest fields the design role must author). It contains **no `system-manifest.yaml` field** — not even `kind`, because a component kind is a design classification (round-9 B2). A **human authors** the real manifest from the handoff in the design phase; **#10 validates the human-authored manifest**. The Advisor **does not** author any manifest field (including `kind`), run #10's validators, or produce the design artifact — that would put the PM front door into design/implementation, which this feature exists to prevent. #10 needs **no** input from the Advisor and ships independently. | Must |
| **ADV-9** | The Advisor **recommends, never silently decides.** Every recommendation is confirmable and overridable by the human, and an override is recorded with its rationale. | Must |
| **ADV-10** | The intake is **role-aware**, reusing HITL's **actual roles** (`docs/playbook/roles.md`: PM, Technical Advisor, Architect, Developer, QA, Ops) — each command/lens is attributed to the role whose concern it is. (Reuse of the role *taxonomy*, applied to asking rather than reviewing, is validated in design.) | Should |
| **ADV-11** | The question/capability catalog is a **curated, human-refreshed** artifact (a curated catalog bump, **not** a live external lookup — that would cross document-driven / governs-not-runtime). It has a **named owner** and a **periodic refresh cadence** (independent of change events, so it cannot go stale indefinitely); additionally a Tier-3 agentic change prompts an **"is the catalog current?"** review step, and a stale-catalog finding is **recorded and surfaced** (not silently ignored). | Should |
| **ADV-12** | The floor recommendation is **auditable and non-silently-droppable.** It is deterministic for a given scenario (ADV-5). A team may **skip** a recommended-mandatory control, but the Advisor **records the skip** as `skips: [{control, owner, reason}]` and surfaces it in the handoff — never silent. **The skip is an Advisor record, not a #10 waiver**: it grants **no** exception at the gate (round-9 M3). The word **"waiver" is reserved for a human-authored downstream exception in #10** (`manifest-waivers.yaml`, tied to an actual blocker, tier + revisit) — the Advisor never authors a waiver. So "can't be skipped silently" holds by *recording* (here), and "hard-blocked until … or waived" holds *at #10* when a human later waives a real blocker. | Must |
| **ADV-13** | **Surface selection is external to the intake and non-circular** (round-9 m1): `pm-design-feature`'s existing "delivery surface?" step is the **`agentic` gate**; only if agentic does a **two-question topology probe** run (component count; any inter-component edge); **≥2 components and ≥1 edge → compound → invoke `hitl:agentic-intake`**, else the single-agent path. The intake is reached **only on the compound branch and does not re-select the surface** — it elicits the full detail. The gate→probe→route rule lives in **`pm-design-feature`** and **`ai/codex/AGENTS.md`**. *(Absorbed from #10 CR-1; round-4 B2 / round-5 M1.)* | Must |
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

1. A PM **with no agentic-systems expertise** runs **one intake** and comes out with a right-sized
   **recommendation report**, a stated recommended floor, a **decision record**, and a neutral
   **`agentic-design-handoff.yaml`** (components + connections + `proposed_kind`s + recommendation IDs +
   target-path hints) — without a specialist, and **without the PM having authored any design** (not even a
   `kind:` field).
2. A **low-stakes** two-agent read-only flow yields a **short report**; saga, deep-memory, and reliability
   lenses are **not** recommended. **Observability is recommended** (2026-07-22 directive) at **minimal
   depth** — a basic trace + a simple PM eval-console. *(The Advisor recommends; #10 enforces on the authored
   manifest.)*
3. A **high-stakes** irreversible-action flow yields the **full report**, and its recommended floor
   (classify + human gate + idempotency + detectability + kill-switch) **cannot be dropped silently** — a
   **skip** is recorded with owner/reason (ADV-12), which grants **no** #10 exception; the hard block happens
   downstream in #10 at design time (and only a **human-authored #10 waiver** relieves it).
4. **Every recommendation** is recorded with a rationale and is overridable (ADV-6/ADV-9).
5. The output is a **recommendation + handoff, not a design**: the decision record + `agentic-design-handoff.yaml`
   contain **no `system-manifest.yaml` field value** (no `kind`, no authored legs) — only `proposed_*`
   recommendations + target-path hints (ADV-8/B2). Verified: the Advisor writes no manifest field; the human
   authors the manifest and **#10 validates it** — #10 needs no input from the Advisor.
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
  is now **derived from #10's imported activation predicates** (floor ≡ activation, `OWNERSHIP-COMPLETE` lint; ADV-5/12,
  B1); **Tier scales depth, not membership**; the canonical state is a **machine-readable YAML** holding the
  authored outputs, with the Markdown decision record generated from it (B4); the catalog `consequence` is
  reconciled to one option→list-of-tagged-unions shape (B4); routing gets an **`agentic` gate** before the
  probe and a single selector (M1, ADR-A9 rewritten); `agentic-deploy` composes only when
  greenfield/platform-change/durable/requested (M6). Exact `COMPOSE-LOW`/`COMPOSE-HIGH` fixtures replace the
  impossible ones (B2). #10-side (compound package): result-review + saga `parallel` + multi-owner baseline
  removed from core (→#42), observability gate made real + tier-scaled (M3), release re-scoped so core = 2.2.0
  (M4). Tracker bodies #12/#13/#15/#38/#41 rewritten (M7).
- **round-8 review + re-scope (2026-07-23):** the round-8 cold review found the executable spike's PASS was
  an artifact of a weakened validator (7 malformed manifests passed) — the auto-authoring seam could only be
  validated by the real validator+schema. An independent strategic evaluation, and the product owner, then
  named the root cause: **auto-authoring the manifest crossed the line HITL exists to hold — it let the PM
  front door produce design/implementation artifacts** (and made the gate audit HITL's own output).
  **Resolution (this revision, v4): the Advisor is re-scoped to `elicit + recommend + record + hand off`.**
  Removed: the canonical-state *writer*, `floor ≡ activation` and the imported-activation apparatus,
  `OWNS_CHECKS`/`OWNERSHIP-COMPLETE`/`AUTHOR-COMPLETE`, the manifest-field authoring (ADV-8), and the seam
  spike's authoring claim. The floor is again a **Tier + risk recommendation** (ADV-5), not a mirror of #10;
  the commands **recommend + record**, they do not author (ADV-1/4); the output is a **decision record + a
  manifest skeleton handoff** (ADV-8); a human authors the design and **#10 validates** it (#10 unchanged,
  can ship first). This converges because the entire failing surface existed only to serve auto-authoring.
- **round-9 confirmation review (2026-07-23):** REVISIONS REQUIRED, but the executive conclusion confirmed
  **the re-scope is sound** — findings were "finish applying it," not "the approach is wrong." Fixes in
  **v4.1**: (B2) the handoff is now a **neutral `agentic-design-handoff.yaml`** carrying `proposed_kind`s +
  recommendation IDs + target-path hints — **not** a manifest skeleton (a `kind:` field is a design value;
  ADV-8); (M9) the 8 per-concern commands **collapse to one intake + a recommendation report** — lenses are
  report sections, not separate commands (ADV-1/3/4); (M2) the floor claim is made **honest** — membership
  uses the safety-relevant factors, Tier/data/stakes/scale inform depth (ADV-5, no depth engine — the
  proportionate fix is subtraction); (M3) **skip ≠ waiver** — the Advisor records a `skip` (no #10
  exception); "waiver" is reserved for a human-authored #10 exception (ADV-12); (m1) routing gate→probe→route
  is external, the intake doesn't re-select (ADV-13). Cascades to HLD (remove the §9 worked-example authoring
  + §11 acceptance + §4.2 `manifest_field`), LLD (one-intake model, neutral handoff schema, composer path
  fix), and #10 (remove Advisor-import/writer refs from its LLD so it ships first). The re-scope itself is
  retained and confirmed.
