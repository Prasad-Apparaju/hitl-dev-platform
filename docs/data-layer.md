# Data layer

What the business things in a system are, where each one lives, how one dataset is made from
another, and what is wrong or unconfirmed, written down once with evidence and kept next to the
system manifest.

```
/hitl:dev-map-data-layer
```

Five stages, each re-runnable: intake (declare the sources, write the questions the layer must
answer, authorize any live read), extract (scripts read the repo and the stores), interpret (one
model context per entity, handed only that entity's evidence), fold (one context writes the four
files from the interpretations), validate (a fail-closed validator, a scorecard, findings offered as
tickets). Output under `docs/02-design/data/`.

## What you get

| File | Answers |
|---|---|
| `ontology.yaml` | What is this thing? Entities with definitions, synonyms and semantic relationships |
| `mappings.yaml` | Where does it live? Stores, fields with presence, keys, owner, who writes and reads it |
| `lineage.yaml` | How was it made? Jobs and the PROV edges between datasets, with the rule as prose |
| `findings.yaml` | What is wrong? A field the code reads that is empty on every row, two entities sharing a name, a source nobody could reach |
| `scorecard.md` | How good is the layer, and can it answer the questions you wrote at intake |

Every assertion carries one of three confidences (`confirmed`, `inferred`, `needs-review`) and cites
the evidence it was read from. A model never writes `confirmed`; a person or a verification run does.

## Before you start

- A confirmed system manifest (`docs/system-manifest.yaml`), so boundary entities can be derived.
- For each store: an export (`<store>.jsonl` or `.csv`, one per store, plus a schema dump for a
  relational database) or a read-only login. Live reads happen only after you reply AUTHORIZED to a
  prompt that names the environment and the calls.
- The questions people actually ask of the data. The scorecard measures the layer by them.

## What the first run looks like

| Stage | You do | Scripts do |
|---|---|---|
| Intake | confirm the proposed sources, give the questions, authorize or skip each live source | scan the repo for connection strings, ORM configs, compose files, IaC |
| Extract | hand over exports where there is no live access | read code (Python first), profile stores: counts, field presence, key overlap |
| Interpret | merge or drop the candidate entities | slice the evidence per entity; one model context each writes an interpretation |
| Fold | nothing | one context writes the four files; a script numbers edges and findings; a script derives the manifest's boundary entities |
| Validate | confirm the list of findings to file; promote entries to confirmed | validator, scorecard, baseline diff |

## Keeping it honest

- The validator rejects an ontology entry that names a store, job, file or endpoint; a negative
  statement written as an edge; a fourth confidence value; an assertion with no evidence; a
  confirmed entry nobody promoted; a citation outside what the interpreting context was handed.
- The scorecard reports verification rates, entities with no mapping, sources declared and not
  extracted, evidence age, open high findings, questions answerable, and name collisions, and
  diffs against the last run.
- Off by default. A repo without `docs/02-design/data/` is unchanged. Advisory by default: Conventions
  and the CI template print findings and pass, until you set `data_layer: { blocking: true }` in
  `.hitl/config.yaml`.

## Config

```yaml
# .hitl/config.yaml
data_layer:
  blocking: false            # true: validator failures and scorecard regressions fail the build
  stale_evidence_days: 90    # the oldest evidence snapshot may be this old before it counts as a regression
  sample_rows: 500
  tier: 3                    # the tier a waiver's tier_limit is compared with
```

## Limits in this version

- The code adapter reads Python. Other languages are counted and never guessed from.
- Live profiling supports PostgreSQL and MongoDB through a read-only fetch layer; other stores go
  through exports.
- Catalogs, dbt, orchestrators, BI tools, greenfield authoring, deploy-time verification and the
  extraction schema for document graphs are later slices of the same epic.

The conventions the validator enforces are in the plugin's `shared/data-layer.md`. A worked example
with a synthetic app, exports, evidence, interpretations, the four files and a baseline scorecard is
at `docs/examples/data-layer/`.
