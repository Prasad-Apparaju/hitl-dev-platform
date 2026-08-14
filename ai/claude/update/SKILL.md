---
description: Update the HITL plugin to the latest version. Re-runs the plugin install command to pull the latest release, shows what changed, and re-wires hooks if needed.
argument-hint: ""
disable-model-invocation: true
---

# Update HITL Plugin

---

## Step 1 — Read the current version

Run:
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

If the result is `NOT_FOUND`, stop and say: "The HITL plugin was not found. Confirm it was installed with `claude plugin install hitl@hitl`."

Record the version shown as the **old version**.

---

## Step 2 — Update the plugin

Run:
```bash
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

`marketplace update` refreshes the cached manifest so the latest release is visible. `plugin update` installs it.

---

## Step 2.5 — Re-read this skill from the version you just installed

**Do this before anything else, unconditionally.** You are executing the `SKILL.md` that was loaded
when the command started — the version you are updating *from*. Step 2 has just installed a
different one, whose `dev-update` may fix or change every step below. If you continue from the copy
in your context, a fix that ships **inside** `dev-update` never runs on the update that delivers it;
it waits for the next release. Worse, a step that was later found to be *unsafe* still runs.

This step is deliberately placed before the version comparison, because both of its outcomes jump
onward and would skip anything after them.

```bash
NEW_SKILL=$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(os.path.join(i['installPath'],'skills/dev-update/SKILL.md')) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)
echo "$NEW_SKILL"
```

**Read that file now, and execute its steps from Step 3 onward instead of the ones in your
context.** Where the two differ, the file wins — it is the version the user just chose to install.
If the path is empty or unreadable, say so and continue with the steps you have.

---

## Step 3 — Read the new version

Run:
```bash
python3 -c "
import json, os, sys
try:
    p = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
    data = json.load(open(p))
    entry = data['plugins']['hitl@hitl'][0]
    print(entry['version']); sys.exit(0)
except Exception: pass
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

If the version **changed**, continue to Step 4.

If the version is **the same as before**, the plugin catalog cache is stale — run a cache-bust update:

```bash
# Delete the catalog cache so Claude Code fetches a fresh copy
rm -f ~/.claude/plugins/plugin-catalog-cache.json

# Re-fetch the marketplace and update
claude plugin marketplace update hitl
claude plugin update hitl@hitl
```

Then re-read the version (repeat the python3 block above). If it still hasn't changed, the installed commit SHA already matches what the marketplace advertises — the user is genuinely on the latest. Say: "Already on the latest version." Then **continue to Step 3b anyway — do not stop.**

Stopping here was a real defect. Steps 3b and 4.x do not update the plugin; they reconcile *this repo* with the installed plugin — hooks, validators, `CLAUDE.md`, and the cleanup of files an earlier version installed. Every one is idempotent. Skipping them on "already latest" meant a repo could never be repaired once its version matched, which is exactly the state a user is in when they run the command a second time to fix something.

If it changed after the cache bust, continue to Step 4.


---

## Step 3b — Migrate settings and audit the active change

Onboarding writes `.claude/settings.json` **only if absent**, so a repo onboarded before a release
keeps its old file and misses what shipped since. Dry-run the migrator, show the user what it
proposes, then apply. Also refresh the validator copies — they are snapshots, not references, so
without this new checks never reach the project they protect.

```bash
MIG="ci/first-pass/migrate_project.py"
[[ -f "$MIG" ]] || MIG="$CLAUDE_PLUGIN_ROOT/shared/ci/first-pass/migrate_project.py"
python3 "$MIG" --root .                    # review, then:
python3 "$MIG" --root . --apply
[[ -d "$CLAUDE_PLUGIN_ROOT/shared/ci/first-pass" ]] && mkdir -p ci/first-pass \
  && cp "$CLAUDE_PLUGIN_ROOT/shared/ci/first-pass/"*.py ci/first-pass/
```

Permissions merge additively. The migrator also reports any active change lightened without
declaring `first_pass`: those certified clean before because enforcement never engaged and will now
fail. That is intended — say so, so it is not read as a regression.

---

## Step 4 — Re-wire hooks if needed

Check whether `.hitl/hooks/` exists in the current project.

If it does not exist, follow the same hook-wiring steps as Step 0 in `/hitl:dev-start-from-prd`: create the wrapper scripts and `.claude/settings.json`.

If it already exists, check **every** marker the current template carries, not just plugin discovery — a wrapper can have current discovery and still be stale, and testing one marker is how that goes unnoticed:

```bash
for m in installed_plugins.json "command -v" HITL_PY; do grep -q "$m" .hitl/hooks/welcome.sh || echo "STALE: missing $m"; done
[[ -f .hitl/hooks/first-pass-permissions.sh ]] || echo "STALE: first-pass-permissions.sh absent"
```

No `installed_plugins.json` = pre-v1.0.9 discovery, broken on current Claude Code. No `command -v` probe or `HITL_PY` = pre-issue-#14: a bare `python3` is the Microsoft Store stub on Windows, on PATH but running nothing, so every hook silently no-ops — and a lone `installed_plugins.json` grep passes straight over it. No `first-pass-permissions.sh` = pre-CR-15, so the permission policy never engages. On any of those, delete `.hitl/hooks/` and re-create all **nine** wrappers (`welcome`, `hitl-gate`, `check-hitl-context`, `first-pass-permissions`, `check-domain-boundary`, `rebuild-graph`, `write-session-summary`, `sync-step-to-issue`, `statusline-hitl`) from the template in Step 0 of `/hitl:dev-start-from-prd`, which is the single source of truth for wrapper contents.

Also check `.claude/settings.json` for the `$CLAUDE_PROJECT_DIR` fix, the `statusLine` entry, and the `SessionStart` → `hitl-gate.sh` hook. Assert what `statusLine` **points at**, not merely that the key is present:
```bash
grep "CLAUDE_PROJECT_DIR" .claude/settings.json
grep -q 'hooks/statusline-hitl.sh' .claude/settings.json \
  || echo "statusLine missing or pointing at a stale script — re-create settings.json"
grep "hitl-gate" .claude/settings.json
```

A repo onboarded before the `.hitl/hooks/` layout has a `statusLine` that runs a **pre-plugin standalone script**:

```json
"statusLine": { "type": "command",
  "command": "bash \"$CLAUDE_PROJECT_DIR/.hitl/statusline.sh\"" }
```

A `grep "statusLine"` matches that happily, so the check passes and the stale script survives every subsequent upgrade. It hardcodes the 32-step development flow and cannot render any other workflow, so on a 6-step `docs` change it reports `Step 3/32` with a trail of steps the change does not contain — while the `UserPromptSubmit` breadcrumb from `welcome.sh` renders correctly. The human and the model then read two disagreeing status lines, which is very hard to diagnose from inside a session (plugin issue #23 item 1).

If a legacy `.hitl/statusline.sh` is present, delete it during re-sync so nothing can be re-pointed at it:
```bash
[ -f .hitl/statusline.sh ] && rm -f .hitl/statusline.sh && echo "Removed legacy .hitl/statusline.sh (superseded by .hitl/hooks/statusline-hitl.sh)"
```

If `CLAUDE_PROJECT_DIR` is absent, the hook commands use relative paths and fail when Claude Code's cwd differs from the project root. If `statusLine` is absent **or points anywhere other than `hooks/statusline-hitl.sh`**, the persistent HITL breadcrumb is missing or wrong. If `hitl-gate` is absent, the session-start change-intake gate won't fire. In any of these cases, delete `.claude/settings.json` and re-create it from the template in Step 0 of `/hitl:dev-start-from-prd`.

Say:

"Hook wrappers and settings.json re-created with current patterns. Wrappers now check `~/.claude/plugins/installed_plugins.json` first (current Claude Code) with fallback to legacy `settings.json`. Hook commands now use `$CLAUDE_PROJECT_DIR` for reliable path resolution. `statusLine` and the `SessionStart` change-intake gate are wired."

---

## Step 4.5 — Migrate the change file to the current workflow schema

If `.hitl/current-change.yaml` exists, migrate its content to the current workflow definition.
This is what keeps the breadcrumb correct after a workflow's steps change between versions
(e.g. brownfield growing 8 → 11 steps). It shows a diff and **requires confirmation** before
writing — it never overwrites silently, and it preserves comments and project-authored
per-step fields by remapping on each step's stable `key`.

**Follow the full procedure in [change-file-migration.md](change-file-migration.md).** Run it
in full — the generator, the diff, the confirmation prompt, and the promote/cleanup steps.

## Step 4.6 — Re-sync the copied-in CI validators

Some validators run via **project-relative paths**, so the repo carries its own copy of the plugin's CI
tools (the plugin isn't present in CI). On upgrade, refresh them so an existing repo picks up new or fixed
validators without re-onboarding — and **install** ones added after this repo was first onboarded (e.g. First
Pass, FR-29, added in 2.4.x). Tool **code** is refreshed (plugin-owned); repo-owned files (waivers, the change
ledger, customized `.github/workflows/*`) are preserved.

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-}"
[[ -z "$ROOT" ]] && ROOT=$(python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));[print(i['installPath']) for i in d.get('plugins',{}).get('hitl@hitl',[]) if os.path.isfile(os.path.join(i.get('installPath',''),'.claude-plugin/plugin.json'))]" 2>/dev/null | head -1)
if [[ -z "$ROOT" ]]; then
  echo "Plugin root not found — skipping CI-tool re-sync."
else
  # First Pass (FR-29): fail-closed skip-ledger validator + its co-located crit catalog + CI gate.
  if [[ -d "$ROOT/shared/ci/first-pass" ]]; then
    mkdir -p ci/first-pass
    cp "$ROOT/shared/ci/first-pass/"*.py ci/first-pass/ 2>/dev/null
    [[ -f "$ROOT/shared/workflows.yaml" ]] && cp "$ROOT/shared/workflows.yaml" ci/first-pass/workflows.yaml   # plugin-canonical crit; safe to refresh
    if [[ -f "$ROOT/shared/ci-workflows/first-pass-check.yml" && ! -f .github/workflows/first-pass-check.yml ]]; then
      mkdir -p .github/workflows && cp "$ROOT/shared/ci-workflows/first-pass-check.yml" .github/workflows/
    fi
    echo "  ✓ ci/first-pass/ (First Pass validator + catalog) synced"
  fi
  # Compound-agentic surface (#10): the system-manifest validator + posture-view generator, invoked
  # repo-relative by pm-design-feature. Self-contained; PRESERVE the repo's own manifest-waivers.yaml.
  if [[ -d "$ROOT/shared/ci/manifest-agentic" ]]; then
    mkdir -p ci/manifest-agentic tools/manifest-agentic
    cp "$ROOT/shared/ci/manifest-agentic/"*.py ci/manifest-agentic/ 2>/dev/null
    [[ ! -f ci/manifest-agentic/manifest-waivers.yaml && -f "$ROOT/shared/ci/manifest-agentic/manifest-waivers.yaml" ]] && cp "$ROOT/shared/ci/manifest-agentic/manifest-waivers.yaml" ci/manifest-agentic/
    cp "$ROOT/shared/tools/manifest-agentic/"*.py tools/manifest-agentic/ 2>/dev/null
    echo "  ✓ ci/manifest-agentic/ (compound-agentic validator) synced — kept your manifest-waivers.yaml"
  fi
  # Release gate (#80): the adversarial-review validator, so a repo's own CI can run it.
  if [[ -d "$ROOT/shared/ci/adversarial" ]]; then
    mkdir -p ci/adversarial
    cp "$ROOT/shared/ci/adversarial/"*.py ci/adversarial/ 2>/dev/null
    echo "  ✓ ci/adversarial/ (release review gate) synced"
  fi
  # Manifest drift (already onboarded in most repos): refresh the checker code only if present.
  if [[ -d "$ROOT/shared/ci/manifest-drift" && -d ci/manifest-drift ]]; then
    cp "$ROOT/shared/ci/manifest-drift/"*.py ci/manifest-drift/ 2>/dev/null
    echo "  ✓ ci/manifest-drift/ refreshed"
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
    echo "  (no retired-test manifest in this plugin build — skipping stale-test cleanup)"
  else
    removed=(); kept=()
    while IFS= read -r stale; do
      [[ -f "$stale" && ! -L "$stale" ]] || continue
      git ls-files --error-unmatch "$stale" >/dev/null 2>&1 || continue   # untracked => not ours
      if command -v shasum >/dev/null 2>&1; then h=$(shasum -a 256 "$stale" | awk '{print $1}')
      elif command -v sha256sum >/dev/null 2>&1; then h=$(sha256sum "$stale" | awk '{print $1}')
      else echo "  (no sha256 tool — skipping stale-test cleanup; nothing was deleted)"; break; fi
      # Match hash AND basename: the manifest is hash->basename, so hash alone would let content
      # shipped as file A delete a file at path B.
      if grep -qi "^$h  $(basename "$stale")$" "$HASHES"; then
        git rm -q --cached "$stale" 2>/dev/null || true
        if rm -f "$stale" 2>/dev/null && [[ ! -e "$stale" ]]; then removed+=("$stale"); fi
      else
        kept+=("$stale")
      fi
    done < <(printf '%s\n' \
      ci/first-pass/test_check_skips.py ci/first-pass/test_driver_e2e.py ci/first-pass/test_first_pass_lib.py \
      ci/manifest-agentic/test_check_manifest_agentic.py ci/manifest-agentic/test_schema_and_examples.py \
      tools/manifest-agentic/test_gen_baseline_evals.py tools/manifest-agentic/test_generate_views.py \
      ci/manifest-drift/test_check_manifest_drift.py \
      ci/agentic-advisor/test_advisor_e2e.py ci/agentic-advisor/test_catalog_lint.py \
      ci/agentic-advisor/test_compose.py ci/agentic-advisor/test_records.py \
      ci/agentic-advisor/test_render_map.py)
    for f in ${removed[@]+"${removed[@]}"}; do echo "  ✓ removed $f (HITL test that cannot run in this repo)"; done
    for f in ${kept[@]+"${kept[@]}"}; do
      echo "  • kept $f — same name as a HITL test but different content, so it is yours or you edited it." >&2
      echo "    If it is a leftover HITL test it will fail here; delete it yourself once you have looked." >&2
    done
  fi

  # stage ONLY the paths that exist — a single `git add` over an absent optional path errors on the whole
  # pathspec and (with `|| true`) would silently stage NOTHING (codex-7).
  for p in ci/first-pass ci/manifest-agentic tools/manifest-agentic ci/manifest-drift ci/adversarial .github/workflows/first-pass-check.yml; do
    [[ -e "$p" ]] && git add "$p"
  done
fi
```

**Why removal and not a fix:** these suites test HITL's own internals against the platform's source
layout. One of them (`test_driver_e2e.py`) extracts the Step 6 generator from `start-change/SKILL.md`,
a file no product repo has or should have — so it cannot be made to pass outside this repo. CI in a
product repo runs the **validators**; the validators' tests belong with the validators' source.

If any tool was installed or updated, commit it: `git commit -m "chore(hitl): sync CI validators to v$NEW_VER"`.
Say which tools were synced (or "CI validators already current").

---

## Step 4.7 — Re-sync the semgrep convention rules

`.semgrep/` is what `/hitl:dev-check-conventions` scans with. `init-project.sh` copies it once at
onboarding, so without this step a rule fix never reaches an already-onboarded project (issue #47).

Unlike `ci/` validators, a product repo's rule set is **co-owned** — teams add and tune rules — so
this never blind-copies:

| Case | Action |
|---|---|
| Shipped rule the repo does **not** have | install it |
| Shipped rule, byte-identical | leave alone, say nothing |
| Shipped rule the repo has **modified** | show the diff and **ask** before overwriting |
| Rule the repo added itself | never touched, never reported as drift |
| Rule listed in `.semgrep/.hitl-optout` | never installed — a deliberate removal stays removed |

Without the opt-out file, "install anything absent" would resurrect a deliberately deleted rule on
every update. One path per line, `#` comments allowed (e.g. `best-practices/tenant-isolation.yaml`).

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$ROOT}"
if [[ -z "$ROOT" || ! -d "$ROOT/shared/semgrep" ]]; then
  echo "No shipped rule set found — skipping semgrep re-sync."
else
  new=(); changed=(); skipped=()
  while IFS= read -r src; do
    rel="${src#"$ROOT"/shared/semgrep/}"
    [[ "$rel" == "install.sh" ]] && continue
    # Honour a deliberate removal — otherwise every update resurrects the deleted rule.
    if [[ -f .semgrep/.hitl-optout ]] && grep -qxF "$rel" <(grep -v '^[[:space:]]*#' .semgrep/.hitl-optout); then
      skipped+=("$rel"); continue
    fi
    if [[ ! -f ".semgrep/$rel" ]]; then
      new+=("$rel")
    elif ! cmp -s "$src" ".semgrep/$rel"; then
      changed+=("$rel")
    fi
  done < <(find "$ROOT/shared/semgrep" -type f \( -name "*.yaml" -o -name "*.yml" -o -name ".semgrepignore" \))
  [[ ${#skipped[@]} -gt 0 ]] && echo "  · opted out (.semgrep/.hitl-optout): ${skipped[*]}"

  # Install everything absent — nothing to lose, nothing to confirm.
  for rel in "${new[@]}"; do
    mkdir -p ".semgrep/$(dirname "$rel")"
    cp "$ROOT/shared/semgrep/$rel" ".semgrep/$rel"
    echo "  + installed .semgrep/$rel"
  done

  # Locally modified files are reported with a diff and left untouched for now.
  for rel in "${changed[@]}"; do
    echo "  ~ .semgrep/$rel differs from the shipped version:"
    diff -u ".semgrep/$rel" "$ROOT/shared/semgrep/$rel" | sed 's/^/      /'
  done
  [[ ${#changed[@]} -eq 0 && ${#new[@]} -eq 0 ]] && echo "  ✓ semgrep rules already current"

  # Superseded files: a rule that was RENAMED upstream leaves its old file behind, and the
  # loop above cannot tell that apart from a rule the project wrote itself, so it would sit
  # there forever as dead config. Report, never auto-delete — the project may have edited it.
  for old in best-practices/pydantic-validation.yaml; do
    if [[ -f ".semgrep/$old" ]]; then
      echo "  ! .semgrep/$old is superseded — it was renamed upstream and made framework-neutral."
      echo "    Its rule could never fire — delete it once you are happy with the replacement."
    fi
  done
fi
```

**If any file is listed as differing, STOP and ask** — show the diff above and ask, per file:

> `.semgrep/<rel>` differs from the version shipped with v$NEW_VER. Overwrite it with the shipped rule, or
> keep yours? (Your edits are lost if you overwrite; keeping yours means you miss any upstream rule fix.)

Only on an explicit yes, copy that one file:
```bash
cp "$ROOT/shared/semgrep/<rel>" ".semgrep/<rel>"
```

Then stage what changed and verify the rule set still loads:
```bash
[[ -d .semgrep ]] && git add .semgrep
command -v semgrep >/dev/null 2>&1 && semgrep scan --config .semgrep/ --error . >/dev/null 2>&1 \
  && echo "  ✓ rule set loads and the repo is clean" \
  || echo "  (semgrep not installed, or findings exist — run /hitl:dev-check-conventions)"
```

Commit with `git commit -m "chore(hitl): sync semgrep rules to v$NEW_VER"`.

---

## Step 4.8 — Ensure CLAUDE.md announces HITL

`CLAUDE.md` is the only thing that can tell a developer this project uses HITL **when they have not
installed the plugin** — no hook runs and no skill exists, so nothing else in the repo speaks.
Onboarding used to skip it whenever one already existed, which is every real project.

Never overwrites the team's file: it maintains one marker-delimited block. Creates, appends,
refreshes, or stays silent if current; a truncated `HITL:BEGIN` leaves the file untouched (exit 3).

```bash
ROOT="${CLAUDE_PLUGIN_ROOT:-$ROOT}"
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
  echo "  The CLAUDE.md section was NOT installed. Report this — do not ignore it." >&2
else
  echo "No HITL block template in this plugin build — skipping."
fi
```

---

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
