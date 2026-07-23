# Agentic Design Advisor: Design (HLD) — v3.3 (round-7: floor from #10 activation)

> Mechanism (the *how*) for [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). Decisions in [`02-adrs.md`](02-adrs.md); **field-level precision (catalog schema,
> composer, floor function, command→manifest mapping, integration) in the LLD [`04-lld.md`](04-lld.md)**;
> test plan in [`03-test-plan.md`](03-test-plan.md).
> Status: **draft, core-lock applied, pending Codex re-review (round 7)**. **v3.2** — reshaped around
> **runnable commands + a composed workflow** (v2), revised after pm + architect rounds (v3), then
> **core-scope-locked** after the round-4 objectives review ([`../agentic-core-scope.md`](../agentic-core-scope.md)):
> **non-circular topology-probe routing** (B2, §3.1); **obligation-first floor** so `floor ⊆ composed` (B3,
> §5); **map trimmed to terminal+Mermaid core**, HTML/live-combined deferred (M8, §9.7); the
> **contract-authoring seam** (`facade_apis`+`authorization`) named (B1, §7). The Advisor is the **front
> door** to the compound-agentic surface ([#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10)):
> it elicits the whole scenario and composes a right-sized workflow of commands; the commands produce the
> manifest #10 then validates.

> **RE-SCOPED 2026-07-23 (v4) — elicit + recommend + record + hand off.** The Advisor stays in the
> PM/elicitation lane: it does **not** author the manifest. Round 8 showed the auto-authoring seam could
> only be validated by the real validator; the deeper problem is that auto-authoring put the PM front door
> into design/implementation — the line HITL must hold. **Removed:** the canonical-state writer, `floor ≡
> activation` + imported-activation, `OWNS_CHECKS`/`OWNERSHIP-COMPLETE`/`AUTHOR-COMPLETE`, and the
> command→manifest-field authoring. Sections below that describe those mechanisms are **superseded**; the
> load-bearing sections (§1, §2, §4, §5, §7) are rewritten to the new model. A human authors the manifest;
> #10 validates it (unchanged, ships independently).

## 1. Thesis

**Encode the expert's questions as a thorough intake, right-size the workflow, recommend the controls,
record the decisions, and hand off to design.** There is no engine, no monolith, and — deliberately — **no
manifest authoring**: the Advisor is a set of `hitl:agentic-*` commands (each runnable on its own), an
intake that understands the whole scenario, a **composition step** that recommends which lenses this change
needs, and a **handoff** (a decision record + a manifest *skeleton* with TODOs). A **human** authors the
real manifest in the design phase; **#10 validates** it. The Advisor produces requirements-level outputs and
a handoff — never the design artifact itself. That boundary is the point: HITL must not let a PM front door
produce design/implementation.

## 2. The command set (ADV-1)

Each expert concern is one runnable command. The intake runs first; HITL composes which of the rest apply.

Each command **elicits + recommends + records** for its lens. The **Produces** column is a **decision-record
entry + a note in the manifest skeleton** — a recommendation the human authors into the manifest in design.
No command authors a validated manifest field (re-scope 2026-07-23).

| Command | Concern (lens) | Recommends + records (→ decision record + skeleton note) |
|---|---|---|
| `hitl:agentic-intake` | understand the whole scenario; **compose the recommended workflow** (§4) | the scenario record + the recommended workflow + the design handoff |
| `hitl:agentic-classify` | component right-sizing (agent vs deterministic; simple vs deep) | a recommended `kind` + rationale per component |
| `hitl:agentic-boundary` | the determinism boundary + the inter-component contract | the recommended trust-leg controls + which facades/authorizations the design must declare (skeleton TODOs) |
| `hitl:agentic-privilege` | privilege / identity / trust (lethal-trifecta); **portability** | the recommended capability/identity bounds for each agent |
| `hitl:agentic-reliability` | reliability, idempotency, failure modes | recommended async/idempotency controls **+ a recommended kill-switch** |
| `hitl:agentic-observability` | detectability; the **PM eval console** | a recommended observability/tracing plan + PM eval-console (which #10's `check_observability` will enforce on the authored manifest — hard directive) |
| `hitl:agentic-memory` | memory / state, PII / data classification | recommended memory/PII controls |
| `hitl:agentic-evals` | evaluation (incl. model/prompt-version drift) | recommended eval coverage (per-agent + e2e) |
| `hitl:agentic-deploy` | build-vs-buy deployment | the **recorded** deployment decision (§8), human-carried |

Every command is **independently runnable** (ADV-1): a team can run `hitl:agentic-privilege` alone against an
existing design to get a privilege *recommendation*. The **intake elicits** the whole scenario; the
**per-concern commands recommend and record** each lens's decision (the two-tier split, ADV-1). None of them
writes a manifest field — the design role authors the manifest from the handoff, and **#10 validates it**.

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

**One selector sequence, no circularity and no misroute (round-4 B2 + round-5 M1).** `pm-design-feature`'s
existing "what is the delivery surface?" step gates the whole thing, then a cheap probe decides compound vs
single — three steps, evaluated in order, before any full intake runs:

1. **Delivery surface = `agentic`?** (the existing surface question, one of web / mobile / api / **agentic** /
   …). If **not agentic** — e.g. an ordinary web UI + API, or two deterministic services — the existing
   deterministic/single-surface flow runs **unchanged**; the topology probe does **not** fire. *(This is the
   `agentic` gate round-5 M1 found missing — a 2-component deterministic system must not route to the
   compound-agentic intake.)*
2. **Topology probe** (only when agentic) — two questions: *how many distinct components
   (services/agents/stores)?* and *does any component call, hand off to, or message another?*
3. **Route:** **≥2 components AND ≥1 inter-component edge → the compound surface** (hand off to
   `hitl:agentic-intake` for the full elicitation §3 + composition §4); a single agent → the existing
   single-agent path (a team may still run one `agentic-*` command standalone, ADV-1).

This is **the single selector**. The full `hitl:agentic-intake` does **not** re-select the surface — it only
fills in the complete component/edge detail on the compound branch (the duplicate selector Codex flagged in
the LLD is removed, §8). **`ai/codex/AGENTS.md`** gains the identical gate→probe→route rule. The handoff
writes the composed workflow (§4) and the canonical state (§7.1), which the design track consumes.

This is the architectural sequencing the round-2 review flagged as missing and the round-4 review found
still circular: *a cheap probe routes; the full intake runs only on the compound branch; the deterministic
flow is never gated or replaced.*

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

### 4.1 The floor is a RECOMMENDATION (Tier + risk); rungs are the optional extras

The workflow is `floor ∪ rungs`. **The floor is the Advisor's expert recommendation of the controls that
shouldn't be skipped for this change** — a deterministic function of the existing HITL **Tier (0–3) + risk
factors** (`side_effects`, `data`, `autonomy`, `stakes`, `scale`). It is **advice**: the Advisor recommends
and records it; the actual enforcement is **#10's own validators at design time** on the human-authored
manifest. The Advisor does **not** predict, mirror, or import #10's activation (the round-5→8 equivalence
apparatus is removed — there is no manifest to make match). Recommended-floor rules (illustrative):

| Recommended floor control | Recommended when |
|---|---|
| classify + boundary | any compound agentic system (≥2 components, ≥1 agent) |
| privilege | any agent (bound its capabilities) |
| observability + PM eval-console | any agent (hard directive; #10's `check_observability` enforces it) |
| evals (per-agent + e2e) | any agent |
| human gate | `side_effects == irreversible` |
| kill-switch | `autonomy ∈ {supervised, autonomous}` and `side_effects ≠ none` |

**Rungs (offered, deferrable):** `agentic-memory` when the scenario hints at cross-session state;
`agentic-deploy` when the change is greenfield / changes platform / adds durable runtime / is requested.
Whether a control is recommended-floor vs offered-rung is the §5 rule; Tier scales the recommended *depth*.

### 4.2 The catalog `consequence` — an option→list map of tagged unions (ADR-A2)

An entry's `consequence` is a **map keyed by answer option → a list of tagged-union items** (one `kind`
each), so different answers drive different downstream effects. The LLD (§2.3) uses this exact shape:

```yaml
consequence:                 # map[ <option-or-"*"> -> list[ item ] ]
  <option>:
    - kind: enum[ classify | boundary | gate | command | floor | manifest_field | declared_artifact ]
      # command → composes a hitl:agentic-* ; floor → a floor obligation id ; manifest_field → a #10 field path ;
      # declared_artifact → a design artifact with no #10 target (kill-switch ONLY; observability authors a manifest_field) ;
      # gate|boundary|classify → the specific design obligation
      target: string         # command name | manifest path | artifact id | floor-rule id
      note: string?
```

The lint (`CAT-SCHEMA`, LLD §2.3) rejects an entry with no `consequence`, an option without a key, or a
list item whose `command`/`manifest_field`/`floor` target does not resolve.

## 5. The recommended floor + Tier depth + rungs (ADV-5/ADV-12)

**The floor is a recommendation, not a gate.** §4.1 lists which controls the Advisor recommends as
non-skippable, from Tier + risk (expert judgment). **Tier scales the recommended depth**, not membership:
observability at Tier 0/1 = an existing approved surface or a generated report, at Tier 2+ = a fuller
console; privilege = per-class vs per-capability; evals = baseline vs extended.

**Non-silently-droppable — by recording, then gated downstream.** A team may choose to skip a
recommended-floor control, but the Advisor **records that choice** (owner + reason) and **surfaces it** — it
is never silently dropped. The Advisor is not the gate; the **hard block-or-waive happens at design time in
#10** (its validators + HITL's tier/waiver process, FR-25) on the human-authored manifest. So "can't be
skipped silently" holds by *recording* here, and "hard-blocked until … or waived" holds *downstream at #10*.
The **observability + PM eval-console** recommendation is enforced by #10's `check_observability` on the
authored manifest (hard directive); the **kill-switch** is a recommended control recorded in the decision
record (no #10 check today).

**Determinism (ADV-12).** The floor recommendation is a deterministic function of the declared risk factors,
so it is reproducible for a scenario; the categorical risk vocabulary minimizes (not eliminates) elicitation
variance.

## 6. Recommendation + decision record (ADV-6/ADV-7/ADV-9)

Inside a command, a material choice (component kind, orchestration pattern, memory strategy, protocol) is a
menu: the Advisor recommends the **simplest option that fits** (bias to simplicity — the counter to the
AI's over-engineering instinct), shows rejected options **with their cost**, and records chosen + rejected.
It never applies a choice silently; the human confirms, and an override is recorded with its reason.
(**Build-vs-buy is not one of these generic menus** — it is owned exclusively by `agentic-deploy`, §8.)

The **decision record** (`docs/01-product/<feature>/agentic-decisions.md`, ADR-style) holds the scenario,
the composed workflow, the floor, and every recommendation + chosen/rejected. It is regenerated (not
appended) on a re-run, so it never drifts from the answers.

## 7. The output — a decision record + a design handoff (ADV-7/ADV-8)

The Advisor produces **two artifacts, neither of which is the design**:

1. **The decision record** (`docs/01-product/<feature>/agentic-decisions.md`) — the scenario, the recommended
   workflow, the recommended floor + rungs, every menu decision (chosen/rejected + rationale), recorded
   skips, and the deploy decision. Regenerated from the scenario state on a re-run (never appended).
2. **The design handoff** — a **scenario summary + the recommended controls + a manifest *skeleton***: a
   structural stub listing the elicited components + edges + which controls the design must include, with
   **TODO placeholders and rationale comments** (`# TODO(design): author facade_apis for callee X`). It is
   explicitly marked *"to be authored by the design role and validated by #10."*

**A human authors the real manifest** from the handoff, in the design phase, using HITL's normal design
skills; **#10 validates** the human-authored manifest. The Advisor writes **no** validated manifest field,
runs **no** #10 validator, and requires **no** change to #10 — #10 activates purely from the *human-authored*
manifest content and can ship independently. This is the boundary the feature exists to hold: the PM front
door produces a recommendation + a handoff, not the design.

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

From those answers (Tier 2, irreversible, PII, supervised, small; a greenfield build with one async edge —
this is Fixture HIGH, test plan §4), composition produces — each floor entry justified by the #10 check it
owns activating (floor ≡ #10 activation):

```
FLOOR (mandatory — its owned #10 check will fire):
  agentic-classify        (check_classification — compound, ≥1 agent)
  agentic-boundary        (check_boundary_legs/topology/references/authorization — agent endpoints, incl. agent→agent)
  agentic-privilege       (check_capabilities — any agent)
  agentic-reliability     (check_async — the async ledger write; + human gate (irreversible) + kill-switch (supervised))
  agentic-observability   (check_observability — any agent; depth = console at Tier 2)
  agentic-evals           (check_eval_coverage — any agent + one e2e)
OFFERED (rungs — no firing #10 check):
  agentic-deploy          (greenfield build → a build-vs-buy call; recorded, human-carried)
NOT COMPOSED:
  agentic-memory          (no cross-session memory declared or hinted — not offered)
  (saga / deep-agent are #10 concerns, not Advisor commands; the flow is agent→async, handled by reliability)
```

The team sees a **six-command floor + one offered rung (deploy)**. Every floor entry is there because #10
will enforce it — nothing is a hand-tuned guess, and nothing the team could defer would then hard-fail #10.
Proportionality shows up as **depth** (Tier-2 console vs a Tier-1 report) and in what is *not* composed
(no memory), not in skipping a control #10 mandates.

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
- **`agentic-observability`** → authors the **`observability` block** — `tracing` across the four hops
  (OTel GenAI), a `cost_budget`, and a **PM eval-console** declaration (where the PM runs the refund-amount
  eval + reviews traces so a hallucinated amount is caught). #10's **`check_observability` floor-gates** it
  (hard directive) — a missing block or console **blocks**. HITL validates the declaration; the product
  builds the running console/trace backend (#21 reference).
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
`check_lifecycle` (the gate), `check_eval_coverage`, **`check_observability`** (the `observability` block
the observability command authored — the floor gate, hard directive) — and **skips** `check_saga`,
`check_async`, `check_deep_agent`, because there's no data for them. The **kill-switch** obligation is the
one remaining **declared artifact** of §7 (no #10 field yet). The human carries the deployment decision
onward. The result is a **right-sized, governed design** the team can hand to the compound-agentic build track.

### 9.6 Contrast — a lighter compound case, and the single-agent path

**A lighter compound system** (Fixture LOW, test plan §4): two agents, read-only, internal, Tier 1. The
floor is still `{classify, boundary, privilege, observability, evals}` — because a two-agent flow *does*
activate #10's classification/boundary/capability/eval/observability checks, so pretending they were
optional would just hard-fail #10 later. What makes it light is **depth**: observability is satisfied by an
existing approved surface or a generated report (not a bespoke console), privilege is per-class, evals are
baseline, and reliability/memory/deploy are absent. Proportionality is real, but it is depth-and-omission,
not skipping a control #10 enforces.

**A single agent** (one component — a doc summarizer): this is **not a compound system**, so the topology
probe (§3.1) routes it to the existing single-agent surface; the compound intake is not invoked. A team can
still run one command standalone (e.g. `agentic-privilege`) against it (ADV-1) — that is the supported
single-component path, not a near-empty compound workflow.

### 9.7 How the map renders (ADV-15) — terminal-first; two core renderings, one source

> **Core scope (round-4 M8).** The **core** map is **terminal text + Markdown/Mermaid** (renderings 1–2
> below) — that is the whole shippable Should. The **rich HTML rendering and the "chat + live map" combined
> mode** (rendering 3 + the block after it) are a **deferred enhancement** with a defined host API, not
> core; they are kept here as the design target for the follow-on. See
> [`../agentic-core-scope.md`](../agentic-core-scope.md).

The **evolving system map** (§9.2–9.4 shows it filling in) is a **generated view** — the same category as
HITL's command-map/posture views, regenerated from the accumulating scenario record **at each meaningful
step** (a component named/typed, a boundary drawn, a gate added, the deploy decision made). As agents are
added one at a time, the map grows one node/annotation at a time. Because HITL is used mostly in the
**terminal**, the map is terminal-first. The two **core** renderings from one data source:

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
> **Deferred enhancement (not core) — rich HTML + combined live mode.**
>
> 3. **Rich interactive HTML** — for the web surface, a shareable link, or the portal (the prototype at
>    `2e888cca-…` demonstrates it). **"Portal" means static-file publishing** (a generated HTML file served
>    as a static page) — *not* a hosted rendering service, which would cross governs-not-runtime.
>
> **Combined "chat + live map" mode (artifact-capable surfaces).** On a Claude Code surface with an artifact
> panel, rendering (3) becomes the *live* view: the intake **re-publishes the map artifact after each
> meaningful step to the same URL**, so the discussion and the evolving map sit together. **Two constraints
> keep it in-lane** for the follow-on: (a) the artifact is a **live view, not an input** (sandboxed, cannot
> post answers back — the conversation stays the input); (b) it is the **rich tier only** — a bare CLI or
> air-gapped setup always falls back to the terminal-text map (rendering 1). The demo at `efd56c28-…` shows
> the loop on a supply-chain flow. This mode is deferred because a Should feature should not carry a live
> re-publish loop and a host API into v1 (round-4 M8).

**Node-type visual vocabulary.** Every rendering uses one consistent visual language so a component's kind
reads at a glance: **agent** (hexagon / green), **deterministic service** (chip / steel), **datastore**
(cylinder / teal), **external actor** (cloud / dashed), **output store** (stacked layers), plus a
**message/email** edge (dashed + ✉) and a **human gate** marker (⛊). The terminal rendering uses ASCII
equivalents of the same vocabulary. LLD §6 specifies the icon set and the ASCII map.

**Boundary (governs-not-runtime):** HITL **writes the files and prints the text**; it does **not** run a
live-reload server. Live browser refresh is the user's IDE/tooling (the IDE Mermaid preview updates on file
change for free); the **core** deliverables are the terminal inline map and the regenerated Markdown/Mermaid
file (the re-published artifact is the deferred rich mode above). Regenerate is deterministic from the
scenario record, so the map never drifts from the design.

## 10. Decisions (locked as ADRs)

| # | Decision |
|---|---|
| A1 | The Advisor is a **set of harness-run commands**, not a separate app and not a monolith |
| A2 | The question/option **catalog is curated, versioned data** (question→consequence), curated-refresh not live lookup |
| A3 | **Recommend, never decide** — output is a proposal + decision record the human confirms |
| A4 | **HITL composes a proportionate workflow** from the intake — ask/run only what's relevant; depth follows risk |
| A5 | The commands **recommend + record**; they **do not author the manifest** (re-scope 2026-07-23). The output is a decision record + a manifest skeleton handoff; a **human authors** the manifest; **#10 validates** it |
| A6 | The **floor is a Tier + risk recommendation** (advice, not a gate) — the controls that shouldn't be skipped; a skip is **recorded**, and the hard block-or-waive happens **downstream at #10** on the human-authored manifest; Tier scales recommended depth |
| A7 | The Advisor **records the build-vs-buy decision; a human carries it** to the platform track — provisions nothing, auto-hands-off to nothing |
| A8 | The **evolving map is a generated view, terminal-first** — **core = inline text (no browser) + Markdown/Mermaid** in the decision record; regenerated per step; the **rich HTML + combined live mode are a deferred enhancement** (M8); HITL writes/prints, runs no live server |
| A9 | The intake **integrates into `pm-design-feature`/`AGENTS.md`** — a **cheap topology probe routes** (no circularity, B2): precedes the design track for compound systems (≥2 components + ≥1 edge), skipped for simple ones; never gates or replaces the existing intake |

## 11. Acceptance criteria (implementation gate)

1. The intake composes a workflow that is **short for a low-risk change** (example §9.6) and **full for a
   high-risk one** (§9.3); saga/async/deep-agent commands appear only when their data is present.
2. The floor **computation is deterministic** given declared factors (§5); a floor command **cannot be
   dropped silently** — dropping one requires a **recorded, tier-appropriate waiver** (ADV-12/ADR-A6).
3. Each command **authors manifest fields** such that #10's per-check activation runs the relevant
   validators — verified on a low- and a high-risk fixture (ADV-8); **`agentic-observability` authors the
   `observability` block** #10's `check_observability` floor-gates (hard directive); the **kill-switch
   declared artifact** is recorded (no #10 target yet), not silently omitted (§7).
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
