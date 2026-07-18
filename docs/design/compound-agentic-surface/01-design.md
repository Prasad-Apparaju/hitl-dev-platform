# Compound Agentic System Surface: Design (HLD)

> Mechanism (the *how*) for the requirements (the *what*) in
> [`../../01-product/compound-agentic-surface/requirements.md`](../../01-product/compound-agentic-surface/requirements.md)
> (CR-1..CR-20). EPIC [#10](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/10). Status:
> **draft, pending architect review**. Targets **2.3.0** on the 2.x line.

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

Everything downstream (CR-2..CR-6) reads from these two additions. (CR-1, CR-3, CR-5.)

## 2. Manifest schema extensions (additive)

New optional fields on `DomainEntry`; a manifest with none of them is a valid non-agentic manifest,
so this is additive (constraint §5). A component-domain adds:

```yaml
domains:
  research_agent:
    purpose: "Answers research questions over the corpus"
    kind: deep_agent            # deterministic | simple_agent | deep_agent   (CR-2)
    facade_apis:
      - name: research
        description: "Run a research task"
        transport: async         # sync | async                              (CR-3, CR-5)
        preconditions: ["query non-empty"]
        error_modes: ["timeout", "no_sources_found"]
        async:                   # present iff transport: async              (CR-12)
          delivery: at_least_once
          idempotency_key: task_id
          dlq: true
          replay: event_sourced
    identity:                    # non-human identity + least privilege      (CR-13, CR-14)
      principal: sa-research-agent
      privilege: [read:corpus, write:memory/research]
    tools:                       # each MUST be in the approved-tool registry (CR-15)
      - web_search
      - vector_query
    memory:                      # short + long term, governed               (CR-18)
      short_term: { strategy: summarize, budget_tokens: 8000 }
      long_term:  { store: vector, writes: [research_notes], pii: redact }
    lifecycle:                   # long-running / durable execution          (CR-17)
      long_running: true
      checkpoint: durable
      resumable: true
      human_gate_pause: true
    evals:                       # eval spec + baseline seed                 (CR-8, CR-16, CR-20)
      spec: docs/03-engineering/evals/research_agent.yaml
```

Two new **top-level registries** (the registries pattern):

- `docs/03-engineering/approved-tools.yaml` — the approved-tool registry: `{tool, scope, risk}` per
  tool. (CR-15.)
- `docs/03-engineering/evals/` — per-component eval specs + the eval registry. (CR-16, CR-20.)

## 3. Derived views (never hand-maintained)

Three views are *generated* from the manifest + registries, exactly like the command-map and catalog:

1. **Topology & routing view** (CR-3): the component graph with typed edges, rendered from `domains`
   + `facade_apis.transport`. A Mermaid graph + a table; the determinism boundary (§4) is drawn on it.
2. **Privilege-posture matrix** (CR-14): each agent × its declared privilege, with over/under-privilege
   flags from the validator (§6).
3. **Approved-tool matrix** (CR-15): each agent × its declared tools, with any unapproved/undeclared
   tool flagged.

Generated, so they cannot drift; static, so no live dashboard ships (governs-not-runtime, D5).

## 4. The determinism boundary (CR-4)

The boundary is *derived*, not hand-drawn: an edge is a **boundary edge** when its two ends differ in
determinism (a `deterministic` domain on one side, an agent on the other). The discipline:

- **stochastic → deterministic** edge: the agent's output MUST be validated (schema/guardrail) before
  the deterministic component trusts it. The design declares the validator on the edge; the validator
  (§6) flags a boundary edge with no declared output check.
- **deterministic → stochastic** edge: MUST declare **bounded cost** (a token/fan-out ceiling) and
  **bounded authority** (the privilege the downstream agent may act with). Flagged if unbounded.

This is the "declare your boundaries and enforce them" principle applied to the det/non-det seam.

## 5. A2A as governed contracts (CR-5)

A2A maps cleanly onto the manifest:

- An agent's **Agent Card** (its advertised capabilities) *is* its list of `facade_apis` — declared,
  reviewed, and boundary-enforced. No capability an agent didn't declare.
- An A2A **Task** payload is a call against a declared facade (preconditions + error_modes apply).
- The **domain-boundary hook** already blocks off-contract cross-domain interaction; it now also
  covers async edges, so an agent cannot reach a capability it wasn't granted.

HITL governs the contract; the transport (SSE/webhook/broker) is the product's runtime (D5, CR-10).

## 6. Enforcement (where the teeth are)

Additive validators, reusing the fail-closed hook pattern:

- **Approved-tool gate** (CR-15): every `tools[]` entry must resolve in `approved-tools.yaml`; an
  undeclared or unapproved tool **blocks**. Runs in CI + as a pre-flight.
- **Privilege validator** (CR-14): flags **over-privilege** (granted ⊋ needed) and **under-privilege**
  (needed ⊋ granted, which would fail at runtime); emits the posture matrix. Design-time; drift-checks
  granted scopes where the product exposes them.
- **Determinism-boundary validator** (CR-4): flags a boundary edge missing its required output
  validation (stochastic→deterministic) or its cost/authority bound (deterministic→stochastic).
- **Async-edge validator** (CR-12): an `async` facade must declare delivery semantics + idempotency;
  `at_least_once` without an idempotency key blocks.

All are fail-closed and carry regression suites under `ci/` — the discipline that hardened the
platform gate.

## 7. The design track (CR-1, CR-2, CR-11, CR-19)

`pm-design-feature` (and `ai/codex/AGENTS.md`) gain a **compound agentic system** surface branch,
selected when a product has ≥2 components and ≥1 inter-component edge. It walks:

1. **Classify** each component (deterministic / simple / deep) — simplest that works (CR-2).
2. **Name the orchestration pattern** (supervisor / hierarchical / swarm / blackboard / sequential /
   hybrid) and justify against task shape, with the token-overhead caution (CR-11).
3. **Draw topology + determinism boundary** (generates §3.1 from the declared manifest).
4. **Declare** each agent's edges, identity/privilege, tools, memory, lifecycle (§2).
5. **Generate baseline evals** (§8) and prompt the PM to own them (CR-20).
6. Assemble the decision packet → TA gate.

At every decision with materially different modern options, the track **presents the capability menu**
(§9) with when-to / when-not, records chosen + rejected as a decision, and — Tier 3 — runs a
"scan for newer capabilities" check. It **always presents options; may recommend, never silently
decides** (CR-19).

## 8. Eval discipline (CR-8, CR-16, CR-20)

- **Baseline-eval generator**: for each component and flow segment, derive a starting eval set from the
  acceptance criteria (owning `FR-n`), the component's `facade_apis` (preconditions + error_modes), the
  determinism-boundary checks, and the known failure modes (CR-6). Written to `docs/03-engineering/evals/`.
- **PM owns them**: the workflow prompts the PM to refine/extend/approve; a component with **no** evals
  is a recorded waiver, not a silent gap. The QA reviewer gate can flag "baseline-only, not meaningfully
  extended" so generation doesn't breed false confidence.
- **Independently runnable**: per-node evals, per-edge contract tests, per-segment sub-flow tests, and
  E2E — mirroring the single-agent `qa-plan-tests` → `qa-verify-quality` path.

## 9. The capability catalog (CR-19)

A curated, refreshable reference — `docs/patterns/compound-agentic-systems.md` — holds the option menu:
each capability (component kinds, orchestration patterns, memory strategies, durable execution, A2A vs
MCP, async transports) with **when-to-use / when-not** and concrete implementations named only as
*examples* (deep agents, LangGraph, Temporal, Vercel AI SDK, A2A SDK). The design skill reads and
surfaces it. **Staleness is the known cost** (requirements §hard-part): the catalog names an owner and a
refresh cadence, and the Tier-3 "scan for newer" step is its backstop. Generalizing this per-domain is
backlogged on [#8](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/8).

## 10. Memory, deep agents, durable execution (CR-7, CR-17, CR-18)

- **Memory** (CR-18): declared per agent (§2). `short_term` is a context-engineering strategy
  (summarize/compress/isolate) with a token budget; `long_term` is a **governed durable store** — writes
  declared (joined with the tool/privilege model), PII redaction required, staleness/ownership tracked.
  Shared-vs-isolated memory is a topology decision drawn on §3.1.
- **Deep agents** (CR-7): a `deep_agent` kind must declare planner, sub-agent registry (capability
  descriptions), context isolation, its own HITL gates, and never-do guardrails.
- **Durable execution** (CR-17): `lifecycle.long_running` triggers required design of checkpointing,
  resumability, human-gate pause/resume, and idempotency-on-resume. Complements the async-edge
  reliability (§6), which is the edge's concern.

## 11. Observability (CR-9)

The design must specify **cross-hop trace propagation** (OTel/OpenInference-style) so a request is
traceable across agent hops, and a **token-cost amplification budget** added to the token-cost
registry (fan-out cost is bounded and observed). HITL requires and validates the design; the live APM
is the product's.

## 12. What this deliberately reuses

Manifest domains + `facade_apis`; the domain-boundary hook; the registries pattern (new tool + eval
registries); tiered waivers (no-evals / accepted-gap); derived views (command-map/catalog precedent);
reviewer subagents (architect + QA gates); the breadcrumb. Nothing orthogonal is introduced.

## 13. Decisions (proposed — to lock at architect review)

| # | Decision | Rationale / alternatives |
|---|---|---|
| D1 | A component **is a manifest domain** (extended with `kind`) | Reuses bounded-context + boundary enforcement; alternative (a separate agent registry) duplicates the manifest and splits enforcement |
| D2 | An A2A/inter-component edge **is a `facade_api`** (extended with `transport`) | Agent Cards already are capability lists; reusing facades gives declaration + review + boundary enforcement for free |
| D3 | Topology + privilege + tool posture are **generated**, never hand-maintained | Same guarantee as command-map/catalog: cannot drift |
| D4 | **Framework-agnostic** — capabilities are governed; LangGraph/A2A/MCP/Temporal/Vercel are examples | Avoids framework-version churn as a maintenance liability (CR-10) |
| D5 | **Governs, not runs** — validate design + emit static views; no runtime dashboard/backbone/eval-engine | Keeps HITL in its lane; the runtime is the product's (companion demo #21) |
| D6 | The capability menu is **always presented**; the harness may recommend, never silently decides | "AI proposes, humans decide" applied to technology choices (CR-19) |
| D7 | The determinism boundary is **derived** from component kinds; the validator enforces the guardrail-at-boundary | Makes the det/non-det seam a checkable invariant, not prose |

## 14. Acceptance criteria (implementation gate)

1. A manifest with `kind` + typed `facade_apis` validates; a manifest without them still validates
   (additive). Catalog `verify` stays lossless; skill-lint passes on new/changed skills.
2. The topology, privilege, and approved-tool views generate from a manifest + registries with zero
   hand-editing.
3. The approved-tool gate blocks an agent declaring an unapproved/undeclared tool; the privilege
   validator flags a deliberately over- and under-privileged agent; the determinism-boundary validator
   flags an unguarded boundary edge; the async-edge validator flags `at_least_once` without an
   idempotency key — each with a regression suite under `ci/`.
4. `pm-design-feature` routes a ≥2-component product into the compound track, presents the capability
   menu at each decision, and records chosen + rejected.
5. The baseline-eval generator produces evals for a component from its acceptance criteria + facade
   contract; a no-evals component is a recorded waiver.
6. Both Codex stages pass (source → built plugin) before the marketplace serves the release.
