---
description: Start any change. Say your goal, then pick Fast Track (the fewest steps this change needs) or Full Scale, and tick steps back in or out. Also picks the issue and the HITL workflow (development / brownfield / migration / prd), seeds and pushes .hitl/current-change.yaml, and routes into the workflow. The front door for every change; the session-start gate insists on it before any work.
argument-hint: "[change id, e.g. SVC-3, or issue number, or description]"
disable-model-invocation: true
---

**Before doing anything else:** Check whether `.hitl/` exists in the current directory. If it does not, stop immediately and output this — do not proceed with any steps:

```
This project hasn't been set up for HITL.
To get started, run one of these commands in your project directory:

  /hitl:dev-start-from-prd      new project from a PRD
  /hitl:dev-start-brownfield    adopt HITL on an existing codebase
  /hitl:dev-start-migration     migrate a system
```

# Start a Change

**Input:** $ARGUMENTS (optional issue number or short description)

This skill is the **enforced front door**: the hooks block real work until a change is active for
the current branch. This skill selects the issue, picks the workflow, and writes the change file.

## Rules that hold throughout

- A change must trace to a GitHub issue. Never proceed without one; never invent an issue number.
- One active change per branch. Don't clobber an existing active change; switch context instead.
- Never hand-write the `workflow.steps` block; always seed it from the bundled `workflows.yaml`
  catalog (`$CLAUDE_PLUGIN_ROOT/shared/workflows.yaml`) via the Step 6 generator.
- The goal comes first: restate it before anything is read or planned and before the workflow
  question. No tier question at intake; the tier is proposed at Step 4 from what the analysis found.
- The `docs` workflow is only for docs-only changes; docs *and* code is `development`.
- The tier is a human's call. Propose one, say which finding drives it, wait for a person to confirm
  or correct it. A `tier_provisional` left set is a blocking error: nobody confirmed.
- People see **Fast Track** and **Full Scale**, written exactly so, capitalized. First Pass is the
  internal name for the skip record and its validator; never say it to people. It is not opt-in.
  The recommendation is advice; taking Full Scale is not recorded.
- A locked step (`floor`, `no_omit`) is never dropped by a rule or a tick: only by a named person
  accepting the risk, with `ack_by`, a reason and, for a hard-gate step, a linked `waiver_ref`.
  A skip is **not** a waiver.
- Pre-selected is not pre-recorded. Nothing is written until the human confirms; doing nothing runs
  the full plan (`keep` is the default), and the actor on every record is the person who confirmed.
- Run under **brief mode** ([`brief.md`](../../shared/first-pass/brief.md): say less, ask less, never
  re-ask what intake settled), the **reduced-friction permission policy**
  ([`permissions.md`](../../shared/first-pass/permissions.md)) and the neutral language in
  [`language.md`](../../shared/first-pass/language.md), all under `shared/first-pass/`.

> **Resurfacing does not happen here.** `resurface.surface()` matches unresolved skips against the new
> change's domains and `allowed_paths`, and neither is known until the workflow's own impact step fills
> them. Called at change start it always matches nothing. It belongs at the impact step, where scope
> exists. See the worked example at
> [`docs/examples/first-pass/`](https://github.com/Prasad-Apparaju/hitl-dev-platform/tree/main/docs/examples/first-pass).

## Step 1 — Don't clobber an active change

Read `.hitl/current-change.yaml`. If it already describes an **active change for the current
branch** (it has a `workflow` or `current_step` block and `expected_branch` matches the current
`git branch --show-current`, or the branch is `issue/N-*` matching `change_id`), stop and say:

> A change is already active on this branch: **<change_id>** (workflow `<id>`, step `<n>/<total>`).
> Continue it, or run `/hitl:dev-switch-context` to move to a different issue.

## Step 2 — Choose the issue (insist)

If `$ARGUMENTS` names an issue, use it. With a `change_id_prefix` in `.hitl/config.yaml` the form is `<PREFIX>-<n>` (`SVC-3`); a bare number is ambiguous across linked repositories, so refuse it and say which form to use ("Use SVC-3, or DOCS-3 for the docs repository"). An id with another repository's prefix is that repository's issue, not a change to start here: resolve it with the `linked.py resolve` fence in `intake-detail.md` beside this skill, and say so. Without a prefix configured, a bare number is fine as before. Otherwise ask first: **"What's the goal, in one
sentence, and what does done look like?"** Then list open issues and see whether one already covers it:

```bash
gh issue list --state open --limit 30
```

- If the work has **no issue**, shape one from that sentence before any planning: offer
  `/hitl:pm-add-feature` (feature) or `/hitl:pm-report-bug` (bug). Require an explicit choice.

Read the chosen issue in full:

```bash
gh issue view <N> --json number,title,body,labels
```

If the user says "Fast Track" during intake, note it and offer it at Step 4 (details in `intake-detail.md`).

## Step 3 — Restate what you understood, and write the stub

**Before anything is read or planned, and before the workflow question**, write back what you
understood, in a fixed shape:

| | |
|---|---|
| what you want | the ask, corrected |
| in scope | what this change covers |
| out of scope | what it explicitly does not, so it can be pointed at later |
| definition of done | what counts as delivered, in the requester's terms |

Length comes from the change. Wait for a confirmation or a correction: this is the cheapest moment
to catch a misread. **Flag a line you cannot check, do not block it.** "The system should be fast"
cannot be shown to be met: say so, offer a sharper version, and if the vague line stays, record it
as flagged unverifiable and accepted anyway, with a name and a date.

Then write the stub (change id, branch and version; not the workflow):
```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
[[ -n "$PY" ]] || { echo "No usable Python found (need python3, python, or py on PATH)."; exit 1; }
N=<issue-number>; TITLE=<short-kebab-slug>; BRANCH="issue/${N}-${TITLE}"   # the branch Step 5 creates
HITL_VERSION=$(cat "$ROOT/.claude-plugin/plugin.json" 2>/dev/null | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('version','0.0.0'))" 2>/dev/null || echo "0.0.0")
PREFIX=$("$PY" -c "import yaml,os;d=yaml.safe_load(open('.hitl/config.yaml')) if os.path.exists('.hitl/config.yaml') else {};print((d or {}).get('change_id_prefix') or 'GH')" 2>/dev/null || echo GH)
CHANGE_ID="${PREFIX}-${N}"
GEN="ci/first-pass/gen_change.py"; [[ -f "$GEN" ]] || GEN="$ROOT/shared/ci/first-pass/gen_change.py"
"$PY" "$GEN" --stub "$CHANGE_ID" "$BRANCH" "$HITL_VERSION" > .hitl/current-change.yaml
```

Fill in the `requirement` block with the confirmed text, `agreed_by` and `agreed_at`. The stub
carries a **provisional tier of 3** and `status: intake`; it does not satisfy the active-change
gate. It keeps the agreed text if the session dies and names the record. **No tier question here.**

## Step 3b — Determine the workflow (read the issue, then confirm)

Classify the work into exactly one workflow, **state your reasoning**, and confirm with the user
before writing anything:

| Workflow | Choose when | Routes to |
|---|---|---|
| `prd`        | Greenfield project being stood up from a PRD; no `docs/system-manifest.yaml` yet | `/hitl:dev-start-from-prd` |
| `brownfield` | Existing codebase not yet onboarded to HITL (no manifest / registries) | `/hitl:dev-start-brownfield` |
| `migration`  | Porting or consolidating a system from a source codebase into this target | `/hitl:dev-start-migration` |
| `development`| **Most issues** — a feature, bug fix, or refactor in an already-documented component | `/hitl:dev-apply-change` |
| `docs`       | The change touches **nothing but documentation** — no source, tests, or IaC | `/hitl:dev-generate-docs` |
| `release`    | Publishing a version to users — the change *is* shipping, not building | **follow the 12-step release table in `dev-practices/workflow-steps.md`**; `/hitl:dev-verification-review` at step 5 |

Heuristics for the choice are in `intake-detail.md` beside this skill. A `docs` change has two extra duties, in `intake-detail.md` beside this skill.

State: "This looks like a **<workflow>** change because …. Proceed with the <workflow> workflow?" Wait for the answer.

## Step 3c — Run the impact analysis, inside this intake

Follow `dev-apply-change` Steps 2 and 3 from its file (`skills/dev-apply-change/SKILL.md` under the
plugin root). Do not invoke the command: its frontmatter forbids model invocation. Step 3 reads the
stub, asks the one security question, writes `.hitl/impact/<change_id>.yaml` with the acceptance
criteria, and resurfaces overlapping skips. **It is not a step in the plan**; it produces the plan.
Do not continue until the record exists and is non-empty: a missing record is a blocking error.

## Step 4 — Propose the tier, then offer two options

Read `intake-detail.md` beside this skill now.

**The tier, from what the analysis found.** Propose one, citing the finding that drives it, and
**wait for a human to confirm or correct it**. Keep the proposal: `export HITL_TIER_PROPOSED=<n>`
for Step 6, which writes it as `tier_proposed`. Record `tier_set_by` and `tier_reason`, and clear
`tier_provisional`.

**Two options.** Size the plan from the record, passing the confirmed tier (the sizer will not read
one from the record), then append its `outcomes` to `.hitl/impact/<change_id>.yaml` as
`rule_outcomes`, or the retrospective cannot ask whether a rule was right:

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
[[ -n "$PY" ]] || { echo "No usable Python found (need python3, python, or py on PATH)."; exit 1; }
CHANGE_ID=<change-id as formed at Step 3>; TIER=<the confirmed tier>
SZ="ci/first-pass/size_plan.py"; [[ -f "$SZ" ]] || SZ="$ROOT/shared/ci/first-pass/size_plan.py"
"$PY" "$SZ" ".hitl/impact/$CHANGE_ID.yaml" "$TIER" fast
```

Show both, and **list what Fast Track leaves out, one step per line, every time.** Do not wait to
be asked. Heading `Fast Track leaves out (most consequential first):`, one line per step, an "Always
stays" line, then the recommendation; exact shape in the reference file. If the two options come
out the same, say so and do not offer a choice.

**Ask with checkboxes**, with the `AskUserQuestion` tool; never "which do you want?" in prose.
First, the plan: one single-select question, header `Plan`, options `Fast Track (Recommended)`,
`Full Scale`, `Pick steps myself` (recommended first), with a `preview` of each option's step list.

**Then, for Fast Track and for Pick steps myself, the checkboxes.** One `multiSelect` call over every
step Full Scale has and Fast Track does not: header `Add back`, question `Fast Track leaves these
out. Tick any you want to keep.`, one option per step in list order. Four options per question, four
questions per call: sixteen boxes; a question needs at least two options; number the questions when
there is more than one, since the tool rejects question texts that repeat. Nothing ticked is Fast
Track as proposed; a ticked step is kept.

**For Pick steps myself, a second checkbox screen** after the "Add back" one: `Leave out any of
these?` (header `Leave out`), over every step that is not `locked`, not `no_omit` and not `issue`,
lowest `forgo_cost` first. Offer it after Fast Track too when someone wants it lighter still. Full
Scale asks nothing more.

**Steps that always stay are never checkboxes.** List them, and say how to ask for a risk-accepted
skip. Without the `AskUserQuestion` tool, print the same lists numbered and take the numbers typed
back. Print the full ordered plan on request, and always for a workflow of 10 steps or fewer.

## Step 4b — Record the choice

**First Pass is how the choice at Step 4 is recorded.** The pre-selection comes from the rules, not
the tier: steps the rules excluded are pre-selected `not_applicable`, each carrying the finding that
decided it; an active conditional step Fast Track leaves out (`proposed`) is pre-selected `defer`,
never `not_applicable`. When the impact record says `reaches_production: false`, pre-fill `deploy`
and `promote` as `decline`, `ack_by` the confirming person. Let one confirmation record the lot.

**The checkboxes in Step 4 are the menu.** Ask once. A step ticked under "Leave out" becomes its
starter when it has one, otherwise `decline` for a ceremony step and `defer` for a standard one
(table in the reference file); say which in one line per step, and ask only if the person wants a
different one. Then say once: **"N steps left out. No issues opened. One line at the top of #N lists
them; they come back at the next change in this area."** A ticket is filed only when the person
says "file this one" (one, for that step).

**This step elicits choices; it does not write the ledger.** The change file does not exist yet.
Capture the choices and let the Step 6 generator apply them (entry rules in the reference file):

```bash
# Only NON-keep steps go in. An absent step means keep. `actor` is the accountable human, not the agent.
cat > .hitl/first-pass-choices.json <<'JSON'
{
  "actor": "name@team",
  "choices": {
    "roi":   { "disposition": "decline", "reason": "internal tool; ROI self-evident" },
    "figma": { "disposition": "defer",   "reason": "no UI change", "followup_ref": "GH-123" },
    "docs":  { "disposition": "starter", "reason": "thin first pass" }
  }
}
JSON
```

If the validator is missing, say so **before** collecting any choices; the ledger is unenforced without it:

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || echo "⚠ Skip-record validator not found: run /hitl:dev-update to install it. Do NOT record skips until it is present: the ledger is unenforced without it."
```

## Step 5 — Create the branch

```bash
N=<issue-number>
TITLE=$(gh issue view "$N" --json title -q .title \
  | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | cut -c1-50 | sed 's/^-//;s/-$//')
# cut BEFORE sed: truncating after the trim re-introduces the trailing hyphen the trim
# just removed, so every title over 50 chars yields `issue/N-…-` (plugin issue #26).
BRANCH="issue/${N}-${TITLE}"
git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
```

## Step 6 — Seed and write `.hitl/current-change.yaml`

Generate the `workflow` block **from the catalog**; the generator marks the first step `current`, the rest `open`:

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
WF=<development|brownfield|migration|migration_review|prd|release|docs>
CHANGE_ID="${PREFIX}-${N}"   # as formed at Step 3
BRANCH=$(git branch --show-current)
# Resolve a working Python (Windows-safe: python3 is the MS Store stub there). See issue #14.
PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
[[ -n "$PY" ]] || { echo "No usable Python found (need python3, python, or py on PATH)."; exit 1; }
HITL_VERSION=$(cat "$ROOT/.claude-plugin/plugin.json" 2>/dev/null \
  | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('version','0.0.0'))" 2>/dev/null || echo "0.0.0")

TIER=2                       # confirmed at Step 4 — never assume it
TIER_SET_BY=""               # required when TIER <= 1, OR when TIER is above a light proposal (#111)
TIER_REASON=""               # one line on why; HITL_TIER_PROPOSED (Step 4) tells the generator the proposal
CHOICES=".hitl/first-pass-choices.json"   # written by Step 4b; absent ⇒ full plan, no First Pass

# Write via a temp file: a generator that dies partway through `> file` leaves a truncated change
# file behind, and a truncated change file reads as "no active change" to the gate.
# The generator lives at ci/first-pass/gen_change.py — resolved the same way as the validators,
# so it works from source and from the installed plugin.
GEN="ci/first-pass/gen_change.py"; [[ -f "$GEN" ]] || GEN="$ROOT/shared/ci/first-pass/gen_change.py"
"$PY" "$GEN" "$WF" "$CHANGE_ID" "$BRANCH" "$HITL_VERSION" "$TIER" "$CHOICES" \
     "$TIER_SET_BY" "$TIER_REASON" > .hitl/current-change.yaml.tmp
rc=$?

# Replace the live file ONLY on success. The generator refuses on several paths (tier attribution,
# malformed choices, catalog not found), and every refusal writes nothing to stdout — so an
# unconditional mv would drop an EMPTY file over the real change file, which is precisely the
# clobber this temp file exists to prevent. The choices are the user's input; do not delete them
# on a failure they will want to retry.
if [[ $rc -eq 0 && -s .hitl/current-change.yaml.tmp ]]; then
  mv .hitl/current-change.yaml.tmp .hitl/current-change.yaml
  rm -f .hitl/first-pass-choices.json     # consumed; the change file is now the record
else
  rm -f .hitl/current-change.yaml.tmp
  echo "Change file NOT written (generator exit $rc). Existing change file and your step choices are untouched." >&2
  exit 1
fi
```

Show the file to the user, then fill the remaining required fields per
`ai/shared/templates/change-context.schema.yaml`, or note that the workflow's own steps will.

> **The roll-up is written at Step 6b, below**, not here: the change file has to exist first. Entries
> recorded before the workflow declares its area are marked project-wide; the `development` route
> narrows them at its impact step.

## Step 6b — Certify the ledger

Run it **before** the Step 7 commit, **without `--rollup`** (the roll-up is appended after the
check). It must exit 0; exit 2 (a silent skip, an unauthorized floor skip, a TDD omission, a
lightened step with no `first_pass` flag) is non-waivable. Then fold the skips into the durable,
project-wide roll-up; **every workflow does this**:

```bash
# CLAUDE_PLUGIN_ROOT is unset in the Bash tool; a bare "$CLAUDE_PLUGIN_ROOT/..." becomes "/...".
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/first-pass/check_skips.py"; RS="ci/first-pass/resurface.py"
[[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/first-pass/check_skips.py"
[[ -f "$RS" ]] || RS="$ROOT/shared/ci/first-pass/resurface.py"
python3 "$CHK" .hitl/current-change.yaml
python3 "$RS" --change .hitl/current-change.yaml --rollup .hitl/skip-ledger.yaml --append
SL="ci/first-pass/skipped_line.py"
[[ -f "$SL" ]] || SL="$ROOT/shared/ci/first-pass/skipped_line.py"
python3 "$SL" --change .hitl/current-change.yaml --apply
```

The last line writes the Step 4b notice on the issue; nothing else is posted or filed for a skip.
What its exit 2 and exit 3 mean is in the reference file. If `ci/first-pass/` is absent, say so and
tell the user to run `/hitl:dev-update`: the ledger is then uncertified for **every** change.

## Step 6c — Partners in other repositories

Ask once: "Does this change have a partner in another repository: its design approved there, a provider that must ship first, or code that implements this design?" On a yes append `linked_changes: [{ repo: owner/name, change_id: <theirs>, role: docs|provider|consumer|code }]` to the change file, link a slice under its epic with `ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"; LINKED="ci/linked/linked.py"; [[ -f "$LINKED" ]] || LINKED="$ROOT/shared/ci/linked/linked.py"; python3 "$LINKED" link-sub owner/docs#<epic> <this repo>#<N>`, and say which steps now wait on which partner (`shared/linked-changes.md`).

## Step 7 — Commit and push the change file

```bash
git add .hitl/current-change.yaml
git commit -m "chore(hitl): start <change_id> (<workflow>) — seed change context"
git push -u origin "$BRANCH" 2>/dev/null || true   # push if a remote exists
```

## Step 8 — Route into the workflow

- `development` → **`/hitl:dev-apply-change <CHANGE_ID>`** (its Steps 4 to 8; the impact analysis already ran at Step 3c)
- `brownfield`  → **`/hitl:dev-start-brownfield`**
- `migration`   → **`/hitl:dev-start-migration`**
- `prd`         → **`/hitl:dev-start-from-prd`**

As each step completes, set that step's `status` to `done` and the next step's to `current` in
`.hitl/current-change.yaml` (and `current_step` to match) so the breadcrumb advances.
