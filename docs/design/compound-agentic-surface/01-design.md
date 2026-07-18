# Compound Agentic System Surface: Design (HLD)

> Mechanism (the *how*) for the requirements (the *what*) in
> [`../../01-product/compound-agentic-surface/requirements.md`](../../01-product/compound-agentic-surface/requirements.md)
> (CR-1..CR-20). EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). Status:
> **v2 in progress** — architect-approved 2026-07-17, but an independent Codex review (2026-07-18) returned
> REVISIONS REQUIRED (6 blockers). Revision per [`04-revision-plan.md`](04-revision-plan.md). Targets **2.2.0**.
> ADRs for D1-D9: [`02-adrs.md`](02-adrs.md) (accepted). Remaining before implementation: the manifest schema update (LLD/#13).

The whole design rests on one move: **a compound agentic system is a manifest, extended.** Components
are manifest domains; inter-component and A2A edges are `facade_apis`; everything else — topology,
determinism boundary, privilege/tool/eval posture — is *derived* from that manifest plus the existing
registries. No new orthogonal machinery; the domain-boundary hook, tiered waivers, the derived-view
pattern (command-map / catalog / readiness register), and reviewer subagents all carry over.

## 1. The system model

A compound agentic system is a directed graph the manifest already almost expresses:

- **Nodes = domains**, extended with a `kind`: `deterministic` | `simple_agent` | `deep_agent`.
- **Edges = `facade_apis`**, extended with a `transport`: `sync` (request/response, incl. MCP tool
  calls) | `async` (A2A: SSE / webhook / polling / broker). An edge is a *declared, reviewed,
  boundary-enforced contract*, never an implicit prompt-string coupling.
- **Orchestration** is declared at the system level (pattern + coordinator), because it is not
  derivable from nodes and edges alone (CR-11).

Everything downstream reads from these additions.

## 2. Manifest schema extensions (additive)

**Which base form.** The authoritative schema (`ai/claude/generate-docs/templates/system-manifest.schema.yaml`)
defines `facade_apis` as a **map keyed by API name**, with `signature`, `blurb`, `mutations`,
`preconditions`, `error_modes`. This design extends **that** form (not the flatter list form in the
older template — reconciling the two is D8). The A2A **Task payload / contract shape lives in
`signature`** (B3). All additions are optional; a manifest with none of them is a valid non-agentic
manifest, so this is additive.

```yaml
orchestration:                     # system-level (CR-11, M3)
  pattern: supervisor              # supervisor | hierarchical | swarm | blackboard | sequential | hybrid
  coordinator: research_supervisor # the domain that routes, if any
  cycle_bound: 5                   # max delegation depth; a graph cycle without this blocks (M1)

domains:
  research_agent:
    purpose: "Answers research questions over the corpus"
    kind: deep_agent               # deterministic | simple_agent | deep_agent           (CR-2)
    facade_apis:                   # MAP keyed by name (schema form)                      (CR-5, B3)
      research:
        signature: "research(query: str, depth: int) -> ResearchResult"  # Task payload shape
        blurb: "Run a research task"
        transport: async           # sync | async                                        (CR-3)
        preconditions: ["query non-empty"]
        error_modes: ["timeout", "no_sources_found"]
        mutations: ["appends to research_notes"]
        async:                     # present iff transport: async                        (CR-12)
          delivery: at_least_once
          idempotency_key: task_id
          timeout: 300s            # cross-hop timeout                                    (M1)
          retry: { max: 3, backoff: exponential }                                       # (M1)
          dlq: true
          replay: event_sourced
          compensation: cancel_research   # saga/compensating action for rollback        (M2)
    identity:                      # non-human principal (granted privilege)             (CR-13, CR-14)
      principal: sa-research-agent
      privilege: [read:corpus, vector:query, web:search, write:memory/research, read:memory/research]
    tools:                         # each MUST resolve in the approved-tool registry     (CR-15)
      - web_search
      - vector_query
    memory:                        # short + long term, governed                         (CR-18)
      short_term: { strategy: summarize, budget_tokens: 8000 }
      long_term:
        store: research
        writes: [research_notes]   # per-STORE scope: write:memory/research  (B1/M5)
        reads:  [research_notes]   # retrieval; per-STORE scope: read:memory/research  (CR-18)
        pii: redact
        scope: isolated            # isolated | shared                                   (m4)
        shared_store: null         # ref when scope: shared
    lifecycle:                     # long-running / durable execution                    (CR-17, M4)
      long_running: true
      checkpoint: durable
      resumable: true
      idempotent_resume: true      # a resumed step must not re-fire side effects
      human_gate_pause: true
      timeout: 24h
      cancellation: cooperative
    deep_agent:                    # REQUIRED iff kind: deep_agent                       (CR-7, B2)
      planner: write_todos
      subagents:                   # the sub-agent registry (capability descriptions)
        - { name: source_finder, capability: "find candidate sources" }
      context_isolation: true
      gates: [human_review_before_publish]
      guardrails: ["never delete corpus", "never exfiltrate raw sources"]
    evals:                         # eval spec + baseline seed                           (CR-8, CR-16, CR-20)
      spec: docs/03-engineering/evals/research_agent.yaml
```

Two new **top-level registries** (the registries pattern):

- `docs/03-engineering/approved-tools.yaml` — approved-tool registry: `{tool, risk, scopes}` where
  **`scopes` is the complete set of privilege scopes the tool requires** (the source for "needed"
  privilege, B1). Every scope an agent needs to *read* or *act* enters through a tool here — there is
  no orphan-privilege channel (inter-agent access is via edges §5, not free-floating scopes). (CR-15.)
- `docs/03-engineering/evals/` — per-component eval specs + the eval registry. (CR-16, CR-20.)

```yaml
# docs/03-engineering/approved-tools.yaml  (justifies the example agent's grant)
tools:
  vector_query: { risk: low, scopes: [vector:query, read:corpus] }
  web_search:   { risk: med, scopes: [web:search] }
```

So the example agent's **needed** = `{vector:query, read:corpus}` (from `vector_query`) ∪ `{web:search}`
(from `web_search`) ∪ `{write:memory/research, read:memory/research}` (its long-term store's writes +
reads) — **exactly** its **granted** set. The showcase manifest passes its own privilege validator.

## 3. Derived + declared views (never hand-maintained)

Views are *generated* from the manifest + registries, like the command-map and catalog — cannot drift,
and static (no live dashboard — governs-not-runtime, D5).

### 3.1 Topology & routing view (CR-3, M3)

The component graph with typed edges, the declared `orchestration.pattern`, and shared-vs-isolated
memory (`memory.long_term.scope`, m4). Rendered as a Mermaid graph + a table; the determinism boundary
(§4) is drawn on it.

### 3.2 Privilege-posture matrix (CR-14)

Each agent × granted vs derived-needed privilege, with over/under flags (§6).

### 3.3 Approved-tool matrix (CR-15)

Each agent × declared tools, unapproved/undeclared flagged.

## 4. The determinism boundary (CR-4)

Derived, not hand-drawn: an edge is a **boundary edge** when its ends differ in determinism (a
`deterministic` domain on one side, an agent on the other). The discipline:

- **stochastic → deterministic**: the agent's output MUST be validated (schema/guardrail) before the
  deterministic component trusts it; the validator (§6) flags a boundary edge with no declared check.
- **deterministic → stochastic**: MUST declare **bounded cost** (token/fan-out ceiling) and **bounded
  authority** (the privilege the downstream agent may act with); flagged if unbounded.

This also covers **non-determinism propagation** (CR-6): a stochastic output crossing into a
deterministic component without validation is exactly the flagged case.

## 5. A2A as governed contracts (CR-5)

- An agent's **Agent Card** (advertised capabilities) *is* its `facade_apis` map — declared, reviewed,
  boundary-enforced. No capability an agent didn't declare.
- An A2A **Task** payload is a call against a declared facade; its **contract shape is `signature`**
  (B3), with `preconditions` + `error_modes` applying.
- **Enforcement is design-time** (M6): the domain-boundary hook checks that a cross-domain interaction
  targets a **declared** facade the caller is permitted to reach. It does **not** inspect live message
  traffic — that would cross into runtime (D5). Runtime transport (SSE/webhook/broker) is the
  product's.

## 6. Enforcement (where the teeth are)

Additive, fail-closed validators with `ci/` regression suites (the platform-gate discipline):

- **Approved-tool gate** (CR-15): every `tools[]` entry must resolve in `approved-tools.yaml`; an
  undeclared or unapproved tool **blocks**.
- **Privilege validator** (CR-14, B1, M5): computes **needed** privilege as
  `⋃(approved-tools[t].scopes for t in tools)` ∪ `{write:memory/<store> for each long_term store with
  writes}` ∪ `{read:memory/<store> for each store in long_term.reads}`. Memory scopes are **per-store, not
  per-write** (two writes to one store collapse to one scope). It then flags **over-privilege**
  (`granted ∖ needed`) and **under-privilege** (`needed ∖ granted`). Model invariant (D9): *every*
  privilege an agent needs traces to a tool scope or a memory scope — there is no orphan channel, so a
  granted scope with no such source is genuine over-privilege, not a false positive. A declared memory
  write without its `write:memory/<store>` grant surfaces as under-privilege — the memory↔privilege
  invariant is enforced here, not in prose (M5). Emits the posture matrix. Design-time; the optional
  granted-scope drift-check is **strictly read-only and opt-in**, never a runtime opinion (m6).
- **Determinism-boundary validator** (CR-4): flags a boundary edge missing its output validation or its
  cost/authority bound.
- **Async-edge validator** (CR-12, M2): an `async` facade must declare delivery + idempotency
  (`at_least_once` without an idempotency key blocks); a multi-step async workflow must declare
  `compensation`.
- **Topology validator** (CR-6, M1): **cycle/loop detection** off the graph — a cycle in the agent
  graph without a declared `orchestration.cycle_bound` (max delegation depth) blocks; the graph is
  already built for §3.1, so this is free.
- **Deep-agent completeness validator** (CR-7, B2): `kind: deep_agent` REQUIRES the `deep_agent` block
  (planner, subagents, context_isolation, gates, guardrails) **and** `memory.long_term` (persistent
  memory is part of CR-7); missing any blocks.
- **Lifecycle completeness validator** (CR-17, M4): `lifecycle.long_running: true` REQUIRES
  `checkpoint`, `resumable`, `idempotent_resume`, and `timeout`; missing any blocks.

CR-6's remaining named modes map to existing mechanisms: cross-hop **timeout/retry** → the `async`
block fields; **cost amplification** → §11; **cross-agent trust** → the identity/privilege model.

## 7. The design track (CR-1, CR-2, CR-11, CR-19)

`pm-design-feature` (and `ai/codex/AGENTS.md`) gain a **compound agentic system** surface branch,
selected when a product has ≥2 components and ≥1 inter-component edge. It walks:

1. **Classify** each component (CR-2).
2. **Name the orchestration pattern** and justify against task shape, with the token-overhead caution
   (CR-11) — written to `orchestration`.
3. **Draw topology + determinism boundary** (§3.1).
4. **Declare** edges, identity/privilege, tools, memory, lifecycle, deep_agent block (§2).
5. **Generate baseline evals** (§8) and prompt the PM to own them (CR-20).
6. Assemble the decision packet → TA gate.

At every decision with materially different modern options it **presents the capability menu** (§9) with
when-to / when-not, records chosen + rejected, and — Tier 3 — runs a "scan for newer capabilities"
check. It **always presents options; may recommend, never silently decides** (CR-19). Note (m5): CR-2's
"simplest that works" and CR-11's pattern-justification are **reviewed at the TA gate**, not enforced by
an automated validator — they are design-track discipline, not teeth, unlike the tool/privilege gates.

## 8. Eval discipline (CR-8, CR-16, CR-20)

- **Baseline-eval generator**: derive a starting eval set for each component and flow segment from the
  acceptance criteria (owning `FR-n`), the `facade_apis` contract (`signature` + `preconditions` +
  `error_modes`), the determinism-boundary checks, and the known failure modes (CR-6). Written to
  `docs/03-engineering/evals/`.
- **PM owns them**: the workflow prompts the PM to refine/extend/approve; a component with **no** evals
  is a recorded waiver. The QA reviewer gate can flag "baseline-only, not meaningfully extended" so
  generation doesn't breed false confidence.
- **Independently runnable**: per-node evals, per-edge contract tests, per-segment sub-flow tests, E2E.
- **Continuous eval from production traffic** (CR-16 maturity rung, m2): out of scope for the shipped
  capability (it needs the product's runtime), but the eval spec format is designed so production
  traces can be replayed into it later; noted as the maturity step, not built here.

## 9. The capability catalog (CR-19)

A curated, refreshable reference — `docs/patterns/compound-agentic-systems.md` — holds the option menu:
each capability with **when-to-use / when-not** and concrete implementations named only as *examples*
(deep agents, LangGraph, Temporal, Vercel AI SDK, A2A SDK). The design skill reads and surfaces it.
**Staleness is the known cost**: the catalog names an owner and a refresh cadence, and the Tier-3 "scan
for newer" step is its backstop. Generalizing this per-domain is backlogged on
[#8](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/8).

## 10. Memory, deep agents, durable execution (CR-7, CR-17, CR-18)

- **Memory** (CR-18): declared per agent (§2). `short_term` is a context-engineering strategy with a
  token budget; `long_term` is a **governed durable store** — writes declared (and joined to privilege
  by the §6 validator), PII redaction required, `scope` (shared|isolated) declared so §3.1 can render
  it, staleness/ownership tracked.
- **Deep agents** (CR-7, B2): the `deep_agent` block is required and completeness-validated.
- **Durable execution** (CR-17, M4): `lifecycle` fields (checkpoint, resumable, idempotent_resume,
  timeout, cancellation, human_gate_pause) are completeness-validated. Complements the async-edge
  reliability (§6), which is the edge's concern.

## 11. Observability (CR-9)

The design must specify **cross-hop trace propagation** (OTel/OpenInference-style) and a **token-cost
amplification budget** on the token-cost registry (fan-out cost bounded and observed). HITL requires and
validates the design; the live APM is the product's.

## 12. Identity: node vs edge (CR-13, m3)

`identity`/`privilege` are declared on the **node** (the agent's principal and what it may do once
invoked). "**Who may invoke**" is enforced on the **edge** by the domain-boundary hook (the caller must
be a declared domain permitted to reach the facade). **Just-in-time** is a runtime property the design
requires (least-privilege, short-lived credentials) but does not represent statically — flagged so the
node-vs-edge split is a conscious choice, not an omission.

## 13. What this deliberately reuses

Manifest domains + `facade_apis`; the domain-boundary hook; the registries pattern (new tool + eval
registries); tiered waivers (no-evals / accepted-gap); derived views; reviewer subagents; the
breadcrumb. Nothing orthogonal is introduced.

## 14. Decisions (proposed — to lock at ADR stage)

| # | Decision | Rationale / alternatives |
|---|---|---|
| D1 | A component **is a manifest domain** (extended with `kind`) | Reuses bounded-context + boundary enforcement; a separate agent registry would duplicate the manifest and split enforcement |
| D2 | An A2A/inter-component edge **is a `facade_api`** (extended with `transport`) | Agent Cards already are capability lists; reusing facades gives declaration + review + boundary enforcement for free |
| D3 | Topology + privilege + tool posture are **generated**, never hand-maintained | Same guarantee as command-map/catalog: cannot drift |
| D4 | **Framework-agnostic** — capabilities governed; LangGraph/A2A/MCP/Temporal/Vercel are examples | Avoids framework-version churn as a maintenance liability (CR-10) |
| D5 | **Governs, not runs** — validate design + emit static views; no runtime dashboard/backbone/eval-engine; boundary hook stays design-time | Keeps HITL in its lane; the runtime is the product's (companion demo #21) |
| D6 | The capability menu is **always presented**; the harness may recommend, never silently decides | "AI proposes, humans decide" applied to technology choices (CR-19) |
| D7 | The determinism boundary is **derived** from component kinds; a validator enforces guardrail-at-boundary | Makes the det/non-det seam a checkable invariant, not prose |
| D8 | Extend the **schema (map) form** of `facade_apis`; the A2A Task payload maps to `signature`; reconcile the older list-form template to match | The schema is authoritative; a payload contract needs a home; the pre-existing schema/template disagreement must not be inherited silently |
| D9 | **Every agent privilege traces to a tool scope or a memory scope** — no orphan-privilege channel; memory scopes are per-store | Makes the privilege validator's needed-set complete and computable (a granted scope with no source is genuine over-privilege); inter-agent access is governed by edges (§5), not free-floating scopes |

## 15. Architect review disposition (round 1)

| Finding | Disposition |
|---|---|
| **B1** privilege "needed" has no source | Fixed §6: needed derived from `approved-tools[].scopes` + `memory.long_term.writes`; over/under now computable |
| **B2** deep-agent elements unencoded | Fixed §2/§6: `deep_agent` block + completeness validator |
| **B3** facade schema mismatch + no A2A payload home | Fixed §2/§5/D8: extend the schema map form; payload = `signature`; reconcile template |
| **M1** CR-6 failure modes unmechanized | Fixed §6: topology cycle-detection validator; timeout/retry in `async`; boundary + identity cover the rest |
| **M2** sagas/compensation dropped | Fixed §2/§6: `async.compensation`; multi-step async requires it |
| **M3** topology can't show routing/pattern | Fixed §1/§2/§3: declared `orchestration` (pattern + coordinator) |
| **M4** lifecycle under-declared/unenforced | Fixed §2/§6: timeout/cancellation/idempotent_resume + lifecycle completeness validator |
| **M5** memory-write↔privilege unenforced | Fixed §6: folded into the privilege validator's needed-set |
| **M6** boundary hook async ambiguity | Fixed §5: explicitly design-time (declared-facade check), not live traffic |
| **m1** version 2.2.0 vs 2.3.0 | Fixed: header now 2.2.0 (matches requirements) |
| **m2** continuous-eval-from-prod missing | Fixed §8: noted as the maturity rung, format designed for it, not built |
| **m3** CR-13 node vs edge | Fixed §12: explicit node/edge split + JIT-is-runtime note |
| **m4** shared-vs-isolated memory no field | Fixed §2/§3: `memory.long_term.scope` |
| **m5** CR-2/CR-11 no teeth | Acknowledged §7: TA-gate discipline, not an automated gate — stated |
| **m6** drift-check touches live plane | Fixed §6: strictly read-only + opt-in |

**Round 2** re-review confirmed round-1 closed but caught two real defects the revisions introduced:

| Finding (round 2) | Disposition |
|---|---|
| The showcase privilege example **failed its own validator** (grant `write:memory/research` vs derived `write:memory/vector`; `read:corpus` unsourced) | Fixed §2: memory `store: research`; added the `approved-tools.yaml` scope mapping (`vector_query → [vector:query, read:corpus]`, `web_search → [web:search]`) so needed = granted exactly |
| **Needed-set soundness** — no channel for read/input scopes that aren't tool-scopes or memory-writes | Fixed §6/D9: model invariant — every privilege traces to a tool scope or memory scope; `read:corpus` enters via `vector_query`'s scopes; no orphan channel |
| **M1 cycle bound had no declared field** — validator blocked on a field that couldn't be declared | Fixed §2/§6: `orchestration.cycle_bound` (max delegation depth) |
| Memory-scope granularity (per-write vs per-store) unspecified | Fixed §6: **per-store** |
| Deep-agent completeness didn't require persistent memory (CR-7) | Fixed §6: also requires `memory.long_term` |
| "§3.1" cross-refs but no §3.1 heading | Fixed §3: real §3.1/§3.2/§3.3 subsections |

**Round 3: APPROVED.** All round-2 items confirmed closed; the showcase reconciles exactly. One
non-blocking latent gap it flagged for LLD — the `read:memory/<store>` clause had no declared source —
is closed here by adding `memory.long_term.reads` (retrieval governance, CR-18); the showcase grants
`read:memory/research` and still balances.

## 16. Acceptance criteria (implementation gate)

1. A manifest with the §2 additions validates; a manifest without them still validates (additive).
   Catalog `verify` stays lossless; skill-lint passes on new/changed skills.
2. Topology, privilege, and approved-tool views generate from a manifest + registries with zero
   hand-editing, and the topology view renders the orchestration pattern + shared/isolated memory.
3. Each validator has a `ci/` regression suite and fails closed: approved-tool gate; privilege
   validator flagging a deliberately over- and under-privileged agent (incl. a memory-write without its
   grant); determinism-boundary; async-edge (idempotency + compensation); topology cycle-detection;
   deep-agent completeness; lifecycle completeness.
4. `pm-design-feature` routes a ≥2-component product into the compound track, presents the capability
   menu at each decision, and records chosen + rejected.
5. The baseline-eval generator produces evals for a component from its acceptance criteria + facade
   contract; a no-evals component is a recorded waiver.
6. Both Codex stages pass (source → built plugin) before the marketplace serves 2.2.0.
