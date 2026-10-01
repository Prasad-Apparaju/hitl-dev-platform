# Data Layer: Architecture Decision Records

> Status: **proposed, v1 (2026-09-30)**, Phase 0 of the [implementation plan](05-implementation-plan.md).
> Decisions for FR-31 slice 1. HLD: [`01-design.md`](01-design.md); LLD: [`03-lld.md`](03-lld.md);
> requirements: [`../../01-product/data-layer/requirements.md`](../../01-product/data-layer/requirements.md).
> ADR-9, ADR-11 and ADR-13 settle things the 2026-09-25 edit of
> [#131](https://github.com/Prasad-Apparaju/hitl-dev-platform/issues/131) added after the requirements
> were cut; they are marked **for the owner to confirm**.

---

## ADR-1: The ontology is the source of the manifest's boundary entities; Fold writes the block

**Context.** DL-6 says every manifest `boundary_entity` must be an ontology entity. The manifest
template has no `boundary_entities` field and the generator emits only a DRAFT `entity_crossing`
string per domain pair. On a generated brownfield manifest the rule is vacuous.

**Decision.** The ontology is the source. After Fold, `tools/data-layer/manifest_tie.py` derives
`domains.<d>.boundary_entities` from mappings: an entity whose stores are written from files in domain
D and read from files in domain E is a boundary entity of D consumed by E. It writes the block with
`shape` from the mapping's fields and `consumed_by` from the readers, and keeps any human edits by
entity name on its own re-run. The manifest generator overwrites the whole file on its re-run, so the
tie is re-run after it; the block is derived, never hand-maintained. The validator's boundary-entity
rule is waivable through the data layer's own `ci/data-layer/data-layer-waivers.yaml` (same row shape
as the manifest-agentic file, kebab-cased entity name as locus, `--tier` default 3). The shared file is
not used: its locus grammar rejects foreign rows, and one such row disables every waiver in it.

**Alternatives.** The generator guesses a block (no evidence behind it). The validator reads
`entity_crossing` strings (free text, not entities).

**Consequences.** (+) The manifest's cross-domain surface is derived from evidence and stays in step
with the layer. (+) Plugin #24's "full persistence surface" is `mappings.yaml`, not a second doc.
(−) The tie script edits a file another generator owns; it touches only the one block and is idempotent.

---

## ADR-2: Slice 2 activates on the impact record; intake asks nothing new

**Context.** DL-11 asked one new intake question. The impact record already has `surfaces: data` and
`data_migration`, and `baseline` and `sec_design` already engage on record fields.

**Decision.** The `data_layer` step engages on `{ any: [surfaces:data, data_migration] }`. One
question stays, asked only when neither is set and the change names an entity in its issue or impact
brief: "does this change the meaning or derivation of an entity without changing a stored shape?" A
yes sets `surfaces: data` with provenance `human`. Built in slice 2; the predicate is fixed now so
slice 1's files carry what the rule needs (entity IDs in mappings and lineage).

**Alternatives.** A new predicate field (a second source for the same fact). Always ask (the
per-change tax the requirements review rejected).

**Consequences.** (+) No new field, no new question in the common case. (−) A derivation-only
change the rules cannot see depends on the person answering the one question honestly.

---

## ADR-3: One skill, five re-runnable stages, no modes flag

**Context.** #131 open question 1: one skill with modes or a family of skills.

**Decision.** One skill, `/hitl:dev-map-data-layer`, with an optional stage argument
(`intake`, `extract`, `interpret`, `fold`, `validate`, or an entity ID for a single re-interpret).
Stage state lives in `.hitl/data-layer/state.yaml`. With no argument the skill resumes at the first
stage not marked done.

**Alternatives.** Five skills (five entries in help, five banners to keep aligned, and the stage
order lives nowhere). Modes as flags on one skill (same as stages, with worse names).

**Consequences.** (+) The stage order is in one file; a failed Validate names the stage to re-run.
(−) The skill body is long; it stays under the lint cap by keeping every contract in `shared/`.

---

## ADR-4: Adapters are pure Python with lazy optional drivers; the offline export mode is the tested path

**Context.** Adapters touch stores outside the repo. CI has no stores. Drivers differ per team.

**Decision.** Each adapter runs on the standard library plus PyYAML. Store drivers (`psycopg`,
`pymongo`, `snowflake-connector`) are imported inside the live fetch layer only, and an import failure
is recorded in `run.log` as access not obtained, never raised. The offline mode reads exports the
person produced (JSON lines, CSV, a schema dump) and is the mode the tests, the fixture and the
validation review use. Live mode is the same code behind a `ReadOnlyFetch` interface with no write
method; it refuses to start unless the source's `authorization` block in `sources.yaml` is complete
(DL-8).

**Alternatives.** Driver-first adapters (untestable in CI, and the risk class the requirements review
flagged). A fetch layer with a write method that is "never called" (the test cannot prove a negative
about an interface that has the method).

**Consequences.** (+) The tested surface is small and the live path is a thin shell over it.
(+) Air-gapped teams drop exports into `evidence/` by hand (FR-24). (−) Live profiling of a large
store is sampled, not full; counts are exact, presence and overlap are from the sample, and the
envelope says so.

---

## ADR-5: Stage isolation is enforced by what a stage is handed, recorded in `inputs:`, checked by the validator

**Context.** DL-4 asks that each stage read only the previous stage's artifacts. Prose in a skill
cannot enforce that.

**Decision.** Evidence files are one per source and type, so `slice_evidence.py` first writes one
slice per candidate entity (the items that name its class, stores or keys, each with its origin). The
skill builds every Interpret prompt from an explicit file list (that entity's slice, the schema, the
interpretation template) and names no other file. The interpretation
records the list as `inputs:`. The validator rejects any evidence reference whose file is not in the
interpretation's `inputs` (`CITATION_OUTSIDE_INPUTS`, non-waivable). The Fold sub-agent is handed the
`interpretations/` directory and the previous `lineage.yaml` and `findings.yaml` read-only, nothing
else; the scripts that follow it get only what LLD §6 lists. A wiring test reads the skill and checks that each
stage's prompt names only its own inputs.

**Alternatives.** Trust the prose. A single long-context pass (the method the field project showed
does not scale past a handful of entities, and the reason the talk's pipeline worked).

**Consequences.** (+) Isolation is a property of the artifacts, so a different model can re-run a stage
from the same inputs. (−) The slicer decides what an entity's evidence is before the model sees it; an
item it misses is invisible to that interpretation and shows on the scorecard as an entity without a
mapping. (−) Isolated sub-agents cannot allocate integer IDs, so edges and findings leave Interpret
without one and `assign_ids.py` numbers them after Fold against the previous files.

---

## ADR-6: A question is answerable when every ID it needs exists at a confidence other than `needs-review`

**Context.** DL-2 makes competency questions the acceptance criteria. "Answerable" needs a mechanical
definition the scorecard can compute.

**Decision.** A question record carries `needs: { entities, mappings, edges }`. It is answerable when
every listed ID exists in the four files with `confidence` of `confirmed` or `inferred`. The model
drafts the needs list at intake; the person confirms it (`confirmed_by`), and an unconfirmed needs
list counts as not answerable. The scorecard reports answerable, not answerable, and unconfirmed.

**Alternatives.** Ask a model whether the layer answers the question (not reproducible, and the
scorecard must be a script). Count a question answered when its entities exist (ignores the edges
the question is usually about).

**Consequences.** (+) Deterministic, diffable, and a change that drops an edge to `needs-review`
visibly un-answers a question. (−) "Exists at inferred" is a weaker claim than "answered"; the
scorecard labels it so.

---

## ADR-7: Findings become tickets only through issue hygiene, never into the incident registry

**Context.** #131 open question 3: does `findings.yaml` seed the incident registry.

**Decision.** No. Stage 5 lists open findings of severity high and medium, one line each, and takes
one confirmation for the list, per `shared/issue-hygiene.md` (search first, one confirmation per
batch, at most one rollup when unattended). A filed finding records `status: ticketed:#N`. The
incident registry is for incidents; a finding that caused one is linked from the incident, by a person.

**Consequences.** (+) No ticket is created without a person. (−) A finding nobody confirms stays open
in the file; the scorecard counts it.

---

## ADR-8: The files live at `docs/02-design/data/`

**Context.** Brownfield writes HLDs and LLDs under `docs/02-design/technical/`; the manifest is
`docs/system-manifest.yaml`.

**Decision.** `docs/02-design/data/` holds the six YAML files, `evidence/`, `interpretations/` and
`scorecard.yaml`. Evidence files are committed; a team whose exports hold sensitive values profiles
with `--no-samples` so the envelope carries counts and presence only, and the secrets scan in
Conventions covers the folder like any other.

**Alternatives.** `.hitl/` (hidden, not a document people read). `docs/02-design/technical/data/`
(a sibling of HLDs, but the layer is not an HLD).

**Consequences.** (+) Mappings sit beside the LLDs they cite. (−) `evidence/` grows per run; each run
replaces the previous file for the same source and type, so the folder holds one snapshot per pair.

---

## ADR-9: Off by default, advisory by default, blocking per repo (for the owner to confirm)

**Context.** The 2026-09-25 edit of #131 adds an adoption model: nothing in HITL depends on the layer,
every check comments by default and blocks only when a team sets blocking on per repo. Requirements
v1 DL-10 and DL-11 said Reconcile "cannot close" with a stale edge.

**Decision.** Three tiers of strictness, none of them a new gate:

| What | Default | With `data_layer: { blocking: true }` in `.hitl/config.yaml` |
|---|---|---|
| The four files are malformed or break a structural rule (LLD §4 table) | the validator exits 2; Conventions reports it; CI template not installed | the CI template is installed and fails |
| A change-level check (slice 2: missing delta, stale edge, scorecard regression) | a comment on the change, step closes | the step cannot close |
| The layer is absent | one SKIPPED line, nothing else | same |

In slice 1 the two modes differ in one place: Conventions lists a validator exit 2 under Warnings with
the text "data layer: advisory mode" when blocking is off, and under Violations when it is on.

Requirements v1.1 amends DL-10 and DL-11 to "with blocking on". Slice 1 ships only the first row.

**Alternatives.** Blocking by default (what v1 said; the owner's later edit reverses it). Advisory
always (then the invalid-file case has no teeth and the layer rots).

**Consequences.** (+) A team can turn the layer on and off without losing data. (−) Two repos with the
same files can report differently; the scorecard header prints the mode.

---

## ADR-10: Slice 1 ships the skill standalone; no brownfield catalog step until slice 2

**Context.** The brownfield workflow is 11 numbered steps in `workflows.yaml`, mirrored in the catalog
and in every open onboarding's change file. Adding a step changes `total` and needs a migration.

**Decision.** Slice 1 adds no step. `start-brownfield` Step 3 copies the validators and Step 7 says in
one paragraph that the data layer exists and how to run it, once (the issue's "mentioned once" rule).
A catalog step, if wanted, lands with slice 2's migration.

**Consequences.** (+) A minor release, no migration. (−) Nothing in the onboarding breadcrumb shows the
layer was skipped; the scorecard's absence in Conventions is the only signal.

---

## ADR-11: The fixture is synthetic; the field project is the private acceptance run (for the owner to confirm)

**Context.** The field project's evidence is client data and this repo is public.

**Decision.** `docs/examples/data-layer/` is a small invented fulfilment app: an ORM model, a document
store read through a driver, a nightly job that writes a cache, offline exports for two stores, a
third source declared and not extracted, one synonym collision, one negative finding, five
competency questions, interpretations, the four files and a baseline scorecard. The owner runs the
skill on the field project privately and reports the scorecard against the hand-built pass; that
report is the slice's acceptance evidence, kept out of this repo.

**Alternatives.** A redacted export of the field project (redaction of a document store is never
provably complete, and this repo is public). A public open-source app as the fixture (real, but its
data model is not under this repo's control and has no planted collision or negative finding).

**Consequences.** (+) Every test and the validation review run on public data. (−) The fixture cannot
show scale; the field run does.

---

## ADR-12: Interpret runs only in the skill; its isolation is tested mechanically

**Context.** CI has no model. Interpret is the one stage a model performs.

**Decision.** Extract, Fold's manifest tie, Validate and the scorecard are scripts tested in CI from
the fixture's committed interpretations. Interpret and the Fold sub-agent are exercised by the skill
during the validation review on the fixture. Their isolation is a validator rule (ADR-5), so CI
proves the property on any interpretation set, including ones a model wrote.

**Consequences.** (+) CI is deterministic. (−) The quality of a model's interpretation is judged by the
review and the field run, not by a test.

---

## ADR-13: One evidence core for both layers (for the owner to confirm)

**Context.** Part B of #131 (business rules, FR-35) says it shares FR-31's evidence model and scorecard,
and the issue's slice list puts rule extraction first.

**Decision.** `data-layer.schema.yaml` defines the shared core once: the confidence enum, the evidence
envelope and item locator, the `evidence` reference, `confirmed_by`, `inputs:` on an interpretation.
The four data files and the future `rules.yaml` are instances of it. The validator is a core (parse,
confidence, evidence resolution, promoter, citation inside inputs, ID uniqueness) plus a rule table
per file family, so adding `rules.yaml` is a table, not a second validator. The scorecard reports per
family. Which family is built first is a release-planning call recorded in the plan, not here.

**Alternatives.** One schema per family (two confidence enums and two evidence shapes to keep aligned,
and the issue's "shares the evidence model" becomes prose). Defer the shared core until FR-35 is
designed (the data layer then ships a schema FR-35 must adopt unchanged or fork).

**Consequences.** (+) Part B does not re-decide confidence, evidence or isolation. (−) The core is
designed before its second user exists; the rule table keeps family-specific rules out of it.
