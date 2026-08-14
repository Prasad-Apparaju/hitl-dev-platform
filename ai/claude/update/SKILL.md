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

Then re-read the version (repeat the python3 block above). If it still hasn't changed, the installed commit SHA already matches what the marketplace advertises — the user is genuinely on the latest. Say: "Already on the latest version — no changes." and stop.

If it changed after the cache bust, continue to Step 4.

Show: "Updated: **v\<old\>** → **v\<new\>**"

Then show the relevant `## [<new-version>]` section from `CHANGELOG.md` in the plugin directory. If `CHANGELOG.md` is not present, say: "Full release notes: https://github.com/Prasad-Apparaju/hitl-dev-platform/blob/main/CHANGELOG.md"

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
This is what keeps the breadcrumb correct after the workflow's steps change between versions
(e.g. the brownfield workflow growing from 8 → 11 steps). It is HITL: it shows a diff and
**requires confirmation** before writing.

Requires `python3` with PyYAML. The generator remaps by each step's stable `key`, so completion
status survives renumbering. It is **surgical at the line level**: it rewrites each existing step
*line* in place (updating `n` and `status`) and leaves everything else in the `workflow:` block —
**every comment (trailing or standalone) and every non-catalog per-step field such as `owner:`** —
untouched. Project-authored keys are carried across by `key`, not regenerated from the catalog (the
catalog cannot represent them), so nothing the user added is silently dropped; `phase`/`substep` are
refreshed from the catalog. Genuinely-new catalog steps are appended after the last existing step.
If the catalog is unchanged the block is left byte-for-byte intact and only the version stamps move.
The file is never round-tripped through a YAML dumper. It writes a proposed
`.hitl/current-change.yaml.migrated`, prints the per-step table **and the actual unified diff**, and
does **not** overwrite anything yet. (Limitation: step *lines* must be single-line flow maps — the
format HITL writes; a hand-authored multi-line block step is updated but flagged to verify by diff.)

```bash
CATALOG="${CLAUDE_PLUGIN_ROOT:-.}/shared/workflows.yaml"
[[ -f "$CATALOG" ]] || CATALOG="ai/shared/workflows.yaml"
# Resolve a working Python (Windows-safe: python3 is the MS Store stub there). See issue #14.
PY=""; for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done
[[ -n "$PY" ]] || { echo "No usable Python found (need python3, python, or py on PATH)."; exit 1; }
NEW_VER=$("$PY" -c "import json; print(json.load(open('${CLAUDE_PLUGIN_ROOT:-.}/.claude-plugin/plugin.json'))['version'])" 2>/dev/null || echo "0.0.0")

"$PY" - "$CATALOG" "$NEW_VER" << 'PY'
import sys, re, yaml, difflib
catalog_path, new_ver = sys.argv[1], sys.argv[2]
F = ".hitl/current-change.yaml"
text = open(F).read()                       # raw text — preserved verbatim except the step lines we splice
doc = yaml.safe_load(text) or {}            # parse is READ-ONLY (values only); we never dump the doc back
catalog = yaml.safe_load(open(catalog_path))["workflows"]

# Determine the workflow id.
wf = doc.get("workflow", {}) or {}
wf_id = wf.get("id")
if not wf_id:
    phase = (doc.get("current_step") or {}).get("phase", "")
    wf_id = {"PRD Setup":"prd","Brownfield Setup":"brownfield","Migration Setup":"migration",
             "Migration Review":"migration_review"}.get(phase, "development")

cat = catalog[wf_id]
cat_by_key = {s["key"]: s for s in cat["steps"]}
old_steps = {str(s.get("key")): s for s in wf.get("steps", [])}   # parsed dicts (carry owner + extras)
old_cur_n = (doc.get("current_step") or {}).get("number")
old_cur_key = next((str(s["key"]) for s in wf.get("steps", []) if s.get("status")=="current"), None)
def n_int(n):
    d = re.sub(r"[^0-9]", "", str(n)); return int(d) if d else 0

# 1) Resolve status per catalog key (remap by key; infer done/open for genuinely-new steps).
status_by_key, is_new = {}, {}
for s in cat["steps"]:
    key = s["key"]
    if key in old_steps:
        status_by_key[key] = old_steps[key].get("status", "open"); is_new[key] = False
    else:
        st = "open"
        if isinstance(old_cur_n, int) and n_int(s["n"]) and n_int(s["n"]) < old_cur_n:
            st = "done"
        status_by_key[key] = st; is_new[key] = True

# 2) Enforce EXACTLY ONE 'current' — repairs BOTH zero-current and duplicate-current (issue #22).
order = [s["key"] for s in cat["steps"]]
curr = [k for k in order if status_by_key[k] == "current"]
if len(curr) != 1:
    if curr:
        canon = old_cur_key if old_cur_key in curr else max(curr, key=order.index)
    else:
        canon = old_cur_key if old_cur_key in status_by_key else \
                next((k for k in order if status_by_key[k] != "done"), order[0])
    ci = order.index(canon)
    for k in curr:
        if k != canon: status_by_key[k] = "done" if order.index(k) < ci else "open"
    status_by_key[canon] = "current"

# 3) Emit ONE flow-map step line, carrying every non-core key across (catalog wins for phase/substep).
def tok(v):
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return str(v)
    v = str(v)
    return v if re.fullmatch(r"[A-Za-z0-9_./-]+", v) else '"%s"' % v.replace('"', '\\"')
CORE = ("n", "key", "label", "status")
def step_line(cstep, trailing=""):
    key = cstep["key"]
    parts = [f'n: {cstep["n"]}', f'key: {key}', f'label: {tok(cstep["label"])}', f'status: {status_by_key[key]}']
    for k in ("phase", "substep"):                       # catalog-canonical display keys
        if k in cstep: parts.append(f'{k}: {tok(cstep[k])}')
    for k, v in old_steps.get(key, {}).items():          # user-authored extras (owner, custom fields)
        if k in CORE or k in ("phase", "substep"): continue
        parts.append(f'{k}: {tok(v)}')
    line = "    - { " + ", ".join(parts) + " }"
    return line + ("  " + trailing if trailing else "")

# 4) SURGICAL splice: rewrite step LINES in place inside `steps:`; leave comments/blank lines verbatim.
step_re = re.compile(r"^\s*-\s*\{.*\}\s*(#.*)?$")
key_re  = re.compile(r"[{,]\s*key:\s*([^,}\s]+)")
block_m = re.search(r"(?ms)^workflow:.*?(?=^\S|\Z)", text)
block_changed, diff = False, []

if block_m:
    lines = block_m.group(0).split("\n")
    si = next((i for i, l in enumerate(lines) if re.match(r"^\s+steps:\s*$", l)), None)
    if si is not None:
        head, region = lines[:si+1], lines[si+1:]
        out_region, seen, block_style = [], set(), False
        for l in region:
            if step_re.match(l) and "{" in l:                        # a flow-map step line
                km = key_re.search(l); k = km.group(1) if km else None
                cm = re.search(r"\}\s*(#.*)$", l); trailing = cm.group(1) if cm else ""
                if k in cat_by_key:
                    new_l = step_line(cat_by_key[k], trailing)
                    if new_l != l: block_changed = True
                    out_region.append(new_l); seen.add(k)
                else:
                    block_changed = True; diff.append(f"  - removed  {k}")
            elif re.match(r"^\s*-\s", l) and "{" not in l:
                block_style = True; out_region.append(l)             # rare hand-authored multi-line step
            else:
                out_region.append(l)                                 # comment / blank — verbatim
        new_keys = [s["key"] for s in cat["steps"] if s["key"] not in seen]
        if new_keys:                                                 # append genuinely-new steps after last step line
            block_changed = True
            last = max((i for i, l in enumerate(out_region) if step_re.match(l)), default=len(out_region)-1)
            out_region = out_region[:last+1] + [step_line(cat_by_key[k]) for k in new_keys] + out_region[last+1:]
        for s in cat["steps"]:
            k = s["key"]; tag = "+ added" if is_new[k] else "  keep"
            diff.append(f"  {tag:7} {str(s['n']):>3} {k:<18} {status_by_key[k]}")
        def up_head(hl, key, val):
            for i, l in enumerate(hl):
                if re.match(rf"^\s+{key}:\s", l):
                    hl[i] = re.sub(rf"({key}:\s*).*", lambda m: m.group(1)+val, l, count=1); return
            hl.insert(1, f"  {key}: {val}")
        oh = list(head)
        up_head(head, "id", wf_id); up_head(head, "version", f'"{new_ver}"'); up_head(head, "total", str(cat["total"]))
        if head != oh: block_changed = True
        if block_style: print("  ⚠ block-style step(s) detected — lines updated; verify comments by the diff below.")
        nb = "\n".join(head + out_region);  nb += "" if nb.endswith("\n") else "\n"
        out = text[:block_m.start()] + nb + text[block_m.end():]
    else:
        out = text                                                   # no `steps:` — leave the block alone
else:
    # No workflow block (pre-v2 file): build a fresh one (comment preservation not applicable).
    block_changed = True
    wb = ["workflow:", f"  id: {wf_id}", f'  version: "{new_ver}"', f"  total: {cat['total']}", "  steps:"]
    wb += [step_line(s) for s in cat["steps"]]
    wb = "\n".join(wb) + "\n"
    if re.search(r"(?m)^current_step:", text):
        out = re.sub(r"(?m)^current_step:", wb + "current_step:", text, count=1)
    elif re.search(r"(?m)^source_artifacts:", text):
        out = re.sub(r"(?m)^source_artifacts:", wb + "source_artifacts:", text, count=1)
    else:
        out = text.rstrip("\n") + "\n" + wb

# 5) Upsert the scalar version stamps (replace in place, or prepend if missing).
def upsert(t, key, val):
    line = f'{key}: "{val}"'
    return re.sub(rf"(?m)^{key}:.*$", lambda m: line, t, count=1) if re.search(rf"(?m)^{key}:", t) else line + "\n" + t
out = upsert(out, "schema_version", "2.0")
out = upsert(out, "hitl_version", new_ver)

open(F + ".migrated", "w").write(out)
print(f"Workflow: {wf_id}  →  {cat['total']} steps (was {wf.get('total','?')})")
print("Step migration (remapped by key):"); print("\n".join(diff))
if not block_changed:
    print("\nCatalog unchanged — only version stamps updated; workflow block left byte-for-byte intact.")
ud = list(difflib.unified_diff(text.splitlines(), out.splitlines(),
                               F, F + ".migrated", lineterm=""))
print("\n--- actual diff (review before confirming) ---")
print("\n".join(ud) if ud else "(no changes)")
PY
```

Show the diff to the user. If they confirm, apply it:
```bash
mv .hitl/current-change.yaml.migrated .hitl/current-change.yaml
git add .hitl/current-change.yaml && git commit -m "chore(hitl): migrate change file to workflow schema v$NEW_VER"
```
If they decline, delete `.hitl/current-change.yaml.migrated` and leave the original untouched.
If the file already has `schema_version: "2.0"` and `workflow.version` equals the current plugin
version, skip this step and say "Change file already on the current workflow schema."

---

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
  # Manifest drift (already onboarded in most repos): refresh the checker code only if present.
  if [[ -d "$ROOT/shared/ci/manifest-drift" && -d ci/manifest-drift ]]; then
    cp "$ROOT/shared/ci/manifest-drift/"*.py ci/manifest-drift/ 2>/dev/null
    echo "  ✓ ci/manifest-drift/ refreshed"
  fi
  # stage ONLY the paths that exist — a single `git add` over an absent optional path errors on the whole
  # pathspec and (with `|| true`) would silently stage NOTHING (codex-7).
  for p in ci/first-pass ci/manifest-agentic tools/manifest-agentic ci/manifest-drift .github/workflows/first-pass-check.yml; do
    [[ -e "$p" ]] && git add "$p"
  done
fi
```

If any tool was installed or updated, commit it: `git commit -m "chore(hitl): sync CI validators to v$NEW_VER"`.
Say which tools were synced (or "CI validators already current").

---

## Step 4.7 — Re-sync the semgrep convention rules

`.semgrep/` is what `/hitl:dev-check-conventions` scans with. `init-project.sh` copies it once at
onboarding, so without this step a rule fix never reaches a project that is already set up — the
rule set stays frozen at whatever shipped the day it was onboarded (issue #47).

Unlike `ci/` validators, a product repo's rule set is **co-owned**: teams add their own rules and tune the
shipped ones for their stack. So this never blind-copies. Three cases, handled differently:

| Case | Action |
|---|---|
| Shipped rule the repo does **not** have | install it (a rule added after this repo was onboarded) |
| Shipped rule, byte-identical | leave alone, say nothing |
| Shipped rule the repo has **modified** | show the diff and **ask** before overwriting |
| Rule the repo added itself | never touched, never reported as drift |
| Rule listed in `.semgrep/.hitl-optout` | never installed — a deliberate removal stays removed |

The opt-out file matters: "install anything absent" would otherwise resurrect a rule the team
deliberately deleted, on every single update. One path per line; `#` comments allowed. A
single-tenant project dropping the vector-store rule writes `best-practices/tenant-isolation.yaml`.

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

## Step 5 — Confirm

Output this exactly:

---
**HITL plugin updated to v\<new-version\>.**

**Restart Claude Code now** to load the new skills and hooks.
