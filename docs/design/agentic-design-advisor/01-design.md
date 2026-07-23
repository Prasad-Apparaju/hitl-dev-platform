# Agentic Design Advisor: Design (HLD) — v4.1 (one intake + recommendation report; neutral handoff)

> Mechanism (the *how*) for [`../../01-product/agentic-design-advisor/requirements.md`](../../01-product/agentic-design-advisor/requirements.md)
> (ADV-1..ADV-15). Decisions in [`02-adrs.md`](02-adrs.md); field-level precision in the LLD
> [`04-lld.md`](04-lld.md); test plan in [`03-test-plan.md`](03-test-plan.md).
> Status: **draft, v4.1 — round-9 fixes applied.**
>
> **The model (v4.1):** the Advisor is **one intake command** (`hitl:agentic-intake`) that **elicits** the
> whole scenario, **recommends** a right-sized set of controls (a **recommendation report** whose sections
> are the relevant lenses — not 8 separate commands), **records** every decision, and **hands off** a
> **decision record + a neutral `agentic-design-handoff.yaml`** (components + connections + `proposed_kind`s
> + recommendation IDs + target-path hints — **not** a manifest). A **human authors** the manifest in the
> design phase; **#10 validates** it (unchanged, ships independently). The Advisor **authors no manifest
> field** (not even `kind`) — that boundary is the point of the feature: HITL must not let a PM front door
> produce design/implementation.
>
> **History (superseded).** v2–v3.3 had the Advisor's commands *author* the manifest #10 validates (a
> canonical-state writer, `floor ≡ activation`, imported activation, `OWNS_CHECKS`/`OWNERSHIP-COMPLETE`/
> `AUTHOR-COMPLETE`). Rounds 4–8 showed that seam only validated by building the real validator, and it
> crossed the PM/design line. It is **removed** (2026-07-23 re-scope); any residual authoring wording is a
> defect, not current design.

## 1. Thesis

**Encode the expert's questions as one thorough intake, right-size the recommendations, record the
decisions, and hand off to design.** There is no engine, no monolith, and — deliberately — **no manifest
authoring**: the Advisor is **one `hitl:agentic-intake` command** that understands the whole scenario,
**recommends** which controls this change needs (a right-sized **recommendation report** whose sections are
the relevant lenses), and **hands off** a decision record + a neutral `agentic-design-handoff.yaml`
(`proposed_kind`s + recommendation IDs + target-path hints). A **human** authors the real manifest in the
design phase; **#10 validates** it. The Advisor produces requirements-level outputs and a handoff — never
the design artifact itself (not even a `kind:` field). That boundary is the point: HITL must not let a PM
front door produce design/implementation.

## 2. One intake + its recommendation report (ADV-1)

The Advisor is **one command, `hitl:agentic-intake`** (round-9 M9: proportionate to a recommendation front
door — no 8 separate `hitl:agentic-*` commands). It elicits the whole scenario, then produces a
**recommendation report** whose **sections are the lenses** this change warrants. Each lens is a **section**,
not a runnable command; it **recommends + records** for its concern. No lens authors a manifest field — the
report is *advice* the design role acts on.

| Lens (report section) | Concern | Recommends + records (→ decision record; handoff = `proposed_*` + recommendation IDs) |
|---|---|---|
| classify | component right-sizing (agent vs deterministic; simple vs deep) | a **`proposed_kind`** + rationale per component (a recommendation, not a `kind:` field) |
| boundary | the determinism boundary + the inter-component contract | recommended trust-leg controls + which facades/authorizations the design must declare (target-path hints) |
| privilege | privilege / identity / trust (lethal-trifecta); **portability** | recommended capability/identity bounds per agent |
| reliability | reliability, idempotency, failure modes | recommended async/idempotency controls + a recommended **kill-switch** |
| observability | detectability; the **PM eval console** | a recommended observability/tracing plan + PM eval-console (which #10's `check_observability` **enforces** on the authored manifest — hard directive) |
| memory | memory / state, PII / data classification | recommended memory/PII controls |
| evals | evaluation (incl. model/prompt-version drift) | recommended eval coverage (per-agent + e2e) |
| deploy | build-vs-buy deployment | the **recorded** deployment decision (§8), human-carried |

A team may **re-run the intake focused on one lens** to refresh a single recommendation, but there is no
separate command per lens. The intake elicits once; each lens section **recommends and records** off the
already-elicited answers (no re-elicitation). None writes a manifest field — the design role authors the
manifest from the handoff (§7), and **#10 validates it**.

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
each), so different answers drive different downstream effects. There is **no `manifest_field` kind** — the
Advisor targets no #10 field (round-9 B2). The LLD (§2.3) uses this exact shape:

```yaml
consequence:                 # map[ <option-or-"*"> -> list[ item ] ]
  <option>:
    - kind: enum[ classify | boundary | gate | floor | recommendation | recorded_artifact ]
      # floor → a recommended-floor obligation id ; recommendation → a report recommendation id ;
      # recorded_artifact → a recorded design note with no #10 target (kill-switch; observability is a recommendation) ;
      # gate|boundary|classify → the specific recommended obligation
      target: string         # floor-rule id | recommendation id | artifact id
      note: string?
```

The lint (`CAT-SCHEMA`, LLD §2.3) rejects an entry with no `consequence`, an option without a key, or a
list item whose `floor`/`recommendation` target does not resolve. No consequence names a manifest field.

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

1. **The decision record / recommendation report** (`docs/01-product/<feature>/agentic-decisions.md`) — the
   scenario, the recommendation report (per-lens recommendations), the recommended floor + rungs, every menu
   decision (chosen/rejected + rationale), recorded **skips**, and the deploy decision. Regenerated from the
   scenario state on a re-run (never appended).
2. **The neutral design handoff — `agentic-design-handoff.yaml`** (explicitly **NOT** `system-manifest.yaml`;
   round-9 B2). It carries **recommendations and hints, no manifest field**:

   ```yaml
   schema_version: "1.0"
   feature: <id>
   components:   [ { id, proposed_kind: enum[deterministic,simple_agent,deep_agent], rationale } ]   # proposed_kind, NOT kind:
   connections:  [ { from: component-id, to: component-id, nature: enum[calls,hands-off,messages] } ]  # not `interactions`
   recommendations: [ { id, lens, control, depth, rationale } ]                                        # the floor/rungs, by id
   skips:        [ { control, owner, reason } ]                                                        # recorded, not a #10 waiver
   target_paths: [ { recommendation-id, manifest_path_hint, note } ]                                   # WHERE the design role authors it
   ```

   Every value is a **recommendation** (`proposed_kind`) or a **hint** (`manifest_path_hint`) — nothing here
   is a valid `system-manifest.yaml` field, not even `kind`, because a kind is a design classification the
   architect must author. If the design role adopts it, they author the manifest **anew** (a defined
   conversion step they own); the handoff is never edited-in-place into a manifest.

**A human authors the real manifest** from the handoff, in the design phase, using HITL's normal design
skills; **#10 validates** the human-authored manifest. The Advisor writes **no** manifest field, runs **no**
#10 validator, and requires **no** change to #10 — #10 activates purely from the *human-authored* manifest
and ships independently. This is the boundary the feature exists to hold: the PM front door produces a
recommendation + a handoff, not the design.

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

### 9.3 The intake recommends a right-sized floor

From those answers (Tier 2, irreversible, PII, supervised, small; greenfield, one async connection — Fixture
HIGH, test plan §4), the intake recommends a floor **from the risk factors** (expert safety judgment — *not*
derived from #10 activation):

```
RECOMMENDED FLOOR (report sections — shouldn't be skipped):
  classify        (any agent — right-size the two agents)
  boundary        (agent endpoints — validate the refund proposal before the deterministic service trusts it)
  privilege       (any agent — bound capabilities)
  reliability     (irreversible ⇒ recommend a HUMAN GATE; supervised+side-effects ⇒ recommend a KILL-SWITCH; async ⇒ idempotency)
  observability   (any agent — recommend tracing + a PM eval-console; depth: a console at Tier 2)
  evals           (any agent — recommend per-agent + one e2e eval)
OFFERED (rungs):
  deploy          (greenfield ⇒ a build-vs-buy recommendation; recorded, human-carried)
NOT RECOMMENDED:
  memory          (no cross-session state hinted)
```

The team sees a **six-section floor + one offered rung (deploy)** — one intake, not eight commands.
Proportionality shows up as **recommended depth** (a Tier-2 console vs a Tier-1 report) and in what is *not*
recommended (no memory). The floor is **advice**: nothing here gates — #10 does, later, on the human-authored
manifest.

### 9.4 What each lens recommends (into the report + the handoff)

- **classify** → **recommends** `proposed_kind: simple_agent` for the two agents, `deterministic` for the
  services, with rationale ("bounded task, no long-horizon planning"). *(A recommendation in the handoff —
  the architect authors the real `kind`.)*
- **boundary** → recommends validating `resolution_agent → refund_service` (the proposed refund must be
  checked before the deterministic service trusts it) and notes the target paths the design must author
  (`interactions[].response.validation`, the callee `facade_apis`).
- **privilege** → recommends `resolution_agent` may read + propose, nothing more; flags that direct payment
  access would be over-privilege.
- **reliability** → recommends a **human gate** before any refund, an **idempotency key** on the async ledger
  write, and a **kill-switch** (a recorded recommendation — #10 has no kill-switch field).
- **observability** → recommends a tracing plan across the four hops (OTel GenAI), a cost budget, and a **PM
  eval-console** (where the PM runs the refund-amount eval). *#10's `check_observability` will **enforce**
  this on the human-authored manifest (hard directive); the Advisor only recommends it.*
- **evals** → recommends per-agent baselines + one e2e, for the PM to own.
- **deploy** → recommends a **managed platform** (from-scratch rejected: "you'd rebuild orchestration/state/
  retries for no reason"), surfaces the lock-in trade-off + the three portability questions, **records** the
  decision, and prompts a human to carry it to the platform/ops track.

### 9.5 The handoff, and what the human + #10 do next

The intake writes the **decision record** (the report above) and the neutral **`agentic-design-handoff.yaml`**
— `proposed_kind`s, connections, the recommendation IDs, and target-path hints. **No manifest field is
written.** In the **design phase**, a human (architect/developer) authors the real `system-manifest.yaml`
from the handoff — the actual `kind`s, `interactions`, trust legs, `uses`, lifecycle gate, `observability`
block, evals. On `derive.py verify`, **#10's per-check activation runs on that human-authored manifest** and
enforces exactly the checks its content triggers — including `check_observability` on the authored block. If
the team **skipped** a recommended control (say the human gate), that skip is recorded in the handoff (owner
+ reason) but grants **no** #10 exception — #10 will still block until a human authors the control or a
**human-authored #10 waiver** relieves it. The result is a right-sized recommendation the design role turns
into a governed design.

### 9.6 Contrast — a lighter compound case, and the single-agent path

**A lighter compound system** (Fixture LOW, test plan §4): two agents, read-only, internal, Tier 1. The
recommended floor is `{classify, boundary, privilege, observability, evals}` — recommended because a
two-agent agentic system genuinely needs those controls (and #10 will enforce them once the design is
authored), so recommending them is honest safety advice, not ceremony. These are **five report sections of
one intake**, computed off the already-elicited answers — **not** five commands that re-elicit. What makes
it light: recommended **depth** is minimal (observability = an existing approved surface or a generated
report, not a bespoke console; privilege per-class; evals baseline) and reliability/memory/deploy are not
recommended at all. Proportionality is depth-and-omission — and the floor is *advice*, not a gate.

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
| A1 | The Advisor is **one `hitl:agentic-intake` command** producing a recommendation report — not 8 commands, not an app (round-9 M9) |
| A2 | The question/option **catalog is curated, versioned data** (question→consequence), curated-refresh not live lookup |
| A3 | **Recommend, never decide** — output is a proposal + decision record the human confirms |
| A4 | **HITL composes a proportionate workflow** from the intake — ask/run only what's relevant; depth follows risk |
| A5 | The intake **recommends + records**; it **authors no manifest field** (re-scope 2026-07-23). Output = a decision record + a neutral `agentic-design-handoff.yaml` (`proposed_kind`s + recommendation IDs + hints, no `kind:`); a **human authors** the manifest; **#10 validates** it |
| A6 | The **floor is a Tier + risk recommendation** (advice, not a gate) — the controls that shouldn't be skipped; a skip is **recorded**, and the hard block-or-waive happens **downstream at #10** on the human-authored manifest; Tier scales recommended depth |
| A7 | The Advisor **records the build-vs-buy decision; a human carries it** to the platform track — provisions nothing, auto-hands-off to nothing |
| A8 | The **evolving map is a generated view, terminal-first** — **core = inline text (no browser) + Markdown/Mermaid** in the decision record; regenerated per step; the **rich HTML + combined live mode are a deferred enhancement** (M8); HITL writes/prints, runs no live server |
| A9 | The intake **integrates into `pm-design-feature`/`AGENTS.md`** — a **cheap topology probe routes** (no circularity, B2): precedes the design track for compound systems (≥2 components + ≥1 edge), skipped for simple ones; never gates or replaces the existing intake |

## 11. Acceptance criteria (implementation gate)

1. The intake produces a **recommendation report** that is **short for a low-risk change** (§9.6) and **full
   for a high-risk one** (§9.3) — a lens section appears only when its data is present; it is **one intake**,
   not per-lens commands.
2. The recommended floor is **deterministic** given declared factors (§5); a recommended-floor control
   **cannot be skipped silently** — a skip is recorded `{control, owner, reason}` (ADV-12). The skip is an
   Advisor record, **not** a #10 waiver, and grants no gate exception; the hard block is downstream at #10.
3. The Advisor **authors no manifest field.** The output is the decision record + a neutral
   **`agentic-design-handoff.yaml`** (`proposed_kind`s + recommendation IDs + target-path hints, **no**
   manifest field, not even `kind`, §7/ADV-8); a **human authors** the manifest; **#10 validates** it —
   including `check_observability` on the *authored* observability block (the Advisor only *recommends* it).
   Verified: no `agentic-*` output contains a `system-manifest.yaml` field value.
4. Every menu decision emits a recommendation + rationale + recorded chosen/rejected; an override is
   recorded (ADV-6/ADV-9); build-vs-buy is owned by the deploy lens alone (not the generic menu).
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
