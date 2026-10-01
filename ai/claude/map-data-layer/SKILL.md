---
description: >
  Build an existing system's data layer with evidence (FR-31): declared sources, competency
  questions, code and store evidence, one interpretation per entity in its own context, four files
  (ontology, mappings, lineage, findings), a validator and a scorecard. Use when a brownfield
  system's data is written down nowhere, when an agent cannot answer why a figure is what it is, or
  after onboarding once the manifest is confirmed. Five re-runnable stages.
argument-hint: "[intake | extract | interpret | fold | validate | ent:<id>]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this, and do not proceed with any other step:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

---

# Map the Data Layer

Five stages, each re-runnable on its own. Scripts read the repo and, with the person's stated
authorization, the stores. A model reads evidence one entity at a time and nothing else. The
conventions, file shapes and the wording rule are in `shared/data-layer.md`. Nothing here is a
workflow step: this writes nothing to the change file and posts nothing to any issue.

**Input:** $ARGUMENTS (optional: a stage name to re-run, or `ent:<id>` to re-interpret one entity;
empty resumes at the first stage not marked done in `.hitl/data-layer/state.yaml`).

## Step 0 — Resolve the tools and the state

```bash
# CLAUDE_PLUGIN_ROOT is unset in the Bash tool; a bare "$CLAUDE_PLUGIN_ROOT/..." becomes "/...".
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
DL="tools/data-layer";            [[ -f "$DL/code_adapter.py" ]]      || DL="$ROOT/shared/tools/data-layer"
CK="ci/data-layer";               [[ -f "$CK/check_data_layer.py" ]]  || CK="$ROOT/shared/ci/data-layer"
TPL="$ROOT/shared/templates/data-layer"   # the plugin ships the templates; product repos never hold a copy
DATA="docs/02-design/data"
[[ -f "$DL/code_adapter.py" && -f "$CK/check_data_layer.py" && -d "$TPL" ]] || echo "data-layer: tools not found; run /hitl:dev-update"
mkdir -p "$DATA" .hitl/data-layer
[[ -f .hitl/data-layer/state.yaml ]] || printf 'stages:\n  intake: open\n  extract: open\n  interpret: open\n  fold: open\n  validate: open\n' > .hitl/data-layer/state.yaml
cat .hitl/data-layer/state.yaml
```

If a tool is missing, stop and say so in one line. Otherwise pick the stage: the argument if given,
else the first stage whose state is `open`. Say which stage runs and why, in one line. When a stage
finishes, set its state to `done` with the time; when it fails, `failed`.

## Stage 1 — Intake (DL-1, DL-2, DL-8)

**Sources.** Run the scan and show the proposal:

```bash
python3 "$DL/intake_scan.py" --root . --out "$DATA/sources.proposed.yaml"
```

Walk the list with the person, one line per source: keep, rename, drop, or add one the scan missed
(a warehouse only analysts touch, a catalog). For each kept source ask for three things in one
question: the environment (`dev`, `staging`, `prod`, or `offline-export` when they will hand you an
export), the access they can grant (`read_only` or `none`), and whether it is in scope. Write the
result to `$DATA/sources.yaml` in the shape of `$TPL/sources.yaml`, `status: declared` on every row,
and delete the proposal file. Never copy a connection string's value anywhere.

**Competency questions.** Ask: "What must this layer be able to answer? Give me the questions, as
people ask them." Add the ones the problem statement and open tickets imply. For each, draft the
`needs` list (the entity, mapping and edge IDs it will take; IDs may not exist yet) and show the
list once for confirmation. Write `$DATA/questions.yaml` in the shape of `$TPL/questions.yaml`;
`confirmed_by` is the person who confirmed the needs list, with the time. At least one question.

**Authorization, per in-scope source with `mode: live` and `granted: read_only`.** Nothing reads a
live store before this reply. Ask exactly:

> About to read `<source id>` on `<environment>` read-only, calls limited to listing stores,
> counting rows and sampling up to 500 rows. Nothing is written. Reply **AUTHORIZED** to proceed, or
> **SKIP** to record the source as declared, not extracted.

On AUTHORIZED, write into that source's row:
`authorization: { by: <git user.email>, at: <now UTC>, environment: <the source's environment>, statement: AUTHORIZED }`.
On SKIP, set `access.granted: none` and `status: declared-not-extracted`. Any other reply is asked again.

Done when every in-scope source has `environment` and `access`, every live one with read access has
`authorization`, and `questions.yaml` has one confirmed question. Mark `intake: done`.

## Stage 2 — Extract (DL-3, DL-8): scripts only

For each in-scope source in `sources.yaml`, by kind. Nothing in this stage is written by a model.

| kind | command |
|---|---|
| `code` | `python3 "$DL/code_adapter.py" --root . --source <id> --data-dir "$DATA"` |
| `relational` or `document`, offline | ask for the export folder (`<store>.jsonl` or `.csv`, one per store) and, for relational, a schema dump; then `python3 "$DL/profile_adapter.py" --source <id> --data-dir "$DATA" --export <folder> --stores <its stores> [--schema-dump <file.sql>] --code-evidence "$DATA/evidence/<code source>/code-*.yaml"` |
| `relational` or `document`, live | `python3 "$DL/profile_adapter.py" --source <id> --data-dir "$DATA" --live --driver <postgres or mongo> --dsn-env <VAR> --code-evidence "$DATA/evidence/<code source>/code-*.yaml"` |
| anything else | not supported in this version; the source stays `declared-not-extracted` and the report says so |

`--no-samples` when the person says the exports hold values that must not be committed. Exit 2 is a
refusal (no authorization, a write requested): show the line the adapter printed and stop. Exit 3
means the source could not be read (driver missing, export missing): the script has already set the
source to `declared-not-extracted`; say so and continue with the next source. Every run leaves one
line in `$DATA/run.log`; show the new lines at the end of the stage.

Done when every in-scope source is `extracted` or `declared-not-extracted`. Mark `extract: done`.

## Stage 3 — Interpret (DL-4, DL-9): one context per entity

**Candidates.** Propose, then let the person merge, rename, drop or add (an entity the code names
but no store holds gets `stores: []` and a `fields:` list):

```bash
python3 "$DL/slice_evidence.py" --data-dir "$DATA" --propose
```

Edit `$DATA/candidates.yaml` as agreed, then slice:

```bash
python3 "$DL/slice_evidence.py" --data-dir "$DATA"
```

An empty slice means nothing in the evidence names that entity; say so and keep it (it will show on
the scorecard as an entity without a mapping).

**One sub-agent per candidate.** With `ent:<id>` as the argument, only that one. Use the Agent tool,
a general-purpose agent, clean context, one at a time or in parallel. The brief is built from a file
list and names nothing else. It is, verbatim, with the three paths filled in:

<!-- brief:interpret -->
> You are interpreting ONE entity of a system's data layer from evidence. Read exactly these three
> files and nothing else: `docs/02-design/data/evidence/slices/<name>.yaml` (the evidence),
> `<TPL>/data-layer.schema.yaml` (the schema) and `<TPL>/interpretation.yaml` (the shape to write).
> Write `docs/02-design/data/interpretations/<name>.yaml` for entity `ent:<name>`: under `proposed`,
> one ontology entry (name, a one- or two-sentence business definition, synonyms, semantic
> relationships), the mappings (store, fields with types and presence from the profile items, natural
> key, scope, written_by and read_by from the code locators), lineage activities and edges in PROV
> terms with the rule as prose, and findings for anything negative or contradictory. Rules: every
> assertion carries `confidence` of `inferred` or `needs-review` (never `confirmed`) and an `evidence`
> list citing the slice file and item IDs you actually used; a definition never names a store, job,
> file or endpoint; edges and findings carry no `id`; put what you could not settle in
> `open_questions`. `inputs:` lists the three paths above. Reply with the path you wrote.
<!-- /brief -->

After each returns, run the validator on the folder; a finding against `interpretations/<name>.yaml`
is sent back to that one sub-agent with the finding text, once. Done when every candidate has an
interpretation and the validator reports no finding against `interpretations/`. Mark `interpret: done`.

## Stage 4 — Fold (DL-5, DL-6): interpretations only, then two scripts

Keep the previous `lineage.yaml` and `findings.yaml` for the ID assigner:

```bash
mkdir -p .hitl/data-layer/previous
for f in lineage.yaml findings.yaml; do [[ -f "$DATA/$f" ]] && cp "$DATA/$f" .hitl/data-layer/previous/; done
```

**One sub-agent**, clean context, Agent tool, with this brief verbatim:

<!-- brief:fold -->
> You are folding per-entity interpretations into a system's data layer. Read exactly these and
> nothing else: every file under `docs/02-design/data/interpretations/`, the previous
> `.hitl/data-layer/previous/lineage.yaml` and `.hitl/data-layer/previous/findings.yaml` if present
> (read-only, for continuity of wording), `<TPL>/data-layer.schema.yaml`, and the four templates
> `<TPL>/ontology.yaml`, `<TPL>/mappings.yaml`, `<TPL>/lineage.yaml`, `<TPL>/findings.yaml`. Write
> `docs/02-design/data/ontology.yaml`, `mappings.yaml`, `lineage.yaml` and `findings.yaml`: merge
> entries that describe the same thing under one stable ID; keep every `confidence` as proposed (never
> raise one to `confirmed`); rewrite every evidence citation from a slice to its origin, using the
> `origin: { file, item }` each slice item carries, so the four files cite source evidence only; leave
> edges and findings without an `id`; keep `map:<entity>/<source>.<store>` IDs; put a disagreement
> between two interpretations in `findings.yaml`, never resolve it silently. Reply with the four paths.
<!-- /brief -->

Then number and tie:

```bash
python3 "$DL/assign_ids.py" --data-dir "$DATA" --previous .hitl/data-layer/previous
python3 "$DL/manifest_tie.py" --data-dir "$DATA" --manifest docs/system-manifest.yaml
```

The tie prints each boundary entity it derived and any path no manifest domain owns; show both.
The manifest generator overwrites the file on its own re-run, so after any re-generation run the tie
again. Mark `fold: done`.

## Stage 5 — Validate (DL-5 to DL-9)

```bash
python3 "$CK/check_data_layer.py" --data-dir "$DATA" --manifest docs/system-manifest.yaml --waivers "$CK/data-layer-waivers.yaml"
BASE=""; [[ -f "$DATA/scorecard.yaml" ]] && cp "$DATA/scorecard.yaml" .hitl/data-layer/previous/scorecard.yaml && BASE="--baseline .hitl/data-layer/previous/scorecard.yaml"
python3 "$CK/scorecard.py" --data-dir "$DATA" $BASE
```

A validator `BLOCK` names the file and the rule; send it to Stage 3 (one entity) or Stage 4 and
re-run from there, never patch the four files by hand. `warn` lines are shown and kept.

**Findings as tickets.** List every finding with severity high or medium and `status: open`, one line
each (ID, severity, statement), and take ONE confirmation for the list, following
`shared/issue-hygiene.md` (search first; one rollup when unattended). For each filed one set
`status: ticketed:#N` in `findings.yaml`. A finding nobody confirms stays open in the file.

**Promotion.** Say which entries are `inferred` and how to confirm one: a person adds
`confirmed_by: { who, at, how: human }` and sets `confidence: confirmed`, or a later profiling run
confirms a field. Never set `confirmed` yourself.

Mark `validate: done`. Report, in plain English and nothing else: the scorecard's report as printed,
the validator's one-line summary, the tickets filed, and the stage to run next time (`validate` after
promotions, `interpret ent:<id>` after new evidence, `extract` after a schema change).

## Never

- Never read a live store before the AUTHORIZED reply is in `sources.yaml`; never write to any source.
- Never hand an Interpret sub-agent anything but its own slice, the schema and the template; never
  hand the Fold sub-agent an evidence file.
- Never write `confirmed`, never invent an `id`, never cite evidence that is not in a file.
- Never file a ticket without the person's confirmation of the list; never post to an issue.
- Never edit the four files by hand to make the validator pass; re-run the stage.
