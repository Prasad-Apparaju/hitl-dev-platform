#!/usr/bin/env bash
# _steps.sh — shared HITL breadcrumb parser. Sourced by welcome.sh and statusline-hitl.sh.
#
# This is the ONLY place that knows how to read the self-describing `workflow` block embedded
# in .hitl/current-change.yaml. Both renderers source this file so the banner and the status
# line can never drift on step count or labels (the four-way drift that motivated this design).
#
# It is intentionally dependency-free (awk only — no jq/yq/python). It relies on the embedded
# steps being written as single-line YAML flow maps, exactly as the schema and the start-skills
# produce them:
#
#   workflow:
#     id: development
#     version: "1.0.28"
#     total: 31
#     steps:
#       - { n: 1,   key: issue,       label: "Issue",   status: done }
#       - { n: 19a, key: arch_review, label: "ArchRvw", status: current }
#       - { n: 20,  key: rerun,       label: "Rerun",   status: open }
#
# Status values: done (✓) · current (▶) · open (·).

# hitl_python → echo the first working Python interpreter, or return 1 if none (issue #14).
# On Windows, `python3` is usually the Microsoft Store stub: it's on PATH but exits non-zero and
# runs nothing, so a hard-coded `python3` makes every hook silently no-op. The `import sys` smoke
# test rejects the stub. Prefers $HITL_PY (set by the wrapper) to avoid re-probing per call.
hitl_python() {
  if [[ -n "${HITL_PY:-}" ]] && command -v "$HITL_PY" >/dev/null 2>&1; then echo "$HITL_PY"; return 0; fi
  local c
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys" >/dev/null 2>&1; then echo "$c"; return 0; fi
  done
  return 1
}

# hitl_has_workflow <yaml> → exit 0 if the file has an embedded `workflow:` block with steps.
hitl_has_workflow() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  awk '/^workflow:/{w=1} w && /^[ ]+steps:/{print "yes"; exit}' "$f" | grep -q yes
}

# hitl_workflow_field <yaml> <field> → echo a scalar field (id|version|total|title) from the
# workflow block. Reads only the indented lines inside `workflow:` (before `steps:`).
hitl_workflow_field() {
  local f="$1" field="$2"
  awk -v key="$field" '
    /^workflow:/        { w=1; next }
    w && /^[^ ]/        { exit }                       # left the workflow block
    w && /^[ ]+steps:/  { exit }                       # stop at the steps list
    w {
      line=$0
      if (line ~ "^[ ]+" key ":") {
        sub("^[ ]+" key ":[ ]*", "", line)
        gsub(/^"|"$/, "", line)                        # strip surrounding quotes
        sub(/[ ]+#.*/, "", line)                       # strip trailing comment
        gsub(/[ ]+$/, "", line)
        print line; exit
      }
    }
  ' "$f"
}

# hitl_steps <yaml> → emit one line per step as: n|label|status
# Order is preserved. Substeps (e.g. 19a) come through as their literal n.
hitl_steps() {
  local f="$1"
  # Handles BOTH single-line flow maps ("- { n: 1, key: …, status: done }") and
  # multi-line block style ("- n: 1\n  key: …\n  status: done"). Both are valid YAML; the
  # writer emits flow style, but anything that hand-edits the file (incl. an agent flipping
  # statuses) may emit block style — the breadcrumb must render either (issue #15).
  awk '
    function field(t, key,   v) {        # extract `key:`-value from a block line, unquoted
      v=t; sub("^[ ]*" key ":[ ]*","",v); sub(/[ ]+#.*/,"",v); sub(/[ ]*$/,"",v)
      gsub(/^"|"$/,"",v); gsub(/^'"'"'|'"'"'$/,"",v); return v
    }
    function flush() { if (have) { if (st=="") st="open"; print n "|" lbl "|" st } have=0; n=""; lbl=""; st="" }
    /^workflow:/        { w=1; next }
    w && /^[ ]+steps:/  { s=1; next }
    s {
      line=$0
      if (line ~ /^[^ ]/)            { flush(); exit }          # next top-level key ends steps
      if (line ~ /^[ ]+- *\{/) {                                 # ── flow style (self-contained)
        flush()
        n=line;   sub(/.*[{,][ ]*n:[ ]*/,    "", n);   sub(/[ ]*[,}].*/, "", n);   gsub(/["{} ]/,"",n)
        lbl=line; sub(/.*[,{][ ]*label:[ ]*/, "", lbl); sub(/[ ]*[,}].*/, "", lbl); gsub(/^"|"$/,"",lbl)
        st=line;  sub(/.*[,{][ ]*status:[ ]*/, "", st); sub(/[ ]*[,}].*/, "", st); gsub(/["{} ]/,"",st)
        if (st=="") st="open"
        print n "|" lbl "|" st; have=0; next
      }
      if (line ~ /^[ ]+-[ ]/) {                                  # ── block style: new list item
        flush(); have=1
        rest=line; sub(/^[ ]+-[ ]*/,"",rest)                     # may carry an inline field, e.g. "- n: 1"
        if (rest ~ /^n:/)      n=field(rest,"n")
        else if (rest ~ /^key:/) {}                              # key unused for rendering
        else if (rest ~ /^label:/)  lbl=field(rest,"label")
        else if (rest ~ /^status:/) st=field(rest,"status")
        next
      }
      if (have && line ~ /^[ ]+[A-Za-z_]+:/) {                   # ── block style: continuation field
        if (line ~ /^[ ]+n:/)        n=field(line,"n")
        else if (line ~ /^[ ]+label:/)  lbl=field(line,"label")
        else if (line ~ /^[ ]+status:/) st=field(line,"status")
        next
      }
    }
    END { flush() }
  ' "$f"
}

# hitl_total <yaml> → the breadcrumb denominator (workflow.total, or count of integer steps).
hitl_total() {
  local f="$1" t
  t=$(hitl_workflow_field "$f" total)
  if [[ -n "$t" && "$t" =~ ^[0-9]+$ ]]; then echo "$t"; return; fi
  hitl_steps "$f" | awk -F'|' '$1 ~ /^[0-9]+$/ {n=$1} END{print n+0}'
}

# hitl_current_n <yaml> → the `n` of the step whose status is `current` (e.g. "3" or "19a").
hitl_current_n() {
  hitl_steps "$1" | awk -F'|' '$3=="current"{print $1; exit}'
}

# hitl_current_label <yaml> → the label of the current step.
hitl_current_label() {
  hitl_steps "$1" | awk -F'|' '$3=="current"{print $2; exit}'
}

# hitl_cs_field <yaml> <name|phase|number> → read a field from the current_step block.
# Tolerant of block style ("current_step:\n  name: …") AND flow style
# ("current_step: { name: …, phase: … }"), and of quoted OR unquoted values (issue #15).
hitl_cs_field() {
  awk -v key="$2" '
    /^current_step:/ {
      if ($0 ~ /^current_step:[ ]*\{/) {                     # flow style on one line
        line=$0
        if (match(line, key ":[ ]*\"[^\"]*\"")) { v=substr(line,RSTART,RLENGTH); sub(key ":[ ]*\"","",v); sub(/"$/,"",v); print v; exit }
        if (match(line, key ":[ ]*[^,}]+"))     { v=substr(line,RSTART,RLENGTH); sub(key ":[ ]*","",v); sub(/[ ]+$/,"",v); gsub(/^"|"$/,"",v); print v; exit }
        exit
      }
      f=1; next                                              # block style follows
    }
    f && /^[^ ]/ { exit }                                    # left the current_step block
    f && $0 ~ "^[ ]+" key ":" {
      v=$0; sub("^[ ]+" key ":[ ]*","",v); sub(/[ ]+#.*/,"",v); sub(/[ ]*$/,"",v); gsub(/^"|"$/,"",v); print v; exit
    }
  ' "$1"
}

# ── Change-activation + branch reconciliation (issue #12) ─────────────────────────────────────

# hitl_change_active <yaml> → exit 0 if a change is active (file has current_step or workflow).
hitl_change_active() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  grep -q "^current_step:" "$f" 2>/dev/null || hitl_has_workflow "$f"
}

# hitl_scalar <yaml> <field> → top-level scalar (e.g. change_id, expected_branch, tier).
hitl_scalar() {
  awk -v k="$2" '$0 ~ "^" k ":" { sub("^" k ":[ ]*","",$0); gsub(/^"|"$/,"",$0); print; exit }' "$1"
}

# hitl_branch_reconcile <yaml> <current_branch> → echoes one of:
#   noactive       — no change is active
#   match          — branch agrees with the active change
#   unverifiable    — non-issue/* branch with no expected_branch to check against (soft)
#   mismatch       — branch disagrees with the active change (hard)
# Rules: prefer an explicit `expected_branch`; else derive the issue number from `issue/N-*`
# and compare to change_id's number; else treat as unverifiable (don't nag deliberate branches).
hitl_branch_reconcile() {
  local f="$1" branch="$2" expected change_id branch_issue yaml_issue
  hitl_change_active "$f" || { echo "noactive"; return; }
  expected=$(hitl_scalar "$f" expected_branch)
  if [[ -n "$expected" ]]; then
    [[ "$branch" == "$expected" ]] && echo "match" || echo "mismatch"
    return
  fi
  branch_issue=$(echo "$branch" | sed -n 's|issue/\([0-9][0-9]*\)-.*|\1|p')
  if [[ -n "$branch_issue" ]]; then
    change_id=$(hitl_scalar "$f" change_id)
    yaml_issue=$(echo "$change_id" | sed -n 's|.*[^0-9]\([0-9][0-9]*\)$|\1|p')
    [[ -n "$yaml_issue" && "$branch_issue" == "$yaml_issue" ]] && echo "match" || echo "mismatch"
    return
  fi
  echo "unverifiable"
}

# hitl_intake_directive — the mandatory session-start intake instruction. Emitted (to stdout,
# which Claude Code injects as context) by both the SessionStart hook (hitl-gate.sh) and the
# UserPromptSubmit hook (welcome.sh) whenever no change is active for the current branch.
hitl_intake_directive() {
  cat <<'DIRECTIVE'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⛔ HITL — NO ACTIVE CHANGE FOR THIS BRANCH

  This is a HITL-enabled project. Before any real work (writing code, editing
  files) you MUST take the user through change intake. Intake itself is a normal
  conversation — talking through the work and creating an issue is expected and
  encouraged, not blocked:

    1. If the user has no issue yet, chat to shape the work, then create one
       (gh issue create, /hitl:pm-add-feature, or /hitl:pm-report-bug). If they
       already have an issue, help them choose it.
    2. Determine the right HITL workflow for it (development / brownfield /
       migration / prd) by reading the issue and confirming with the user.
    3. Show the full ordered step plan for that workflow.
    4. Write + commit + push .hitl/current-change.yaml, then follow the breadcrumb.

  Run  /hitl:dev-start-change  to do all of this. You may freely discuss and create
  the issue first — just don't start editing files until a change is active.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIRECTIVE
}

# hitl_render_trail <yaml> [color]
#   Render the windowed step trail (3 back + current + 3 ahead), e.g.:
#     … ✓2.Figma ▶3.Impact ·4.ROI ·5.Docs ·6.IaC …
#   Pass "color" as the 2nd arg to wrap the current step in green ANSI (for the status line).
#   Glyphs come from each step's status: done ✓ · current ▶ · open ·
hitl_render_trail() {
  local f="$1" color="${2:-}"
  hitl_steps "$f" | awk -F'|' -v color="$color" '
    BEGIN { GRN="\033[32m"; RST="\033[0m" }
    { n[NR]=$1; lbl[NR]=$2; st[NR]=$3; if ($3=="current") cur=NR }
    END {
      total=NR
      if (cur==0) cur=1
      ws=cur-3; if (ws<1) ws=1
      we=cur+3; if (we>total) we=total
      out=""
      if (ws>1) out="… "
      for (i=ws; i<=we; i++) {
        glyph="·"
        if (st[i]=="done") glyph="✓"
        else if (st[i]=="current") glyph="▶"
        seg=glyph n[i] "." lbl[i]
        if (st[i]=="current" && color=="color") seg=GRN seg RST
        out=out seg " "
      }
      if (we<total) out=out "…"
      printf "%s", out
    }
  '
}
