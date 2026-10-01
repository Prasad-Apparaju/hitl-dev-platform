# Data layer conventions

`/hitl:dev-map-data-layer` (FR-31) writes a system's data layer under `docs/02-design/data/`: what the
business things are, where each one lives, how one dataset is made from another, and what is wrong
or unconfirmed. Everything below is what the validator (`ci/data-layer/check_data_layer.py`) holds
the files to. The shapes are in `shared/templates/data-layer/`; the design is the data-layer package
in the platform repo.

## The files

| File | Layer | Holds |
|---|---|---|
| `sources.yaml` | intake | declared sources: kind, environment, access, status, authorization for live reads |
| `questions.yaml` | intake | competency questions with the IDs each needs; a person confirms the needs list |
| `ontology.yaml` | business | entities: name, definition, synonyms, semantic relationships. Never a store, job, file or endpoint name |
| `mappings.yaml` | technical | per entity: store, fields with presence, natural key, scope, owner, counts, writers and readers |
| `lineage.yaml` | operational | activities (jobs, handlers) with the files they live in; edges in PROV terms (`used`, `wasGeneratedBy`, `wasDerivedFrom`) with the rule as prose |
| `findings.yaml` | annotations | negative and cross-cutting findings with a severity and an `about` list; never an edge |
| `evidence/` | raw | one file per source and type, written by scripts; `evidence/slices/` holds per-entity cuts with each item's origin |
| `interpretations/` | model | one file per entity, citing its slice only, `inputs:` listing what it was handed |
| `scorecard.yaml`, `scorecard.md` | report | the last run's metrics; the next run's baseline |
| `candidates.yaml` | intake to interpret | the entity list the person agreed to slice by |

## Three words for confidence

`confirmed`, `inferred`, `needs-review`. A model writes the second or third. `confirmed` needs
`confirmed_by: { who, at, how }` where `how` is `human` or `verification`. A mapping on a source that
was declared and not extracted is `needs-review`, and so is an entity whose every mapping is.

## Every assertion cites evidence

`evidence: [{ file: evidence/<source>/<type>-<ts>.yaml, item: ev:<source>/<type>/<nnnn> }]`. An empty
list is rejected. The four files cite source evidence; interpretations cite their slice, and Fold
rewrites to the origin. Evidence types: `schema`, `query_history`, `catalog`, `dbt_manifest`, `code`,
`profile`, `document`, `design`, `human`, `slice`.

## Read-only, and authorized before any live read

Adapters never write to a source. A live source with read access carries an `authorization` block
(`by`, `at`, `environment`, `statement: AUTHORIZED`) before any adapter touches it, and the
`environment` must equal the source's. `run.log` records every run with the calls it made; a call
outside `stores`, `count`, `sample`, `schema`, `scan` is rejected.

## Off by default, advisory by default

A repo without `docs/02-design/data/` runs every workflow unchanged; Conventions prints one SKIPPED
line. With the files present, the validator rejects a malformed or rule-breaking file in every mode.
With `data_layer: { blocking: true }` in `.hitl/config.yaml`, Conventions lists a validator failure
under Violations and the CI template fails the build; otherwise under Warnings with the words
"data layer: advisory mode". Other keys under `data_layer:`: `stale_evidence_days` (90), `sample_rows`
(500), `tier` (3).

## Waivers

One rule is waivable: a manifest boundary entity with no ontology entity or synonym. Rows go in
`ci/data-layer/data-layer-waivers.yaml` with the kebab-cased entity name as locus, an owner, a reason,
a `tier_limit` and a `revisit` date. A lapsed row does not suppress.

## Wording on the page

The scorecard report and every line the skill says follow `shared/plain-english.md`. A finding's
statement carries the numbers. No praise, no blame.
