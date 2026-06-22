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

Heuristics from the issue: labels (`bug`/`enhancement` → development), wording ("migrate",
"port", "consolidate" → migration; "onboard", "adopt HITL", "no docs yet" → brownfield), and
whether `docs/system-manifest.yaml` exists (absent on a real project → prd/brownfield).

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

## Step 5 — Create the branch

```bash
N=<issue-number>
TITLE=$(gh issue view "$N" --json title -q .title \
  | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//' | cut -c1-50)
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

"$PY" - "$WF" "$CHANGE_ID" "$BRANCH" "$HITL_VERSION" << 'PY' > .hitl/current-change.yaml
import sys, yaml
wf_id, change_id, branch, ver = sys.argv[1:5]
# Catalog: prefer the plugin copy, fall back to the source path.
import os
for p in (os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT",""), "shared/workflows.yaml"),
          "ai/shared/workflows.yaml"):
    if os.path.isfile(p):
        cat = yaml.safe_load(open(p))["workflows"][wf_id]; break
else:
    sys.exit("workflows.yaml not found")
steps = cat["steps"]
first = steps[0]
lines = [
    'schema_version: "2.0"',
    f'hitl_version: "{ver}"',
    '',
    f'change_id: {change_id}',
    'tier: 2            # confirm/adjust during the workflow',
    'status: planning',
    f'expected_branch: "{branch}"',
    '',
    'workflow:',
    f'  id: {cat["id"]}',
    f'  version: "{ver}"',
    f'  total: {cat["total"]}',
    '  steps:',
]
for s in steps:
    st = "current" if s is first else "open"
    lines.append(f'    - {{ n: {s["n"]}, key: {s["key"]}, label: "{s["label"]}", status: {st} }}')
lines += [
    'current_step:',
    f'  number: {first["n"] if str(first["n"]).isdigit() else str(first["n"])[:-1]}',
    f'  name: "{first["label"]}"',
    f'  phase: "{first["phase"]}"',
]
print("\n".join(lines))
PY
```

Show the resulting file to the user. Then complete the remaining required fields for the change
(`source_artifacts.issue`, `manifest.domain`, `allowed_paths`, approvals) per the
`change-context.schema.yaml`, or note they will be filled by the workflow's own steps.

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
