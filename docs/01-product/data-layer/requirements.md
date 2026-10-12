# Data Layer: Requirements

> **What** HITL must produce and keep current for the data a system holds: a business ontology, source
> mappings and lineage, derived from evidence, next to the system manifest. Product one-liner: **FR-31**
> in the [PRD](../prd.md) backlog table (§5.7), assigned 2026-09-19; FR-30 is
> [#105](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/105) and FR-32 is
> [#118](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/118). The **how** (adapters,
> file schemas, validators, the hook) is the design package at `docs/design/data-layer/`, not started.
> Status: **draft v2.2 (2026-10-12)**, restructured from EPIC
> [#131](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/131) after its first review, amended
> for the adoption model the issue gained on 2026-09-25, and widened on 2026-10-10 to a formal ontology
> validated by a reasoner and a decision-trace module every governed system carries, then on the same day to play
> along: opt-out per change, background derivation, a review page, and compliance levels derived from shipped
> consumers (§12).
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
checked in CI. No hosted UI; the skill publishes a generated review page (DL-26).

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

The layer is also compiled into a **formal ontology**: OWL 2 axioms, SHACL shapes and SHACL-AF rules
generated from the YAML, checked by a reasoner for coherence and against sampled store data for
conformance (DL-18 to DL-22). The YAML stays the source of truth; the compiled files are outputs. Every
ontology carries a **decision-trace module** (DL-23) so the governed system can record its own decisions,
exceptions and approvals as precedent. Converting a flow of the governed system to an agent on top of
that is a separate requirement, FR-38, with its own document.

This is an EPIC delivered in slices. Slice 1 is what the field project already did, made repeatable.
The issue's own list (edited 2026-09-25) numbers eight slices S1 to S8 across both parts of #131; the
business-rule layer (FR-35, Part B) shares this document's evidence model and scorecard and has no
requirements doc yet. The table below is the data-layer part only.

| Slice | Delivers | Requirements |
|---|---|---|
| 1 Brownfield core | Source intake, code and store evidence, per-entity interpretation, the four files, the scorecard, the manifest tie | DL-1 to DL-9 |
| 2 Kept current | The background delta at Reconcile, the conventions comment, the drift hook, the Depended-on hold | DL-10, DL-11, DL-25 |
| 3 More sources | Warehouse, dbt, orchestrator, BI and catalog adapters; catalog export | DL-12, DL-13 |
| 4 Forward and across | Greenfield authoring (FR-17), migration mapping (FR-19) | DL-14, DL-15 |
| 5 Verified and published | Deploy-time verification of mappings, the versioned extraction schema | DL-16, DL-17 |
| 6 Formal ontology | Axioms and rules in the YAML, the compiler, the reasoning stage, instance validation | DL-18 to DL-22 |
| 7 Decision trace | The module every ontology carries, its shapes and conformance check | DL-23 |
| 8 Plays along | Per-change opt-out, background derivation, the review page, compliance levels from shipped consumers, question-driven candidates, dead-code exclusion, the Action Catalog (optional) | DL-24 to DL-29, DL-2 |

## 4. Goals

1. **Write the data layer down once, with evidence.** Every entity, mapping and edge cites what it was read from.
2. **Say what is not known.** Unconfirmed is a first-class state, and the scorecard reports it.
3. **Answer the questions people have.** The layer is measured by the competency questions it can answer, not by its size.
4. **Keep it current at the point of change.** Every change refreshes the layer in the background; a change that touches an id a customer-facing consumer depends on cannot ship with that id stale (§6).
5. **One vocabulary.** Records, documents and agents use the same entity IDs.
6. **Govern, do not run.** HITL produces documents and validators. Teams load them where they like.
7. **Coherent as well as evidenced.** The compiled ontology is free of contradictions a reasoner can find, and the data it describes conforms to its shapes, before anything acts on it.
8. **Never slows a feature down.** The layer derives in the background, comments by default, and blocks only on the ids a customer-facing consumer depends on (§6).
9. **Precedent exists before an agent needs it.** The system records its own decisions from day one, so a later conversion of a flow to an agent has something to act on.

## 5. Requirements

Requirement IDs are `DL-<n>`.

| ID | Requirement | Priority | Slice |
|---|---|---|---|
| **DL-1** | **Sources are declared, then confirmed.** Intake scans the repo for connection strings, driver and ORM configs, dbt projects, orchestrator DAGs, IaC and env names, proposes an inventory, and the person confirms it, adds what the scan missed, and states per source the environment, the access they can grant, and whether it is in scope. The result is `sources.yaml`, the contract for everything after. A source declared but not reached is recorded as `declared, not extracted`, and every entity depending on it inherits `needs-review`. | Must | 1 |
| **DL-2** | **Competency questions are the layer's acceptance criteria.** Intake collects the questions the layer must answer (from the problem statement, tickets, and the people who will consume it), before anything is derived. Each is recorded with the entities and edges it needs. **The questions drive the first pass:** at intake a question's needs are nouns, since no ids exist yet; after Extract the skill binds each noun to a proposed candidate (an ORM class, table or collection the evidence names) and the person confirms the binding; the candidate list offered is those bound candidates, everything else the evidence names is shown as known and not interpreted, and more is pulled in one question at a time. The scorecard reports how many questions are answerable from the four files. A change whose delta stops a question being answerable is a finding. | Must | 1; 8 for the candidate rule |
| **DL-3** | **Evidence is separate from interpretation.** Adapters write typed, timestamped evidence files (`schema`, `query_history`, `catalog`, `dbt_manifest`, `code`, `profile`, `document`, `design`, `human`). Interpretation reads evidence files only. An assertion with no evidence entry is not written. A different model can re-process the same evidence. | Must | 1 |
| **DL-4** | **Each stage runs in a fresh context and reads only the previous stage's artifacts.** Extract is scripts, no model. Interpret runs one entity at a time, each in a context that holds only that entity's evidence. Fold reads interpretations only. Validate reads the four files and the competency questions. What a stage is handed is all it can read; nothing carries reasoning forward except the artifact. | Must | 1 |
| **DL-5** | **Three layers, three files, findings apart.** Semantic relationships live in the ontology, derivation edges in lineage (PROV terms: `used`, `wasGeneratedBy`, `wasDerivedFrom`), store and field facts in mappings. Negative findings ("code requests this field, the store never populates it") are annotations in `findings.yaml` with a severity, never edges. Confidence is one of three values. An ontology entry that names a service, job, file or endpoint is rejected by the validator. | Must | 1 |
| **DL-6** | **The manifest and the ontology agree.** Every `boundary_entity` in `system-manifest.yaml` is an ontology entity. The validator rejects a boundary entity absent from the ontology. | Must | 1 |
| **DL-7** | **A scorecard says how good the layer is, and diffs against the last run.** Verification rate of entities, fields and edges; entities with no mapping; negative findings stored as edges; age spread of evidence snapshots; sources declared but not extracted; open high-severity findings; competency questions answerable (DL-2); entities whose synonyms or natural keys collide with another entity. `--baseline` diffs two runs; `/hitl:dev-check-conventions` reports it. | Must | 1 |
| **DL-8** | **Adapters are read-only and run under the person's own credentials, with authorization stated before any live-store access.** Before an adapter touches a live store, the person names the environment and confirms they are authorized to read it, the same way the penetration-test skill requires authorization before an active scan. Nothing writes to any source. Air-gapped sources are run by hand and their output dropped into `evidence/` (FR-24). | Must | 1 |
| **DL-9** | **Model-assisted, human-confirmed.** A model writes the interpretation; a person, or a verification against the store, promotes an entry to `confirmed`. Catalog entries are evidence with a confidence like any other source: a definition untouched for two years is `inferred`. Where the catalog, the code and the store disagree about a key, that is a finding, not a merge. Findings are offered as tickets with their evidence attached and filed only when a person confirms (issue hygiene applies). | Must | 1 |
| **DL-10** | **Drift is caught at the change.** Every lineage edge cites files. When a change's diff touches a cited file, the edge is marked `needs-review` and Reconcile lists it. At the Depended-on level (DL-27), Reconcile cannot close with a `needs-review` edge citing a changed file until a person re-confirms it; the background re-derivation (DL-25) writes `inferred` and does not release the hold. At the Advisory level the list is a comment on the change. Where a steward is named for the dataset, they are the reviewer. | Must | 2 |
| **DL-11** | **The layer ships with the feature, without a step.** The impact record lists the entities, stores, edges and rules a change touches, from the diff; intake asks nothing new. At Reconcile the delta is derived in the background (DL-25) and folded into the files at `inferred`. The Conventions check comments on a store name in code with no mapping, or a job reading or writing datasets with no lineage edge; it fails only for a Depended-on id (DL-27). A scorecard regression against the baseline is reported the same way. Fast Track and Full Scale can both leave the layer out of a change with a record (DL-24). | Must | 2 |
| **DL-12** | **A catalog is an input first, a destination second.** Where one exists it is harvested before code is read: its glossary sets the vocabulary, entities adopt its term IDs rather than inventing parallel names, and its stewards become the owners DL-10 routes to. Export back is a delta: application-side lineage, mappings for stores the catalog cannot crawl, and findings, as valid OpenLineage plus glossary links. Git is authoritative; the catalog is a projection; re-export overwrites. | Should | 3 |
| **DL-13** | **One adapter per source type, each stating what it needs and what it yields.** Warehouse (schema, view SQL, observed lineage from query history where the grant allows, sampled profiling), dbt (model lineage, tests, owners), orchestrator (static lineage from DAG code, OpenLineage events if enabled), BI tools (which datasets feed which dashboards), ERP or SaaS metadata, document corpora (candidate definitions and synonyms, evidence type `document`, never a mapping or an edge on their own). Each adapter records the access it did not get. Observed and static lineage that disagree are a finding. | Should | 3 |
| **DL-14** | **Greenfield authors the same files forward.** After system design (FR-17) the PRD's nouns become a deliberately small ontology, aligned to a standard where one exists. Mappings are designed in the LLD with evidence type `design` and promoted to `confirmed` only by verification against a real environment (DL-16). Lineage edges are declared in each pipeline's LLD before code exists; the Conventions check holds code to them. The ontology is the source of the manifest's boundary entities from day one. | Should | 4 |
| **DL-15** | **Migration maps two ontologies.** Brownfield extraction on the source system, greenfield authoring on the target, and a mapping between them. The parity check (FR-19) fails on a source entity with no target entity and no recorded decision not to map it. | Could | 4 |
| **DL-16** | **Deploy verifies the mappings against the target environment.** The profiling adapter runs read-only on the deployed store: new stores and fields exist, counts are sane, `verified_at` is set. An unverifiable mapping stays `proposed` and the deploy step says so. | Should | 5 |
| **DL-17** | **The ontology is exported as a versioned extraction schema.** Entity types with descriptions, relationship names, synonyms and stable entity IDs, in a form at least one open-source document-graph extractor accepts unchanged, carrying the ontology version and pinned to the release. A document graph built on an old schema is detectable by its pin. Documents remain evidence (DL-13); the retrieval runtime is the team's. | Should | 5 |
| **DL-18** | **Entities and relationships carry axioms.** An entity may declare subclass, disjointness and equivalence with other entities, and keys (a mapping's natural key becomes an `owl:hasKey` on the entity, one per store that declares one; two stores whose keys disagree is a finding, as in DL-9). A relationship may declare domain, range, inverse, characteristics (functional, inverse-functional, transitive, symmetric) and cardinality restrictions. Every axiom is an assertion like any other: it carries confidence and evidence, a model never writes `confirmed`, and the validator rejects an axiom that names a store, job, file or endpoint. | Must | 6 |
| **DL-19** | **Rules live in one file with the evidence core.** `rules.yaml` holds each rule's id, a plain-English statement with exact values, a formal body in SHACL-AF (a SPARQL rule or a triple rule), an owner, a `why`, a status (`draft`, `confirmed`, `rejected`, `discrepancy`), a source (`recovered`, `intended`, `both`), confidence and evidence. The file is an instance of the shared core (ADR-13). "Alert the owner early" is not a rule; "URGENT when needed within 14 days" is. The reverse and forward capture of FR-35 write this file. | Must | 6 |
| **DL-20** | **The YAML compiles to a formal ontology, deterministically.** One script writes `ontology.ttl` (OWL 2), `shapes.ttl` (SHACL from mappings and axioms, plus action pre- and postconditions when the Action Catalog is on) and `rules.ttl` (SHACL-AF) from the YAML. Annotation properties carry each assertion's confidence, evidence references and `confirmed_by`. The compiled files are outputs, never edited by hand, and carry a pin of the YAML they came from; the validator rejects a compiled file whose pin does not match. | Must | 6 |
| **DL-21** | **A reasoning stage checks coherence and records what it infers.** Always: the OWL 2 RL closure and SHACL validation, in pure Python. When a JVM is present: full OWL 2 DL consistency and classification through HermiT, with the access recorded like any adapter. Two runs: strict over `confirmed` assertions only, exploratory over `confirmed` and `inferred`. A run that includes a `needs-review` assertion is refused. Strict-run findings block only for a Depended-on id (DL-27); exploratory findings are advisory. Inconsistencies, unsatisfiable classes, shape violations, inferred axioms and, when the Action Catalog is on, an action whose postcondition cannot hold under the axioms, are written as findings with evidence type `inference` at confidence `inferred`; a person or a verification run promotes or rejects them (DL-9). Reasoning validates coherence, not truth: a consistent ontology can still be wrong about the system, and only evidence and DL-22 check that. | Must | 6 |
| **DL-22** | **Sampled data is validated against the shapes.** The profile adapter's samples (offline export, or live under DL-8) are converted to RDF and validated with the compiled shapes and rules. A violation is a finding with evidence types `profile` and `inference`. The export also emits RML mappings generated from `mappings.yaml` for a team that wants to load full data elsewhere; HITL loads nothing. | Must | 6 |
| **DL-23** | **Every ontology carries the decision-trace module.** Decision, Policy, Exception, Approval and Precedent are entities and activities in PROV-O terms with a fixed minimum of properties (who, when, under which rule id, citing which precedent, with what outcome). Greenfield ontologies carry it from day one; brownfield ontologies gain it on the first run. HITL ships the module, its shapes and a conformance check that reads a system's trace records read-only, under DL-8's authorization rule for any live read; HITL never writes a trace record itself. A team may remove the module with a recorded decision; off is never the silent default. | Must | 7 |
| **DL-24** | **Opt-out per change, whatever the project setting.** At intake one line leaves the layer out of this change, recorded as a skip with actor and reason (FR-29), on Fast Track and Full Scale alike. At the Advisory level the skip needs nothing more. At the Depended-on level, for the ids a shipped consumer reads, it is a floor skip as FR-29 defines: `ack_by` from the accountable role, a `waiver_ref` because the Reconcile hold (DL-10) is fail-closed, and a `followup_ref` when the disposition is defer. Never silent. | Must | 8 |
| **DL-25** | **Per-change derivation runs in the background and holds no step.** At Reconcile the skill derives the delta from the diff (stores, fields, jobs, rules touched), writes it at `inferred`, and queues it for review. No person confirms anything at the step, and no step waits for the review, with one exception: a Depended-on id whose cited file the change touched holds Reconcile until a person re-confirms it (DL-10, DL-27). The impact record lists the touched ids; the review happens on the page (DL-26) when someone opens it. | Must | 8 |
| **DL-26** | **A generated review page presents the ontology, knowledge graph and decision trace.** The skill publishes a private page (the Artifact tool, as Team Pulse and the test scenarios already do): the graph drawn, one card per entity, relationship, mapping, rule, lineage edge, trace record type and, when the Action Catalog is on, action, each showing its evidence, confidence, the question it answers and the consumers that read it, with confirm, correct and reject. Corrections return through the skill and are written to the YAML; nobody edits YAML by hand. Offline distribution (FR-24) renders the same page as a local HTML file without the comment channel. Corrections come back the way the test-scenarios page already does (a pull reads the page's comments and submitted rows since the last pull); the per-assertion confirm, correct and reject grammar is new and is designed with the page. Every assertion gains a `written_at` timestamp (a shared-core change, §6) so the scorecard can report review latency: how long an `inferred` entry has waited. | Must | 8 |
| **DL-27** | **Compliance level is derived from shipped consumers, never from a flag.** A consumer registry lists what reads the layer: an FR-38 flow, a compound-design component (FR-26), the pinned extraction schema (DL-17), each with the ids it reads, its exposure (public, partner, internal) and the release it shipped in. The publish step registers what it can; onboarding asks once. A compound-design component becomes a consumer through three new manifest fields, exposure, the ids it reads and the release pin, a schema bump on the compound manifest, since its `authorization.audience` names a domain and not an exposure. Per id: Off (no files), Advisory (no shipped consumer reads it), Depended-on (a consumer with public or partner exposure that reads it has been promoted). A consumed id must be `confirmed` before its consumer is promoted. A team may set one further level, all ids Depended-on, as its only configuration choice. An unregistered consumer is a stated limit, not a silent one: the conformance check (DL-23) names any writer of trace records that is not in the registry. | Must | 8 |
| **DL-28** | **Dead code is excluded by evidence and recorded, never silently.** Extraction reads the deployed branch, not the default branch, with deployment and scheduler configuration as a source in its own right; the code source in `sources.yaml` carries an `entrypoints` list, seeded by intake from compose, process and scheduler files and confirmed by the person, which reachability is computed from. Code that no entrypoint reaches, a job with no schedule, a route that is not mounted, a duplicated script whose other copy is the live one, and a path that writes a field the store never holds or reads one that is empty on every row, each produce a finding of kind `dead-code` with its evidence. Such code contributes no entity, mapping, edge or rule to the layer. Where usage logs exist, a path not executed in the window is a `dead-code` finding at `inferred` (Part B, observed). Deletion is a person's decision through issue hygiene (DL-9). | Must | 8 |
| **DL-29** | **Action Catalog (optional): the governed verbs, by name.** The feature is called the Action Catalog wherever people meet it (intake, the review page, Conventions). Its file, `actions.yaml`, an instance of the shared core, exists only when a team turns the Action Catalog on and is never created otherwise. Each action names the entities and fields it reads and writes, its preconditions and postconditions (compiled to shapes), the rule ids that govern its outcome, the roles allowed to invoke it, and the trace record it emits (DL-23). Brownfield recovers candidates from handlers, routes, mutations and jobs with evidence; greenfield declares them from the PRD's use cases before code. HITL emits the catalog in a standard form and ships no tool definitions; a team's build step derives its tools from it. With the catalog on: the compound surface's privilege check compares a component's tools against it, a change touching a file an action cites marks it `needs-review` (DL-10), and FR-38 converts a flow only through catalogued actions. With it off, nothing in the layer or in FR-38 refers to it, and FR-38 falls back to the team's own tool declarations. HITL never executes an action and never evaluates a precondition at run time. | Could | 8 |

## 6. Constraints

- **Off by default, advisory by default, mandatory only where depended on.** Nothing in HITL depends on the layer; a repo without the files runs every workflow unchanged and creates none of them. In the development workflow every check comments. The only thing that blocks a change is a stale or unconfirmed id that a promoted customer-facing consumer reads (DL-27), and even that can be skipped with an accountable acknowledgement (DL-24). The layer's own CI checks its own files for malformation and never a feature change. Turning the layer off keeps the files and stops refreshing them. Brownfield onboarding mentions the layer once and never prompts for it again. This supersedes the per-repo `blocking` switch of v1.1 (ADR-9, superseded by ADR-19).

| Level | When | What a change sees |
|---|---|---|
| Off | No files under `docs/02-design/data/` | One SKIPPED line |
| Advisory | Files exist; no promoted public or partner consumer reads the id | Background derivation at Reconcile, a comment, a one-line opt-out |
| Depended-on | A promoted public or partner consumer reads the id | Reconcile cannot close on a stale entry for that id until a person re-confirms it; compiled files re-pinned at the release; opt-out is a floor skip with `ack_by` and `waiver_ref` |
- **Governs, does not run.** Output is documents, adapters and validators. No graph database, agent, query layer, catalog UI, embeddings, chunk store or retrieval loop.
- **Read-only by construction.** No adapter writes to a source (DL-8).
- **Shared core change.** DL-18 to DL-23 extend the shared core: evidence type `inference`, axiom keys on entities and relationships, a `rules.yaml` family, the Action Catalog's `actions.yaml` family (DL-29, optional), and a `written_at` timestamp on every assertion (DL-26). `data-layer.schema.yaml` moves to 1.1, the validator gains a rules check beside the existing six, and the ontology key list opens for axioms. Existing files stay valid.
- **Optional reasoning dependencies.** `rdflib`, `pyshacl` and `owlrl` are optional extras like Graphify; without them the reasoning stage reports SKIPPED and nothing else changes. A JVM is optional and only widens the check (DL-21). Hard dependencies stay bash, python3, PyYAML and git (NFR-1).
- **Reuse existing mechanisms.** The manifest and its drift checker, the conditional-step pattern (`cond:` in `workflows.yaml`), the impact record, the skip record (FR-29), `dev-check-conventions`, issue hygiene, the offline distribution (FR-24).
- **Evidence classes are labelled.** Every assertion says what kind of evidence backs it and when it was taken.
- **Plain English.** The four files and the scorecard read as documents people check, not as a schema dump.

## 7. Non-goals

- **Not a runtime.** HITL produces the schema a document graph should use and nothing else of the retrieval stack.
- **Not agent tool definitions or prompt fragments.** Generating those from the mappings, or from the Action Catalog when a team turns it on, is a team's own build step that reads the layer; shipping them would put HITL into runtime input.
- **Not column-level lineage inside SQL warehouses.** Existing tools do that; the merge takes theirs.
- **Not full automation.** Interpretation is model-assisted and human-confirmed, like the rest of onboarding.
- **Not a hosted UI.** The review page is generated and published by the skill, or written as a local file; HITL runs no server for it.
- **Not a reasoner service or a triple store.** The compiler and the reasoning stage run in the person's session and write files. HITL ships no SPARQL endpoint, no instance store and no agent runtime. The YAML is the source of truth; the OWL, SHACL and rules files are compiled from it (ADR-16).
- **Not the agent runtime.** Converting a flow to an agent is FR-38; HITL governs the conversion (candidates, shadow mode, promotion, write-back) and ships none of the runtime.
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
7. At the Advisory level, a change that adds a collection gets a Conventions comment and a background delta at `inferred`, and no step waits; at the Depended-on level the same change fails Conventions and a change that edits a file cited by a Depended-on edge cannot close Reconcile until a person re-confirms it (DL-10, DL-11, DL-25).
8. A catalog glossary term is adopted by ID, not duplicated; export produces valid OpenLineage (DL-12).
9. Greenfield entries start as `design` and become `confirmed` only after deploy-time verification (DL-14, DL-16).
10. The exported extraction schema is accepted unchanged by one named open-source extractor and carries the ontology version (DL-17).
11. An axiom with no evidence, or one that names a store, is rejected; a compiled file whose pin does not match the YAML is rejected (DL-18, DL-20).
12. A deliberately contradictory fixture (two disjoint entities with a shared key, a cardinality that cannot be met) produces inconsistency findings at `inferred` with evidence type `inference`, and a run that includes a `needs-review` assertion is refused (DL-21).
13. A sampled store row that breaks a shape produces a violation finding citing both the profile evidence and the inference (DL-22).
14. A greenfield ontology carries the decision-trace module without being asked; removing it needs a recorded decision; the conformance check reads a system's trace records and reports missing required properties (DL-23).
15. With the layer on and no shipped consumer, a change that opts out at intake records a skip and no step waits; with a promoted public consumer reading `ent:x`, a change touching a file cited by `ent:x` cannot close Reconcile until a person re-confirms the entry, a background re-derivation at `inferred` does not release it, and its opt-out needs `ack_by` and a `waiver_ref` (DL-10, DL-24, DL-27).
16. A change touching a store produces a delta at `inferred` at Reconcile without any prompt to the developer; the review page shows it as waiting and the scorecard reports its age (DL-25, DL-26).
17. A correction made on the review page is written to the YAML by the skill with `confirmed_by` set; the YAML file was not edited by hand (DL-26).
18. A consumer is promoted only when every id it reads is `confirmed`; a trace writer absent from the registry is named by the conformance check (DL-27).
19. With two confirmed questions whose needs name three nouns, after Extract the skill offers a binding of each noun to a proposed candidate; once confirmed, the candidate list has those three, the other entities the evidence names are listed as known and not interpreted, and adding a third question adds its bound candidates (DL-2).
20. A fixture whose `sources.yaml` declares two entrypoints, with an unscheduled job, an unmounted route and a module neither entrypoint reaches, produces three `dead-code` findings and no entity, mapping or edge from them; a field the code writes and the store never holds produces a fourth (DL-28).
21. With the Action Catalog off, no `actions.yaml` exists, the compiler and validator mention no actions, and FR-38's checks read the team's tool declarations; with it on, an action whose postcondition contradicts a disjointness axiom is a finding, a component declaring a tool with no catalogued action fails the privilege check, and a change touching a handler an action cites marks the action `needs-review` (DL-29).

## 9. Version

Slice 1 adds a skill, files and validators and changes no existing gate: a minor release on the 2.x line.
Slice 2 adds background work at Reconcile and a Conventions comment with one failure mode at the Depended-on level; it changes no step list, so no catalog bump unless the Reconcile hold needs one. Slotting is a
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
| v2.2 | 2026-10-12 | DL-29, the Action Catalog, an optional family on the shared core (the governed verbs: entities touched, pre- and postconditions as shapes, governing rule ids, allowed roles, trace record emitted), recovered on brownfield and declared on greenfield, off unless a team turns it on; DL-20, DL-21, DL-26 and the shared-core note read it only when on; FR-38 converts through catalogued actions when present; scenario 21. Borrowed from Foundry's action types after the 2026-10-12 comparison. |
| v2.1 | 2026-10-10 | After validation round 1 of v2.1: DL-11 rewritten to the background model (no conditional step); the Depended-on hold is released only by a person re-confirming, named in DL-10, DL-25, §6 and scenarios 7 and 15; DL-24 adds `waiver_ref` because the hold is fail-closed; DL-26 adds `written_at` to the shared core and names the correction channel as new; DL-2 binds question nouns to candidates after Extract; DL-27 names the three compound-manifest fields it needs; DL-28 declares entrypoints in `sources.yaml`; §9 no longer claims a catalog bump. |
| v2.1 | 2026-10-10 | Also: DL-2 amended so the candidate list is derived from the questions and expanded one question at a time; DL-28 dead code excluded by evidence (deployed branch, deployment and scheduler config as a source, reachability, store disagreement, observed usage) and recorded as findings; scenarios 19 and 20. |
| v2.1 | 2026-10-10 | Plays along: per-change opt-out at either plan (DL-24), background derivation that holds no step (DL-25), a generated review page for the ontology, graph and trace with corrections written back by the skill (DL-26), compliance derived per id from shipped consumers and their exposure (DL-27). §6 blocking switch replaced by the three levels; §1 "No UI" became "No hosted UI"; goal 8 added; slice 8; scenarios 15 to 18; ADR-19. Owner's direction of 2026-10-10. |
| v2.0 | 2026-10-10 | Widened from a documents-only layer to a formal ontology and a decision-trace module after the owner's direction of 2026-10-08 to 2026-10-10 (agentic flows backed by the system's own context graph): DL-18 to DL-23, slices 6 and 7, goals 7 and 9 (numbered after goal 8 was inserted in v2.1), the §7 non-goal "Not a formal ontology" replaced by "Not a reasoner service or a triple store", the optional-dependency constraint, acceptance scenarios 11 to 14. Decisions in ADR-14 to ADR-18. FR-38 (flow conversion) registered in the PRD with its own document to follow. |
| v1.1 | 2026-09-30 | Adoption model from the 2026-09-25 issue edit: off by default, advisory by default, blocking per repo (§6); DL-10 and DL-11 reworded to "with blocking on"; §3 notes the issue's eight-slice list and Part B (FR-35) sharing the evidence model; design package Phase 0 written (`docs/design/data-layer/`). |
| v1 | 2026-09-14 | Restructured from #131. Findings applied: linked plugin #24 and #16, which cover the same gap and the same drift mechanism; split one FR with a fifteen-clause acceptance cell into an epic with five slices, slice 1 being what the field project already did; moved the adapter table, file schemas and per-step lifecycle to design input; replaced the unverified "per-session named-environment confirmation HITL already uses" with an authorization requirement (DL-8); removed agent tool definitions and prompt fragments from the publish step (§7); left the FR number open until FR-30 is settled; added competency questions (DL-2), stage isolation (DL-4) and the collision metric (DL-7) from the video review. |
