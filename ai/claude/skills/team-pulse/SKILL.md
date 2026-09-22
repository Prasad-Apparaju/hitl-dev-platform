---
name: team-pulse
description: >
  One page, generated from GitHub, that shows who is on what, what is waiting on someone else,
  and who can unblock it: per person and per epic, last two weeks, every number linked to its
  source. For everyone on the team, not one role's report on the rest. Use when someone asks
  where things stand, who is blocked, whether a PR has a reviewer, or where to spend the
  afternoon.
argument-hint: "[team | leads]"
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

# Team Pulse

Who is on what, what is waiting on someone else, and who can unblock it. Read from GitHub with
`gh` only; rendered as one self-contained page; every number and event links to where it came
from. The conventions it relies on are in `shared/team-pulse.md`.

**Input:** $ARGUMENTS (optional: `team` or `leads`; empty uses the stored audience)

This is not a change step. It writes nothing to the change file and posts nothing to any issue.

## Step 1 — Resolve the generator and the audience

```bash
# CLAUDE_PLUGIN_ROOT is unset in the Bash tool; a bare "$CLAUDE_PLUGIN_ROOT/..." becomes "/...".
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
PULSE="tools/team-pulse/pulse.py"
[[ -f "$PULSE" ]] || PULSE="$ROOT/shared/tools/team-pulse/pulse.py"
[[ -f "$PULSE" ]] || echo "team-pulse: generator not found; run /hitl:dev-update"
gh auth status >/dev/null 2>&1 || echo "team-pulse: gh is not signed in; run gh auth login"
```

If the generator or `gh` is missing, stop and say so in one line.

**First run only.** If `.hitl/config.yaml` has no `team_pulse:` block, ask one question with
two options and store the answer:

> Who gets this page? **team** (every contributor sees the same page; the default) or **leads**
> (adds a planning section with hours and review load that only named leads should see; the team
> page is still produced).

Write the answer as `team_pulse:\n  audience: <answer>` into `.hitl/config.yaml` (append; keep
other blocks). Never ask again. `$ARGUMENTS` overrides the stored audience for this run only.

## Step 2 — Collect

```bash
python3 "$PULSE" collect --out .hitl/pulse/data.json
```

It prints the counts. If it exits 3, `gh` could not read the repository: show its message and
stop. Facts only leave this step; nothing here is written by a model.

## Step 3 — Write the notes, from the data only

```bash
python3 "$PULSE" notes --data .hitl/pulse/data.json > .hitl/pulse/notes.json
```

Read `.hitl/pulse/data.json` and fill every empty string in `.hitl/pulse/notes.json`:

- **Per person, one sentence** saying what they are on, from their events and open PRs. Example:
  "On the API slice; PR #20 has waited four days for bob's review."
- **Per epic, one summary sentence** (slices done, what is moving) **and one nudge** that names
  the thing that is waiting and who can supply it. Example: "PR #20 needs a reviewer; bob was
  asked." An epic with nothing waiting gets a nudge of "Nothing waiting."

Rules. Facts from the JSON only. No praise, no blame, no hedging, no verdict on a person. Nothing
that is not in the data. If the data is thin, the sentence is short.

## Step 4 — Render

```bash
python3 "$PULSE" render --data .hitl/pulse/data.json --notes .hitl/pulse/notes.json --audience <audience>
```

With `leads`, run it a second time with `--audience team` so contributors keep their page. The
files land under `docs/04-operations/` (`team-pulse.html`, and `team-pulse-leads.html` for
leads). Do not commit them unless the person asks; they are generated.

**Publishing.** If `publish: artifact` is set, or the person asks for a link, and the Artifact
tool is available in this session: publish `docs/04-operations/team-pulse.html` as a private
artifact (favicon 📡, a stable title such as "Team Pulse"), and the leads page as a second,
separate artifact that is never shared with the team link. Republish the same file path on later
runs so the URL stays the same. Without the Artifact tool, the file is the page; say where it is.

## Step 5 — Report

End with: the file path or URL, the counts the generator printed, and the three most important
items from the attention strip, one line each, in the generator's words. Nothing else.

## Never

- Never post the page, a summary or a nudge to an issue or a PR.
- Never write a note that is not backed by the collected data.
- Never share the leads page with the team link, or the team link's page with the planning section.
- Never count a hook or gate comment as a person's activity.
