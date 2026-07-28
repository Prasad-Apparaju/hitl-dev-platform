# First Pass — Low-Level Design

> Status: **IMPLEMENTED, v1 (2026-07-27)** — realized in `ci/first-pass/` (validator + lib) + `ai/shared/first-pass/` (prose), hardened across 4 adversarial rounds (see §11). Implements HLD [`01-design.md`](01-design.md) + ADRs [`02-adrs.md`](02-adrs.md)
> for FR-29. Every schema/table here traces to a CR in [`../../01-product/first-pass/requirements.md`](../../01-product/first-pass/requirements.md).

## 1. Scope

Concrete design for: the step-criticality field (§2) and its assignment (§3), the skip-record and ledger
schemas (§4), the starter registry (§5), the resurfacing engine (§6), the floor↔waiver bridge (§7), brief
mode (§8), the permission policy (§9), the driver flow (§10), and lints (§11).

## 2. Step criticality in `workflows.yaml` (ADR-2)

Each step gains a `crit`; where criticality differs by tier, a compact `crit_by_tier` overrides it (keys are
tiers, value is the effective criticality at that tier **and above** until the next key). Both stay on the
single-line flow-map so the awk breadcrumb parser is untouched (it reads only `n/key/label/status/phase`).

```yaml
# ai/shared/workflows.yaml — additive fields (examples)
- { n: 4,  key: roi,          label: "ROI",     phase: "Design", crit: ceremony }
- { n: 7,  key: test_plan,    label: "Tests",   phase: "Design", crit: standard }
- { n: 28, key: deploy,       label: "Deploy",  phase: "Ship",   crit: floor }
- { n: 19a, key: arch_review, label: "ArchRvw", phase: "Verify", crit: standard, crit_by_tier: { 3: floor } }
```

- `crit`: `ceremony | standard | floor`. **Default `standard`** when omitted (back-compat).
- `crit_by_tier`: optional `{ <tier>: <crit> }`; the effective criticality is the highest-tier key ≤ the
  change's tier, else `crit`. Resolved once at plan time and cached on the change's `steps[]` note (not needed
  by the parser).
- `no_omit: true` (optional): the step **may be thinned to a `starter` but never deferred or declined** — it
  cannot be fully omitted. Used for the TDD steps (RED/GREEN): First Pass may thin the test-first discipline to
  one happy-path case, but never drop "prove it runs." `no_omit` restricts the disposition menu (§10) to
  `do-now | starter`; it is independent of `crit`.
- `resolve_crit(step, tier)` → the effective criticality (LLD §11 lints its monotonicity: criticality may only
  rise with tier, never fall).

## 3. Proposed criticality assignment — the 31-step `development` workflow

Effective criticality by tier. **`floor` cells are the protected set** (skippable only via §7). This is the
**proposed default for review** — the exact assignment is a design decision the architect/TA confirms.

| # | key | ceremony/standard/floor | Floor when | Rationale |
|---|-----|---|---|---|
| 1 | issue | standard | — | the anchor; a skip is a headless change (allowed, recorded) |
| 2 | figma | ceremony | — | mockups; often N/A |
| 3 | impact | standard | T3 | cross-domain blast radius must be understood at T3 |
| 4 | roi | ceremony | — | justification; self-evident for many v1s |
| 5 | docs | standard | — | starter = skeleton design (§5) |
| 6 | iac | standard | T2 (if infra touched) | infra changes are load-bearing when present |
| 7 | test_plan | standard | — | starter = skeleton |
| 8 | training | ceremony | — | enablement |
| 9 | packet | standard | T3 | the decision-packet approval gate |
| 10 | red | standard · **`no_omit`** | — | TDD-as-design cornerstone: **starter-only** (one happy-path test now; edge cases deferred) — never fully skipped |
| 11 | test_review | ceremony | — | — |
| 12 | design_plus | standard | — | — |
| 13 | verify_red | standard | — | — |
| 14 | green | standard · **`no_omit`** | — | **starter-only**: "a working system" must prove it runs — thinnable to the happy path, never dropped |
| 15 | verify_green | standard | — | — |
| 16 | refactor | ceremony | — | — |
| 17 | conventions | standard | — | convention gate |
| 18 | review1 | standard | — | — |
| 19 | review2 | standard | — | — |
| 19a | arch_review | standard | T3 | architecture review is load-bearing at T3 |
| — | security_review | standard | T3 (required), T2 (recommended) | STRIDE/SAST; **floor at T3** (maps to a hard gate) |
| 20 | rerun | standard | — | — |
| 21 | reconcile | standard | — | — |
| 22 | qa_verify | standard | T3 | QA sign-off load-bearing at T3 |
| 23 | impact_brief | ceremony | — | downstream note |
| 24 | rollout | standard | T3 | rollout/rollback plan for risky deploys |
| 25 | verify_pr | standard | — | — |
| 26 | integration_verify | standard | T2 | integration proof |
| 27 | figma_compare | ceremony | — | — |
| 28 | deploy | **floor** | T1+ | irreversible-ops (backup/migrate/deploy) — always deliberate |
| 29 | promote | **floor** | T1+ | promotion/rollback — irreversible |
| 30 | roi_30 | ceremony | — | post-ship measurement |
| 31 | roi_90 | ceremony | — | post-ship measurement |

Also always-floor regardless of workflow position: the **fail-closed validators** (`ci/manifest-agentic`,
`ci/manifest-drift`) and **backup-before-migrate** — a First Pass run never removes these; skipping one is a §7
floor skip linked to a waiver.

## 4. Skip record + ledger (ADR-3, CR-3/CR-6/CR-10)

**Shared skip-record schema** (also used by FR-28; one dialect):

```yaml
# one skip entry
step: roi                     # workflow step key (or an FR-28 control id)
crit: ceremony                # resolved criticality
actor: "pm@team"              # who chose (CR-11)
reason: "internal tool; ROI self-evident for v1"   # neutral, required, non-empty
ts: "2026-07-27T10:00:00Z"
disposition: decline          # defer | decline | starter   (CR-6)
followup_ref: null            # issue ref, set when disposition=defer (CR-7)
starter_artifact: null        # path to the needs-enhancement artifact, when disposition=starter (CR-13)
waiver_ref: null              # waiver id, required when crit=floor and the step maps to a hard gate (CR-4)
ack_by: null                  # accountable role, required when crit=floor (CR-5)
resolved: false               # flipped true when the follow-up/enhancement lands
```

**Per-change ledger** — added to `.hitl/current-change.yaml`:

```yaml
first_pass: true              # this change is running in First Pass
skips:
  - { step: roi, crit: ceremony, actor: "pm@team", reason: "internal tool; ROI self-evident", ts: "…", disposition: decline, resolved: false }
  - { step: test_plan, crit: standard, actor: "pm@team", reason: "thin v1", ts: "…", disposition: starter, starter_artifact: "docs/.../test-plan.md", resolved: false }
```

Corresponding `workflow.steps[]` entries get `status: skipped` (ADR-8), e.g.
`- { n: 4, key: roi, label: "ROI", status: skipped, phase: "Design" }`.

**Project roll-up** — `.hitl/skip-ledger.yaml`, appended on each skip, for cross-change referability (CR-10):

```yaml
schema_version: "1.0"
entries:
  - { change_id: "GH-123", step: roi, crit: ceremony, disposition: decline, domains: [billing], paths: ["src/billing/"], ts: "…", resolved: false }
```

`domains`/`paths` are copied from the change so the resurfacing engine (§6.2) can match a later change to a
prior skip.

### 4.1 Breadcrumb rendering (yes — the breadcrumb reflects First Pass)

The breadcrumb always shows the **whole** plan (First Pass never hides steps), with skipped/starter steps
visibly distinct — so the trail *is* the First Pass shape at a glance.

- **Glyphs:** `✓` done · `▶` current · `·` open · `⊘` skipped (defer/decline) · `◐` starter (minimal produced,
  needs-enhancement). Only `status` drives the glyph, so the awk parser (`hooks/_steps.sh`) gains two
  glyph mappings and nothing else (ADR-8).
- **Current pointer:** advances **past** `skipped`/`starter` steps — they are not open work for this change, so
  the `▶` never lands on one.
- **Progress:** the denominator stays the full plan (the whole remains visible); "addressed" = done + starter +
  skipped. A Tier-2 change that thinned ROI/Figma/training and started the test plan renders, e.g.,
  `… ✓Impact ⊘ROI ◐Tests ▶RED …` — the reader sees exactly what was lightened, inline.
- **Later resolution:** when a starter is enhanced or a deferred step is completed (on the follow-up), its glyph
  flips `◐`/`⊘` → `✓` and the ledger entry's `resolved` flips true (§6, §11 keeps them consistent).

## 5. Starter registry (ADR-6, CR-13)

A curated map: step key → the *honest-minimal* starter and its marker. Steps not listed offer only
defer/decline.

| step | starter (honest-minimal) | marker |
|---|---|---|
| acceptance criteria (in issue/packet) | the single criterion **"a working version of the system exists and runs"** | `needs-enhancement: behavioral + edge-case criteria` |
| test_plan | a skeleton: one happy-path case per component + a TODO list of edge cases | `needs-enhancement` |
| docs | a design stub: headings + the decisions already made, gaps marked | `needs-enhancement` |
| impact | the domains/paths touched (mechanically derivable) without full downstream analysis | `needs-enhancement` |
| rollout | "deploy + manual rollback via redeploy previous" as the minimal plan | `needs-enhancement` |

Every starter artifact is written with the marker header and is recorded as `disposition: starter` with a
`starter_artifact` path; its enhancement is a fast-follow (§6.1). A starter is **never** presented as complete
(ADR-6).

## 6. Resurfacing engine (ADR-5, CR-8/CR-9)

Three triggers, escalating by criticality; persuade at boundaries, never mid-build.

### 6.1 At the follow-up ticket (defer + starter)
On defer/starter, seed (or link) a follow-up issue whose body embeds the skip record and, for a starter, links
the `needs-enhancement` artifact. Title/body use neutral language (§6.3).

### 6.2 At the next change touching the same area
When `dev-start-change` initializes a new change, it reads `.hitl/skip-ledger.yaml` and surfaces any **unresolved**
entry whose `domains ∩ new.domains ≠ ∅` **or** `paths ∩ new.changed_paths ≠ ∅`. v1 overlap = manifest-domain or
path-prefix intersection (semantic overlap deferred, HLD §8). Escalation:
- `ceremony`: not resurfaced here (surfaced only at its follow-up).
- `standard`: a gentle one-line reminder ("heads-up — X was thinned here last time; want to fold the
  enhancement into this change?").
- `floor`: a clear reminder plus the waiver's revisit date.

### 6.3 At incident / postmortem
The incident skill queries the ledger for the affected domains/paths and lists what was skipped there, with
actor/reason/date — factual, non-blaming — so a review can weigh it. This is where "refer back to convince"
lands hardest, still politely.

**Language (CR-9).** Record voice is neutral ("Recorded: ROI skipped for GH-123 — reason: internal tool.").
Resurfacing voice is respectful-persuasive, never blaming ("When you last changed billing you deferred the
security review; given this change touches auth, it may be worth doing now — happy to scope it."). Templates
live in a `first-pass/language.md` companion; they reconcile with `challenge-stance.md` (surface the risk,
respect the choice; no shame).

## 7. Floor + waiver bridge (ADR-4, CR-4/CR-5/CR-11)

Skipping a `floor` step:
1. The driver refuses the light path and requires the **accountable role** for that step (`ack_by`) —
   resolved from a role map: security_review → security/TA; deploy/promote → ops/TA; validators → architect/TA.
2. It captures a **risk-accepted** `reason` from that role.
3. If the step maps to a **fail-closed gate**, it requires (or offers to author) a linked **waiver** in the
   existing mechanism (`ci/manifest-agentic/manifest-waivers.yaml` or the relevant gate's waiver) and records
   `waiver_ref`. The skip records the *choice*; the waiver grants the *gate exception* (they are linked, never
   merged).
4. Without both `ack_by` and (where applicable) `waiver_ref`, the floor step **cannot** be marked skipped.

## 8. Brief mode (CR-14)

A `first_pass: true` change puts the driver in brief mode: no restating the plan it is about to run, no
re-asking an answered question, one-line confirmations, and it surfaces only decisions and the record kept.
Dispositions are collected through the **single menu** (§10.1) — one pass, not a step-by-step interview.
Implemented as an interaction directive in the skill (not new tooling). Brief mode does not apply to the
resurfacing voice at boundaries (which is allowed to persuade).

## 9. Permission policy (ADR-7, CR-15)

First Pass sets a scoped policy, not `bypassPermissions`:

- **Auto-allow (no prompt):** reads anywhere in the project working tree; edits to files **within the change's
  scope** (declared domain / project subtree); running the project's own tests/build.
- **Always prompt (critical-action list):** any write/delete **outside** the project root or the change's
  declared domain; `git push --force`; deploy/promote/migrate commands; external network sends; secret /
  credential access; destructive DB operations; anything the domain-boundary hook flags as out-of-scope.

Scope is the change's declared manifest domain + the project root; detection reuses the existing
`check-domain-boundary.sh` hook. The critical-action list is maintained in `first-pass/permissions.md` and maps
onto Claude Code permission modes + allow/deny lists (exact mapping is an open boundary — HLD §8).

## 10. Driver flow

### 10.1 The disposition menu (CR-14 — one interaction, not 31 questions)

First Pass presents the whole plan **once**, as a single **menu**, and collects every disposition in one pass
(brief mode; no step-by-step interrogation). It is rendered via the host's menu / multi-select affordance
(e.g. an `AskUserQuestion`-style selector, or a numbered text menu when that is unavailable). Each step's
**allowed options are constrained** by its `crit` and `no_omit`:

| step type | menu options offered |
|---|---|
| `ceremony` | **keep** · starter* · skip (defer / decline) |
| `standard` | **keep** · starter* · defer · decline |
| `standard` + `no_omit` (TDD) | **keep** · starter — *no defer/decline* |
| `floor` | **keep** · *request risk-accepted skip* → routes to §7 (accountable-role ack + waiver) |

*starter offered only when the step is in the starter registry (§5). `keep` is always the pre-selected default,
so doing nothing runs the full plan (CR-1).*

Example (Tier 2), grouped by criticality so the floor is visually set apart:

```
First Pass — how should each step run? (default = keep)
  Ceremony      2 Figma [keep]   4 ROI [keep]   8 Training [keep]   23 Impact-brief [keep]
  Standard      5 Docs [keep]    7 Test plan [keep]   3 Impact [keep]   24 Rollout [keep]
  TDD           10 RED [keep]    14 GREEN [keep]        (starter-only)
  Floor         28 Deploy [keep] 29 Promote [keep]      (skip needs risk-accept)
Reply with changes, e.g.  "4 skip, 7 starter, 10 starter"
```

### 10.2 Sequence

```
determine plan (tiered)  ──► annotate each step with resolve_crit(step, tier) + no_omit
present the disposition MENU once (§10.1); collect all choices in one pass
for each step the team lightened:
    validate the choice is allowed for that step's crit/no_omit
    if crit == floor:                      # §7
        require ack_by (accountable role) + reason
        if maps-to-hard-gate: require/author waiver_ref
    write skip entry (per-change ledger + roll-up)   # §4, never silent
    set steps[].status = skipped | starter           # §4.1 breadcrumb
    if disposition == starter: generate from registry (§5), mark needs-enhancement
    if disposition in (defer, starter): seed/link follow-up ticket (§6.1)
proceed to build (kept steps run as today; brief mode + permission policy on)
```

## 11. Validator findings — the fail-closed set (`ci/first-pass/check_skips.py`)

Table-driven, FR-28-style. **Exit 2 on any non-waivable finding; exit 0 only when genuinely clean; and the CLI
NEVER tracebacks** — any residual exception on hostile input becomes a `MALFORMED` block (`run()` catches it),
so a caller that treats only exit-2 as a block fails **closed**. The load-bearing rule learned across four
adversarial rounds: **a mismatched/typo'd/wrong-type input must fail closed, never coerce to a safe default.**

**Non-waivable (the guarantee):**

| finding | fires when | CR |
|---|---|---|
| `SILENT_SKIP` | a `skipped`/`starter` step has no record, or a record has empty actor/reason/invalid disposition | CR-3 |
| `FLOOR_NO_ACK` | a `floor` skip has no accountable-role `ack_by` | CR-5 |
| `FLOOR_NO_WAIVER` | a `floor` skip on a **hard-gate** step (conventions/qa_verify/arch_review/integration_verify/iac/security_review/sec_design/cve_audit/pentest/manifest_validate) has no `waiver_ref` — deploy/promote are irreversible-**ops** floor, ack-only, no gate to waive | CR-4 |
| `NO_OMIT` | a `no_omit` step (TDD RED/GREEN) is defer/decline rather than starter | CR-6 |
| `UNKNOWN_STEP` | a skip's step key is not in the catalog (a typo/whitespace/case must not resolve to `standard`) | — |
| `INVALID_STATUS` | a step status is outside the closed enum {done,current,open,skipped,starter} (a bogus status can't hide a silent floor skip) | — |
| `INVALID_TIER` | `tier` is not an int in 0..4 (a string/bool must not default to 2 and dodge a tier-3 floor); criticality is then evaluated at the strictest tier | — |
| `MALFORMED` | a present-but-wrong-type `workflow`/`steps`/`skips`, a non-string/duplicate step key, a duplicate YAML key, or any parse/validation crash | — |
| `CRIT_MONOTONIC` | a catalog `crit_by_tier` lowers criticality as tier rises (`resolve_crit` is also monotonic-safe by construction, so a bad catalog can never lower a floor at runtime) | — |
| `INCOMPLETE_PLAN` | a load-bearing step (`floor` at this tier, or `no_omit`) is **missing from the plan entirely** — deleting it instead of skipping it left no status/record to inspect (codex-1) | — |
| `STARTER_MARK` | a `starter` artifact is missing / unreadable / not marked `needs-enhancement` on its own line — an unmarked stub presented as complete is the fabricated-artifact ADR-6 forbids (codex-4) | CR-13 |

**`first_pass` is type-strict:** a present-but-non-bool value (`[]`, `0`, `""`) is `MALFORMED` **and** enforces —
it is never read as an intentional `false` (codex-2). Every step must carry a **recognized string status**;
missing/null is `INVALID_STATUS` (codex-3).

**Waivable (surfaced, not blocking):** `LEDGER_STEPS` (ledger↔steps inconsistency), `ROLLUP` (a per-change skip
missing from the auxiliary `.hitl/skip-ledger.yaml`, or a malformed roll-up — resurfacing degraded, change not
blocked), `DEFER_NO_FOLLOWUP` (a deferred step with no linked fast-follow).

**Permission classifier** (`ci/first-pass/permissions.py`, §9) and the **resurfacing voice**
(`ci/first-pass/resurface.py`, §6) were hardened in the same rounds: reads/edits auto-allow only within the
project/scope (absolute — incl. Windows drive-letter/UNC — and `..`-escaping paths always prompt); blame words
in a user-supplied `reason` are redacted from the reminder (CR-9).
