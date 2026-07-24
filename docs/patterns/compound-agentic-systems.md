# Pattern: Compound Agentic Systems

**When your product is a graph of deterministic services + simple/deep agents talking over sync, async, and
event edges — not a single agent — govern it as a compound-agentic system.** HITL validates the *design*
(declarations, coverage, consistency); the product owns the runtime.

> This is the practitioner's guide. Field-level truth lives in the design package
> [`docs/design/compound-agentic-surface/`](../design/compound-agentic-surface/) (HLD/ADRs/LLD). The
> schema is [`ai/claude/generate-docs/templates/system-manifest.schema.yaml`](../../ai/claude/generate-docs/templates/system-manifest.schema.yaml);
> the worked reference is [`docs/examples/compound-agentic/system-manifest.yaml`](../examples/compound-agentic/system-manifest.yaml).

## When to use it

During `pm-design-feature`, if the delivery surface is **agentic**, answer the two-question probe:

1. How many distinct components (services / agents / stores)?
2. Does any component call, hand off to, or message another?

**≥2 components AND ≥1 inter-component edge → the compound-agentic surface.** A single agent stays on the
single-agent path; a non-agentic multi-service app never reaches the probe. Don't reach for this pattern for a
lone tool-using agent — that is over-engineering, which the surface exists to prevent.

## The model: a manifest, extended

A compound system is your existing `docs/system-manifest.yaml` with additive, optional blocks. A deterministic
or legacy manifest is unaffected — each validator activates only on the data it governs (a manifest that
declares nothing new needs no new registry).

### 1. Classify each component — the simplest kind that fits

`kind: deterministic | simple_agent | deep_agent` on each domain. State `kind_rationale` for every agent — the
anti-over-engineering check. Reach for `deep_agent` (planner + subagents + virtual-filesystem memory) only when
the task genuinely needs long-horizon planning; most agents are `simple_agent`.

### 2. Edges — the `interactions` list, with trust legs

One `interactions[]` element per edge (parallel edges between the same pair are two elements — a `sync_call`
*and* an `event` both from A to B). Each edge has a `kind` (`sync_call` / `async_task` / `event`), the `facade`
it targets, and **trust legs**:

| leg (source → consumer) | must carry |
|---|---|
| consumer is an **agent** | `cost_bound` + `authority_bound` (⊆ the agent's `identity.privilege`) |
| **agent → deterministic** | `validation` (a schema/guardrail policy) |
| deterministic → deterministic | nothing |

You cannot skip a control by omitting the leg — an omitted leg that the rule requires is a blocker.

### 3. Privilege — necessary and sufficient

Each agent declares an `identity` (principal + granted scopes) and least-privilege `uses` (capability +
operations + resources). Every used scope must be ⊆ its ceiling in `approved-capabilities.yaml`; grants and
needs must **mutually cover** (an over-broad grant is over-privilege; a used-but-ungranted scope is
under-privilege). Who-may-invoke is `authorization.allowed_callers` on the edge — an *authorization*, never an
identity grant.

### 4. Reliability — declare what survives failure

`async` (idempotency + DLQ for at-least-once delivery), `lifecycle` (durable checkpoint/resume for
long-running components), and top-level `sagas` for distributed compensation. The core validates declared
sagas; a transactional flow with no covering saga raises an **advisory** (HITL does not yet enforce
distributed compensation — handle rollback deliberately).

### 5. Observability — the floor gate

Every agentic system declares a top-level `observability` block: tracing (a convention — `otel_genai` /
`openinference` — with its required span attributes, and every agent hop traced), a `cost_budget`, and a
**PM `eval_console`** whose depth scales with tier (a report/existing surface at Tier ≤ 1, a real console at
Tier ≥ 2). **A system without it does not pass.** HITL gates the declaration; the product builds the backend.

### 6. Evals — independently testable

A per-agent eval `spec` plus one `e2e` segment (`segments[]`), approved at Tier 2+. HITL governs *coverage*,
not results — running the evals (the adapter) is the product's, deferred to the follow-on (#42).

## Validate + generate

```bash
# gate the design (exit 0 = passes; exit 2 = blockers)
python3 ci/manifest-agentic/check_manifest_agentic.py docs/system-manifest.yaml --tier <0..3>

# generate posture views + the eval index (regenerate-and-diff; --check fails on drift)
python3 tools/manifest-agentic/generate_views.py docs/system-manifest.yaml
```

The validators are **fail-closed and per-check activated**; a human may record a tier-appropriate exception in
`ci/manifest-agentic/manifest-waivers.yaml` (owner + reason + revisit) — never a silent skip. The generator
emits `docs/03-engineering/agentic-posture/` (topology, privilege, tool matrix, projections) and the eval
index; CI runs `--check` so a generated view can never drift from the manifest.

## Registries you author once

- `docs/03-engineering/approved-capabilities.yaml` — capability ceilings + tool runtime refs
- `docs/03-engineering/policies.yaml` — schemas / guardrails / actions referenced by legs, sagas, guardrails
- `docs/03-engineering/stores.yaml` — durable + shared stores for memory / checkpoints
- `docs/03-engineering/evals/` — the (generated) index, waivers, and per-target specs

## What HITL does *not* ship

No runtime, message broker, durable-execution engine, live dashboard, or eval runner — those are the product's
runtime, which the surface governs but never provides (governs-not-runtime). See
[`docs/design/agentic-core-scope.md`](../design/agentic-core-scope.md) for the core-vs-deferred boundary.
