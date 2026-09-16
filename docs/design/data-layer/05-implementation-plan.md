# Data Layer (EPIC #131): Implementation Plan

> Status: **draft v0 (2026-09-15)**, written from
> [requirements v1](../../01-product/data-layer/requirements.md) before the rest of this design package
> exists. Phase 0 produces the HLD, ADRs, LLD and test plan, then revises this file so every phase traces
> to an LLD section, the way [first-pass/05-implementation-plan.md](../first-pass/05-implementation-plan.md)
> does. Slice 1 is planned in detail, slice 2 in outline, slices 3 to 5 as placeholders. Nothing here is
> built.

## 1. What the plan rides on (verified in the repo)

| Mechanism | Where | Used for |
|---|---|---|
| Manifest generator | `tools/generate-manifest/generator.py` | Shape of the adapters: a script that scans and writes YAML, human fields preserved across re-runs |
| Manifest drift checker | `ci/manifest-drift/check_manifest_drift.py` | Shape of the validator: exit 0/1, `--strict`, run by Conventions and by a CI workflow template |
| Validator install and update | `start-brownfield` Step 3 copy block; `dev-update --sync-validators`; `ci/shipped-validators.sha256` | Getting `ci/data-layer/` and `tools/data-layer/` into product repos and keeping them current |
| Conditional steps | `cond:` plus `engages:` predicates in `ai/shared/workflows.yaml`; `tools/workflow-catalog/derive.py verify` | The slice-2 `data_layer` step |
| Impact record | `ai/shared/templates/impact-record.schema.yaml`: `surfaces: [data]`, `data_migration`, `docs_affected` | The activator for the slice-2 step, without a new intake question |
| Authorization before an active action | `ops/pentest` Step 1b, reply **AUTHORIZED** | DL-8, before any live-store read |
| Fail-closed validator discipline | `ci/first-pass/check_skips.py`, NEG cases proven by mutation | The data-layer validator |
| Issue hygiene, skip record, plain English | `ai/shared/issue-hygiene.md`, `ai/shared/skip-record.md`, `ai/shared/plain-english.md` | Findings as tickets (DL-9), Fast Track leaving the step out (DL-11), the scorecard text |

## 2. Things the requirements assume that the repo does not yet provide

Settle these in Phase 0. Each is an ADR or a requirements amendment, not a build task.

1. **`boundary_entities` is not a generated field.** DL-6 ties the ontology to the manifest's boundary
   entities. The template `ai/shared/templates/system-manifest-template.yaml` has no such field and the
   generator emits only `entity_crossing: "DRAFT ..."` strings in the interaction matrix. Only the
   greenfield example manifest carries `domains.<d>.boundary_entities`. On a generated brownfield
   manifest DL-6 is vacuous: zero boundary entities, validator passes. Options: the generator emits a
   DRAFT `boundary_entities` block per domain; or the ontology becomes the source and the fold step
   back-fills the manifest; or DL-6 also reads the names in `entity_crossing`. Recommendation: the
   ontology is the source and Fold writes the manifest block, since the ontology has evidence and the
   generator's guess does not.
2. **DL-11 asks a new intake question; the impact record already answers it.** `surfaces: data` and
   `data_migration` exist and drive `baseline` and `sec_design` today. The step should engage on
   `{ any: [surfaces:data, data_migration] }` and ask nothing new. Keep a question only for the case the
   rules cannot see: an entity or derivation changed without a persisted-shape change.
3. **A brownfield onboarding step is a catalog change.** The `brownfield` workflow is numbered 1 to 11
   in `workflows.yaml` and mirrored in `tools/workflow-catalog/catalog.yaml`. Adding a step changes
   `total` and every open onboarding. Slice 1 therefore ships the skill standalone, pointed to from
   Step 3 and Step 7 prose. The catalog step lands with slice 2's migration.
4. **The field project's evidence cannot be the test fixture.** It is client data and this repo is
   public. Slice 1 needs a synthetic fixture: a small app with an ORM, a driver call and a nightly job,
   plus offline exports standing in for a document store and a relational database. The field project
   remains the private acceptance run the user performs.
5. **Interpret needs a model; CI cannot run it.** Extract, Fold, Validate and the scorecard are scripts
   and are tested in CI from fixture interpretations. Interpret is exercised by the skill run on the
   fixture during the validation review, and its isolation is checked mechanically (each interpretation
   declares `inputs:` and the validator rejects a citation outside them).
6. **Answerability (DL-2) needs a mechanical definition.** Proposed: a question record lists the entity,
   mapping and edge IDs it needs; it is answerable when every ID exists at a confidence other than
   `needs-review`. The model drafts the needs list at intake; a person confirms it.

Also open: the FR number (FR-30 is claimed by #105 and #118); the design package refers to DL-n until it
is settled, and the PRD row is a release precondition. The requirements branch
`issue/131-data-layer-requirements` is committed and not pushed.

## 3. Principles (carried from #10, #35, FR-29)

- **Schema first, validator early.** The six file schemas and the fixture land before any adapter, so the
  guarantees are testable before anything can write the files.
- **Every NEG case proven by mutation.** A green happy path is not acceptance.
- **Additive.** A repo with no `docs/02-design/data/` behaves exactly as today. Conventions reports the
  validator as absent, never as passed.
- **Reuse.** No new hook, gate, ledger or dialect. The drift check in slice 2 is a diff intersection run
  at Reconcile, not an edit-time hook.
- **Model-assisted, script-verified.** Anything a validator can decide, a validator decides.

## 4. Slice 1: brownfield core

### Build order

```
0 design pkg ─► A schemas + fixture ─┬─► B validator + scorecard ─┬─► D skill ─► E integration ─► F validation + release
                                     └─► C adapters ──────────────┘
```

### Phases

| Phase | Deliverable | Depends | Requirements | Key tests | Size |
|---|---|---|---|---|---|
| **0** | **Design package.** `01-design.md` (HLD: the five stages, the six files, the evidence folder, the manifest tie), `02-adrs.md` (the decisions in §2 and §7), `03-lld.md` (file schemas field by field, adapter contracts, validator rules, scorecard metrics and diff), `04-test-plan.md` (NEG families), this file revised. One validation review of the package before Phase A. | requirements merged | all DL-1..9 | review record | M |
| **A** | **Schemas + fixture.** `ai/shared/templates/data-layer/`: `sources.yaml`, `questions.yaml`, `ontology.yaml`, `mappings.yaml`, `lineage.yaml`, `findings.yaml` templates plus one `data-layer.schema.yaml` in the style of `change-context.schema.yaml` (confidence enum, evidence types, PROV edge terms, `inputs:` on interpretations). Synthetic worked example `docs/examples/data-layer/`: the small app, offline evidence exports, interpretations, the four files, a scorecard baseline, one collision, one negative finding, one declared-not-extracted source. | 0 | DL-1, DL-3, DL-5 | schema round-trips; the example validates clean | M |
| **B** | **Validator + scorecard.** `ci/data-layer/check_data_layer.py` (fail-closed, table-driven): ontology entry naming a service, job, file or endpoint; negative finding written as an edge; fourth confidence value; assertion with no evidence entry; citation outside the interpretation's declared `inputs`; boundary entity absent from the ontology; source declared-not-extracted whose dependants are not `needs-review`. `ci/data-layer/scorecard.py`: the DL-7 metrics, `--baseline` diff, answerability per DL-2, a plain-English report. `ci/workflows/data-layer-check.yml` template. | A | DL-2, DL-4, DL-5, DL-6, DL-7 | NEG-1..7 by mutation; SCORE-*; BASE-* (diff never hides a regression) | L |
| **C** | **Adapters** under `tools/data-layer/`: `intake_scan.py` (connection strings, ORM and driver configs, dbt project, DAG files, IaC, env names, proposed `sources.yaml`); `code_adapter.py` (Python first, AST: ORM entities, repository reads and writes, driver calls, joins and keys, evidence type `code`); `profile_adapter.py` (document store and relational: counts, field presence, key overlap; **offline export mode first**, live mode the same code behind a read-only fetch layer that requires an authorization record in `sources.yaml`). Every run writes `evidence/<source>/<type>-<timestamp>.yaml` and `run.log` with the access used. Optional drivers imported lazily; a missing driver is recorded as access not obtained, never a crash. | A | DL-1, DL-3, DL-8 | scan finds every fixture source; fake client asserts no write method called (AUTH-1); no authorization record, no live run (AUTH-2); missing driver recorded (SRC-1) | L |
| **D** | **Skill** `ai/claude/map-data-layer/SKILL.md`, `/hitl:dev-map-data-layer`, five stages with banners and `.hitl/current-change.yaml` step tracking as `start-brownfield` does: 1 Intake (scan, confirm, competency questions, per-source environment and **AUTHORIZED** reply before any live read); 2 Extract (scripts only); 3 Interpret (one sub-agent per entity, handed only that entity's evidence paths, writing `interpretations/<entity>.yaml` with `inputs:`); 4 Fold (a sub-agent handed interpretations only, writing the four files and the manifest `boundary_entities` block per ADR); 5 Validate (validator, scorecard, findings offered as tickets under issue hygiene, filed only on confirmation). Re-runnable per stage. Registered in `plugin.json`; passes skill-lint; report text passes the plain-English lint. | B, C | DL-1, DL-2, DL-4, DL-8, DL-9 | skill-lint; wiring test that every stage names only its inputs; plain-English on the report | L |
| **E** | **Integration.** `start-brownfield` Step 3 copies `ci/data-layer/` and `tools/data-layer/` next to the other validators and Step 7 points to the skill; `check-conventions` Step 1 runs the validator and scorecard, reporting absent as SKIPPED; `dev-update --sync-validators` and `ci/shipped-validators.sha256` cover the new files (the wiring test holds it); build script sweeps the new `shared/` paths; `help` skill entry; CHANGELOG; `docs/README.md` design row; `docs/examples/README` row. | D | DL-6, DL-7 | `ci/wiring` suite; fresh sandbox install runs the example end to end | M |
| **F** | **Validation + release.** One clean-context validation review with the acceptance scenarios 1 to 6 from requirements §8.2 as the checklist, run on the fixture in a `CLAUDE_CONFIG_DIR` sandbox, one page, no adversarial pass. Separately the user runs the skill on the field project and reports the scorecard against the hand-built baseline. Release as a minor on 2.x per `docs/releasing.md`: release change file, review records, install verify. | E | all slice 1 | full suite plus the two runs | M |

### The load-bearing two

**Phase B** is the guarantee. Until it exists nothing the skill writes can be trusted, so it is built and
mutation-tested before the skill. Rules 1 to 5 in the validator table are non-waivable; the boundary-entity
rule takes a waiver file in the `manifest-waivers.yaml` style because brownfield manifests will be wrong
before the ontology is.

**Phase D's isolation** is the mechanism the requirements took from the ontology-pipeline talk (DL-4). It
is enforced by what a stage is handed, not by prose: the skill builds each Interpret prompt from a file list,
the sub-agent has no other files named to it, the interpretation records that list as `inputs:`, and the
validator rejects any citation outside it. A wiring test reads the skill text and checks each stage names
only its own inputs, the way `test_wiring.py` checks other skills today.

### Definition of done (slice 1)

- Validator and scorecard green on the worked example; every NEG case fails closed by mutation.
- A fresh sandbox install runs `/hitl:dev-map-data-layer` on the example through all five stages, and
  Conventions reports the scorecard.
- A source declined at intake is `declared, not extracted` with its dependants `needs-review`
  (scenario 1); no live read happens before AUTHORIZED, and the run log shows read-only access
  (scenario 6).
- The field project run reports a scorecard with a verification rate, an answerability count and at least
  the synonym collision the hand pass found (scenario 5).
- Validation review record filed; released on 2.x; install-verified.

## 5. Slice 2: kept current (outline)

Rides the 2.9.0 and 2.10.0 precedent: a catalog change with a migration for open changes.

| Piece | Where | Note |
|---|---|---|
| `data_layer` conditional step after Docs (4d) | `catalog.yaml`, `workflows.yaml`, `workflow-steps.md`, the product repo's `ci/first-pass/workflows.yaml` copy (refreshed by `dev-update`), `derive.py verify` | `engages: { any: [surfaces:data, data_migration] }`; `crit: standard`; Fast Track records it with a skip record |
| Delta file `data-delta-<change>.yaml` at status `proposed` | `generate-docs` Docs step; template in `ai/shared/templates/data-layer/` | Reviewed with the LLD |
| Conventions failure modes | `check_data_layer.py --diff <base>` | Store name in the diff with no mapping; job reading or writing a dataset with no lineage edge; detection tables per stack, Python first (open question 2 in #131) |
| Drift at Reconcile | `check_data_layer.py --changed-files` fed from `git diff --name-only` | Cited files in the diff mark their edges `needs-review`; Reconcile cannot close with one open; steward named where mappings carry an owner. A diff intersection, not an edit-time hook |
| Scorecard no-regression | `scorecard.py --baseline` in Reconcile | Regression is a finding, not a silent pass |
| Migration for open changes | `migrate_project.py` step, as 2.9.0 did | Open changes get the step `not_applicable` unless their impact record activates it |

## 6. Slices 3 to 5 (placeholders)

- **3 More sources (DL-12, DL-13):** one adapter per source type, each a separate sub-issue with its own
  fixture export; catalog harvest before code; OpenLineage export validated against the published schema.
- **4 Forward and across (DL-14, DL-15):** `start-from-prd` gains a data-layer pass after system design;
  `data-model-mapping-template.md` (the existing migration template) becomes the DL-15 mapping between two
  ontologies rather than a parallel artifact.
- **5 Verified and published (DL-16, DL-17):** `ops/deploy` runs `profile_adapter.py` read-only on the
  target; `export_schema.py` emits the extraction schema pinned to the release, validated against one named
  open-source extractor's schema input (open question 4 in #131).

## 7. Decisions for the Phase 0 ADRs

1. Manifest tie: ontology as source, Fold writes `boundary_entities` (§2.1).
2. Activator: impact-record findings, no new question (§2.2).
3. Skill boundary: one skill with five re-runnable stages, no modes flag (open question 1 in #131).
4. Adapter dependencies: pure Python plus lazy optional drivers, offline export mode is the tested path.
5. Stage isolation: sub-agent per entity from a file list, `inputs:` recorded, validator-enforced.
6. Answerability: all needed IDs present at a confidence other than `needs-review`.
7. Findings to tickets: offered under issue hygiene, filed on confirmation, never seeded into the incident
   registry directly (open question 3 in #131).
8. Where the files live: `docs/02-design/data/`, beside the LLDs the mappings cite.

## 8. Sizing

Relative, not hours. Slice 1 is roughly the size of First Pass (nine phases, four review rounds there;
seven phases and one validation review here) with two large pieces the platform has not built before: a
validator over a new artifact family, and adapters that touch stores outside the repo. The adapters are
the risk. The offline-first decision keeps their tested surface small; live mode is a fetch layer over the
same code.
