# Data Layer: Requirements

> **What** HITL must produce and keep current for the data a system holds: a business ontology, source
> mappings and lineage, derived from evidence, next to the system manifest. Product one-liner: **FR-TBD**
> in the [PRD](../prd.md); the number is assigned when FR-30 is settled (it is claimed by both
> [#105](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/105) and
> [#118](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/118)). The **how** (adapters,
> file schemas, validators, the hook) is the design package at `docs/design/data-layer/`, not started.
> Status: **draft v1 (2026-09-14)**, restructured from EPIC
> [#131](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/131) after its first review (§12).
> Related: plugin [#24](https://github.com/pappar/hitl-claude-plugin/issues/24) (brownfield produces
> no data model), plugin [#16](https://github.com/pappar/hitl-claude-plugin/issues/16) (manifest as a
> living artifact), FR-17, FR-18, FR-19, FR-29.

## 1. Problem

Brownfield onboarding (FR-18) maps a codebase into a manifest, HLDs, LLDs and ADRs. The manifest holds
domains, boundary entities and the interaction matrix. Nothing in HITL records what the data means, where
each entity lives, or how one dataset is derived from another. That knowledge sits in the code, the live
stores and sometimes a catalog, written down together nowhere. Every agent or script built on the system
rediscovers it, and nothing keeps it current once a feature ships.

| How the gap shows | What is missing |
|---|---|
| An agent asked "why is this figure what it is" cannot answer; the rule lives in a nightly job | Lineage |
| A cached result and a live read of the same fact look like two sources | Lineage, freshness |
| Every new consumer of a pipeline re-reads the pipeline code for the join keys and the rule | Mappings |
| A feature adds a collection or a job and the model of the system is stale the day it ships | Ownership, drift |
| A document graph extracted by a model names the same things differently from the operational data | Shared vocabulary |

**Evidence.** *Field project (2026-08 to 2026-09):* the Technical Advisor ran the method by hand, one entity
at a time. Result: about 20 business entities, roughly 70 relationships, several hundred fields; two thirds
of the relationships came from code, one third from profiling the live store. The first pass found a pipeline
whose repository source no longer matched the data it wrote, a dead access-control validator, a field two
services request that is empty on every row, and two ID spaces sharing a vocabulary with zero overlap. Each
became a ticket with evidence. The same project is plugin #24's evidence that onboarding produced no data
model: one domain's LLD documented 5 of 25 persistence classes, a second domain's 9 entities were not
documented at all, and the completeness summary could not report the absence. *Weaknesses the field pass
showed:* under half the entities fully confirmed, one entity live-verified end to end, and negative findings
modelled as relationships in the first cut, which a naive traversal follows as facts.

**Delivery surface.** Documents and validators in the product repo, produced by a Claude Code skill and
checked in CI. No UI.

## 2. Users

| User | What they need |
|---|---|
| **Technical Advisor / Architect** | The data layer of an existing system written down with evidence, and a way to see what is unconfirmed |
| **Developer** | The keys, rules and stores a change touches, without re-reading the pipeline; a validator that says when the layer is stale |
| **Data owner / steward** | To be named on what they own and asked when a change touches it |
| **Agent and pipeline builders** | One vocabulary with stable IDs that records and documents both use |
| **PM** | Findings surfaced as tickets with evidence, not as folklore |

## 3. Scope

The **data layer** is three documents and an evidence folder under `docs/02-design/data/`, following the
DAMA-DMBOK split:

| Layer | Holds | Answers |
|---|---|---|
| Ontology (business) | Entities, definitions, synonyms, semantic relationships | What is this thing |
| Mappings (technical) | Per entity: stores, fields, keys, owner, counts as profiled | Where does it live |
| Lineage (operational) | Derivation edges with job, rule as prose, freshness, consumers | How was it made |

Negative and cross-cutting findings are annotations in a fourth file, never edges. Every assertion carries a
confidence (`confirmed`, `inferred`, `needs-review`) and cites evidence.

This is an EPIC delivered in slices. Slice 1 is what the field project already did, made repeatable.

| Slice | Delivers | Requirements |
|---|---|---|
| 1 Brownfield core | Source intake, code and store evidence, per-entity interpretation, the four files, the scorecard, the manifest tie | DL-1 to DL-9 |
| 2 Kept current | The conditional step in every change, the delta file, the conventions check, the drift hook | DL-10, DL-11 |
| 3 More sources | Warehouse, dbt, orchestrator, BI and catalog adapters; catalog export | DL-12, DL-13 |
| 4 Forward and across | Greenfield authoring (FR-17), migration mapping (FR-19) | DL-14, DL-15 |
| 5 Verified and published | Deploy-time verification of mappings, the versioned extraction schema | DL-16, DL-17 |

## 4. Goals

1. **Write the data layer down once, with evidence.** Every entity, mapping and edge cites what it was read from.
2. **Say what is not known.** Unconfirmed is a first-class state, and the scorecard reports it.
3. **Answer the questions people have.** The layer is measured by the competency questions it can answer, not by its size.
4. **Keep it current at the point of change.** A change that touches a cited file or adds a store cannot ship with the layer stale.
5. **One vocabulary.** Records, documents and agents use the same entity IDs.
6. **Govern, do not run.** HITL produces documents and validators. Teams load them where they like.

## 5. Requirements

Requirement IDs are `DL-<n>`.

| ID | Requirement | Priority | Slice |
|---|---|---|---|
| **DL-1** | **Sources are declared, then confirmed.** Intake scans the repo for connection strings, driver and ORM configs, dbt projects, orchestrator DAGs, IaC and env names, proposes an inventory, and the person confirms it, adds what the scan missed, and states per source the environment, the access they can grant, and whether it is in scope. The result is `sources.yaml`, the contract for everything after. A source declared but not reached is recorded as `declared, not extracted`, and every entity depending on it inherits `needs-review`. | Must | 1 |
| **DL-2** | **Competency questions are the layer's acceptance criteria.** Intake collects the questions the layer must answer (from the problem statement, tickets, and the people who will consume it), before anything is derived. Each is recorded with the entities and edges it needs. The scorecard reports how many are answerable from the four files. A change whose delta stops a question being answerable is a finding. | Must | 1 |
| **DL-3** | **Evidence is separate from interpretation.** Adapters write typed, timestamped evidence files (`schema`, `query_history`, `catalog`, `dbt_manifest`, `code`, `profile`, `document`, `design`, `human`). Interpretation reads evidence files only. An assertion with no evidence entry is not written. A different model can re-process the same evidence. | Must | 1 |
| **DL-4** | **Each stage runs in a fresh context and reads only the previous stage's artifacts.** Extract is scripts, no model. Interpret runs one entity at a time, each in a context that holds only that entity's evidence. Fold reads interpretations only. Validate reads the four files and the competency questions. What a stage is handed is all it can read; nothing carries reasoning forward except the artifact. | Must | 1 |
| **DL-5** | **Three layers, three files, findings apart.** Semantic relationships live in the ontology, derivation edges in lineage (PROV terms: `used`, `wasGeneratedBy`, `wasDerivedFrom`), store and field facts in mappings. Negative findings ("code requests this field, the store never populates it") are annotations in `findings.yaml` with a severity, never edges. Confidence is one of three values. An ontology entry that names a service, job, file or endpoint is rejected by the validator. | Must | 1 |
| **DL-6** | **The manifest and the ontology agree.** Every `boundary_entity` in `system-manifest.yaml` is an ontology entity. The validator rejects a boundary entity absent from the ontology. | Must | 1 |
| **DL-7** | **A scorecard says how good the layer is, and diffs against the last run.** Verification rate of entities, fields and edges; entities with no mapping; negative findings stored as edges; age spread of evidence snapshots; sources declared but not extracted; open high-severity findings; competency questions answerable (DL-2); entities whose synonyms or natural keys collide with another entity. `--baseline` diffs two runs; `/hitl:dev-check-conventions` reports it. | Must | 1 |
| **DL-8** | **Adapters are read-only and run under the person's own credentials, with authorization stated before any live-store access.** Before an adapter touches a live store, the person names the environment and confirms they are authorized to read it, the same way the penetration-test skill requires authorization before an active scan. Nothing writes to any source. Air-gapped sources are run by hand and their output dropped into `evidence/` (FR-24). | Must | 1 |
| **DL-9** | **Model-assisted, human-confirmed.** A model writes the interpretation; a person, or a verification against the store, promotes an entry to `confirmed`. Catalog entries are evidence with a confidence like any other source: a definition untouched for two years is `inferred`. Where the catalog, the code and the store disagree about a key, that is a finding, not a merge. Findings are offered as tickets with their evidence attached and filed only when a person confirms (issue hygiene applies). | Must | 1 |
| **DL-10** | **Drift is caught at the change.** Every lineage edge cites files. When a change's diff touches a cited file, the edge is marked `needs-review` and Reconcile lists it. Reconcile cannot close with a `needs-review` edge citing a changed file; the edge is re-confirmed or re-derived. Where a steward is named for the dataset, they are the reviewer. | Must | 2 |
| **DL-11** | **The layer ships with the feature.** Intake asks one question: does the change add or alter an entity, field, store, relationship or derivation? Yes activates a conditional `data_layer` step and the impact record lists the affected entities and edges. The Docs step writes a delta at status `proposed`, reviewed with the LLD. The Conventions check fails on a store name in code with no mapping, or a job reading or writing datasets with no lineage edge. Reconcile folds the delta into the four files, and the scorecard must not regress against the baseline. Fast Track can leave the step out with a record (FR-29). | Must | 2 |
| **DL-12** | **A catalog is an input first, a destination second.** Where one exists it is harvested before code is read: its glossary sets the vocabulary, entities adopt its term IDs rather than inventing parallel names, and its stewards become the owners DL-10 routes to. Export back is a delta: application-side lineage, mappings for stores the catalog cannot crawl, and findings, as valid OpenLineage plus glossary links. Git is authoritative; the catalog is a projection; re-export overwrites. | Should | 3 |
| **DL-13** | **One adapter per source type, each stating what it needs and what it yields.** Warehouse (schema, view SQL, observed lineage from query history where the grant allows, sampled profiling), dbt (model lineage, tests, owners), orchestrator (static lineage from DAG code, OpenLineage events if enabled), BI tools (which datasets feed which dashboards), ERP or SaaS metadata, document corpora (candidate definitions and synonyms, evidence type `document`, never a mapping or an edge on their own). Each adapter records the access it did not get. Observed and static lineage that disagree are a finding. | Should | 3 |
| **DL-14** | **Greenfield authors the same files forward.** After system design (FR-17) the PRD's nouns become a deliberately small ontology, aligned to a standard where one exists. Mappings are designed in the LLD with evidence type `design` and promoted to `confirmed` only by verification against a real environment (DL-16). Lineage edges are declared in each pipeline's LLD before code exists; the Conventions check holds code to them. The ontology is the source of the manifest's boundary entities from day one. | Should | 4 |
| **DL-15** | **Migration maps two ontologies.** Brownfield extraction on the source system, greenfield authoring on the target, and a mapping between them. The parity check (FR-19) fails on a source entity with no target entity and no recorded decision not to map it. | Could | 4 |
| **DL-16** | **Deploy verifies the mappings against the target environment.** The profiling adapter runs read-only on the deployed store: new stores and fields exist, counts are sane, `verified_at` is set. An unverifiable mapping stays `proposed` and the deploy step says so. | Should | 5 |
| **DL-17** | **The ontology is exported as a versioned extraction schema.** Entity types with descriptions, relationship names, synonyms and stable entity IDs, in a form at least one open-source document-graph extractor accepts unchanged, carrying the ontology version and pinned to the release. A document graph built on an old schema is detectable by its pin. Documents remain evidence (DL-13); the retrieval runtime is the team's. | Should | 5 |

## 6. Constraints

- **Governs, does not run.** Output is documents, adapters and validators. No graph database, agent, query layer, catalog UI, embeddings, chunk store or retrieval loop.
- **Read-only by construction.** No adapter writes to a source (DL-8).
- **Reuse existing mechanisms.** The manifest and its drift checker, the conditional-step pattern (`cond:` in `workflows.yaml`), the impact record, the skip record (FR-29), `dev-check-conventions`, issue hygiene, the offline distribution (FR-24).
- **Evidence classes are labelled.** Every assertion says what kind of evidence backs it and when it was taken.
- **Plain English.** The four files and the scorecard read as documents people check, not as a schema dump.

## 7. Non-goals

- **Not a runtime.** HITL produces the schema a document graph should use and nothing else of the retrieval stack.
- **Not agent tool definitions or prompt fragments.** Generating those from the mappings is a team's own build step that reads the layer; shipping them would put HITL into runtime input.
- **Not column-level lineage inside SQL warehouses.** Existing tools do that; the merge takes theirs.
- **Not full automation.** Interpretation is model-assisted and human-confirmed, like the rest of onboarding.
- **Not a formal ontology.** The files are YAML with PROV vocabulary for lineage. An OWL export is a possible consumer, not the source of truth.
- **Not a fixed agent cast.** DL-4 is about context isolation between stages. It names no manager, coder or QA agent, and no stage repairs another's output after the fact; a stage that fails validation is re-run from its inputs.

## 8. Success measures

### 8.1 Success metric (baselined today)

- **Coverage at onboarding:** the share of brownfield onboardings that produce a data layer with a scorecard. Baseline **0** (plugin #24: the field project's onboarding produced none). Target: every onboarding after slice 1 ships.
- **Answerability:** competency questions answerable from the layer, on the field project. Baseline: not measured; the field pass had no question list. Target set at the first scorecard run and required not to regress per change (DL-11).
- **Verification rate:** entities fully confirmed. Baseline on the field project: under half. A target is not set until the method is repeatable; the honest measure for now is that the rate is reported and climbs.

### 8.2 Acceptance scenarios (pass/fail)

1. Onboarding an existing codebase with a document store and a relational database writes `sources.yaml` from a scan plus confirmation, and a source the person declines to grant access to is recorded `declared, not extracted` with its dependants `needs-review` (DL-1).
2. Intake collects at least the competency questions in §1's table for that system, and the scorecard reports how many are answerable (DL-2, DL-7).
3. An interpretation for one entity is produced in a context holding only that entity's evidence files; the fold that writes `ontology.yaml` is given interpretations only. Verified by what each stage is handed (DL-4).
4. The validator rejects an ontology entry naming a service, a negative finding written as an edge, a fourth confidence value, and a boundary entity absent from the ontology (DL-5, DL-6).
5. The scorecard runs on the field project's evidence, diffs against a baseline, and reports two entities whose synonyms collide (DL-7).
6. No adapter runs against a live store before the person names the environment and confirms authorization; a run log shows read-only access only (DL-8).
7. A change that adds a collection with no delta entry fails the Conventions check; a change that edits a file cited by a lineage edge cannot close Reconcile until the edge is re-confirmed (DL-10, DL-11).
8. A catalog glossary term is adopted by ID, not duplicated; export produces valid OpenLineage (DL-12).
9. Greenfield entries start as `design` and become `confirmed` only after deploy-time verification (DL-14, DL-16).
10. The exported extraction schema is accepted unchanged by one named open-source extractor and carries the ontology version (DL-17).

## 9. Version

Slice 1 adds a skill, files and validators and changes no existing gate: a minor release on the 2.x line.
Slice 2 adds a conditional step to the development workflow and a Conventions failure mode, so it needs a
catalog bump and a migration for open changes, the same as 2.9.0 and 2.10.0 did. Slotting is a
release-planning decision.

## 10. Standards alignment (pointer)

DAMA-DMBOK for the business, technical and operational split; W3C PROV-O for lineage vocabulary;
OpenLineage for the export format. Catalog products (Atlan, Collibra, DataHub, OpenMetadata, Purview) hold
and serve all three layers but derive lineage from SQL logs and orchestrator events, not from application
code; HITL consumes what they hold and produces what they lack. The rationale is design, not a requirement.

## 11. References

- EPIC #131, the original proposal; its §2 (adapter table), §4 (file schemas), §5 (scorecard thresholds) and §6 (per-step lifecycle) are design input for `docs/design/data-layer/`.
- Plugin #24: brownfield onboarding produces no data model; its proposed fix (a required data-architecture HLD plus the full persistence surface) is the thinnest version of slice 1 and should not be built separately.
- Plugin #16: manifest as a living artifact; DL-10 is the same mechanism applied to lineage edges.
- "Architecting automated ontologies", a walkthrough of a multi-agent pipeline for extracting formal ontologies from insurance-contract text (video, 2026; no paper citation given; results judged by an LLM panel on one domain). Taken: competency questions as the functional requirement (DL-2), context isolation between stages with the artifact as the only handoff (DL-4), and the warning that cross-file semantic duplication is the unsolved problem (the collision metric in DL-7). Not taken: the fixed four-agent cast, the vector-RAG evaluation probe (runtime), and OWL/SPARQL as the target (§7).

## 12. Review history

| Version | Date | Change |
|---|---|---|
| v1 | 2026-09-14 | Restructured from #131. Findings applied: linked plugin #24 and #16, which cover the same gap and the same drift mechanism; split one FR with a fifteen-clause acceptance cell into an epic with five slices, slice 1 being what the field project already did; moved the adapter table, file schemas and per-step lifecycle to design input; replaced the unverified "per-session named-environment confirmation HITL already uses" with an authorization requirement (DL-8); removed agent tool definitions and prompt fragments from the publish step (§7); left the FR number open until FR-30 is settled; added competency questions (DL-2), stage isolation (DL-4) and the collision metric (DL-7) from the video review. |
