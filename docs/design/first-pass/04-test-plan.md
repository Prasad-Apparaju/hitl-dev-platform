# First Pass — Test Plan

> Status: **draft, v1 (2026-07-27)** — conformance for FR-29. Verifies the HLD [`01-design.md`](01-design.md) /
> ADRs [`02-adrs.md`](02-adrs.md) / LLD [`03-lld.md`](03-lld.md) against the requirements
> [`../../01-product/first-pass/requirements.md`](../../01-product/first-pass/requirements.md).
> Discipline (session lesson from #10/#35): **verify by running and by mutating inputs** — a green happy path is
> not enough; the fail-closed cases below must actually *fail* the guard.

## 0. What must be impossible (the fail-closed core)

These are the load-bearing negatives — each must be **caught**, not silently accepted. They mirror FR-28's
`validate_skips` / #10's fail-closed validators.

| ID | Adversarial input | Required outcome |
|----|-------------------|------------------|
| **NEG-1** | a step with `status: skipped` and **no** ledger entry | FAIL — no silent skip (CR-3) |
| **NEG-2** | a ledger entry with empty/absent `actor` or `reason` | FAIL — record must be complete (CR-3) |
| **NEG-3** | a `floor` step skipped with **no** `ack_by` | FAIL — floor needs accountable-role ack (CR-5) |
| **NEG-4** | a `floor` step mapping to a hard gate skipped with **no** `waiver_ref` | FAIL — skip ≠ waiver (CR-4) |
| **NEG-5** | a `no_omit` step (RED/GREEN) with disposition `defer` or `decline` | FAIL — starter-only (CR-6) |
| **NEG-6** | a `disposition: starter` artifact with **no** `needs-enhancement` marker | FAIL — never present a stub as complete (CR-13) |
| **NEG-7** | a ledger `step` with no matching `steps[]` entry (or a `skipped`/`starter` step absent from the ledger) | FAIL — ledger ↔ steps consistency (ADR-8) |
| **NEG-8** | a `crit_by_tier` that **lowers** criticality as tier rises | FAIL — monotonicity lint (LLD §11) |
| **NEG-9** | a per-change skip missing from `.hitl/skip-ledger.yaml` roll-up | FAIL — roll-up integrity (CR-10) |
| **NEG-10** | a permission policy that auto-allows a critical action (deploy / out-of-scope write / force-push) | FAIL — critical-only (CR-15) |

`NEG-1`, `NEG-3`, `NEG-4`, `NEG-5` are **non-waivable** (they are the framework's guarantee under First Pass).

## 1. Criticality resolution (CR-2)

- **CRIT-1** `resolve_crit(step, tier)` returns `crit` when no `crit_by_tier`; the highest-tier key ≤ tier otherwise.
- **CRIT-2** a step with no `crit` resolves to `standard` (back-compat default).
- **CRIT-3** deploy/promote resolve `floor` at every tier; security_review/arch_review/qa_verify resolve `floor` at Tier 3; `ceremony` steps stay `ceremony` at all tiers.
- **CRIT-4** determinism: the same (plan, tier) yields byte-identical criticality annotations.

## 2. Skip record + ledger (CR-3, CR-6, CR-10)

- **SKIP-1** every disposition (defer/decline/starter) writes an entry with `step, crit, actor, reason, ts, disposition`.
- **SKIP-2** disposition enum is exactly {defer, decline, starter}; anything else is rejected.
- **SKIP-3** a declined step can be re-opened; a starter can be marked enhanced (`resolved: true`) — state transitions recorded.
- **SKIP-4** the shared schema round-trips for both an FR-29 step-skip and an FR-28 control-skip (one dialect, ADR-3).

## 3. Floor + waiver (CR-4, CR-5, CR-11)

- **FLOOR-1** skipping a floor step requires `ack_by` = the mapped accountable role; a wrong/absent role is rejected (NEG-3).
- **FLOOR-2** a floor step mapping to a hard gate requires a resolvable `waiver_ref`; the waiver exists in the existing waiver file (NEG-4).
- **FLOOR-3** the skip record and the waiver stay **linked, not merged** — the waiver grants the gate exception; the skip records the choice.
- **FLOOR-4** authority: a `ceremony`/`standard` skip needs no special role; a floor skip by a non-accountable actor is rejected.

## 4. no_omit / TDD (CR-6)

- **NOOMIT-1** RED/GREEN offer only {keep, starter} in the menu; {defer, decline} are absent (NEG-5).
- **NOOMIT-2** a starter for RED/GREEN produces at least one happy-path test and marks edge cases deferred.

## 5. Starter registry (CR-13)

- **STARTER-1** the acceptance-criteria starter is exactly the single criterion "a working version of the system exists and runs" — never fabricated detailed criteria.
- **STARTER-2** every starter artifact carries the `needs-enhancement` marker (NEG-6) and is recorded with a `starter_artifact` path.
- **STARTER-3** a step not in the registry offers no starter option (falls back to defer/decline; or keep/– for no_omit).

## 6. Resurfacing (CR-7, CR-8, CR-9)

- **RESURF-1** a deferred/starter step seeds/links a follow-up ticket embedding the skip record.
- **RESURF-2** a new change whose `domains ∩ prior.domains ≠ ∅` **or** `paths ∩ prior.paths ≠ ∅` surfaces the unresolved prior skip; a non-overlapping change surfaces nothing.
- **RESURF-3** escalation: `ceremony` not resurfaced at next-change; `standard` gentle; `floor` clear + waiver revisit date.
- **RESURF-4** language: record voice is neutral; resurfacing voice is respectful-persuasive and contains no blaming/shaming tokens (lint against a denylist).
- **RESURF-5** no resurfacing fires mid-build (execution phase) — only at follow-up / next-change / incident (ADR-5).
- **RESURF-6** the incident skill lists exactly the skips for the affected domains/paths with actor/reason/date.

## 7. Permissions (CR-15)

- **PERM-1** in-scope reads/edits (project tree / declared domain) auto-allow (no prompt) under `first_pass: true`.
- **PERM-2** each critical action (out-of-scope write, delete outside scope, deploy/promote/migrate, external send, force-push, secret access) still prompts (NEG-10).
- **PERM-3** First Pass never selects `bypassPermissions`; scope is resolved via the existing domain-boundary hook.

## 8. Breadcrumb (CR-16)

- **BREAD-1** `skipped` renders `⊘`, `starter` renders `◐`, alongside `✓ ▶ ·`; the awk parser handles the two new statuses.
- **BREAD-2** the whole plan is shown (no step hidden); the `▶` current pointer never lands on a skipped/starter step.
- **BREAD-3** a starter/deferral marked resolved flips its glyph to `✓`.

## 9. Menu (CR-14)

- **MENU-1** the menu is presented once and collects all dispositions in a single pass (no per-step interview).
- **MENU-2** each step's offered options match its `crit`/`no_omit` (ceremony=all, standard=all, no_omit=keep/starter, floor=keep/risk-accept).
- **MENU-3** `keep` is the default; an empty reply runs the full plan (CR-1) with no ledger entries.

## 10. Back-compat + brief mode (CR-1, CR-14)

- **COMPAT-1** a change without `first_pass` validates and renders exactly as today (all steps `open/done/current`, no ledger).
- **COMPAT-2** a legacy `workflows.yaml` step with no `crit` is treated as `standard`; nothing breaks.
- **COMPAT-3** brief mode emits no plan-restatement and does not re-ask an answered question (interaction lint / transcript check).

## 11. How these run

- The validator/lint tests (§0–§5, §8, §11) run as a table-driven Python suite under `ci/first-pass/`, in the
  FR-28 validator style (fail-closed; NEG-* asserted by mutation, not just happy-path).
- Skill-behavior tests (menu, brief mode, resurfacing voice, permissions) run as scripted-transcript / fixture
  checks; where a behavior can be reduced to a pure function (overlap detection, option constraint, glyph map),
  it is unit-tested directly.
- A worked example (a Tier-2 change run in First Pass) is generated and its ledger + breadcrumb asserted
  end-to-end, mirroring the #10/#35 worked-example pattern.
