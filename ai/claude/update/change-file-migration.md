# Change-file migration — the Step 4.5 procedure

Split out of `dev-update`'s SKILL.md to keep its body under the 500-line skill limit; the
lint README's guidance is to split a section out rather than trim prose to fit. Referenced
from **Step 4.5 — Migrate the change file to the current workflow schema**.

## Contents

| Stage | What it does |
|---|---|
| Preconditions | What the migration guarantees, and its one format limitation |
| Resolve Python | Windows-safe interpreter probe (issue #14) |
| 1. Resolve status | Remap completion by stable `key`, so renumbering never loses progress |
| 2. Enforce one `current` | Repairs both zero-current and duplicate-current (issue #22) |
| 3. Emit step lines | One flow map per step, carrying project-authored keys across |
| 4. Surgical splice | Rewrite step lines in place; comments and blank lines stay verbatim |
| 5. Version stamps | Upsert `schema_version` / `workflow.version` |
| Diff and confirm | Print the unified diff, then apply **only** on explicit confirmation |


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
