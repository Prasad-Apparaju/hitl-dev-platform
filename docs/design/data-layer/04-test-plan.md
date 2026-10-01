# Data Layer: Test Plan

> Status: **draft v1 (2026-09-30)**, Phase 0. Conformance for FR-31 slice 1 against the HLD
> [`01-design.md`](01-design.md), ADRs [`02-adrs.md`](02-adrs.md) and LLD [`03-lld.md`](03-lld.md).
> Discipline carried from First Pass: every fail-closed case is asserted **by mutation** of the
> fixture; a green happy path is not acceptance. Tests live in `ci/data-layer/test_*.py` and
> `tools/data-layer/test_*.py`, run from the fixture at `docs/examples/data-layer/`.

## 0. What must be impossible (the fail-closed core)

Each row takes the clean fixture, applies the mutation, and requires the named code with
`waivable: false` and exit 2. These are the framework's guarantee (LLD §4).

| ID | Mutation of the fixture | Required outcome | DL |
|---|---|---|---|
| **NEG-1** | an ontology entity whose definition names `jobs/nightly_eta.py` | `ONTOLOGY_NAMES_IMPLEMENTATION` | DL-5 |
| **NEG-1b** | a definition reading "served by the orders-service over gRPC"; a synonym equal to a manifest domain name | `ONTOLOGY_NAMES_IMPLEMENTATION` | DL-5 |
| **NEG-2** | an ontology synonym equal to another entity's store name (`eta_cache` on `Order`); and, as the pass case, `orders` as a synonym of `Order` whose own table is `orders` must NOT fire | `ONTOLOGY_NAMES_IMPLEMENTATION` | DL-5 |
| **NEG-3** | a lineage edge with `negative: true` | `NEGATIVE_AS_EDGE` | DL-5 |
| **NEG-4** | a finding carrying `subject` and `object` | `FINDING_SHAPED_AS_EDGE` | DL-5 |
| **NEG-5** | `confidence: probable` | `CONFIDENCE_UNKNOWN` | DL-5 |
| **NEG-6** | a mapping with `evidence: []` | `NO_EVIDENCE` | DL-3 |
| **NEG-7** | an evidence reference to an item ID not in the file | `EVIDENCE_UNRESOLVED` | DL-3 |
| **NEG-8** | an evidence file with `evidence_type: guess` | `EVIDENCE_TYPE_UNKNOWN` | DL-3 |
| **NEG-9** | `confidence: confirmed` with `confirmed_by` removed | `CONFIRMED_WITHOUT_PROMOTER` | DL-9 |
| **NEG-10** | an interpretation proposing a `confirmed` entry | `MODEL_WROTE_CONFIRMED` | DL-9 |
| **NEG-11** | an interpretation citing a slice or evidence file absent from its `inputs` (another entity's slice, or the source file its slice came from) | `CITATION_OUTSIDE_INPUTS` | DL-4 |
| **NEG-12** | the same `ent:` ID in two entities; the same `lin:` in two edges | `ID_DUPLICATE` | all |
| **NEG-12a** | an edge in `lineage.yaml` with no `id` | `ID_MISSING` | all |
| **NEG-12b** | an interpretation edge carrying `id: lin:1` | `ID_PROPOSED_BY_MODEL` | DL-4 |
| **NEG-13** | a lineage relation `derivedFrom` (not PROV spelling) | `EDGE_TERM_UNKNOWN` | DL-5 |
| **NEG-14** | `used` with a `map:` subject and an `act:` object | `EDGE_TYPE_MISMATCH` | DL-5 |
| **NEG-15** | an activity with `files: []` | `ACTIVITY_NO_FILES` | DL-10 |
| **NEG-16** | a mapping on `src:warehouse` (declared, not extracted) at `inferred`; an entity whose only mapping is on it at `inferred` | `UNEXTRACTED_SOURCE_NOT_REVIEW` | DL-1 |
| **NEG-17** | a mapping whose `store.source` is `src:nowhere` | `SOURCE_UNKNOWN` | DL-1 |
| **NEG-17a** | a mapping whose `entity` is `ent:nowhere`; an edge whose subject is `ent:nowhere`; a finding `about: [ent:nowhere]` | `MAPPING_ENTITY_UNKNOWN`, `EDGE_ENTITY_UNKNOWN`, `FINDING_ABOUT_UNKNOWN` | DL-5 |
| **NEG-18** | an evidence file with `access.mode: live` and no `authorization` | `LIVE_WITHOUT_AUTHORIZATION` | DL-8 |
| **NEG-19** | a `sources.yaml` live source whose `authorization.environment` differs from its `environment` | `LIVE_WITHOUT_AUTHORIZATION` | DL-8 |
| **NEG-20** | an evidence file with `access.read_only: false`; a `run.log` line with `calls=insert` | `WRITE_ACCESS_RECORDED` | DL-8 |
| **NEG-21** | a manifest boundary entity `Invoice` with no ontology entity or synonym, and no row in `ci/data-layer/data-layer-waivers.yaml` | `BOUNDARY_NOT_IN_ONTOLOGY` (waivable: the only one in this table) | DL-6 |
| **NEG-22** | an unknown top-level key in `ontology.yaml` | `SCHEMA_UNKNOWN_FIELD` | DL-5 |
| **NEG-23** | `ontology.yaml` as a YAML list; a duplicate key; a tab-indented file; an empty file | `MALFORMED`, exit 2, no traceback | all |
| **NEG-24** | a `data-layer-waivers.yaml` row for `BOUNDARY_NOT_IN_ONTOLOGY` with `revisit` in the past, or `tier_limit` below `--tier` (default 3), or a locus that is not the kebab-cased entity name | the finding is not suppressed | DL-6 |
| **NEG-25** | a waiver naming a non-waivable code (`NO_EVIDENCE`) | the finding is not suppressed | DL-3 |

Every code in LLD §4 appears at least once above or in §3; `test_every_code_has_a_mutation` asserts that
by reading the validator's code table. The waivable warnings are in VAL-2.

## 1. Fixture and schemas (Phase A)

- **FIX-1** the fixture's six files, evidence folder and interpretations validate clean: exit 0, no findings.
- **FIX-2** the fixture holds, by assertion on the files: one `declared-not-extracted` source whose
  dependants are `needs-review`; one `confirmed` negative finding with `how: verification`; one synonym
  collision; five questions of which three are answerable, one not, one unconfirmed.
- **FIX-3** every template in `ai/shared/templates/data-layer/` parses and carries only keys the schema lists.
- **FIX-4** the fixture's interpretations cite only their own slice (the isolation property holds on the
  committed set, so NEG-11's mutation is the only way to break it), and the four files cite origin
  evidence files only, never a slice.
- **FIX-5** the fixture's `evidence/slices/` are reproduced byte-identical by `slice_evidence.py` from the
  evidence files and the candidate list.

## 2. Adapters (Phase C)

- **SCAN-1** `intake_scan.py` on the fixture proposes every declared source with the right `kind` and a
  `declared_from` that resolves to a real file and line; no connection-string value appears in the output.
- **SCAN-2** a repo with no detectable source proposes an empty list and exits 0.
- **CODE-1** `code_adapter.py` finds the ORM entity, the store literals, the reads and writes, the join and
  its keys, the tenant naming template; item locators resolve to the quoted line.
- **CODE-2** a non-Python file is counted under `files_skipped.other_language` and yields no item.
- **PROF-1** offline mode on the exports yields exact counts, field presence per field, key candidates and
  key overlap for the pair the code adapter named.
- **PROF-2** `--no-samples` writes no field values into the evidence file.
- **AUTH-1** live mode with no `authorization` block exits 2, writes `result=refused reason=no_authorization`,
  and the fake fetch records zero calls.
- **AUTH-2** live mode with a complete block runs against a fake `ReadOnlyFetch`; the fake asserts that only
  `stores`, `count`, `sample` were called and that the object has no attribute named `insert`, `update`,
  `delete`, `write` or `execute`.
- **AUTH-3** `authorization.environment` not equal to the source's environment exits 2.
- **SRC-1** a live driver whose import fails writes `result=refused reason=driver_missing` and exits 3;
  the source stays `declared-not-extracted`.
- **SRC-2** every adapter exit, including refusals, leaves one line in `run.log`.
- **ENV-1** every evidence file an adapter writes passes the validator core (envelope, types, IDs).

## 3. Validator (Phase B)

- **VAL-1** the fixture passes; each NEG-* row above fails with its code; the finding carries a `locus`
  naming the entry.
- **VAL-2** warnings (`EDGE_RULE_IS_CODE`, `EDGE_READS_NEGATIVE`, `QUESTION_NEEDS_UNKNOWN`,
  `QUESTION_NEEDS_UNCONFIRMED`) exit 0 without `--strict` and 1 with it.
- **VAL-3** no `docs/02-design/data/` directory prints `data layer: absent` and exits 0.
- **VAL-4** hostile input (binary file, a 50 MB YAML, a symlink out of the tree, a file named `..`) exits 2
  with `MALFORMED`, never a traceback.
- **VAL-5** the validator reads the manifest only for `boundary_entities`; a manifest that fails to parse
  is one `MALFORMED` finding with the manifest as locus, and the four files are still checked.
- **VAL-6** the validator core (parse, confidence, evidence, promoter, inputs, IDs) runs unchanged on a
  `rules.yaml` stub with the shared fields (ADR-13), so adding a family is a rule table only.

## 4. Scorecard (Phase B)

- **SCORE-1** on the fixture the metrics equal hand-computed values: verification rates, the no-mapping
  entity, the unextracted source, the one high finding, zero negative edges, answerable 3 of 5 with one
  unconfirmed, the one collision pair.
- **SCORE-2** answerability (ADR-6): dropping one needed edge to `needs-review` flips its question to not
  answerable; removing `confirmed_by` from a question's needs flips it to unconfirmed.
- **SCORE-3** collisions: a synonym differing only by case still collides; a natural key shared across
  two sources does not.
- **SCORE-4** evidence age uses `taken_at`, not file mtime.
- **BASE-1** `--baseline` on an identical run reports zero deltas and no regression.
- **BASE-2** each regression direction in LLD §5.1 is produced by one mutation and marked; a metric
  moving the other way is not.
- **BASE-3** a regression exits 1 only with `--strict`; a missing baseline is reported and exits 0.
- **BASE-4** the report is one page in plain English: no em dash, none of the words the plain-English
  lint rejects, regressions listed before anything else.

## 4a. Slicer and ID assigner (Phase C, D)

- **SLICE-1** every item in a slice carries an `origin` that resolves to the source file and item; every
  item whose `data` names the entity's class, store or tied key is in the slice; an item naming only
  another entity is not.
- **SLICE-2** an entity with no matching item gets an empty slice, not a missing file, so the stage
  reports it rather than skipping it.
- **IDS-1** `assign_ids.py` on the fixture's previous files plus a new edge gives the new edge the next
  integer and keeps every existing ID; an existing edge re-proposed with the same (relation, subject,
  object) keeps its ID; a finding matched by (kind, about, statement) keeps its ID.
- **IDS-2** two new edges proposed by two interpretations get two different IDs.
- **IDS-3** citations in the four files point at origin files after Fold (FIX-4), never at a slice.

## 5. Manifest tie (Phase D)

- **TIE-1** on the fixture, the entity written in one domain and read in another appears under the
  writer's `boundary_entities` with the reader in `consumed_by`.
- **TIE-2** an entity read and written inside one domain is not a boundary entity.
- **TIE-3** re-running keeps a human-added key on an existing entry and updates `shape`.
- **TIE-4** a path in no manifest domain is listed as `unowned` and produces no entry.
- **TIE-5** the block the tie writes passes `BOUNDARY_NOT_IN_ONTOLOGY` by construction.
- **TIE-6** after a manifest generator re-run the block is gone and the validator is silent on it; re-running
  the tie restores it unchanged.

## 6. Skill and wiring (Phase D, E)

- **WIRE-1** each stage's prompt in the skill names only the inputs LLD §6 lists; the Fold sub-agent names
  `interpretations/` and the two previous files and no evidence path; an Interpret sub-agent names one
  slice and no other entity's slice or any source evidence file.
- **WIRE-2** the skill's authorization exchange contains the literal **AUTHORIZED** and **SKIP** and no
  live read command precedes it in the stage.
- **WIRE-3** the skill's ticket step cites issue hygiene or searches first (existing wiring test).
- **WIRE-4** the brownfield copy block, `dev-update`'s sync and removal lists, `shipped-validators.sha256`
  and the plugin build script name the same file set.
- **WIRE-5** `workflows.yaml` and the catalog are byte-identical before and after slice 1 (ADR-10).
- **LINT-1** skill body under the cap; every `shared/` path the skill names exists in the built plugin.
- **LINT-2** every string the skill tells the model to say passes the plain-English lint.

## 7. Acceptance scenarios (requirements §8.2, slice 1 rows) and where each is proven

| Scenario | Proven by |
|---|---|
| 1 sources from scan plus confirmation; declined source is `declared-not-extracted` with dependants `needs-review` | SCAN-1, FIX-2, NEG-16, the fixture run in the validation review |
| 2 competency questions collected; scorecard reports answerable | FIX-2, SCORE-1, SCORE-2 |
| 3 interpretation per entity from that entity's evidence only; fold handed interpretations only | NEG-11, FIX-4, WIRE-1 |
| 4 validator rejects a service name in the ontology, a negative as an edge, a fourth confidence, a boundary entity absent | NEG-1 to NEG-5, NEG-21 |
| 5 scorecard diffs against a baseline and reports a collision | SCORE-1, SCORE-3, BASE-1, BASE-2 |
| 6 no live read before AUTHORIZED; run log shows read-only | AUTH-1 to AUTH-3, NEG-18 to NEG-20, SRC-2, WIRE-2 |

The field project run (ADR-11) is the private acceptance for scenario 5's scale and for the
verification-rate baseline; its report is not in this repo.

## 8. Validation review (Phase F)

One clean-context validation review, checklist = the six scenarios above plus NEG-1 to NEG-25 by
running the suite, on the fixture in a `CLAUDE_CONFIG_DIR` sandbox, one page, no adversarial pass.
Record at `.hitl/reviews/<change>-round1-correctness.yaml` in the 2.0 schema.
