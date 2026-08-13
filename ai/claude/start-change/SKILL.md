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

Heuristics from the issue: labels (`bug`/`enhancement` → development; `documentation`/`docs` → docs), wording ("migrate",
"port", "consolidate" → migration; "onboard", "adopt HITL", "no docs yet" → brownfield), and
whether `docs/system-manifest.yaml` exists (absent on a real project → prd/brownfield).

**The `docs` workflow is only for changes that touch nothing but docs.** If a change edits docs *and* code, it is a `development` change (the delivery spine already reconciles docs). This keeps the docs workflow from becoming a way to skip the gates on real code. Its own reviewer gate (`doc_review`) is domain-routed: route the review to the role that owns the touched area (Architect for design docs, PM for product docs, Ops for runbooks). At its final `merge` step, set the top-level `status: merged` in `.hitl/current-change.yaml` so the change file does not linger and satisfy the gate for the next change.

State: "This looks like a **<workflow>** change because …. Proceed with the <workflow> workflow?"
Wait for confirmation (or correction) before Step 4.

---

## Step 4 — Show the full step plan

Read the chosen workflow's steps from the bundled workflow catalog — `workflows.yaml`, resolved
as `$CLAUDE_PLUGIN_ROOT/shared/workflows.yaml` in the installed plugin (or `ai/shared/workflows.yaml`
when running from source) — and print the complete ordered plan so the user sees the whole journey
up front, e.g.:

```
development workflow — 31 steps (+ 19a):
  1 Issue · 2 Figma · 3 Impact · 4 ROI · 5 Docs · 6 IaC · 7 Tests · 8 Train · 9 Packet
  10 RED · 11 TstRvw · 12 Dsn+ · 13 VfyRED · 14 GREEN · 15 VfyGRN · 16 Refact · 17 Conv
  18 Rvw1 · 19 Rvw2 · 19a ArchRvw · 20 Rerun · 21 Recncl · 22 QAVfy · 23 ImpBrf
  24 Rollout · 25 VfyPR · 26 IntVfy · 27 Figma2 · 28 Deploy · 29 Promote · 30 30dROI · 31 90dROI
```

---

## Step 4b — Offer First Pass (optional, FR-29)

If the team wants to ship a basic version fast and iterate (PMs especially), offer **First Pass** — a
thin-whole-first, skip-with-record way to run this same plan. It is opt-in; the default is the full plan.

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
CHK="ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || CHK="$CLAUDE_PLUGIN_ROOT/shared/ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || echo "⚠ First Pass validator not found — run /hitl:dev-update to install it. Do NOT record skips until it is present: the ledger is unenforced without it."
```

Certification happens in **Step 6b**, once the change file exists and there is something real to certify.

Run the change under **brief mode** and the **reduced-friction permission policy**
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
WF=<development|brownfield|migration|migration_review|prd>
CHANGE_ID="GH-<N>"
BRANCH=$(git branch --show-current)
# Resolve a working Python (Windows-safe: python3 is the MS Store stub there). See issue #14.
PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
[[ -n "$PY" ]] || { echo "No usable Python found (need python3, python, or py on PATH)."; exit 1; }
HITL_VERSION=$(cat "${CLAUDE_PLUGIN_ROOT:-.}/.claude-plugin/plugin.json" 2>/dev/null \
  | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('version','0.0.0'))" 2>/dev/null || echo "0.0.0")

TIER=2                       # confirm with the user — tier decides which steps may be lightened at all
CHOICES=".hitl/first-pass-choices.json"   # written by Step 4b; absent ⇒ full plan, no First Pass

# Write via a temp file: a generator that dies partway through `> file` leaves a truncated change
# file behind, and a truncated change file reads as "no active change" to the gate.
"$PY" - "$WF" "$CHANGE_ID" "$BRANCH" "$HITL_VERSION" "$TIER" "$CHOICES" << 'PY' > .hitl/current-change.yaml.tmp
import sys, os, json, yaml
from datetime import datetime, timezone
wf_id, change_id, branch, ver, tier_s, choices_path = sys.argv[1:7]
tier = int(tier_s)

# Catalog: prefer the plugin copy, fall back to the source path.
for p in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT",""), "shared/workflows.yaml"),
          "ai/shared/workflows.yaml"):
    if os.path.isfile(p):
        cat = yaml.safe_load(open(p))["workflows"][wf_id]; break
else:
    sys.exit("workflows.yaml not found")

# Criticality must be resolved the SAME way the validator resolves it, so import it rather than
# reimplement it here — two copies of this rule is how a floor step quietly becomes skippable.
resolve_crit = None
for d in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT",""), "shared/ci/first-pass"), "ci/first-pass"):
    if os.path.isfile(os.path.join(d, "check_skips.py")):
        sys.path.insert(0, d)
        try:
            from check_skips import resolve_crit
        except Exception:
            resolve_crit = None
        break
if resolve_crit is None:
    sys.exit("check_skips.py not found — cannot resolve step criticality. Run /hitl:dev-update.")

choices, actor = {}, ""
if os.path.isfile(choices_path):
    doc = json.load(open(choices_path))
    choices = doc.get("choices") or {}
    actor = doc.get("actor") or ""
    unknown = [k for k in choices if k not in {s["key"] for s in cat["steps"]}]
    if unknown:
        sys.exit(f"first-pass choices name steps not in the {wf_id} workflow: {unknown}")
    if choices and not actor:
        sys.exit("first-pass choices need an `actor` — a skip is accountable to a person, not the agent.")

STATUS_FOR = {"defer": "skipped", "decline": "skipped", "starter": "starter"}
ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
q = lambda v: json.dumps("" if v is None else str(v))   # JSON strings are valid YAML double-quoted scalars

steps = cat["steps"]
first = next((s for s in steps if s["key"] not in choices), steps[0])   # never point `current` at a lightened step
lines = [
    'schema_version: "2.0"',
    f'hitl_version: "{ver}"',
    '',
    f'change_id: {change_id}',
    f'tier: {tier}',
    'status: planning',
    f'expected_branch: "{branch}"',
]
if choices:
    lines += ['', 'first_pass: true   # dispositions were chosen at intake; the ledger below is enforced']
lines += [
    '',
    'workflow:',
    f'  id: {cat["id"]}',
    f'  version: "{ver}"',
    f'  total: {cat["total"]}',
    '  steps:',
]
for s in steps:
    ch = choices.get(s["key"])
    st = STATUS_FOR[ch["disposition"]] if ch else ("current" if s is first else "open")
    lines.append(f'    - {{ n: {s["n"]}, key: {s["key"]}, label: "{s["label"]}", phase: "{s["phase"]}", status: {st} }}')

if choices:
    lines += ['', 'skips:']
    by_key = {s["key"]: s for s in steps}
    for key, ch in choices.items():
        crit = resolve_crit(by_key[key], tier)
        entry = (f'  - {{ step: {key}, crit: {crit}, actor: {q(actor)}, reason: {q(ch.get("reason"))}, '
                 f'ts: "{ts}", disposition: {ch["disposition"]}, resolved: false')
        for opt in ("followup_ref", "ack_by", "waiver_ref", "artifact_path"):
            if ch.get(opt):
                entry += f', {opt}: {q(ch[opt])}'
        lines.append(entry + ' }')

lines += [
    '',
    'current_step:',
    f'  number: {first["n"] if str(first["n"]).isdigit() else str(first["n"])[:-1]}',
    f'  name: "{first["label"]}"',
    f'  phase: "{first["phase"]}"',
]
print("\n".join(lines))
PY

mv .hitl/current-change.yaml.tmp .hitl/current-change.yaml
rm -f .hitl/first-pass-choices.json      # consumed; the change file is now the record
```

Show the resulting file to the user. Then complete the remaining required fields for the change
(`source_artifacts.issue`, `manifest.domain`, `allowed_paths`, approvals) per the
`ai/shared/templates/change-context.schema.yaml`, or note they will be filled by the
workflow's own steps.

> **The roll-up is not written here.** `.hitl/skip-ledger.yaml` entries carry the domains and paths a
> skip applies to, and neither is known until the workflow's impact step declares them. Appending now
> would write entries that resurfacing can never match. The impact step appends them, alongside the
> resurfacing read.

---

## Step 6b — Certify the ledger

Only meaningful once the change file exists. Run it **before** the Step 7 commit, so nothing
uncertified is ever pushed:

```bash
CHK="ci/first-pass/check_skips.py"
[[ -f "$CHK" ]] || CHK="$CLAUDE_PLUGIN_ROOT/shared/ci/first-pass/check_skips.py"
python3 "$CHK" .hitl/current-change.yaml --rollup .hitl/skip-ledger.yaml
```

It must exit 0. A silent skip, an unauthorized floor skip, a TDD omission, or a lightened step with no
`first_pass` flag exits 2 and is non-waivable. If `ci/first-pass/` is absent, say so plainly and tell the
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
