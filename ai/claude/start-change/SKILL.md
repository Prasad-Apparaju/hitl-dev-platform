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

## Step 3b — Confirm the tier (a human's call, always)

Propose a tier from the issue and say why, then **wait for a human to confirm or correct it**. Do not
seed a change without one. Tier decides which steps may be lightened at all, and nothing downstream
re-checks the declaration against what the change actually touches.

Where protection actually changes: **3 → 2** takes `impact`, `packet`, `arch_review`, `qa_verify`
and `rollout` off `floor`; **2 → 1** moves only `integration_verify`; `deploy` and `promote` never
demote. **Declaring 2 instead of 3 is the consequential call** — slow down on that one.

Tiers are defined in [`/hitl:dev-practices`](../dev-practices/SKILL.md). Both departures from the
tier you proposed are attributed: the generator refuses a tier 0/1 without `tier_set_by` and
`tier_reason`, and refuses a tier 2+ without them when the shape probe said the change was trivial.
A light path is a human's call; so is overruling a proposal that the change is small.

> Default up. If a change could plausibly be tier 2 or tier 3, it is tier 3. The cost of extra process
> is lower than the cost of an under-reviewed change, and a wrong tier is not caught later.

### Default up, but propose from the shape

"Default up" is right for a change that touches the product; applied to one line in a shell script
it produced a three-and-a-half hour run for adding an environment variable. **Look at what the
change touches before you propose a tier** ([`right-sizing.md`](right-sizing.md)): if the diff is
non-source only and the request is a value rather than behaviour, propose tier 0/1 with the reason
pre-filled and let them correct you. Making someone argue a tier *down* is the friction that pushes
people out of the process entirely.

---

## Step 4 — Show the step plan

Read the chosen workflow's steps from the bundled workflow catalog — `workflows.yaml`, resolved
as `$CLAUDE_PLUGIN_ROOT/shared/workflows.yaml` in the installed plugin (or `ai/shared/workflows.yaml`
when running from source) — and print the whole journey **by phase**, e.g.:

```
development workflow — 31 steps (+19a) across 7 phases:
  Requirements  2   Issue → Figma
  Design        7   Impact → Packet
  Build         8   RED → Conv
  Verify        6   Rvw1 → QAVfy
  Assess        2   ImpBrf → Rollout
  Ship          5   VfyPR → Promote
  Post-Ship     2   30dROI → 90dROI
```

The phase summary is the shape of the work — enough to judge whether the workflow fits.

**Say plainly that this plan is provisional.** Nothing here has read the codebase yet: intake runs
before a line is written, so nothing at this point knows what the change touches. The plan is the
full spine because that is the honest default when the shape is unknown — not because anyone
decided it fits.

> That's the full route — 31 steps. I haven't looked at the code yet, so this is everything rather
> than what you need. Impact analysis is the step that works out what this actually touches, and
> we'll right-size the plan there.

**The sizing happens after impact analysis** (`/hitl:dev-apply-change` step 3), which is the first
moment anything knows the shape of the work. See [`selection.md`](selection.md). Do not try to size
it here: an earlier version probed `git diff` at intake and always got an empty answer, because at
intake there is nothing to diff.

**Print the full ordered list on request** ("show me every step"), and always print it in full for a
workflow of 10 steps or fewer, where the phase summary would be longer than the list it replaces.

---

## Step 4b — Offer First Pass (FR-29)

**First Pass** lightens what does not apply, on the record, and keeps going — for a developer on a
one-line regression as much as a PM shipping a thin first version. Above tier 1 it is opt-in and the
full plan is the default. **At tier 0 or 1, offer it without being asked**: ceremony steps
pre-selected as declined, reason filled in, one confirmation for the lot
([`right-sizing.md`](right-sizing.md)).

Pre-selected is not pre-recorded. **Nothing is written until the human confirms**, and doing nothing
still runs the full plan — `keep` remains the default disposition (CR-1). The actor on every resulting
record is the person who confirmed, never the agent.

**Present the disposition menu ONCE** (brief mode — not a step-by-step interview). Each step's `crit`
(from the catalog, resolved against this change's `tier`) constrains its options:

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

See [`first-pass-choices.md`](first-pass-choices.md) for the choices file, the floor/starter/defer
rules, and what to do when the validator is missing.

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
"$PY" - "$WF" "$CHANGE_ID" "$BRANCH" "$HITL_VERSION" "$TIER" "$CHOICES" "$TIER_SET_BY" "$TIER_REASON" << 'PY' > .hitl/current-change.yaml.tmp
import sys, os, json, yaml
from datetime import datetime, timezone
wf_id, change_id, branch, ver, tier_s, choices_path = sys.argv[1:7]
tier_set_by, tier_reason = (sys.argv[7:9] + ["", ""])[:2]
try:
    tier = int(tier_s)
except ValueError:
    sys.exit(f"tier must be an integer 0-4, got {tier_s!r}")
if not 0 <= tier <= 4:
    sys.exit(f"tier must be 0-4, got {tier}")
if tier <= 1 and not (tier_set_by.strip() and tier_reason.strip()):
    sys.exit("tier <= 1 needs TIER_SET_BY and TIER_REASON — a light path is a human's call, "
             "and it unlocks the batch-decline path at intake.")

# Catalog: prefer the plugin copy, fall back to the source path.
for p in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT",""), "shared/workflows.yaml"),
          "ai/shared/workflows.yaml"):
    if os.path.isfile(p):
        _all = yaml.safe_load(open(p))["workflows"]
        if wf_id not in _all:
            sys.exit(f"unknown workflow {wf_id!r}; the catalog defines: {sorted(_all)}")
        cat = _all[wf_id]
        break
else:
    sys.exit("workflows.yaml not found")

# Criticality must be resolved the SAME way the validator resolves it, so import it rather than
# reimplement it here — two copies of this rule is how a floor step quietly becomes skippable.
resolve_crit = has_starter = is_allowed = None
for d in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT",""), "shared/ci/first-pass"), "ci/first-pass"):
    if os.path.isfile(os.path.join(d, "check_skips.py")):
        sys.path.insert(0, d)
        try:
            from check_skips import resolve_crit; from starters import has_starter
            from dispositions import is_allowed
        except Exception:
            resolve_crit = has_starter = is_allowed = None
        break
if resolve_crit is None or has_starter is None or is_allowed is None:
    sys.exit("ci/first-pass not found — cannot resolve criticality or the starter registry. "
             "Run /hitl:dev-update.")

STATUS_FOR = {"defer": "skipped", "decline": "skipped", "starter": "starter"}

# Validate the whole choices document before touching anything. A malformed file must produce a
# clear refusal, not a traceback: the caller replaces the live change file with our stdout, so an
# ambiguous failure is worse here than anywhere else in the pipeline.
choices, actor = {}, ""
if os.path.isfile(choices_path):
    try:
        doc = json.load(open(choices_path))
    except ValueError as e:
        sys.exit(f"{choices_path} is not valid JSON: {e}")
    if not isinstance(doc, dict):
        sys.exit(f"{choices_path} must be a JSON object with `actor` and `choices`.")
    raw = doc.get("choices") or {}
    if not isinstance(raw, dict):
        sys.exit("`choices` must be an object keyed by step, e.g. {\"roi\": {\"disposition\": \"decline\", ...}}")
    actor = doc.get("actor") or ""
    if not isinstance(actor, str):
        sys.exit("`actor` must be a string.")
    known = {s["key"] for s in cat["steps"]}
    for key, ch in raw.items():
        if not isinstance(ch, dict):
            sys.exit(f"choice for '{key}' must be an object, got {type(ch).__name__}.")
        disp = ch.get("disposition")
        if disp == "keep":
            continue          # `keep` is the default and the menu offers it; it is simply not a record
        if disp not in STATUS_FOR:
            sys.exit(f"choice for '{key}' has disposition {disp!r}; expected one of "
                     f"{sorted(STATUS_FOR)} (or 'keep' to leave the step alone).")
        if not str(ch.get("reason") or "").strip():
            sys.exit(f"choice for '{key}' needs a `reason` — a skip without one is a silent skip.")
        if key not in known:
            sys.exit(f"first-pass choices name steps not in the {wf_id} workflow: {key}")
        # `starter` is only offered for steps with a registered honest-minimal artifact. The menu says
        # so, but a menu is not an enforcement boundary — a hand-written choices file could otherwise
        # invent a starter for any step and certify clean.
        # Registry check first — `is_allowed` subsumes it but cannot say what to do instead.
        if ch["disposition"] == "starter" and not has_starter(key):
            sys.exit(f"'{key}' has no registered starter (ci/first-pass/starters.py); use defer or decline.")
        if not is_allowed({s["key"]: s for s in cat["steps"]}[key], tier, ch["disposition"]):
            sys.exit(f"'{ch['disposition']}' is not allowed for '{key}' at tier {tier} (see the Step 4b "
                     f"menu; a no_omit step may only be thinned to a starter).")
        choices[key] = ch
    if choices and not actor.strip():
        sys.exit("first-pass choices need an `actor` — a skip is accountable to a person, not the agent.")
ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
q = lambda v: json.dumps("" if v is None else str(v))   # JSON strings are valid YAML double-quoted scalars

steps = cat["steps"]
# `current` must never land on a lightened step (schema: the pointer never points at skipped/starter).
# If every step was lightened there is no honest pointer and no change left to run, so refuse rather
# than emit a file that contradicts its own schema.
first = next((s for s in steps if s["key"] not in choices), None)
if first is None:
    sys.exit("every step in the plan was lightened — there is no change left to run. Keep at least one.")
# Every interpolated scalar goes through q(). A branch name or change id containing a quote used to
# produce a file that was non-empty and exited 0 but did not parse — and the shell guard checks status
# and emptiness, not validity, so it installed the broken file over the live one.
lines = [
    'schema_version: "2.0"',
    f'hitl_version: {q(ver)}',
    '',
    f'change_id: {q(change_id)}',
    f'tier: {tier}',
]
if tier <= 1:
    lines += [f'tier_set_by: {q(tier_set_by)}', f'tier_reason: {q(tier_reason)}']
lines += [
    'status: planning',
    f'expected_branch: {q(branch)}',
]
if choices:
    lines += ['', 'first_pass: true   # dispositions were chosen at intake; the ledger below is enforced']
lines += [
    '',
    'workflow:',
    f'  id: {q(cat["id"])}',
    f'  version: {q(ver)}',
    f'  total: {cat["total"]}',
    '  steps:',
]
for s in steps:
    ch = choices.get(s["key"])
    st = STATUS_FOR[ch["disposition"]] if ch else ("current" if s is first else "open")
    lines.append(f'    - {{ n: {q(s["n"])}, key: {q(s["key"])}, label: {q(s["label"])}, '
                 f'phase: {q(s["phase"])}, status: {st} }}')

if choices:
    lines += ['', 'skips:']
    by_key = {s["key"]: s for s in steps}
    for key, ch in choices.items():
        crit = resolve_crit(by_key[key], tier)
        entry = (f'  - {{ step: {key}, crit: {crit}, actor: {q(actor)}, reason: {q(ch.get("reason"))}, '
                 f'ts: "{ts}", disposition: {ch["disposition"]}, resolved: false')
        for opt in ("followup_ref", "ack_by", "waiver_ref", "starter_artifact"):
            if ch.get(opt):
                entry += f', {opt}: {q(ch[opt])}'
        lines.append(entry + ' }')

lines += [
    '',
    'current_step:',
    f'  number: {first["n"] if str(first["n"]).isdigit() else str(first["n"])[:-1]}',
    f'  name: {q(first["label"])}',
    f'  phase: {q(first["phase"])}',
]
out = "\n".join(lines)
# Refuse to hand the wrapper something it cannot parse. The guard downstream checks exit status and
# non-emptiness; only this check can catch a file that is both and still invalid.
try:
    yaml.safe_load(out)
except yaml.YAMLError as e:
    sys.exit(f"generated change file is not valid YAML ({e.__class__.__name__}) — refusing to emit it.")
print(out)
PY
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
