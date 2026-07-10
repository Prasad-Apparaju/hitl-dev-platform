#!/usr/bin/env bash
# ci/breadcrumb/run_matrix.sh — breadcrumb test matrix.
#
# Verifies that the HITL breadcrumb renderers show the correct status for every runtime
# workflow and a representative set of step states. Implements the stated success criterion
# in docs/design/workflow-model/00-requirements.md §6 and 02-rollout.md §6:
#   "Every workflow ... is verified to actually run end to end, and the breadcrumb shows the
#    correct status ... proven by exercising the renderers, not by reading the catalog."
#
# What it does, per case:
#   1. builds an isolated temp dir with its own .hitl/ and (where branch matters) its own git repo
#   2. seeds .hitl/current-change.yaml from ai/shared/workflows.yaml for the chosen workflow + state,
#      copying each step's phase (additive) and populating current_step.name with the FULL step name
#   3. runs the real renderers (welcome.sh banner + statusline-hitl.sh) AND the _steps.sh library
#   4. asserts the rendered Phase-2 breadcrumb concretely — non-empty where expected, the current
#      step is highlighted (▶ + FULL name), the phase ribbon shows the right glyph per phase
#      (✓ done / ◐ current / · untouched), NO global "Step N / total" counter leaks, and no
#      error text leaks. Exits non-zero if ANY case fails.
#
# It seeds step lists FROM the catalog (not hand-copied), so the matrix tracks the catalog and
# tests the renderers — it does not re-encode the step model.
#
# Usage:  ci/breadcrumb/run_matrix.sh            # run the whole matrix
#         ci/breadcrumb/run_matrix.sh -v         # verbose: print each rendered trail
#
# Does NOT modify the renderers or any other repo file; does NOT commit.

set -u

# ── locate repo + renderers ────────────────────────────────────────────────────────────────────
CI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$CI_DIR/../.." && pwd)"
HOOKS="$REPO_ROOT/ai/claude/hooks"
STEPS_LIB="$HOOKS/_steps.sh"
WELCOME="$HOOKS/welcome.sh"
STATUSLINE="$HOOKS/statusline-hitl.sh"
WORKFLOWS="$REPO_ROOT/ai/shared/workflows.yaml"
STEPDOC="$REPO_ROOT/ai/claude/dev-practices/workflow-steps.md"   # full step names (development)

VERBOSE=0
[[ "${1:-}" == "-v" ]] && VERBOSE=1

for f in "$STEPS_LIB" "$WELCOME" "$STATUSLINE" "$WORKFLOWS"; do
  [[ -f "$f" ]] || { echo "FATAL: missing required file: $f" >&2; exit 2; }
done

# shellcheck source=/dev/null
source "$STEPS_LIB"

PY="$(hitl_python)" || { echo "FATAL: no working python interpreter for fixture generation" >&2; exit 2; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/bc_matrix.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
FINDINGS=()
declare -a FAILED_CASES

# ── fixture generation ──────────────────────────────────────────────────────────────────────────
# emit_change_yaml <workflow_id> <current_n> [skip_n] [expected_branch]
#   Reads the workflow's step list from workflows.yaml, marks every step before <current_n> done,
#   the <current_n> step current, the rest open, and (if given) <skip_n> as skipped. Emits a full
#   schema-v2 change file (flow-map style) on stdout. <current_n> may be a substep like "19a".
emit_change_yaml() {
  WF="$1" CUR="$2" SKIP="${3:-}" EB="${4:-}" STEPDOC="$STEPDOC" "$PY" - "$WORKFLOWS" <<'PY'
import sys, re, os
wf_file = sys.argv[1]
wf_id  = os.environ["WF"]
cur    = os.environ["CUR"]
skip   = os.environ.get("SKIP","")
eb     = os.environ.get("EB","")
style  = os.environ.get("STYLE","flow")   # "flow" (single-line maps) or "block" (multi-line)
nophase= os.environ.get("NOPHASE","")     # "1" → omit per-step phase (back-compat fixture)
stepdoc= os.environ.get("STEPDOC","")     # workflow-steps.md, for FULL step names (development)

# Full step names live in workflow-steps.md as "**<n>. <Full Name>** …" headings. That doc covers
# ONLY the development workflow, so it is consulted ONLY for development; every other workflow falls
# back to its short catalog label. current_step.name is the FULL name (the Phase-2 trail expands it).
fullnames = {}
if wf_id == "development" and stepdoc and os.path.exists(stepdoc):
    for ln in open(stepdoc).read().splitlines():
        m = re.match(r'^\*\*(\d+[a-z]?)\.\s+(.+?)\*\*', ln)
        if m:
            nm = m.group(2)
            nm = re.sub(r'\s*\(conditional\)\s*$', '', nm).strip()
            fullnames[m.group(1)] = nm

# Minimal dependency-free parse of ai/shared/workflows.yaml (flow-map step entries).
import io
lines = open(wf_file).read().splitlines()
# find the block for wf_id under "workflows:"
steps, total, title = [], None, None
in_workflows = False
cur_wf = None
for ln in lines:
    if re.match(r'^workflows:\s*$', ln): in_workflows = True; continue
    if not in_workflows: continue
    m = re.match(r'^  (\w+):\s*$', ln)
    if m:
        cur_wf = m.group(1); continue
    if cur_wf != wf_id: continue
    mt = re.match(r'^\s*total:\s*(\d+)', ln)
    if mt: total = int(mt.group(1)); continue
    ms = re.match(r'^\s*-\s*\{(.*)\}\s*$', ln)
    if ms:
        body = ms.group(1)
        def field(k):
            mm = re.search(k + r':\s*("([^"]*)"|[^,}]+)', body)
            if not mm: return ""
            return (mm.group(2) if mm.group(2) is not None else mm.group(1)).strip().strip('"')
        steps.append({"n": field("n"), "key": field("key"), "label": field("label"), "phase": field("phase")})

if not steps:
    sys.stderr.write("could not parse steps for workflow %r\n" % wf_id)
    sys.exit(3)

# integer index order for "before/after" comparison; substeps sort just after their parent int
def order(n):
    m = re.match(r'^(\d+)([a-z]*)$', n)
    base = int(m.group(1))
    return (base, m.group(2))

cur_ord = order(cur)
out = []
out.append('schema_version: "2.0"')
out.append('hitl_version: "1.0.28"')
out.append('change_id: GH-000')
out.append('tier: 2')
out.append('status: implementation-approved')
if eb:
    out.append('expected_branch: "%s"' % eb)
out.append('workflow:')
out.append('  id: %s' % wf_id)
out.append('  version: "1.0.28"')
if total is not None:
    out.append('  total: %d' % total)
out.append('  steps:')
cur_label = None
cur_phase = None
cur_int = None
cur_sub = ""
for s in steps:
    n = s["n"]
    if n == cur:
        st = "current"; cur_label = s["label"]; cur_phase = s["phase"]
        mm = re.match(r'^(\d+)([a-z]*)$', n)
        cur_int = mm.group(1); cur_sub = mm.group(2)
    elif skip and n == skip:
        st = "skipped"
    elif order(n) < cur_ord:
        st = "done"
    else:
        st = "open"
    ph = s["phase"]
    if style == "block":
        out.append('    - n: %s' % n)
        out.append('      key: %s' % s["key"])
        out.append('      label: "%s"' % s["label"])
        out.append('      status: %s' % st)
        if ph and not nophase:
            out.append('      phase: "%s"' % ph)
    else:
        if ph and not nophase:
            out.append('    - { n: %s, key: %s, label: "%s", status: %s, phase: "%s" }' % (n, s["key"], s["label"], st, ph))
        else:
            out.append('    - { n: %s, key: %s, label: "%s", status: %s }' % (n, s["key"], s["label"], st))
# current_step.name is the FULL step name (the Phase-2 trail expands it); fall back to short label.
cur_name = fullnames.get(cur, cur_label or "")
out.append('current_step:')
out.append('  number: %s' % (cur_int or "1"))
if cur_sub:
    out.append('  substep: "%s"' % cur_sub)
out.append('  name: "%s"' % cur_name)
if cur_phase:
    out.append('  phase: "%s"' % cur_phase)
print("\n".join(out))
PY
}

# emit_block_style <workflow_id> <current_n>
#   Same as emit_change_yaml but renders steps[] in multi-line BLOCK style (issue #15 path).
#   Delegates to emit_change_yaml with STYLE=block — a single python invocation, so there is no
#   stdin/heredoc conflict to corrupt the fixture.
emit_block_style() {
  STYLE=block emit_change_yaml "$1" "$2"
}

# ── per-case scaffolding ────────────────────────────────────────────────────────────────────────
# new_case_dir <name> <branch>  → makes $WORK/<name>/.hitl, inits a git repo on <branch>, echoes dir
new_case_dir() {
  local name="$1" branch="$2" d="$WORK/$1"
  mkdir -p "$d/.hitl"
  ( cd "$d" && git init -q . && git config user.email t@t && git config user.name t \
      && git checkout -q -b "$branch" ) 2>/dev/null
  echo "$d"
}

# run_welcome <dir>  — stdout of the banner renderer (no leaking stderr into asserts)
run_welcome() { ( cd "$1" && bash "$WELCOME" 2>/tmp/_bc_welcome_err ); }

# run_statusline <dir> <branch>
run_statusline() {
  printf '{"cwd":"%s","model":{"display_name":"Opus"},"context_window":{"used_percentage":42}}' "$1" \
    | CLAUDE_PROJECT_DIR="$1" bash "$STATUSLINE" 2>/tmp/_bc_status_err
}

# ── assertion helpers ───────────────────────────────────────────────────────────────────────────
# Each records pass/fail and prints a one-line result.
_ok()   { PASS=$((PASS+1)); printf '  PASS  %s\n' "$1"; }
_bad()  { FAIL=$((FAIL+1)); FAILED_CASES+=("$1"); printf '  FAIL  %s\n' "$1"; }

assert_contains() { # <label> <haystack> <needle>
  if printf '%s' "$2" | grep -qF -- "$3"; then _ok "$1 — contains '$3'"; else
    _bad "$1 — MISSING '$3'"; [[ $VERBOSE -eq 1 ]] && printf '        got: %q\n' "$2"; fi
}
assert_not_contains() { # <label> <haystack> <needle>
  if printf '%s' "$2" | grep -qF -- "$3"; then
    _bad "$1 — UNEXPECTEDLY contains '$3'"; else _ok "$1 — free of '$3'"; fi
}
assert_not_matches() { # <label> <haystack> <ERE>
  if printf '%s' "$2" | grep -qE -- "$3"; then
    _bad "$1 — UNEXPECTEDLY matches /$3/"; [[ $VERBOSE -eq 1 ]] && printf '        got: %q\n' "$2"
  else _ok "$1 — free of /$3/"; fi
}
# no global "Step N / total" counter may leak anywhere in Phase 2 (the trail is numberless and
# the denominator was replaced by the phase ribbon).
assert_no_global_counter() { # <label> <combined output>
  assert_not_matches "$1: no 'Step N / ' counter"  "$2" 'Step [0-9]+ / '
  assert_not_matches "$1: no 'Step N/M' counter"   "$2" 'Step [0-9]+/[0-9]'
}
assert_nonempty() { # <label> <value>
  if [[ -n "${2//[[:space:]]/}" ]]; then _ok "$1 — non-empty"; else _bad "$1 — EMPTY"; fi
}
# no error text leaked: renderers must not emit awk/python/jq stack noise or "error"
assert_no_error_leak() { # <label> <combined output>
  local bad=0
  printf '%s' "$2" | grep -qiE 'traceback|awk:|syntax error|command not found|unexpected token|jq: error|parse error' && bad=1
  if [[ $bad -eq 0 ]]; then _ok "$1 — no renderer error text leaked"; else _bad "$1 — ERROR TEXT LEAKED"; fi
}

# ── matrix definition ───────────────────────────────────────────────────────────────────────────
# For each workflow we need: id, the first step n, a middle step n, the last step n. Derive from
# the catalog so we don't hardcode them.
catalog_field() { # <wf_id> <first|middle|last|label_of:N|phase_of:N|name_of:N>
  WF="$1" Q="$2" STEPDOC="$STEPDOC" "$PY" - "$WORKFLOWS" <<'PY'
import sys, re, os
wf_file=sys.argv[1]; wf_id=os.environ["WF"]; q=os.environ["Q"]
stepdoc=os.environ.get("STEPDOC","")
lines=open(wf_file).read().splitlines()
in_w=False; cur=None; ns=[]; labels={}; phases={}
for ln in lines:
    if re.match(r'^workflows:\s*$', ln): in_w=True; continue
    if not in_w: continue
    m=re.match(r'^  (\w+):\s*$', ln)
    if m: cur=m.group(1); continue
    if cur!=wf_id: continue
    ms=re.match(r'^\s*-\s*\{(.*)\}\s*$', ln)
    if ms:
        body=ms.group(1)
        nn=re.search(r'n:\s*([^,}]+)', body).group(1).strip()
        ns.append(nn)
        lm=re.search(r'label:\s*"([^"]*)"', body)
        labels[nn]=lm.group(1) if lm else ""
        pm=re.search(r'phase:\s*"([^"]*)"', body)
        phases[nn]=pm.group(1) if pm else ""
# full step names from workflow-steps.md — development ONLY; others fall back to the short label
fullnames={}
if wf_id == "development" and stepdoc and os.path.exists(stepdoc):
    for ln in open(stepdoc).read().splitlines():
        mm=re.match(r'^\*\*(\d+[a-z]?)\.\s+(.+?)\*\*', ln)
        if mm:
            nm=re.sub(r'\s*\(conditional\)\s*$','',mm.group(2)).strip()
            fullnames[mm.group(1)]=nm
ints=[n for n in ns if re.match(r'^\d+$', n)]
if q=="first": print(ints[0])
elif q=="last": print(ints[-1])
elif q=="middle": print(ints[len(ints)//2])
elif q.startswith("label_of:"): print(labels.get(q.split(":",1)[1], ""))
elif q.startswith("phase_of:"): print(phases.get(q.split(":",1)[1], ""))
elif q.startswith("name_of:"):
    k=q.split(":",1)[1]; print(fullnames.get(k, labels.get(k, "")))
PY
}

WORKFLOWS_LIST=(development brownfield migration migration_review prd docs)

echo "================================================================"
echo " HITL breadcrumb test matrix"
echo " renderers: $WELCOME"
echo "            $STATUSLINE"
echo " catalog:   $WORKFLOWS"
echo "================================================================"

# helper to run one standard position case (first/middle/last)
run_position_case() {
  local wf="$1" pos="$2" n full phase first_phase dir banner status combined
  n="$(catalog_field "$wf" "$pos")"
  [[ -z "$n" ]] && { _bad "$wf/$pos — could not derive step n from catalog"; return; }
  full="$(catalog_field "$wf" "name_of:$n")"        # FULL current step name (trail expands it)
  phase="$(catalog_field "$wf" "phase_of:$n")"      # current step's phase (ribbon shows it ◐)
  first_phase="$(catalog_field "$wf" "phase_of:$(catalog_field "$wf" first)")"
  dir="$(new_case_dir "${wf}_${pos}" "issue/000-x")"
  emit_change_yaml "$wf" "$n" "" "issue/000-x" > "$dir/.hitl/current-change.yaml"
  banner="$(run_welcome "$dir")"
  status="$(run_statusline "$dir")"
  combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
  [[ $VERBOSE -eq 1 ]] && { echo "    --- $wf/$pos (step $n='$full', phase '$phase') ---"; echo "$banner" | sed 's/^/    /'; }

  local lib_trail lib_ribbon
  lib_trail="$(cd "$dir" && hitl_render_trail .hitl/current-change.yaml "" "$full")"
  lib_ribbon="$(cd "$dir" && hitl_render_ribbon .hitl/current-change.yaml)"
  # ── trail: current step is "▶ <FULL name>" (numberless, no "▶<n>.<label>") ──
  assert_nonempty   "$wf/$pos: library trail"            "$lib_trail"
  assert_contains   "$wf/$pos: library trail current ▶"  "$lib_trail" "▶ ${full}"
  assert_nonempty   "$wf/$pos: banner"                   "$banner"
  assert_contains   "$wf/$pos: banner shows current ▶"   "$banner" "▶ ${full}"
  assert_contains   "$wf/$pos: statusline shows current" "$status" "▶ ${full}"
  # ── phase ribbon: current step's phase shows ◐ ──
  assert_contains   "$wf/$pos: library ribbon current phase ◐" "$lib_ribbon" "${phase} ◐"
  assert_contains   "$wf/$pos: banner shows phase ribbon"      "$banner" "${phase} ◐"
  # ── for middle/last the first phase is fully behind us → it shows ✓ ──
  if [[ "$pos" != "first" && "$first_phase" != "$phase" ]]; then
    assert_contains "$wf/$pos: earlier phase ✓"           "$banner" "${first_phase} ✓"
  fi
  # ── no global "Step N / total" counter survives Phase 2, anywhere ──
  assert_no_global_counter "$wf/$pos"                    "$combined"
  assert_no_error_leak     "$wf/$pos"                    "$combined"
}

# ── 1. FIRST / MIDDLE / LAST for every workflow ─────────────────────────────────────────────────
for wf in "${WORKFLOWS_LIST[@]}"; do
  echo "── workflow: $wf ──────────────────────────────────────────────"
  run_position_case "$wf" first
  run_position_case "$wf" middle
  run_position_case "$wf" last
done

# ── 2. development 19a SUBSTEP ───────────────────────────────────────────────────────────────────
echo "── case: development 19a substep ─────────────────────────────"
dir="$(new_case_dir "dev_19a" "issue/000-x")"
emit_change_yaml development 19a "" "issue/000-x" > "$dir/.hitl/current-change.yaml"
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
lib_trail="$(cd "$dir" && hitl_render_trail .hitl/current-change.yaml "" "Architect Code Review")"
cur_n="$(cd "$dir" && hitl_current_n .hitl/current-change.yaml)"
assert_contains   "dev/19a: current_n is the substep" "$cur_n" "19a"
# Phase 2: the current step is shown by its FULL name, numberless — "▶ Architect Code Review".
assert_contains   "dev/19a: library trail shows ▶ Architect Code Review" "$lib_trail" "▶ Architect Code Review"
assert_contains   "dev/19a: banner shows ▶ Architect Code Review"        "$banner" "▶ Architect Code Review"
assert_contains   "dev/19a: statusline shows ▶ Architect Code Review"    "$status" "▶ Architect Code Review"
# 19a lives in the Verify phase → ribbon shows "Verify ◐"
assert_contains   "dev/19a: ribbon shows Verify ◐"                       "$banner" "Verify ◐"
assert_no_global_counter "dev/19a"                                       "$combined"
assert_no_error_leak     "dev/19a"                                       "$combined"

# ── 3. SKIPPED step present in the trail (in the visible window) ─────────────────────────────────
echo "── case: skipped step in trail ───────────────────────────────"
# current at step 5 (Docs); mark step 3 (Impact) skipped — 3 is within the 3-back window of 5.
dir="$(new_case_dir "dev_skip" "issue/000-x")"
emit_change_yaml development 5 3 "issue/000-x" > "$dir/.hitl/current-change.yaml"
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
lib_steps="$(cd "$dir" && hitl_steps .hitl/current-change.yaml)"
lib_trail="$(cd "$dir" && hitl_render_trail .hitl/current-change.yaml "" "Update Docs")"
# hitl_steps now emits n|label|status|phase — skipped status is preserved (phase appended).
assert_contains   "dev/skip: steps parse keeps skipped status" "$lib_steps" "3|Impact|skipped|Design"
assert_nonempty   "dev/skip: trail non-empty"                  "$lib_trail"
# current step is shown numberless by its FULL name.
assert_contains   "dev/skip: current still highlighted ▶ Update Docs" "$lib_trail" "▶ Update Docs"
# a skipped step renders with the open glyph "·" (renderer maps only done/current specially),
# and crucially is NOT shown as done (✓) — assert it appears as ·Impact (numberless), never ✓Impact.
assert_contains   "dev/skip: skipped step shown as ·Impact"    "$lib_trail" "·Impact"
assert_not_contains "dev/skip: skipped step not marked done"   "$lib_trail" "✓Impact"
assert_no_global_counter "dev/skip"                            "$combined"
assert_no_error_leak     "dev/skip"                            "$combined"

# ── 4. BRANCH MISMATCH soft-warning marker (must warn, must not crash) ───────────────────────────
echo "── case: branch mismatch warning ─────────────────────────────"
dir="$(new_case_dir "dev_mismatch" "totally-wrong-branch")"
emit_change_yaml development 10 "" "issue/000-refund-flow" > "$dir/.hitl/current-change.yaml"
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
recon="$(cd "$dir" && hitl_branch_reconcile .hitl/current-change.yaml totally-wrong-branch)"
assert_contains   "dev/mismatch: reconcile = mismatch"   "$recon" "mismatch"
assert_contains   "dev/mismatch: banner warning marker ⚠" "$banner" "⚠"
assert_contains   "dev/mismatch: banner names the branch" "$banner" "totally-wrong-branch"
assert_contains   "dev/mismatch: statusline warning ⚠"    "$status" "⚠"
# even with a mismatch, the trail must still render (warn, not crash) — step 10's FULL name.
assert_contains   "dev/mismatch: trail still rendered"    "$banner" "▶ AI Generates Tests (RED)"
assert_no_global_counter "dev/mismatch"                   "$combined"
assert_no_error_leak     "dev/mismatch"                   "$combined"

# ── 5. BLOCK-style YAML must parse identically to flow-style (issue #15) ─────────────────────────
echo "── case: block-style YAML parse (issue #15) ──────────────────"
dir="$(new_case_dir "dev_block" "issue/000-x")"
emit_block_style development 14 > "$dir/.hitl/current-change.yaml"
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
block_trail="$(cd "$dir" && hitl_render_trail .hitl/current-change.yaml "" "Generate Code (GREEN)")"
block_ribbon="$(cd "$dir" && hitl_render_ribbon .hitl/current-change.yaml)"
# compare against the flow-style equivalent (rendered the same way)
dir2="$(new_case_dir "dev_flow_ref" "issue/000-x")"
emit_change_yaml development 14 "" "issue/000-x" > "$dir2/.hitl/current-change.yaml"
flow_trail="$(cd "$dir2" && hitl_render_trail .hitl/current-change.yaml "" "Generate Code (GREEN)")"
flow_ribbon="$(cd "$dir2" && hitl_render_ribbon .hitl/current-change.yaml)"
assert_nonempty   "dev/block: block trail non-empty"            "$block_trail"
# current shown numberless by FULL name; step 14 is in the Build phase → ribbon "Build ◐".
assert_contains   "dev/block: block trail current ▶ Generate Code (GREEN)" "$block_trail" "▶ Generate Code (GREEN)"
assert_contains   "dev/block: block ribbon Build ◐"            "$block_ribbon" "Build ◐"
assert_contains   "dev/block: banner renders from block YAML"  "$banner" "▶ Generate Code (GREEN)"
if [[ "$block_trail" == "$flow_trail" ]]; then _ok "dev/block: block trail == flow trail"; else
  _bad "dev/block: block trail DIFFERS from flow trail"
  [[ $VERBOSE -eq 1 ]] && { echo "        block: $block_trail"; echo "        flow:  $flow_trail"; }
fi
if [[ "$block_ribbon" == "$flow_ribbon" ]]; then _ok "dev/block: block ribbon == flow ribbon"; else
  _bad "dev/block: block ribbon DIFFERS from flow ribbon"
  [[ $VERBOSE -eq 1 ]] && { echo "        block: $block_ribbon"; echo "        flow:  $flow_ribbon"; }
fi
assert_no_global_counter "dev/block"                          "$combined"
assert_no_error_leak     "dev/block"                          "$combined"

# ── 5b. BACK-COMPAT: steps carry NO per-step phase → ribbon falls back to current_step.phase ─────
# A change file written before per-step `phase` existed has a workflow block + steps, but none of
# the steps carry a `phase`. hitl_render_ribbon must then fall back to the lone current_step.phase
# ("<phase> ◐"), and the banner must still render the full trail without crashing.
echo "── case: back-compat — steps without per-step phase ──────────"
dir="$(new_case_dir "dev_nophase" "issue/000-x")"
NOPHASE=1 emit_change_yaml development 14 "" "issue/000-x" > "$dir/.hitl/current-change.yaml"
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
np_steps="$(cd "$dir" && hitl_steps .hitl/current-change.yaml)"
np_ribbon="$(cd "$dir" && hitl_render_ribbon .hitl/current-change.yaml)"
np_trail="$(cd "$dir" && hitl_render_trail .hitl/current-change.yaml "" "Generate Code (GREEN)")"
# precondition: the seeded steps really have an EMPTY phase column (n|label|status|<empty>).
assert_contains    "dev/nophase: steps carry no per-step phase" "$np_steps" "14|GREEN|current|"
assert_not_contains "dev/nophase: no per-step Build phase"      "$np_steps" "14|GREEN|current|Build"
# fallback: ribbon collapses to the single current_step.phase glyph "Build ◐" (not a full ribbon).
assert_contains    "dev/nophase: ribbon falls back to Build ◐"  "$np_ribbon" "Build ◐"
assert_not_contains "dev/nophase: ribbon is NOT the full ribbon" "$np_ribbon" "Requirements ✓"
# the banner still renders the full named trail, no crash.
assert_nonempty    "dev/nophase: banner still renders"          "$banner"
assert_contains    "dev/nophase: banner shows Build ◐ fallback" "$banner" "Build ◐"
assert_contains    "dev/nophase: trail current ▶ Generate Code (GREEN)" "$np_trail" "▶ Generate Code (GREEN)"
assert_no_global_counter "dev/nophase"                          "$combined"
assert_no_error_leak     "dev/nophase"                          "$combined"

# ── 6. ZERO-STEPS / MISSING-WORKFLOW must degrade, not crash ─────────────────────────────────────
echo "── case: missing-workflow (pre-v2 file) degrades ─────────────"
dir="$(new_case_dir "degrade_prev2" "some-branch")"
cat > "$dir/.hitl/current-change.yaml" <<'YML'
schema_version: "1.0"
change_id: GH-555
tier: 1
status: planning
current_step:
  number: 3
  name: "Impact Analysis"
  phase: "Design"
YML
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"; rc_banner=0
( cd "$dir" && bash "$WELCOME" >/dev/null 2>&1 ) || rc_banner=$?
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
assert_contains    "degrade/prev2: banner exits cleanly"     "$rc_banner" "0"
assert_nonempty    "degrade/prev2: banner still prints"      "$banner"
assert_contains    "degrade/prev2: shows migrate hint"       "$banner" "step trail unavailable"
assert_contains    "degrade/prev2: statusline migrate hint"  "$status" "dev-update"
assert_no_error_leak "degrade/prev2"                         "$combined"

echo "── case: completely missing change file degrades ─────────────"
dir="$(new_case_dir "degrade_nofile" "nf-branch")"   # .hitl/ exists, no current-change.yaml
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"; rc_banner=0
( cd "$dir" && bash "$WELCOME" >/dev/null 2>&1 ) || rc_banner=$?
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
assert_contains    "degrade/nofile: banner exits cleanly"        "$rc_banner" "0"
assert_contains    "degrade/nofile: banner shows intake gate"    "$banner" "NO ACTIVE CHANGE"
assert_contains    "degrade/nofile: statusline no-active-change" "$status" "no active change"
assert_no_error_leak "degrade/nofile"                            "$combined"

echo "── case: a merged change is inactive (issue #19 stale-file gate) ──"
# A valid workflow block that has been marked merged must NOT keep satisfying the
# session gate — the next change has to go through intake, not inherit the old one.
dir="$(new_case_dir "merged_inactive" "issue/000-x")"
# conclude sets the top-level status to merged (replacing the working status)
emit_change_yaml development 14 "" "issue/000-x" | sed 's/^status: .*/status: merged/' > "$dir/.hitl/current-change.yaml"
banner="$(run_welcome "$dir")"; status="$(run_statusline "$dir")"
combined="$banner"$'\n'"$status"$'\n'"$(cat /tmp/_bc_welcome_err /tmp/_bc_status_err 2>/dev/null)"
[[ $VERBOSE -eq 1 ]] && echo "$banner" | sed 's/^/    /'
assert_contains    "merged/inactive: banner forces intake"       "$banner" "NO ACTIVE CHANGE"
assert_contains    "merged/inactive: statusline no-active-change" "$status" "no active change"
assert_not_contains "merged/inactive: no stale trail"            "$banner" "▶ Generate Code"
assert_no_error_leak "merged/inactive"                           "$combined"

# ── summary ─────────────────────────────────────────────────────────────────────────────────────
echo "================================================================"
echo " RESULT: $PASS passed, $FAIL failed (of $((PASS+FAIL)) assertions)"
if [[ $FAIL -gt 0 ]]; then
  echo " FAILED assertions:"
  for c in "${FAILED_CASES[@]}"; do echo "   - $c"; done
fi
echo "================================================================"
[[ $FAIL -eq 0 ]]
