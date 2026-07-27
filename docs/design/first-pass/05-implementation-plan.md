# First Pass (FR-29) — Implementation Plan

> Status: **BUILT (Phases A–I complete), v1 (2026-07-27)** — all phases implemented on `feat/first-pass`; 4 clean-context adversarial rounds converged (r1 2 CRITICAL → r4 clean); 51 first-pass tests, breadcrumb 271, derive verify OK. Remaining: Codex validation + 2.x release. The *how-to-build* roadmap for First Pass (HLD
> [`01-design.md`](01-design.md), ADRs [`02-adrs.md`](02-adrs.md), LLD [`03-lld.md`](03-lld.md), test-plan
> [`04-test-plan.md`](04-test-plan.md)). No new design decisions — every artifact traces to an LLD §.
> Targets the 2.x line, after #22 metrics or interleaved (version TBD).

## Principles (carried from #10/#35)

- **Schema-first, validator-early.** Land the additive schema, then the fail-closed guard, before the skill
  behavior — so the guarantees are testable before anything can use them.
- **TDD per rule; verify by running and by mutating.** Each NEG-* case in the test-plan is written RED first and
  proven to fail-closed; a green happy path alone is not acceptance (the recurring #10/#35 lesson).
- **Additive + back-compat.** A change without `first_pass`, and a legacy `workflows.yaml` without `crit`,
  behave exactly as today (COMPAT-1/2 gate every phase).
- **Reuse, don't reinvent.** Converge on FR-28's skip record, #10's waivers, the existing domain-boundary hook,
  and the awk breadcrumb parser — no parallel machinery.

## Build order

```
A schema+catalog ─┬─► B validator/lints ─┬─► D starters ─┐
                  └─► C driver+menu ──────┤              ├─► H integration ─► I validation+release
                                          ├─► E resurfacing
                                          ├─► F breadcrumb
                                          └─► G permissions
```

| Phase | Sub-issue (TBD) | Deliverable | Depends | LLD | Key tests |
|-------|------|-------------|---------|-----|-----------|
| **A** | FP-1 | **Schema + catalog.** Add `crit` / `crit_by_tier` / `no_omit` to every `development` step in `ai/shared/workflows.yaml` (the §3 assignment); extend `docs/changes/change-context.schema.yaml` with `first_pass`, the `skips[]` ledger, and `status` enum values `skipped`/`starter`; define the **shared skip-record schema**. Prove additivity. | — | §2, §3, §4 | CRIT-2, COMPAT-1/2 |
| **B** | FP-2 | **Fail-closed validator + lints** `ci/first-pass/check_skips.py` — table-driven, FR-28 style: no-silent-skip, floor-integrity, no_omit, ledger↔steps, starter-marking, roll-up integrity, criticality monotonicity. NEG-1..NEG-9 non-happy-path. | A | §11, §4, §7 | **NEG-1..9**, SKIP-*, FLOOR-*, NOOMIT-1 |
| **C** | FP-3 | **Driver + disposition menu** in `dev-start-change` / `dev-practices`: present the single menu (§10.1), constrain options by crit/no_omit, collect in one pass, enforce the floor path, write the ledger + set step `status`, brief mode. | A | §8, §10 | MENU-*, COMPAT-3, SKIP-1 |
| **D** | FP-4 | **Starter registry + generators** — the honest-minimal starters (AC = "a working system"; test_plan skeleton; docs stub; impact paths; rollout minimal), each emitted with the `needs-enhancement` marker. | B, C | §5 | STARTER-1/2/3, NEG-6, NOOMIT-2 |
| **E** | FP-5 | **Resurfacing** — project roll-up read at `dev-start-change` (overlap = domain/path intersection), the incident-skill query, follow-up-ticket seeding, and `first-pass/language.md` templates (neutral record + respectful-persuasive resurfacing; reconciled with `challenge-stance.md`). | B, C | §6 | RESURF-1..6 |
| **F** | FP-6 | **Breadcrumb glyphs** — `⊘` skipped, `◐` starter in `hooks/_steps.sh` + the welcome/statusline renderers; current-pointer advances past them; resolved flips to `✓`. | A | §4.1 | BREAD-1/2/3 |
| **G** | FP-7 | **Permission policy** — `first-pass/permissions.md` (the critical-action list) + the mapping onto Claude Code permission modes / allow-deny lists; scope via the existing `check-domain-boundary.sh`. Never `bypassPermissions`. | A | §9 | PERM-1/2/3, NEG-10 |
| **H** | FP-8 | **Integration + docs.** Converge `challenge-stance.md` TODO-deferral onto the shared ledger; refactor the FR-28 Advisor skip into the shared schema (one dialect); pattern doc + a worked Tier-2 example (`docs/examples/first-pass/`); CHANGELOG. | B–G | §All | end-to-end worked-example assertions |
| **I** | FP-9 | **Validation + release.** Adversarial passes (Fable) on the validator + driver (mutate the NEG-* space), two-stage Codex (source → built plugin), then package + release on 2.x (build.sh ships `ci/first-pass` + skill + language/permissions prose the manifest-agentic way; sandbox-install verify). | H | — | full suite + fresh-install verify |

## Phase detail — the load-bearing two

**Phase A (schema + catalog)** is where the 31-step criticality assignment (LLD §3) becomes real. Risk: getting
a step's criticality wrong ships a wrong default. Mitigation: the assignment is reviewed by architect/TA as part
of this phase (it is a values call, not a mechanical one); `crit` defaults to `standard` so an un-annotated step
is never accidentally `ceremony`.

**Phase B (validator)** is the guarantee. It must be built and adversarially tested before the driver can write
a ledger anyone trusts. It reuses FR-28's `validate_skips` shape and #10's fail-closed discipline: NEG-1
(silent skip), NEG-3/4 (unauthorized floor skip), and NEG-5 (TDD omission) are **non-waivable** and asserted by
mutation, not happy path.

## Build status (2026-07-27)

**Phases A–H: DONE.** Phase A (schema+catalog: `crit`/`crit_by_tier`/`no_omit` sourced in `catalog.yaml`,
`derive.py verify` guards crit-sync; `first_pass`+`skips[]`+status glyphs in the change schema; shared
skip-record). B (`ci/first-pass/check_skips.py`, fail-closed). C (`dispositions.py` + start-change Step 4b).
D (`starters.py`). E (`resurface.py` + `language.md`). F (breadcrumb ⊘/◐ in `_steps.sh`). G (`permissions.py`
+ `permissions.md`). H (worked example `docs/examples/first-pass/` + challenge-stance convergence).

**Phase I (validation): DONE for the adversarial half.** 4 clean-context Fable rounds, CONVERGED
(r1 2 CRITICAL exit-0 bypasses → r2 no bypass → r3 core converged → r4 clean). Every finding fixed by mutation
+ locked with a regression; the fail-closed vocabulary that emerged is in test-plan §0.1 and LLD §11.
**Remaining:** two-stage Codex validation, then package + release on 2.x (build.sh ships `ci/first-pass` +
`ai/shared/first-pass` prose + the skill; version bump; sandbox-install verify) — **not yet done**. The
validator is also not yet wired into CI (`.github/`).

## Definition of done

- ✅ All test-plan families green (**51 tests**), with the NEG-* cases (incl. the hardening set §0.1) proven
  fail-closed **by mutation**; back-compat holds for non-First-Pass changes.
- ✅ A worked Tier-2 First Pass example exists (ledger + breadcrumb + starter artifact + roll-up), validates clean.
- ✅ One skip dialect (`ai/shared/skip-record.md`) shared by FR-28 + FR-29.
- ⏳ Adversarial (Fable) **done + converged**; two-stage Codex + 2.x release + CI wiring **pending**.

## Open items to resolve during build (from LLD)

- Confirm the §3 criticality assignment (architect/TA) — especially the `floor` set and the `no_omit` steps.
- The exact critical-action ↔ Claude Code permission-mode mapping (Phase G) — verify it can't be widened to
  `bypassPermissions` by accident.
- v1 overlap detection is domain + path intersection only; semantic overlap is a follow-on (HLD §8).
- Whether declined skips expire / are re-offered (requirements open question) — default v1: never expire, always
  re-surfaceable at incident.
