# Platform Bootstrap: Design

> Mechanism for the requirements in `00-requirements.md`. Status: **decisions locked
> 2026-07-11** (§8). Design rationale markers (R1)-(R6) preserved for the audit trail.

## 1. The two artifacts

The design separates **state** (what is true about the platform right now) from **plan**
(what work remains, in what order). State is a register; plan is a generated view of it.

### 1.1 The platform readiness register (state)

`docs/04-operations/platform-readiness.yaml` — sibling of the incident and token-cost
registries, same pattern: version-controlled, machine-readable, written by workflow steps.

```yaml
schema_version: "1.0"
project_kind: brownfield          # brownfield | greenfield | migration
layers:
  verification:                   # layer D
    items:
      - id: D1
        name: "Tier test suites runnable and failing-capable"
        status: gap               # verified | gap | accepted_gap | na
        severity: red             # red | yellow | green (from the entry survey)
        evidence: ""              # required when status: verified
        source: "brownfield step verify_pipeline, 2026-07-11"
      - id: D2
        name: "E2E suite against a real environment"
        status: gap
        # severity / evidence / source as above
  delivery: { items: [] }        # layer E — same item shape
  operation: { items: [] }       # layer F — same item shape
  parity: { items: [] }          # migration only
  cutover: { items: [] }         # migration only
delivery_ready: false             # derived: true when every non-na item is verified or accepted_gap
waivers:
  - item: F3
    tier_limit: 1                 # accepted-gap ceiling: blocks Tier 2+ until revisited
    owner: "TA"
    revisit: "2026-09-01"
    reason: "single-tenant pilot, no on-call rotation yet"
```

Rules:

- **Steps write it; humans review it in PRs** like any doc. No conversational-only findings:
  brownfield steps `verify_pipeline` and `observability` write their verdicts here instead of
  (only) displaying a table (this fixes the persistence gap named in 00 §2).
- `evidence` is required to mark an item `verified` (the required-evidence pattern from 2.0).
- `accepted_gap` requires a waiver entry with owner + revisit date (the tiered-waiver
  pattern). `delivery_ready` is **derived**, never hand-set.
- Layers A-C are not in the register: they are already covered by tracked onboarding steps
  and the change-governance machinery. The register covers exactly what is uncodified today
  (D, E, F, plus the migration-only layers).

### 1.2 The roadmap (plan) — a generated view

`/hitl:plan-platform` (new skill) reads the register plus the entry-point artifacts and
emits the roadmap: one GitHub issue per register gap (or one umbrella issue per layer for
small projects; operator chooses), each carrying acceptance criteria derived from the item
and a `platform_item: <id>` marker. The field project's hand-written roadmap issue becomes
a generated artifact (R1).

Each roadmap issue is then an **ordinary HITL change**: picked up via
`/hitl:dev-start-change`, classified onto the normal spine (most platform items are Tech
Change profile with the `infra` or `tooling` tag). Completing the change updates the
register item to `verified` with the change as evidence. The bridge feeds the existing
workflow; it does not replace it (goal 4).

## 2. The `platform` workflow (catalog encoding)

A new workflow in the numberless catalog. Its steps are **checkpoints that drive and verify
the register**, not the implementation work itself (that lives in roadmap-item changes).

```yaml
platform:
  title: "Platform Bootstrap — onboarded to delivery-ready"
  phases: [Survey, Verify, Deliver, Operate, Parity, Cutover, Ready]
  steps:
    # ── Survey ────────────────────────────────────────────────────
    - { key: derive_register,  name: "Derive Readiness Register",   label: "Register", phase: "Survey",  command: plan-platform,        role: TA }
    - { key: roadmap,          name: "Generate Roadmap",            label: "Roadmap",  phase: "Survey",  command: plan-platform,        role: TA }
    # ── Verify (layer D) ──────────────────────────────────────────
    - { key: test_suites,      name: "Tier Test Suites Stand",      label: "Suites",   phase: "Verify",  command: manual,               role: QA }
    - { key: e2e_env,          name: "E2E Against Real Environment", label: "E2E",     phase: "Verify",  command: manual,               role: QA }
    - { key: traceability,     name: "Test-to-Requirement Matrix",  label: "Trace",    phase: "Verify",  command: guided,               role: QA }
    # ── Deliver (layer E) ─────────────────────────────────────────
    - { key: build_repro,      name: "Reproducible Build",          label: "Build",    phase: "Deliver", command: ops-build,            role: Ops }
    - { key: deploy_playbook,  name: "Full-System Deploy Playbook", label: "Playbook", phase: "Deliver", command: guided,               role: Ops }
    - { key: cd_from_ci,       name: "Deploy Executed From CI",     label: "CD",       phase: "Deliver", command: manual,               role: Ops }
    # ── Operate (layer F) ─────────────────────────────────────────
    - { key: obs_established,  name: "Observability Established",   label: "Observ",   phase: "Operate", command: ops-setup-observability, role: Ops }
    - { key: canary_exercised, name: "Progressive Release Exercised", label: "Canary", phase: "Operate", command: ops-deploy,           role: Ops }
    - { key: sec_posture,      name: "Security Posture Settled",    label: "SecPos",   phase: "Operate", command: ops-pentest,          role: Ops }
    # ── Parity (migration only) ───────────────────────────────────
    - { key: golden_dataset,   name: "Golden Dataset Harness",      label: "Golden",   phase: "Parity",  cond: migration, command: guided, role: QA }
    - { key: shadow_run,       name: "Shadow/Dual-Run Comparison",  label: "Shadow",   phase: "Parity",  cond: migration, command: guided, role: Ops }
    # ── Cutover (migration only) ──────────────────────────────────
    - { key: cutover_plan,     name: "Cutover + Rollback-to-Legacy Plan", label: "CutPlan", phase: "Cutover", cond: migration, command: guided, role: Ops }
    - { key: dual_run,         name: "Dual-Run Window",             label: "DualRun",  phase: "Cutover", cond: migration, command: manual, role: Ops }
    - { key: decommission,     name: "Legacy Sunset + Archival",    label: "Sunset",   phase: "Cutover", cond: migration, command: manual, role: Ops }
    # ── Ready ─────────────────────────────────────────────────────
    - { key: delivery_ready,   name: "Definition of Ready Verified", label: "Ready",   phase: "Ready",   command: plan-platform,        role: TA }
```

Design notes:

- **The existing `cond:` mechanism** carries the migration-only phases (R2); no new
  machinery. Non-migration projects never see Parity/Cutover, exactly as `perf`/`security`/
  `upgrade` conditional steps work on the spine today.
- Steps map 1:1 onto register layers; a checkpoint step is "done" when its layer's items
  are all `verified`/`accepted_gap`/`na`. The workflow is the *sequenced view* of the
  register (dependencies encoded as step order: you cannot exercise a canary before a deploy
  path exists).
- `delivery_ready` (the final step) verifies the four-pillar Definition of Ready: docs core
  reviewed and stable; tests including E2E passing; observability established and verified;
  CI/CD stable including progressive release exercised once. Its completion flips the
  derived `delivery_ready: true` in the register.
- Rough size: 12 steps base, 17 for migration. Comparable to brownfield onboarding (11).

## 3. Entry points (derivation rules)

| Entry | Derives the register from | Wiring change |
|---|---|---|
| Brownfield | Step 5 (`verify_pipeline`) verdicts, step 6 (`observability`) survey, architect-review-existing findings | Steps 5-6 **write** the register (today: display only); `confirm_ready` offers `/hitl:plan-platform` as the recorded next action |
| Greenfield | PRD NFRs (SLOs → observability items; user tiers → environment story; compliance → security items) + the HLD deployment view from `architect-design-system` | `prd` workflow gains a 5th step `platform_roadmap` after `confirm_ready`; the closing prose checklist in `start-from-prd` is **deleted** and replaced by it (R3) |
| Migration | `source_analysis` + `ext_docs` review outputs; `project_kind: migration` activates the conditional phases | `create_issue`/`confirm_ready` seed the register; parity items derive from the source system's user-facing contracts |

In all three cases `/hitl:plan-platform` is the single generator: it reads whatever entry
artifacts exist, writes/refreshes the register, and emits the roadmap issues. Re-running it
is safe (it diffs the register, never overwrites `verified` items with survey guesses).

## 4. Execution model: long-lived, parallel to changes

The platform workflow is **per-project and long-lived**, unlike per-change workflows. It
must not occupy `.hitl/current-change.yaml`, because roadmap items themselves are ordinary
changes that need the change file (R4).

- Progress lives in the register (+ the roadmap issues), not in a change file.
- The breadcrumb/statusline shows a compact platform chip **only while
  `delivery_ready: false`** (for example `platform: Deliver 2/3`), sourced from the register.
  Once ready, the chip disappears permanently; no permanent noise (R5). This follows the
  2.0 lesson from the `unverifiable` branch marker, which was removed for being always-on.
- `/hitl:platform-status` (small read-only skill, or a `plan-platform` mode) renders the
  full ribbon on demand.

## 5. Enforcement (where the teeth are)

Reusing existing gate patterns, tier-scaled:

1. **Production-deploy gate**: `ops-deploy` pre-flight refuses a Tier 2+ **production**
   deploy while `delivery_ready: false`, unless every open item (`gap` OR `accepted_gap`)
   carries a waiver whose `tier_limit` covers the change's tier and whose revisit date has
   not passed. Staging deploys are never blocked (the platform work itself needs them).
   This is the single hard gate (R6). **Hardened 2026-07-11 across two independent
   validation rounds that found fail-open paths: the gate fails CLOSED whenever it cannot
   positively validate the register.** Round 1: no PyYAML-capable interpreter, unparseable
   YAML regardless of its text, zero items while not delivery-ready. Round 2 (schema
   depth): unknown/null item statuses block, `verified` requires non-empty evidence, and a
   waiver releases only when complete (owner + valid unlapsed ISO revisit + integer
   tier_limit covering the tier + reason); any unexpected evaluation error also blocks.
   Round 3 (identity + activation): item ids are required and unique (they are the waiver
   join key; a missing id is never a waivable "?"), `project_kind` must be valid, and a
   migration register may not leave Parity/Cutover items `na`. Round 4 (completeness):
   the canonical item set (D1-F3; P1-C3 on migrations) is required — a truncated register
   blocks — and `na` is never valid for applicable canonical items; a genuine
   "does not apply here" is a recorded waiver, not a status flip. Round 5: canonical items
   must sit in their canonical layers, duplicate waiver entries for one item block
   (last-wins is not a contract), and the plugin build's path normalizer no longer
   double-prefixes template paths (the register-creation instructions were broken in the
   installed layout — the one round-5 blocker, a build bug rather than a gate bug).
   The only deliberate allowance that remains is the missing-register exemption for
   pre-register projects.
2. **Advisory at change intake**: `dev-start-change` warns (does not block) when starting a
   Feature/Enhancement change while red items remain in layers D/E: "you can build this, but
   you cannot deliver it yet; N platform items open."
3. **Waivers are first-class**: `accepted_gap` + owner + revisit date, surfaced in
   `platform-status` and in the impact brief of any change that trips the advisory.

What is deliberately **not** enforced: no gate on layer F for Tier 0/1 projects (a solo
pilot without on-call is a waiver, not a violation), and no blocking of any non-deploy step.
The floor stays proportionate (constraint §5 of 00).

## 6. Skill surface (delta)

| Skill | Change |
|---|---|
| `plan-platform` (**new**) | Derive/refresh register, generate roadmap issues, verify Definition of Ready. The only genuinely new executor. |
| `start-brownfield` | Steps 5-6 persist verdicts to the register; closing step offers `plan-platform` |
| `start-from-prd` | Prose checklist deleted; 5th workflow step added; hands off to `plan-platform` |
| `start-migration` | Seeds `project_kind: migration`; register seeded from source analysis |
| `ops-deploy` | Pre-flight reads the register (gate §5.1) |
| `ops-setup-observability` | On first run, if register item F1 is open, points at `plan-platform` instead of failing obscurely |
| statusline/welcome hooks | Read the register for the conditional chip |

Everything else (scaffolding a pipeline, standing up dashboards, writing the deploy
playbook) is executed as roadmap-item **changes** using existing skills; no new
provisioning skills.

## 7. What this deliberately reuses

- `cond:` conditional steps (2.0) for migration-only phases
- Required-evidence + tiered-waiver patterns (2.0) for register items
- The registries pattern (incident/test/token-cost) for the register file
- Derive-don't-hand-maintain (2.0 command map; durable-core thread) for the roadmap
- The existing spine for all actual implementation work

## 8. Decisions (LOCKED 2026-07-11)

| # | Decision | Locked choice |
|---|---|---|
| D1 | Workflow name | `platform` (register and skill names read naturally: platform-readiness, plan-platform) |
| D2 | Production-deploy gate hardness | **Hard block with waivers** (§5.1). HITL's differentiator is enforcement; an advisory here recreates the untracked-prose failure this design exists to kill |
| D3 | Rollout slicing | **All three entry points in one release.** Known risk, accepted: migration parity/cutover ships without a live migration to validate against; mitigated by those steps being `guided` (ref-doc driven), revisit after first field migration |
| D4 | Roadmap granularity | Operator chooses at generation time; default umbrella-per-layer under 10 gaps, per-item above |
| D5 | Where migration phases live | In `platform` via `cond:` (§2); the migration workflow stays an intake workflow |
| D6 | Version target | 2.1.0; no schema breaks, new workflow + register are additive |

## 9. Acceptance criteria (implementation gate)

1. Catalog `verify` lossless with the new workflow; breadcrumb matrix extended to cover
   `platform` (base and migration-conditional renderings).
2. `plan-platform` generates a register + roadmap on a fixture brownfield project whose
   steps 5-6 found: broken pipeline, no staging job, no alerting. The generated roadmap
   reproduces the field project's hand-written roadmap structure.
3. `ops-deploy` pre-flight blocks a Tier 2 production deploy on that fixture, and permits it
   after items flip to `verified`/waived (pytest, following the `ci/hooks/` harness pattern).
4. `start-from-prd` contains no closing prose checklist; skill-lint passes.
5. Register YAML round-trips through the existing hook parsers without touching
   `current-change.yaml` handling (additive constraint).
