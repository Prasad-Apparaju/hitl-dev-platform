---
description: Start work on a change the right way — pick a GitHub issue, determine the correct HITL workflow (development / brownfield / migration / prd), show its full step plan, seed and push the self-describing .hitl/current-change.yaml, then route into the workflow. This is the front door for every change; the session-start gate insists on it before any work.
argument-hint: "[issue number or description]"
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

---

# Start a Change

**Input:** $ARGUMENTS (optional issue number or short description)

This skill is the **enforced front door**. The HITL hooks (`hitl-gate.sh` on session start,
`welcome.sh` on every prompt) inject a directive that no real work may happen until a change is
active for the current branch, and `check-hitl-context.sh` hard-blocks edits until then. This
skill is how that gate is satisfied: it selects the issue, picks the workflow, and writes the
change file.

---

## Step 1 — Don't clobber an active change

Read `.hitl/current-change.yaml`. If it already describes an **active change for the current
branch** (it has a `workflow` or `current_step` block and `expected_branch` matches the current
`git branch --show-current`, or the branch is `issue/N-*` matching `change_id`), stop and say:

> A change is already active on this branch: **<change_id>** (workflow `<id>`, step `<n>/<total>`).
> Continue it, or run `/hitl:dev-switch-context` to move to a different issue.

Only proceed when there is **no** active, branch-matched change.

---

## Step 2 — Choose the issue (insist)

If `$ARGUMENTS` names an issue number, use it. Otherwise list open issues and ask the user to pick one:

```bash
gh issue list --state open --limit 30
```

- If the user describes work that has **no issue**, do not proceed to planning. Offer to create one:
  `/hitl:pm-add-feature` (feature) or `/hitl:pm-report-bug` (bug). A change must trace to an issue.
- Do not invent an issue number. Require an explicit choice.

Read the chosen issue in full:

```bash
gh issue view <N> --json number,title,body,labels
```

---

## Step 3 — Determine the workflow (read the issue, then confirm)

Classify the work into exactly one workflow, **state your reasoning**, and confirm with the user
before writing anything:

| Workflow | Choose when | Routes to |
|---|---|---|
| `prd`        | Greenfield project being stood up from a PRD; no `docs/system-manifest.yaml` yet | `/hitl:dev-start-from-prd` |
| `brownfield` | Existing codebase not yet onboarded to HITL (no manifest / registries) | `/hitl:dev-start-brownfield` |
| `migration`  | Porting or consolidating a system from a source codebase into this target | `/hitl:dev-start-migration` |
| `development`| **Most issues** — a feature, bug fix, or refactor in an already-documented component | `/hitl:dev-apply-change` |
| `docs`       | The change touches **nothing but documentation** — no source, tests, or IaC | `/hitl:dev-generate-docs` |
| `release`    | Publishing a version to users — the change *is* shipping, not building | **follow the 12-step release table in `dev-practices/workflow-steps.md`**; `/hitl:dev-adversarial-review` at step 5 |

Heuristics from the issue: labels (`bug`/`enhancement` → development; `documentation`/`docs` → docs), wording ("migrate",
"port", "consolidate" → migration; "onboard", "adopt HITL", "no docs yet" → brownfield), and
whether `docs/system-manifest.yaml` exists (absent on a real project → prd/brownfield).

**The `docs` workflow is only for changes that touch nothing but docs.** Docs *and* code is a `development` change (the spine already reconciles docs), which stops `docs` becoming a way to skip the gates on real code. Its `doc_review` gate is domain-routed: Architect for design docs, PM for product, Ops for runbooks. At its final `merge` step set top-level `status: merged` in `.hitl/current-change.yaml`, so the file does not linger and satisfy the gate for the next change.

State: "This looks like a **<workflow>** change because …. Proceed with the <workflow> workflow?"
Wait for confirmation (or correction) before Step 4.

---

## Step 3b — Restate what you understood, and write the stub

**Before anything is read or planned.** Write back what you understood, in a fixed shape:

| | |
|---|---|
| what you want | the ask, corrected |
| in scope | what this change covers |
| out of scope | what it explicitly does not, so it can be pointed at later |
| definition of done | what counts as delivered, in the requester's terms |

Length comes from the change. A one-line fix has a one-line definition of done. Wait for a
confirmation or a correction; this is the cheapest moment to catch a misread, because everything
downstream derives from this text and a wrong plan is harder to argue with than a wrong sentence.

**The definition of done is not the plan restated.** The plan is how the work gets done; this is
what counts as delivered, in the requester's own words. A completed plan does not prove the thing
does what was asked.

**Flag a line you cannot check, do not block it.** "The system should be fast" cannot be shown to be
met. Say so, offer a sharper version, take whatever answer comes back, and if the vague line stays,
record that it was flagged as unverifiable and accepted anyway, with a name and a date. That record
does not require you to have been right about the wording, only to have asked.

Then write the stub:

```bash
GEN="ci/first-pass/gen_change.py"; [[ -f "$GEN" ]] || GEN="$ROOT/shared/ci/first-pass/gen_change.py"
"$PY" "$GEN" --stub "$CHANGE_ID" "$BRANCH" "$HITL_VERSION" > .hitl/current-change.yaml
```

Fill in the `requirement` block with the confirmed text, `agreed_by` and `agreed_at`.

The stub carries a **provisional tier of 3** and `status: intake`. It does not satisfy the
active-change gate, so source edits stay blocked — correct, since no plan has authorised one yet.
What it does is keep the agreed text if the session dies, feed the analysis, and name the record.

**No tier question here.** The tier is proposed at Step 4 from what the analysis found. Asking now
means asking before the evidence exists, which is what tiered a one-line shell script change up to a
three and a half hour path (#97).

---

## Step 3c — Run the impact analysis

Call `/hitl:dev-apply-change`. It reads the stub, works out what this change reaches, writes
`.hitl/impact/<change_id>.yaml`, translates the definition of done into acceptance criteria, and
returns. **It is not a step in the plan** — it is what produces the plan.

Do not continue until the record exists and is non-empty. A change file naming a record that is not
there is a blocking error, because a second artifact is only safe when something notices its absence.

---

## Step 4 — Propose the tier, then offer two options

### The tier, from what the analysis found

Propose one, say which finding drives it, and **wait for a human to confirm or correct it**. Record
`tier_set_by` and `tier_reason`, and clear `tier_provisional`. Leaving it set is a blocking error:
it means nobody confirmed.

The evidence is in the record now, so the proposal cites it rather than the issue's wording. Three
dependent areas and a data migration is a different change from one flagged file with no callers,
and the words in the title do not distinguish them.

Where protection actually changes, from the catalog: **3 → 2** takes `packet`, `arch_review`,
`qa_verify` and `rollout` off `floor`; **2 → 1** moves only `integration_verify`. `deploy`,
`promote`, the test-first cycle and the retrospective never demote. So **declaring 2 instead of 3 is
the consequential call.**

### Two options

Size the plan from the record:

```bash
SZ="ci/first-pass/size_plan.py"; [[ -f "$SZ" ]] || SZ="$ROOT/shared/ci/first-pass/size_plan.py"
"$PY" "$SZ" ".hitl/impact/$CHANGE_ID.yaml" "$WFYAML" fast
```

Show both, and the difference:

```
This change reaches: 3 areas, 1 published interface, a data migration.

  Fast track   21 steps — what this change's own facts call for
  Full scale   31 steps — everything that applies to a change of this shape

  The 10 extra: Figma, ROI, training, design review, code review, refactor,
  conventions, test review, and both ROI checkpoints.

Recommended: fast track. Nothing it drops is protecting something this change touches.
```

One line on which is recommended and why. **The recommendation is advice** — taking full scale
instead is not recorded.

Say what each step protects when asked, from `protects` in the catalog. Order anything outside the
fast track by `forgo_cost`, so the most consequential omission is the first one a person sees.

**Print the full ordered list on request** ("show me every step"), and always in full for a workflow
of 10 steps or fewer, where a phase summary would be longer than the list it replaces.

---

## Step 4b — Record the choice (First Pass, FR-29)

**First Pass is how the choice at Step 4 is recorded.** It is not a separate offer and no longer
opt-in: every change is shown a proposal and confirms or adjusts it. Full scale is simply the answer
set where nothing is dropped. This is the third root cause in #97 — the one feature built for this
problem had to be asked for by someone who already knew it existed.

**The pre-selection comes from the rules, not from the tier.** `size_plan.py` has already decided
what applies and what is needed now, from what this change reaches. Present the steps outside the
chosen option pre-selected, each carrying the finding that decided it as its reason: "no interface
files in this change", "3 dependents". Let **one confirmation record the lot.**

Those entries take the `not_applicable` disposition — the rules determined the step does not apply,
which is a different fact from a person choosing to skip it. Without that distinction a fast track
records a named human declining twenty-odd steps they never looked at, and the retrospective reads
that back as what was left out and why.

A rule may never retire a load-bearing step. `not_applicable` on a `floor` or `no_omit` step is a
non-waivable block (`RULE_OVER_FLOOR`); those are dropped by a named person accepting the risk, or
not at all. `size_plan.py` never offers them, so a plan built from it cannot produce that record.

Pre-selected is not pre-recorded. **Nothing is written until the human confirms**, and doing nothing
still runs the full plan — `keep` remains the default disposition (CR-1). The actor on every resulting
record is the person who confirmed, never the agent.

**Present the disposition menu ONCE** (brief mode — not a step-by-step interview). Each step's `crit`
(from the catalog, resolved against this change's `tier`) constrains its options:

Steps the RULES excluded are pre-selected as `not_applicable` and are not part of this menu; the
menu is for what a person is choosing to lighten beyond that.

| step type | options offered |
|---|---|
| `ceremony` | keep · starter\* · skip (defer / decline) |
| `standard` | keep · starter\* · defer · decline |
| `standard` + `no_omit` (TDD RED/GREEN) | keep · starter — *never defer/decline* |
| `floor` | keep · *request risk-accepted skip* |

\*starter offered only for steps in the registry (`ci/first-pass/starters.py`); `keep` is the default.

**This step elicits choices; it does not write the ledger.** The change file does not exist yet — Step 6
creates it — so recording here would write to a stale or absent file that Step 6 then overwrites. Capture
the choices and let the generator apply them:

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

Rules that still apply when collecting the choices:
1. **Floor** — a `floor` skip requires the accountable role's risk-accepted `ack_by` + reason, and (for a
   step mapping to a hard gate) a linked `waiver_ref`. A skip is **not** a waiver. Put both in the entry.
2. **Starter** — write the honest-minimal artifact from `starters.py` (e.g. acceptance criteria = "a working
   version of the system"), mark it `needs-enhancement`, record its path; seed a fast-follow to *enhance* it.
3. **Defer** — seed a linked fast-follow ticket and put its ref in `followup_ref`.

If the validator is missing, say so **before** collecting any choices — the ledger is unenforced without it:

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || echo "⚠ First Pass validator not found — run /hitl:dev-update to install it. Do NOT record skips until it is present: the ledger is unenforced without it."
```

Certification happens in **Step 6b**, once the change file exists and there is something real to certify.

Run the change under **brief mode** ([`shared/first-pass/brief.md`](../../shared/first-pass/brief.md) —
say less, ask less, never re-ask what intake already settled) and the **reduced-friction permission policy**
([`shared/first-pass/permissions.md`](../../shared/first-pass/permissions.md)); use the neutral /
respectful language in [`shared/first-pass/language.md`](../../shared/first-pass/language.md).

> **Resurfacing does not happen here.** `resurface.surface()` matches unresolved skips against the new
> change's domains and `allowed_paths`, and neither is known until the workflow's own impact step fills
> them. Called at change start it always matches nothing. It belongs at the impact step, where scope
> exists. See the worked example at
> [`docs/examples/first-pass/`](https://github.com/Prasad-Apparaju/hitl-dev-platform/tree/main/docs/examples/first-pass).

---

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

---

## Step 6 — Seed and write `.hitl/current-change.yaml`

Generate the embedded `workflow` block **from the catalog** (do not hand-write the steps — that
is how drift starts). Run this generator, which copies the chosen workflow's steps, marks the
first step `current` and the rest `open`, and stamps the versions:

```bash
WF=<development|brownfield|migration|migration_review|prd|release|docs>
CHANGE_ID="GH-<N>"
BRANCH=$(git branch --show-current)
# Resolve a working Python (Windows-safe: python3 is the MS Store stub there). See issue #14.
PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
[[ -n "$PY" ]] || { echo "No usable Python found (need python3, python, or py on PATH)."; exit 1; }
HITL_VERSION=$(cat "$ROOT/.claude-plugin/plugin.json" 2>/dev/null \
  | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('version','0.0.0'))" 2>/dev/null || echo "0.0.0")

TIER=2                       # from Step 3b — never assume it
TIER_SET_BY=""               # required when TIER <= 1: the human who made the call
TIER_REASON=""               # required when TIER <= 1: one line on why it qualifies
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
  echo "Change file NOT written (generator exit $rc). Existing change file and your First Pass choices are untouched." >&2
  exit 1
fi
```

Show the resulting file to the user. Then complete the remaining required fields for the change
(`source_artifacts.issue`, `manifest.domain`, `allowed_paths`, approvals) per the
`ai/shared/templates/change-context.schema.yaml`, or note they will be filled by the
workflow's own steps.

> **The roll-up is written at Step 6b, below**, not here — the change file has to exist first. Entries
> recorded before the workflow declares its area are marked project-wide; the `development` route
> narrows them at its impact step.

---

## Step 6b — Certify the ledger

Only meaningful once the change file exists. Run it **before** the Step 7 commit, so nothing
uncertified is ever pushed:


**No `--rollup` here, deliberately.** The roll-up is written at the impact step, once the change knows
its own area — so at intake every skip would warn as missing from a ledger it cannot be in yet. A
check that always warns teaches people to ignore it, and this is the check that would otherwise catch
a genuinely missing ledger entry later.

It must exit 0. A silent skip, an unauthorized floor skip, a TDD omission, or a lightened step with no
`first_pass` flag exits 2 and is non-waivable.

Then fold the skips into the durable roll-up so they survive the next intake replacing this file.
**Every workflow does this** (CR-10 is project-wide, and the onboarding and docs routes never declare
a manifest domain at all):

```bash
# CLAUDE_PLUGIN_ROOT is unset in the Bash tool; a bare "$CLAUDE_PLUGIN_ROOT/..." becomes "/...".
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
CHK="ci/first-pass/check_skips.py"; RS="ci/first-pass/resurface.py"
[[ -f "$CHK" ]] || CHK="$ROOT/shared/ci/first-pass/check_skips.py"
[[ -f "$RS" ]] || RS="$ROOT/shared/ci/first-pass/resurface.py"
python3 "$CHK" .hitl/current-change.yaml
python3 "$RS" --change .hitl/current-change.yaml --rollup .hitl/skip-ledger.yaml --append
```

With no area declared yet, entries record as **project-wide** and resurface at any later change until
resolved. The `development` route re-runs this at its impact step, narrowing them to the real scope.
Both runs are idempotent on `(change_id, step)`. If `ci/first-pass/` is absent, say so plainly and tell the
user to run `/hitl:dev-update` — that state means the skip ledger is uncertified for **every** change on
the project, not just this one.

---

## Step 7 — Commit and push the change file

Anchor the change to this branch so anyone who picks it up resumes from the right context:

```bash
git add .hitl/current-change.yaml
git commit -m "chore(hitl): start <change_id> (<workflow>) — seed change context"
git push -u origin "$BRANCH" 2>/dev/null || true   # push if a remote exists
```

---

## Step 8 — Route into the workflow

Hand off to the workflow's own skill and follow the breadcrumb from there:

- `development` → **`/hitl:dev-apply-change <N>`** (impact analysis → plan; steps 1–9)
- `brownfield`  → **`/hitl:dev-start-brownfield`**
- `migration`   → **`/hitl:dev-start-migration`**
- `prd`         → **`/hitl:dev-start-from-prd`**

As each step completes, update the matching step's `status` to `done` and the next step's to
`current` in `.hitl/current-change.yaml` (set `current_step` to match) so the breadcrumb advances.

## Important Rules

- A change must trace to a GitHub issue — never proceed without one.
- Never hand-write the `workflow.steps` block; always seed it from the bundled `workflows.yaml`
  catalog (`$CLAUDE_PLUGIN_ROOT/shared/workflows.yaml`) via the Step 6 generator.
- One active change per branch. Don't clobber an existing active change — switch context instead.
