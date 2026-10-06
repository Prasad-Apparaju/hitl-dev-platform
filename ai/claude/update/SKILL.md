---
description: Update the HITL plugin to the latest version. Re-runs the plugin install command to pull the latest release, shows what changed, and re-wires hooks if needed.
argument-hint: ""
disable-model-invocation: true
---

# Update HITL Plugin

Steps 1 to 3 update the installed plugin. Steps 3b to 4.10 reconcile this repo with it; every one is idempotent and runs whether or not the version changed.

## Rules that hold throughout

- **The installed skill wins.** After Step 2 the newly installed `SKILL.md` replaces the copy in your context (Step 2.5); where they differ, the file wins.
- **Shell state does not persist between tool calls.** Every fence resolves `ROOT` itself; a step never inherits `$ROOT` from an earlier one. Fences probe `python3`, `python` and `py`, because a bare `python3` may be the Microsoft Store stub on Windows.
- **Never stop at "already on the latest version".** The reconcile steps repair this repo, not the plugin.
- **Co-owned files** (validators under `ci/` and `tools/`, `.semgrep/`, `.claude/settings.json`, `CLAUDE.md`) are never blind-copied or deleted: install what is absent, show a diff for anything modified and ask per file; only an explicit yes overwrites. A file is removed only when tracked here and hashing to a version HITL shipped.
- **Reference files** beside this skill are read in full when a step names one; each step links its own.

## Step 1 — Read the current version

```bash
python3 -c "
import json, os, sys
# Try installed_plugins.json first (current Claude Code)
try:
    p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
    data = json.load(open(p))
    entry = data['plugins']['hitl@hitl'][0]
    print(entry['version']); sys.exit(0)
except Exception: pass
# Fallback: scan settings.json for plugin path, then read plugin.json
try:
    cfg = os.path.expanduser('~/.claude/settings.json')
    data = json.load(open(cfg))
    for p in data.get('plugins', []):
        path = p if isinstance(p, str) else p.get('path', '')
        pj = os.path.join(path, '.claude-plugin/plugin.json')
        if os.path.isfile(pj):
            print(json.load(open(pj))['version']); sys.exit(0)
except Exception: pass
print('NOT_FOUND')
"
```

If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found. Confirm it was installed with `claude plugin install hitl@hitl`." Record the version shown as the **old version**.

## Step 2 — Update the plugin

```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```
`marketplace update` refreshes the cached manifest so the latest release is visible. `plugin update` installs it.

## Step 2.5 — Re-read this skill from the version you just installed

**Do this before anything else, unconditionally.** You are executing the `SKILL.md` you are updating *from*; a fix that ships inside `dev-update` must run on the update that delivers it. This step sits before the version comparison because both of that step's outcomes jump onward.
```bash
NEW_SKILL=$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(os.path.join(i['installPath'],'skills/dev-update/SKILL.md')) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)
echo "$NEW_SKILL"
```
**Read that file now, and execute its steps from Step 3 onward instead of the ones in your context.** Where the two differ, the file wins — it is the version the user just chose to install. If the path is empty or unreadable, say so and continue with the steps you have.

## Step 3 — Read the new version

Run the Step 1 block again. If the version **changed**, continue to Step 3b. If it is **the same as before**, the plugin catalog cache is stale — run a cache-bust update:
```bash
# Delete the catalog cache so Claude Code fetches a fresh copy
rm -f ~/.claude/plugins/plugin-catalog-cache.json

# Re-fetch the marketplace and update
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```
Then re-read the version. If it still hasn't changed, the user is genuinely on the latest. Say: "Already on the latest version." Then **continue to Step 3b anyway — do not stop.** If it changed after the cache bust, continue to Step 3b.

## Step 3b — Migrate settings and audit the active change

Onboarding writes `.claude/settings.json` **only if absent**, so an older repo misses what shipped since. Dry-run the migrator, show what it proposes, then apply; prefer the plugin's migrator, the repo's copy may be the version being fixed.
```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
MIG="$ROOT/shared/ci/first-pass/migrate_project.py"; [[ -f "$MIG" ]] || MIG="ci/first-pass/migrate_project.py"
PY=""; for c in python3 python py; do "$c" -c "import yaml" >/dev/null 2>&1 && { PY="$c"; break; }; done
if [[ ! -f "$MIG" ]]; then echo "No migrator found in the project or the plugin: skipping the change-file migration."
elif [[ -z "$PY" ]]; then echo "! No interpreter with PyYAML: migration and change-file audit did NOT run. pip install pyyaml, then re-run."
else
  "$PY" "$MIG" --root . || echo "! The migrator did not complete: the active change has NOT been audited."
  "$PY" "$MIG" --root . --apply
fi
```
Permissions merge additively. The migrator also reports any active change lightened without declaring `first_pass`: those certified clean before because enforcement never engaged and will now fail — intended, say so. A non-zero exit means the audit could not read the change file at all (no PyYAML, invalid YAML, not a mapping): say that plainly and never report the change as verified.

## Step 4 — Re-wire hooks if needed

Check whether `.hitl/hooks/` exists in the current project. If it does not exist, follow the same hook-wiring steps as Step 0 in `/hitl:dev-start-from-prd`: create the wrapper scripts and `.claude/settings.json`.

If it already exists, check **every** marker the current template carries; a wrapper can have current discovery and still be stale:
```bash
for m in installed_plugins.json "command -v" HITL_PY; do grep -q "$m" .hitl/hooks/welcome.sh || echo "STALE: missing $m"; done
[[ -f .hitl/hooks/first-pass-permissions.sh ]] || echo "STALE: first-pass-permissions.sh absent"
```
On any `STALE` line, delete `.hitl/hooks/` and re-create all **nine** wrappers from the template in Step 0 of `/hitl:dev-start-from-prd` (**sub-steps 1-3 only**: create the wrappers, then come straight back here to Step 4.5. Ignore its closing "restart and re-run this command" instruction; following it here skips Steps 4.5 through 4.10 and the completion message). What each marker protects is in [rewire-hooks.md](rewire-hooks.md).

Also check `.claude/settings.json`: `$CLAUDE_PROJECT_DIR`, the `statusLine` entry (what it **points at** and its **shape**, not merely that the key is present) and the `SessionStart` → `hitl-gate.sh` hook. The Step 3b migrator wraps a bare-string `statusLine` and reports a missing or re-pointed one:
```bash
grep "CLAUDE_PROJECT_DIR" .claude/settings.json
grep -q 'hooks/statusline-hitl.sh' .claude/settings.json \
  || echo "statusLine missing or pointing at a stale script: re-create settings.json"
grep "hitl-gate" .claude/settings.json
```
A `statusLine` that runs a **pre-plugin standalone script** passes a grep: read [legacy-statusline.md](legacy-statusline.md), which shows the stale entry and removes the script. If anything is wrong, repair the file; **do not delete it** (the template is a complete file, not a merge, and deleting takes the team's `permissions`, `env`, MCP wiring and every non-HITL hook with it; see [rewire-hooks.md](rewire-hooks.md)). Back it up, then correct only the wrong keys:
```bash
cp .claude/settings.json .claude/settings.json.bak && echo "backed up to .claude/settings.json.bak"
```
Show the user the diff of what you propose to change before writing. Only if the file is absent or unparseable should you write the template wholesale — and say so when you do. Say: "Hook wrappers and settings.json re-created with current patterns. Wrappers now check `~/.claude/plugins/installed_plugins.json` first (current Claude Code) with fallback to legacy `settings.json`. Hook commands now use `$CLAUDE_PROJECT_DIR` for reliable path resolution. `statusLine` and the `SessionStart` change-intake gate are wired."

## Step 4.5 — Migrate the change file to the current workflow schema

If `.hitl/current-change.yaml` exists, migrate it to the current workflow definition so the breadcrumb stays correct after a workflow's steps change. It shows a diff and **requires confirmation** before writing. **Follow the full procedure in [change-file-migration.md](change-file-migration.md).** Run it in full — the generator, the diff, the confirmation prompt, and the promote/cleanup steps.

## Step 4.6 — Re-sync the copied-in CI validators

The repo carries its own copy of the plugin's CI tools (they run by **project-relative path**); refresh them and **install** ones added since onboarding. They are **co-owned**: the per-file protocol, and why HITL's own test suites are removed rather than fixed, are in [resync-validators.md](resync-validators.md); read it before acting on anything the migrator reports.
```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
if [[ -z "$ROOT" ]]; then
  echo "Plugin root not found: skipping CI-tool re-sync."
else
  MIG="$ROOT/shared/ci/first-pass/migrate_project.py"
  PY=""; for c in python3 python py; do "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
  if [[ -f "$MIG" && -n "$PY" ]]; then
    "$PY" "$MIG" --root . --sync-validators "$ROOT" --apply
  else
    echo "  ! No shipped migrator or no python: validators NOT synced. Nothing was overwritten."
  fi
  # Remove dev-repo test suites that earlier versions synced in (plugin issue #29). They resolve
  # paths that exist only in the platform repo, so in a product repo they fail on collection and
  # block the consumer's CI.
  #
  # A filename is NOT evidence of authorship. A team writing tests for the shipped validator
  # check_skips.py names theirs test_check_skips.py — pytest convention — and this very step, by
  # removing the shipped tests, invites them to. Deleting on name alone destroys that file with no
  # recovery path when it is untracked. So a file is removed only when it is BOTH tracked in this
  # repo AND hashes to a version HITL actually shipped. Anything else is reported, never deleted.
  HASHES="$ROOT/shared/ci/retired-tests.sha256"
  if [[ -f "ai/claude/start-change/SKILL.md" ]]; then
    :  # This is the HITL platform repo itself, where these tests are the real suite. Never touch them.
  elif [[ ! -f "$HASHES" ]]; then
    echo "  (no retired-test manifest in this plugin build: skipping stale-test cleanup)"
  else
    removed=(); kept=()
    while IFS= read -r stale; do
      [[ -f "$stale" && ! -L "$stale" ]] || continue
      git ls-files --error-unmatch "$stale" >/dev/null 2>&1 || continue   # untracked => not ours
      if command -v shasum >/dev/null 2>&1; then h=$(shasum -a 256 "$stale" | awk '{print $1}')
      elif command -v sha256sum >/dev/null 2>&1; then h=$(sha256sum "$stale" | awk '{print $1}')
      else echo "  (no sha256 tool: skipping stale-test cleanup; nothing was deleted)"; break; fi
      # Match hash AND basename: the manifest is hash->basename, so hash alone would let content
      # shipped as file A delete a file at path B.
      if grep -qi "^$h  $(basename "$stale")$" "$HASHES"; then
        git rm -q --cached "$stale" 2>/dev/null || true
        if rm -f "$stale" 2>/dev/null && [[ ! -e "$stale" ]]; then removed+=("$stale"); fi
      else
        kept+=("$stale")
      fi
    done < <(printf '%s\n' \
      ci/first-pass/test_check_skips.py ci/first-pass/test_driver_e2e.py ci/first-pass/test_first_pass_lib.py ci/first-pass/test_size_plan.py \
      ci/first-pass/test_129_api_fast_track_e2e.py ci/first-pass/test_skipped_line.py \
      ci/manifest-agentic/test_check_manifest_agentic.py ci/manifest-agentic/test_schema_and_examples.py \
      tools/manifest-agentic/test_gen_baseline_evals.py tools/manifest-agentic/test_generate_views.py \
      ci/manifest-drift/test_check_manifest_drift.py \
      ci/agentic-advisor/test_advisor_e2e.py ci/agentic-advisor/test_catalog_lint.py \
      ci/agentic-advisor/test_compose.py ci/agentic-advisor/test_records.py \
      ci/agentic-advisor/test_render_map.py \
      ci/data-layer/test_check_data_layer.py ci/data-layer/test_scorecard.py tools/data-layer/test_adapters.py \
      ci/linked/test_linked.py ci/test-scenarios/test_check_scenarios.py)
    for f in ${removed[@]+"${removed[@]}"}; do echo "  ✓ removed $f (HITL test that cannot run in this repo)"; done
    for f in ${kept[@]+"${kept[@]}"}; do
      echo "  • kept $f: same name as a HITL test but different content, so it is yours or you edited it." >&2
      echo "    If it is a leftover HITL test it will fail here; delete it yourself once you have looked." >&2
    done
  fi

  # stage ONLY the paths that exist — a single `git add` over an absent optional path errors on the whole
  # pathspec and (with `|| true`) would silently stage NOTHING (codex-7).
  for p in ci/first-pass ci/manifest-agentic tools/manifest-agentic ci/manifest-drift ci/adversarial ci/data-layer tools/data-layer ci/linked ci/test-scenarios .github/workflows/first-pass-check.yml .github/workflows/data-layer-check.yml .github/workflows/test-scenarios-check.yml; do
    [[ -e "$p" ]] && git add "$p"
  done
fi
```
**If any file is listed as differing, STOP and ask**, per file, using the command the migrator printed:

> `<path>` differs from the version shipped with v$NEW_VER. Overwrite it with the shipped copy, or keep
> yours? (Your edits are lost if you overwrite; keeping yours means you miss any upstream fix.)

Only on an explicit yes for that file run the printed `--overwrite <path>` command. Never overwrite a file nobody said yes to, and never "resolve" a difference by deleting the repo's copy. If any tool was installed or updated, commit it: `git commit -m "chore(hitl): sync CI validators to v$NEW_VER"`. Say which tools were installed, which differ and were kept, or "CI validators already current".

## Step 4.7 — Re-sync the semgrep convention rules

`.semgrep/` is what `/hitl:dev-check-conventions` scans with; onboarding copies it once, so this step is how a rule fix reaches an onboarded project. The rule set is **co-owned**, so this never blind-copies. **Read [resync-semgrep.md](resync-semgrep.md) and run its block**: it installs absent rules, prints a diff for modified ones, honours `.semgrep/.hitl-optout`, and reports superseded files.
**If any file is listed as differing, STOP and ask** — show the diff above and ask, per file:

> `.semgrep/<rel>` differs from the version shipped with v$NEW_VER. Overwrite it with the shipped rule, or
> keep yours? (Your edits are lost if you overwrite; keeping yours means you miss any upstream rule fix.)

Only on an explicit yes, copy that one file:
```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
cp "$ROOT/shared/semgrep/<rel>" ".semgrep/<rel>"
```
Then stage what changed and verify the rule set still loads:
```bash
[[ -d .semgrep ]] && git add .semgrep
command -v semgrep >/dev/null 2>&1 && semgrep scan --config .semgrep/ --error . >/dev/null 2>&1 \
  && echo "  ✓ rule set loads and the repo is clean" \
  || echo "  (semgrep not installed, or findings exist: run /hitl:dev-check-conventions)"
```
Commit with `git commit -m "chore(hitl): sync semgrep rules to v$NEW_VER"`.

## Step 4.8 — Ensure CLAUDE.md announces HITL

`CLAUDE.md` is the only thing that tells a developer **without the plugin** that this project uses HITL. This maintains one marker-delimited block and never overwrites the team's file; a truncated `HITL:BEGIN` leaves it untouched (exit 3).
```bash
# Resolve here: shell state does not persist between tool calls, and inheriting $ROOT from an
# earlier step left it empty, so this printed a false "not in this build — skipping".
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
BLOCK="$ROOT/shared/templates/claude-md-hitl-block.md"
SCRIPT="$ROOT/shared/tools/hitl-onboarding/ensure_claude_block.py"
if [[ -f "$BLOCK" && -f "$SCRIPT" ]]; then
  python3 "$SCRIPT" CLAUDE.md "$BLOCK" || true   # exit 3 is a warning, not a failure
  [[ -f CLAUDE.md ]] && git add CLAUDE.md
elif [[ -f "$ROOT/.claude-plugin/plugin.json" ]]; then
  # A real plugin is installed, so the template SHOULD be here. Saying "not in this build" would
  # dress a path defect up as a legitimate absence — which is exactly how the doubled-root bug
  # hid for a whole release (#82).
  echo "UNEXPECTED: plugin found at $ROOT but no block template at $BLOCK." >&2
  echo "  The CLAUDE.md section was NOT installed. Report this: do not ignore it." >&2
else
  echo "No HITL block template in this plugin build: skipping."
fi
```

## Step 4.9 — Ensure persona profiles are gitignored

`.hitl/people/` holds descriptions of named colleagues, and `shared/personas.md` promises they are **local by default**. Onboarding adds the rule; an older project gets it here. Idempotent.
```bash
GITIGNORE=".gitignore"
if ! grep -q "^\.hitl/people/" "$GITIGNORE" 2>/dev/null; then
  printf '\n# HITL persona profiles — descriptions of people. Local unless your team decides otherwise.\n.hitl/people/\n' >> "$GITIGNORE"
  git add "$GITIGNORE" 2>/dev/null || true
fi
if ! grep -q "^\.hitl/breadcrumb\.txt" "$GITIGNORE" 2>/dev/null; then
  printf '.hitl/breadcrumb.txt\n' >> "$GITIGNORE"   # breadcrumb band cache (FR-37), rewritten every prompt
  git add "$GITIGNORE" 2>/dev/null || true
fi
# Verify, do not assert. .gitignore has no effect on a file git already tracks, and outside a repo
# check-ignore fails in a way that reads as "not ignored".
if git check-ignore -q .hitl/people/ 2>/dev/null; then
  echo "✓ .gitignore: .hitl/people/ excluded"
else
  echo "COULD NOT exclude .hitl/people/. Do not tell anyone a profile written here is local."
fi
```
**If a profile is already tracked**, the rule does not untrack it. Say so and let them decide:
```bash
TRACKED=$(git ls-files '.hitl/people/' 2>/dev/null)
if [[ -n "$TRACKED" ]]; then
  echo "NOTE: these profiles are already tracked, so the ignore rule does not cover them:"
  echo "$TRACKED" | sed 's/^/  /'
  echo "  They are in git history. 'git rm --cached' stops future commits but does not remove the past."
  echo "  Tell the people they describe."
fi
```

## Step 4.10 — Ask about release notices, once per person

Same script as onboarding; it asks nobody twice, and there is no share line here.
```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)}"
RN="$ROOT/shared/tools/hitl-onboarding/release_notice.py"
if [[ -f "$RN" ]]; then python3 "$RN" state; else echo "release_notice.py is not in this build: skipping."; fi
```
The first line of the output is the verdict. On `already-answered` or `gh-logged-out`, say the second line to the person and move on. On `ask`, put question 1 in front of the person word for word and wait; then question 2 and wait. An empty answer is no. Then record both answers: `python3 "$RN" record --notice <yes|no> --star <yes|no|skipped>`. If the first answer was yes, show the output of `python3 "$RN" body` (the exact comment) and only then run `python3 "$RN" post --confirmed`. If the second was yes, run `python3 "$RN" star --confirmed`.

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
