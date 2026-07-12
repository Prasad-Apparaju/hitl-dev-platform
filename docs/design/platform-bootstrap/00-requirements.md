# Platform Bootstrap: Requirements

> Design package for plugin issue #21 (platform-bootstrap workflow: the onboarding to
> customer-delivery bridge). Status: **draft, decisions open**. See `01-design.md` for the
> proposed mechanism and the open decisions list.

## 1. Problem

HITL codifies the SDLC's control plane (change governance: the development spine, gates,
breadcrumbs) and the per-change execution of its capability plane (the `ops-*` skill family).
It does not codify **platform standup**: the sequenced work that takes a project from
"onboarded" to "a change can actually be verified, delivered, and operated."

Every ops skill is a per-change executor that assumes the platform exists:

- `ops-deploy` deploys "a verified build artifact to a target environment following the
  approved rollout plan"
- `ops-apply-iac` applies "changes defined in the IaC plan"
- `ops-setup-observability` wires go/no-go criteria to instruments, and (per
  `start-from-prd`'s own wording) "requires the tools provisioned here to already exist"

Nothing creates the first environment, the first pipeline, the first deploy path, or the
first dashboard stack as tracked, gated work.

### The promise mismatch

The shipped surface reads as delivery-complete:

- README workflow spine ends at "canary deploy"; the role table ships 12+ ops skills
- The marketplace entry sells "the full 31-step delivery workflow"
- The PRD's Out of Scope section (§9) fences the paid governance layer and tool
  integrations, but does **not** fence platform standup

So a team adopting HITL on a fresh project reasonably expects the workflow to carry them to
a working deploy, and instead hits an uncodified gap between onboarding and step `rollout`
of the spine.

### Field evidence

A production consolidation project (8 source repos) completed the 11-step brownfield
onboarding cleanly, then hand-rolled everything between "onboarded" and "can deliver": an
engineering-foundations roadmap issue written manually, CI keystone, test backfill, CD
slices. Each hand-rolled piece maps to a filed gap (#16 manifest truth-invariant, #17 epic
breakdown, #18 product spine, #19 docs governance) with this bridge as the remaining
skeleton (#21).

## 2. Audit of the shipped surface (verified 2026-07-11)

Claim-by-claim verification of #21 against the repo:

| Claim | Verdict | Evidence |
|---|---|---|
| ops skills assume an existing platform | **Accurate** | All 14 `ops-*` skill descriptions; `start-from-prd` concedes it explicitly |
| No workflow codifies platform standup | **Accurate** | Catalog has 6 workflows; `prd` (greenfield) = 4 governance steps; nothing between onboarding and the per-change spine is a tracked step |
| Migration lacks parity verification and cutover/decommission | **Accurate** | `migration` = 9 intake steps ending at `confirm_ready`; the spine ends at `promote`/ROI; no golden-dataset, shadow-run, cutover, rollback-to-legacy, or sunset step exists anywhere |
| "Nothing creates the first environment/pipeline" | **Overstated** | Brownfield step `verify_pipeline` (tracked) verifies the pipeline and offers to scaffold a starter CI/CD config; step `observability` sets up agentic observability and surveys application observability; `start-from-prd` closes with a prose checklist covering CI/CD + staging + observability provisioning |

The correction does not rescue the situation, for two reasons:

1. **The greenfield guidance is untracked prose.** It lives in the closing output message of
   `start-from-prd`, after the tracked workflow ends: no breadcrumb, no gate, no evidence,
   nothing that notices if the team skips it. Unenforced prose guidance is exactly the
   failure mode HITL exists to eliminate; by HITL's own standard this is "not covered."
   (The checklist also contains a duplicate item number, which is what untracked prose does.)
2. **The brownfield findings are not persisted.** Steps 5-6 verify and survey, then *say*
   the findings in conversation (a gap table is displayed, not written). There is no
   machine-readable record to derive a roadmap from, which is why the field project wrote
   its roadmap issue by hand. #21's proposal "derive the bootstrap phases from the recorded
   gap registers" assumes a persistence layer that does not exist yet in the product.

## 3. The layer model (from #21, adopted)

A change can be **made** after layer C; it can be **delivered to customers** only after F.

| Layer | Content | Today |
|---|---|---|
| A. Understand & record | code map, manifest, working contract, as-built docs with honest gaps | Covered (brownfield 11-step; thinner on greenfield/migration) |
| B. Product spine | PRD baseline + intake path | Shell shipped in 2.0 (#18); as-built backfill still open |
| C. Change governance | HITL workflow + CI (build/secret-scan/tests) + merge enforcement | Covered for the workflow; CI standup is partial (enforcement scripts copied by `init-project.sh`, workflow templates in `ci/workflows/`, scaffold offer in brownfield step 5) |
| D. Verification | tier test suites that can fail; E2E against a real environment; test-to-FR traceability | Not codified |
| E. Delivery | reproducible builds; full-system deploy playbook per environment (order, dependencies, rollback) executed from CI | Not codified (greenfield prose only) |
| F. Safe operation | observability established and verified; progressive release exercised once end-to-end; security posture settled | Not codified (survey + flag only; agentic observability is set up) |

Migration adds two phases of its own: **parity verification** (between D and E: the
migration's "tests pass" is "output of new == output of legacy") and **cutover &
decommission** (after F: traffic switch, dual-run window, rollback-to-legacy including data
written to the target during the window, legacy sunset).

## 4. Goals

1. **Codify the bridge as tracked, gated work.** A platform workflow whose phases map to
   layers D-F (plus the migration-only phases), entered from all three entry points.
2. **Persist the findings.** Onboarding steps write machine-readable readiness records, not
   conversation tables. This is the write-side prerequisite for everything else.
3. **Derive, don't hand-maintain.** The roadmap is generated from artifacts the entry
   workflows already produce: brownfield readiness records, greenfield PRD NFRs + HLD
   deployment view, migration source analysis + external-docs review. (Same principle that
   generated the command map in 2.0 and that the durable-core design thread locked.)
4. **Feed, don't replace.** Each roadmap item executes as an ordinary HITL change through
   the existing spine. The bridge sequences work; it does not invent a second delivery
   mechanism.
5. **Make "ready for customer delivery" checkable.** A Definition of Ready that the deploy
   path can gate on, with recorded waivers for accepted gaps (reusing the tiered-waiver
   pattern locked in 2.0).
6. **Close the migration back half.** Parity and cutover/decommission become tracked steps.
7. **Promote the greenfield prose checklist** into the tracked workflow (and fix its rot).

## 5. Constraints

- **Additive only** for the change-file schema (locked in 2.0: `n` kept, fields added).
- **Numberless catalog** is the single source; the platform workflow is encoded there and
  derived like every other workflow (keys, phases, labels; `verify` must stay lossless).
- **Command coverage explicit**: every step carries `command:` (skill, `manual`, or
  `guided`) per the catalog rule.
- **Reuse existing mechanisms**: conditional steps (`cond:`), tiered waivers, the
  registries pattern, the breadcrumb ribbon. No new orthogonal machinery.
- **HITL guides and executes with approval; it does not own infrastructure.** Skills
  scaffold configs, run plans, and verify outcomes with operator confirmation (the
  `ops-apply-iac` model). No cloud-provider opinions baked into the workflow.
- **Tier-proportionate**: a solo Tier-0 project must not drown in platform ceremony;
  accepted-gap waivers must be first-class, not an afterthought.

## 6. Non-goals

- Automated infrastructure provisioning without operator approval.
- A hosted or managed platform offering (that is the paid-layer bet, out of scope per PRD §9).
- Epic/slice tracking (#17) and manifest truth-invariant (#16 gaps 2-3): related, separately
  tracked. The readiness register borrows their "derived + verified" principle but does not
  depend on them.
- Backfilling an as-built PRD (#18's deferred half).

## 7. Success criteria

1. A fresh greenfield project reaches its first verified staging deploy with every platform
   step tracked in the breadcrumb and zero hand-written process documents.
2. Brownfield onboarding produces a machine-readable readiness register and a generated
   roadmap; the field project's hand-written roadmap issue could have been generated.
3. A migration can be driven to "legacy decommissioned" entirely through tracked steps,
   including a rollback-to-legacy plan that addresses data written during the dual-run window.
4. The first Tier 2+ production deploy on a project is blocked (or explicitly waived with a
   recorded owner) until the Definition of Ready is satisfied.
5. The catalog `verify` stays lossless; the breadcrumb matrix covers the platform workflow;
   skill-lint passes on all new/changed skills.
6. `start-from-prd`'s closing prose checklist is gone, replaced by tracked steps.
