# Agentic Design Advisor: Design (HLD) — v3

> Mechanism (the *how*) for [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). Decisions in [`02-adrs.md`](02-adrs.md); **field-level precision (catalog schema,
> composer, floor function, command→manifest mapping, integration) in the LLD [`04-lld.md`](04-lld.md)**;
> test plan in [`03-test-plan.md`](03-test-plan.md).
> Status: **draft, pending review**. **v3** — reshaped around **runnable commands + a composed workflow**
> (v2), then revised after two rounds of pm + architect review (ADV-13 integration, floor waiver, honest
> kill-switch/observability targets, complete composition/consequence tables). The Advisor is the **front
> door** to the compound-agentic surface ([#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10)):
> it elicits the whole scenario and composes a right-sized workflow of commands; the commands produce the
> manifest #10 then validates.

## 1. Thesis

**Encode the expert's questions as a thorough intake, then let HITL compose a right-sized workflow of
runnable commands.** There is no engine to build and no monolith: the Advisor is a set of `hitl:agentic-*`
commands (each runnable on its own), an intake that understands the whole scenario, and a **composition
step** that decides which commands this change needs. Each command produces real manifest/design
artifacts, and #10's *existing* per-check activation reacts to that manifest content — so the Advisor
**configures by producing the right manifest, it does not feed #10 a validator list** (this is the v1
fiction the architect review caught, now removed).

## 2. The command set (ADV-1)

Each expert concern is one runnable command. The intake runs first; HITL composes which of the rest apply.

| Command | Concern (lens) | Produces |
|---|---|---|
| `hitl:agentic-intake` | understand the whole scenario; **compose the workflow** (§4) | the scenario record + the composed workflow |
| `hitl:agentic-classify` | component right-sizing (agent vs deterministic; simple vs deep) | domain `kind`s + `kind_rationale` |
| `hitl:agentic-boundary` | the determinism boundary | trust-leg obligations on interactions |
| `hitl:agentic-privilege` | privilege / identity / trust (lethal-trifecta); **portability** (providers bound as capabilities, not embedded) | agent `uses`/`identity` declarations |
| `hitl:agentic-reliability` | reliability, idempotency, failure modes | manifest `async`/idempotency fields (#10) **+ a declared kill-switch artifact** † |
| `hitl:agentic-observability` | detectability — how misbehavior is seen in prod | **a declared observability artifact** (tracing/eval plan) † — #10 validator arrives with #15 (CR-9) |
| `hitl:agentic-memory` | memory / state, PII / data classification | memory declarations + pii policy |
| `hitl:agentic-evals` | evaluation (incl. model/prompt-version drift) | eval coverage + specs |
| `hitl:agentic-deploy` | build-vs-buy deployment | the **recorded** deployment decision (§8) |

**† Two outputs have no #10 manifest target today (ADV-8, ADR-A5):** the **kill-switch** and all of
**`agentic-observability`** produce **declared design artifacts** in the decision record (recorded,
human-reviewed), *not* manifest fields #10 validates. Observability's #10 check lands with **#15** (#10's
CR-9 is deferred there). This is stated honestly rather than claimed as a manifest→#10 mapping that
doesn't exist. **Cost / amplification** (a lens, ADV-2) is not a separate command — it is carried by
`agentic-boundary` as the leg-level `cost_bound` on interactions into an agent.

Every command is **independently runnable** (ADV-1): a team can run `hitl:agentic-privilege` alone against
an existing design. The **intake elicits** the whole scenario; the **per-concern commands own each lens's
decision and consequence** (the two-tier split, ADV-1) — the intake is not the monolith, it is the
elicitor that hands off to the composed commands.

## 3. The intake (ADV-2) — understand the whole scenario

`hitl:agentic-intake` is as thorough as HITL's deterministic design intake (`pm-design-feature`): it walks
every lens (§2 column 2, plus stakes/tier/compliance and cost) asking the questions a seasoned
agentic-systems expert asks, so nothing critical is missed. It is **role-aware** (ADV-10), attributing
each lens to its owning role from `docs/playbook/roles.md` (PM / Technical Advisor / Architect / Developer
/ QA / Ops), and it **records** the answers as the scenario record. It asks in plain language and
interprets free-text answers into the catalog's options; the harness runs the conversation, HITL supplies
the questions and the option menus (the catalog, ADR-A2).

### 3.1 Surface selection & integration (ADV-13) — how the intake hooks into the existing flow

The Advisor **does not replace** HITL's existing design intake; it is the **compound-agentic branch of
it**. Concretely (ADR-A9):

- **`pm-design-feature`** already asks "what is the delivery surface?" (web / mobile / API / agentic / …).
  A branch is added: once the elicited system has **≥2 components and ≥1 inter-component edge**, that step
  **hands off to `hitl:agentic-intake`** instead of the single-agent path. For a single-component product,
  nothing changes — it stays on the existing single-agent surface. So the Advisor **precedes** the design
  track for compound systems and is skipped for simple ones; it never gates or replaces the deterministic
  flow.
- **`ai/codex/AGENTS.md`** gains a **routing rule** so the Codex/agent design path recognizes the compound
  surface (the same ≥2-components-and-≥1-edge trigger) and follows the composed workflow rather than the
  single-agent template.
- The trigger is evaluated **from the intake's own component/edge count** — no new detector; the intake
  already elicits the component list (§3). The handoff writes the composed workflow (§4) and the scenario
  record, which the design track then consumes.

This is the architectural sequencing the round-2 review flagged as missing: *precede for compound, skip
for simple, never replace the existing intake.*

## 4. Composition (ADV-3) — HITL figures out the workflow

After the intake understands the requirements, HITL **composes the workflow**: the ordered set of
`hitl:agentic-*` commands this change needs. Composition is deterministic given the answers:

1. **Relevance.** A command is included only if the scenario has data for its lens — no side effects ⇒ no
   reliability/saga command; single component ⇒ no boundary/topology command. (This is the proportionality
   mechanism; a lens with no data contributes no command.)
2. **Floor vs rung (§5).** Each included command is marked **mandatory** (in the floor) or **offered**
   (a deferrable rung).
3. **Order.** Commands are ordered by dependency (classify → boundary/privilege → reliability/observability
   → evals → deploy), so each runs against the artifacts the prior ones produced.

The composed workflow is written to the decision record and is what the team runs. A re-run with the same
answers composes the identical workflow (auditable, ADV-12).

### 4.1 Relevance predicates — all commands (not just examples)

A command is composed **iff** its relevance predicate holds (the same shape as #10's per-check activation
table). The full set:

| Command | Composed when (relevance) |
|---|---|
| `agentic-classify` | always (a compound system was selected — ≥2 components) |
| `agentic-boundary` | any interaction crosses an agent↔deterministic or agent↔external seam |
| `agentic-privilege` | any component is an agent (it holds capabilities/identity) |
| `agentic-reliability` | `side_effects ≠ none`, **or** any interaction is `async_task`/`event`, **or** `autonomy ∈ {supervised, autonomous}` (kill-switch) |
| `agentic-observability` | `stakes ∈ {customer_facing, regulated}` **or** `autonomy == autonomous` |
| `agentic-memory` | any agent declares memory/state, **or** `data ∈ {sensitive, pii}` |
| `agentic-evals` | any component is an agent (quality is unprovable without evals) |
| `agentic-deploy` | always for a compound system (a build-vs-buy call is always made) |

Composed ≠ mandatory: whether a composed command is **floor** (mandatory) or **rung** (offered) is the §5
rule. A command whose relevance predicate is false is not composed at all (proportionality).

### 4.2 The catalog `consequence` — a tagged union (ADR-A2)

Each catalog entry's `consequence` is a **tagged union** (one `kind`), so `test_catalog_lint.py` can
validate it and the composer can act on it:

```yaml
consequence:
  kind: enum[ classify | boundary | gate | command | floor | manifest_field | declared_artifact ]
  # kind: command          → composes a hitl:agentic-* command (name)
  # kind: floor            → adds/removes a floor entry (with the §5 rule ref)
  # kind: manifest_field   → authors a specific #10 manifest field (path)
  # kind: declared_artifact → records a design artifact with no #10 target (kill-switch, observability §2 †)
  # kind: gate|boundary|classify → the specific design obligation
  target: string           # command name | manifest path | artifact id | floor-rule id
  note: string
```

A lint (`CAT-CONSEQUENCE`) rejects an entry with no `consequence`; `CAT-COMMANDS`/`CAT-ACTIVATES` check
that a `command`/`manifest_field` target actually resolves (a real command, a real #10 field).

## 5. Floor and ladder (ADV-5/ADV-12) — reuse Tier, offer the rungs

The floor is a **deterministic function of the existing HITL Tier (0–3) plus agentic risk factors** — it
does **not** introduce a competing scale (the architect review's orthogonal-machinery catch). The risk
factors have an enumerated vocabulary so the floor is reproducible:

```
stakes        ∈ {internal, customer_facing, regulated}
side_effects  ∈ {none, reversible, irreversible}
data          ∈ {none, sensitive, pii}
autonomy      ∈ {assisted, supervised, autonomous}
scale         ∈ {small, large}
```

**Floor rule (deterministic):** `floor = the set of mandatory commands`, where a command is mandatory iff
its rule fires. The rules (worked in the LLD) are monotone in Tier and risk, e.g.:

| Mandatory command | Fires when |
|---|---|
| `agentic-classify` | always, once composed (≥1 agent) |
| `agentic-boundary` | any interaction crosses an agent↔deterministic (or external) seam |
| `agentic-privilege` | Tier ≥ 2, **or** `data ∈ {sensitive, pii}`, **or** the lethal-trifecta pattern is present |
| human gate (via `agentic-reliability`) | `side_effects == irreversible` |
| kill-switch (via `agentic-reliability`) | `autonomy ∈ {supervised, autonomous}` and `side_effects ≠ none` |
| `agentic-observability` | Tier ≥ 2, **or** `autonomy == autonomous` |
| `agentic-evals` | Tier ≥ 2 and `stakes ∈ {customer_facing, regulated}` |

**Precedence:** if several rules apply, the command is mandatory (union, not override) — so the floor is
the *highest* obligation across all matching conditions; there is no ambiguity. Commands not in the floor
but relevant are **offered as rungs** ("add now, or defer and record as waived").

**Floor enforcement — non-silently-droppable, but waivable (ADV-12, ADR-A6).** A floor command **cannot be
dropped silently**; below the floor **without a waiver** is a blocker. But — consistent with HITL's own
hard-gate precedent (PRD FR-25: "hard-blocked until … *or waived*") and with "humans decide" (ADV-9) — a
floor command **can** be dropped via an **explicit, tier-appropriate waiver** recorded in the decision
record (owner, reason, tier-limit, revisit), the same waiver shape HITL already uses. The floor is the
teeth (no accidental under-governance); the waiver is the human escape hatch (auditable, never silent).
The `kill-switch` and observability floor entries are satisfied by their **declared artifacts** (§2 †),
human-reviewed, since they have no #10 check today.

**Determinism, honestly (ADV-12).** The floor is a deterministic function of the *declared* risk factors,
so the *computation* is reproducible. It does **not** claim two people describe the same scenario
identically — the risk-factor vocabulary (§5, above) is categorical to minimize that variance, but
elicitation consistency is a softer property than computation determinism, and the requirement is scoped to
the latter.

## 6. Recommendation + decision record (ADV-6/ADV-7/ADV-9)

Inside a command, a material choice (component kind, orchestration pattern, memory strategy, protocol) is a
menu: the Advisor recommends the **simplest option that fits** (bias to simplicity — the counter to the
AI's over-engineering instinct), shows rejected options **with their cost**, and records chosen + rejected.
It never applies a choice silently; the human confirms, and an override is recorded with its reason.
(**Build-vs-buy is not one of these generic menus** — it is owned exclusively by `agentic-deploy`, §8.)

The **decision record** (`docs/01-product/<feature>/agentic-decisions.md`, ADR-style) holds the scenario,
the composed workflow, the floor, and every recommendation + chosen/rejected. It is regenerated (not
appended) on a re-run, so it never drifts from the answers.

## 7. What the commands produce (ADV-8) — no seed fiction

Each command writes **real manifest fields and design artifacts** (the table in §2). #10's compound-agentic
validators then activate **from the manifest content that is present** — its existing per-check activation,
unchanged. There is **no** "active-validator set" passed to #10, and **no change to #10 is required**: if
`agentic-classify` writes `kind: simple_agent` and `agentic-boundary` writes the trust legs, then #10's
`check_boundary_legs`/`check_capabilities` fire because that data is there. The Advisor *configures by
authoring the manifest*, which is exactly the "additive, no double-source" property ADR-A5 claims —
now demonstrated against #10's real activation model rather than an invented seam.

**The honest exception (ADR-A5).** Not every command authors a #10-validated field. Two obligations have
**no #10 target today** and instead produce **declared design artifacts** (recorded, human-reviewed): the
**kill-switch** (from `agentic-reliability`) — there is no `kill_switch` field or check in #10's schema —
and **`agentic-observability`** — #10's CR-9 is deferred to **#15**, so its validator doesn't exist yet.
These are stated as declared artifacts, not as a manifest→#10 mapping that doesn't hold; when #15 lands,
observability's artifact gains a real #10 check. Making them mandatory-floor is still sound — the control
is real and human-reviewed — it just isn't machine-validated by #10 until its target exists.

## 8. Deployment (ADV-14, ADR-A7) — record, human-carries

`hitl:agentic-deploy` elicits the build-vs-buy drivers, presents the menu (from-scratch / managed platform
/ self-hosted OSS, implementations named only as examples), recommends **managed unless there is a specific
reason to build**, and **records** the decision in the decision record. When it recommends **managed**, it
**surfaces the lock-in trade-off** — the industry's platforms (AgentCore / Foundry / Gemini) integrate
identity, telemetry, and state vertically, so "buy" is convenient but sticky — and makes the team answer
the **three portability-diligence questions**: **governance** (neutral foundation vs vendor-owned control),
**packaging** (same agent artifact on another cloud without a rewrite), **state** (can the memory/state be
exported). This turns the managed default from a reflex into an eyes-open choice. It then **prompts a human
to carry the decision into HITL's platform/ops track** (FR-25 platform-bootstrap). There is **no automated
handoff** and **no provisioning** — the platform-bootstrap feature is not modified by this package (the
architect review confirmed it has no intake for a deployment direction; inventing one was the v1 error).

## 9. A worked example — building an agentic solution with HITL

*Illustrative and domain-neutral (a generic customer-support assistant, not any specific product).* This
shows what "using HITL to build an agentic solution" actually looks like.

### 9.1 The system

A team wants a support assistant: a request comes in, gets classified, the customer's account is looked up,
a resolution is drafted, and — for some cases — a **refund is issued**. Four components:

| Component | Kind (proposed) | Notes |
|---|---|---|
| `intake_agent` | simple agent | classifies the request, extracts intent |
| `account_service` | deterministic | looks up the account/order (system of record) |
| `resolution_agent` | simple agent | drafts a resolution; may **propose a refund** |
| `refund_service` | deterministic | executes an approved refund via a payment API (**irreversible**) |

### 9.2 Run `hitl:agentic-intake`

The team runs one command. It asks across the lenses; the answers that matter:

- **Components:** 4, two of them agents → **≥2 components + ≥1 edge**, so the intake **selects the
  compound-agentic surface** (ADV-13) and routes in.
- **Right-sizing:** are the agents *deep*? No — bounded classify/draft tasks → **simple agents**. Do you
  need multi-agent at all? Yes, two distinct jobs. (The intake actively pushes back on over-engineering
  here.)
- **Side effects:** issuing a refund is **irreversible**.
- **Data:** account data is **PII**.
- **Autonomy:** the resolution agent proposes; a human approves refunds → **supervised**.
- **Stakes:** customer-facing + money → **Tier 2**.
- **Scale:** moderate, **small**.

### 9.3 HITL composes the workflow

From those answers (Tier 2, irreversible, PII, supervised, small), composition produces:

```
FLOOR (mandatory):
  agentic-classify        (≥1 agent)
  agentic-boundary        (resolution_agent → refund_service crosses the seam; intake_agent → account_service)
  agentic-privilege       (Tier 2 + PII)
  agentic-reliability      → human gate (irreversible) + kill-switch (supervised + side effects)
  agentic-observability   (Tier 2)
  agentic-evals           (Tier 2 + customer-facing)
OFFERED (rungs, deferrable):
  agentic-memory          (only if you want cross-session context — team defers it, recorded as waived)
NOT INCLUDED (no data for the lens):
  saga/compensation       (irreversible ≠ compensable — you gate, you don't compensate)
  async reliability       (the flow is synchronous)
  deep-agent machinery    (no deep agents)
  agentic-deploy? → INCLUDED (every compound build makes a build-vs-buy call)
```

The team sees a **six-command floor + one offered rung**, and — crucially — **never sees** the saga,
async, or deep-agent machinery, because their system doesn't need it. That is the proportionality working.

### 9.4 The team runs the composed commands

- **`agentic-classify`** → writes `kind: simple_agent` on the two agents, `deterministic` on the two
  services, with `kind_rationale` ("bounded task, no long-horizon planning").
- **`agentic-boundary`** → marks `resolution_agent → refund_service`: the proposed refund (agent output)
  must be **validated** (amount within policy, matches the looked-up order) before the deterministic
  `refund_service` trusts it; and `intake_agent`'s classification is validated before `account_service`
  queries on it.
- **`agentic-privilege`** → `resolution_agent` may **read** account data and **propose**, nothing more;
  `refund_service` may call the payment API. The command flags that giving `resolution_agent` direct
  payment access would be over-privilege → declined.
- **`agentic-reliability`** → a **human gate** before any refund (`lifecycle.human_gate`, a #10 field) and
  an **idempotency key** (a #10 `async`/lifecycle field); plus a **kill-switch** — a **declared artifact**
  (a flag that disables auto-resolution fleet-wide), human-reviewed, since #10 has no kill-switch field
  (§7 exception).
- **`agentic-observability`** → records a **declared observability artifact** (tracing across the four
  hops + an **eval on proposed refund amounts** so a hallucinated amount is caught). This is a *design
  artifact today* — #10's observability check (CR-9) lands with #15; until then it is human-reviewed, not
  machine-validated (§7 exception).
- **`agentic-evals`** → seeds baseline evals for each agent and the end-to-end flow, for the PM to own.
- **`agentic-deploy`** → drivers say small scale, customer-facing, no data-residency constraint →
  **recommends a managed agent platform** (from-scratch listed as rejected, "you'd rebuild orchestration,
  state, and retries for no reason"). It then surfaces the **lock-in trade-off** and makes the team answer:
  governance (the platform is vendor-owned — accepted), packaging (the agent is packaged portably, not
  cloud-locked — required), and state (the refund/session memory must be **exportable** — recorded as a
  requirement on the chosen platform). **Records** the decision, and a human carries "managed platform,
  with exportable state" to the platform/ops track.

### 9.5 What #10 and the human do next

The commands have authored the manifest (`kind`s, `interactions`, trust legs, `uses`, lifecycle gate,
evals). On the next `derive.py verify`, **#10's per-check activation runs** (checked against #10 LLD §6.0):
`check_classification`, `check_topology` + `check_references` (any `interactions` present),
`check_authorization` (interactions target agents), `check_boundary_legs`, `check_capabilities`,
`check_lifecycle` (the gate), `check_eval_coverage` — and **skips** `check_saga`, `check_async`,
`check_deep_agent`, because there's no data for them. There is **no** `check_observability` and no
kill-switch check — those two obligations are the **declared artifacts** of §7, not #10 fields (yet). No
#10 change, no seed. The human carries the deployment decision onward. The result is a **right-sized,
governed design** the team can hand to the compound-agentic build track.

### 9.6 Contrast — a trivial case

A single agent that summarizes public docs for an internal tool: the intake finds **1 component, no side
effects, no PII, internal** → composition includes only `agentic-classify` and **offers** a light
`agentic-evals`; the floor is essentially "declare it." The team barely feels HITL. Same commands, same
Advisor — a completely different weight, set by the scenario, not by ceremony.

### 9.7 How the map renders (ADV-15) — terminal-first, three renderings, one source

The **evolving system map** (§9.2–9.4 shows it filling in) is a **generated view** — the same category as
HITL's command-map/posture views, regenerated from the accumulating scenario record **at each meaningful
step** (a component named/typed, a boundary drawn, a gate added, the deploy decision made). As agents are
added one at a time, the map grows one node/annotation at a time. Because HITL is used mostly in the
**terminal**, the map is terminal-first and renders three ways from one data source:

1. **Terminal-native inline** — a compact box-drawing map re-printed at each milestone (the live view, **no
   browser**), e.g.:
   ```
   support assistant · compound-agentic surface
     intake_agent ─▶ account_service ─▶ resolution_agent ──⛊──▶ refund_service
       agent          service · PII        agent           gate    service · irreversible
     boundary ✓✓   privilege ⚿⚿   kill-switch ⏻
     getting: classify · boundary · gate · privilege · detectability · evals · deploy
     not needed: sagas (irreversible→gate) · async (sync) · deep memory (no long-horizon)
   ```
2. **Markdown + Mermaid** — the same map + the getting/available/not-needed table written into the decision
   record (`agentic-decisions.md`), previewable in the IDE / on GitHub, **auto-updating on file change** (no
   browser).
3. **Optional rich interactive HTML** — for the web surface, a shareable link, or the portal (the prototype
   at `2e888cca-…` demonstrates it). A bonus rendering, never the baseline. **"Portal" means static-file
   publishing** (a generated HTML file served as a static page, like the existing portal) — *not* a hosted
   rendering service, which would cross governs-not-runtime.

**Combined "chat + live map" mode (artifact-capable surfaces).** On a Claude Code surface with an artifact
panel (web/desktop), rendering (3) becomes the *live* view: the intake **re-publishes the map artifact after
each meaningful step to the same URL**, so the discussion (the chat) and the evolving map (the side panel)
sit together and update as the user answers. This is the natural home for "picture the system as you
discuss it." **Two constraints keep it in-lane:** (a) the artifact is a **live view, not an input** — it is
sandboxed and cannot post answers back, so the *conversation* stays the input and the map is the evolving
*output*; a two-way "fill the form and it builds the design" web app would cross into runtime and is out of
scope. (b) It is the **rich tier only** — a bare CLI or air-gapped setup still gets the terminal-text map
(rendering 1). The demo at `efd56c28-…` shows the loop on the Cerrtus flow.

**Node-type visual vocabulary.** Every rendering uses one consistent visual language so a component's kind
reads at a glance: **agent** (hexagon / green), **deterministic service** (chip / steel), **datastore**
(cylinder / teal), **external actor** (cloud / dashed), **output store** (stacked layers), plus a
**message/email** edge (dashed + ✉) and a **human gate** marker (⛊). The terminal rendering uses ASCII
equivalents of the same vocabulary. LLD §6 specifies the icon set and the ASCII map.

**Boundary (governs-not-runtime):** HITL **writes the files and prints the text**; it does **not** run a
live-reload server. Live browser refresh is the user's IDE/tooling (the IDE Mermaid preview updates on file
change for free); the terminal inline map, the regenerated file, and (on capable surfaces) the re-published
artifact are what HITL provides. Regenerate is deterministic from the scenario record, so the map never
drifts from the design.

## 10. Decisions (locked as ADRs)

| # | Decision |
|---|---|
| A1 | The Advisor is a **set of harness-run commands**, not a separate app and not a monolith |
| A2 | The question/option **catalog is curated, versioned data** (question→consequence), curated-refresh not live lookup |
| A3 | **Recommend, never decide** — output is a proposal + decision record the human confirms |
| A4 | **HITL composes a proportionate workflow** from the intake — ask/run only what's relevant; depth follows risk |
| A5 | The commands **author the manifest**; #10's existing per-check activation reacts — configure, don't feed a validator list, don't duplicate |
| A6 | The **floor is a deterministic function of Tier + risk**; the ladder offers deferrable rungs (no new axis) |
| A7 | The Advisor **records the build-vs-buy decision; a human carries it** to the platform track — provisions nothing, auto-hands-off to nothing |
| A8 | The **evolving map is a generated view, terminal-first** — inline text (no browser) + Markdown/Mermaid in the decision record + optional HTML; regenerated per step; HITL writes/prints, runs no live server |
| A9 | The intake **integrates into `pm-design-feature`/`AGENTS.md`** — precedes the design track for compound systems (≥2 components + ≥1 edge), skipped for simple ones; never gates or replaces the existing intake |

## 11. Acceptance criteria (implementation gate)

1. The intake composes a workflow that is **short for a low-risk change** (example §9.6) and **full for a
   high-risk one** (§9.3); saga/async/deep-agent commands appear only when their data is present.
2. The floor **computation is deterministic** given declared factors (§5); a floor command **cannot be
   dropped silently** — dropping one requires a **recorded, tier-appropriate waiver** (ADV-12/ADR-A6).
3. Each command **authors manifest fields** such that #10's *unmodified* per-check activation runs the
   relevant validators — verified on a low- and a high-risk fixture (ADV-8), with no change to #10; the
   **kill-switch and observability declared artifacts** are recorded (no #10 target yet), not silently
   omitted (§7).
4. Every menu decision emits a recommendation + rationale + recorded chosen/rejected; an override is
   recorded (ADV-6/ADV-9); build-vs-buy is owned by `agentic-deploy` alone (not the generic menu).
5. `agentic-deploy` recommends managed for a low-stakes small-scale flow, requires a reason to override to
   build, surfaces the **lock-in / portability diligence**, records the decision, and prompts a human
   handoff — provisioning nothing (ADV-14/ADR-A7).
6. The decision record (scenario + composed workflow + decisions) is durable and regenerates on a re-run.
7. **`pm-design-feature`/`AGENTS.md` route a compound system (≥2 components + ≥1 edge) into the intake**,
   and leave a single-component product on the existing single-agent surface (ADV-13/ADR-A9).

## 12. Standards alignment (rationale)

*(Moved here from requirements per the WHAT/HOW taxonomy — this is design rationale, not a requirement.)*

The industry's enterprise agent platforms (Amazon Bedrock AgentCore, Microsoft Foundry Agent Service,
Google Gemini Enterprise Agent Platform) have converged on the same runtime layers — **runtime, memory,
tool gateway, identity, observability, governance**. The Advisor's lenses map onto them at the *design/
governance* layer (memory, privilege/identity, observability, deployment), and its "questions an expert
asks" match the operational questions those platforms are built to answer (task completion, tool choice,
authority, cost, quality-after-model-update). HITL's manifest is the **design-time analog of the portable,
framework-agnostic agent contract** the industry still lacks at the runtime layer — declare what the agent
needs (model, memory, tools, permissions, evals) and stay provider-agnostic. This is a **validation of
direction, not a mandate to ship a runtime**: the Advisor governs the *choice* of those layers (esp.
build-vs-buy, ADV-14) and never ships them. Named alignments: the observability lens targets
**OpenTelemetry** GenAI conventions; the portability facet applies the **Twelve-Factor** "attached
resources" principle; neutral governance is tracked by the **Linux Foundation Agentic AI Foundation** (MCP
/ AGENTS.md / A2A). Source: requirements §11 References.
