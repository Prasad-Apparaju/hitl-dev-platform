# Data Layer: Low-Level Design

> Status: **draft v1 (2026-09-30)**, Phase 0. Implements HLD [`01-design.md`](01-design.md) and ADRs
> [`02-adrs.md`](02-adrs.md) for FR-31 slice 1. Every schema and table traces to a DL in
> [`../../01-product/data-layer/requirements.md`](../../01-product/data-layer/requirements.md).
> This document is longer than the one-page-per-component ceiling: the file schemas are the
> contract every other piece is tested against, and they are listed in full on purpose.

## 1. Scope

The shared evidence core (§2.0), the six files and two folders (§2.1 to §2.9), the adapter contracts
(§3), the validator rules (§4), the scorecard (§5), the skill's stage contracts (§6), the manifest tie
(§7), integration edits (§8) and lints (§9). Paths are relative to `docs/02-design/data/` unless
written from the repo root.

### 1.1 Identifiers

| Prefix | Names | Example | Rule |
|---|---|---|---|
| `src:` | a declared source | `src:orders-db` | kebab-case, unique in `sources.yaml` |
| `ent:` | an ontology entity | `ent:order` | kebab-case, stable across runs; never reused |
| `map:` | a mapping | `map:order/orders-db.orders` | `<entity>/<source>.<store>` |
| `act:` | a lineage activity (job, pipeline step, request handler) | `act:nightly-eta` | kebab-case |
| `lin:` | a lineage edge | `lin:7` | integer, never reused |
| `fnd:` | a finding | `fnd:3` | integer, never reused |
| `q:` | a competency question | `q:2` | integer |
| `ev:` | an evidence item inside one evidence file | `ev:code/0041` | `<type>/<4 digits>`, unique within the file; a slice copies items under their original IDs |

Every ID is unique across all six files (`ID_DUPLICATE`, §4).

## 2. File schemas

### 2.0 The shared core (ADR-13), in `ai/shared/templates/data-layer/data-layer.schema.yaml`

```yaml
# Every assertion in every family carries these.
confidence:
  enum: [confirmed, inferred, needs-review]      # exactly three; a fourth value is CONFIDENCE_UNKNOWN
evidence:
  type: list[ref]                                 # empty list is NO_EVIDENCE
  ref: { file: "evidence/<source>/<type>-<ts>.yaml", item: "ev:<type>/<nnnn>" }
confirmed_by:                                     # required when confidence is confirmed
  who: string                                     # a person, or "verification:<adapter run>"
  at: timestamp
  how: enum [human, verification]
inputs:                                           # on an interpretation only
  type: list[path]                                # the files the writer was handed; nothing else may be cited
evidence_types:
  enum: [schema, query_history, catalog, dbt_manifest, code, profile, document, design, human]
prov_relations:
  enum: [used, wasGeneratedBy, wasDerivedFrom]
```

### 2.1 `sources.yaml` (DL-1, DL-8)

```yaml
schema_version: "1.0"
written_by: { stage: intake, at: 2026-09-30T09:00:00Z }
sources:
  - id: src:orders-db
    kind: relational            # relational | document | warehouse | dbt | orchestrator | catalog | bi | saas | code | documents
    declared_from: ["docker-compose.yml:14", "app/settings.py:8"]   # from the scan, file:line
    environment: dev            # dev | staging | prod | offline-export
    in_scope: true
    access: { granted: read_only, mode: offline }                   # granted: read_only | none; mode: offline | live
    status: declared            # declared | extracted | declared-not-extracted  (set by Extract)
    authorization:              # required when mode is live; absent otherwise
      by: "ta@team"
      at: 2026-09-30T09:10:00Z
      environment: dev          # must equal the source's environment
      statement: AUTHORIZED     # the literal reply
    notes: ""
```

Rules. `status` is written only by Extract: `extracted` when an evidence file exists for the source,
`declared-not-extracted` otherwise. A `live` source with an incomplete `authorization` is
`LIVE_WITHOUT_AUTHORIZATION` (§4) and the adapter refuses to run before the validator ever sees it.

### 2.2 `questions.yaml` (DL-2, ADR-6)

```yaml
schema_version: "1.0"
questions:
  - id: q:1
    text: "Why is the ETA on an order what it is?"
    asked_by: "ops lead"
    from: "problem-statement"              # problem-statement | ticket:#N | person | document:<path>
    needs:
      entities: [ent:order, ent:shipment]
      mappings: [map:eta/eta-cache.eta_cache]
      edges: [lin:3]
    confirmed_by: { who: "ta@team", at: 2026-09-30T09:20:00Z, how: human }   # the needs list, not the answer
```

### 2.3 `ontology.yaml` (DL-5)

```yaml
schema_version: "1.0"
entities:
  - id: ent:order
    name: Order
    definition: "A customer's request to buy, from placement to fulfilment or cancellation."
    synonyms: [purchase order, PO]
    catalog_term: null                     # "glossary:<id>" when adopted from a catalog (slice 3)
    relationships:
      - { name: has, target: ent:order-line, cardinality: one-to-many,
          confidence: confirmed, evidence: [{ file: evidence/app/code-20260930T0900.yaml, item: ev:code/0007 }],
          confirmed_by: { who: "ta@team", at: 2026-09-30T11:00:00Z, how: human } }
    confidence: inferred
    evidence: [{ file: evidence/app/code-20260930T0900.yaml, item: ev:code/0001 }]
```

Rules. `name`, `definition` and `synonyms` may not contain a path separator, a URL scheme or a code-file
extension from the code adapter's list. `name` and each synonym may not equal, case-folded, a store
name, activity ID, source ID or file basename found in `mappings.yaml`, `lineage.yaml` or
`sources.yaml`, except the names of the entity's own mapped stores (so `Order` may carry the synonym
`orders` when `orders` is its table). Both are `ONTOLOGY_NAMES_IMPLEMENTATION`; the match is on whole
tokens, so a definition that mentions "orders" in prose passes. A relationship
has no `polarity`, `negative`, `absent` or `missing` key (`NEGATIVE_AS_EDGE`).

### 2.4 `mappings.yaml` (DL-5, DL-9)

```yaml
schema_version: "1.0"
mappings:
  - id: map:order/orders-db.orders
    entity: ent:order
    store: { source: src:orders-db, kind: table, name: orders, naming_template: null }   # "orders_{tenant}" when templated
    fields:
      - { name: id, type: uuid, present_pct: 100.0, confidence: confirmed, evidence: [ ... ] }
      - { name: promised_date, type: date, present_pct: 97.4, confidence: inferred, evidence: [ ... ] }
    natural_key: [order_no]
    scope: tenant                           # global | tenant | region | null
    owner: "orders-team"                    # steward; slice 2 routes drift here
    counts: { rows: 1203, taken_at: 2026-09-30T09:40:00Z, sampled: false }
    written_by: ["app/models/order.py", "app/repo/orders.py"]     # repo paths from code evidence
    read_by: ["jobs/nightly_eta.py", "app/api/orders.py"]
    verified_at: null
    confidence: inferred
    evidence: [ ... ]
```

Rules. `entity` must exist in the ontology (`MAPPING_ENTITY_UNKNOWN`). `store.source` must exist in
`sources.yaml` (`SOURCE_UNKNOWN`). When that source is `declared-not-extracted`, the mapping and every
field in it must be `needs-review` (`UNEXTRACTED_SOURCE_NOT_REVIEW`).

### 2.5 `lineage.yaml` (DL-5, DL-10)

```yaml
schema_version: "1.0"
activities:
  - id: act:nightly-eta
    kind: job                               # job | pipeline-step | handler | view | manual
    files: ["jobs/nightly_eta.py"]          # every edge through this activity cites these (DL-10)
    schedule: "nightly 02:00"
    owner: "orders-team"
edges:
  - id: lin:3
    relation: wasGeneratedBy                # used | wasGeneratedBy | wasDerivedFrom
    subject: map:eta/eta-cache.eta_cache    # see the type table
    object: act:nightly-eta
    rule: "ETA is the promised date plus the carrier's median lag over the last 30 days."   # prose, never code
    freshness: { cadence: nightly, observed_max_age_hours: 26 }
    consumers: [ent:order, "dashboard: ops daily"]
    confidence: inferred
    evidence: [ ... ]
```

Relation types the validator enforces (`EDGE_TERM_UNKNOWN`, `EDGE_TYPE_MISMATCH`):

| relation | subject | object |
|---|---|---|
| `used` | `act:` | `map:` or `ent:` |
| `wasGeneratedBy` | `map:` or `ent:` | `act:` |
| `wasDerivedFrom` | `map:` or `ent:` | `map:` or `ent:` |

An edge has no `polarity`, `negative`, `absent` or `missing` key. An edge whose `rule` starts with
"never", "not", "no ", "missing" or "empty" is a waivable warning (`EDGE_READS_NEGATIVE`); the
structural rule above is the guarantee, the wording check is a nudge.

### 2.6 `findings.yaml` (DL-5, DL-9)

```yaml
schema_version: "1.0"
findings:
  - id: fnd:1
    kind: negative                          # negative | disagreement | collision | unextracted | dead-code | stale
    severity: high                          # high | medium | low
    about: [map:shipment/shipments-db.shipments, act:nightly-eta]
    statement: "Code reads shipments.carrier_ref on every run; the field is empty on every profiled row."
    confidence: confirmed
    evidence: [ ... ]
    confirmed_by: { who: "verification:profile_adapter 2026-09-30T09:40:00Z", at: 2026-09-30T09:40:00Z, how: verification }
    status: open                            # open | ticketed:#N | resolved | accepted
```

A finding has no `subject`, `object`, `relation`, `from` or `to` key (`FINDING_SHAPED_AS_EDGE`).

### 2.7 Evidence files, `evidence/<source>/<type>-<timestamp>.yaml` (DL-3, DL-8)

```yaml
schema_version: "1.0"
evidence_type: code                         # one of the nine types
source: src:app
taken_at: 2026-09-30T09:00:00Z
adapter: { name: code_adapter.py, version: "1.0.0" }
access: { mode: offline, environment: offline-export, read_only: true }     # live adds authorization: { by, at }
coverage: { languages: [python], files_scanned: 212, files_skipped: { other_language: 14 } }
items:
  - id: ev:code/0001
    kind: orm_entity                        # per adapter, §3
    locator: "app/models/order.py:12"       # file:line, or "<export>#<row>" for profiles
    data: { class: Order, table: orders, fields: [id, order_no, promised_date] }
```

One file per source and type per run; a new run replaces it. `taken_at` feeds the age metric.
`run.log` (one line per adapter run) sits beside the folder:

```
2026-09-30T09:40:00Z profile_adapter src:orders-db mode=offline env=offline-export read_only=true calls=count,sample(500) result=ok
2026-09-30T09:41:00Z profile_adapter src:warehouse mode=live env=prod read_only=true result=refused reason=no_authorization
```

### 2.7a Evidence slices, `evidence/slices/<entity>.yaml` (DL-4, ADR-5)

Evidence files are one per source and type, so handing an Interpret sub-agent whole files would hand
it every entity's evidence. `tools/data-layer/slice_evidence.py` writes one slice per candidate entity:
the items whose `data` names the entity's class, store, or a key the code adapter tied to that store,
plus the profile items for those stores. A slice has the §2.7 envelope with `evidence_type: slice`,
`entity:`, and `origin: { file, item }` on every item, which keeps its original `ev:` ID. An
interpretation cites slice files; Fold rewrites each citation to its origin before writing the four
files, so the four files cite source evidence only. The validator resolves a citation to a slice by
`item` in that slice, and a citation in the four files by `item` in the origin file.

### 2.8 Interpretations, `interpretations/<entity>.yaml` (DL-3, DL-4, DL-9)

```yaml
schema_version: "1.0"
entity: ent:order
inputs:                                     # exactly the files the sub-agent was handed: its slice, the schema, the template
  - evidence/slices/order.yaml
  - ai/shared/templates/data-layer/data-layer.schema.yaml
  - ai/shared/templates/data-layer/interpretation.yaml
written_by: { model: "claude", at: 2026-09-30T10:05:00Z }
proposed:
  ontology: { ...one entity entry as in §2.3, confidence inferred or needs-review... }
  mappings: [ ...entries as in §2.4... ]
  lineage: { activities: [...], edges: [...] }     # edges and findings carry NO id (§6, Fold assigns them)
  findings: [ ... ]
open_questions: ["Is order_no unique per tenant or global? The export has one tenant."]
```

Rules. Every `evidence.file` under `proposed` must be in `inputs` (`CITATION_OUTSIDE_INPUTS`). No
entry under `proposed` may be `confirmed` (`MODEL_WROTE_CONFIRMED`): promotion happens in the four
files, by a person or a verification run. A proposed edge or finding with an `id` is
`ID_PROPOSED_BY_MODEL`: isolated sub-agents cannot allocate integers, so `lin:` and `fnd:` are assigned
after Fold by `tools/data-layer/assign_ids.py`, which reads the previous `lineage.yaml` and
`findings.yaml`, matches an edge by (relation, subject, object) and a finding by (kind, about,
statement) to keep an existing ID, and gives each new one the next integer above the previous
maximum. `map:` IDs are deterministic from entity, source and store, so interpretations may carry them.

### 2.9 `scorecard.yaml`

Written by `scorecard.py`; the baseline for the next run. Shape in §5.4.

## 3. Adapter contracts (`tools/data-layer/`)

Common: `--root <repo>` (default `.`), `--data-dir docs/02-design/data`, `--source <src:id>`, exit 0 on
success, 2 on refusal (no authorization, write access requested), 3 on a source it cannot read; a line
in `run.log` on every exit; never a traceback.

### 3.1 `intake_scan.py` (DL-1)

Reads the repo; writes `sources.proposed.yaml` in the same shape as §2.1 with `status: proposed` and
`declared_from` filled. The person edits it into `sources.yaml` at Stage 1.

| Detector | Looks at | Proposes |
|---|---|---|
| connection strings | `*.env*`, compose, settings and config files, IaC; schemes `postgres`, `mysql`, `mongodb`, `snowflake`, `bigquery`, `redshift`, `jdbc` | a source per distinct host and database, kind from the scheme; the value is never copied, only the file and line |
| env var names | `*_URL`, `*_URI`, `*_DSN`, `*_HOST` | a source with `kind: unknown` for the person to set |
| ORM and driver configs | SQLAlchemy `create_engine`, Django `DATABASES`, `pymongo.MongoClient`, `motor`, Prisma schema, Mongoose `connect` | a source tied to the code locator |
| dbt | `dbt_project.yml`, `profiles.yml` | `kind: dbt` |
| orchestrators | `dags/`, `airflow.cfg`, Dagster definitions | `kind: orchestrator` |
| IaC | Terraform resources for RDS, DocumentDB, Snowflake, BigQuery | a source per resource |

### 3.2 `code_adapter.py` (DL-3), Python in slice 1

Item kinds and what each carries:

| kind | locator | data |
|---|---|---|
| `orm_entity` | class line | class, table or collection, fields with declared types, declared keys and relationships |
| `store_literal` | call line | store name string, how it was reached (`db["x"]`, `Table("x")`, `FROM x`), tenant template if an f-string |
| `read` / `write` | call line | store, method (`find`, `select`, `insert`, `update`, `execute`), fields named in the call where literal |
| `join` | statement line | left store, right store, keys from `ON a = b`, `$lookup` `localField`/`foreignField`, or merge keys |
| `key_use` | line | store, field used as a lookup key |
| `ddl` | migration line | table, columns, constraints |

Files in other languages are counted under `coverage.files_skipped.other_language` and the stage
report names the count; nothing is guessed from them.

### 3.3 `profile_adapter.py` (DL-3, DL-8)

Offline mode: `--export <dir>` of JSON lines or CSV, one file per store, or a schema dump. Live mode:
`--live`, which requires `sources.yaml` to carry a complete `authorization` for the source with
`environment` equal to the source's; otherwise exit 2 and `result=refused reason=no_authorization`.
`--no-samples` keeps values out of the evidence file (ADR-8).

```python
class ReadOnlyFetch(Protocol):            # the only interface live drivers implement; no write method exists
    def stores(self) -> list[str]: ...
    def count(self, store: str) -> int: ...
    def sample(self, store: str, n: int) -> Iterable[dict]: ...
```

Items: `count` (rows, exact), `field_presence` (per field, percent of sampled rows with a non-empty
value, sample size), `key_candidates` (fields unique within the sample), `key_overlap` (for each key
pair the code adapter's `join` items name, the share of left values present on the right), `schema`
(from a dump). A driver import that fails writes `result=refused reason=driver_missing`.

## 4. Validator rules, `ci/data-layer/check_data_layer.py`

Finding model from `check_skips.py` (`{code, message, waivable}`, exit 2 on any non-waivable finding,
never a traceback) with a `locus` field added here; `--strict` turning warnings into exit 1 is borrowed
from `check_manifest_drift.py`. Exit 0 otherwise. Waivers live in the data layer's own file,
`ci/data-layer/data-layer-waivers.yaml`, with the same row shape as `manifest-waivers.yaml`
(`code, locus, owner, reason, tier_limit, revisit`), because that validator's locus grammar is
lowercase kebab and one foreign row disables its whole file. The locus is the kebab-cased entity name;
`--tier` defaults to 3; a lapsed `revisit` or a `tier_limit` below the run's tier does not suppress.
Only rows marked waivable can be waived.

Config, under `data_layer:` in `.hitl/config.yaml`, every key optional: `blocking` (false),
`stale_evidence_days` (90), `sample_rows` (500), `tier` (3).

| Code | Rule | Waivable | DL |
|---|---|---|---|
| `MALFORMED` | a file does not parse, has a duplicate key, or a top-level key of the wrong type | no | all |
| `SCHEMA_UNKNOWN_FIELD` | a key the schema does not list | no | DL-5 |
| `CONFIDENCE_UNKNOWN` | a `confidence` outside the three values, or missing | no | DL-5 |
| `NO_EVIDENCE` | an assertion with an empty `evidence` list | no | DL-3 |
| `EVIDENCE_UNRESOLVED` | an `evidence.file` that does not exist, or an `item` not in it | no | DL-3 |
| `EVIDENCE_TYPE_UNKNOWN` | an evidence file whose `evidence_type` is outside the nine | no | DL-3 |
| `CONFIRMED_WITHOUT_PROMOTER` | `confirmed` with no complete `confirmed_by` | no | DL-9 |
| `MODEL_WROTE_CONFIRMED` | an interpretation proposes `confirmed` | no | DL-9 |
| `CITATION_OUTSIDE_INPUTS` | an interpretation cites a file not in its `inputs` | no | DL-4 |
| `ID_DUPLICATE` | the same ID twice across the six files | no | all |
| `ID_MISSING` | an edge or finding in the four files with no `id` (Fold ran, `assign_ids.py` did not) | no | all |
| `ID_PROPOSED_BY_MODEL` | an interpretation edge or finding carrying an `id` | no | DL-4 |
| `ONTOLOGY_NAMES_IMPLEMENTATION` | `name` or a synonym equals, case-folded, a store name, activity ID, source ID or file basename anywhere in mappings, lineage or sources, except the entity's own mapped stores; or `name`, `definition` or a synonym contains a path separator, a URL scheme or a code-file extension | no | DL-5 |
| `NEGATIVE_AS_EDGE` | a relationship or edge with a `polarity`, `negative`, `absent` or `missing` key | no | DL-5 |
| `FINDING_SHAPED_AS_EDGE` | a finding with `subject`, `object`, `relation`, `from` or `to` | no | DL-5 |
| `EDGE_TERM_UNKNOWN` | a relation outside the PROV three | no | DL-5 |
| `EDGE_TYPE_MISMATCH` | subject or object type wrong for the relation (§2.5 table) | no | DL-5 |
| `EDGE_RULE_IS_CODE` | a `rule` containing a code fence, a `SELECT`, a `def ` or a `{`  | yes | DL-5 |
| `EDGE_READS_NEGATIVE` | a `rule` starting with a negative word | yes | DL-5 |
| `ACTIVITY_NO_FILES` | an activity with an empty `files` list | no | DL-10 |
| `MAPPING_ENTITY_UNKNOWN`, `EDGE_ENTITY_UNKNOWN`, `FINDING_ABOUT_UNKNOWN`, `QUESTION_NEEDS_UNKNOWN` | a reference to an ID that exists nowhere | no (question: yes) | DL-5, DL-2 |
| `SOURCE_UNKNOWN` | a mapping store on a source not in `sources.yaml` | no | DL-1 |
| `UNEXTRACTED_SOURCE_NOT_REVIEW` | a mapping or field on a `declared-not-extracted` source, or an entity all of whose mappings are on such sources, at a confidence other than `needs-review` | no | DL-1 |
| `LIVE_WITHOUT_AUTHORIZATION` | an evidence file with `access.mode: live` and no `authorization`, or a live source in `sources.yaml` without one, or an `authorization.environment` that differs from the source's `environment` | no | DL-8 |
| `WRITE_ACCESS_RECORDED` | `access.read_only` false, or a `run.log` line with a call outside `stores,count,sample,schema` | no | DL-8 |
| `BOUNDARY_NOT_IN_ONTOLOGY` | a manifest `boundary_entities` name with no ontology entity of that name or synonym | yes, `(boundary_not_in_ontology, <kebab-name>)` | DL-6 |
| `QUESTION_NEEDS_UNCONFIRMED` | a question whose needs list has no `confirmed_by` | yes | DL-2 |

With no `docs/02-design/data/` directory the validator prints one line, `data layer: absent`, and exits 0;
Conventions reports it as SKIPPED.

## 5. Scorecard, `ci/data-layer/scorecard.py` (DL-7, DL-2)

### 5.1 Metrics

| Metric | Computed as | Regression when |
|---|---|---|
| verification rate, entities | confirmed entities / entities | falls |
| verification rate, fields | confirmed fields / fields across mappings | falls |
| verification rate, edges | confirmed edges / edges | falls |
| entities with no mapping | entities with zero mappings, listed | rises |
| sources declared, not extracted | count and IDs | rises |
| evidence age | oldest, newest and median `taken_at` across evidence files, in days | oldest grows past `stale_evidence_days` (default 90) |
| open high-severity findings | findings with severity high and status open | rises |
| negative findings written as edges | edges carrying `EDGE_READS_NEGATIVE` | rises |
| answerable questions | per ADR-6: answerable / total, plus unconfirmed needs lists | falls |
| collisions | pairs of entities sharing a synonym (case-folded) or a natural key field name within the same source | rises |

### 5.2 Diff

`--baseline <scorecard.yaml>` prints every metric with before, after and delta, marks each regression,
and exits 1 with `--strict` when any regression exists; otherwise 0. A missing baseline is reported,
never treated as a regression or a pass.

### 5.3 Report

One page, plain English, written to stdout and to `scorecard.md` beside `scorecard.yaml`: the mode
line (advisory or blocking), the ten metrics as a table, the regressions first if any, the questions
not answerable with the IDs they wait on, the collisions by pair, and the open high findings by ID.

### 5.4 `scorecard.yaml`

```yaml
schema_version: "1.0"
run_at: 2026-09-30T12:00:00Z
mode: advisory
metrics:
  verification_rate: { entities: 0.40, fields: 0.62, edges: 0.33 }
  entities_without_mapping: [ent:delivery-slot]
  sources_not_extracted: [src:warehouse]
  evidence_age_days: { oldest: 3, newest: 0, median: 1 }
  open_high_findings: 1
  negative_edges: 0
  answerable: { yes: 3, no: 1, unconfirmed: 1, total: 5 }
  collisions: [[ent:shipment, ent:delivery-slot, "synonym: delivery"]]
```

## 6. Skill stage contracts (`ai/claude/map-data-layer/SKILL.md`, ADR-3, ADR-5)

State: `.hitl/data-layer/state.yaml` with one status per stage (`open`, `done`, `failed`) and the time.

| Stage | Handed | Produces | Done when |
|---|---|---|---|
| 1 Intake | the repo, `sources.proposed.yaml`, the person | `sources.yaml`, `questions.yaml` | every in-scope source has `environment`, `access`; every live one has `authorization`; at least one question is confirmed |
| 2 Extract | `sources.yaml` | evidence files, `run.log`, source `status` | every in-scope source is `extracted` or `declared-not-extracted` |
| 3 Interpret | `slice_evidence.py` first (handed `evidence/` and the candidate list); then per entity: its slice, `data-layer.schema.yaml`, the interpretation template | `evidence/slices/<entity>.yaml`; `interpretations/<entity>.yaml` | one slice and one interpretation per candidate entity; validator core clean on each |
| 4 Fold | the sub-agent: `interpretations/`, the schema, the four templates, and the previous `lineage.yaml` and `findings.yaml` read-only; then `assign_ids.py` (previous two files, the new four); then `manifest_tie.py` (`mappings.yaml`, `docs/system-manifest.yaml`) | the four files with IDs; the manifest block | validator clean or a named stage to re-run |
| 5 Validate | the four files, `questions.yaml`, `sources.yaml`, `evidence/` and `run.log`, `interpretations/`, the manifest, `data-layer-waivers.yaml`, `.hitl/config.yaml`, the last `scorecard.yaml` | findings list, tickets on confirmation, `scorecard.yaml`, `scorecard.md` | report printed |

Intake's authorization exchange, per live source:

> About to read `<source id>` on `<environment>` read-only with `<access>`, calls limited to listing
> stores, counting rows, sampling up to `<n>` rows. Nothing is written. Reply **AUTHORIZED** to proceed,
> or **SKIP** to record the source as declared, not extracted.

Interpret's candidate list is mechanical: every `orm_entity` class, every `store_literal` name not
already an ORM table, every dbt model, de-duplicated by name. The person may merge or drop candidates
before the sub-agents start. The sub-agent prompt names the entity, the file list, the schema and the
template, and nothing else; the wiring test (§9) reads the skill for that property.

## 7. Manifest tie, `tools/data-layer/manifest_tie.py` (ADR-1)

Input: `mappings.yaml`, `docs/system-manifest.yaml`. For each mapping, the domain of each path in
`written_by` and `read_by` is the manifest domain whose `files` list contains it. An entity written from
domain D and read from any other domain E is a boundary entity of D with `consumed_by` including E.
Output: `domains.<D>.boundary_entities.<EntityName>` with `shape` (field names and types from the
mapping) and `consumed_by`. Existing entries with the same name keep any human-added keys. Paths in no
domain are listed in the output as `unowned` and left out of the block. The manifest generator
overwrites the whole file on re-run (`generator.py` writes, it does not merge), so the block does not
survive a generator run; Step 3 prose says to re-run the tie after regenerating, and the validator's
boundary rule stays silent on an absent block.

## 8. Integration edits

| Where | Edit |
|---|---|
| `start-brownfield` Step 3 | copy `ci/data-layer/*.py` and `tools/data-layer/*.py` as the other validators are copied; the CI template only when `data_layer.blocking` is true |
| `start-brownfield` Step 7 | one paragraph: the data layer exists, `/hitl:dev-map-data-layer` builds it, run it when the manifest is confirmed |
| `check-conventions` Step 1 | a fifth block: run the validator (`--strict` only with blocking on), then the scorecard with `--baseline`; a validator exit 2 is listed under Warnings with the text "data layer: advisory mode" when blocking is off and under Violations when it is on; absent script or absent layer prints SKIPPED |
| `dev-update` | sync list and removal list name every new file |
| `ci/shipped-validators.sha256`, `ci/retired-tests.sha256` | hashes of the shipped validators and the test files |
| plugin `build.sh` | copy blocks for `ci/data-layer`, `tools/data-layer`, `templates/data-layer`; `data-layer.md` in `SHARED_PROSE` |
| `help`, `plugin.json`, `docs/README.md`, `docs/examples/README.md`, CHANGELOG | the entries |

## 9. Lints and wiring tests

- `test_wiring.py`: every stage in the skill names only its own inputs; the skill searches before
  filing or follows issue hygiene; the brownfield copy block and `dev-update` agree on the file list;
  the catalog is untouched by slice 1.
- Skill lint: body under the cap; every `shared/` path resolves in the built plugin.
- Plain-English lint: the scorecard report strings and every line the skill says.
- Manifest tests: every shipped validator hash present and labelled.
